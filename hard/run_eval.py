#!/usr/bin/env python3
"""开启工具的 pi 评测：每题在独立工作目录中运行，模型自行写代码处理真实 CSV"""

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from scoring import score, short

ROOT = Path(__file__).parent
DATA = ROOT / "data"
VENV = ROOT.parent / ".venv"
WORK = ROOT / "work"
RESULTS = ROOT / "results"

MODELS = {
    "deepseek-flash": ("newapi", "deepseek-flash"),
    "claude-haiku-5-5": ("newapi", "claude-haiku-5-5"),
}

HINT = {
    "integer": "答案为整数（JSON number）。",
    "number": "答案为数字（JSON number），按题目要求的小数位四舍五入。",
    "string": "答案为字符串（JSON string）。",
    "list": "答案为 JSON 数组，元素顺序按题目要求。",
    "dict": "答案为 JSON 对象，键为字符串。",
    "set": "答案为 JSON 数组，顺序不限。",
    "json": "答案为 JSON 对象，字段名与题目一致。",
}

PROMPT = """当前工作目录是一个数据分析工作区，包含数据文件：{files}，以及 README.md（数据字典与统一口径，必须先阅读并严格遵守）。

任务（难度 L{level}）：{question}

要求：
- 使用 bash 运行 Python 代码完成计算（python3 已安装 pandas、numpy、scipy），不要心算或估算。
- {output}
- 只读写当前工作目录内的文件。
"""

lock = threading.Lock()


def qhash(case):
    return hashlib.sha1(json.dumps([case["question"], case["files"]], ensure_ascii=False).encode()).hexdigest()[:12]


def build_prompt(case):
    if case["answer_type"] == "csv":
        out = f"把结果写入 {case['expected']}（UTF-8、逗号分隔、含表头、不含索引列），并在 answer.json 中写入 {{\"answer\": \"{case['expected']}\"}}。"
    else:
        out = f"完成后把最终答案写入当前目录的 answer.json，格式为 {{\"answer\": <答案>}}。{HINT[case['answer_type']]}"
    return PROMPT.format(files="、".join(case["files"]), level=case["level"], question=case["question"], output=out)


def parse_events(path):
    m = {"turns": 0, "tool_calls": 0, "tool_errors": 0, "tokens_in": 0, "tokens_out": 0, "cost": 0.0, "final_text": "", "api_error": None}
    if not path.exists():
        return m
    for line in path.open(encoding="utf-8", errors="replace"):
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("type") == "message_end":
            msg = e.get("message", {})
            if msg.get("role") == "assistant":
                m["turns"] += 1
                u = msg.get("usage") or {}
                m["tokens_in"] += (u.get("input") or 0) + (u.get("cacheRead") or 0) + (u.get("cacheWrite") or 0)
                m["tokens_out"] += u.get("output") or 0
                m["cost"] += (u.get("cost") or {}).get("total") or 0
                if msg.get("stopReason") == "error":
                    m["api_error"] = (msg.get("errorMessage") or "unknown")[:300]
                content = msg.get("content") or []
                m["tool_calls"] += sum(1 for c in content if c.get("type") == "toolCall")
                texts = [c.get("text", "") for c in content if c.get("type") == "text"]
                if texts:
                    m["final_text"] = texts[-1][-300:]
            elif msg.get("role") == "toolResult" and msg.get("isError"):
                m["tool_errors"] += 1
    m["cost"] = round(m["cost"], 6)
    return m


def sandbox_prefix(wd):
    """bubblewrap：根文件系统只读；家目录换成空 tmpfs，只读挂回 pi 程序与 .venv；仅工作目录可写；/tmp 每题独立。
    pi 启动时要在 ~/.pi 里建锁文件，所以 ~/.pi 用临时覆盖层：沙箱内可写，写入随沙箱丢弃，不改动宿主机配置。"""
    home = Path.home()
    cmd = ["bwrap", "--die-with-parent", "--unshare-pid", "--unshare-ipc", "--unshare-uts",
           "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc",
           "--tmpfs", "/tmp", "--tmpfs", str(home),
           "--overlay-src", str(home / ".pi"), "--tmp-overlay", str(home / ".pi")]
    for p in [Path(shutil.which("pi")).parent.parent, VENV.resolve()]:
        cmd += ["--ro-bind", str(p), str(p)]
    return cmd + ["--bind", str(wd), str(wd), "--chdir", str(wd), "--setenv", "TMPDIR", "/tmp", "--"]


def run_once(name, case, args, wd):
    if wd.exists():
        shutil.rmtree(wd)
    wd.mkdir(parents=True)
    for f in case["files"]:
        src, dst = Path(args.data) / f, wd / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy(src, dst)
    shutil.copy(args.readme, wd / "README.md")
    provider, model = MODELS[name]
    cmd = ["pi", "--provider", provider, "--model", model, "-p", "--no-session", "-nc", "-ns", "-np", "-ne",
           "--no-mcp", "--offline", "--mode", "json"]
    if args.thinking:
        cmd += ["--thinking", args.thinking]
    if args.sandbox == "bwrap":
        cmd = sandbox_prefix(wd.resolve()) + cmd
    env = {**os.environ, "PATH": f"{VENV / 'bin'}:{os.environ['PATH']}", "VIRTUAL_ENV": str(VENV)}
    t0 = time.time()
    timed_out = False
    with open(wd / "events.jsonl", "w") as out, open(wd / "stderr.txt", "w") as err:
        p = subprocess.Popen(cmd, cwd=wd, stdin=subprocess.PIPE, stdout=out, stderr=err, text=True,
                             env=env, start_new_session=True)
        p.stdin.write(build_prompt(case))
        p.stdin.close()
        try:
            p.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
            timed_out = True
    wall = time.time() - t0
    m = parse_events(wd / "events.jsonl")
    stderr = (wd / "stderr.txt").read_text(errors="replace")[-400:]
    # 接口报错（额度不足、限流、5xx 等）会中断模型的工作，属于基础设施失败，需要重试，不能算模型答错
    infra = (not timed_out) and (p.returncode != 0 or m["turns"] == 0 or m["api_error"] is not None)
    if infra and m["api_error"]:
        stderr = m["api_error"]
    return wall, timed_out, infra, m, stderr, p.returncode


def run_case(name, case, args, out_path):
    wd = WORK / args.tag / name / f"{case['id']:03d}"
    for attempt in range(args.retries + 1):
        wall, timed_out, infra, m, stderr, rc = run_once(name, case, args, wd)
        if not infra:
            break
        time.sleep(5 * (attempt + 1))
    correct, parsed, reason = score(case, wd)
    if timed_out:
        reason = "超时；" + reason
    for f in case["files"] + ["README.md"]:
        p = wd / f
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink(missing_ok=True)
    for d in sorted((x for x in wd.rglob("*") if x.is_dir()), reverse=True):
        if not any(d.iterdir()):
            d.rmdir()
    rec = {"id": case["id"], "qhash": qhash(case), "level": case["level"], "category": case["category"],
           "model": name, "answer_type": case["answer_type"], "expected": short(case["expected"]),
           "parsed": parsed, "correct": correct, "reason": reason, "wall": round(wall, 1),
           "timed_out": timed_out, "error": f"rc={rc} {stderr}" if infra else None, "sandbox": args.sandbox, **m}
    with lock, out_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=",".join(MODELS))
    ap.add_argument("--levels", default="1-10", help="如 1-3 或 1,5,10")
    ap.add_argument("--ids", default="", help="只跑指定题号，逗号分隔")
    ap.add_argument("--limit", type=int, default=0, help="每级只跑前 N 题")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--thinking", default=None)
    ap.add_argument("--tag", default="tools")
    ap.add_argument("--cases", default=str(ROOT / "test_cases.json"))
    ap.add_argument("--readme", default=str(DATA / "README.md"))
    ap.add_argument("--data", default=str(DATA), help="题目 files 所在的数据目录")
    ap.add_argument("--sandbox", choices=["bwrap", "none"], default="bwrap",
                    help="bwrap：每题在 bubblewrap 沙箱中运行（默认）；none：不隔离")
    args = ap.parse_args()
    if args.sandbox == "bwrap" and not shutil.which("bwrap"):
        raise SystemExit("未找到 bwrap，请先安装 bubblewrap，或使用 --sandbox none")

    if "-" in args.levels:
        a, b = map(int, args.levels.split("-"))
        levels = set(range(a, b + 1))
    else:
        levels = set(map(int, args.levels.split(",")))
    all_cases = json.load(open(args.cases, encoding="utf-8"))
    cases = [c for c in all_cases if c["level"] in levels]
    if args.ids:
        ids = set(map(int, args.ids.split(",")))
        cases = [c for c in cases if c["id"] in ids]
    if args.limit:
        seen = {}
        cases = [c for c in cases if seen.setdefault(c["level"], []).append(1) or len(seen[c["level"]]) <= args.limit]
    by_id = {c["id"]: c for c in all_cases}

    outdir = RESULTS / args.tag
    outdir.mkdir(parents=True, exist_ok=True)
    jobs = []
    for name in args.models.split(","):
        out_path = outdir / f"{name}.jsonl"
        done = {}
        if out_path.exists():
            for line in out_path.open(encoding="utf-8"):
                r = json.loads(line)
                if r["error"] is None and r["id"] in by_id and r["qhash"] == qhash(by_id[r["id"]]):
                    done[r["id"]] = r
        with out_path.open("w", encoding="utf-8") as f:
            for r in done.values():
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        jobs += [(name, c, out_path) for c in cases if c["id"] not in done]

    jobs.sort(key=lambda j: (j[1]["id"], j[0]))  # 两个模型交替排队，中途出问题时双方进度一致
    print(f"待运行 {len(jobs)} 个任务，并发 {args.workers}，单题超时 {args.timeout}s", flush=True)
    quota_streak, tripped = 0, False
    with ThreadPoolExecutor(args.workers) as ex:
        futs = [ex.submit(run_case, n, c, args, p) for n, c, p in jobs]
        for i, fu in enumerate(as_completed(futs), 1):
            if fu.cancelled():
                continue
            r = fu.result()
            mark = "✓" if r["correct"] else ("E" if r["error"] else "✗")
            print(f"[{i}/{len(jobs)}] {r['model']:<17} L{r['level']:<2} #{r['id']:<3} {mark} {r['wall']:>6}s "
                  f"tools={r['tool_calls']:<3} ${r['cost']:.4f} {'' if r['correct'] else (r['error'] or r['reason'])[:60]}", flush=True)
            quota_streak = quota_streak + 1 if r["error"] and "quota" in r["error"] else 0
            if quota_streak >= 8 and not tripped:
                tripped = True
                n = sum(f.cancel() for f in futs)
                print(f"连续 {quota_streak} 个任务因额度不足失败，已取消剩余 {n} 个未开始的任务。补充额度后用同一个 --tag 重跑即可。", flush=True)
    print(f"完成。结果目录：{outdir}")


if __name__ == "__main__":
    main()

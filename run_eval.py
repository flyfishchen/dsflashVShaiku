#!/usr/bin/env python3
"""用 pi 对比评测 deepseek-flash 与 claude-haiku-5-5 的数据处理分析能力"""

import argparse
import hashlib
import json
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).parent
RESULTS = ROOT / "results"

MODELS = {
    "deepseek-flash": ("newapi", "deepseek-flash"),
    "claude-haiku-5-5": ("newapi", "claude-haiku-5-5"),
}

SYSTEM_PROMPT = "你是一名严谨的数据分析师。请仔细计算，最后只输出最终答案本身，不要输出单位、解释或推导过程。"

lock = threading.Lock()


def call_pi(provider, model, question, thinking, timeout):
    cmd = ["pi", "--provider", provider, "--model", model, "-p", "-nt", "--no-session",
           "-nc", "-ns", "-np", "-ne", "--no-mcp", "--offline", "--system-prompt", SYSTEM_PROMPT]
    if thinking:
        cmd += ["--thinking", thinking]
    t0 = time.time()
    p = subprocess.run(cmd, input=question, capture_output=True, text=True, timeout=timeout)
    return p.stdout.strip(), p.stderr.strip(), p.returncode, time.time() - t0


NUM_RE = re.compile(r"-?\d[\d,]*\.?\d*(?:[eE]-?\d+)?|-?\.\d+")


def extract_number(text):
    text = re.sub(r"\\boxed\{([^}]*)\}", r"\1", text)
    nums = NUM_RE.findall(text)
    if not nums:
        return None
    raw = nums[-1].replace(",", "")
    try:
        val = float(raw)
    except ValueError:
        return None
    if "%" in text[text.rfind(nums[-1]):text.rfind(nums[-1]) + len(nums[-1]) + 2]:
        val /= 100
    return val


def score(case, output):
    exp = case["expected"]
    if case["answer_type"] == "string":
        norm = lambda s: re.sub(r"[\s`*\"'。.，,：:]", "", str(s)).lower()
        o, e = norm(output), norm(exp)
        return o == e or (e in o and len(o) <= len(e) + 12), output[-60:]
    got = extract_number(output)
    if got is None:
        return False, None
    exp = float(exp)
    if case["answer_type"] == "integer":
        return abs(got - exp) < 1e-9, got
    # 允许 1 个末位单位的舍入差异；未要求保留小数则须精确
    m = re.search(r"保留(\d)位小数", case["question"])
    unit = 10 ** -int(m.group(1)) if m else (1 if "取整" in case["question"] else 0)
    tol = unit + 1e-9
    ok = abs(got - exp) <= tol
    # 百分数写法容错（如 45.3 与 0.453）
    if not ok and exp != 0:
        ok = abs(got / 100 - exp) <= tol or abs(got * 100 - exp) <= tol
    return ok, got


def qhash(case):
    return hashlib.sha1(case["question"].encode()).hexdigest()[:12]


def load_done(path, cases_by_id):
    """只保留无错误、且题面未变的记录"""
    done = {}
    if path.exists():
        for line in path.open(encoding="utf-8"):
            r = json.loads(line)
            c = cases_by_id.get(r["id"])
            if r.get("error") is None and c and r.get("qhash") == qhash(c):
                done[r["id"]] = r
    return done


def run_one(name, case, args, out_path):
    provider, model = MODELS[name]
    err, out, latency = None, "", 0.0
    for attempt in range(args.retries + 1):
        try:
            out, stderr, rc, latency = call_pi(provider, model, case["question"], args.thinking, args.timeout)
            if rc == 0 and out:
                err = None
                break
            err = f"rc={rc} {stderr[-300:]}"
        except subprocess.TimeoutExpired:
            err = "timeout"
        time.sleep(2 * (attempt + 1))
    correct, parsed = score(case, out) if err is None else (False, None)
    rec = {"id": case["id"], "qhash": qhash(case), "level": case["level"], "category": case["category"], "model": name,
           "expected": case["expected"], "parsed": parsed, "correct": correct,
           "output": out, "latency": round(latency, 2), "error": err}
    with lock, out_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=",".join(MODELS), help="逗号分隔")
    ap.add_argument("--levels", default="1-10", help="如 1-3 或 1,5,10")
    ap.add_argument("--limit", type=int, default=0, help="每级只跑前 N 条（调试用）")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--thinking", default=None, help="off/low/medium/high，默认用模型默认值")
    ap.add_argument("--tag", default="default", help="结果子目录名，区分不同配置")
    args = ap.parse_args()

    if "-" in args.levels:
        a, b = map(int, args.levels.split("-"))
        levels = set(range(a, b + 1))
    else:
        levels = set(map(int, args.levels.split(",")))

    all_cases = json.load(open(ROOT / "test_cases.json", encoding="utf-8"))
    cases_by_id = {c["id"]: c for c in all_cases}
    cases = [c for c in all_cases if c["level"] in levels]
    if args.limit:
        per = {}
        cases = [c for c in cases if per.setdefault(c["level"], []).append(c) or len(per[c["level"]]) <= args.limit]

    outdir = RESULTS / args.tag
    outdir.mkdir(parents=True, exist_ok=True)

    jobs = []
    for name in args.models.split(","):
        out_path = outdir / f"{name}.jsonl"
        done = load_done(out_path, cases_by_id)
        # 重写文件：丢弃失败记录，保留成功记录，以便重试
        with out_path.open("w", encoding="utf-8") as f:
            for r in done.values():
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        jobs += [(name, c, out_path) for c in cases if c["id"] not in done]

    print(f"待运行 {len(jobs)} 个任务，并发 {args.workers}")
    n_ok = 0
    with ThreadPoolExecutor(args.workers) as ex:
        futs = [ex.submit(run_one, n, c, args, p) for n, c, p in jobs]
        for i, fu in enumerate(as_completed(futs), 1):
            r = fu.result()
            n_ok += r["correct"]
            mark = "✓" if r["correct"] else ("E" if r["error"] else "✗")
            print(f"[{i}/{len(jobs)}] {r['model']:<17} L{r['level']:<2} #{r['id']:<3} {mark} "
                  f"exp={r['expected']} got={r['parsed']} {r['latency']}s", flush=True)
    print(f"完成。结果目录：{outdir}")


if __name__ == "__main__":
    main()

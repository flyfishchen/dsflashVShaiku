#!/usr/bin/env python3
"""汇总工具型评测结果：用工作目录中保留的答案按当前标准答案重新判分"""

import json
import sys
from collections import defaultdict
from pathlib import Path

from run_eval import WORK, qhash
from scoring import score, short

ROOT = Path(__file__).parent
tag = sys.argv[1] if len(sys.argv) > 1 else "tools"
cases_file = sys.argv[2] if len(sys.argv) > 2 else ROOT / "test_cases.json"
outdir = ROOT / "results" / tag
cases = {c["id"]: c for c in json.load(open(cases_file, encoding="utf-8"))}
LEVEL = {1: "基础读取", 2: "过滤与类型解析", 3: "分组聚合", 4: "文本与正则", 5: "日期与时区",
         6: "统计推断", 7: "多表联结", 8: "数据质量与清洗", 9: "复杂变换", 10: "高级分析"}

data = {}
for f in sorted(outdir.glob("*.jsonl")):
    recs = {}
    for line in f.open(encoding="utf-8"):
        r = json.loads(line)
        c = cases.get(r["id"])
        if not c or r["qhash"] != qhash(c):
            continue
        if r["error"] is None:
            ok, parsed, why = score(c, WORK / tag / f.stem / f"{r['id']:03d}")
            r.update(correct=ok, parsed=parsed, expected=short(c["expected"]),
                     reason=("超时；" if r["timed_out"] else "") + why)
        recs[r["id"]] = r
    data[f.stem] = recs
models = list(data)


def agg(rs):
    n = len(rs)
    return {"n": n, "correct": sum(r["correct"] for r in rs),
            "wall": round(sum(r["wall"] for r in rs) / n, 1) if n else 0,
            "tools": round(sum(r["tool_calls"] for r in rs) / n, 1) if n else 0,
            "cost": round(sum(r["cost"] for r in rs), 4),
            "tok_in": sum(r["tokens_in"] for r in rs), "tok_out": sum(r["tokens_out"] for r in rs),
            "timeouts": sum(r["timed_out"] for r in rs), "errors": sum(r["error"] is not None for r in rs)}


summary = {"tag": tag, "overall": {}, "levels": {}, "types": {}, "failures": defaultdict(list)}
for m in models:
    rs = list(data[m].values())
    summary["overall"][m] = agg(rs)
    for lv in range(1, 11):
        summary["levels"].setdefault(lv, {})[m] = agg([r for r in rs if r["level"] == lv])
    for t in sorted({c["answer_type"] for c in cases.values()}):
        summary["types"].setdefault(t, {})[m] = agg([r for r in rs if r["answer_type"] == t])
    for r in sorted(rs, key=lambda r: r["id"]):
        if not r["correct"]:
            summary["failures"][m].append({k: r[k] for k in ("id", "level", "expected", "parsed", "reason", "wall", "tool_calls")})
ids = set.intersection(*(set(d) for d in data.values())) if data else set()
summary["both_wrong"] = sorted(i for i in ids if all(not data[m][i]["correct"] for m in models))
summary["only"] = {m: sorted(i for i in ids if data[m][i]["correct"] and all(not data[o][i]["correct"] for o in models if o != m)) for m in models}

hdr = "".join(f"{m:>30}" for m in models)
print(f"\n{'等级':<16}{hdr}")
print(f"{'':<16}" + "".join(f"{'正确   耗时  工具  费用':>30}" for _ in models))
for lv in range(1, 11):
    row = summary["levels"][lv]
    print(f"L{lv:<2} {LEVEL[lv]:<12}" + "".join(
        f"{row[m]['correct']:>4}/{row[m]['n']:<3}{row[m]['wall']:>7}s{row[m]['tools']:>6}  ${row[m]['cost']:<7.4f}".rjust(30) for m in models))
print("-" * (16 + 30 * len(models)))
for m in models:
    s = summary["overall"][m]
    print(f"{m}: {s['correct']}/{s['n']} = {100 * s['correct'] / max(s['n'], 1):.1f}%  平均耗时 {s['wall']}s  "
          f"平均工具调用 {s['tools']}  总费用 ${s['cost']}  输入 {s['tok_in']:,} / 输出 {s['tok_out']:,} tokens  "
          f"超时 {s['timeouts']}  调用失败 {s['errors']}")
print("\n按答案类型：")
for t, row in summary["types"].items():
    print(f"  {t:<8}" + "".join(f"  {m}: {row[m]['correct']}/{row[m]['n']}" for m in models))
print(f"\n两个模型都错：{summary['both_wrong']}")
for m, v in summary["only"].items():
    print(f"仅 {m} 答对：{v}")
json.dump(summary, open(outdir / "summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\n已写入 {outdir / 'summary.json'}")

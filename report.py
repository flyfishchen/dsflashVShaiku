#!/usr/bin/env python3
"""汇总评测结果，输出终端表格与 summary.json"""

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
from run_eval import qhash, score  # noqa: E402

tag = sys.argv[1] if len(sys.argv) > 1 else "full"
outdir = ROOT / "results" / tag
cases = {c["id"]: c for c in json.load(open(ROOT / "test_cases.json", encoding="utf-8"))}

LEVEL_NAMES = {1: "基础运算", 2: "数据过滤", 3: "聚合统计", 4: "字符串处理", 5: "日期时间",
               6: "统计分析", 7: "多表联结", 8: "数据质量", 9: "复杂变换", 10: "高级分析"}

data = {}
for f in sorted(outdir.glob("*.jsonl")):
    recs = {}
    for line in f.open(encoding="utf-8"):
        r = json.loads(line)
        c = cases.get(r["id"])
        if not c or r.get("qhash") != qhash(c):
            continue
        # 按当前期望答案与判分规则重新判分
        if r["error"] is None:
            r["correct"], r["parsed"] = score(c, r["output"])
            r["expected"] = c["expected"]
        recs[r["id"]] = r
    data[f.stem] = recs

models = list(data)
summary = {"tag": tag, "models": {}, "levels": {}, "failures": defaultdict(list)}

for m in models:
    recs = data[m].values()
    lat = sorted(r["latency"] for r in recs if r["error"] is None)
    summary["models"][m] = {
        "n": len(recs), "correct": sum(r["correct"] for r in recs),
        "errors": sum(r["error"] is not None for r in recs),
        "avg_latency": round(sum(lat) / len(lat), 2) if lat else None,
        "p50_latency": lat[len(lat) // 2] if lat else None,
    }
    for r in recs:
        if not r["correct"]:
            summary["failures"][m].append({k: r[k] for k in ("id", "level", "expected", "parsed", "error")}
                                          | {"output": r["output"][-200:]})

for lv in range(1, 11):
    row = {}
    for m in models:
        rs = [r for r in data[m].values() if r["level"] == lv]
        row[m] = {"n": len(rs), "correct": sum(r["correct"] for r in rs),
                  "avg_latency": round(sum(r["latency"] for r in rs) / len(rs), 2) if rs else None}
    summary["levels"][lv] = row

both_wrong = [i for i in cases if all(i in data[m] and not data[m][i]["correct"] for m in models)]
summary["both_wrong"] = both_wrong

w = 22
print(f"\n{'等级':<12}" + "".join(f"{m:>{w}}" for m in models))
for lv in range(1, 11):
    cells = "".join(f"{summary['levels'][lv][m]['correct']:>3}/{summary['levels'][lv][m]['n']:<3} "
                    f"({summary['levels'][lv][m]['avg_latency']}s)".rjust(w) for m in models)
    print(f"L{lv:<2} {LEVEL_NAMES[lv]:<8}" + cells)
print("-" * (12 + w * len(models)))
for m in models:
    s = summary["models"][m]
    print(f"{m}: {s['correct']}/{s['n']} = {100 * s['correct'] / max(s['n'], 1):.1f}%  "
          f"错误调用 {s['errors']}  平均延迟 {s['avg_latency']}s  P50 {s['p50_latency']}s")
print(f"两个模型都答错的用例：{both_wrong}")

json.dump(summary, open(outdir / "summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"\n已写入 {outdir / 'summary.json'}")

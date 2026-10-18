#!/usr/bin/env python3
"""汇总同一配置下的多轮重复评测：正确率均值/标准差、逐题稳定性、配对显著性检验"""

import argparse
import json
import statistics as st
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

from run_eval import WORK, qhash
from scoring import score

ROOT = Path(__file__).parent
LEVEL = {1: "基础读取", 2: "过滤与类型解析", 3: "分组聚合", 4: "文本与正则", 5: "日期与时区",
         6: "统计推断", 7: "多表联结", 8: "数据质量与清洗", 9: "复杂变换", 10: "高级分析"}

ap = argparse.ArgumentParser()
ap.add_argument("tags", nargs="+")
ap.add_argument("--cases", default=str(ROOT / "test_cases_nohint.json"))
ap.add_argument("--out", default=str(ROOT / "results" / "repeat_summary.json"))
args = ap.parse_args()

cases = {c["id"]: c for c in json.load(open(args.cases, encoding="utf-8"))}
# runs[model][tag][id] = record（按当前标准答案重新判分）
runs = defaultdict(dict)
for tag in args.tags:
    for f in sorted((ROOT / "results" / tag).glob("*.jsonl")):
        recs = {}
        for line in f.open(encoding="utf-8"):
            r = json.loads(line)
            c = cases.get(r["id"])
            if not c or r["qhash"] != qhash(c) or r["error"] is not None:
                continue
            r["correct"], r["parsed"], r["reason"] = score(c, WORK / tag / f.stem / f"{r['id']:03d}")
            recs[r["id"]] = r
        runs[f.stem][tag] = recs
models = sorted(runs)
for m in models:
    for tag, recs in runs[m].items():
        missing = set(cases) - set(recs)
        if missing:
            print(f"警告：{m} {tag} 缺少 {len(missing)} 题：{sorted(missing)[:20]}")


def msd(xs, fmt="{:.1f}"):
    return f"{fmt.format(st.mean(xs))} ± {fmt.format(st.stdev(xs) if len(xs) > 1 else 0)}"


out = {"tags": args.tags, "models": {}, "levels": {}, "per_case": {}}
print(f"\n======== {len(args.tags)} 轮重复评测（{', '.join(args.tags)}）========\n")
for m in models:
    per_run = {t: sum(r["correct"] for r in recs.values()) for t, recs in runs[m].items()}
    eff = {k: [st.mean(r[k] for r in recs.values()) for recs in runs[m].values()] for k in ("wall", "tool_calls")}
    cost = [sum(r["cost"] for r in recs.values()) for recs in runs[m].values()]
    out["models"][m] = {"per_run_correct": per_run, "wall": eff["wall"], "tool_calls": eff["tool_calls"], "cost": cost}
    print(f"{m:<18} 每轮正确数 {list(per_run.values())}  均值 {msd(list(per_run.values()))}  "
          f"平均耗时 {msd(eff['wall'])}s  工具调用 {msd(eff['tool_calls'])}  每轮费用 ${msd(cost, '{:.3f}')}")

print(f"\n{'等级':<16}" + "".join(f"{m:>26}" for m in models))
for lv in range(1, 11):
    ids = [i for i, c in cases.items() if c["level"] == lv]
    row = {}
    for m in models:
        xs = [sum(recs[i]["correct"] for i in ids if i in recs) for recs in runs[m].values()]
        ws = [st.mean(recs[i]["wall"] for i in ids if i in recs) for recs in runs[m].values()]
        row[m] = {"correct": xs, "wall": ws}
    out["levels"][lv] = row
    print(f"L{lv:<2} {LEVEL[lv]:<12}" + "".join(
        f"{msd(row[m]['correct'])}/20  {st.mean(row[m]['wall']):>5.1f}s".rjust(26) for m in models))

# 逐题通过率
rate = {m: {i: np.mean([runs[m][t][i]["correct"] for t in runs[m] if i in runs[m][t]]) for i in cases} for m in models}
n_runs = {m: len(runs[m]) for m in models}
print("\n逐题稳定性（只列至少一个模型在某轮答错的题）：")
print(f"{'题号':<6}{'等级':<6}" + "".join(f"{m:>20}" for m in models) + "   题目")
for i in sorted(cases):
    if all(rate[m][i] == 1 for m in models):
        continue
    out["per_case"][i] = {m: rate[m][i] for m in models}
    cells = "".join(f"{round(rate[m][i] * n_runs[m])}/{n_runs[m]}".rjust(20) for m in models)
    print(f"#{i:<5}L{cases[i]['level']:<5}{cells}   {cases[i]['question'][:46]}")

if len(models) == 2:
    a, b = models
    diff = np.array([rate[a][i] - rate[b][i] for i in sorted(cases)])
    wins, losses = int((diff > 0).sum()), int((diff < 0).sum())
    p_sign = stats.binomtest(wins, wins + losses).pvalue if wins + losses else 1.0
    rng = np.random.default_rng(0)
    boots = [diff[rng.integers(0, len(diff), len(diff))].mean() * 100 for _ in range(20000)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    stable = {m: sorted(i for i in cases if rate[m][i] == 0) for m in models}
    flaky = {m: sorted(i for i in cases if 0 < rate[m][i] < 1) for m in models}
    out["paired"] = {"wins": {a: wins, b: losses}, "sign_test_p": p_sign,
                     "acc_diff_pct": float(diff.mean() * 100), "ci95": [float(lo), float(hi)],
                     "stable_fail": stable, "flaky": flaky}
    print(f"\n配对比较（{a} − {b}）：")
    print(f"  正确率差 {diff.mean() * 100:+.2f} 个百分点，按题 bootstrap 95% CI [{lo:+.2f}, {hi:+.2f}]")
    print(f"  逐题通过率 {a} 更高 {wins} 题、{b} 更高 {losses} 题，符号检验 p = {p_sign:.4f}")
    for m in models:
        print(f"  {m}：每轮都错 {stable[m]}；时对时错 {flaky[m]}")

json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
print(f"\n已写入 {args.out}")

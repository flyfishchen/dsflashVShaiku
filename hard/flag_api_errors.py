#!/usr/bin/env python3
"""把运行中出现过接口报错的记录标记为基础设施失败（error 非空），之后用同一个 tag 重跑即可只补跑这些任务"""

import json
import sys
from pathlib import Path

from run_eval import WORK, parse_events

ROOT = Path(__file__).parent
for tag in sys.argv[1:]:
    for f in sorted((ROOT / "results" / tag).glob("*.jsonl")):
        recs = [json.loads(line) for line in f.open(encoding="utf-8")]
        n = 0
        for r in recs:
            wd = WORK / tag / f.stem / f"{r['id']:03d}"
            m = parse_events(wd / "events.jsonl")
            if r["error"] is None and m["api_error"]:
                r["error"] = m["api_error"]
                n += 1
        with f.open("w", encoding="utf-8") as out:
            for r in recs:
                out.write(json.dumps(r, ensure_ascii=False) + "\n")
        valid = sum(r["error"] is None for r in recs)
        print(f"{tag:<8} {f.stem:<18} 标记接口失败 {n:>3} 条；有效记录 {valid}/{len(recs)}，其中答对 {sum(r['correct'] for r in recs if r['error'] is None)}")

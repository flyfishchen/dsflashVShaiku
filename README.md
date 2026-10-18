# dsflashVShaiku

用 pi（`@earendil-works/pi-coding-agent` 1.3.0）评测 **DeepSeek V4.1-Flash-1017** 与 **Claude Haiku 5.5** 的数据处理与分析能力（pi 中的模型 ID 分别为 `newapi/deepseek-flash` 和 `newapi/claude-haiku-5-5`）。题目分 10 个难度等级、每级 20 题，从读文件计数一直到 cohort 留存、关联规则和统计检验。完整分析见 [`reports/eval_report.html`](reports/eval_report.html)（下载后用浏览器打开）。

## 结论

| 轮次 | 条件 | Haiku 5.5 | DeepSeek | 平均每题耗时 H / D |
|---|---|---|---|---|
| 1 | 关闭工具，数据写在题目里（10–25 行），只靠推理 | 199/200 | 200/200 | 3.7s / 1.9s |
| 2 | 开启工具处理真实 CSV，README 写明所有脏数据及处理口径 | 200/200 | 200/200 | 15.0s / 9.6s |
| 3 | 同上，但 README 不提示脏数据（单轮，仅作参考） | 198/200 | 194/200 | 18.6s / 20.7s |
| 4 | 同第 3 轮，独立重复 3 轮 | **199.0 ± 0.0** | **195.7 ± 1.2** | 19.7s / 20.8s |

- 口径写清楚时（第 1、2 轮），两个模型都接近满分，难度等级拉不开差距。
- 需要自己发现脏数据时（第 4 轮），Haiku 小幅稳定领先。正确率差 +1.67 个百分点，按题 bootstrap 95% CI 为 [+0.17, +3.33]，符号检验 p = 0.039。
- 差距几乎全部来自 A/B 实验中同时出现在两组的 30 个用户。DeepSeek 在 21 次相关运行中发现了 18 次，但有 8 次权衡后选择不剔除；Haiku 21 次都剔除了。README 没有逐字写明这种情况怎么处理，如果把“不处理”也算对，两者持平。所以这体现的是判断风格的差异，不是计算能力的差距。
- 效率按难度分化：DeepSeek 在简单题上更快，复杂题上更慢；中位耗时 12.2s 对 16.8s，P90 耗时 45.9s 对 33.2s。费用基本持平，每千题约 $2.4 对 $2.3。

## 目录结构

```
.
├── generate_cases.py        # 第 1 轮：生成 200 道题（数据直接写在题面里）
├── run_eval.py              # 第 1 轮：关闭工具调用 pi
├── report.py                # 第 1 轮：汇总
├── test_cases.json
├── results/full/            # 第 1 轮结果
├── reports/eval_report.html # 完整分析报告
└── hard/                    # 第 2–4 轮：开启工具，处理真实 CSV
    ├── gen_data.py          # 生成干净真值（truth/）与脏数据（data/）
    ├── gen_cases.py         # 从真值计算 200 道题的标准答案（expected/）
    ├── make_nohint.py       # 生成无提示版题目 test_cases_nohint.json
    ├── README_nohint.md     # 无提示版数据字典（第 3、4 轮使用）
    ├── data/                # 模型可见的数据，以及有提示版 README（第 2 轮使用）
    ├── run_eval.py          # 每题建独立工作目录，开启工具调用 pi
    ├── scoring.py           # 判分：answer.json 与输出 CSV
    ├── report.py            # 单轮汇总
    ├── compare_runs.py      # 多轮汇总、逐题稳定性、配对检验
    └── results/             # 各轮结果（tools、nohint、nohint_r1..r3）
```

`hard/truth/`、`hard/expected/` 和逐次运行日志 `hard/work/`（约 950MB）没有提交，可以用下面的命令重新生成。

## 数据集与陷阱

第 2–4 轮使用一套合成的电商数据：订单 2.5 万条、订单明细 4.9 万条、行为事件 5.4 万条，另有客户、商品、汇率、每日指标、旧系统导出、A/B 实验、员工和客服工单，共 11 个文件。数据中刻意放入以下问题：

- 整行重复；同一城市有多种写法（北京 / 北京市 / Beijing / 首尾空格）；性别和出生日期格式混用
- 价格是 `¥1,299.00` 这样的字符串；订单时间混用 UTC（以 Z 结尾）与北京时间
- quantity 为 0 或 −1；外币需按下单当日汇率换算，没有当日汇率时用之前最近一天的
- GBK 编码、分号分隔、带千分位的旧系统文件；跨年时区边界；A/B 实验中有用户同时分到两组
- 孤儿外键、缺失日期、负数收入、被误录 10 倍的单价（规范要求以文件为准，不做修正）

标准答案只从生成时的干净真值计算，不依赖任何清洗代码。另用一个只读脏文件的独立清洗器做核对，16 项核心字段与真值完全一致。

## 复现

前提：已安装 pi 1.3.0，且 newapi provider 下能使用 `deepseek-flash` 和 `claude-haiku-5-5`（可用 `pi --list-models` 确认）。

```bash
# Python 环境（第 2–4 轮的数据生成、判分和模型执行代码都使用它）
uv venv .venv
uv pip install --python .venv/bin/python pandas numpy scipy

# 第 1 轮：关闭工具
python3 generate_cases.py
python3 run_eval.py --tag full
python3 report.py full

# 第 2–4 轮：开启工具
cd hard
PY=../.venv/bin/python
$PY gen_data.py
$PY gen_cases.py
$PY make_nohint.py

$PY run_eval.py --tag tools                       # 第 2 轮：有提示
$PY report.py tools

for i in 1 2 3; do                                # 第 4 轮：无提示，重复 3 轮
  $PY run_eval.py --tag nohint_r$i --cases test_cases_nohint.json --readme README_nohint.md --workers 6
done
$PY compare_runs.py nohint_r1 nohint_r2 nohint_r3
```

`hard/run_eval.py` 的常用参数：

| 参数 | 说明 |
|---|---|
| `--models` | 逗号分隔的模型名，默认两个都跑 |
| `--levels` / `--ids` / `--limit` | 只跑部分等级、指定题号，或每级前 N 题 |
| `--workers` / `--timeout` | 并发数（默认 8）、单题超时秒数（默认 900） |
| `--thinking` | 思考强度（off / low / medium / high），默认使用模型自身的设置 |
| `--tag` | 结果目录名；同一个 tag 支持断点续跑，题面改动后会自动重跑该题 |
| `--cases` / `--readme` | 题目文件与放进工作目录的 README |

每道题的事件日志、模型写的代码和产出文件都保存在 `hard/work/<tag>/<模型>/<题号>/`。`report.py` 和 `compare_runs.py` 会读取这些文件，按当前标准答案重新判分，所以修正标准答案后不必重跑模型。

## 注意事项

- 开启工具后，模型以当前用户的权限执行 bash。提示词要求只在当前工作目录内读写，但这只是提示约束。实测 Haiku 在 13%–20% 的任务里会把脚本写到 `/tmp`（DeepSeek 约 4%），未影响评测结果。如果要大规模并行运行，建议用 bubblewrap 等工具做系统层面的隔离。
- 题目和判分由 Claude（Opus 5.5）设计。标准答案取自真值，两个模型使用相同的提示词，每次修正题目都对两个模型同时重跑，但题目风格可能更接近 Claude 系模型的习惯。
- 评测过程中发现并修正过 8 处题目缺陷，例如 Python 的银行家舍入、题意歧义、判分容差过宽等，详见报告第 07 节。

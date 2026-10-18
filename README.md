# dsflashVShaiku

用 pi（`@earendil-works/pi-coding-agent` 1.3.0）评测 **DeepSeek V4.1-Flash-1017** 与 **Claude Haiku 5.5** 的数据处理与分析能力（pi 中的模型 ID 分别为 `newapi/deepseek-flash` 和 `newapi/claude-haiku-5-5`）。共两套题库：v1 用于逐步提高出题难度；v2 是更接近真实工作的高难度题库。每套都分 10 个难度等级、每级 20 题。

**在线报告：https://flyfishchen.github.io/dsflashVShaiku/reports/eval_report.html**（源文件为 [`reports/eval_report.html`](reports/eval_report.html)）。

## 结论

| 轮次 | 题库与条件 | Haiku 5.5 | DeepSeek | 平均每题耗时 H / D |
|---|---|---|---|---|
| 1 | v1：关闭工具，数据写在题目里（10–25 行），只靠推理 | 199/200 | 200/200 | 3.7s / 1.9s |
| 2 | v1：开启工具处理真实 CSV，README 写明所有脏数据及处理口径 | 200/200 | 200/200 | 15.0s / 9.6s |
| 3 | v1：同上，但 README 不提示脏数据（单轮，仅作参考） | 198/200 | 194/200 | 18.6s / 20.7s |
| 4 | v1：同第 3 轮，独立重复 3 轮 | **199.0 ± 0.0** | **195.7 ± 1.2** | 19.7s / 20.8s |
| 5 | v2：高难度题库，不提示具体问题，沙箱隔离，独立重复 3 轮 | **197.7 ± 1.5** | **197.7 ± 0.6** | 46.0s / 54.5s |

- **正确率很接近。** v1 无提示时 Haiku 小幅领先（+1.67 个百分点，符号检验 p = 0.039）；v2 两者打平（差 0.00，95% CI [−1.33, +1.33]）。
- **v1 的差距来自“规范没写到时怎么判断”。** 差距几乎全部出在 A/B 实验中同时分在两组的 30 个用户：DeepSeek 多数时候发现了，却以“规范没逐字写明”为由选择不剔除。v2 把统计口径写全后，这一差距没有再出现。
- **单纯提高难度拉不开差距。** v2 换成对账、实体合并、变更日志回放、MRR 瀑布、多触点归因、根因分解等任务后，两者仍都在 98.8%。
- **失误风格不同。** Haiku 倾向过度套用 README 的通用规范，v2 中 7 次失误有 5 次出在最简单的 L1–L2；DeepSeek 倾向读错定义、把答案写进子目录，失误都在 L4 及以后。
- **效率随任务复杂度分化。** 简单、口径明确的任务 DeepSeek 更快更便宜（v1 有提示时快 36%、便宜 29%）。多步复杂任务 Haiku 更快更省：v2 平均每题 46.0s 对 54.5s，工具调用 6.6 次对 9.0 次，每千题费用 $5.06 对 $5.47。DeepSeek 慢题更多，v2 的 P90 耗时为 127s 对 86s。

## 目录结构

```
.
├── generate_cases.py         # 第 1 轮：生成 200 道题（数据直接写在题面里）
├── run_eval.py               # 第 1 轮：关闭工具调用 pi
├── report.py                 # 第 1 轮：汇总
├── test_cases.json
├── results/full/             # 第 1 轮结果
├── reports/
│   ├── eval_report.html      # 完整分析报告（GitHub Pages 发布）
│   └── make_standalone.py    # 把 Artifact 版报告包装成独立 HTML
└── hard/                     # 第 2–5 轮：开启工具，处理真实数据
    ├── gen_data.py           # v1：生成干净真值（truth/）与脏数据（data/）
    ├── gen_cases.py          # v1：从真值计算 200 道题的标准答案（expected/）
    ├── make_nohint.py        # v1：生成无提示版题目 test_cases_nohint.json
    ├── README_nohint.md      # v1 无提示版数据字典（第 3、4 轮使用）
    ├── data/                 # v1 模型可见的数据，以及有提示版 README（第 2 轮使用）
    ├── v2/
    │   ├── gen_data.py       # v2：生成 34 个数据文件（data/）与真值（truth/）
    │   ├── gen_cases.py      # v2：从真值计算 200 道题的标准答案（expected/）
    │   ├── README_data.md    # v2 数据字典
    │   └── test_cases.json   # v2 题目
    ├── run_eval.py           # 每题建独立工作目录，在沙箱中开启工具调用 pi
    ├── scoring.py            # 判分：answer.json 与输出 CSV
    ├── report.py             # 单轮汇总
    ├── compare_runs.py       # 多轮汇总、逐题稳定性、配对检验
    ├── flag_api_errors.py    # 把运行中遇到接口报错的记录标记为需要重跑
    └── results/              # 各轮结果（tools、nohint、nohint_r1..r3、v2_r1..r3）
```

以下内容没有提交，都可以用下面的命令重新生成：
- `hard/truth/`、`hard/expected/`、`hard/v2/data/`、`hard/v2/truth/`、`hard/v2/expected/`。其中 v2 数据由固定随机种子生成，可以逐字节复现。
- 逐次运行日志 `hard/work/`（约 2.3GB）。

## v1 数据集与陷阱

第 2–4 轮使用一套合成的电商数据：订单 2.5 万条、订单明细 4.9 万条、行为事件 5.4 万条，另有客户、商品、汇率、每日指标、旧系统导出、A/B 实验、员工和客服工单，共 11 个文件。数据中刻意放入以下问题：

- 整行重复；同一城市有多种写法（北京 / 北京市 / Beijing / 首尾空格）；性别和出生日期格式混用
- 价格是 `¥1,299.00` 这样的字符串；订单时间混用 UTC（以 Z 结尾）与北京时间
- quantity 为 0 或 −1；外币需按下单当日汇率换算，没有当日汇率时用之前最近一天的
- GBK 编码、分号分隔、带千分位的旧系统文件；跨年时区边界；A/B 实验中有用户同时分到两组
- 孤儿外键、缺失日期、负数收入、被误录 10 倍的单价（规范要求以文件为准，不做修正）

## v2 数据集与题型

第 5 轮使用全新的一套数据，共 34 个文件、约 81MB：

- 中美 6 家门店两年的订单。旧系统按月分区，年中改过字段名，还有跨文件重复；新系统是嵌套 JSON，同一订单有多次导出记录；美国门店有夏令时边界问题。
- 支付网关流水与退款，含漏收、重复扣款、少付、拒付、超额退款和孤儿流水。
- 两套会员系统，手机号和邮箱写法各不相同。
- 商品变更日志（CDC），有乱序和重复事件。
- 库存进销流水、SaaS 订阅事件。
- 103 万行传感器读数，其中 6 台设备实际用华氏度上报。
- 营销触点与转化、三组实验数据。
- 30 万行 Nginx 访问日志，来自两个时区，有截断行和爬虫流量。
- 定长格式的总账。

10 个等级依次为：多格式读取 → 清洗与异常识别 → 对账 → 实体合并 → 时间与时区 → 增量与历史数据（CDC 回放、拉链表、时点关联）→ 业务指标（MRR 瀑布、留存、先进先出与加权平均成本）→ 统计推断进阶（辛普森悖论、CUPED、双重差分、多重检验）→ 归因与分解（5 种归因模型、GMV 根因定位、价量分解）→ 综合分析（多字段 JSON 摘要与多张交付表）。

两套题库的标准答案都只从生成时的干净真值计算，不依赖任何清洗代码。此外各用一个只读脏文件的独立清洗器做核对，v1、v2 各 16 项核心字段都与真值完全一致。

## 复现

前提：
- 已安装 pi 1.3.0，且 newapi provider 下能使用 `deepseek-flash` 和 `claude-haiku-5-5`（可用 `pi --list-models` 确认）。
- 已安装 bubblewrap，且版本支持 `--tmp-overlay`（已在 0.11.1 上验证）。

```bash
# Python 环境（第 2–5 轮的数据生成、判分和模型执行代码都使用它）
uv venv .venv
uv pip install --python .venv/bin/python pandas numpy scipy

# 第 1 轮：关闭工具
python3 generate_cases.py
python3 run_eval.py --tag full
python3 report.py full

# 第 2–4 轮：v1，开启工具
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

# 第 5 轮：v2，重复 3 轮
(cd v2 && ../$PY gen_data.py && ../$PY gen_cases.py)
for i in 1 2 3; do
  $PY run_eval.py --tag v2_r$i --cases v2/test_cases.json --readme v2/README_data.md --data v2/data --workers 8 --timeout 1200
done
$PY compare_runs.py v2_r1 v2_r2 v2_r3 --cases v2/test_cases.json --out results/v2_repeat_summary.json
```

`hard/run_eval.py` 的常用参数：

| 参数 | 说明 |
|---|---|
| `--models` | 逗号分隔的模型名，默认两个都跑 |
| `--levels` / `--ids` / `--limit` | 只跑部分等级、指定题号，或每级前 N 题 |
| `--workers` / `--timeout` | 并发数（默认 8）、单题超时秒数（默认 900） |
| `--thinking` | 思考强度（off / low / medium / high），默认使用模型自身的设置 |
| `--tag` | 结果目录名；同一个 tag 支持断点续跑，题面改动后会自动重跑该题 |
| `--cases` / `--readme` / `--data` | 题目文件、放进工作目录的 README、题目 `files` 所在的数据目录 |
| `--sandbox` | `bwrap`（默认）在 bubblewrap 沙箱中运行；`none` 不隔离 |

运行器的几个行为：
- **判分可重算**：每道题的事件日志、模型写的代码和产出文件都保存在 `hard/work/<tag>/<模型>/<题号>/`。`report.py` 和 `compare_runs.py` 会读取这些文件，按当前标准答案重新判分，所以修正标准答案后不必重跑模型。
- **接口报错自动重试**：运行中出现接口报错（额度不足、限流、5xx 等）的任务记为基础设施失败并自动重试，不算模型答错。
- **额度熔断**：连续 8 个任务因额度不足失败时，自动停止派发剩余任务。补充额度后，用同一个 `--tag` 重跑即可。

## 注意事项

- 运行器默认在 bubblewrap 沙箱中执行每道题，隔离方式如下：
  - 根文件系统只读；家目录换成空的临时目录，只读挂回 pi 程序和 `.venv`，因此 `~/.ssh`、其他项目和评测结果都不可见。
  - 只有当前题目的工作目录可写；每题有独立的 `/tmp`。
  - `~/.pi` 使用临时覆盖层：pi 可以写锁文件，但写入不会改动宿主机配置。
  - 网络保持开放，因为模型需要调用 API。pi 的模型配置（含 API key）在沙箱内仍可读。
- v1 四轮运行时还没有沙箱，越界写文件只靠提示词约束：Haiku 在 13%–20% 的任务里会把脚本写到 `/tmp`，DeepSeek 约 4%。经核查，这没有影响评测结果。v2 全部在沙箱中运行，Haiku 写 `/tmp` 的比例为 46.5%，DeepSeek 为 10.2%，这些写入都留在各自的沙箱里。
- 题目和判分由 Claude（Opus 5.5）设计。为减少偏向：标准答案取自真值；两个模型使用相同的提示词；每次修正题目，两个模型都同时重跑。但题目风格仍可能更接近 Claude 系模型的习惯。
- 评测过程中发现并修正过 15 处题目缺陷（v1 8 处、v2 7 处），例如 Python 的银行家舍入、题意歧义、题目引用了其他题的定义、变更日志的 lsn 与生效时间矛盾等。详见报告第 08 节。

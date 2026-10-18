#!/usr/bin/env python3
"""由 test_cases.json 生成无提示版题目 test_cases_nohint.json：题意与标准答案不变，删去所有脏数据提示"""

import json
import re
from pathlib import Path

HERE = Path(__file__).parent
S = "对每个 user_id 按时间排序，相邻两个事件间隔超过 30 分钟则开始一个新会话。"
EV = "只看北京时间 2024 年内的事件，"

REWRITE = {
    1: "orders.csv 文件共有多少行数据（不含表头）？",
    5: "order_items.csv 文件共有多少行数据（不含表头）？",
    6: "把 order_items.csv 文件中 quantity 列的数值逐行相加，总和是多少？",
    7: "customers.csv 文件共有多少行数据（不含表头）？",
    9: "orders.csv 文件中 channel 为 app 的行有多少？",
    11: "daily_kpi.csv 中 dau 的平均值是多少？保留2位小数。",
    13: "ab_test.csv 文件中 group 为 B 的行有多少？",
    14: "employees.csv 中 salary 的中位数是多少？保留1位小数。",
    16: "order_items.csv 文件中有多少个不同的 product_id？",
    18: "orders.csv 文件中 coupon_code 非空的行有多少？",
    19: "events.csv 文件共有多少行数据（不含表头）？",
    20: "events.csv 文件中 event_type 为 purchase 的行有多少？",
    32: "order_items 中有多少条明细的 quantity 违反字段定义？",
    33: "quantity 符合字段定义且 discount_rate 大于等于 0.2 的明细有多少条（不要求订单存在于 orders）？",
    36: "北京时间 2024 年 6 月的事件有多少条？",
    40: "A 组和 B 组中，converted = 1 且 revenue > 200 的用户一共有多少个？",
    43: "在有效订单中，按 product_id 汇总 quantity，销量最高的 product_id 是什么？",
    52: "不含“总裁办”，平均薪资最高的 dept 是哪个？",
    54: EV + "各 event_type 分别有多少条记录？键为 event_type。",
    58: "按 order_items 中的 order_id 分组，统计每个 order_id 中 quantity 符合字段定义的明细条数，求平均值（只统计至少有一条这样的明细的 order_id）。保留4位小数。",
    59: "A、B 两组的转化率（converted 的均值）分别是多少？键为 A、B，保留4位小数。",
    62: "用正则 ^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$ 校验 email，不合法的客户有多少人？",
    64: "姓（name 的第一个字）为“王”的客户有多少人？",
    65: "name 恰好为 3 个字的客户有多少人？",
    70: "customers.csv 文件中 city 列按原样（逐字符比较）共有多少种不同的字符串取值？",
    71: "客户一共分布在多少个不同的城市？",
    72: "有多少位客户的 city 字段（去掉首尾空格后）只由英文字母和撇号组成？",
    81: "有多少个订单的 order_time 是以 Z 结尾的 UTC 时间写法？",
    90: EV + "按北京时间的小时（0–23）统计事件数，事件最多的是几点？",
    91: EV + "最早一条事件的北京时间是什么？格式 YYYY-MM-DD HH:MM:SS（直接舍去毫秒）。",
    106: "dau 与 revenue 的 Spearman 秩相关系数是多少？保留4位小数。",
    107: "对 A、B 两组转化率做合并比例的双比例 z 检验，z 值（B − A）是多少？保留4位小数。",
    108: "对 A、B 两组转化率做合并比例的双比例 z 检验，双侧 p 值是多少？保留4位小数。",
    109: "只看 A、B 两组中 converted = 1 的用户，对 revenue 做 Welch t 检验（B 组减 A 组），t 值是多少？保留4位小数。",
    110: "只看 A、B 两组中 converted = 1 的用户，对 revenue 做 Welch t 检验，双侧 p 值是多少？保留4位小数。",
    111: "B 组转化率的 95% Wald 置信区间下限是多少（z = 1.959964）？保留4位小数。",
    114: "salary 的偏度是多少（使用 scipy.stats.skew 默认参数）？保留4位小数。",
    115: "salary 的峰度是多少（使用 scipy.stats.kurtosis 默认参数，即 Fisher 定义）？保留4位小数。",
    120: "只看 A、B 两组中 converted = 1 的用户，对 revenue 做 Mann-Whitney U 检验（scipy.stats.mannwhitneyu，B 组作为第一个参数，其余默认），U 统计量是多少？保留1位小数。",
    124: "按客户所在城市汇总北京时间 2024 年有效订单的人民币 GMV，最高的城市是哪个？",
    126: "按 supplier_id 汇总有效订单的 quantity，销量最高的 supplier_id 是哪个？",
    127: "有效订单的总毛利是多少？毛利 = Σ quantity × (unit_price × (1 − discount_rate) × 汇率 − cost)。保留2位小数。",
    130: "order_items 中有多少条明细的 order_id 不在 orders 表中？",
    131: "状态为 refunded 的订单中，按 product_id 汇总 quantity，最多的 product_id 是哪个？",
    133: "按客户所在城市统计工单数（没有客户的工单不计），工单最多的城市是哪个？",
    136: "有效订单的明细中，按 quantity 加权的平均 discount_rate 最高的 category 是哪个？",
    137: EV + "把 purchase 事件按 product_id 关联到 category，purchase 次数最多的 category 是哪个？",
    143: "有多少位客户的 birth_date 使用“YYYY年M月D日”的中文写法？",
    148: "检查价格异常：对属于 orders 表中订单、且 quantity 符合字段定义的明细，计算 |unit_price × 汇率 − list_price| ÷ list_price，大于 0.5 的明细有多少条？",
    150: "daily_kpi 中有多少行的 revenue 违反字段定义？",
    153: "用所在 dept 的薪资中位数填充缺失薪资后，全体员工薪资总和是多少？保留2位小数。",
    157: "ab_test 中同时出现在 A 组和 B 组的用户有多少个？",
    158: "events 中有多少条记录的 event_time 转换为北京时间后不在 2024 年内？",
    160: "生成有效订单汇总表 order_summary.csv，每个有效订单一行，列依次为 order_id,order_date,customer_id,items_qty,goods_amount_cny,shipping_fee_cny,gmv_cny。order_date 为北京时间日期 YYYY-MM-DD；items_qty 为该订单 quantity 之和（没有明细为 0）；三个金额列为换算成人民币后的值，保留2位小数；按 order_id 升序。",
    161: EV + S + "一共有多少个会话？",
    162: EV + S + "平均每个会话有多少个事件？保留4位小数。",
    163: EV + S + "会话时长（最后一个事件时间 − 第一个事件时间，单位秒，含毫秒）的中位数是多少？保留1位小数。",
    164: EV + S + "包含 purchase 事件的会话占全部会话的比例是多少？保留4位小数。",
    167: "对有效订单数 ≥ 2 的 customer_id，按下单时间排序，计算“第 2 单人民币 GMV ÷ 第 1 单人民币 GMV”（第 1 单 GMV 为 0 的客户跳过），求中位数。保留4位小数。",
    168: "生成 city_top_customer.csv：对每个城市，找出该城市有效订单人民币 GMV 合计最高的客户（只看 customers 表中的客户）。列依次为 city,customer_id,gmv_cny（保留2位小数），每个城市一行，按 gmv_cny 降序。",
    173: EV + S + "按会话计算漏斗转化率：含 add_to_cart 的会话数 ÷ 含 view 的会话数、含 checkout ÷ 含 add_to_cart、含 purchase ÷ 含 checkout，以长度 3 的数组给出，保留4位小数。",
    174: "在有效订单中（同一订单内同一商品只算一次），同时出现次数最多的商品对是哪一对？用 \"小的product_id,大的product_id\" 格式给出（如 \"P0001,P0002\"）。",
    178: "在每个 dept 内按薪资降序做 dense rank，取排名第 2 的薪资值，把所有部门的这个值加起来是多少（没有第 2 名的部门跳过）？保留2位小数。",
    179: "计算 2024 年每月 revenue 占全年 revenue 的比例（缺失日期不补），以长度 12 的数组给出（1 月到 12 月），保留4位小数。",
    184: "用最小二乘法拟合 revenue = a × dau + b（缺失日期不补），斜率 a 是多少？保留4位小数。",
    185: "用最小二乘法拟合 revenue = a × dau + b（缺失日期不补），R² 是多少？保留4位小数。",
    188: "关联规则：在有效订单中（同一订单内同一商品只算一次），对共同出现订单数 ≥ 20 的商品对计算 lift = support(A,B) ÷ (support(A) × support(B))，support 为包含该商品（对）的订单数 ÷ 订单总数（订单总数 = 至少含一件商品的有效订单数）。lift 最高的商品对是哪一对？用 \"小的product_id,大的product_id\" 格式给出。",
    189: EV + "在有过 view 事件的用户中，有过 purchase 事件的用户占比是多少？保留4位小数。",
    194: "样本比例失衡（SRM）检查：用卡方拟合优度检验 A、B 两组用户数是否符合 1:1，p 值是多少？保留4位小数。",
    195: "样本量估算：以 A 组的转化率为 p1，p2 = p1 + 0.01，α = 0.05（双侧）、检验功效 0.8，每组所需样本量 n = (z_{0.975} + z_{0.8})² × (p1(1−p1) + p2(1−p2)) ÷ (p2 − p1)²，向上取整。n 是多少？",
    197: "按 (category, channel) 组合汇总有效订单的毛利（毛利 = Σ quantity × (unit_price × (1 − discount_rate) × 汇率 − cost)），毛利最高的组合是哪个？用 \"category|channel\" 格式给出。",
}
RAW = "（按文件原样逐行统计，不应用 README 中的分析规范）"
for _i in (1, 5, 6, 7, 9, 13, 16, 18, 19, 20):
    REWRITE[_i] = REWRITE[_i].rstrip("？") + RAW + "？"
# L8 中明确要求做清洗/审计的题，题目本身就是任务，原样保留
KEEP = {8, 141, 142, 144, 145, 146, 156}
HINT = re.compile(r"去重|剔除|污染|归一化|统一口径|忽略缺失|首尾空格|有效行|无效行|revenue < 0|原始文件|不去重|异常记录|录入错误|不做任何处理")
# 会话题仍保留“只看北京时间 2024 年内的事件”这一业务范围限定，它不是脏数据提示
SCOPE_OK = re.compile(r"^只看北京时间 2024 年内的事件，")

cases = json.load(open(HERE / "test_cases.json", encoding="utf-8"))
for c in cases:
    if c["id"] in REWRITE:
        c["question"] = REWRITE[c["id"]]
    q = SCOPE_OK.sub("", c["question"]).replace("去掉首尾空格后", "")
    if c["id"] not in KEEP and HINT.search(q):
        raise SystemExit(f"#{c['id']} 仍含提示：{c['question']}")
unused = set(REWRITE) - {c["id"] for c in cases}
assert not unused, unused
json.dump(cases, open(HERE / "test_cases_nohint.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"改写 {len(REWRITE)} 题，原样保留的 L8 显式清洗题 {len(KEEP)} 道，共 {len(cases)} 题 → test_cases_nohint.json")

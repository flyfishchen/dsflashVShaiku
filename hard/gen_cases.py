#!/usr/bin/env python3
"""从干净真值计算 200 道工具型数据处理题的标准答案（10 级 × 20 题）"""

import json
import math
import pickle
import re
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).parent
DATA = HERE / "data"
EXP = HERE / "expected"
EXP.mkdir(exist_ok=True)
T = pickle.load(open(HERE / "truth" / "truth.pkl", "rb"))


def rnd(x, k=0):
    v = float(Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-k), rounding=ROUND_HALF_UP))
    return int(v) if k == 0 else v


def top1(s, smallest=False):
    s = s.sort_values(ascending=smallest)
    if (s == s.iloc[0]).sum() > 1:
        raise ValueError(f"并列：\n{s[s == s.iloc[0]]}")
    k = s.index[0]
    return k.item() if hasattr(k, "item") else k


def raw(name):
    return pd.read_csv(DATA / name, dtype=str, keep_default_na=False)


cases = []


def Q(level, cat, files, question, expected, atype="number", csv=None):
    c = {"id": len(cases) + 1, "level": level, "category": cat, "files": files,
         "question": question, "answer_type": atype}
    if atype == "csv":
        df, keys, num_tol = csv
        out = expected
        df.to_csv(EXP / f"{c['id']:03d}_{out}", index=False)
        c.update(expected=out, key_cols=keys, num_tol=num_tol)
    else:
        if isinstance(expected, (np.integer,)):
            expected = int(expected)
        if isinstance(expected, (np.floating,)):
            expected = float(expected)
        c["expected"] = expected
    cases.append(c)


def dround(d, k):
    return {str(a): rnd(b, k) for a, b in d.items()}


# ======================================================== 派生真值
cust, prod, orders, items, fx = (T[k].copy() for k in ["cust", "prod", "orders", "items", "fx"])
ev, kpi, legacy, ab, emp, tk = (T[k].copy() for k in ["events", "kpi", "legacy", "ab", "emp", "tickets"])

REF = pd.Timestamp("2025-01-01")
bd = cust.birth_date
cust["age"] = 2025 - bd.dt.year - ((bd.dt.month > 1) | (bd.dt.day > 1)).astype(int)

orders["date"] = orders.ts.dt.normalize()
orders["month"] = orders.ts.dt.strftime("%Y-%m")
valid = items[items.quantity > 0].copy()
valid["amt"] = valid.quantity * valid.unit_price * (1 - valid.discount_rate)
orders["goods"] = orders.order_id.map(valid.groupby("order_id").amt.sum()).fillna(0.0)
orders["qty"] = orders.order_id.map(valid.groupby("order_id").quantity.sum()).fillna(0).astype(int)
orders["gmv"] = orders.goods + orders.shipping_fee
orders["gmv_cny"] = orders.gmv * orders.rate
orders["goods_cny"] = orders.goods * orders.rate
orders["ship_cny"] = orders.shipping_fee * orders.rate
paid = orders[orders.status == "paid"].copy()
paid_known = paid[paid.customer_id.isin(cust.customer_id)]

vl = valid.merge(orders[["order_id", "status", "rate", "customer_id", "channel", "ts", "month", "currency"]], on="order_id")
vl["amt_cny"] = vl.amt * vl.rate
vl = vl.merge(prod[["product_id", "category", "cost", "supplier_id", "list_price"]], on="product_id")
vl["profit"] = vl.quantity * (vl.unit_price * (1 - vl.discount_rate) * vl.rate - vl.cost)
pvl = vl[vl.status == "paid"]

cny_gmv = paid[paid.currency == "CNY"].gmv

ab_a, ab_b = ab[ab.group == "A"], ab[ab.group == "B"]
emp_tree = emp[~emp.orphan]
children = emp_tree.dropna(subset=["manager_id"]).groupby("manager_id").emp_id.apply(list).to_dict()


def descendants(e):
    out, stack = 0, list(children.get(e, []))
    while stack:
        x = stack.pop()
        out += 1
        stack.extend(children.get(x, []))
    return out


depth = {"E001": 1}
queue = ["E001"]
while queue:
    x = queue.pop()
    for ch in children.get(x, []):
        depth[ch] = depth[x] + 1
        queue.append(ch)

tk["created_bj"] = tk.created
ORDER_RE = r"O\d{6}"

F_O, F_I, F_C, F_P = "orders.csv", "order_items.csv", "customers.csv", "products.csv"
F_FX, F_E, F_K, F_L = "fx_rates.csv", "events.csv", "daily_kpi.csv", "legacy_sales.csv"
F_AB, F_EMP, F_T = "ab_test.csv", "employees.csv", "support_tickets.csv"

ro, rc, ri, rev, rab = raw(F_O), raw(F_C), raw(F_I), raw(F_E), raw(F_AB)

# ======================================================== L1 基础读取
L, C = 1, "基础读取"
Q(L, C, [F_O], "orders.csv 原始文件共有多少行数据（不含表头，不去重）？", len(ro), "integer")
Q(L, C, [F_P], "products.csv 中有多少个不同的 category？", prod.category.nunique(), "integer")
Q(L, C, [F_P], "products.csv 中 cost 列的总和是多少？保留2位小数。", rnd(prod.cost.sum(), 2))
Q(L, C, [F_P], "products.csv 中 cost 最高的商品的 product_id 是什么？", top1(prod.set_index("product_id").cost), "string")
Q(L, C, [F_I], "order_items.csv 原始文件共有多少行数据（不含表头，不去重）？", len(ri), "integer")
Q(L, C, [F_I], "order_items.csv 原始文件中 quantity 列的总和是多少（不去重、不剔除任何行）？", int(ri.quantity.astype(int).sum()), "integer")
Q(L, C, [F_C], "customers.csv 原始文件共有多少行数据（不含表头，不去重）？", len(rc), "integer")
Q(L, C, [F_C], "customers.csv 整行去重后还剩多少行？", len(rc.drop_duplicates()), "integer")
Q(L, C, [F_O], "orders.csv 原始文件中 channel 为 app 的行有多少（不去重）？", int((ro.channel == "app").sum()), "integer")
Q(L, C, [F_FX], "fx_rates.csv 中 USD 的 rate_to_cny 最大值是多少？保留4位小数。", rnd(fx[fx.currency == "USD"].rate.max(), 4))
Q(L, C, [F_K], "daily_kpi.csv 中 dau 的平均值是多少（不剔除任何行）？保留2位小数。", rnd(kpi.dau.mean(), 2))
Q(L, C, [F_K], "daily_kpi.csv 共有多少行数据（不含表头）？", len(kpi), "integer")
Q(L, C, [F_AB], "ab_test.csv 原始文件中 group 为 B 的行有多少（不剔除污染样本）？", int((rab.group == "B").sum()), "integer")
Q(L, C, [F_EMP], "employees.csv 中 salary 的中位数是多少（忽略缺失值）？保留1位小数。", rnd(emp.salary.median(), 1))
Q(L, C, [F_EMP], "employees.csv 中有多少个不同的 dept？", emp.dept.nunique(), "integer")
Q(L, C, [F_I], "order_items.csv 原始文件中有多少个不同的 product_id？", ri.product_id.nunique(), "integer")
Q(L, C, [F_P], "products.csv 中有多少个不同的 supplier_id？", prod.supplier_id.nunique(), "integer")
Q(L, C, [F_O], "orders.csv 原始文件中 coupon_code 非空的行有多少（不去重）？", int((ro.coupon_code != "").sum()), "integer")
Q(L, C, [F_E], "events.csv 原始文件共有多少行数据（不含表头）？", len(rev), "integer")
Q(L, C, [F_E], "events.csv 原始文件中 event_type 为 purchase 的记录有多少条（不剔除异常记录）？", int((rev.event_type == "purchase").sum()), "integer")

# ======================================================== L2 过滤与类型解析
L, C = 2, "过滤与类型解析"
Q(L, C, [F_P], "list_price 大于 1000 元的商品有多少个？", int((prod.list_price > 1000).sum()), "integer")
Q(L, C, [F_P], "所有商品 list_price 的平均值是多少？保留2位小数。", rnd(prod.list_price.mean(), 2))
Q(L, C, [F_P], "毛利率 (list_price − cost) / list_price 低于 30% 的商品有多少个？", int(((prod.list_price - prod.cost) / prod.list_price < .3).sum()), "integer")
Q(L, C, [F_O], "有效订单（paid）有多少个？", len(paid), "integer")
Q(L, C, [F_O], "状态为 refunded 的订单有多少个？", int((orders.status == "refunded").sum()), "integer")
Q(L, C, [F_O], "shipping_fee 为 0 的有效订单有多少个？", int((paid.shipping_fee == 0).sum()), "integer")
Q(L, C, [F_C], "没有等级（tier 为空）的客户有多少人？", int(cust.tier.isna().sum()), "integer")
Q(L, C, [F_C], "女性客户有多少人？", int((cust.gender == "F").sum()), "integer")
Q(L, C, [F_C], "城市为上海的客户有多少人？", int((cust.city == "上海").sum()), "integer")
Q(L, C, [F_C], "年龄大于等于 40 岁的客户有多少人？", int((cust.age >= 40).sum()), "integer")
Q(L, C, [F_C], "signup_date 在 2024 年内的客户有多少人？", int((cust.signup_date.dt.year == 2024).sum()), "integer")
Q(L, C, [F_I], "去重后，order_items 中的无效行（quantity ≤ 0）有多少行？", int((items.quantity <= 0).sum()), "integer")
Q(L, C, [F_I], "去重后，order_items 的有效行中 discount_rate 大于等于 0.2 的有多少行（不要求订单存在于 orders）？", int(((items.quantity > 0) & (items.discount_rate >= .2)).sum()), "integer")
Q(L, C, [F_P], "category 为 手机数码 且 list_price 低于 3000 元的商品有多少个？", int(((prod.category == "手机数码") & (prod.list_price < 3000)).sum()), "integer")
Q(L, C, [F_O], "币种为 USD 的订单有多少个（任意状态）？", int((orders.currency == "USD").sum()), "integer")
Q(L, C, [F_E], "剔除异常记录后，北京时间 2024 年 6 月的事件有多少条？", int((ev.ts.dt.strftime("%Y-%m") == "2024-06").sum()), "integer")
Q(L, C, [F_L], "legacy_sales.csv 中所有有效销售额的总和是多少？保留2位小数。", rnd(legacy.sales.sum(), 2))
Q(L, C, [F_L], "legacy_sales.csv 中销售额大于 1,000,000 的记录有多少条？", int((legacy.sales > 1e6).sum()), "integer")
Q(L, C, [F_EMP], "2020-01-01 之前入职的员工有多少人？", int((emp.hire_date < "2020-01-01").sum()), "integer")
Q(L, C, [F_AB], "剔除污染样本后，converted = 1 且 revenue > 200 的用户有多少个？", int(((ab.converted == 1) & (ab.revenue > 200)).sum()), "integer")

# ======================================================== L3 分组聚合
L, C = 3, "分组聚合"
Q(L, C, [F_O], "有效订单数最多的 channel 是哪个？", top1(paid.channel.value_counts()), "string")
Q(L, C, [F_P], "每个 category 各有多少个商品？键为 category。", {k: int(v) for k, v in prod.category.value_counts().items()}, "dict")
Q(L, C, [F_O, F_I], "在有效订单中，按 product_id 汇总有效行的 quantity，销量最高的 product_id 是什么？", top1(pvl.groupby("product_id").quantity.sum()), "string")
Q(L, C, [F_O, F_I], "币种为 CNY 的有效订单的 GMV 总和是多少（原币种即人民币）？保留2位小数。", rnd(cny_gmv.sum(), 2))
cc = cust.city.value_counts().reset_index()
cc.columns = ["city", "n"]
Q(L, C, [F_C], "客户数最多的前 3 个城市是哪些？按客户数降序，并列时按城市名升序，以数组给出。",
  cc.sort_values(["n", "city"], ascending=[False, True]).city.head(3).tolist(), "list")
Q(L, C, [F_C], "按 tier（金/银/铜，不含空值）统计客户的平均年龄。键为 tier，保留2位小数。", dround(cust.groupby("tier").age.mean(), 2), "dict")
Q(L, C, [F_O], "按北京时间月份（YYYY-MM）统计有效订单数，订单数最多的月份是哪个？", top1(paid.month.value_counts()), "string")
Q(L, C, [F_O], "北京时间 2024 年的有效订单有多少个？", int((paid.ts.dt.year == 2024).sum()), "integer")
Q(L, C, [F_O], "有效订单数大于等于 10 的 customer_id 有多少个？", int((paid.customer_id.value_counts() >= 10).sum()), "integer")
Q(L, C, [F_O], "只看币种为 CNY 的有效订单，各 channel 的平均 shipping_fee 是多少？键为 channel，保留2位小数。",
  dround(paid[paid.currency == "CNY"].groupby("channel").shipping_fee.mean(), 2), "dict")
Q(L, C, [F_O], "有效订单中，各 coupon_code（不含空值）分别有多少个订单？键为 coupon_code。",
  {k: int(v) for k, v in paid[paid.coupon_code != ""].coupon_code.value_counts().items()}, "dict")
Q(L, C, [F_EMP], "不含“总裁办”，平均薪资最高的 dept 是哪个（忽略缺失薪资）？", top1(emp[emp.dept != "总裁办"].groupby("dept").salary.mean()), "string")
Q(L, C, [F_EMP], "每个 dept 各有多少名员工？键为 dept。", {k: int(v) for k, v in emp.dept.value_counts().items()}, "dict")
Q(L, C, [F_E], "剔除异常记录后，各 event_type 分别有多少条记录？键为 event_type。", {k: int(v) for k, v in ev.event_type.value_counts().items()}, "dict")
l24 = legacy[legacy.month.str.startswith("2024")]
Q(L, C, [F_L], "2024 年（月份 2024-01 至 2024-12）有效销售额合计最高的门店是哪个？", top1(l24.groupby("store").sales.sum()), "string")
Q(L, C, [F_K], "按星期几统计 dau 的平均值，平均 dau 最高的是星期几（周一=1 … 周日=7）？", top1(kpi.groupby(kpi.date.dt.dayofweek + 1).dau.mean()), "integer")
Q(L, C, [F_P], "各 category 的平均 list_price 是多少？键为 category，保留2位小数。", dround(prod.groupby("category").list_price.mean(), 2), "dict")
Q(L, C, [F_I], "去重后按 order_items 中的 order_id 分组，统计每个 order_id 的有效行数，求平均值（只统计至少有一条有效行的 order_id）。保留4位小数。",
  rnd(valid.groupby("order_id").size().mean(), 4))
Q(L, C, [F_AB], "剔除污染样本后，A、B 两组的转化率（converted 的均值）分别是多少？键为 A、B，保留4位小数。", dround(ab.groupby("group").converted.mean(), 4), "dict")
Q(L, C, [F_O], "有效订单按 currency 统计订单数。键为 currency。", {k: int(v) for k, v in paid.currency.value_counts().items()}, "dict")

# ======================================================== L4 文本与正则
L, C = 4, "文本与正则"
EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
email_ok = cust.email.str.strip().str.match(EMAIL_RE)
Q(L, C, [F_C], "手机号有效（恰好 11 位数字且以 1 开头）的客户有多少人？", int(cust.phone.str.fullmatch(r"1\d{10}").sum()), "integer")
Q(L, C, [F_C], "用正则 ^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$ 校验 email（先去除首尾空格），不合法的客户有多少人？", int((~email_ok).sum()), "integer")
Q(L, C, [F_C], "在 email 合法（规则：正则 ^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$）的客户中，把 @ 后的域名转为小写，出现次数最多的域名是哪个？",
  top1(cust[email_ok].email.str.strip().str.split("@").str[1].str.lower().value_counts()), "string")
Q(L, C, [F_C], "姓（name 去除首尾空格后的第一个字）为“王”的客户有多少人？", int((cust.name.str[0] == "王").sum()), "integer")
Q(L, C, [F_C], "name 去除首尾空格后恰好为 3 个字的客户有多少人？", int((cust.name.str.len() == 3).sum()), "integer")
words = prod.product_name.str.split(" ")
Q(L, C, [F_P], "product_name 按空格分词后，最后一个词为 Pro 的商品有多少个？", int((words.str[-1] == "Pro").sum()), "integer")
Q(L, C, [F_P], "product_name 按空格分词后第一个词为品牌名，一共有多少个不同的品牌？", words.str[0].nunique(), "integer")
Q(L, C, [F_P], "按品牌（product_name 的第一个词）计算平均 list_price，平均价格最高的品牌是哪个？", top1(prod.groupby(words.str[0]).list_price.mean()), "string")
dig = paid.coupon_code.str.extract(r"(\d+)")[0].dropna().astype(int)
Q(L, C, [F_O], "有效订单中 coupon_code 含数字的（如 VIP20 中的 20），这些数字的平均值是多少？保留2位小数。", rnd(dig.mean(), 2))
Q(L, C, [F_C], "customers.csv 原始文件中（不去重、不做任何处理，区分大小写和空格）city 字段共有多少种不同的取值？", rc.city.nunique(), "integer")
Q(L, C, [F_C], "按统一口径把 city 归一化后，共有多少个不同的城市？", cust.city.nunique(), "integer")
rcd = rc.drop_duplicates()
Q(L, C, [F_C], "去重后，city 字段去除首尾空格后仅由英文字母和撇号组成的客户有多少人？", int(rcd.city.str.strip().str.fullmatch(r"[A-Za-z']+").sum()), "integer")
txt = tk.text
Q(L, C, [F_T], "text 中包含“退款”二字的工单有多少个？", int(txt.str.contains("退款").sum()), "integer")
refs = txt.str.findall(ORDER_RE)
Q(L, C, [F_T], "text 中提到的订单号（字母 O 后跟 6 位数字）一共有多少个不同的订单号？", len(set(x for r in refs for x in r)), "integer")
st = orders.set_index("order_id").status
Q(L, C, [F_T, F_O], "text 中至少提到一个状态为 refunded 的订单的工单有多少个？", int(sum(any(st.get(x) == "refunded" for x in r) for r in refs)), "integer")
Q(L, C, [F_T], "text 中带有 [P1] 标签的工单有多少个？", int(txt.str.contains("[P1]", regex=False).sum()), "integer")
Q(L, C, [F_T], "text 中同时包含“物流”和“延迟”的工单有多少个？", int((txt.str.contains("物流") & txt.str.contains("延迟")).sum()), "integer")
Q(L, C, [F_T], "text 的平均字符数是多少？保留2位小数。", rnd(txt.str.len().mean(), 2))
Q(L, C, [F_T], "text 中出现手机号（1 开头的连续 11 位数字，前后都不是数字）的工单有多少个？", int(txt.str.contains(r"(?<!\d)1\d{10}(?!\d)").sum()), "integer")
amts = [float(a or b) for t in txt for a, b in re.findall(r"¥(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)元", t)]
Q(L, C, [F_T], "text 中出现的金额（形如 ¥123.45 或 123.45元）的总和是多少？保留2位小数。", rnd(sum(amts), 2))

# ======================================================== L5 日期与时区
L, C = 5, "日期与时区"
Q(L, C, [F_O], "去重后的订单中，order_time 为 UTC 写法（以 Z 结尾）的有多少个？", int((orders.time_fmt == "utc").sum()), "integer")
Q(L, C, [F_O], "北京时间日期为 2024-02-29 的有效订单有多少个？", int((paid.date == "2024-02-29").sum()), "integer")
Q(L, C, [F_O], "北京时间 00:00:00 至 05:59:59 下单的有效订单有多少个？", int((paid.ts.dt.hour < 6).sum()), "integer")
Q(L, C, [F_O], "有效订单中，北京时间周六或周日下单的占比是多少？保留4位小数。", rnd((paid.ts.dt.dayofweek >= 5).mean(), 4))
Q(L, C, [F_O], "北京时间 2024 年有效订单数与 2023 年有效订单数之比（2024 ÷ 2023）是多少？保留4位小数。",
  rnd((paid.ts.dt.year == 2024).sum() / (paid.ts.dt.year == 2023).sum(), 4))
first_paid = paid_known.groupby("customer_id").date.min()
su = cust.set_index("customer_id").signup_date
Q(L, C, [F_O, F_C], "对 customers 表中有有效订单的客户，计算“首个有效订单的北京时间日期 − signup_date”的天数，求中位数。保留1位小数。",
  rnd((first_paid - su.loc[first_paid.index]).dt.days.median(), 1))
gaps = paid.sort_values("ts").groupby("customer_id").ts.diff().dropna().dt.total_seconds() / 86400
Q(L, C, [F_O], "对有效订单数 ≥ 2 的 customer_id，按下单时间排序后计算相邻两单的间隔天数（= 时间差秒数 / 86400），汇总所有间隔求平均值。保留2位小数。", rnd(gaps.mean(), 2))
iso = paid.ts.dt.isocalendar()
Q(L, C, [F_O], "按 ISO 周统计有效订单数，ISO 年为 2024 的各周中，订单数最多的是第几周？", top1(iso[iso.year == 2024].groupby("week").size()), "integer")
Q(L, C, [F_O], "所有“当月最后一天”（北京时间）下单的有效订单一共有多少个？", int(paid.ts.dt.is_month_end.sum()), "integer")
Q(L, C, [F_E], "剔除异常记录后，按北京时间的小时（0–23）统计事件数，事件最多的是几点？", top1(ev.ts.dt.hour.value_counts()), "integer")
Q(L, C, [F_E], "剔除异常记录后，最早一条事件的北京时间是什么？格式 YYYY-MM-DD HH:MM:SS（直接舍去毫秒）。", ev.ts.min().strftime("%Y-%m-%d %H:%M:%S"), "string")
usd = fx[fx.currency == "USD"].set_index("date").rate
Q(L, C, [F_FX], "2024 年 USD 的 rate_to_cny 高于 7.2 的记录有多少条？", int(((usd.index.year == 2024) & (usd > 7.2)).sum()), "integer")
mar = pd.date_range("2024-03-01", "2024-03-31")
Q(L, C, [F_FX], "把 USD 汇率补齐到 2024-03-01 至 2024-03-31 的每一天（当天没有汇率就用之前最近一个有汇率的日期的值），这 31 天的平均汇率是多少？保留4位小数。",
  rnd(np.mean([usd[usd.index <= d].iloc[-1] for d in mar]), 4))
all_days = pd.date_range("2023-01-01", "2024-12-31")
missing = sorted(all_days.difference(kpi.date).strftime("%Y-%m-%d"))
Q(L, C, [F_K], "2023-01-01 至 2024-12-31 之间，daily_kpi 缺失了多少天？", len(missing), "integer")
Q(L, C, [F_K], "列出 2023-01-01 至 2024-12-31 之间 daily_kpi 缺失的所有日期（YYYY-MM-DD，升序）。", missing, "list")
Q(L, C, [F_EMP], "截至 2025-01-01，员工平均司龄是多少年（司龄 = 天数 / 365.25）？保留2位小数。", rnd(((REF - emp.hire_date).dt.days / 365.25).mean(), 2))
Q(L, C, [F_EMP], "哪个月份（1–12）入职的员工最多？", top1(emp.hire_date.dt.month.value_counts()), "integer")
Q(L, C, [F_T], "按北京时间，2024 年第四季度（10–12 月）创建的工单有多少个？",
  int(((tk.created_bj.dt.year == 2024) & (tk.created_bj.dt.month >= 10)).sum()), "integer")
ots = orders.set_index("order_id").ts
hrs = [(c - ots[r[0]]).total_seconds() / 3600 for c, r in zip(tk.created_bj, refs) if r]
Q(L, C, [F_T, F_O], "对提到订单号的工单，取 text 中第一个出现的订单号，计算“工单创建时间 − 该订单下单时间”的小时数，求中位数。保留2位小数。", rnd(np.median(hrs), 2))
mc = paid.groupby("month").size()
mom = (mc / mc.shift(1) - 1)
Q(L, C, [F_O], "按北京时间月份统计有效订单数，2024 年各月中环比增长率（相对上一个月，1 月对比 2023-12）最高的是哪个月？格式 YYYY-MM。",
  top1(mom[mom.index.str.startswith("2024")]), "string")

# ======================================================== L6 统计推断
L, C = 6, "统计推断"
Q(L, C, [F_O, F_I], "币种为 CNY 的有效订单 GMV 的中位数是多少？保留2位小数。", rnd(cny_gmv.median(), 2))
Q(L, C, [F_O, F_I], "币种为 CNY 的有效订单 GMV 的 90% 分位数是多少？保留2位小数。", rnd(cny_gmv.quantile(.9), 2))
Q(L, C, [F_O, F_I], "币种为 CNY 的有效订单 GMV 的样本标准差是多少？保留2位小数。", rnd(cny_gmv.std(), 2))
Q(L, C, [F_P], "list_price 与 cost 的皮尔逊相关系数是多少？保留4位小数。", rnd(prod.list_price.corr(prod.cost), 4))
q1, q3 = cny_gmv.quantile(.25), cny_gmv.quantile(.75)
Q(L, C, [F_O, F_I], "按 1.5×IQR 规则，币种为 CNY 的有效订单 GMV 中有多少个异常值（小于 Q1−1.5IQR 或大于 Q3+1.5IQR）？",
  int(((cny_gmv < q1 - 1.5 * (q3 - q1)) | (cny_gmv > q3 + 1.5 * (q3 - q1))).sum()), "integer")
kp = kpi[kpi.revenue >= 0]
Q(L, C, [F_K], "剔除 revenue < 0 的行后，dau 与 revenue 的 Spearman 秩相关系数是多少？保留4位小数。", rnd(stats.spearmanr(kp.dau, kp.revenue).statistic, 4))
na, nb, xa, xb = len(ab_a), len(ab_b), ab_a.converted.sum(), ab_b.converted.sum()
pp = (xa + xb) / (na + nb)
z = (xb / nb - xa / na) / math.sqrt(pp * (1 - pp) * (1 / na + 1 / nb))
Q(L, C, [F_AB], "剔除污染样本后，对 A、B 两组转化率做合并比例的双比例 z 检验，z 值（B − A）是多少？保留4位小数。", rnd(z, 4))
Q(L, C, [F_AB], "剔除污染样本后，对 A、B 两组转化率做合并比例的双比例 z 检验，双侧 p 值是多少？保留4位小数。", rnd(2 * stats.norm.sf(abs(z)), 4))
ra, rb = ab_a[ab_a.converted == 1].revenue, ab_b[ab_b.converted == 1].revenue
wt = stats.ttest_ind(rb, ra, equal_var=False)
Q(L, C, [F_AB], "剔除污染样本后，只看 converted = 1 的用户，对 revenue 做 Welch t 检验（B 组减 A 组），t 值是多少？保留4位小数。", rnd(wt.statistic, 4))
Q(L, C, [F_AB], "剔除污染样本后，只看 converted = 1 的用户，对 revenue 做 Welch t 检验，双侧 p 值是多少？保留4位小数。", rnd(wt.pvalue, 4))
pb = xb / nb
Q(L, C, [F_AB], "剔除污染样本后，B 组转化率的 95% Wald 置信区间下限是多少（z = 1.959964）？保留4位小数。", rnd(pb - 1.959964 * math.sqrt(pb * (1 - pb) / nb), 4))
ct = pd.crosstab(paid.channel, paid.currency)
Q(L, C, [F_O], "对有效订单的 channel × currency 列联表做卡方独立性检验，卡方统计量是多少？保留4位小数。", rnd(stats.chi2_contingency(ct).statistic, 4))
pc = cust.customer_id.map(paid.customer_id.value_counts()).fillna(0)
Q(L, C, [F_C, F_O], "对 customers 表中每个客户（没有有效订单的记为 0 单），年龄与有效订单数的皮尔逊相关系数是多少？保留4位小数。", rnd(cust.age.corr(pc), 4))
sal = emp.salary.dropna()
Q(L, C, [F_EMP], "salary 的偏度是多少（忽略缺失值，使用 scipy.stats.skew 默认参数）？保留4位小数。", rnd(stats.skew(sal), 4))
Q(L, C, [F_EMP], "salary 的峰度是多少（忽略缺失值，使用 scipy.stats.kurtosis 默认参数，即 Fisher 定义）？保留4位小数。", rnd(stats.kurtosis(sal), 4))
Q(L, C, [F_K], "dau 的变异系数（样本标准差 ÷ 均值）是多少？保留4位小数。", rnd(kpi.dau.std() / kpi.dau.mean(), 4))
g = paid[paid.currency == "CNY"].groupby("channel").gmv
Q(L, C, [F_O, F_I], "对币种为 CNY 的有效订单 GMV，按 channel 分组做单因素方差分析，F 值是多少？保留4位小数。", rnd(stats.f_oneway(*[x for _, x in g]).statistic, 4))
lz = legacy.dropna(subset=["sales"]).copy()
lz["z"] = lz.groupby("store").sales.transform(lambda s: (s - s.mean()) / s.std())
Q(L, C, [F_L], "在每个门店内部对有效销售额做 Z-score 标准化（样本标准差），|z| > 2.5 的记录有多少条？", int((lz.z.abs() > 2.5).sum()), "integer")
Q(L, C, [F_P], "计算每个 category 的 list_price 中位数，这些中位数中的最大值是多少？保留2位小数。", rnd(prod.groupby("category").list_price.median().max(), 2))
Q(L, C, [F_AB], "剔除污染样本后，只看 converted = 1 的用户，对 revenue 做 Mann-Whitney U 检验（scipy.stats.mannwhitneyu，B 组作为第一个参数，其余默认），U 统计量是多少？保留1位小数。",
  rnd(stats.mannwhitneyu(rb, ra).statistic, 1))

# ======================================================== L7 多表联结
L, C = 7, "多表联结"
Q(L, C, [F_O, F_I, F_FX], "北京时间 2024 年有效订单的 GMV 合计（换算为人民币）是多少？保留2位小数。", rnd(paid[paid.ts.dt.year == 2024].gmv_cny.sum(), 2))
Q(L, C, [F_O, F_I, F_P, F_FX], "按 category 汇总有效订单的商品金额（行金额换算为人民币，不含运费），金额最高的 category 是哪个？", top1(pvl.groupby("category").amt_cny.sum()), "string")
Q(L, C, [F_C, F_O], "customers 表中从未有过有效订单的客户有多少人？", int((~cust.customer_id.isin(paid.customer_id)).sum()), "integer")
pk = paid_known.merge(cust[["customer_id", "city", "tier"]], on="customer_id")
Q(L, C, [F_C, F_O, F_I, F_FX], "按客户城市（归一化后）汇总北京时间 2024 年有效订单的人民币 GMV，最高的城市是哪个？", top1(pk[pk.ts.dt.year == 2024].groupby("city").gmv_cny.sum()), "string")
gold = pk[pk.tier == "金"]
Q(L, C, [F_C, F_O, F_I, F_FX], "金级客户的有效订单平均客单价（人民币 GMV 合计 ÷ 订单数）是多少？保留2位小数。", rnd(gold.gmv_cny.sum() / len(gold), 2))
Q(L, C, [F_O, F_I, F_P], "按 supplier_id 汇总有效订单中有效行的 quantity，销量最高的 supplier_id 是哪个？", top1(pvl.groupby("supplier_id").quantity.sum()), "string")
Q(L, C, [F_O, F_I, F_P, F_FX], "有效订单的总毛利是多少？毛利 = Σ quantity × (unit_price × (1 − discount_rate) × 汇率 − cost)，只计有效行。保留2位小数。", rnd(pvl.profit.sum(), 2))
oc = orders.merge(cust[["customer_id", "signup_date"]], on="customer_id")
Q(L, C, [F_O, F_C], "下单时间的北京日期早于客户 signup_date 的订单有多少个（任意状态，只看 customer_id 在 customers 表中的订单）？", int((oc.date < oc.signup_date).sum()), "integer")
Q(L, C, [F_O, F_C], "customer_id 不在 customers 表中的订单有多少个（任意状态）？", int((~orders.customer_id.isin(cust.customer_id)).sum()), "integer")
Q(L, C, [F_I, F_O], "去重后，order_items 中 order_id 不在 orders 表中的行有多少？", int((~items.order_id.isin(orders.order_id)).sum()), "integer")
Q(L, C, [F_O, F_I], "状态为 refunded 的订单中，按 product_id 汇总有效行的 quantity，最多的 product_id 是哪个？", top1(vl[vl.status == "refunded"].groupby("product_id").quantity.sum()), "string")
cg = paid.groupby("customer_id").gmv_cny.sum().sort_values(ascending=False)
k10 = math.ceil(len(cg) * .1)
Q(L, C, [F_O, F_I, F_FX], "按 customer_id 汇总有效订单的人民币 GMV，取 GMV 最高的前 10% 客户（个数 = ceil(有有效订单的 customer_id 数 × 0.1)），他们的 GMV 占全部有效订单 GMV 的比例是多少？保留4位小数。",
  rnd(cg.head(k10).sum() / cg.sum(), 4))
tkc = tk.dropna(subset=["customer_id"]).merge(cust[["customer_id", "city"]], on="customer_id")
Q(L, C, [F_T, F_C], "按客户城市（归一化后）统计工单数（忽略 customer_id 为空的工单），工单最多的城市是哪个？", top1(tkc.city.value_counts()), "string")
has_tk = cust.customer_id.isin(tk.customer_id.dropna())
Q(L, C, [F_T, F_C, F_O], "对 customers 表中的客户，有工单的客户的平均有效订单数减去没有工单的客户的平均有效订单数，差值是多少（无有效订单记为 0）？保留4位小数。",
  rnd(pc[has_tk].mean() - pc[~has_tk].mean(), 4))
Q(L, C, [F_O, F_I, F_FX], "币种为 USD 的有效订单 GMV 合计换算为人民币是多少？保留2位小数。", rnd(paid[paid.currency == "USD"].gmv_cny.sum(), 2))
wd = pvl.groupby("category").apply(lambda d: (d.discount_rate * d.quantity).sum() / d.quantity.sum(), include_groups=False)
Q(L, C, [F_O, F_I, F_P], "有效订单的有效行中，按 quantity 加权的平均 discount_rate 最高的 category 是哪个？", top1(wd), "string")
Q(L, C, [F_E, F_P], "剔除异常记录后，把 purchase 事件按 product_id 关联到 category，purchase 次数最多的 category 是哪个？",
  top1(ev[ev.event_type == "purchase"].merge(prod, on="product_id").category.value_counts()), "string")
em = emp.merge(emp[["emp_id", "salary"]].rename(columns={"emp_id": "manager_id", "salary": "m_salary"}), on="manager_id")
Q(L, C, [F_EMP], "薪资高于其直属上级薪资的员工有多少人（两人薪资都不缺失时才比较）？", int((em.salary > em.m_salary).sum()), "integer")
Q(L, C, [F_EMP], "直接下属人数最多的员工有多少名直接下属？", int(max(len(v) for v in children.values())), "integer")
l24c = l24.assign(city=l24.store.str[:2])
Q(L, C, [F_L], "以门店名前两个字作为城市，汇总 2024 年有效销售额，最高的城市是哪个？", top1(l24c.groupby("city").sales.sum()), "string")

# ======================================================== L8 数据质量与清洗
L, C = 8, "数据质量与清洗"
Q(L, C, [F_O], "orders.csv 原始文件中有多少行是多余的完全重复行（原始行数 − 整行去重后行数）？", len(ro) - len(ro.drop_duplicates()), "integer")
Q(L, C, [F_C], "customers.csv 原始文件中有多少行是多余的完全重复行？", len(rc) - len(rc.drop_duplicates()), "integer")
Q(L, C, [F_C], "去重后，birth_date 使用“YYYY年M月D日”中文写法的客户有多少人？", int(rcd.birth_date.str.contains("年").sum()), "integer")
Q(L, C, [F_O], "orders.csv 原始文件中 status 字段（不做任何处理，区分大小写和空格）有多少种不同的取值？", ro.status.nunique(), "integer")
cc_df = pd.DataFrame({
    "customer_id": cust.customer_id, "name": cust.name, "gender": cust.gender.fillna(""),
    "birth_date": cust.birth_date.dt.strftime("%Y-%m-%d"), "city": cust.city,
    "signup_date": cust.signup_date.dt.strftime("%Y-%m-%d"), "tier": cust.tier.fillna("")}).sort_values("customer_id")
Q(L, C, [F_C], "生成清洗后的客户表 customers_clean.csv，列依次为 customer_id,name,gender,birth_date,city,signup_date,tier。要求：整行去重；name 去除首尾空格；gender 统一为 M/F（未知留空）；birth_date 统一为 YYYY-MM-DD；city 归一化；tier 为空则留空；按 customer_id 升序。",
  "customers_clean.csv", "csv", (cc_df, ["customer_id"], {}))
oc_df = pd.DataFrame({
    "order_id": orders.order_id, "customer_id": orders.customer_id, "order_time": orders.ts.dt.strftime("%Y-%m-%d %H:%M:%S"),
    "status": orders.status, "channel": orders.channel, "currency": orders.currency,
    "shipping_fee": orders.shipping_fee, "coupon_code": orders.coupon_code}).sort_values("order_id")
Q(L, C, [F_O], "生成清洗后的订单表 orders_clean.csv，列依次为 order_id,customer_id,order_time,status,channel,currency,shipping_fee,coupon_code。要求：整行去重；order_time 统一为北京时间 YYYY-MM-DD HH:MM:SS；status 统一为小写且去除空格；coupon_code 为空则留空；按 order_id 升序。",
  "orders_clean.csv", "csv", (oc_df, ["order_id"], {"shipping_fee": 1e-9}))
pc_df = pd.DataFrame({"product_id": prod.product_id, "list_price": prod.list_price, "cost": prod.cost,
                      "gross_margin": ((prod.list_price - prod.cost) / prod.list_price).map(lambda v: rnd(v, 4))})
Q(L, C, [F_P], "生成 products_clean.csv，列依次为 product_id,list_price,cost,gross_margin。list_price 解析为数值；gross_margin = (list_price − cost) / list_price，保留4位小数；按 product_id 升序。",
  "products_clean.csv", "csv", (pc_df, ["product_id"], {"list_price": .001, "cost": .001, "gross_margin": 1e-4}))
dev = vl.assign(d=(vl.unit_price * vl.rate - vl.list_price).abs() / vl.list_price)
Q(L, C, [F_I, F_O, F_P, F_FX], "检查价格异常：对去重后、属于 orders 表中订单的有效行，计算 |unit_price × 汇率 − list_price| ÷ list_price，大于 0.5 的行有多少？", int((dev.d > .5).sum()), "integer")
kf = kpi.set_index("date").reindex(all_days)
Q(L, C, [F_K], "把 daily_kpi 补全为 2023-01-01 至 2024-12-31 的每一天，缺失日的 dau 用线性插值填充，补全后 dau 的总和是多少？保留2位小数。", rnd(kf.dau.interpolate().sum(), 2))
Q(L, C, [F_K], "daily_kpi 中 revenue < 0 的录入错误有多少行？", int((kpi.revenue < 0).sum()), "integer")
Q(L, C, [F_EMP], "manager_id 指向不存在员工的记录有多少条？", int(emp.orphan.sum()), "integer")
Q(L, C, [F_EMP], "salary 缺失的员工有多少人？", int(emp.salary.isna().sum()), "integer")
fill = emp.salary.fillna(emp.groupby("dept").salary.transform("median"))
Q(L, C, [F_EMP], "用所在 dept 的薪资中位数（忽略缺失）填充缺失薪资后，全体员工薪资总和是多少？保留2位小数。", rnd(fill.sum(), 2))
Q(L, C, [F_T], "customer_id 为空的工单有多少个？", int(tk.customer_id.isna().sum()), "integer")
lo, hi = cny_gmv.quantile(.01), cny_gmv.quantile(.99)
Q(L, C, [F_O, F_I], "对币种为 CNY 的有效订单 GMV 做 1%/99% 缩尾（低于 1% 分位数的取 1% 分位数，高于 99% 分位数的取 99% 分位数），缩尾后的均值是多少？保留2位小数。", rnd(cny_gmv.clip(lo, hi).mean(), 2))
Q(L, C, [F_I], "order_items.csv 原始文件中有多少行是多余的完全重复行？", len(ri) - len(ri.drop_duplicates()), "integer")
Q(L, C, [F_AB], "ab_test 中同时出现在 A 组和 B 组的污染用户有多少个？", len(T["ab_contam"]), "integer")
Q(L, C, [F_E], "events 中的异常记录（北京时间不在 2024 年内）有多少条？", T["event_anomalies"], "integer")
Q(L, C, [F_L], "legacy_sales.csv 中销售额为 N/A 的记录有多少条？", int(legacy.sales.isna().sum()), "integer")
os_df = pd.DataFrame({"order_id": paid.order_id, "order_date": paid.date.dt.strftime("%Y-%m-%d"), "customer_id": paid.customer_id,
                      "items_qty": paid.qty, "goods_amount_cny": paid.goods_cny.round(2), "shipping_fee_cny": paid.ship_cny.round(2),
                      "gmv_cny": paid.gmv_cny.round(2)}).sort_values("order_id")
Q(L, C, [F_O, F_I, F_FX], "生成有效订单汇总表 order_summary.csv，每个有效订单一行，列依次为 order_id,order_date,customer_id,items_qty,goods_amount_cny,shipping_fee_cny,gmv_cny。order_date 为北京时间日期 YYYY-MM-DD；items_qty 为有效行 quantity 之和（无有效行为 0）；三个金额列为换算成人民币后的值，保留2位小数；按 order_id 升序。",
  "order_summary.csv", "csv", (os_df, ["order_id"], {"items_qty": 1e-9, "goods_amount_cny": .011, "shipping_fee_cny": .011, "gmv_cny": .011}))

# ======================================================== L9 复杂变换
L, C = 9, "复杂变换"
sess = ev.groupby("session_id").agg(n=("ts", "size"), start=("ts", "min"), end=("ts", "max"),
                                     types=("event_type", lambda s: set(s)))
SESS_DEF = "剔除异常记录后，对每个 user_id 按时间排序，相邻两个事件间隔超过 30 分钟则开始一个新会话。"
Q(L, C, [F_E], SESS_DEF + "一共有多少个会话？", len(sess), "integer")
Q(L, C, [F_E], SESS_DEF + "平均每个会话有多少个事件？保留4位小数。", rnd(sess.n.mean(), 4))
Q(L, C, [F_E], SESS_DEF + "会话时长（最后一个事件时间 − 第一个事件时间，单位秒，含毫秒）的中位数是多少？保留1位小数。", rnd((sess.end - sess.start).dt.total_seconds().median(), 1))
Q(L, C, [F_E], SESS_DEF + "包含 purchase 事件的会话占全部会话的比例是多少？保留4位小数。", rnd(sess.types.map(lambda s: "purchase" in s).mean(), 4))
piv = paid.pivot_table(index="month", columns="channel", values="gmv_cny", aggfunc="sum", fill_value=0)
piv = piv.reindex(pd.period_range("2023-01", "2024-12", freq="M").strftime("%Y-%m"), fill_value=0)
mp_df = pd.DataFrame({"month": piv.index, "app": piv["app"].round(2).values, "web": piv["web"].round(2).values,
                      "mini_program": piv["mini_program"].round(2).values})
Q(L, C, [F_O, F_I, F_FX], "生成透视表 monthly_pivot.csv：行为北京时间月份 2023-01 至 2024-12（共 24 行），列依次为 month,app,web,mini_program，值为该月该渠道有效订单的人民币 GMV 合计，保留2位小数，没有订单填 0；按 month 升序。",
  "monthly_pivot.csv", "csv", (mp_df, ["month"], {"app": .011, "web": .011, "mini_program": .011}))
r7 = kf.dau.rolling(7, min_periods=7).mean()
Q(L, C, [F_K], "把 daily_kpi 补全为 2023-01-01 至 2024-12-31 的每一天（缺失日的 dau 保持为空，不填充），计算 7 日滚动平均 dau（窗口为当天及前 6 天，窗口内必须 7 天都有值），最大值是多少？保留2位小数。", rnd(r7.max(), 2))
po = paid.sort_values(["customer_id", "ts"])
f2 = po.groupby("customer_id").gmv_cny.apply(lambda s: s.iloc[1] / s.iloc[0] if len(s) >= 2 and s.iloc[0] > 0 else np.nan).dropna()
Q(L, C, [F_O, F_I, F_FX], "对有效订单数 ≥ 2 的 customer_id，按下单时间排序，计算“第 2 单人民币 GMV ÷ 第 1 单人民币 GMV”（第 1 单 GMV 为 0 的客户剔除），求中位数。保留4位小数。", rnd(f2.median(), 4))
cgk = pk.groupby(["city", "customer_id"]).gmv_cny.sum().reset_index()
best = cgk.sort_values("gmv_cny", ascending=False).groupby("city").head(1)
assert cgk.groupby("city").gmv_cny.apply(lambda s: (s == s.max()).sum()).max() == 1
ct_df = pd.DataFrame({"city": best.city, "customer_id": best.customer_id, "gmv_cny": best.gmv_cny.round(2)}).sort_values("gmv_cny", ascending=False)
Q(L, C, [F_C, F_O, F_I, F_FX], "生成 city_top_customer.csv：对每个城市（归一化后），找出该城市有效订单人民币 GMV 合计最高的客户（只看 customers 表中的客户）。列依次为 city,customer_id,gmv_cny（保留2位小数），每个城市一行，按 gmv_cny 降序。",
  "city_top_customer.csv", "csv", (ct_df, ["city"], {"gmv_cny": .011}))
fm = paid_known.groupby("customer_id").ts.min().dt.strftime("%Y-%m")
Q(L, C, [F_C, F_O], "对 customers 表中的客户，以首个有效订单的北京时间月份作为“新客月份”，列出 2024-01 至 2024-12 每月的新客数（长度 12 的数组）。",
  [int((fm == f"2024-{m:02d}").sum()) for m in range(1, 13)], "list")
dg = paid.groupby("date").gmv_cny.sum().sort_index().cumsum()
Q(L, C, [F_O, F_I, F_FX], "按北京时间日期累计有效订单的人民币 GMV，累计值首次达到全部有效订单 GMV 50% 的日期是哪天？格式 YYYY-MM-DD。",
  dg[dg >= dg.iloc[-1] * .5].index[0].strftime("%Y-%m-%d"), "string")
pw = paid[(paid.date >= "2023-01-02") & (paid.date <= "2024-12-29")]
wk = pw.groupby([pw.ts.dt.isocalendar().year, pw.ts.dt.isocalendar().week]).size()
wk.index = [f"{y}-W{w:02d}" for y, w in wk.index]
Q(L, C, [F_O], "按 ISO 周统计有效订单数，只考虑 2023-W01 至 2024-W52，计算每周相对上一周的环比增长率，增长率最高的是哪一周？格式 YYYY-Www（如 2024-W05）。",
  top1((wk / wk.shift(1) - 1).dropna()), "string")
last = paid_known.groupby("customer_id").date.max()
Q(L, C, [F_C, F_O], "对 customers 表中有有效订单的客户，计算 Recency = 2025-01-01 − 最近一次有效订单的北京时间日期（天数），求平均值。保留2位小数。", rnd((REF - last).dt.days.mean(), 2))
ns = [sum(t in s for s in sess.types) for t in ["view", "add_to_cart", "checkout", "purchase"]]
Q(L, C, [F_E], SESS_DEF + "按会话计算漏斗转化率：含 add_to_cart 的会话数 ÷ 含 view 的会话数、含 checkout ÷ 含 add_to_cart、含 purchase ÷ 含 checkout，以长度 3 的数组给出，保留4位小数。",
  [rnd(ns[i + 1] / ns[i], 4) for i in range(3)], "list")
basket = pvl.groupby("order_id").product_id.apply(lambda s: sorted(set(s)))
pair_cnt = Counter(p for b in basket for p in combinations(b, 2))
Q(L, C, [F_O, F_I], "在有效订单中（只看有效行，同一订单内同一商品只算一次），同时出现次数最多的商品对是哪一对？用 \"小的product_id,大的product_id\" 格式给出（如 \"P0001,P0002\"）。",
  ",".join(top1(pd.Series(pair_cnt))), "string")
lp = legacy.pivot_table(index="store", columns="month", values="sales")
yoy = {s: np.nanmean([lp.at[s, f"2024-{m:02d}"] / lp.at[s, f"2023-{m:02d}"] - 1 for m in range(1, 13)
                      if not (np.isnan(lp.at[s, f"2024-{m:02d}"]) or np.isnan(lp.at[s, f"2023-{m:02d}"]))]) for s in lp.index}
Q(L, C, [F_L], "对每个门店计算 2024 年各月相对 2023 年同月的同比增长率（任一侧为 N/A 的月份跳过），再求平均，平均同比增长率最高的门店是哪个？", top1(pd.Series(yoy)), "string")
Q(L, C, [F_EMP], "组织树（以 CEO 为根，CEO 为第 1 层）最深有几层？", max(depth.values()), "integer")
Q(L, C, [F_EMP], "除 CEO 外，所有层级下属总数（直接和间接）最多的员工是谁？给出 emp_id。",
  top1(pd.Series({e: descendants(e) for e in emp_tree.emp_id if e != "E001"})), "string")
sec = emp.dropna(subset=["salary"]).groupby("dept").salary.apply(lambda s: sorted(s.unique(), reverse=True)[1] if s.nunique() >= 2 else np.nan).dropna()
Q(L, C, [F_EMP], "在每个 dept 内按薪资降序做 dense rank（忽略缺失薪资），取排名第 2 的薪资值，把所有部门的这个值加起来是多少（没有第 2 名的部门跳过）？保留2位小数。", rnd(sec.sum(), 2))
k24 = kpi[(kpi.date.dt.year == 2024) & (kpi.revenue >= 0)]
ms = k24.groupby(k24.date.dt.month).revenue.sum()
Q(L, C, [F_K], "剔除 revenue < 0 的行（缺失日期不补），计算 2024 年每月 revenue 占全年 revenue 的比例，以长度 12 的数组给出（1 月到 12 月），保留4位小数。", [rnd(v / ms.sum(), 4) for v in ms.values], "list")


def longest_streak(months):
    ps = sorted(set(pd.Period(m, "M").ordinal for m in months))
    best = cur = 1
    for a, b in zip(ps, ps[1:]):
        cur = cur + 1 if b == a + 1 else 1
        best = max(best, cur)
    return best


Q(L, C, [F_O], "对每个 customer_id，找出其“连续每个月都有有效订单”（北京时间月份）的最长连续月数，所有客户中的最大值是多少？",
  int(paid.groupby("customer_id").month.apply(longest_streak).max()), "integer")

# ======================================================== L10 高级分析
L, C = 10, "高级分析"
fm_p = paid_known.groupby("customer_id").ts.min().dt.to_period("M")
act = paid_known.assign(p=paid_known.ts.dt.to_period("M")).groupby("customer_id").p.apply(set)


def retention(cohort, k):
    members = fm_p[fm_p == cohort].index
    return sum((cohort + k) in act[c] for c in members) / len(members)


COH = "对 customers 表中的客户，以首个有效订单的北京时间月份为 cohort，某客户在 cohort 月份之后第 k 个月（k=0 为 cohort 当月）有有效订单即视为该月留存，留存率 = 留存客户数 ÷ cohort 客户数。"
Q(L, C, [F_C, F_O], COH + "2024-01 cohort 在 k = 3 时的留存率是多少？保留4位小数。", rnd(retention(pd.Period("2024-01", "M"), 3), 4))
coh_rows = []
for m in range(1, 7):
    p = pd.Period(f"2024-{m:02d}", "M")
    coh_rows.append({"cohort": str(p), **{f"m{k}": rnd(retention(p, k), 4) for k in range(7)}})
Q(L, C, [F_C, F_O], COH + "生成 cohort_retention.csv：行为 cohort 2024-01 至 2024-06，列依次为 cohort,m0,m1,m2,m3,m4,m5,m6（对应 k=0..6 的留存率，保留4位小数），按 cohort 升序。",
  "cohort_retention.csv", "csv", (pd.DataFrame(coh_rows), ["cohort"], {f"m{k}": 1e-4 + 1e-9 for k in range(7)}))
rfm = paid_known.groupby("customer_id").agg(last=("date", "max"), f=("order_id", "size"), m=("gmv_cny", "sum")).sort_index()
rfm["r"] = (REF - rfm["last"]).dt.days
R = pd.qcut(rfm.r.rank(method="first", ascending=False), 5, labels=[1, 2, 3, 4, 5])
Fs = pd.qcut(rfm.f.rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
M = pd.qcut(rfm.m.rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
Q(L, C, [F_C, F_O, F_I, F_FX],
  "对 customers 表中有有效订单的客户做 RFM 打分：Recency = 2025-01-01 − 最近一次有效订单北京日期（天），Frequency = 有效订单数，Monetary = 有效订单人民币 GMV 合计。"
  "先按 customer_id 升序排列，R 分 = pd.qcut(recency.rank(method='first', ascending=False), 5, labels=[1,2,3,4,5])，"
  "F 分 = pd.qcut(frequency.rank(method='first'), 5, labels=[1..5])，M 分 = pd.qcut(monetary.rank(method='first'), 5, labels=[1..5])。R、F、M 都为 5 分的客户有多少人？",
  int(((R == 5) & (Fs == 5) & (M == 5)).sum()), "integer")
lr = stats.linregress(kp.dau, kp.revenue)
Q(L, C, [F_K], "剔除 revenue < 0 的行（缺失日期不补），用最小二乘法拟合 revenue = a × dau + b，斜率 a 是多少？保留4位小数。", rnd(lr.slope, 4))
Q(L, C, [F_K], "剔除 revenue < 0 的行（缺失日期不补），用最小二乘法拟合 revenue = a × dau + b，R² 是多少？保留4位小数。", rnd(lr.rvalue ** 2, 4))
med = kf.dau.rolling(7, center=True, min_periods=4).median()
resid = kf.dau - med
thr = 3 * resid.std()
anom_dates = sorted(resid[resid.abs() > thr].index.strftime("%Y-%m-%d"))
Q(L, C, [F_K], "异常检测：把 daily_kpi 补全为 2023-01-01 至 2024-12-31 的每一天（缺失日 dau 为空，不插值）；计算居中 7 日滚动中位数 med = dau.rolling(7, center=True, min_periods=4).median()；残差 r = dau − med；阈值 = 3 × r 的样本标准差（忽略空值）。列出 |r| > 阈值的所有日期（YYYY-MM-DD，升序）。",
  anom_dates, "list")
ps_ = pvl.groupby("product_id").amt_cny.sum().sort_values(ascending=False)
Q(L, C, [F_O, F_I, F_FX], "帕累托分析：按 product_id 汇总有效订单的人民币商品金额（不含运费），按金额降序累计，累计占比首次达到 80% 时共用了多少个商品？",
  int((ps_.cumsum() / ps_.sum() < .8).sum() + 1), "integer")
N_b = len(basket)
sup1 = Counter(p for b in basket for p in b)
lift = {pr: (c / N_b) / ((sup1[pr[0]] / N_b) * (sup1[pr[1]] / N_b)) for pr, c in pair_cnt.items() if c >= 20}
Q(L, C, [F_O, F_I], "关联规则：在有效订单中（只看有效行，同一订单内同一商品只算一次），对共同出现订单数 ≥ 20 的商品对计算 lift = support(A,B) ÷ (support(A) × support(B))，support 为包含该商品（对）的订单数 ÷ 订单总数（订单总数 = 至少有一条有效行的有效订单数）。lift 最高的商品对是哪一对？用 \"小的product_id,大的product_id\" 格式给出。",
  ",".join(top1(pd.Series(lift))), "string")
viewers = set(ev[ev.event_type == "view"].user_id)
buyers = set(ev[ev.event_type == "purchase"].user_id)
Q(L, C, [F_E], "剔除异常记录后，在有过 view 事件的用户中，有过 purchase 事件的用户占比是多少？保留4位小数。", rnd(len(viewers & buyers) / len(viewers), 4))
p24 = paid[paid.ts.dt.year == 2024]
arpu = p24.groupby("month").gmv_cny.sum() / p24.groupby("month").customer_id.nunique()
Q(L, C, [F_O, F_I, F_FX], "计算北京时间 2024 年每个月的 ARPU（当月有效订单人民币 GMV 合计 ÷ 当月有有效订单的 customer_id 数），再求 12 个月的平均值。保留2位小数。", rnd(arpu.mean(), 2))
rep = pvl.groupby(["category", "customer_id"]).order_id.nunique().reset_index()
rr = rep.groupby("category").order_id.apply(lambda s: (s >= 2).mean())
Q(L, C, [F_O, F_I, F_P], "按 category 计算复购率：在有效订单中购买过该类目的 customer_id 里，在 ≥ 2 个不同有效订单中购买过该类目的客户所占比例。复购率最高的 category 是哪个？", top1(rr), "string")
si = kpi.groupby(kpi.date.dt.dayofweek).dau.mean() / kpi.dau.mean()
Q(L, C, [F_K], "计算 dau 的星期季节指数：各星期几的 dau 均值 ÷ 全部行的 dau 均值（缺失日期不补），以长度 7 的数组给出（周一到周日），保留4位小数。", [rnd(v, 4) for v in si.values], "list")
mg = paid.groupby("month").gmv_cny.sum().sort_index()
fit = np.polyfit(np.arange(1, 25), mg.values, 1)
Q(L, C, [F_O, F_I, F_FX], "按北京时间月份汇总有效订单人民币 GMV（2023-01 至 2024-12，x = 1..24），用最小二乘线性趋势 y = a·x + b 拟合，预测 2025-01（x = 25）的值。保留2位小数。", rnd(np.polyval(fit, 25), 2))
Q(L, C, [F_AB], "样本比例失衡（SRM）检查：剔除污染样本后，用卡方拟合优度检验 A、B 两组用户数是否符合 1:1，p 值是多少？保留4位小数。", rnd(stats.chisquare([na, nb]).pvalue, 4))
p1 = xa / na
p2 = p1 + .01
nreq = math.ceil((stats.norm.ppf(.975) + stats.norm.ppf(.8)) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2)) / (p2 - p1) ** 2)
Q(L, C, [F_AB], "样本量估算：以剔除污染样本后 A 组的转化率为 p1，p2 = p1 + 0.01，α = 0.05（双侧）、检验功效 0.8，每组所需样本量 n = (z_{0.975} + z_{0.8})² × (p1(1−p1) + p2(1−p2)) ÷ (p2 − p1)²，向上取整。n 是多少？", nreq, "integer")
h1 = set(paid[(paid.ts >= "2024-01-01") & (paid.ts < "2024-07-01")].customer_id)
h2 = set(paid[(paid.ts >= "2024-07-01") & (paid.ts < "2025-01-01")].customer_id)
Q(L, C, [F_O], "流失分析：北京时间 2024 年上半年（1–6 月）有有效订单、但下半年（7–12 月）没有有效订单的 customer_id 有多少个？", len(h1 - h2), "integer")
gp = pvl.groupby(["category", "channel"]).profit.sum()
top_gp = top1(gp)
Q(L, C, [F_O, F_I, F_P, F_FX], "按 (category, channel) 组合汇总有效订单的毛利（毛利 = Σ quantity × (unit_price × (1 − discount_rate) × 汇率 − cost)，只计有效行），毛利最高的组合是哪个？用 \"category|channel\" 格式给出。",
  f"{top_gp[0]}|{top_gp[1]}", "string")
s23 = cust[cust.signup_date.dt.year == 2023]
po_k = paid_known.merge(s23[["customer_id", "signup_date"]], on="customer_id")
dd_ = (po_k.date - po_k.signup_date).dt.days
conv = po_k[(dd_ >= 0) & (dd_ <= 365)].customer_id.nunique()
Q(L, C, [F_C, F_O], "2023 年注册的客户中，在注册后 365 天内（0 ≤ 有效订单北京日期 − signup_date ≤ 365 天）有过有效订单的客户占比是多少？保留4位小数。", rnd(conv / len(s23), 4))
slopes = {}
for s in lp.index:
    y = np.array([lp.at[s, f"2024-{m:02d}"] for m in range(1, 13)])
    x = np.arange(1, 13)
    ok = ~np.isnan(y)
    slopes[s] = np.polyfit(x[ok], y[ok], 1)[0]
Q(L, C, [F_L], "对每个门店，用 2024 年各月有效销售额（x = 月份 1..12，N/A 月份跳过）做最小二乘线性拟合，斜率为正的门店有多少个？", int(sum(v > 0 for v in slopes.values())), "integer")
mr = {}
for m_, kids in children.items():
    ms_ = emp.set_index("emp_id").salary
    ks = ms_.loc[kids].dropna()
    if len(ks) >= 2 and not np.isnan(ms_[m_]):
        mr[m_] = ks.mean() / ms_[m_]
Q(L, C, [F_EMP], "对每个至少有 2 名“薪资不缺失的直接下属”且自身薪资不缺失的员工，计算“直接下属平均薪资 ÷ 本人薪资”，比值最高的是谁？给出 emp_id。", top1(pd.Series(mr)), "string")

# ======================================================== 输出
cnt = Counter(c["level"] for c in cases)
assert len(cases) == 200 and all(v == 20 for v in cnt.values()), cnt
json.dump(cases, open(HERE / "test_cases.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("各级题数：", dict(sorted(cnt.items())), "合计", len(cases))
print("真值中植入的 KPI 异常日期：", T["kpi_anomaly_dates"])
print("按规则检测出的异常日期：  ", anom_dates)
print("植入的商品关联对：", T["pairs"])
print("答案类型分布：", Counter(c["answer_type"] for c in cases))

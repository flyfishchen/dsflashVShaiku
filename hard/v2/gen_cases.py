#!/usr/bin/env python3
"""v2：从真值计算 200 道题（10 级 × 20）的标准答案"""

import gzip
import json
import math
import pickle
import re
from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).parent
DATA = HERE / "data"
EXP = HERE / "expected"
EXP.mkdir(exist_ok=True)
T = pickle.load(open(HERE / "truth/truth.pkl", "rb"))
UTC = timezone.utc


def rnd(x, k=0):
    v = float(Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-k), rounding=ROUND_HALF_UP))
    return int(v) if k == 0 else v


def top1(s, smallest=False):
    s = pd.Series(s).sort_values(ascending=smallest)
    if (s == s.iloc[0]).sum() > 1:
        raise ValueError(f"并列：\n{s[s == s.iloc[0]]}")
    k = s.index[0]
    return k.item() if hasattr(k, "item") else k


def py(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, dict):
        return {str(k): py(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [py(x) for x in v]
    return v


cases = []


def Q(level, cat, files, question, expected, atype="number", csv=None, tols=None):
    c = {"id": len(cases) + 1, "level": level, "category": cat, "files": files, "question": question, "answer_type": atype}
    if atype == "csv":
        df, keys, num_tol = csv
        fn = f"{c['id']:03d}_{expected}"
        df.to_csv(EXP / fn, index=False)
        c.update(expected=expected, key_cols=keys, num_tol=num_tol, exp_path=f"v2/expected/{fn}")
    else:
        c["expected"] = py(expected)
    if tols:
        c["tols"] = tols
    cases.append(c)


def dr(d, k):
    return {str(a): rnd(b, k) for a, b in d.items()}


# ============================================================ 派生真值
FXS = T["fx"].set_index("date").usd_cny


def fx_at(d):
    return float(FXS.iloc[FXS.index.searchsorted(pd.Timestamp(d), side="right") - 1])


o = T["orders"].copy()
o["year"] = [d.year if d is not None else None for d in o.local_date]
fx_cache = {}
o["fx"] = [np.nan if d is None else (1.0 if c == "CNY" else fx_cache.setdefault(d, fx_at(d))) for d, c in zip(o.local_date, o.currency)]
o["net_cny"] = o.net * o.fx
o["ym"] = [d.strftime("%Y-%m") if d is not None else None for d in o.local_date]
comp = o[o.status == "completed"]
A = o[o.src == "A"]
Ac = A[A.status == "completed"]
L = o[o.src == "L"]
Lc = L[L.status == "completed"]
CN = {"S01", "S02", "S03", "S04"}
items = T["items"].merge(o[["order_id", "store_id", "status", "utc", "currency"]], on="order_id")
SKU_HIST = defaultdict(list)
for e in T["cdc"]:
    SKU_HIST[e["sku"]].append((e["ts"], e["after"]))


def sku_state(sku, t):
    h = SKU_HIST[sku]
    i = bisect_right([x[0] for x in h], t) - 1
    return h[i][1] if i >= 0 else None


items["cat_t"] = [sku_state(s, u.to_pydatetime().replace(tzinfo=UTC))["category"] for s, u in zip(items.sku, items.utc)]
items["cat0"] = [SKU_HIST[s][0][1]["category"] for s in items.sku]
icn = items[(items.store_id.isin(CN)) & (items.status == "completed")]

F_ST, F_FX = "stores.csv", "fx_daily.csv"
F_LEG, F_API = "sales/legacy", "sales/api/orders_2024.jsonl"
F_PAY, F_REF = "payments/gateway_settlement.csv", "payments/refunds.csv"
F_MEM, F_CRM = "crm/members_shop.csv", "crm/contacts_crm.csv"
F_CDC = "catalog/product_cdc.jsonl"
F_INVP, F_INVS = "inventory/purchases.csv", "inventory/shipments.csv"
F_SUB = "subscriptions/subscription_events.csv"
F_DEV, F_IOT = "iot/devices.csv", "iot/readings.csv.gz"
F_TP, F_CV, F_SP = "marketing/touchpoints.csv", "marketing/conversions.csv", "marketing/spend.csv"
F_AB, F_DID, F_MM = "experiments/ab_users.csv", "experiments/did_stores.csv", "experiments/multi_metric.csv"
F_LOG = "logs/access.log"
F_COA, F_GL = "finance/chart_of_accounts.csv", "finance/gl_2024.txt"
SALES_ALL = [F_ST, F_FX, F_LEG, F_API]

# ============================================================ L1 多格式读取与解析
LV, C = 1, "多格式读取与解析"
leg_files = sorted((DATA / F_LEG).glob("*.csv"))
leg_raw = [pd.read_csv(f, dtype=str, keep_default_na=False) for f in leg_files]
Q(LV, C, [F_LEG], "sales/legacy/ 下 12 个文件按原样逐行统计，一共有多少行数据（不含表头）？", sum(len(x) for x in leg_raw), "integer")
Q(LV, C, [F_LEG], "旧系统文件中一共有多少个不同的订单（不按日期筛选）？", len(L), "integer")
Q(LV, C, [F_LEG], "旧系统文件中全部 completed 订单（不按日期筛选）的原价合计，按币种分别是多少？键为币种，保留2位小数。", dr(Lc.groupby("currency").gross.sum(), 2), "dict")
Q(LV, C, [F_LEG], "旧系统文件中全部人民币 completed 订单（不按日期筛选）的折扣合计是多少？保留2位小数。", rnd(Lc[Lc.currency == "CNY"].discount.sum(), 2))
Q(LV, C, [F_API], "2024 年新系统一共有多少个不同的订单？", len(A), "integer")
Q(LV, C, [F_API], "2024 年新系统中，最终状态为 cancelled 的订单有多少个？", int((A.status == "cancelled").sum()), "integer")
Q(LV, C, [F_API], "2024 年新系统所有订单（每个订单只算一次）的明细行一共有多少条？", len(T["items"]), "integer")
Q(LV, C, [F_API], "2024 年新系统中使用过促销码 FLASH20 的订单有多少个（任意状态）？", int(T["promos"][T["promos"].code == "FLASH20"].order_id.nunique()), "integer")
Q(LV, C, [F_API], "2024 年新系统 completed 订单一共卖出多少件商品（明细 qty 之和）？", int(items[items.status == "completed"].qty.sum()), "integer")
gl = T["gl"]
Q(LV, C, [F_GL], "gl_2024.txt 中一共有多少张凭证（不同的 journal_id）？", gl.journal_id.nunique(), "integer")
Q(LV, C, [F_GL], "gl_2024.txt 中所有分录的借方金额合计是多少（不剔除任何行）？保留2位小数。", rnd(gl.amount[gl.amount > 0].sum(), 2))
Q(LV, C, [F_GL], "gl_2024.txt 中所有分录的贷方金额合计是多少（不剔除任何行，取正数）？保留2位小数。", rnd(-gl.amount[gl.amount < 0].sum(), 2))
gl_lines = (DATA / F_GL).read_text(encoding="utf-8").splitlines()
Q(LV, C, [F_GL], "gl_2024.txt 中金额字段带千分位逗号的分录有多少行？", sum("," in ln[37:53] for ln in gl_lines), "integer")
logs = T["logs"]
lp = logs[~logs.malformed]
Q(LV, C, [F_LOG], "access.log 中格式完整、能按日志格式解析的行有多少？", len(lp), "integer")
Q(LV, C, [F_LOG], "能解析的请求中，状态码为 404 的有多少个？", int((lp.status == 404).sum()), "integer")
Q(LV, C, [F_LOG], "能解析的请求中（含爬虫），请求次数最多的 IP 是哪个？", top1(lp.ip.value_counts()), "string")
with gzip.open(DATA / F_IOT, "rt") as f:
    iot_raw = pd.read_csv(f, dtype=str)
Q(LV, C, [F_IOT], "readings.csv.gz 按原样逐行统计，一共有多少行数据（不含表头）？", len(iot_raw), "integer")
Q(LV, C, [F_IOT], "readings.csv.gz 中一共出现了多少台不同的设备？", iot_raw.device_id.nunique(), "integer")
cdc_lines = (DATA / F_CDC).read_text(encoding="utf-8").splitlines()
Q(LV, C, [F_CDC], "product_cdc.jsonl 按原样逐行统计，一共有多少条事件？", len(cdc_lines), "integer")
Q(LV, C, [F_CDC], "product_cdc.jsonl 中一共有多少个不同的事件（按 lsn）？", len(T["cdc"]), "integer")

# ============================================================ L2 清洗、标准化与异常识别
LV, C = 2, "清洗与异常识别"
fid = pd.concat([x.assign(_f=f.name)[["order_id", "_f"]] for x, f in zip(leg_raw, leg_files)])
Q(LV, C, [F_LEG], "旧系统中，同一个订单号出现在两个或以上月份文件中的订单有多少个？", int((fid.groupby("order_id")._f.nunique() >= 2).sum()), "integer")
STD = ["order_id", "store_id", "member_id", "order_time", "currency", "gross", "discount", "status"]
leg_std = pd.concat([x.set_axis(STD, axis=1) for x in leg_raw])
Q(LV, C, [F_LEG], "把 12 个旧系统文件统一字段后合并，完全重复的多余行有多少？", len(leg_std) - len(leg_std.drop_duplicates()), "integer")
Q(LV, C, [F_LEG, F_ST], "旧系统中，下单时间因夏令时开始而不存在的订单有多少个？", int((~o.time_ok).sum()), "integer")
amb = L[(L.store_id.isin(["S05", "S06"])) & (L.local.map(lambda x: x.strftime("%Y-%m-%d %H")) == "2023-11-05 01")]
Q(LV, C, [F_LEG, F_ST], "旧系统中，下单时间因夏令时结束而出现两次（有歧义）的订单有多少个？", len(amb), "integer")
Q(LV, C, [F_API], "新系统中，有多少个订单先以 completed 导出、后来又以 cancelled 状态导出？", int(o.cancelled_later.sum()), "integer")
api_lines = (DATA / F_API).read_text(encoding="utf-8").splitlines()
Q(LV, C, [F_API], "新系统导出文件中，内容完全相同的多余记录有多少条？", len(api_lines) - len(set(api_lines)), "integer")
Q(LV, C, [F_IOT, F_DEV], "有几台设备实际上是以华氏度上报温度的？列出这些设备（JSON 数组，顺序不限）。", T["f_devs"], "set")
iot = T["iot"]
Q(LV, C, [F_IOT, F_DEV], "把以华氏度上报的设备换算为摄氏度、并去掉完全重复的行之后，仍超出合理范围的读数有多少条？", int((~iot.valid).sum()), "integer")
Q(LV, C, [F_IOT], "readings.csv.gz 中完全重复的多余行有多少？", len(iot_raw) - len(iot_raw.drop_duplicates()), "integer")
Q(LV, C, [F_IOT, F_DEV], "统一时区、换算华氏度、去重并剔除无效值后，有效读数一共有多少条？", int(iot.valid.sum()), "integer")
mem, crm = T["members"], T["crm"]
Q(LV, C, [F_MEM], "members_shop 中有多少条记录的手机号是有效的中国大陆手机号（统一写法后为 1 开头的 11 位数字）？", int(mem.phone.notna().sum()), "integer")
Q(LV, C, [F_MEM, F_CRM], "members_shop 与 contacts_crm 两个文件中，统一写法后一共出现了多少个不同的手机号？", len(set(mem.phone.dropna()) | set(crm.phone.dropna())), "integer")
Q(LV, C, [F_MEM], "members_shop 中统一写法后（去首尾空格、转小写）有多少个不同的邮箱？", int(mem.email.dropna().nunique()), "integer")
Q(LV, C, [F_GL], "gl_2024.txt 中记账日期不是合法日期的分录有多少行？", int((~gl.date_ok).sum()), "integer")
Q(LV, C, [F_GL], "gl_2024.txt 中借贷不平衡的凭证有哪些？以 JSON 数组按凭证号升序给出。", T["unbal"], "list")
Q(LV, C, [F_LOG], "能解析的请求中，爬虫请求（User-Agent 含 bot、spider 或 crawler，不区分大小写）占多少比例？保留4位小数。", rnd(lp.is_bot.mean(), 4))
Q(LV, C, [F_LOG], "能解析的请求中，时间带 -0700 时区偏移的有多少个？", int(lp.west.sum()), "integer")
cdc = T["cdc"]
Q(LV, C, [F_CDC], "被删除过（出现过 op = d）的 SKU 有多少个？", len({e["sku"] for e in cdc if e["op"] == "d"}), "integer")
Q(LV, C, [F_CDC], "删除后又被重新创建（op = c）的 SKU 有哪些？以 JSON 数组按 SKU 升序给出。", sorted({e["sku"] for e in cdc if e["op"] == "c"}), "list")
Q(LV, C, [F_LEG], "旧系统文件在年中改过字段名。改名后的“订单原价”和“折扣”字段名分别是什么？用 \"原价字段名,折扣字段名\" 格式给出。", "total_amount,discount_amt", "string")

# ============================================================ L3 对账
LV, C = 3, "对账"
pay, ref = T["payments"], T["refunds"]
ok_ids = set(o.order_id)
pa = pay[pay.order_id.isin(ok_ids)]
succ = pa[pa.status == "SUCCESS"].groupby("order_id").amount.agg(["sum", "count"])
revd = pa[pa.status == "REVERSED"].groupby("order_id").amount.sum()
refd = ref.groupby("order_id").amount.sum()
fail_o = set(pa[pa.status == "FAILED"].order_id)
rec = Ac[["order_id", "store_id", "currency", "net", "net_cny", "utc"]].copy()
rec["paid"] = rec.order_id.map(succ["sum"]).fillna(0.0)
rec["n_succ"] = rec.order_id.map(succ["count"]).fillna(0).astype(int)
rec["reversed"] = rec.order_id.map(revd).fillna(0.0)
rec["refunded"] = rec.order_id.map(refd).fillna(0.0)
d_ = (rec.paid - rec.net).round(2)


def classify(r, d):
    if r.n_succ == 0:
        return "missing"
    if r.n_succ >= 2:
        return "double"
    if d < -0.01:
        return "underpaid"
    if d > 0.01:
        return "overpaid"
    return "matched"


rec["result"] = [classify(r, d) for r, d in zip(rec.itertuples(), d_)]
RECDEF = "（只看 2024 年新系统中最终状态为 completed 的订单；SUCCESS 记录即一次成功扣款）"
Q(LV, C, [F_API, F_PAY], "有多少个 completed 订单没有任何 SUCCESS 支付记录？" + RECDEF, int((rec.result == "missing").sum()), "integer")
Q(LV, C, [F_API, F_PAY], "有多少个 completed 订单被重复扣款（SUCCESS 记录 ≥ 2 条）？" + RECDEF, int((rec.result == "double").sum()), "integer")
dbl = rec[rec.result == "double"]
Q(LV, C, [F_API, F_PAY], "被重复扣款的订单多收的金额（SUCCESS 金额合计 − 订单净额）按币种分别合计是多少？键为币种，保留2位小数。" + RECDEF, dr((dbl.paid - dbl.net).groupby(dbl.currency).sum(), 2), "dict")
Q(LV, C, [F_API, F_PAY], "只有 1 条 SUCCESS 记录、且扣款金额比订单净额少 0.01 以上的 completed 订单有多少个？" + RECDEF, int((rec.result == "underpaid").sum()), "integer")
Q(LV, C, [F_API, F_PAY], "只有 1 条 SUCCESS 记录、扣款金额与订单净额不完全相等但差额不超过 0.01 的 completed 订单有多少个？" + RECDEF, int(((rec.n_succ == 1) & (d_.abs() > 0) & (d_.abs() <= 0.01)).sum()), "integer")
Ax = A[A.status == "cancelled"]
Q(LV, C, [F_API, F_PAY, F_REF], "2024 年新系统中最终状态为 cancelled、有 SUCCESS 扣款、但没有任何退款记录的订单有多少个？",
  int(sum(1 for i in Ax.order_id if i in succ.index and i not in refd.index)), "integer")
Q(LV, C, [F_API, F_PAY], "支付记录中，order_id 在新系统订单里找不到的有多少条？", int((~pay.order_id.isin(ok_ids)).sum()), "integer")
paid_net = succ["sum"].sub(revd, fill_value=0)
over = sorted(i for i, v in refd.items() if v > paid_net.get(i, 0) + 0.01)
Q(LV, C, [F_API, F_PAY, F_REF], "退款金额合计超过该订单实际扣款（SUCCESS 金额合计 − REVERSED 金额合计）的订单有哪些？以 JSON 数组按订单号升序给出。", over, "list")
COLL = "实收 = SUCCESS 金额合计 − REVERSED 金额合计 − 退款金额合计，只统计能对应到新系统订单的记录"
for cur in ["CNY", "USD"]:
    s = pa[(pa.currency == cur)]
    v = s[s.status == "SUCCESS"].amount.sum() - s[s.status == "REVERSED"].amount.sum() - ref[(ref.currency == cur) & ref.order_id.isin(ok_ids)].amount.sum()
    Q(LV, C, [F_API, F_PAY, F_REF], f"{cur} 的实收合计是多少？{COLL}。保留2位小数。", rnd(v, 2))
Q(LV, C, [F_PAY], "支付文件中所有 CNY 记录的手续费合计是多少？保留2位小数。", rnd(pay[pay.currency == "CNY"].fee.sum(), 2))
Q(LV, C, [F_API, F_PAY], "发生过拒付（有 REVERSED 记录）的订单有多少个？", int(revd.index.nunique()), "integer")
Q(LV, C, [F_API, F_PAY], "先有 FAILED 记录、又有 SUCCESS 记录的订单有多少个？", len(fail_o & set(succ.index)), "integer")
rec_df = pd.DataFrame({"order_id": rec.order_id, "expected": rec.net.round(2), "paid": rec.paid.round(2), "reversed": rec.reversed.round(2),
                       "refunded": rec.refunded.round(2), "result": rec.result}).sort_values("order_id")
Q(LV, C, [F_API, F_PAY, F_REF], "生成对账表 reconciliation.csv：2024 年新系统每个最终 completed 订单一行，列依次为 order_id,expected,paid,reversed,refunded,result。"
  "expected 为订单净额，paid 为 SUCCESS 金额合计，reversed 为 REVERSED 金额合计，refunded 为退款金额合计（均为原币种，保留2位小数，没有记录为 0）。"
  "result 规则：SUCCESS 条数为 0 → missing；≥ 2 → double；否则 paid − expected < −0.01 → underpaid，> 0.01 → overpaid，其余 → matched。按 order_id 升序。",
  "reconciliation.csv", "csv", (rec_df, ["order_id"], {"expected": .011, "paid": .011, "reversed": .011, "refunded": .011}))
mis = rec[rec.result == "missing"]
Q(LV, C, SALES_ALL + [F_PAY], "按门店汇总没有任何 SUCCESS 支付记录的 completed 订单的净额（换算为人民币），金额最高的门店是哪个？给出 store_id。" + RECDEF, top1(mis.groupby("store_id").net_cny.sum()), "string")
mt = rec[rec.result == "matched"].merge(pa[pa.status == "SUCCESS"][["order_id", "paid_at"]], on="order_id")
Q(LV, C, [F_API, F_PAY], "对 matched 订单（恰好有 1 条 SUCCESS 记录，且 |SUCCESS 金额 − 订单净额| ≤ 0.01），SUCCESS 扣款时间与下单时间之差（秒）的中位数是多少？保留1位小数。" + RECDEF, rnd(((mt.paid_at - mt.utc).dt.total_seconds()).median(), 1))
coa = T["coa"]
glv = gl[~gl.journal_id.isin(T["unbal"])].merge(coa, on="account")
Q(LV, C, [F_GL, F_COA], "剔除借贷不平衡的凭证后，各科目类型的余额（借方 − 贷方）是多少？键为 type，保留2位小数。", dr(glv.groupby("type").amount.sum(), 2), "dict")
glvd = glv[glv.date_ok]
rev_ = -glvd[glvd.type == "revenue"].amount.sum()
exp_ = glvd[glvd.type == "expense"].amount.sum()
GLDEF = "剔除借贷不平衡的凭证和记账日期无效的行"
Q(LV, C, [F_GL, F_COA], f"{GLDEF}后，2024 年收入（revenue 类科目贷方 − 借方）合计是多少？保留2位小数。", rnd(rev_, 2))
Q(LV, C, [F_GL, F_COA], f"{GLDEF}后，2024 年净利润（收入 − 费用；费用为 expense 类科目借方 − 贷方）是多少？保留2位小数。", rnd(rev_ - exp_, 2))
q3 = glvd[(glvd.account == "6001") & (glvd.date.dt.month.isin([7, 8, 9]))]
Q(LV, C, [F_GL, F_COA], f"{GLDEF}后，2024 年第三季度（按记账日期）主营业务收入（科目 6001，贷方 − 借方）是多少？保留2位小数。", rnd(-q3.amount.sum(), 2))

# ============================================================ L4 实体合并
LV, C = 4, "实体合并"
recs_ = pd.concat([mem[["rid", "phone", "email"]], crm[["rid", "phone", "email"]]], ignore_index=True)
parent = list(range(len(recs_)))


def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


for col in ["phone", "email"]:
    first = {}
    for i, v in enumerate(recs_[col]):
        if isinstance(v, str):
            if v in first:
                a, b = find(i), find(first[v])
                if a != b:
                    parent[a] = b
            else:
                first[v] = i
recs_["root"] = [find(i) for i in range(len(recs_))]
recs_["is_m"] = recs_.rid.str.startswith("M")
key = {}
for root, g in recs_.groupby("root"):
    ms = sorted(g.rid[g.is_m])
    key[root] = ms[0] if ms else sorted(g.rid)[0]
recs_["key"] = recs_.root.map(key)
cl = recs_.groupby("key").agg(n=("rid", "size"), nm=("is_m", "sum"), nph=("phone", lambda s: s.dropna().nunique()), nem=("email", lambda s: s.dropna().nunique()))
cl["nc"] = cl.n - cl.nm
m2k = dict(zip(recs_.rid[recs_.is_m], recs_.key[recs_.is_m]))
RULE = ("合并规则：members_shop 与 contacts_crm 中的任意两条记录，若统一写法后的手机号相同，或统一写法后的邮箱相同，即视为同一个人；该关系可传递（A 与 B 同人、B 与 C 同人，则 A、B、C 同人）。"
        "每个合并后的人称为一个“簇”，簇的代表 ID 为簇内字典序最小的 member_id（簇内没有 member_id 时为最小的 crm_id）。")
FM = [F_MEM, F_CRM]
Q(LV, C, FM, RULE + "合并后一共有多少个簇？", len(cl), "integer")
Q(LV, C, FM, RULE + "只包含 members_shop 记录（没有任何 CRM 记录）的簇有多少个？", int((cl.nc == 0).sum()), "integer")
Q(LV, C, FM, RULE + "只包含 contacts_crm 记录的簇有多少个？", int((cl.nm == 0).sum()), "integer")
Q(LV, C, FM, RULE + "同时包含两个系统记录的簇有多少个？", int(((cl.nm > 0) & (cl.nc > 0)).sum()), "integer")
Q(LV, C, FM, RULE + "最大的簇包含多少条记录？", int(cl.n.max()), "integer")
Q(LV, C, FM, RULE + "包含 2 个及以上 member_id 的簇有多少个？", int((cl.nm >= 2).sum()), "integer")
Q(LV, C, FM, RULE + "簇内出现 2 个及以上不同手机号（统一写法后）的簇有多少个？", int((cl.nph >= 2).sum()), "integer")
Q(LV, C, FM, RULE + "簇内出现 2 个及以上不同邮箱（统一写法后）的簇有多少个？", int((cl.nem >= 2).sum()), "integer")
oc = comp[comp.member_id.notna() & comp.time_ok].copy()
oc["key"] = oc.member_id.map(m2k)
OCDEF = "（订单只算 completed，下单时间无效的订单不计；金额为订单净额换算成的人民币）"
FMS = FM + SALES_ALL
Q(LV, C, FMS, RULE + "按簇统计 2024 年的订单数，订单数最多的簇有多少笔订单？" + OCDEF, int(oc[oc.year == 2024].groupby("key").size().max()), "integer")
kn = oc.groupby("key").net_cny.sum()
Q(LV, C, FMS, RULE + "按簇统计 2023–2024 两年的订单金额合计，最高的簇金额是多少？保留2位小数。" + OCDEF, rnd(kn.max(), 2))
Q(LV, C, FMS, RULE + "按簇统计 2023–2024 两年的订单金额合计，金额最高的簇的代表 ID 是什么？" + OCDEF, top1(kn), "string")
y23, y24 = set(oc[oc.year == 2023].key), set(oc[oc.year == 2024].key)
Q(LV, C, FMS, RULE + "2023 年和 2024 年都有订单的簇有多少个？" + OCDEF, len(y23 & y24), "integer")
Q(LV, C, FMS, RULE + "2023 年有订单、2024 年没有订单的簇有多少个？" + OCDEF, len(y23 - y24), "integer")
o24 = oc[oc.year == 2024]
Q(LV, C, FMS, RULE + "2024 年有订单的不同 member_id 数，比 2024 年有订单的簇数多多少？" + OCDEF, int(o24.member_id.nunique() - o24.key.nunique()), "integer")
kc = o24.groupby("key").size()
Q(LV, C, FMS, RULE + "2024 年有 2 笔及以上订单的簇，占 2024 年有订单的簇的比例是多少？保留4位小数。" + OCDEF, rnd((kc >= 2).mean(), 4))
agg = oc.groupby("key").agg(orders=("order_id", "size"), net_cny=("net_cny", "sum"))
agg["members"] = cl.loc[agg.index, "nm"].astype(int)
agg = agg.sort_values("net_cny", ascending=False)
assert agg.net_cny.iloc[99] != agg.net_cny.iloc[100]
top = agg.head(100).reset_index()
Q(LV, C, FMS, RULE + "生成 person_ltv.csv：按 2023–2024 两年订单金额合计取前 100 个簇，列依次为 cluster_key,members,orders,net_cny（members 为簇内 member_id 个数，orders 为订单数，net_cny 保留2位小数），按 net_cny 降序。" + OCDEF,
  "person_ltv.csv", "csv", (pd.DataFrame({"cluster_key": top.key, "members": top.members, "orders": top.orders, "net_cny": top.net_cny.round(2)}), ["cluster_key"], {"members": 1e-9, "orders": 1e-9, "net_cny": .011}))
crm_city = pd.read_csv(DATA / F_CRM, dtype=str, keep_default_na=False).set_index("crm_id").city
sh_keys = set(recs_[(~recs_.is_m) & (recs_.rid.map(crm_city) == "上海")].key)
Q(LV, C, FMS, RULE + "包含至少一条 city 为“上海”的 CRM 记录的簇，2024 年订单金额合计是多少？保留2位小数。" + OCDEF, rnd(o24[o24.key.isin(sh_keys)].net_cny.sum(), 2))
mreg = mem.set_index("rid").created
spread = recs_[recs_.is_m].assign(reg=lambda d: d.rid.map(mreg)).groupby("key").reg.agg(lambda s: (s.max() - s.min()).days if len(s) >= 2 else 0)
Q(LV, C, FM, RULE + "簇内 member_id 的注册时间（register_time）最早与最晚相差超过 365 天的簇有多少个？", int((spread > 365).sum()), "integer")
Q(LV, C, FMS, RULE + "2024 年在 2 家及以上门店下过单的簇有多少个？" + OCDEF, int((o24.groupby("key").store_id.nunique() >= 2).sum()), "integer")
Q(LV, C, FMS, RULE + "2024 年“按簇计算的人均订单金额”是“按 member_id 计算的人均订单金额”的多少倍？人均 = 订单金额合计 ÷ 有订单的簇数（或 member_id 数）。保留4位小数。" + OCDEF,
  rnd(o24.member_id.nunique() / o24.key.nunique(), 4))

# ============================================================ L5 时间与时区
LV, C = 5, "时间与时区"
lu = Lc[Lc.store_id.isin(["S05", "S06"]) & Lc.time_ok]
Q(LV, C, [F_LEG, F_ST], "2023 年旧系统美国门店（S05、S06）的 completed 订单，按 UTC 日期统计订单数，最多的是哪一天？格式 YYYY-MM-DD。", top1(lu.utc.dt.strftime("%Y-%m-%d").value_counts()), "string")
Q(LV, C, [F_LEG, F_ST], "S05 在 2023-11-05 本地时间 01:00–01:59 之间的订单（任意状态），换算成 UTC 后最早的一笔是什么时间？格式 YYYY-MM-DD HH:MM:SS。",
  amb[amb.store_id == "S05"].utc.min().strftime("%Y-%m-%d %H:%M:%S"), "string")
Q(LV, C, [F_API, F_ST], "按业务日期，S06 在 2024-03-10 有多少个订单（任意最终状态）？", int(((A.store_id == "S06") & (A.local_date == datetime(2024, 3, 10).date())).sum()), "integer")
cv_ = comp[comp.time_ok]
Q(LV, C, SALES_ALL, "2023–2024 年全部门店的 completed 订单，按北京时间日期统计订单数，最多的是哪一天？格式 YYYY-MM-DD。", top1((cv_.utc + pd.Timedelta(hours=8)).dt.strftime("%Y-%m-%d").value_counts()), "string")
Q(LV, C, [F_API, F_ST], "2024 年新系统 completed 订单按门店本地时间的小时（0–23）统计，订单最多的是几点？", top1(Ac.local.map(lambda x: x.hour).value_counts()), "integer")
Q(LV, C, [F_API, F_ST], "2024 年新系统 completed 订单按 UTC 时间的小时（0–23）统计，订单最多的是几点？", top1(Ac.utc.dt.hour.value_counts()), "integer")
iu = iot.sort_values(["device_id", "ts"])
gap = iu.groupby("device_id").ts.diff().dt.total_seconds()
iu = iu.assign(gap=gap)
IOTDEF = "（统一为 UTC、去掉完全重复的行；断线 = 同一设备相邻两条读数的时间间隔超过 1 小时）"
Q(LV, C, [F_IOT], "所有设备的断线次数合计是多少？" + IOTDEF, int((iu.gap > 3600).sum()), "integer")
Q(LV, C, [F_IOT], "最长的一次断线持续了多少小时（相邻读数时间差）？保留2位小数。" + IOTDEF, rnd(iu.gap.max() / 3600, 2))
Q(LV, C, [F_IOT], "最长的一次断线发生在哪台设备？" + IOTDEF, iu.loc[iu.gap.idxmax(), "device_id"], "string")
iv = iot[iot.valid].merge(T["devices"][["device_id", "site"]], on="device_id")
IVDEF = "（以华氏度上报的设备换算为摄氏度，去重并剔除无效值，时间统一为 UTC）"
d15 = iv[iv.ts.dt.strftime("%Y-%m-%d") == "2024-11-15"]
hm = d15.groupby(["site", "device_id", d15.ts.dt.hour]).temp_c.mean().reset_index()
Q(LV, C, [F_IOT, F_DEV], "2024-11-15（UTC）各仓库的日均温度是多少？先求每台设备每个 UTC 小时的平均温度，再对同一仓库当天所有“设备-小时”值求平均。键为 site，保留2位小数。" + IVDEF,
  dr(hm.groupby("site").temp_c.mean(), 2), "dict")
nov = iv[iv.ts.dt.month == 11]
Q(LV, C, [F_IOT, F_DEV], "2024 年 11 月（UTC）每台设备的数据完整率 = 有效读数条数 ÷ (30 × 288)，完整率最低的是哪台设备？" + IVDEF, top1(nov.groupby("device_id").size(), smallest=True), "string")
dd = iv.groupby(["device_id", iv.ts.dt.strftime("%Y-%m-%d")]).temp_c.agg(lambda s: s.max() - s.min())
k_ = top1(dd)
Q(LV, C, [F_IOT, F_DEV], "按 UTC 日期，单台设备单日温差（当日最高 − 最低）最大的是哪台设备、哪一天？用 \"device_id|YYYY-MM-DD\" 格式给出。" + IVDEF, f"{k_[0]}|{k_[1]}", "string")
subs = T["subs"].sort_values(["account_id", "event_date", "seq"])
spells, cur_start = {}, {}
for acc, g in subs.groupby("account_id"):
    n, prev, st = 0, 0, None
    for r in g.itertuples():
        if prev == 0 and r.mrr_after > 0:
            n += 1
            st = r.event_date
        prev = r.mrr_after
    spells[acc] = n
    if prev > 0:
        cur_start[acc] = st
SUBDEF = "（账户 MRR 从 0 变为正数开始一段付费期，再次变为 0 时该段结束；截至最后一个事件仍在付费的当前一段也算一段；同一账户的事件按 event_date、seq 排序）"
Q(LV, C, [F_SUB], "所有账户中，付费期段数最多的账户有几段付费期？" + SUBDEF, max(spells.values()), "integer")
Q(LV, C, [F_SUB], "2024-12-31 日终仍在付费的账户，其当前这段付费期已持续的天数（2024-12-31 − 本段开始日期）的中位数是多少？保留1位小数。" + SUBDEF,
  rnd(np.median([(pd.Timestamp("2024-12-31") - v).days for v in cur_start.values()]), 1))
Q(LV, C, [F_LOG], "能解析的请求中（含爬虫），5xx 状态码最多的 UTC 小时是哪个？格式 YYYY-MM-DD HH。", top1(lp[lp.status >= 500].ts.dt.strftime("%Y-%m-%d %H").value_counts()), "string")
lh = lp[~lp.is_bot].sort_values(["ip", "ts"])
newsess = lh.groupby("ip").ts.diff().isna() | (lh.groupby("ip").ts.diff() > pd.Timedelta(minutes=30))
SESS = "（只看能解析的非爬虫请求；同一 IP 相邻请求间隔超过 30 分钟即开始新会话）"
Q(LV, C, [F_LOG], "一共有多少个会话？" + SESS, int(newsess.sum()), "integer")
Q(LV, C, [F_LOG], "平均每个会话有多少个请求？保留4位小数。" + SESS, rnd(len(lh) / newsess.sum(), 4))
tp, cvs = T["tp"], T["cv"]
tps = tp.sort_values("ts")
lastgap = []
tp_by = {u: g.ts.tolist() for u, g in tps.groupby("user_id")}
for r in cvs.itertuples():
    ts_ = [t for t in tp_by.get(r.user_id, []) if t < r.ts]
    if ts_:
        lastgap.append((r.ts - ts_[-1]).total_seconds() / 3600)
Q(LV, C, [F_TP, F_CV], "对每笔转化，找到该用户在转化之前（不限时间窗）的最后一个触点，两者的时间间隔（小时）的中位数是多少？没有更早触点的转化不计。保留2位小数。", rnd(np.median(lastgap), 2))
days = pd.date_range("2024-01-01", "2024-12-31")
Q(LV, C, [F_FX], "把 2024 年每个日历日都补上汇率（当天没有就用之前最近一天的），全年 366 天的平均汇率是多少？保留4位小数。", rnd(np.mean([fx_at(d) for d in days]), 4))
s05 = comp[(comp.store_id == "S05") & comp.time_ok]
Q(LV, C, SALES_ALL, "按业务日期，S05 在 2023-01-01 至 2024-12-31 期间有多少天没有任何 completed 订单？", len(set(pd.date_range("2023-01-01", "2024-12-31").date) - set(s05.local_date)), "integer")

# ============================================================ L6 增量与历史数据
LV, C = 6, "增量与历史数据"


def states_at(t):
    return {s: sku_state(s, t) for s in SKU_HIST}


t_mid = datetime(2024, 6, 30, 23, 59, 59, tzinfo=UTC)
sm = {k: v for k, v in states_at(t_mid).items() if v}
Q(LV, C, [F_CDC], "回放变更日志：截至 2024-06-30 23:59:59（UTC），处于存在状态（未被删除）的 SKU 有多少个？", len(sm), "integer")
Q(LV, C, [F_CDC], "回放变更日志：截至 2024-06-30 23:59:59（UTC），存在的 SKU 的平均标价是多少？保留2位小数。", rnd(np.mean([v["price_cny"] for v in sm.values()]), 2))
s23 = {k: v for k, v in states_at(datetime(2023, 12, 31, 23, 59, 59, tzinfo=UTC)).items() if v}
Q(LV, C, [F_CDC], "回放变更日志：截至 2023-12-31 23:59:59（UTC），各类目分别有多少个存在的 SKU？键为 category。", dict(Counter(v["category"] for v in s23.values())), "dict")
pchg = Counter(e["sku"] for e in cdc if e["op"] == "u" and e["before"]["price_cny"] != e["after"]["price_cny"])
Q(LV, C, [F_CDC], "价格（price_cny）发生变化的更新事件一共有多少次？", sum(pchg.values()), "integer")
Q(LV, C, [F_CDC], "价格变化次数达到 8 次及以上的 SKU 有多少个？", sum(1 for v in pchg.values() if v >= 8), "integer")
Q(LV, C, [F_CDC], "通过更新事件（op = u，且 before 与 after 的 category 不同）改变过类目的 SKU 有多少个？", len({e["sku"] for e in cdc if e["op"] == "u" and e["before"]["category"] != e["after"]["category"]}), "integer")
scd = []
for sku, h in SKU_HIST.items():
    cur = None
    for ts, after in h:
        if after is None:
            if cur:
                cur["valid_to"] = ts
                scd.append(cur)
                cur = None
            continue
        if cur is None or after["price_cny"] != cur["price_cny"]:
            if cur:
                cur["valid_to"] = ts
                scd.append(cur)
            cur = {"sku": sku, "price_cny": after["price_cny"], "valid_from": ts, "valid_to": None}
    if cur:
        scd.append(cur)
scd = pd.DataFrame(scd).sort_values(["sku", "valid_from"])
fmt = lambda t: "" if t is None or pd.isna(t) else pd.Timestamp(t).strftime("%Y-%m-%d %H:%M:%S")
scd_out = pd.DataFrame({"sku": scd.sku, "price_cny": scd.price_cny, "valid_from": scd.valid_from.map(fmt), "valid_to": scd.valid_to.map(fmt)})
Q(LV, C, [F_CDC], "生成价格历史拉链表 sku_price_history.csv，列依次为 sku,price_cny,valid_from,valid_to。规则：SKU 首次出现、重新创建或价格变化时开始一个新版本；"
  "只有类目等其他字段变化时不开新版本；删除时结束当前版本；valid_to 为下一版本的开始时间或删除时间，当前仍有效的版本留空；时间为 UTC，格式 YYYY-MM-DD HH:MM:SS。按 sku、valid_from 升序。",
  "sku_price_history.csv", "csv", (scd_out, ["sku", "valid_from"], {"price_cny": .001}))
PIT = "（标价取下单时刻该 SKU 在变更日志中的 price_cny；只看 2024 年新系统中国门店 S01–S04 最终 completed 订单的明细）"
FPIT = [F_API, F_CDC, F_ST]
Q(LV, C, FPIT, "成交单价高于下单时刻标价的明细有多少行？" + PIT, int((icn.unit_price > icn.list_price_cny).sum()), "integer")
Q(LV, C, FPIT, "平均折扣深度 = 1 − Σ(qty × unit_price) ÷ Σ(qty × 下单时刻标价) 是多少？保留4位小数。" + PIT, rnd(1 - (icn.qty * icn.unit_price).sum() / (icn.qty * icn.list_price_cny).sum(), 4))
Q(LV, C, FPIT, "下单时刻在变更日志中不存在（未创建或已删除）的 SKU 出现在多少行明细中？" + PIT, 0, "integer")
Q(LV, C, FPIT, "按下单时刻标价计算的标价总额 Σ(qty × 标价) 是多少？保留2位小数。" + PIT, rnd((icn.qty * icn.list_price_cny).sum(), 2))
ta = top1((icn.qty * icn.unit_price).groupby(icn.cat_t).sum())
tb = top1((icn.qty * icn.unit_price).groupby(icn.cat0).sum())
Q(LV, C, FPIT, "按销售额（qty × unit_price）汇总类目，分别按“下单时刻的类目”和“2023-01-01 初始快照中的类目”归类，销售额第一的类目各是什么？用 \"下单时刻类目|初始快照类目\" 格式给出。" + PIT, f"{ta}|{tb}", "string")
au = Ac[Ac.currency == "USD"]
v_bd = (au.net * au.fx).sum()
v_utc = sum(n * fx_at(u.date()) for n, u in zip(au.net, au.utc))
Q(LV, C, [F_API, F_ST, F_FX], "2024 年新系统美国门店 completed 订单净额按业务日期汇率换算为人民币，合计是多少？保留2位小数。", rnd(v_bd, 2))
Q(LV, C, [F_API, F_ST, F_FX], "2024 年新系统美国门店 completed 订单净额换算为人民币，分别按业务日期和按 UTC 日期取汇率（其余汇率规则同 README），两种合计之差（按 UTC 日期 − 按业务日期）是多少？保留2位小数。", rnd(v_utc - v_bd, 2))


def mrr_at(day):
    s = subs[subs.event_date <= day]
    last = s.groupby("account_id").tail(1)
    return last.set_index("account_id")


m_mid, m_end = mrr_at(pd.Timestamp("2024-06-30")), mrr_at(pd.Timestamp("2024-12-31"))
Q(LV, C, [F_SUB], "2024-06-30 日终全部账户的 MRR 合计是多少（美元）？", int(m_mid.mrr_after.sum()), "integer")
Q(LV, C, [F_SUB], "2024-12-31 日终全部账户的 MRR 合计是多少（美元）？", int(m_end.mrr_after.sum()), "integer")
Q(LV, C, [F_SUB], "2024-12-31 日终 MRR 大于 0 的账户有多少个？", int((m_end.mrr_after > 0).sum()), "integer")
Q(LV, C, [F_API], "如果不按 updated_at 取每个订单的最新记录，只是去掉完全重复的行，然后数 status 为 completed 的行，会比正确的 completed 订单数多出多少？", int(o.cancelled_later.sum()), "integer")
Q(LV, C, [F_API, F_ST], "2024 年新系统中国门店（S01–S04）completed 订单的净额合计是多少？保留2位小数。", rnd(Ac[Ac.store_id.isin(CN)].net.sum(), 2))
dig = set(items[(items.status == "completed") & (items.cat_t == "数码配件")].order_id)
Q(LV, C, FPIT, "2024 年新系统最终 completed 的订单中（全部门店），至少有一行明细的商品在下单时刻属于“数码配件”类目的订单有多少个？", len(dig), "integer")

# ============================================================ L7 业务指标
LV, C = 7, "业务指标"
months = pd.period_range("2024-01", "2024-12", freq="M")
accs = sorted(subs.account_id.unique())
first_pos = subs[subs.mrr_after > 0].groupby("account_id").event_date.min()


def snap(day):
    s = mrr_at(day).mrr_after
    return s.reindex(accs).fillna(0)


wf = []
prev = snap(pd.Timestamp("2023-12-31"))
for m in months:
    endd = m.to_timestamp(how="end").normalize()
    curv = snap(endd)
    pd_ = pd.Timestamp(m.start_time) - pd.Timedelta(days=1)
    row = {"month": str(m), "start_mrr": prev.sum(), "new": 0, "expansion": 0, "contraction": 0, "churn": 0, "reactivation": 0}
    for a in accs:
        p, c = prev[a], curv[a]
        if p == 0 and c > 0:
            ever = a in first_pos.index and first_pos[a] <= pd_
            row["reactivation" if ever else "new"] += c
        elif p > 0 and c == 0:
            row["churn"] -= p
        elif p > 0 and c > 0:
            row["expansion" if c > p else "contraction"] += (c - p) if c != p else 0
    row["end_mrr"] = curv.sum()
    assert abs(row["start_mrr"] + row["new"] + row["expansion"] + row["contraction"] + row["churn"] + row["reactivation"] - row["end_mrr"]) < 1e-6
    wf.append(row)
    prev = curv
wf = pd.DataFrame(wf)
WFDEF = ("（按月末日终快照比较：上月末 MRR 为 p、本月末为 c。p = 0 且 c > 0：若该账户在上月末之前（含）从未有过正 MRR 记为 new，否则记为 reactivation；"
         "p > 0 且 c = 0 记为 churn（金额 −p）；p、c 都大于 0 时 c > p 记为 expansion（c − p），c < p 记为 contraction（c − p，为负数）。月内的中间变化不计。）")
Q(LV, C, [F_SUB], "生成 2024 年 MRR 瀑布表 mrr_waterfall_2024.csv，每月一行，列依次为 month,start_mrr,new,expansion,contraction,churn,reactivation,end_mrr（month 形如 2024-01，金额为美元整数）。" + WFDEF,
  "mrr_waterfall_2024.csv", "csv", (wf, ["month"], {c: 1e-6 for c in wf.columns if c != "month"}))
Q(LV, C, [F_SUB], "2024 年全年 new MRR 合计是多少（美元）？" + WFDEF, int(wf.new.sum()), "integer")
Q(LV, C, [F_SUB], "2024 年全年 churn MRR 合计是多少（美元，负数）？" + WFDEF, int(wf.churn.sum()), "integer")
m23 = snap(pd.Timestamp("2023-12-31"))
m24 = snap(pd.Timestamp("2024-12-31"))
base = m23[m23 > 0]
Q(LV, C, [F_SUB], "净收入留存率 NRR = 2023-12-31 日终 MRR > 0 的账户在 2024-12-31 的 MRR 合计 ÷ 这些账户在 2023-12-31 的 MRR 合计，是多少？保留4位小数。", rnd(m24[base.index].sum() / base.sum(), 4))
Q(LV, C, [F_SUB], "毛收入留存率 GRR = Σ min(账户 2024-12-31 MRR, 账户 2023-12-31 MRR) ÷ Σ 账户 2023-12-31 MRR（只看 2023-12-31 MRR > 0 的账户），是多少？保留4位小数。",
  rnd(np.minimum(m24[base.index], base).sum() / base.sum(), 4))
Q(LV, C, [F_SUB], "2023-12-31 日终 MRR > 0 的账户中，2024-12-31 日终 MRR 为 0 的比例（logo churn）是多少？保留4位小数。", rnd((m24[base.index] == 0).mean(), 4))
Q(LV, C, [F_SUB], "2024 年 SaaS Quick Ratio = (new + expansion + reactivation) ÷ |churn + contraction|（12 个月合计）是多少？保留4位小数。" + WFDEF,
  rnd((wf.new.sum() + wf.expansion.sum() + wf.reactivation.sum()) / abs(wf.churn.sum() + wf.contraction.sum()), 4))
Q(LV, C, [F_SUB], "2024-12-31 日终的 ARPA（MRR 合计 ÷ MRR > 0 的账户数）是多少？保留2位小数。", rnd(m24.sum() / (m24 > 0).sum(), 2))
wf["net"] = wf.end_mrr - wf.start_mrr
Q(LV, C, [F_SUB], "2024 年哪些月份的 MRR 净变动（月末 − 上月末）为负？以 JSON 数组按月份升序给出（形如 2024-03）。", wf[wf.net < 0].month.tolist(), "list")
pl = m_end[m_end.mrr_after > 0].groupby("plan").mrr_after.sum()
Q(LV, C, [F_SUB], "2024-12-31 日终各套餐（按账户最后一个事件的 plan）的 MRR 合计是多少（美元）？键为 plan。", {k: int(v) for k, v in pl.items()}, "dict")
inv_p, inv_s = T["inv_p"], T["inv_s"]
fifo_cogs, wac_cogs, end_qty, end_val, oldest, stockout = {}, {}, {}, {}, [], 0
open_val = (inv_p[inv_p.received_at == "2023-12-31"].qty * inv_p[inv_p.received_at == "2023-12-31"].unit_cost).sum()
for sku in sorted(inv_p.sku.unique()):
    lots = inv_p[inv_p.sku == sku].sort_values(["received_at", "lot_id"])
    sh = inv_s[inv_s.sku == sku].groupby("shipped_at").qty.sum()
    q_fifo, cogs_f, qty_w, val_w, cogs_w = [], 0.0, 0, 0.0, 0.0
    rec_by = {d: g for d, g in lots.groupby("received_at")}
    for d in pd.date_range("2023-12-31", "2024-12-31"):
        if d in rec_by:
            for r in rec_by[d].itertuples():
                q_fifo.append([r.qty, r.unit_cost, r.received_at])
                qty_w += r.qty
                val_w += r.qty * r.unit_cost
        if d.year == 2024 and sum(x[0] for x in q_fifo) == 0:
            stockout += 1
        need = int(sh.get(d, 0))
        if need:
            avg = val_w / qty_w
            cogs_w += need * avg
            val_w -= need * avg
            qty_w -= need
            while need:
                take = min(need, q_fifo[0][0])
                cogs_f += take * q_fifo[0][1]
                q_fifo[0][0] -= take
                need -= take
                if q_fifo[0][0] == 0:
                    q_fifo.pop(0)
    fifo_cogs[sku], wac_cogs[sku] = cogs_f, cogs_w
    end_qty[sku] = sum(x[0] for x in q_fifo)
    end_val[sku] = sum(x[0] * x[1] for x in q_fifo)
    oldest += [x[2] for x in q_fifo if x[0] > 0]
INVDEF = "（同一天先入库后出库；2023-12-31 入库的批次为期初库存）"
FI = [F_INVP, F_INVS]
Q(LV, C, FI, "按先进先出法，2024 年销货成本合计是多少？保留2位小数。" + INVDEF, rnd(sum(fifo_cogs.values()), 2))
Q(LV, C, FI, "按先进先出法，2024-12-31 期末库存价值是多少？保留2位小数。" + INVDEF, rnd(sum(end_val.values()), 2))
Q(LV, C, FI, "按移动加权平均法（每次入库后重新计算平均单位成本，出库按当时平均成本结转，不做中间四舍五入），2024 年销货成本合计是多少？保留2位小数。" + INVDEF, rnd(sum(wac_cogs.values()), 2))
Q(LV, C, FI, "先进先出法与移动加权平均法的 2024 年销货成本之差（绝对值）最大的 SKU 是哪个？" + INVDEF, top1(pd.Series({k: abs(fifo_cogs[k] - wac_cogs[k]) for k in fifo_cogs})), "string")
Q(LV, C, FI, "按先进先出法，2024-12-31 期末仍有剩余数量的批次中，最早的入库日期是哪天？格式 YYYY-MM-DD。" + INVDEF, min(oldest).strftime("%Y-%m-%d"), "string")
Q(LV, C, FI, "2024 年库存周转率 = 先进先出销货成本 ÷ ((期初库存价值 + 期末库存价值) ÷ 2) 是多少？保留4位小数。" + INVDEF, rnd(sum(fifo_cogs.values()) / ((open_val + sum(end_val.values())) / 2), 4))
Q(LV, C, FI, "2024 年“缺货 SKU-天”有多少个？缺货指某 SKU 在某天入库之后、出库之前的库存为 0。" + INVDEF, stockout, "integer")
s_raw = pd.read_csv(DATA / F_INVS, dtype=str)
Q(LV, C, [F_INVS], "shipments.csv 中完全重复的多余行有多少？", len(s_raw) - len(s_raw.drop_duplicates()), "integer")
a24 = Ac.copy()
share = a24.groupby("store_id").net_cny.sum() / a24.net_cny.sum()
ts_ = top1(share)
Q(LV, C, SALES_ALL, "2024 年各门店 completed 订单净额（换算为人民币）占全部门店的比例中，最高的是哪家门店、占比多少？以 JSON 对象给出，字段为 store_id、share（保留4位小数）。",
  {"store_id": ts_, "share": rnd(share[ts_], 4)}, "json", tols={"share": 4})
Q(LV, C, SALES_ALL, "2024 年 completed 订单按渠道的客单价（净额换算为人民币后的合计 ÷ 订单数）是多少？键为 channel，保留2位小数。", dr(a24.groupby("channel").net_cny.sum() / a24.groupby("channel").size(), 2), "dict")

# ============================================================ L8 统计推断进阶
LV, C = 8, "统计推断进阶"
ab = T["abx"]
g = ab.groupby("variant")
Q(LV, C, [F_AB], "A、B 两组的总体转化率分别是多少？键为 A、B，保留4位小数。", dr(g.converted.mean(), 4), "dict")
sg = ab.groupby(["segment", "variant"]).converted.mean()
Q(LV, C, [F_AB], "按 segment 分层后各组的转化率是多少？键形如 new_A、new_B、returning_A、returning_B，保留4位小数。", {f"{s}_{v}": rnd(x, 4) for (s, v), x in sg.items()}, "dict")
simpson = all(sg[(s, "B")] > sg[(s, "A")] for s in ["new", "returning"]) and g.converted.mean()["B"] < g.converted.mean()["A"]
Q(LV, C, [F_AB], "B 组是否在每个 segment 内的转化率都高于 A 组、但总体转化率低于 A 组？回答“是”或“否”。", "是" if simpson else "否", "string")
wA = ab[ab.variant == "A"].segment.value_counts(normalize=True)
Q(LV, C, [F_AB], "以 A 组的 segment 构成为权重，对 B 组做直接标准化后的转化率 Σ_s w_s(A) × p_s(B) 是多少？保留4位小数。", rnd(sum(wA[s] * sg[(s, "B")] for s in wA.index), 4))
num = den = 0
for s in ["new", "returning"]:
    na_ = ((ab.segment == s) & (ab.variant == "A")).sum()
    nb_ = ((ab.segment == s) & (ab.variant == "B")).sum()
    w = na_ * nb_ / (na_ + nb_)
    num += w * (sg[(s, "B")] - sg[(s, "A")])
    den += w
mh = num / den
Q(LV, C, [F_AB], "按 segment 分层的 Mantel-Haenszel 风险差 Σ_s w_s (p_sB − p_sA) ÷ Σ_s w_s（w_s = n_sA × n_sB ÷ (n_sA + n_sB)）是多少？保留4位小数。", rnd(mh, 4))
theta = np.cov(ab.post_revenue, ab.pre_revenue, ddof=1)[0, 1] / np.var(ab.pre_revenue, ddof=1)
adj = ab.post_revenue - theta * (ab.pre_revenue - ab.pre_revenue.mean())
CUP = "CUPED：θ = cov(post_revenue, pre_revenue) ÷ var(pre_revenue)（全部用户合并计算），调整后指标 = post_revenue − θ × (pre_revenue − pre_revenue 的均值）。"
Q(LV, C, [F_AB], CUP + "θ 是多少？保留4位小数。", rnd(theta, 4))
Q(LV, C, [F_AB], CUP + "调整后指标的组间均值差（B − A）是多少？保留4位小数。", rnd(adj[ab.variant == "B"].mean() - adj[ab.variant == "A"].mean(), 4))
Q(LV, C, [F_AB], "未调整的 post_revenue 组间均值差（B − A）是多少？保留4位小数。", rnd(ab[ab.variant == "B"].post_revenue.mean() - ab[ab.variant == "A"].post_revenue.mean(), 4))
Q(LV, C, [F_AB], CUP + "方差缩减比例 1 − var(调整后指标) ÷ var(post_revenue) 是多少？保留4位小数。", rnd(1 - adj.var() / ab.post_revenue.var(), 4))
cp = stats.ttest_ind(adj[ab.variant == "B"], adj[ab.variant == "A"], equal_var=False).pvalue
Q(LV, C, [F_AB], CUP + "对调整后指标做 Welch t 检验（B vs A），双侧 p 值是多少？保留4位小数。", rnd(cp, 4))
did = T["did"]
post = did.week >= 11
mm_ = did.assign(post=post).groupby(["treated", "post"]).sales.mean()
Q(LV, C, [F_DID], "双重差分（2×2）：(处理组后期均值 − 处理组前期均值) − (对照组后期均值 − 对照组前期均值)，后期为 week ≥ 11，是多少？保留2位小数。",
  rnd((mm_[(1, True)] - mm_[(1, False)]) - (mm_[(0, True)] - mm_[(0, False)]), 2))
lg = did.assign(post=post, ls=np.log(did.sales)).groupby(["treated", "post"]).ls.mean()
Q(LV, C, [F_DID], "对 ln(sales) 做同样的 2×2 双重差分，结果是多少？保留4位小数。", rnd((lg[(1, True)] - lg[(1, False)]) - (lg[(0, True)] - lg[(0, False)]), 4))
pre_ = did[did.week <= 10]
X = np.column_stack([np.ones(len(pre_)), pre_.treated, pre_.week, pre_.treated * pre_.week])
beta = np.linalg.lstsq(X, np.log(pre_.sales), rcond=None)[0]
Q(LV, C, [F_DID], "平行趋势检验：只用 week 1–10，对 ln(sales) 做 OLS 回归 ln(sales) ~ 1 + treated + week + treated × week，交互项系数是多少？保留4位小数。", rnd(beta[3], 4))
Dm = ((did.treated == 1) & post).astype(float)
Xs = pd.get_dummies(did.store_id, drop_first=True, dtype=float)
Xw = pd.get_dummies(did.week, prefix="w", drop_first=True, dtype=float)
X2 = np.column_stack([np.ones(len(did)), Dm, Xs.values, Xw.values])
b2 = np.linalg.lstsq(X2, np.log(did.sales), rcond=None)[0]
Q(LV, C, [F_DID], "双向固定效应回归 ln(sales) ~ D + 门店固定效应 + 周固定效应（D = 处理组且 week ≥ 11 时为 1），D 的系数是多少？保留4位小数。", rnd(b2[1], 4))
mmx = T["mm"]
ms_ = [f"m{k:02d}" for k in range(1, 13)]
pv = pd.Series({m: stats.ttest_ind(mmx[mmx.variant == "B"][m], mmx[mmx.variant == "A"][m], equal_var=False).pvalue for m in ms_})
MT = "对 m01–m12 分别做 Welch t 检验（B vs A，双侧）。"
Q(LV, C, [F_MM], MT + "未校正时 p < 0.05 的指标有哪些？以 JSON 数组按指标名升序给出。", sorted(pv[pv < .05].index), "list")
Q(LV, C, [F_MM], MT + "Bonferroni 校正（α = 0.05）后显著的指标有哪些？以 JSON 数组按指标名升序给出。", sorted(pv[pv < .05 / 12].index), "list")
rk = pv.sort_values()
mlist = len(rk)
thr = [rk.iloc[i] <= (i + 1) / mlist * .05 for i in range(mlist)]
kmax = max([i for i, t in enumerate(thr) if t], default=-1)
Q(LV, C, [F_MM], MT + "Benjamini–Hochberg 校正（q = 0.05）后显著的指标有哪些？以 JSON 数组按指标名升序给出。", sorted(rk.index[:kmax + 1]), "list")
qv = (rk * mlist / np.arange(1, mlist + 1))[::-1].cummin()[::-1].clip(upper=1)
Q(LV, C, [F_MM], MT + "m10 的 Benjamini–Hochberg 调整后 p 值（q 值）是多少？保留4位小数。", rnd(qv["m10"], 4))
X3 = np.column_stack([np.ones(len(ab)), (ab.variant == "B"), (ab.segment == "new"), (ab.variant == "B") & (ab.segment == "new")]).astype(float)
b3 = np.linalg.lstsq(X3, ab.post_revenue, rcond=None)[0]
Q(LV, C, [F_AB], "OLS 回归 post_revenue ~ 1 + B + new + B × new（B、new 为 0/1 指示变量），交互项系数是多少？保留4位小数。", rnd(b3[3], 4))
p1 = sg[("returning", "A")]
p2 = p1 + .01
n_ = math.ceil((stats.norm.ppf(.975) + stats.norm.ppf(.8)) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2)) / (p2 - p1) ** 2)
Q(LV, C, [F_AB], "以 A 组 returning 用户的转化率为 p1、p2 = p1 + 0.01，双侧 α = 0.05、功效 0.8，每组所需样本量 n = (z_{0.975} + z_{0.8})² × (p1(1−p1) + p2(1−p2)) ÷ (p2 − p1)²，向上取整，是多少？", n_, "integer")

# ============================================================ L9 归因与分解
LV, C = 9, "归因与分解"
CHS = ["paid_search", "social", "email", "affiliate", "display", "direct"]
cv_by = defaultdict(list)
for r in cvs.sort_values("ts").itertuples():
    cv_by[r.user_id].append(r)
tp_rows = defaultdict(list)
for r in tps.itertuples():
    tp_rows[r.user_id].append((r.ts, r.channel))
credit = {m: defaultdict(float) for m in ["first", "last", "linear", "decay", "position"]}
paths, unattr, nconv = [], 0, 0
for u, cl_ in cv_by.items():
    prev_t = None
    for c in cl_:
        nconv += 1
        lo = c.ts - pd.Timedelta(days=30)
        tps_ = [(t, ch) for t, ch in tp_rows.get(u, []) if t <= c.ts and t >= lo and (prev_t is None or t > prev_t)]
        prev_t = c.ts
        if not tps_:
            unattr += 1
            for m in credit:
                credit[m]["unattributed"] += c.revenue
            continue
        chs = [ch for _, ch in tps_]
        paths.append(">".join(chs))
        n = len(chs)
        credit["first"][chs[0]] += c.revenue
        credit["last"][chs[-1]] += c.revenue
        for ch in chs:
            credit["linear"][ch] += c.revenue / n
        w = np.array([.5 ** ((c.ts - t).total_seconds() / 86400 / 7) for t, _ in tps_])
        for ch, wi in zip(chs, w / w.sum()):
            credit["decay"][ch] += c.revenue * wi
        if n == 1:
            credit["position"][chs[0]] += c.revenue
        elif n == 2:
            credit["position"][chs[0]] += c.revenue * .5
            credit["position"][chs[1]] += c.revenue * .5
        else:
            credit["position"][chs[0]] += c.revenue * .4
            credit["position"][chs[-1]] += c.revenue * .4
            for ch in chs[1:-1]:
                credit["position"][ch] += c.revenue * .2 / (n - 2)
ATT = ("归因窗口：一笔转化的候选触点为同一用户、时间在 (该用户上一笔转化时间, 本笔转化时间] 之间且不早于本笔转化前 30 天（含）的触点，按时间排序。"
       "没有候选触点的转化记为 unattributed。答案为 JSON 对象，包含全部 6 个渠道和 unattributed，没有归因收入的记为 0。")
FA = [F_TP, F_CV]


def cd(m):
    return {k: rnd(credit[m].get(k, 0), 2) for k in CHS + ["unattributed"]}


Q(LV, C, FA, ATT + "首次触点归因（全部收入归第一个触点）下，各渠道的归因收入是多少？保留2位小数。", cd("first"), "dict")
Q(LV, C, FA, ATT + "末次触点归因下，各渠道的归因收入是多少？保留2位小数。", cd("last"), "dict")
Q(LV, C, FA, ATT + "线性归因（收入平均分给每个触点）下，各渠道的归因收入是多少？保留2位小数。", cd("linear"), "dict")
Q(LV, C, FA, ATT + "时间衰减归因（触点权重 = 0.5^(距转化天数 ÷ 7)，天数可为小数，权重归一化后分配收入）下，各渠道的归因收入是多少？保留2位小数。", cd("decay"), "dict")
Q(LV, C, FA, ATT + "位置归因（1 个触点得 100%；2 个触点各 50%；3 个及以上首末各 40%，中间触点平分 20%）下，各渠道的归因收入是多少？保留2位小数。", cd("position"), "dict")
ATT0 = ATT.split("答案为")[0]
Q(LV, C, FA, ATT0 + "unattributed 的转化笔数占全部转化笔数的比例是多少？保留4位小数。", rnd(unattr / nconv, 4))
Q(LV, C, FA, ATT0 + "有候选触点的转化，平均有多少个候选触点？保留4位小数。", rnd(np.mean([p.count(">") + 1 for p in paths]), 4))
Q(LV, C, FA, ATT0 + "有候选触点的转化中，最常见的渠道路径是什么？路径为按时间排序的渠道名，用 \">\" 连接（如 social>email）。", top1(pd.Series(paths).value_counts()), "string")
sp = T["spend"].groupby("channel").spend.sum()
Q(LV, C, FA + [F_SP], ATT0 + "按线性归因收入计算 ROAS（归因收入 ÷ 全年投放花费），在有投放花费的渠道中 ROAS 最高的是哪个？", top1(pd.Series({k: credit["linear"][k] / sp[k] for k in sp.index})), "string")
Q(LV, C, FA, ATT0 + "首次触点归因收入减去末次触点归因收入，差值最大的渠道是哪个？", top1(pd.Series({k: credit["first"].get(k, 0) - credit["last"].get(k, 0) for k in CHS})), "string")
ac = Ac.copy()
ac["m"] = ac.ym
g78 = ac[ac.m.isin(["2024-07", "2024-08"])]
tot = g78.groupby("m").net_cny.sum()
RC = "（2024 年新系统最终 completed 订单，按业务月份，净额换算为人民币）"
Q(LV, C, SALES_ALL, "2024 年 8 月相比 7 月，订单净额合计变化了多少（8 月 − 7 月）？保留2位小数。" + RC, rnd(tot["2024-08"] - tot["2024-07"], 2))
cell = g78.groupby(["store_id", "channel", "m"]).net_cny.agg(["sum", "size"]).unstack("m").fillna(0)
cd_ = cell[("sum", "2024-08")] - cell[("sum", "2024-07")]
worst = top1(cd_, smallest=True)
Q(LV, C, SALES_ALL, "按“门店 × 渠道”分解 8 月相比 7 月的净额变化，贡献最负的组合是哪个？用 \"store_id|channel\" 格式给出。" + RC, f"{worst[0]}|{worst[1]}", "string")
Q(LV, C, SALES_ALL, "贡献最负的“门店 × 渠道”组合，8 月相比 7 月的净额变化是多少？保留2位小数。" + RC, rnd(cd_[worst], 2))
n7, n8 = cell.loc[worst, ("size", "2024-07")], cell.loc[worst, ("size", "2024-08")]
aov7, aov8 = cell.loc[worst, ("sum", "2024-07")] / n7, cell.loc[worst, ("sum", "2024-08")] / n8
DEC = "把该组合的变化拆为订单量效应 = (N8 − N7) × AOV7 与客单价效应 = N8 × (AOV8 − AOV7)，N 为订单数，AOV 为客单价（净额 ÷ 订单数）。"
Q(LV, C, SALES_ALL, "对贡献最负的“门店 × 渠道”组合，" + DEC + "订单量效应是多少？保留2位小数。" + RC, rnd((n8 - n7) * aov7, 2))
Q(LV, C, SALES_ALL, "剔除贡献最负的“门店 × 渠道”组合后，其余组合 8 月相比 7 月的净额变化合计是多少？保留2位小数。" + RC, rnd(cd_.sum() - cd_[worst], 2))
it78 = icn.merge(o[["order_id", "ym"]], on="order_id")
it78 = it78[it78.ym.isin(["2024-07", "2024-08"])]
pq = it78.assign(s=it78.qty * it78.unit_price).groupby(["cat_t", "ym"]).agg(s=("s", "sum"), q=("qty", "sum")).unstack("ym").fillna(0)
P7, P8 = pq[("s", "2024-07")] / pq[("q", "2024-07")], pq[("s", "2024-08")] / pq[("q", "2024-08")]
Q7, Q8 = pq[("q", "2024-07")], pq[("q", "2024-08")]
PVM = "（中国门店 S01–S04 最终 completed 订单的明细，按下单时刻类目；P_c 为类目平均成交单价 = 销售额 ÷ 件数，Q_c 为件数，销售额 = qty × unit_price）"
Q(LV, C, FPIT, "8 月相比 7 月的价格效应 Σ_c (P8_c − P7_c) × Q8_c 是多少？保留2位小数。" + PVM, rnd(((P8 - P7) * Q8).sum(), 2))
Q(LV, C, FPIT, "8 月相比 7 月的数量效应 Σ_c (Q8_c − Q7_c) × P7_c 是多少？保留2位小数。" + PVM, rnd(((Q8 - Q7) * P7).sum(), 2))
mt_ = ac.groupby("m").net_cny.sum()
chg = (mt_ / mt_.shift(1) - 1).loc["2024-02":]
Q(LV, C, SALES_ALL, "2024 年 2–12 月中，订单净额相对上月下降比例最大的是哪个月？格式 YYYY-MM。" + RC, top1(chg, smallest=True), "string")
s1 = ac[ac.store_id == "S01"]
sh_ = s1.groupby(["m", "channel"]).net_cny.sum().unstack().fillna(0)
shr = sh_.div(sh_.sum(axis=1), axis=0)
Q(LV, C, SALES_ALL, "S01 的 app 渠道净额占 S01 全部净额的比例，8 月比 7 月变化了多少个百分点（8 月 − 7 月）？保留2位小数。" + RC, rnd((shr.loc["2024-08", "app"] - shr.loc["2024-07", "app"]) * 100, 2))
s1a = s1[s1.channel == "app"]
wk = s1a.groupby(s1a.local.map(lambda x: x.isocalendar()[1])).size().reindex(range(1, 53), fill_value=0)
first_drop = next(w for w in range(9, 53) if wk[w] < .5 * wk[w - 8:w].mean())
Q(LV, C, SALES_ALL, "按 ISO 周（门店本地日期）统计 2024 年 S01 app 渠道的 completed 订单数，从第 9 周起，第一个订单数低于前 8 周平均值 50% 的是哪一周？格式 2024-Wxx（两位周数）。", f"2024-W{first_drop:02d}", "string")

# ============================================================ L10 综合分析
LV, C = 10, "综合分析"
J = "以 JSON 对象给出，字段名与题目一致。"
Q(LV, C, SALES_ALL, "2024 年新系统经营摘要：orders（completed 订单数）、gmv_cny（completed 订单净额换算为人民币的合计，保留2位小数）、aov_cny（gmv_cny ÷ orders，保留2位小数）、cancel_rate（最终 cancelled 订单数 ÷ 全部订单数，保留4位小数）。" + J,
  {"orders": len(Ac), "gmv_cny": rnd(Ac.net_cny.sum(), 2), "aov_cny": rnd(Ac.net_cny.sum() / len(Ac), 2), "cancel_rate": rnd((A.status == "cancelled").mean(), 4)}, "json", tols={"gmv_cny": 2, "aov_cny": 2, "cancel_rate": 4})
mk = comp[comp.time_ok].groupby("ym").agg(orders=("order_id", "size"), gmv_cny=("net_cny", "sum"), active_members=("member_id", "nunique")).reset_index()
mk["aov_cny"] = mk.gmv_cny / mk.orders
mk_out = pd.DataFrame({"month": mk.ym, "orders": mk.orders, "gmv_cny": mk.gmv_cny.round(2), "aov_cny": mk.aov_cny.round(2), "active_members": mk.active_members})
Q(LV, C, SALES_ALL, "生成 2023-01 至 2024-12 的月度经营表 monthly_kpi.csv（新旧系统合并），每月一行，列依次为 month,orders,gmv_cny,aov_cny,active_members："
  "按业务月份统计 completed 订单数、净额换算为人民币的合计、客单价、有订单的不同 member_id 数（非会员订单不计入 active_members）。下单时间无效的订单不计。金额保留2位小数，按 month 升序。",
  "monthly_kpi.csv", "csv", (mk_out, ["month"], {"orders": 1e-9, "gmv_cny": .011, "aov_cny": .011, "active_members": 1e-9}))
rc_cny = rec[rec.currency == "CNY"]
exp_c = rc_cny.net.sum()
col_c = (rc_cny.paid - rc_cny.reversed - rc_cny.refunded).sum()
Q(LV, C, [F_API, F_PAY, F_REF], "人民币订单对账摘要（只看 2024 年新系统最终 completed 的 CNY 订单）：expected（订单净额合计）、collected（这些订单的 SUCCESS 合计 − REVERSED 合计 − 退款合计）、gap（expected − collected），均保留2位小数。" + J,
  {"expected": rnd(exp_c, 2), "collected": rnd(col_c, 2), "gap": rnd(exp_c - col_c, 2)}, "json", tols={"expected": 2, "collected": 2, "gap": 2})
sr = rec.groupby("store_id").agg(completed_orders=("order_id", "size"), expected=("net", "sum"),
                                 collected=("paid", "sum"), rv=("reversed", "sum"), rf=("refunded", "sum")).reset_index()
sr["collected"] = sr.collected - sr.rv - sr.rf
sr["missing_orders"] = sr.store_id.map(rec[rec.result == "missing"].groupby("store_id").size()).fillna(0).astype(int)
sr["double_orders"] = sr.store_id.map(rec[rec.result == "double"].groupby("store_id").size()).fillna(0).astype(int)
sr_out = pd.DataFrame({"store_id": sr.store_id, "completed_orders": sr.completed_orders, "expected": sr.expected.round(2), "collected": sr.collected.round(2),
                       "missing_orders": sr.missing_orders, "double_orders": sr.double_orders})
Q(LV, C, [F_API, F_PAY, F_REF], "生成门店对账表 store_recon.csv（只看 2024 年新系统最终 completed 的订单），每家门店一行，列依次为 store_id,completed_orders,expected,collected,missing_orders,double_orders。"
  "expected 为订单净额合计，collected 为这些订单的 SUCCESS 合计 − REVERSED 合计 − 退款合计（均为原币种，保留2位小数）；missing_orders 为没有 SUCCESS 记录的订单数，double_orders 为 SUCCESS 记录 ≥ 2 条的订单数。按 store_id 升序。",
  "store_recon.csv", "csv", (sr_out, ["store_id"], {"completed_orders": 1e-9, "expected": .011, "collected": .011, "missing_orders": 1e-9, "double_orders": 1e-9}))
Q(LV, C, [F_IOT, F_DEV], "传感器健康摘要：fahrenheit_devices（以华氏度上报的设备，按 device_id 升序的数组）、worst_completeness_device（2024 年 11 月 UTC 有效读数最少的设备）、longest_outage_hours（最长断线小时数，保留2位小数；断线 = 同一设备相邻读数间隔超过 1 小时）。" + J,
  {"fahrenheit_devices": T["f_devs"], "worst_completeness_device": top1(nov.groupby("device_id").size(), smallest=True), "longest_outage_hours": rnd(iu.gap.max() / 3600, 2)}, "json", tols={"longest_outage_hours": 2})
sh_dev = iv[(iv.site == "上海仓") & (iv.ts.dt.month == 11)]
ddf = sh_dev.groupby(["device_id", sh_dev.ts.dt.strftime("%Y-%m-%d")]).temp_c.agg(["size", "mean", "min", "max"]).reset_index()
ddf.columns = ["device_id", "date", "readings", "mean_c", "min_c", "max_c"]
for c in ["mean_c", "min_c", "max_c"]:
    ddf[c] = ddf[c].round(2)
Q(LV, C, [F_IOT, F_DEV], "生成 device_daily.csv：上海仓所有设备在 2024 年 11 月（UTC 日期）每台设备每天一行（只输出当天有有效读数的日期），列依次为 device_id,date,readings,mean_c,min_c,max_c（温度为摄氏度，保留2位小数）。按 device_id、date 升序。" + IVDEF,
  "device_daily.csv", "csv", (ddf, ["device_id", "date"], {"readings": 1e-9, "mean_c": .011, "min_c": .011, "max_c": .011}))
Q(LV, C, [F_AB], "实验结论摘要：overall_diff（B − A 总体转化率差）、mh_diff（按 segment 分层的 Mantel-Haenszel 风险差，权重 n_sA × n_sB ÷ (n_sA + n_sB)）、cuped_diff（CUPED 调整后 post_revenue 的 B − A 均值差，θ 用全部用户合并计算）、cuped_p（调整后指标 Welch t 检验双侧 p 值），均保留4位小数。" + J,
  {"overall_diff": rnd(g.converted.mean()["B"] - g.converted.mean()["A"], 4), "mh_diff": rnd(mh, 4),
   "cuped_diff": rnd(adj[ab.variant == "B"].mean() - adj[ab.variant == "A"].mean(), 4), "cuped_p": rnd(cp, 4)}, "json", tols={"overall_diff": 4, "mh_diff": 4, "cuped_diff": 4, "cuped_p": 4})
Q(LV, C, FA, ATT0 + "归因摘要：top_channel_linear（线性归因收入最高的渠道，不含 unattributed）、top_channel_last（末次触点归因收入最高的渠道，不含 unattributed）、unattributed_share（unattributed 转化笔数占比，保留4位小数）。" + J,
  {"top_channel_linear": top1(pd.Series({k: credit["linear"].get(k, 0) for k in CHS})), "top_channel_last": top1(pd.Series({k: credit["last"].get(k, 0) for k in CHS})),
   "unattributed_share": rnd(unattr / nconv, 4)}, "json", tols={"unattributed_share": 4})
ca = pd.DataFrame({"channel": CHS + ["unattributed"], **{m2: [rnd(credit[m].get(k, 0), 2) for k in CHS + ["unattributed"]] for m, m2 in
                                                         [("first", "first"), ("last", "last"), ("linear", "linear"), ("decay", "time_decay"), ("position", "position")]}})
Q(LV, C, FA, ATT0 + "生成 channel_attribution.csv：6 个渠道和 unattributed 各一行，列依次为 channel,first,last,linear,time_decay,position，分别为首次触点、末次触点、线性、时间衰减（权重 0.5^(距转化天数 ÷ 7)）、位置归因（40/20/40）的归因收入，保留2位小数。",
  "channel_attribution.csv", "csv", (ca, ["channel"], {c: .011 for c in ["first", "last", "linear", "time_decay", "position"]}))
Q(LV, C, SALES_ALL, "GMV 下滑根因摘要（2024 年 8 月相比 7 月）：cell（按“门店 × 渠道”分解后贡献最负的组合，格式 store_id|channel）、delta_cny（该组合净额变化）、volume_effect（该组合的订单量效应 (N8 − N7) × AOV7）、price_effect（该组合的客单价效应 N8 × (AOV8 − AOV7)），其中 N 为该组合的订单数、AOV 为该组合的客单价（净额 ÷ 订单数），金额保留2位小数。" + RC + J,
  {"cell": f"{worst[0]}|{worst[1]}", "delta_cny": rnd(cd_[worst], 2), "volume_effect": rnd((n8 - n7) * aov7, 2), "price_effect": rnd(n8 * (aov8 - aov7), 2)}, "json",
  tols={"delta_cny": 2, "volume_effect": 2, "price_effect": 2})
fo = oc.groupby("key").local_date.min()
c23 = fo[[d.year == 2023 for d in fo]]
coh = pd.DataFrame({"key": c23.index, "cohort": [d.strftime("%Y-%m") for d in c23]})
coh["ret"] = coh.key.isin(y24)
co = coh.groupby("cohort").agg(size=("key", "size"), retained_2024=("ret", "sum")).reset_index()
co["rate"] = (co.retained_2024 / co["size"]).round(4)
Q(LV, C, FMS, RULE + "生成 cohort_2023.csv：按簇的首笔订单月份（只看首单在 2023 年的簇）分组，每月一行，列依次为 cohort,size,retained_2024,rate：size 为簇数，retained_2024 为其中 2024 年有订单的簇数，rate = retained_2024 ÷ size（保留4位小数）。按 cohort 升序。" + OCDEF,
  "cohort_2023.csv", "csv", (co, ["cohort"], {"size": 1e-9, "retained_2024": 1e-9, "rate": 1e-4 + 1e-9}))
Q(LV, C, [F_SUB], "订阅健康摘要：mrr_2024_end（2024-12-31 日终 MRR 合计，美元整数）、nrr（2023-12-31 日终 MRR > 0 的账户在 2024-12-31 的 MRR 合计 ÷ 这些账户在 2023-12-31 的 MRR 合计）、grr（对同一批账户，Σ min(2024-12-31 MRR, 2023-12-31 MRR) ÷ Σ 2023-12-31 MRR）、quick_ratio（2024 年 12 个月合计的 (new + expansion + reactivation) ÷ |churn + contraction|），比率保留4位小数。" + WFDEF + J,
  {"mrr_2024_end": int(m24.sum()), "nrr": rnd(m24[base.index].sum() / base.sum(), 4), "grr": rnd(np.minimum(m24[base.index], base).sum() / base.sum(), 4),
   "quick_ratio": rnd((wf.new.sum() + wf.expansion.sum() + wf.reactivation.sum()) / abs(wf.churn.sum() + wf.contraction.sum()), 4)}, "json", tols={"nrr": 4, "grr": 4, "quick_ratio": 4})
Q(LV, C, FI, "库存摘要：fifo_cogs（先进先出 2024 年销货成本）、wac_cogs（移动加权平均 2024 年销货成本）、ending_value_fifo（先进先出期末库存价值），均保留2位小数；stockout_sku_days（入库后出库前库存为 0 的 SKU-天数）。" + INVDEF + J,
  {"fifo_cogs": rnd(sum(fifo_cogs.values()), 2), "wac_cogs": rnd(sum(wac_cogs.values()), 2), "ending_value_fifo": rnd(sum(end_val.values()), 2), "stockout_sku_days": stockout}, "json",
  tols={"fifo_cogs": 2, "wac_cogs": 2, "ending_value_fifo": 2})
inv_out = pd.DataFrame({"sku": list(fifo_cogs), "fifo_cogs": [round(fifo_cogs[k], 2) for k in fifo_cogs], "wac_cogs": [round(wac_cogs[k], 2) for k in fifo_cogs],
                        "ending_qty": [end_qty[k] for k in fifo_cogs], "ending_value_fifo": [round(end_val[k], 2) for k in fifo_cogs]})
Q(LV, C, FI, "生成 inventory_sku.csv：每个 SKU 一行，列依次为 sku,fifo_cogs,wac_cogs,ending_qty,ending_value_fifo（2024 年先进先出销货成本、移动加权平均销货成本、期末数量、先进先出期末价值，金额保留2位小数）。按 sku 升序。" + INVDEF,
  "inventory_sku.csv", "csv", (inv_out, ["sku"], {"fifo_cogs": .011, "wac_cogs": .011, "ending_qty": 1e-9, "ending_value_fifo": .011}))
nb = lp[~lp.is_bot]
Q(LV, C, [F_LOG], "接口可用性摘要（只看能解析的非爬虫请求）：availability（非 5xx 请求占比，保留4位小数）、p95_checkout_ms（路径 /api/checkout 的请求耗时 P95，毫秒，保留2位小数）、worst_hour_utc（5xx 请求最多的 UTC 小时，格式 YYYY-MM-DD HH）。" + J,
  {"availability": rnd((nb.status < 500).mean(), 4), "p95_checkout_ms": rnd(nb[nb.route == "/api/checkout"].rt.quantile(.95) * 1000, 2),
   "worst_hour_utc": top1(nb[nb.status >= 500].ts.dt.strftime("%Y-%m-%d %H").value_counts())}, "json", tols={"availability": 4, "p95_checkout_ms": 2})
route = nb.path.str.split("?").str[0].map(lambda p: "/".join("{id}" if s.isdigit() else s for s in p.split("/")))
es = nb.assign(route2=route).groupby("route2").agg(requests=("rt", "size"), error_rate=("status", lambda s: (s >= 500).mean()),
                                                   p50_ms=("rt", lambda s: s.quantile(.5) * 1000), p95_ms=("rt", lambda s: s.quantile(.95) * 1000)).reset_index()
es_out = pd.DataFrame({"route": es.route2, "requests": es.requests, "error_rate": es.error_rate.round(4), "p50_ms": es.p50_ms.round(2), "p95_ms": es.p95_ms.round(2)})
Q(LV, C, [F_LOG], "生成 endpoint_stats.csv（只看能解析的非爬虫请求）：先把路径归一为路由——去掉 ? 及之后的查询串，并把完全由数字组成的路径段替换为 {id}（如 /api/orders/123 → /api/orders/{id}）。"
  "每个路由一行，列依次为 route,requests,error_rate,p50_ms,p95_ms：请求数、5xx 占比（保留4位小数）、请求耗时的中位数与 P95（毫秒，保留2位小数）。按 route 升序。",
  "endpoint_stats.csv", "csv", (es_out, ["route"], {"requests": 1e-9, "error_rate": 1e-4 + 1e-9, "p50_ms": .011, "p95_ms": .011}))
Q(LV, C, [F_GL, F_COA], f"总账摘要（{GLDEF}后）：revenue（收入，revenue 类科目贷方 − 借方）、expense（费用，expense 类科目借方 − 贷方）、net_income（revenue − expense），均保留2位小数；unbalanced（借贷不平衡的凭证号，按升序的数组）。" + J,
  {"revenue": rnd(rev_, 2), "expense": rnd(exp_, 2), "net_income": rnd(rev_ - exp_, 2), "unbalanced": T["unbal"]}, "json", tols={"revenue": 2, "expense": 2, "net_income": 2})
glm = glvd.assign(month=glvd.date.dt.strftime("%Y-%m"))
gm = pd.DataFrame({"month": sorted(glm.month.unique())})
gm["revenue"] = gm.month.map(-glm[glm.type == "revenue"].groupby("month").amount.sum()).fillna(0).round(2)
gm["expense"] = gm.month.map(glm[glm.type == "expense"].groupby("month").amount.sum()).fillna(0).round(2)
gm["net_income"] = (gm.month.map(-glm[glm.type == "revenue"].groupby("month").amount.sum()).fillna(0) - gm.month.map(glm[glm.type == "expense"].groupby("month").amount.sum()).fillna(0)).round(2)
Q(LV, C, [F_GL, F_COA], f"生成 gl_monthly.csv（{GLDEF}后）：2024 年每月一行（按记账日期），列依次为 month,revenue,expense,net_income（month 形如 2024-01，金额保留2位小数）。按 month 升序。",
  "gl_monthly.csv", "csv", (gm, ["month"], {"revenue": .011, "expense": .011, "net_income": .011}))
s_end = {k: v for k, v in states_at(datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC)).items() if v}
Q(LV, C, FPIT, "商品数据摘要：active_skus_2024_end（截至 2024-12-31 23:59:59 UTC 存在的 SKU 数）、price_changes（价格发生变化的更新事件数）、above_list_lines（2024 年新系统中国门店 S01–S04 最终 completed 订单中，成交单价高于下单时刻标价的明细行数）。" + J,
  {"active_skus_2024_end": len(s_end), "price_changes": sum(pchg.values()), "above_list_lines": int((icn.unit_price > icn.list_price_cny).sum())}, "json")
Q(LV, C, FMS, RULE + "会员摘要：clusters（簇数）、multi_member_clusters（包含 2 个及以上 member_id 的簇数）、top_cluster_key（2023–2024 两年订单金额最高的簇的代表 ID）、top_cluster_net_cny（该簇的金额，保留2位小数）。" + OCDEF + J,
  {"clusters": len(cl), "multi_member_clusters": int((cl.nm >= 2).sum()), "top_cluster_key": top1(kn), "top_cluster_net_cny": rnd(kn.max(), 2)}, "json", tols={"top_cluster_net_cny": 2})

cnt = Counter(c["level"] for c in cases)
assert len(cases) == 200 and all(v == 20 for v in cnt.values()), dict(cnt)
json.dump(cases, open(HERE / "test_cases.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("各级题数：", dict(sorted(cnt.items())), "合计", len(cases))
print("答案类型：", Counter(c["answer_type"] for c in cases))
print("示例：Simpson =", simpson, "| 根因组合 =", worst, "| 首个下滑周 =", first_drop, "| BH 显著 =", sorted(rk.index[:kmax + 1]))

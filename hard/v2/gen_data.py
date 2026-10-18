#!/usr/bin/env python3
"""v2 数据集：data/ 为模型可见数据，truth/ 为干净真值（标准答案只从真值计算）"""

import gzip
import json
import pickle
import shutil
from bisect import bisect_right
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
DATA = HERE / "data"
TRUTH = HERE / "truth"
if DATA.exists():
    shutil.rmtree(DATA)
DATA.mkdir()
TRUTH.mkdir(exist_ok=True)
rng = np.random.default_rng(20261019)
UTC = timezone.utc
T = {}


def W(rel, df, **kw):
    p = DATA / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False, **kw)


def pick(opts, p, n=None):
    return rng.choice(np.array(opts, dtype=object), size=n, p=p)


SURN = list("王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾萧田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤")
GIV = list("伟芳娜敏静丽强磊军洋勇艳杰娟涛明超秀霞平刚桂英华玉兰萍红鹏辉建林云飞浩宇欣怡梓涵子轩雨晨思佳嘉琪婷雪颖博文斌")


def name():
    return rng.choice(SURN) + "".join(rng.choice(GIV, rng.choice([1, 2], p=[.3, .7])))


# =============================================================== 门店与汇率
STORES = pd.DataFrame([
    ("S01", "上海旗舰店", "上海", "CN", "Asia/Shanghai", "CNY", 30),
    ("S02", "北京国贸店", "北京", "CN", "Asia/Shanghai", "CNY", 25),
    ("S03", "深圳湾店", "深圳", "CN", "Asia/Shanghai", "CNY", 22),
    ("S04", "成都太古里店", "成都", "CN", "Asia/Shanghai", "CNY", 18),
    ("S05", "San Francisco Union Square", "San Francisco", "US", "America/Los_Angeles", "USD", 10),
    ("S06", "New York SoHo", "New York", "US", "America/New_York", "USD", 12),
], columns=["store_id", "name", "city", "country", "timezone", "currency", "base"])
W("stores.csv", STORES.drop(columns="base"))
TZ = {r.store_id: ZoneInfo(r.timezone) for r in STORES.itertuples()}
CUR = dict(zip(STORES.store_id, STORES.currency))

bd = pd.bdate_range("2022-12-26", "2024-12-31")
bd = bd[~np.isin(np.arange(len(bd)), rng.choice(np.arange(5, len(bd)), 10, replace=False))]
fx = pd.DataFrame({"date": bd, "usd_cny": np.clip(6.9 + np.cumsum(rng.normal(.0005, .01, len(bd))), 6.7, 7.35).round(4)})
W("fx_daily.csv", fx.assign(date=fx.date.dt.strftime("%Y-%m-%d")))
FXS = fx.set_index("date").usd_cny


def fx_at(d):
    return float(FXS.iloc[FXS.index.searchsorted(pd.Timestamp(d), side="right") - 1])


T["stores"], T["fx"] = STORES, fx

# =============================================================== 会员（两套系统，用于实体合并）
N_P = 5000
phones = set()
while len(phones) < 9000:
    phones.add("1" + str(rng.choice(list("3456789"))) + "".join(rng.choice(list("0123456789"), 9)))
phones = sorted(phones)
rng.shuffle(phones)
DOMS = ["qq.com", "163.com", "gmail.com", "126.com", "outlook.com", "sina.com"]


def mk_email(i):
    return f"{''.join(rng.choice(list('abcdefghijklmnopqrstuvwxyz'), rng.integers(4, 8)))}{i}@{rng.choice(DOMS)}"


persons = pd.DataFrame({"pid": [f"P{i:05d}" for i in range(N_P)], "name": [name() for _ in range(N_P)],
                        "phone": phones[:N_P], "email": [mk_email(i) for i in range(N_P)]})
spare_phone = iter(phones[N_P:])
fam = rng.choice(N_P, 80, replace=False).reshape(40, 2)
for a, b in fam:
    persons.loc[b, "email"] = persons.loc[a, "email"]


def fmt_phone(p):
    r = rng.random()
    if r < .45:
        return p
    if r < .60:
        return f"+86 {p[:3]} {p[3:7]} {p[7:]}"
    if r < .72:
        return f"+86-{p[:3]}-{p[3:7]}-{p[7:]}"
    if r < .82:
        return f"86{p}"
    if r < .92:
        return f"{p[:3]}-{p[3:7]}-{p[7:]}"
    return f"(+86){p}"


def fmt_email(e):
    r = rng.random()
    if r < .75:
        return e
    if r < .9:
        return e.upper() if rng.random() < .5 else e.capitalize()
    return f" {e} "


def mk_records(prefix, n_people, n_second, second_kind, start, id_width):
    idx = rng.choice(N_P, n_people, replace=False)
    seconds = set(rng.choice(idx, n_second, replace=False))
    rows = []
    for i in idx:
        p = persons.iloc[i]
        rows.append([p.pid, p["name"], p.phone, p.email])
        if i in seconds:
            if second_kind == "new_email":
                rows.append([p.pid, p["name"], p.phone, f"alt{len(rows)}_{mk_email(i)}"])
            else:
                rows.append([p.pid, p["name"], next(spare_phone), p.email])
    df = pd.DataFrame(rows, columns=["pid", "name", "phone", "email"]).sample(frac=1, random_state=int(rng.integers(1e9))).reset_index(drop=True)
    m = rng.random(len(df))
    df.loc[m < .05, "phone"] = None
    df.loc[(m >= .05) & (m < .10), "email"] = None
    df.insert(0, "rid", [f"{prefix}{i:0{id_width}d}" for i in range(1, len(df) + 1)])
    df["created"] = [start + timedelta(seconds=int(rng.integers(0, 700 * 86400))) for _ in range(len(df))]
    return df


members = mk_records("M", 4500, 150, "new_email", datetime(2021, 1, 1), 6)
crm = mk_records("C", 4200, 300, "new_phone", datetime(2020, 6, 1), 5)
W("crm/members_shop.csv", pd.DataFrame({
    "member_id": members.rid, "name": members["name"], "phone": [fmt_phone(p) if isinstance(p, str) else "" for p in members.phone],
    "email_addr": [fmt_email(e) if isinstance(e, str) else "" for e in members.email], "register_time": members.created.map(lambda d: d.strftime("%Y-%m-%dT%H:%M:%S"))}))
W("crm/contacts_crm.csv", pd.DataFrame({
    "crm_id": crm.rid, "full_name": crm["name"], "mobile": [fmt_phone(p) if isinstance(p, str) else "" for p in crm.phone],
    "email": [fmt_email(e) if isinstance(e, str) else "" for e in crm.email], "city": pick(["上海", "北京", "深圳", "成都", "杭州", "广州"], None, len(crm)),
    "created_at": crm.created.map(lambda d: d.strftime("%Y-%m-%d"))}))
T["persons"], T["members"], T["crm"] = persons, members, crm

# =============================================================== 商品 CDC
CATS = ["服饰", "鞋靴", "箱包", "美妆", "家居", "数码配件", "运动", "食品"]
N_SKU = 300
T0 = datetime(2023, 1, 1, tzinfo=UTC)
T1 = datetime(2025, 1, 1, tzinfo=UTC)
events, lsn = [], 0
state = {}
for i in range(1, N_SKU + 1):
    sku = f"SKU{i:04d}"
    lsn += 1
    after = {"sku": sku, "name": f"商品{i:04d}", "category": str(rng.choice(CATS)),
             "price_cny": round(float(np.exp(rng.normal(5.3, .6))), 2), "status": "active"}
    events.append({"lsn": lsn, "ts": T0, "op": "r", "sku": sku, "before": None, "after": after})
    state[sku] = after
plan = []
for sku in state:
    for _ in range(rng.poisson(4)):
        plan.append((T0 + timedelta(seconds=int(rng.integers(86400, 730 * 86400))), sku, "price"))
for sku in rng.choice(list(state), 30, replace=False):
    plan.append((T0 + timedelta(seconds=int(rng.integers(86400, 730 * 86400))), sku, "cat"))
dels = rng.choice(list(state), 20, replace=False)
for sku in dels:
    plan.append((datetime(2024, 4, 1, tzinfo=UTC) + timedelta(seconds=int(rng.integers(0, 180 * 86400))), sku, "del"))
plan.sort(key=lambda x: x[0])
deleted_at = {}
for ts, sku, kind in plan:
    cur = state.get(sku)
    if cur is None:
        continue
    if kind == "del":
        lsn += 1
        events.append({"lsn": lsn, "ts": ts, "op": "d", "sku": sku, "before": dict(cur), "after": None})
        state[sku] = None
        deleted_at[sku] = ts
        continue
    new = dict(cur)
    if kind == "price":
        new["price_cny"] = round(cur["price_cny"] * float(rng.uniform(.85, 1.15)), 2)
    else:
        new["category"] = str(rng.choice([c for c in CATS if c != cur["category"]]))
    lsn += 1
    events.append({"lsn": lsn, "ts": ts, "op": "u", "sku": sku, "before": dict(cur), "after": new})
    state[sku] = new
for sku in list(deleted_at)[:3]:
    ts = deleted_at[sku] + timedelta(days=int(rng.integers(20, 60)))
    if ts < T1:
        lsn += 1
        after = {"sku": sku, "name": f"商品{sku[3:]}（新版）", "category": str(rng.choice(CATS)),
                 "price_cny": round(float(np.exp(rng.normal(5.3, .6))), 2), "status": "active"}
        events.append({"lsn": lsn, "ts": ts, "op": "c", "sku": sku, "before": None, "after": after})
# lsn 必须与生效时间同序：按 (ts, 原生成顺序) 重新编号
events.sort(key=lambda e: (e["ts"], e["lsn"]))
for k, e in enumerate(events, 1):
    e["lsn"] = k
T["cdc"] = events
SKU_HIST = {}
for e in events:
    SKU_HIST.setdefault(e["sku"], []).append((e["ts"], e["after"]))


def sku_state(sku, t):
    h = SKU_HIST[sku]
    i = bisect_right([x[0] for x in h], t) - 1
    return h[i][1] if i >= 0 else None


cdc_lines = [{"lsn": e["lsn"], "ts_ms": int(e["ts"].timestamp() * 1000), "op": e["op"], "sku": e["sku"],
              "before": e["before"], "after": e["after"]} for e in events]
dup = [cdc_lines[i] for i in rng.choice(len(cdc_lines), 40, replace=False)]
cdc_out = cdc_lines + dup
rng.shuffle(cdc_out)
(DATA / "catalog").mkdir(parents=True, exist_ok=True)
with open(DATA / "catalog/product_cdc.jsonl", "w", encoding="utf-8") as f:
    for e in cdc_out:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")

# =============================================================== 销售订单
HOUR_P = np.array([1, .5, .3, .2, .2, .3, .8, 2, 3, 4, 5, 6, 6, 5, 5, 5, 5, 5.5, 6, 7, 7, 6, 4, 2], float)
HOUR_P /= HOUR_P.sum()
member_ids = members.rid.tolist()


def local_ok(naive, tz):
    """返回 'ok' / 'ambiguous' / 'nonexistent'"""
    a = naive.replace(tzinfo=tz, fold=0)
    b = naive.replace(tzinfo=tz, fold=1)
    if a.utcoffset() != b.utcoffset():
        back = a.astimezone(UTC).astimezone(tz).replace(tzinfo=None)
        return "nonexistent" if back != naive else "ambiguous"
    return "ok"


def daily_mult(d, country):
    m = 1.25 if d.weekday() >= 5 else 1.0
    if d.month == 12:
        m *= 1.3
    if country == "CN" and d.month == 2:
        m *= .8
    return m


orders = []
oid = {"L": 0, "A": 0}
for s in STORES.itertuples():
    tz = TZ[s.store_id]
    for d in pd.date_range("2023-01-01", "2024-12-31"):
        n = rng.poisson(s.base * daily_mult(d, s.country))
        src = "L" if d.year == 2023 else "A"
        for _ in range(n):
            while True:
                h = int(rng.choice(24, p=HOUR_P))
                naive = datetime(d.year, d.month, d.day, h, int(rng.integers(60)), 0 if (src == "L" and d.month >= 7) else int(rng.integers(60)))
                if local_ok(naive, tz) == "ok":
                    break
            if src == "A":
                ch = str(pick(["app", "web", "pos"], [.5, .2, .3] if s.country == "CN" else [.3, .3, .4]))
                if d.year == 2024 and d.month == 8 and s.store_id == "S01" and ch == "app" and rng.random() < .6:
                    continue
            else:
                ch = None
            orders.append({"src": src, "store_id": s.store_id, "local": naive, "channel": ch, "time_ok": True})
# 夏令时陷阱（旧系统美国门店）
for sid in ["S05", "S06"]:
    for k in range(4):
        orders.append({"src": "L", "store_id": sid, "local": datetime(2023, 11, 5, 1, int(rng.integers(0, 60)), 0), "channel": None, "time_ok": True})
    for k in range(3 if sid == "S05" else 2):
        orders.append({"src": "L", "store_id": sid, "local": datetime(2023, 3, 12, 2, int(rng.integers(0, 60)), 0), "channel": None, "time_ok": False})
orders = pd.DataFrame(orders)
orders["utc"] = [r.local.replace(tzinfo=TZ[r.store_id], fold=0).astimezone(UTC).replace(tzinfo=None) if r.time_ok else pd.NaT
                 for r in orders.itertuples()]
orders = orders.sort_values(["src", "utc", "store_id"], na_position="last", kind="stable").reset_index(drop=True)
ids = []
for s in orders.src:
    oid[s] += 1
    ids.append(f"{s}{oid[s]:06d}")
orders.insert(0, "order_id", ids)
orders["member_id"] = [None if rng.random() < .1 else member_ids[int(rng.integers(len(member_ids)))] for _ in range(len(orders))]
orders["currency"] = orders.store_id.map(CUR)
orders["local_date"] = [r.local.date() if r.time_ok else None for r in orders.itertuples()]

# 2024 新系统：明细与促销
POP = 1 / np.arange(1, N_SKU + 1) ** .8
rng.shuffle(POP)
POP /= POP.sum()
SKUS = [f"SKU{i:04d}" for i in range(1, N_SKU + 1)]
PROMO = ["NEW10", "VIP15", "SUMMER", "FLASH20", "MEMBER5"]
items_rows, promo_rows = [], []
gross, disc = [], []
for r in orders.itertuples():
    if r.src == "L":
        cn = CUR[r.store_id] == "CNY"
        g = round(float(np.exp(rng.normal(5.8 if cn else 3.9, .55))), 2)
        dsc = 0.0 if rng.random() < .6 else round(g * float(rng.uniform(.05, .2)), 2)
        gross.append(g)
        disc.append(dsc)
        continue
    t = r.utc.replace(tzinfo=UTC)
    k = min(1 + rng.poisson(1.0), 6)
    chosen = []
    while len(chosen) < k:
        sku = SKUS[int(rng.choice(N_SKU, p=POP))]
        st = sku_state(sku, t)
        if st is not None and sku not in chosen:
            chosen.append(sku)
    g = 0.0
    for sku in chosen:
        lp = sku_state(sku, t)["price_cny"]
        q = int(rng.choice([1, 2, 3], p=[.75, .18, .07]))
        if CUR[r.store_id] == "CNY":
            up = round(lp * float(rng.uniform(1.05, 1.2) if rng.random() < .01 else rng.uniform(.85, 1.0)), 2)
        else:
            up = round(lp / 7.0 * float(rng.uniform(.85, 1.0)), 2)
        items_rows.append((r.order_id, sku, q, up, lp))
        g += q * up
    g = round(g, 2)
    dsc = 0.0
    npromo = 0 if rng.random() < .7 else (1 if rng.random() < .85 else 2)
    for code in rng.choice(PROMO, npromo, replace=False):
        a = round(g * float(rng.uniform(.03, .08)), 2)
        promo_rows.append((r.order_id, str(code), a))
        dsc += a
    gross.append(g)
    disc.append(round(dsc, 2))
orders["gross"] = gross
orders["discount"] = disc
orders["net"] = (orders.gross - orders.discount).round(2)
orders["status"] = pick(["completed", "cancelled"], [.92, .08], len(orders))
items = pd.DataFrame(items_rows, columns=["order_id", "sku", "qty", "unit_price", "list_price_cny"])
promos = pd.DataFrame(promo_rows, columns=["order_id", "code", "amount"])

# 新系统 upsert：3% 订单后来被取消（出现两条，updated_at 较新的为准）；1% 完全重复
api = orders[orders.src == "A"].copy()
api["created_local"] = [r.utc.replace(tzinfo=UTC).astimezone(TZ[r.store_id]) for r in api.itertuples()]
api["updated"] = api.created_local.map(lambda c: c + timedelta(seconds=int(rng.integers(20, 600))))
later = set(rng.choice(api[api.status == "completed"].order_id, int(len(api) * .03), replace=False))
orders.loc[orders.order_id.isin(later), "status"] = "cancelled"
orders["cancelled_later"] = orders.order_id.isin(later)
it_by = {k: g.to_dict("records") for k, g in items.groupby("order_id")}
pr_by = {k: g.to_dict("records") for k, g in promos.groupby("order_id")}
lines = []
for r in api.itertuples():
    base = {"id": r.order_id, "store": {"id": r.store_id}, "channel": r.channel,
            "customer": ({"member_id": r.member_id} if r.member_id else None),
            "created_at": r.created_local.isoformat(timespec="seconds"),
            "updated_at": r.updated.isoformat(timespec="seconds"), "currency": r.currency,
            "items": [{"sku": x["sku"], "qty": x["qty"], "unit_price": x["unit_price"]} for x in it_by.get(r.order_id, [])],
            "promotions": [{"code": x["code"], "amount": x["amount"]} for x in pr_by.get(r.order_id, [])],
            "status": "completed" if r.order_id in later else r.status}
    lines.append(base)
    if r.order_id in later:
        v2 = dict(base, status="cancelled", updated_at=(r.updated + timedelta(days=int(rng.integers(1, 10)), seconds=int(rng.integers(0, 86400)))).isoformat(timespec="seconds"))
        lines.append(v2)
    elif rng.random() < .01:
        lines.append(dict(base))
order_of = np.arange(len(lines))
# 轻度乱序：按块打乱
blocks = np.array_split(order_of, 400)
rng.shuffle(blocks)
(DATA / "sales/api").mkdir(parents=True, exist_ok=True)
with open(DATA / "sales/api/orders_2024.jsonl", "w", encoding="utf-8") as f:
    for b in blocks:
        for i in b:
            f.write(json.dumps(lines[i], ensure_ascii=False) + "\n")

# 旧系统：按本地月份分区 CSV，下半年字段改名
leg = orders[orders.src == "L"].copy()
leg["ym"] = leg.local.map(lambda x: x.strftime("%Y-%m"))
(DATA / "sales/legacy").mkdir(parents=True, exist_ok=True)
for ym, g in leg.groupby("ym"):
    h1 = int(ym[-2:]) <= 6
    out = pd.DataFrame({
        "order_id": g.order_id, "store_id": g.store_id, "member_id": g.member_id.fillna(""),
        "order_time": g.local.map(lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if h1 else x.strftime("%Y/%m/%d %H:%M")),
        "currency": g.currency,
        ("amount" if h1 else "total_amount"): g.gross.map(lambda v: f"{v:.2f}"),
        ("discount" if h1 else "discount_amt"): g.discount.map(lambda v: f"{v:.2f}"),
        "status": g.status.str.upper() if h1 else g.status})
    if ym == "2023-09":
        aug = leg[leg.local.map(lambda x: x.strftime("%Y-%m-%d")) == "2023-08-31"]
        out = pd.concat([out, pd.DataFrame({
            "order_id": aug.order_id, "store_id": aug.store_id, "member_id": aug.member_id.fillna(""),
            "order_time": aug.local.map(lambda x: x.strftime("%Y/%m/%d %H:%M")), "currency": aug.currency,
            "total_amount": aug.gross.map(lambda v: f"{v:.2f}"), "discount_amt": aug.discount.map(lambda v: f"{v:.2f}"),
            "status": aug.status})])
    out = pd.concat([out, out.sample(3, random_state=int(rng.integers(1e9)))]).sample(frac=1, random_state=int(rng.integers(1e9)))
    out.to_csv(DATA / f"sales/legacy/orders_{ym}.csv", index=False)
T["orders"], T["items"], T["promos"] = orders, items, promos
T["aug31_dups"] = int((leg.local.map(lambda x: x.strftime("%Y-%m-%d")) == "2023-08-31").sum())

# =============================================================== 支付与退款（2024 新系统订单）
pays, refs, pay_truth = [], [], {}
pid_n, rid_n = 0, 0


def fee_of(amount, cur):
    return round(amount * .006, 2) if cur == "CNY" else round(amount * .029 + .30, 2)


def add_pay(oid_, t, amount, cur, status, fee=None):
    global pid_n
    pid_n += 1
    pays.append({"payment_id": f"PAY{pid_n:07d}", "order_id": oid_, "paid_at": t, "amount": round(amount, 2), "currency": cur,
                 "fee": fee_of(amount, cur) if fee is None and status == "SUCCESS" else (fee or 0.0), "status": status})


def add_ref(oid_, t, amount, cur):
    global rid_n
    rid_n += 1
    refs.append({"refund_id": f"RF{rid_n:06d}", "order_id": oid_, "refund_at": t, "amount": round(amount, 2), "currency": cur})


for r in orders[orders.src == "A"].itertuples():
    t0 = r.utc + timedelta(seconds=int(rng.integers(5, 1800)))
    cat = "normal"
    if r.status == "completed" or r.cancelled_later:
        u = rng.random()
        if r.cancelled_later:
            add_pay(r.order_id, t0, r.net, r.currency, "SUCCESS")
            add_ref(r.order_id, t0 + timedelta(days=int(rng.integers(1, 12))), r.net, r.currency)
            cat = "cancelled_refunded"
        elif u < .015:
            cat = "missing"
        elif u < .025:
            add_pay(r.order_id, t0, r.net, r.currency, "SUCCESS")
            add_pay(r.order_id, t0 + timedelta(seconds=int(rng.integers(10, 300))), r.net, r.currency, "SUCCESS")
            cat = "double"
        elif u < .045:
            add_pay(r.order_id, t0 - timedelta(seconds=30), r.net, r.currency, "FAILED")
            add_pay(r.order_id, t0, r.net, r.currency, "SUCCESS")
            cat = "retry_ok"
        elif u < .055:
            add_pay(r.order_id, t0, r.net - float(rng.uniform(.5, max(.6, min(50, r.net * .5)))), r.currency, "SUCCESS")
            cat = "underpaid"
        elif u < .060:
            add_pay(r.order_id, t0, r.net + .01, r.currency, "SUCCESS")
            cat = "rounding"
        elif u < .063:
            add_pay(r.order_id, t0, r.net, r.currency, "SUCCESS")
            add_pay(r.order_id, t0 + timedelta(days=int(rng.integers(10, 40))), r.net, r.currency, "REVERSED", fee=15.0)
            cat = "chargeback"
        else:
            add_pay(r.order_id, t0, r.net, r.currency, "SUCCESS")
            if rng.random() < .04:
                ra = round(r.net * float(rng.uniform(.1, .5)), 2)
                add_ref(r.order_id, t0 + timedelta(days=int(rng.integers(1, 20))), ra, r.currency)
                cat = "partial_refund"
    else:
        if rng.random() < .07:
            add_pay(r.order_id, t0, r.net, r.currency, "SUCCESS")
            cat = "cancelled_paid_unrefunded"
        else:
            cat = "cancelled_unpaid"
    pay_truth[r.order_id] = cat
over = rng.choice([p["order_id"] for p in pays if pay_truth[p["order_id"]] == "partial_refund"], 5, replace=False)
for o in over:
    net = float(orders.loc[orders.order_id == o, "net"].iloc[0])
    add_ref(o, datetime(2024, 12, 20) + timedelta(seconds=int(rng.integers(0, 86400 * 5))), net * .8, CUR[orders.loc[orders.order_id == o, "store_id"].iloc[0]])
for k in range(20):
    add_pay(f"A9{k:05d}", datetime(2024, 1, 1) + timedelta(seconds=int(rng.integers(0, 365 * 86400))), float(rng.uniform(20, 900)), "CNY", "SUCCESS")
pays = pd.DataFrame(pays)
refs = pd.DataFrame(refs)
W("payments/gateway_settlement.csv", pays.assign(paid_at=pays.paid_at.map(lambda t: t.strftime("%Y-%m-%dT%H:%M:%SZ")),
                                                  amount=pays.amount.map(lambda v: f"{v:.2f}"), fee=pays.fee.map(lambda v: f"{v:.2f}")).sample(frac=1, random_state=11))
W("payments/refunds.csv", refs.assign(refund_at=refs.refund_at.map(lambda t: t.strftime("%Y-%m-%dT%H:%M:%SZ")),
                                      amount=refs.amount.map(lambda v: f"{v:.2f}")).sample(frac=1, random_state=12))
T["payments"], T["refunds"], T["pay_truth"], T["over_refund"] = pays, refs, pay_truth, sorted(over)

# =============================================================== 库存（先进先出）
inv_p, inv_s = [], []
lot_n, shp_n = 0, 0
for k in range(1, 21):
    sku = f"INV{k:02d}"
    cost = float(rng.uniform(20, 200))
    lot_n += 1
    q0 = int(rng.integers(80, 200))
    inv_p.append({"lot_id": f"LOT{lot_n:04d}", "sku": sku, "received_at": pd.Timestamp("2023-12-31"), "qty": q0, "unit_cost": round(cost, 2)})
    onhand, pipeline = q0, []
    lam = float(rng.uniform(3, 12))
    for d in pd.date_range("2024-01-01", "2024-12-31"):
        for (ad, q, c) in [x for x in pipeline if x[0] == d]:
            lot_n += 1
            inv_p.append({"lot_id": f"LOT{lot_n:04d}", "sku": sku, "received_at": d, "qty": q, "unit_cost": c})
            onhand += q
        pipeline = [x for x in pipeline if x[0] != d]
        dem = int(rng.poisson(lam))
        ship = min(dem, onhand)
        if ship > 0:
            shp_n += 1
            inv_s.append({"shipment_id": f"SH{shp_n:06d}", "sku": sku, "shipped_at": d, "qty": ship})
            onhand -= ship
        if onhand + sum(x[1] for x in pipeline) < lam * 10:
            cost *= float(rng.uniform(.95, 1.07))
            pipeline.append((d + pd.Timedelta(days=int(rng.integers(3, 10))), int(lam * rng.uniform(15, 30)), round(cost, 2)))
inv_p = pd.DataFrame(inv_p)
inv_s = pd.DataFrame(inv_s)
W("inventory/purchases.csv", inv_p.assign(received_at=inv_p.received_at.dt.strftime("%Y-%m-%d")))
s_out = inv_s.assign(shipped_at=inv_s.shipped_at.dt.strftime("%Y-%m-%d"))
W("inventory/shipments.csv", pd.concat([s_out, s_out.sample(10, random_state=13)]).sample(frac=1, random_state=14))
T["inv_p"], T["inv_s"] = inv_p, inv_s

# =============================================================== 订阅事件
PLANS = {"basic": 99, "pro": 299, "enterprise": 999}
sub_rows = []
for k in range(1, 1501):
    acc = f"AC{k:04d}"
    d = pd.Timestamp("2022-06-01") + pd.Timedelta(days=int(rng.integers(0, 910)))
    plan = str(pick(list(PLANS), [.55, .35, .10]))
    mrr = PLANS[plan] * (1 if rng.random() < .8 else int(rng.integers(2, 6)))
    seq = 1
    sub_rows.append([acc, d, seq, "new", plan, mrr])
    active = True
    while True:
        d = d + pd.Timedelta(days=int(rng.exponential(160)) + 1)
        if d > pd.Timestamp("2024-12-31"):
            break
        seq += 1
        u = rng.random()
        if active:
            if u < .35:
                active = False
                sub_rows.append([acc, d, seq, "churn", plan, 0])
            elif u < .7:
                np_ = {"basic": "pro", "pro": "enterprise", "enterprise": "enterprise"}[plan]
                nm = mrr + PLANS[np_] if np_ == plan else int(mrr / PLANS[plan] * PLANS[np_])
                plan, mrr = np_, nm
                sub_rows.append([acc, d, seq, "upgrade", plan, mrr])
            else:
                np_ = {"basic": "basic", "pro": "basic", "enterprise": "pro"}[plan]
                nm = max(PLANS[np_], int(mrr * .6)) if np_ == plan else int(mrr / PLANS[plan] * PLANS[np_])
                if nm == mrr:
                    continue
                plan, mrr = np_, nm
                sub_rows.append([acc, d, seq, "downgrade", plan, mrr])
            if rng.random() < .08 and d < pd.Timestamp("2024-12-20"):
                seq += 1
                plan2 = {"basic": "pro", "pro": "enterprise", "enterprise": "enterprise"}[plan]
                if active and plan2 != plan:
                    mrr = int(mrr / PLANS[plan] * PLANS[plan2])
                    plan = plan2
                    sub_rows.append([acc, d, seq, "upgrade", plan, mrr])
        else:
            if u < .25:
                active = True
                plan = str(pick(list(PLANS), [.6, .3, .1]))
                mrr = PLANS[plan]
                sub_rows.append([acc, d, seq, "reactivate", plan, mrr])
            else:
                break
subs = pd.DataFrame(sub_rows, columns=["account_id", "event_date", "seq", "event_type", "plan", "mrr_after"])
s_out = subs.assign(event_date=subs.event_date.dt.strftime("%Y-%m-%d"))
W("subscriptions/subscription_events.csv", pd.concat([s_out, s_out.sample(25, random_state=15)]).sample(frac=1, random_state=16))
T["subs"] = subs

# =============================================================== IoT 传感器（约 100 万行，gzip）
N_DEV = 60
SITES = ["上海仓", "苏州仓", "广州仓", "成都仓"]
devs = pd.DataFrame({"device_id": [f"DEV{i:03d}" for i in range(1, N_DEV + 1)], "site": [SITES[i % 4] for i in range(N_DEV)],
                     "install_date": [(pd.Timestamp("2023-01-01") + pd.Timedelta(days=int(rng.integers(0, 600)))).strftime("%Y-%m-%d") for _ in range(N_DEV)]})
f_devs = sorted(rng.choice(devs.device_id, 6, replace=False))
devs["firmware"] = ["2.3.1" if d in f_devs else str(pick(["1.8.0", "1.9.2", "2.1.0"], [.3, .4, .3])) for d in devs.device_id]
W("iot/devices.csv", devs)
start = pd.Timestamp("2024-10-01")
n_slot = 61 * 288
base_t = {"上海仓": 18, "苏州仓": 17, "广州仓": 24, "成都仓": 15}
recs, outages = [], []
for r in devs.itertuples():
    slots = np.arange(n_slot)
    keep = np.ones(n_slot, bool)
    for _ in range(int(rng.integers(0, 4))):
        s0 = int(rng.integers(288, n_slot - 400))
        ln = int(rng.integers(36, 360))
        keep[s0:s0 + ln] = False
        outages.append((r.device_id, s0, ln))
    slots = slots[keep]
    ts = start + pd.to_timedelta(slots * 300 + rng.integers(-30, 31, len(slots)), unit="s")
    hours = (slots * 300 / 3600) % 24
    temp = base_t[r.site] - (pd.Series(slots).values / n_slot) * 6 + 4 * np.sin((hours - 9) / 24 * 2 * np.pi) + rng.normal(0, .6, len(slots)) + rng.normal(0, 1.5)
    df = pd.DataFrame({"device_id": r.device_id, "ts": ts, "temp_c": temp.round(2)})
    recs.append(df)
iot = pd.concat(recs, ignore_index=True)
glitch = rng.choice(len(iot), int(len(iot) * .0005), replace=False)
iot["valid"] = True
iot.loc[glitch, "valid"] = False
out = iot.copy()
out["temp"] = np.where(out.device_id.isin(f_devs), (out.temp_c * 9 / 5 + 32).round(2), out.temp_c)
out.loc[glitch, "temp"] = 999.9
plus8 = rng.random(len(out)) < .2
out["ts_s"] = np.where(plus8, (out.ts + pd.Timedelta(hours=8)).dt.strftime("%Y-%m-%dT%H:%M:%S+08:00"), out.ts.dt.strftime("%Y-%m-%dT%H:%M:%SZ"))
out = out[["device_id", "ts_s", "temp"]].rename(columns={"ts_s": "ts"})
dups = out.sample(frac=.005, random_state=17)
out = pd.concat([out, dups])
chunks = np.array_split(np.arange(len(out)), 200)
rng.shuffle(chunks)
out = out.iloc[np.concatenate(chunks)]
(DATA / "iot").mkdir(exist_ok=True)
with gzip.GzipFile(DATA / "iot/readings.csv.gz", "wb", mtime=0) as gz:
    gz.write(out.to_csv(index=False).encode("utf-8"))
T["iot"], T["devices"], T["f_devs"], T["outages"] = iot, devs, f_devs, outages

# =============================================================== 营销触点与转化
N_U = 20000
CH = ["paid_search", "social", "email", "affiliate", "display", "direct"]
CH_P = [.28, .24, .16, .08, .14, .10]
tp_rows, cv_rows = [], []
Y0 = datetime(2024, 1, 1)
for u in range(1, N_U + 1):
    uid = f"U{u:05d}"
    n = rng.poisson(5)
    ts = sorted(Y0 + timedelta(seconds=int(x)) for x in rng.integers(0, 366 * 86400, n))
    first_ch = None
    for i, t in enumerate(ts):
        if i == 0:
            ch = str(pick(CH, [.2, .4, .05, .1, .2, .05]))
        elif i == n - 1:
            ch = str(pick(CH, [.25, .1, .35, .1, .05, .15]))
        else:
            ch = str(pick(CH, CH_P))
        tp_rows.append([uid, t, ch, f"{ch[:3].upper()}-{int(rng.integers(1, 6))}"])
    p = min(.04 + .025 * n, .35)
    if ts and rng.random() < p:
        t = ts[-1] + timedelta(seconds=int(rng.integers(600, 5 * 86400)))
        if t < datetime(2025, 1, 1):
            cv_rows.append([uid, t, round(float(np.exp(rng.normal(5.2, .7))), 2)])
            if rng.random() < .15:
                t2 = t + timedelta(days=int(rng.integers(5, 60)))
                if t2 < datetime(2025, 1, 1):
                    k = rng.poisson(1)
                    for x in range(k):
                        tp_rows.append([uid, t + (t2 - t) * float(rng.uniform(.1, .9)), str(pick(CH, CH_P)), "RET-1"])
                    cv_rows.append([uid, t2, round(float(np.exp(rng.normal(5.0, .7))), 2)])
    elif not ts and rng.random() < .02:
        cv_rows.append([uid, Y0 + timedelta(seconds=int(rng.integers(0, 365 * 86400))), round(float(np.exp(rng.normal(5.0, .7))), 2)])
tp = pd.DataFrame(tp_rows, columns=["user_id", "ts", "channel", "campaign"])
cv = pd.DataFrame(cv_rows, columns=["user_id", "ts", "revenue"])
cv.insert(0, "conversion_id", [f"CV{i:05d}" for i in range(1, len(cv) + 1)])
spend = []
for d in pd.date_range("2024-01-01", "2024-12-31"):
    for ch, base in {"paid_search": 2600, "social": 1800, "email": 300, "affiliate": 700, "display": 1200}.items():
        spend.append([d.strftime("%Y-%m-%d"), ch, round(base * float(rng.uniform(.7, 1.3)), 2)])
W("marketing/touchpoints.csv", tp.assign(ts=tp.ts.map(lambda t: t.strftime("%Y-%m-%d %H:%M:%S"))).sample(frac=1, random_state=18))
W("marketing/conversions.csv", cv.assign(ts=cv.ts.map(lambda t: t.strftime("%Y-%m-%d %H:%M:%S"))))
W("marketing/spend.csv", pd.DataFrame(spend, columns=["date", "channel", "spend"]))
T["tp"], T["cv"], T["spend"] = tp, cv, pd.DataFrame(spend, columns=["date", "channel", "spend"])

# =============================================================== 实验
N_X = 40000
var = pick(["A", "B"], [.5, .5], N_X)
seg = np.where(rng.random(N_X) < np.where(var == "B", .65, .35), "new", "returning")
pc = np.select([(var == "A") & (seg == "new"), (var == "B") & (seg == "new"), (var == "A") & (seg == "returning")], [.05, .058, .15], .162)
pre = np.round(np.exp(rng.normal(3.5, .8, N_X)) * np.where(seg == "new", .4, 1.0), 2)
post = np.round(np.clip(.6 * pre + rng.normal(10, 15, N_X) + np.where(var == "B", 2.0, 0), 0, None), 2)
abx = pd.DataFrame({"user_id": [f"X{i:05d}" for i in range(1, N_X + 1)], "variant": var, "segment": seg,
                    "converted": (rng.random(N_X) < pc).astype(int), "pre_revenue": pre, "post_revenue": post})
W("experiments/ab_users.csv", abx)
did = []
treated = set(rng.choice(40, 15, replace=False))
for s in range(40):
    fe = float(rng.uniform(8000, 20000))
    for w in range(1, 21):
        tr = s in treated
        did.append([f"ST{s + 1:02d}", w, int(tr), round(fe * (1 + .01 * w) * (1.08 if tr and w >= 11 else 1) * float(rng.normal(1, .03)), 2)])
did = pd.DataFrame(did, columns=["store_id", "week", "treated", "sales"])
W("experiments/did_stores.csv", did)
N_M = 10000
mv = pick(["A", "B"], [.5, .5], N_M)
mm = pd.DataFrame({"user_id": [f"Y{i:05d}" for i in range(1, N_M + 1)], "variant": mv})
eff = {"m01": .08, "m04": .06, "m07": .05, "m10": .025}
for k in range(1, 13):
    c = f"m{k:02d}"
    mm[c] = np.round(rng.normal(1, 1, N_M) + np.where(mv == "B", eff.get(c, 0), 0), 4)
W("experiments/multi_metric.csv", mm)
T["abx"], T["did"], T["mm"] = abx, did, mm

# =============================================================== Nginx 访问日志
EP = [("GET", "/api/products/{id}", .30, -2.6, .5), ("GET", "/api/products?category={cat}", .15, -2.2, .5),
      ("POST", "/api/cart", .12, -2.0, .6), ("GET", "/api/orders/{id}", .10, -1.9, .5),
      ("POST", "/api/checkout", .05, -.9, .7), ("GET", "/static/{file}", .20, -4.0, .4), ("GET", "/health", .08, -5.0, .3)]
UA_H = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/129.0", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5) Safari/604.1",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) Safari/605.1", "Mozilla/5.0 (Linux; Android 14) Chrome/128.0"]
UA_B = ["Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)", "Mozilla/5.0 (compatible; bingbot/2.0)",
        "Mozilla/5.0 (compatible; AhrefsBot/7.0)", "Baiduspider+(+http://www.baidu.com/search/spider.htm)", "python-requests/2.32 crawler"]
ips_h = [f"{rng.integers(1, 223)}.{rng.integers(0, 256)}.{rng.integers(0, 256)}.{rng.integers(1, 255)}" for _ in range(5000)]
ips_b = [f"66.249.{rng.integers(0, 256)}.{rng.integers(1, 255)}" for _ in range(30)]
ipw = 1 / np.arange(1, 5001) ** .9
ipw /= ipw.sum()
L0 = datetime(2024, 10, 14, tzinfo=UTC)
NL = 300000
hp = np.array([3, 2, 1, .6, .5, .7, 1.5, 3, 5, 6, 6.5, 6, 6, 6, 6.5, 6, 6, 6.5, 7, 8, 8.5, 8, 6, 4.5])  # 按北京时间
hp /= hp.sum()
day = rng.integers(0, 7, NL)
hr_bj = rng.choice(24, NL, p=hp)
sec = rng.integers(0, 3600, NL)
ts_utc = [L0 + timedelta(days=int(d), hours=int(h) - 8, seconds=int(s)) for d, h, s in zip(day, hr_bj, sec)]
log_rows = []
for i in range(NL):
    t = ts_utc[i]
    if not (L0 <= t < L0 + timedelta(days=7)):
        t = t + timedelta(days=7) if t < L0 else t - timedelta(days=7)
    bot = rng.random() < .15
    ip = ips_b[int(rng.integers(30))] if bot else ips_h[int(rng.choice(5000, p=ipw))]
    ua = UA_B[int(rng.integers(len(UA_B)))] if bot else UA_H[int(rng.integers(len(UA_H)))]
    e = EP[int(rng.choice(len(EP), p=[x[2] for x in EP]))]
    path = e[1].replace("{id}", str(int(rng.integers(1, 5000)))).replace("{cat}", str(rng.choice(CATS))).replace("{file}", f"app.{int(rng.integers(1, 9))}.js")
    rt = float(np.exp(rng.normal(e[3], e[4])))
    spike = datetime(2024, 10, 15, 6, tzinfo=UTC) <= t < datetime(2024, 10, 15, 7, tzinfo=UTC) and e[1] in ("/api/checkout", "/api/cart")
    st = 503 if rng.random() < (.30 if spike else .005) else (404 if rng.random() < .02 else (201 if e[0] == "POST" else 200))
    if st >= 500:
        rt *= 3
    log_rows.append((t, ip, e[0], path, e[1], st, int(rng.integers(200, 50000)), ua, round(rt, 3), bot, rng.random() < .3))
logs = pd.DataFrame(log_rows, columns=["ts", "ip", "method", "path", "route", "status", "bytes", "ua", "rt", "is_bot", "west"])
lines_a, lines_b = [], []
logs = logs.sort_values("ts").reset_index(drop=True)
logs["malformed"] = rng.random(len(logs)) < .003
for r in logs.itertuples():
    tz = timezone(timedelta(hours=-7)) if r.west else timezone(timedelta(hours=8))
    tl = r.ts.astimezone(tz).strftime("%d/%b/%Y:%H:%M:%S %z")
    ln = f'{r.ip} - - [{tl}] "{r.method} {r.path} HTTP/1.1" {r.status} {r.bytes} "-" "{r.ua}" {r.rt:.3f}'
    if r.malformed:
        ln = ln[:int(rng.integers(10, len(ln) - 30))]
    (lines_b if r.west else lines_a).append(ln)
(DATA / "logs").mkdir(exist_ok=True)
(DATA / "logs/access.log").write_text("\n".join(lines_a + lines_b) + "\n", encoding="utf-8")
T["logs"] = logs

# =============================================================== 总账（定长格式）
COA = [("1001", "库存现金", "asset", "debit"), ("1002", "银行存款", "asset", "debit"), ("1122", "应收账款", "asset", "debit"),
       ("1405", "库存商品", "asset", "debit"), ("1601", "固定资产", "asset", "debit"), ("2202", "应付账款", "liability", "credit"),
       ("2211", "应付职工薪酬", "liability", "credit"), ("2221", "应交税费", "liability", "credit"), ("4001", "实收资本", "equity", "credit"),
       ("6001", "主营业务收入", "revenue", "credit"), ("6051", "其他业务收入", "revenue", "credit"), ("6401", "主营业务成本", "expense", "debit"),
       ("6601", "销售费用", "expense", "debit"), ("6602", "管理费用", "expense", "debit"), ("6603", "财务费用", "expense", "debit")]
coa = pd.DataFrame(COA, columns=["account", "name", "type", "normal_balance"])
W("finance/chart_of_accounts.csv", coa)
TEMPL = [("6001", "1122", "销售收入"), ("6051", "1002", "其他收入"), ("1002", "1122", "回款"), ("6401", "1405", "结转成本"),
         ("6601", "1002", "广告费"), ("6602", "2211", "计提工资"), ("6603", "1002", "手续费"), ("1405", "2202", "采购入库"), ("2202", "1002", "支付货款")]
gl = []
for j in range(1, 3001):
    d = pd.Timestamp("2024-01-01") + pd.Timedelta(days=int(rng.integers(0, 366)))
    a1, a2, desc = TEMPL[int(rng.integers(len(TEMPL)))]
    amt = round(float(np.exp(rng.normal(8.5, 1.0))), 2)
    if a1 in ("6001", "6051"):
        lines_ = [(a2, amt), (a1, -amt)]
        if rng.random() < .5:
            tax = round(amt * .13, 2)
            lines_ = [(a2, round(amt + tax, 2)), (a1, -amt), ("2221", -tax)]
    else:
        lines_ = [(a1, amt), (a2, -amt)]
    for ln, (acc, v) in enumerate(lines_, 1):
        gl.append({"journal_id": f"JE{j:06d}", "line_no": ln, "date": d, "account": acc, "dept": str(rng.choice(["D010", "D020", "D030"])),
                   "currency": "CNY", "amount": v, "desc": desc, "date_ok": True})
gl = pd.DataFrame(gl)
unbal = rng.choice(gl.journal_id.unique(), 6, replace=False)
for j in unbal:
    i = gl.index[gl.journal_id == j][0]
    gl.loc[i, "amount"] = round(gl.loc[i, "amount"] + float(rng.choice([-1, 1]) * rng.uniform(10, 500)), 2)
bad_d = rng.choice(gl.index, 15, replace=False)
gl.loc[bad_d, "date_ok"] = False
fixed = []
for r in gl.itertuples():
    ds = r.date.strftime("%Y%m%d") if r.date_ok else str(rng.choice(["20240230", "20241301", "20240931", "20240000"]))
    a = abs(r.amount)
    s = f"{a:,.2f}" if rng.random() < .05 else f"{a:.2f}"
    s = s + ("-" if r.amount < 0 else " ")
    fixed.append(f"{r.journal_id:<10}{r.line_no:>4}{ds:8}{r.account:<8}{r.dept:<4}{r.currency:3}{s:>16}{r.desc:<40}")
(DATA / "finance/gl_2024.txt").write_text("\n".join(fixed) + "\n", encoding="utf-8")
T["gl"], T["coa"], T["unbal"] = gl, coa, sorted(unbal)

with open(TRUTH / "truth.pkl", "wb") as f:
    pickle.dump(T, f)
tot = 0
for p in sorted(DATA.rglob("*")):
    if p.is_file():
        tot += p.stat().st_size
        print(f"{str(p.relative_to(DATA)):<40} {p.stat().st_size / 1024:>9.1f} KB")
print(f"合计 {tot / 1024 / 1024:.1f} MB；订单 {len(orders)}（旧 {sum(orders.src == 'L')}，新 {sum(orders.src == 'A')}），明细 {len(items)}，IoT {len(iot)}，日志 {len(logs)}")

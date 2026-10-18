#!/usr/bin/env python3
"""生成带脏数据的电商数据集。

data/   模型可见的脏数据（CSV + README.md）
truth/  干净真值（pickle），标准答案只从这里计算，不依赖任何清洗代码
"""

import pickle
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
DATA = HERE / "data"
TRUTH = HERE / "truth"
DATA.mkdir(exist_ok=True)
TRUTH.mkdir(exist_ok=True)

rng = np.random.default_rng(20261018)


def pick(options, p, n):
    return rng.choice(np.array(options, dtype=object), size=n, p=p)


SURNAMES = list("王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾萧田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤")
GIVEN = list("伟芳娜敏静丽强磊军洋勇艳杰娟涛明超秀霞平刚桂英华玉兰萍红鹏辉建林云飞浩宇欣怡梓涵子轩雨晨思佳嘉琪婷雪颖博文斌")
SW = 1 / np.arange(1, len(SURNAMES) + 1) ** 0.8
SW /= SW.sum()


def gen_name():
    return rng.choice(SURNAMES, p=SW) + "".join(rng.choice(GIVEN, rng.choice([1, 2], p=[.3, .7])))


def gen_phone():
    return "1" + rng.choice(list("3456789")) + "".join(rng.choice(list("0123456789"), 9))


CITIES = [("北京", "Beijing"), ("上海", "Shanghai"), ("广州", "Guangzhou"), ("深圳", "Shenzhen"),
          ("杭州", "Hangzhou"), ("成都", "Chengdu"), ("武汉", "Wuhan"), ("南京", "Nanjing"),
          ("西安", "Xi'an"), ("重庆", "Chongqing"), ("苏州", "Suzhou"), ("天津", "Tianjin"),
          ("长沙", "Changsha"), ("郑州", "Zhengzhou"), ("青岛", "Qingdao")]
CITY_W = np.array([14, 14, 10, 10, 8, 7, 6, 6, 5, 5, 4, 4, 3, 2, 2], float)
CITY_W /= CITY_W.sum()
PINYIN = dict(CITIES)

# ---------------------------------------------------------------- customers
N_C = 3000
cust = pd.DataFrame({"customer_id": [f"C{i:05d}" for i in range(1, N_C + 1)]})
cust["name"] = [gen_name() for _ in range(N_C)]
cust["gender"] = pick(["M", "F"], [.5, .5], N_C)
span = (pd.Timestamp("2004-12-31") - pd.Timestamp("1960-01-01")).days + 1
cust["birth_date"] = pd.Timestamp("1960-01-01") + pd.to_timedelta(rng.integers(0, span, N_C), unit="D")
cust["city"] = pick([c for c, _ in CITIES], CITY_W, N_C)
cust["signup_date"] = pd.Timestamp("2022-01-01") + pd.to_timedelta(rng.integers(0, 1096, N_C), unit="D")
cust["tier"] = pick(["金", "银", "铜", None], [.10, .25, .50, .15], N_C)

phones = []
for _ in range(N_C):
    p = gen_phone()
    r = rng.random()
    if r < .01:
        p = p[:-1]
    elif r < .02:
        p = p + str(rng.integers(0, 10))
    elif r < .03:
        p = "2" + p[1:]
    phones.append(p)
cust["phone"] = phones

DOMAINS = ["qq.com", "163.com", "gmail.com", "126.com", "outlook.com", "sina.com", "company.cn"]
DOM_P = [.35, .25, .10, .10, .08, .07, .05]
emails = []
for _ in range(N_C):
    user = "".join(rng.choice(list("abcdefghijklmnopqrstuvwxyz"), rng.integers(4, 9)))
    if rng.random() < .5:
        user += str(rng.integers(1, 1000))
    dom = rng.choice(DOMAINS, p=DOM_P)
    if rng.random() < .05:
        dom = dom.upper()
    r = rng.random()
    if r < .01:
        e = f"{user}#{dom}"
    elif r < .02:
        e = f"{user}@@{dom}"
    elif r < .03:
        e = f"{user}@{dom.split('.')[0]}"
    elif r < .04:
        e = f"@{dom}"
    else:
        e = f"{user}@{dom}"
    emails.append(e)
cust["email"] = emails

# 脏化
c_dirty = cust.copy()
c_dirty["name"] = [(" " + n if rng.random() < .5 else n + " ") if rng.random() < .06 else n for n in cust["name"]]
g_out, g_truth = [], []
for g in cust["gender"]:
    r = rng.random()
    if r < .05:
        g_out.append(""); g_truth.append(None)
    elif r < .35:
        g_out.append("男" if g == "M" else "女"); g_truth.append(g)
    else:
        g_out.append(g); g_truth.append(g)
c_dirty["gender"] = g_out
cust["gender"] = g_truth


def fmt_birth(d):
    r = rng.random()
    if r < .60:
        return d.strftime("%Y-%m-%d")
    if r < .85:
        return f"{d.year}/{d.month}/{d.day}"
    return f"{d.year}年{d.month}月{d.day}日"


c_dirty["birth_date"] = [fmt_birth(d) for d in cust["birth_date"]]


def fmt_city(c):
    r = rng.random()
    if r < .50:
        return c
    if r < .65:
        return c + "市"
    if r < .85:
        p = PINYIN[c]
        return rng.choice([p, p.lower(), p.upper()])
    return rng.choice([" " + c, c + " ", " " + c + " "])


c_dirty["city"] = [fmt_city(c) for c in cust["city"]]
c_dirty["signup_date"] = cust["signup_date"].dt.strftime("%Y-%m-%d")
c_dirty["tier"] = cust["tier"].fillna("")
c_dirty = c_dirty[["customer_id", "name", "gender", "birth_date", "city", "phone", "email", "signup_date", "tier"]]
dup = c_dirty.sample(80, random_state=1)
c_dirty = pd.concat([c_dirty, dup]).sample(frac=1, random_state=2)
c_dirty.to_csv(DATA / "customers.csv", index=False)

# ---------------------------------------------------------------- products
CATS = {
    "手机数码": (["手机", "耳机", "智能手表"], 7.6, .6),
    "电脑办公": (["笔记本", "显示器", "键盘鼠标"], 7.8, .6),
    "家用电器": (["空调", "冰箱", "小家电"], 7.4, .7),
    "服饰鞋包": (["男装", "女装", "箱包"], 5.3, .5),
    "美妆个护": (["护肤", "彩妆", "个护电器"], 5.0, .6),
    "食品生鲜": (["零食", "生鲜", "饮料"], 3.8, .5),
    "图书文娱": (["图书", "文具", "乐器"], 4.2, .7),
    "运动户外": (["运动鞋", "健身器材", "户外装备"], 5.8, .6),
}
BRANDS = ["华星", "米乐", "极光", "青松", "蓝鲸", "云帆", "锦程", "北辰", "星河", "山海", "朗逸", "优品", "嘉禾", "瑞丰", "辰光", "乐活"]
BRAND_W = np.linspace(2, 1, len(BRANDS))
BRAND_W /= BRAND_W.sum()
N_P = 400
prows = []
cat_names = list(CATS)
for i in range(1, N_P + 1):
    cat = rng.choice(cat_names)
    subs, mu, sig = CATS[cat]
    suffix = rng.choice(["", "Pro", "Max", "Lite", "Plus"], p=[.5, .15, .1, .1, .15])
    name = f"{rng.choice(BRANDS, p=BRAND_W)} {rng.choice(list('ABCDEFGHJKMNRSTXZ'))}{rng.integers(1, 100)}" + (f" {suffix}" if suffix else "")
    lp = max(round(float(np.exp(rng.normal(mu, sig))), 2), 1.0)
    prows.append({"product_id": f"P{i:04d}", "product_name": name, "category": cat, "subcategory": rng.choice(subs),
                  "list_price": lp, "cost": round(lp * rng.uniform(.4, .85), 2),
                  "supplier_id": f"S{rng.integers(1, 31):02d}",
                  "launch_date": pd.Timestamp("2020-01-01") + pd.Timedelta(days=int(rng.integers(0, 1827)))})
prod = pd.DataFrame(prows)
p_dirty = prod.copy()


def fmt_price(p):
    r = rng.random()
    if r < .4:
        return f"¥{p:,.2f}"
    if r < .7:
        return f"{p:,.2f}"
    return f"{p:.2f}"


p_dirty["list_price"] = [fmt_price(p) for p in prod["list_price"]]
p_dirty["launch_date"] = prod["launch_date"].dt.strftime("%Y-%m-%d")
p_dirty.to_csv(DATA / "products.csv", index=False)

pop = 1 / np.arange(1, N_P + 1) ** 0.9
rng.shuffle(pop)
pop /= pop.sum()
top50 = np.argsort(-pop)[:50]
pairs = rng.choice(top50, (5, 2), replace=False)
PAIR_MAP = {}
for a, b in pairs:
    PAIR_MAP[int(a)] = int(b)

# ---------------------------------------------------------------- fx
bdays = pd.bdate_range("2022-12-26", "2024-12-31")
keep = np.ones(len(bdays), bool)
keep[rng.choice(np.arange(5, len(bdays)), 12, replace=False)] = False
bdays = bdays[keep]
n = len(bdays)
usd = np.clip(6.95 + np.cumsum(rng.normal(0.0006, 0.01, n)), 6.7, 7.4).round(4)
hkd = (usd / 7.81 + rng.normal(0, 0.0008, n)).round(4)
fx = pd.concat([pd.DataFrame({"date": bdays, "currency": "USD", "rate": usd}),
                pd.DataFrame({"date": bdays, "currency": "HKD", "rate": hkd})]).sort_values(["date", "currency"]).reset_index(drop=True)
fx_out = fx.rename(columns={"rate": "rate_to_cny"}).copy()
fx_out["date"] = fx_out["date"].dt.strftime("%Y-%m-%d")
fx_out.to_csv(DATA / "fx_rates.csv", index=False)


def rate_at(cur, day):
    if cur == "CNY":
        return 1.0
    f = fx[(fx.currency == cur) & (fx.date <= day)]
    return float(f.iloc[-1]["rate"])


FX_LOOKUP = {cur: fx[fx.currency == cur].set_index("date")["rate"] for cur in ["USD", "HKD"]}


def rate_fast(cur, day):
    if cur == "CNY":
        return 1.0
    s = FX_LOOKUP[cur]
    return float(s.iloc[s.index.searchsorted(day, side="right") - 1])

# ---------------------------------------------------------------- orders
HOUR_P = np.array([2, 1, .6, .4, .3, .4, .8, 2, 3.5, 4.5, 5, 5, 5.5, 4.5, 4, 4, 4.2, 4.5, 5, 6, 7.5, 8, 6.5, 4], float)
HOUR_P /= HOUR_P.sum()
N_O = 25000
w = rng.pareto(1.2, N_C) + 0.05
cidx = rng.choice(N_C, N_O, p=w / w.sum())
end_day = pd.Timestamp("2024-12-31")
orows = []
for ci in cidx:
    start = max(cust.at[ci, "signup_date"], pd.Timestamp("2023-01-01"))
    day = start + pd.Timedelta(days=int(rng.integers(0, (end_day - start).days + 1)))
    orows.append((cust.at[ci, "customer_id"], day))
before = rng.choice([i for i, ci in enumerate(cidx) if cust.at[ci, "signup_date"] >= pd.Timestamp("2023-03-01")], 30, replace=False)
for i in before:
    cid_, _ = orows[i]
    su = cust.loc[cust.customer_id == cid_, "signup_date"].iloc[0]
    d = su - pd.Timedelta(days=int(rng.integers(1, 61)))
    orows[i] = (cid_, max(d, pd.Timestamp("2023-01-01")))
for k in range(40):
    day = pd.Timestamp("2023-01-01") + pd.Timedelta(days=int(rng.integers(0, 731)))
    orows.append((f"C9{k:04d}", day))
orders = pd.DataFrame(orows, columns=["customer_id", "day"])
no = len(orders)
orders["ts"] = (orders["day"] + pd.to_timedelta(rng.choice(24, no, p=HOUR_P), unit="h")
                + pd.to_timedelta(rng.integers(0, 60, no), unit="m") + pd.to_timedelta(rng.integers(0, 60, no), unit="s"))
orders = orders.drop(columns="day").sort_values("ts", kind="stable").reset_index(drop=True)
orders.insert(0, "order_id", [f"O{i:06d}" for i in range(1, no + 1)])
orders["status"] = pick(["paid", "refunded", "cancelled"], [.85, .08, .07], no)
orders["channel"] = pick(["app", "web", "mini_program"], [.55, .25, .20], no)
orders["currency"] = pick(["CNY", "USD", "HKD"], [.92, .05, .03], no)
orders["shipping_fee"] = pick([0, 6, 10, 15], [.4, .3, .2, .1], no).astype(int)
orders["coupon_code"] = pick(["", "NEW10", "VIP20", "FS", "SALE15"], [.70, .08, .07, .08, .07], no)
orders["time_fmt"] = pick(["bj_dash", "bj_slash", "utc"], [.5, .25, .25], no)
orders["rate"] = [rate_fast(c, t.normalize()) for c, t in zip(orders.currency, orders.ts)]

o_dirty = orders[["order_id", "customer_id"]].copy()
o_dirty["order_time"] = [t.strftime("%Y-%m-%d %H:%M:%S") if f == "bj_dash" else
                         t.strftime("%Y/%m/%d %H:%M:%S") if f == "bj_slash" else
                         (t - pd.Timedelta(hours=8)).strftime("%Y-%m-%dT%H:%M:%SZ")
                         for t, f in zip(orders.ts, orders.time_fmt)]
o_dirty["status"] = [rng.choice([s, s, s.upper(), s.capitalize(), " " + s, s + " "]) for s in orders.status]
for c in ["channel", "currency", "shipping_fee", "coupon_code"]:
    o_dirty[c] = orders[c]
o_dirty = pd.concat([o_dirty, o_dirty.sample(150, random_state=3)]).sample(frac=1, random_state=4)
o_dirty.to_csv(DATA / "orders.csv", index=False)

# ---------------------------------------------------------------- order_items
lp_arr = prod["list_price"].to_numpy()
irows = []
for oid, cur, rate in zip(orders.order_id, orders.currency, orders.rate):
    k = min(1 + rng.poisson(0.8), 5)
    chosen = list(rng.choice(N_P, k, replace=False, p=pop))
    for a in list(chosen):
        b = PAIR_MAP.get(int(a))
        if b is not None and b not in chosen and rng.random() < .6:
            chosen.append(b)
    for ln, pi in enumerate(chosen, 1):
        q = int(rng.choice([1, 2, 3, 4, 5], p=[.7, .15, .08, .04, .03]))
        if rng.random() < .005:
            q = int(rng.choice([0, -1]))
        up = round(lp_arr[pi] * rng.uniform(.85, 1.0) / rate, 2)
        irows.append([oid, ln, f"P{pi + 1:04d}", q, up, float(rng.choice([0, .05, .1, .2], p=[.5, .2, .2, .1]))])
items = pd.DataFrame(irows, columns=["order_id", "line_no", "product_id", "quantity", "unit_price", "discount_rate"])
typo = rng.choice(items.index[items.quantity > 0], 20, replace=False)
items.loc[typo, "unit_price"] = (items.loc[typo, "unit_price"] * 10).round(2)
orph = pd.DataFrame([[f"O99{k:04d}", 1, f"P{rng.integers(1, N_P + 1):04d}", 1, 99.0, 0.0] for k in range(1, 26)], columns=items.columns)
items = pd.concat([items, orph], ignore_index=True)
i_dirty = pd.concat([items, items.sample(15, random_state=5)]).sample(frac=1, random_state=6)
i_dirty.to_csv(DATA / "order_items.csv", index=False)

# ---------------------------------------------------------------- events
users = cust[cust.signup_date <= "2024-06-30"].sample(1500, random_state=7)["customer_id"].tolist()
B0 = pd.Timestamp("2024-01-01 00:00:00")
SPAN = (pd.Timestamp("2024-12-31 20:00:00") - B0).total_seconds()
erows, sid = [], 0
for u in users:
    starts = np.sort(rng.uniform(0, SPAN, rng.poisson(6) + 1))
    last_end = -1e18
    for s in starts:
        s = max(s, last_end + 2700 + rng.uniform(0, 3600))
        if s > SPAN:
            break
        sid += 1
        seq = ["view"] * int(rng.integers(1, 9))
        if rng.random() < .35:
            seq.append("add_to_cart")
            if rng.random() < .5:
                seq.append("checkout")
                if rng.random() < .7:
                    seq.append("purchase")
        t, viewed, target = s, [], None
        for j, et in enumerate(seq):
            if j > 0:
                t += rng.uniform(5, 900)
            if et == "view":
                pid = int(rng.choice(N_P, p=pop)); viewed.append(pid)
            else:
                if target is None:
                    target = int(rng.choice(viewed))
                pid = target
            ms = int(round(((B0 + pd.Timedelta(seconds=t)) - pd.Timedelta(hours=8) - pd.Timestamp("1970-01-01")).total_seconds() * 1000))
            erows.append((u, ms, et, f"P{pid + 1:04d}", sid))
        last_end = t
events = pd.DataFrame(erows, columns=["user_id", "event_ms", "event_type", "product_id", "session_id"])
events["ts"] = pd.to_datetime(events.event_ms, unit="ms") + pd.Timedelta(hours=8)
anom = []
for k in range(20):
    u = rng.choice(users)
    if k < 6:
        ms = int(rng.integers(0, 10 ** 9))
    elif k < 12:
        ms = int((pd.Timestamp("2099-01-01") - pd.Timestamp("1970-01-01")).total_seconds() * 1000) + int(rng.integers(0, 10 ** 9))
    elif k < 16:  # 北京时间 2023-12-31 22:00~23:59
        bj = pd.Timestamp("2023-12-31 22:00:00") + pd.Timedelta(seconds=int(rng.integers(0, 7200)))
        ms = int((bj - pd.Timedelta(hours=8) - pd.Timestamp("1970-01-01")).total_seconds() * 1000)
    else:  # 北京时间 2025-01-01 00:00~01:59
        bj = pd.Timestamp("2025-01-01 00:00:00") + pd.Timedelta(seconds=int(rng.integers(0, 7200)))
        ms = int((bj - pd.Timedelta(hours=8) - pd.Timestamp("1970-01-01")).total_seconds() * 1000)
    anom.append((u, ms, "view", f"P{rng.integers(1, N_P + 1):04d}"))
e_dirty = pd.concat([events[["user_id", "event_ms", "event_type", "product_id"]],
                     pd.DataFrame(anom, columns=["user_id", "event_ms", "event_type", "product_id"])])
e_dirty = e_dirty.rename(columns={"event_ms": "event_time"}).sample(frac=1, random_state=8)
e_dirty.to_csv(DATA / "events.csv", index=False)

# ---------------------------------------------------------------- daily_kpi
dates = pd.date_range("2023-01-01", "2024-12-31")
nd = len(dates)
t = np.arange(nd)
weekly = np.array([-300, -200, -150, -100, 200, 800, 700])[dates.dayofweek]
dau = 10000 + 8 * t + weekly + rng.normal(0, 250, nd)
cand = np.arange(30, nd - 30)
anom_idx = []
while len(anom_idx) < 6:
    i = int(rng.choice(cand))
    if all(abs(i - j) > 20 for j in anom_idx):
        anom_idx.append(i)
for k, i in enumerate(sorted(anom_idx)):
    dau[i] *= 1.7 if k % 2 == 0 else 0.45
dau = dau.round().astype(int)
revenue = (dau * rng.normal(12, 0.8, nd) + rng.normal(0, 3000, nd)).round(2)
blocked = set()
for i in anom_idx:
    blocked |= set(range(i - 4, i + 5))
neg_idx = []
while len(neg_idx) < 3:
    i = int(rng.choice(cand))
    if i not in blocked and i not in neg_idx:
        neg_idx.append(i)
revenue[neg_idx] = -np.abs(revenue[neg_idx])
blocked |= set(neg_idx)
miss_idx = []
while len(miss_idx) < 15:
    i = int(rng.integers(5, nd - 5))
    if i not in blocked and i not in miss_idx:
        miss_idx.append(i)
kpi = pd.DataFrame({"date": dates, "dau": dau, "revenue": revenue}).drop(index=miss_idx).reset_index(drop=True)
k_out = kpi.copy()
k_out["date"] = k_out["date"].dt.strftime("%Y-%m-%d")
k_out.to_csv(DATA / "daily_kpi.csv", index=False)

# ---------------------------------------------------------------- legacy_sales (GBK, ';')
STORES = [("北京一店", "华北"), ("北京二店", "华北"), ("上海一店", "华东"), ("上海二店", "华东"), ("广州一店", "华南"),
          ("深圳一店", "华南"), ("杭州一店", "华东"), ("成都一店", "西南"), ("武汉一店", "华中"), ("南京一店", "华东"),
          ("西安一店", "西北"), ("重庆一店", "西南")]
months = pd.period_range("2023-01", "2024-12", freq="M")
lrows = []
for s, region in STORES:
    base = rng.uniform(0.8e6, 3e6)
    g = rng.normal(0.004, 0.012)
    for ti, m in enumerate(months):
        season = 1 + 0.15 * np.sin(2 * np.pi * (m.month - 3) / 12) + (0.2 if m.month == 12 else 0)
        lrows.append([s, region, str(m), round(base * season * (1 + g) ** ti * rng.normal(1, .05), 2)])
legacy = pd.DataFrame(lrows, columns=["store", "region", "month", "sales"])
spike = rng.choice(len(legacy), 3, replace=False)
legacy.loc[spike, "sales"] = (legacy.loc[spike, "sales"] * 1.8).round(2)
na_idx = rng.choice([i for i in range(len(legacy)) if i not in spike], 4, replace=False)
legacy.loc[na_idx, "sales"] = np.nan
with open(DATA / "legacy_sales.csv", "w", encoding="gbk", newline="") as f:
    f.write("门店;区域;月份;销售额\n")
    for r in legacy.itertuples():
        f.write(f"{r.store};{r.region};{r.month};{'N/A' if pd.isna(r.sales) else f'{r.sales:,.2f}'}\n")

# ---------------------------------------------------------------- ab_test
N_AB = 20000
ab = pd.DataFrame({"user_id": [f"U{i:05d}" for i in range(1, N_AB + 1)], "group": pick(["A", "B"], [.5, .5], N_AB)})
pconv = np.where(ab.group == "A", .100, .109)
ab["converted"] = (rng.random(N_AB) < pconv).astype(int)
rev = np.where(ab.group == "A", rng.lognormal(4.8, .6, N_AB), rng.lognormal(4.85, .6, N_AB)).round(2)
ab["revenue"] = np.where(ab.converted == 1, rev, 0.0)
contam = ab.sample(30, random_state=9).copy()
contam["group"] = contam["group"].map({"A": "B", "B": "A"})
contam["converted"] = (rng.random(30) < .1).astype(int)
contam["revenue"] = np.where(contam.converted == 1, rng.lognormal(4.8, .6, 30).round(2), 0.0)
ab_dirty = pd.concat([ab, contam]).sample(frac=1, random_state=10)
ab_dirty.to_csv(DATA / "ab_test.csv", index=False)
ab_clean = ab[~ab.user_id.isin(contam.user_id)].reset_index(drop=True)

# ---------------------------------------------------------------- employees
N_E = 300
DEPTS = ["研发", "市场", "销售", "运营", "财务", "人力"]
erows2 = [{"emp_id": "E001", "dept": "总裁办", "manager_id": None, "depth": 1}]
for i, d in enumerate(DEPTS):
    erows2.append({"emp_id": f"E{i + 2:03d}", "dept": d, "manager_id": "E001", "depth": 2})
DW = {2: 3.0, 3: 2.0, 4: 1.2, 5: 0.5}
for i in range(len(erows2) + 1, N_E + 1):
    cands = [e for e in erows2 if 2 <= e["depth"] <= 5]
    ww = np.array([DW[e["depth"]] for e in cands])
    m = cands[rng.choice(len(cands), p=ww / ww.sum())]
    erows2.append({"emp_id": f"E{i:03d}", "dept": m["dept"], "manager_id": m["emp_id"], "depth": m["depth"] + 1})
emp = pd.DataFrame(erows2)
BASE = {1: 150000, 2: 60000, 3: 35000, 4: 25000, 5: 18000, 6: 14000}
emp["name"] = [gen_name() for _ in range(N_E)]
emp["salary"] = [round(BASE[d] * rng.uniform(.75, 1.35), -2) for d in emp.depth]
emp["hire_date"] = [pd.Timestamp("2010-01-01")] + [pd.Timestamp("2010-01-01") + pd.Timedelta(days=int(rng.integers(0, 5479))) for _ in range(N_E - 1)]
has_reports = set(emp.manager_id.dropna())
leaves = emp[(~emp.emp_id.isin(has_reports)) & (emp.depth >= 3)].index
orphans = rng.choice(leaves, 2, replace=False)
e_dirty2 = emp.copy()
e_dirty2.loc[orphans[0], "manager_id"] = "E998"
e_dirty2.loc[orphans[1], "manager_id"] = "E999"
emp.loc[orphans, "manager_id"] = None
emp["orphan"] = False
emp.loc[orphans, "orphan"] = True
miss_sal = rng.choice(emp.index[1:], 5, replace=False)
emp.loc[miss_sal, "salary"] = np.nan
e_dirty2["salary"] = emp["salary"]
e_dirty2["manager_id"] = e_dirty2["manager_id"].fillna("")
e_dirty2["hire_date"] = emp["hire_date"].dt.strftime("%Y-%m-%d")
e_dirty2["salary"] = e_dirty2["salary"].map(lambda v: "" if pd.isna(v) else f"{v:.0f}")
e_dirty2[["emp_id", "name", "dept", "manager_id", "salary", "hire_date"]].to_csv(DATA / "employees.csv", index=False)

# ---------------------------------------------------------------- support_tickets
ISSUES = ["物流一直没有更新，配送延迟了好几天", "收到的商品有破损，申请退款", "想修改收货地址", "优惠券无法使用",
          "退款还没到账，请尽快处理", "客服回复太慢", "商品与描述不符，要求退款", "发票开错了，需要重开",
          "物流延迟，麻烦催一下", "咨询会员积分规则", "快递显示已签收但没收到", "商品质量有问题，想换货"]
N_T = 1500
cand_orders = orders[(orders.ts <= "2024-12-01") & (~orders.customer_id.str.startswith("C9"))]
by_cust = orders.groupby("customer_id")["order_id"].apply(list).to_dict()
ts_by_oid = orders.set_index("order_id")["ts"].to_dict()
trows = []
for i in range(1, N_T + 1):
    refs = []
    if rng.random() < .6:
        o = cand_orders.iloc[int(rng.integers(0, len(cand_orders)))]
        cid_ = o.customer_id
        refs.append(o.order_id)
        others = [x for x in by_cust[cid_] if x != o.order_id]
        if others and rng.random() < .15:
            refs.append(others[int(rng.integers(0, len(others)))])
        created = o.ts + pd.Timedelta(seconds=int(rng.integers(3600, 20 * 86400)))
    else:
        cid_ = cust.customer_id.iloc[int(rng.integers(0, N_C))]
        created = pd.Timestamp("2023-03-01") + pd.Timedelta(seconds=int(rng.integers(0, 671 * 86400)))
    if rng.random() < .03:
        cid_ = None
    parts = []
    tag = rng.choice(["", "[P1]", "[P2]", "[P3]"], p=[.2, .16, .4, .24])
    main = rng.choice(ISSUES)
    if refs:
        main = "订单" + "和订单".join(refs) + "，" + main
    text = tag + main
    if rng.random() < .15:
        text += f"，联系电话{gen_phone()}"
    if rng.random() < .25:
        amt = round(float(rng.uniform(10, 5000)), 2)
        text += f"，金额¥{amt:.2f}" if rng.random() < .5 else f"，涉及金额{amt:.2f}元"
    trows.append({"ticket_id": f"T{i:05d}", "customer_id": cid_, "created": created,
                  "channel": rng.choice(["电话", "在线", "邮件"]), "text": text, "refs": refs})
tk = pd.DataFrame(trows)
t_dirty = tk[["ticket_id", "customer_id"]].copy()
t_dirty["customer_id"] = t_dirty["customer_id"].fillna("")
t_dirty["created_at"] = [c.strftime("%Y-%m-%dT%H:%M:%S+08:00") if rng.random() < .7 else
                         (c - pd.Timedelta(hours=8)).strftime("%Y-%m-%dT%H:%M:%SZ") for c in tk.created]
t_dirty["channel"] = tk["channel"]
t_dirty["text"] = tk["text"]
t_dirty.to_csv(DATA / "support_tickets.csv", index=False)

# ---------------------------------------------------------------- README
README = """# 数据说明（必读）

除特别说明外，所有文件均为 UTF-8 编码、逗号分隔、首行为表头。

## 文件与字段
- customers.csv：customer_id, name, gender, birth_date, city, phone, email, signup_date, tier
- products.csv：product_id, product_name, category, subcategory, list_price, cost, supplier_id, launch_date
- orders.csv：order_id, customer_id, order_time, status, channel, currency, shipping_fee, coupon_code
- order_items.csv：order_id, line_no, product_id, quantity, unit_price, discount_rate
- fx_rates.csv：date, currency, rate_to_cny（只有工作日，且个别工作日缺失）
- events.csv：user_id, event_time, event_type, product_id（user_id 与 customer_id 同一体系）
- daily_kpi.csv：date, dau, revenue
- legacy_sales.csv：门店;区域;月份;销售额（GBK 编码、分号分隔）
- ab_test.csv：user_id, group, converted, revenue
- employees.csv：emp_id, name, dept, manager_id, salary, hire_date
- support_tickets.csv：ticket_id, customer_id, created_at, channel, text

## 统一口径（所有题目默认遵守）
1. 去重：customers、orders、order_items 中存在完全重复的行（所有字段都相同），任何统计前先整行去重。题目明确问“原始文件”时除外。
2. customers
   - name 需去除首尾空格。
   - gender：M 或 男 表示男性，F 或 女 表示女性，空值表示未知。
   - birth_date 有三种写法：2001-03-05、2001/3/5、2001年3月5日。
   - city 同一城市有多种写法（如 北京、北京市、Beijing、BEIJING、" 北京 "），统计时统一为不带“市”字的中文城市名，共 15 个城市。
   - 年龄：以 2025-01-01 为基准计算周岁。
   - tier：金 / 银 / 铜，空值表示无等级。
3. products.list_price 可能写成 "¥1,299.00"、"1,299.00" 或 "1299.00"，都是人民币金额；cost 也是人民币。
4. orders
   - order_time 以 Z 结尾的是 UTC 时间；其他写法（2024-01-05 10:00:00 或 2024/01/05 10:00:00）都是北京时间。凡是按日、周、月、小时统计，一律使用北京时间（UTC+8）。
   - status 忽略大小写和首尾空格后，取值为 paid / refunded / cancelled。“有效订单”指 paid 订单。
   - currency 取值为 CNY / USD / HKD。shipping_fee 和 order_items.unit_price 都按订单币种计价。
   - orders 中可能有 customer_id 不在 customers 表中的订单，它们仍是正常订单，参与订单层面的统计。
5. order_items
   - quantity ≤ 0 的行为无效行，所有金额和销量统计都忽略这些行。
   - 行金额 = quantity × unit_price × (1 − discount_rate)；订单商品金额 = 该订单有效行金额之和（没有有效行则为 0）；订单 GMV = 订单商品金额 + shipping_fee。
   - unit_price 以文件为准，不做任何修正。
   - 可能有 order_id 不在 orders 表中的行，它们不属于任何订单。
6. 汇率换算：把非 CNY 金额换算成人民币时，使用 fx_rates 中“订单北京时间日期当天”的 rate_to_cny；当天没有汇率时，使用该日期之前最近一个有汇率的日期。rate_to_cny 表示 1 单位外币兑换的人民币数；CNY 的汇率为 1。cost 和 list_price 本身就是人民币，不需要换算。
7. events.event_time 是 UTC 毫秒时间戳。转换为北京时间后不在 2024 年内的记录是异常记录，任何分析前先剔除。
8. daily_kpi 有部分日期缺失（文件中没有该日期的行）。revenue < 0 表示该行的 revenue 录入错误：只有 revenue 字段无效，该行的 dau 仍然有效，该日期也不算缺失。
9. legacy_sales.csv：GBK 编码、分号分隔，销售额带千分位逗号，个别值为 N/A（视为缺失）。
10. ab_test：同时出现在 A 组和 B 组的 user_id 为污染样本，分析时剔除这些用户的全部记录。
11. employees：manager_id 为空表示 CEO；manager_id 指向不存在员工的，视为没有上级（不属于以 CEO 为根的组织树）。salary 为月薪，可能缺失。
12. support_tickets.created_at 为 ISO 8601 格式，带 +08:00 或 Z（UTC）后缀；customer_id 可能为空。

## 其他约定
- 星期：周一 = 1 … 周日 = 7；ISO 周遵循 ISO 8601（周一为一周第一天）。
- 分位数：如无特别说明，使用线性插值（numpy.percentile / pandas.quantile 的默认方法）。
- 标准差、方差：如无特别说明，使用样本统计量（ddof=1）。
- 按题目要求的小数位四舍五入。
"""
(DATA / "README.md").write_text(README, encoding="utf-8")

# ---------------------------------------------------------------- truth
cust_t = cust.copy()
orders_t = orders.drop(columns=["time_fmt"]).copy()
orders_t["time_fmt"] = orders["time_fmt"]
truth = {
    "cust": cust_t, "prod": prod, "orders": orders_t, "items": items, "fx": fx,
    "events": events, "event_anomalies": len(anom), "kpi": kpi, "kpi_anomaly_dates": sorted(dates[anom_idx].strftime("%Y-%m-%d")),
    "legacy": legacy, "ab": ab_clean, "ab_contam": sorted(contam.user_id), "emp": emp, "tickets": tk,
    "pairs": [(f"P{a + 1:04d}", f"P{b + 1:04d}") for a, b in pairs],
}
with open(TRUTH / "truth.pkl", "wb") as f:
    pickle.dump(truth, f)

for p in sorted(DATA.iterdir()):
    print(f"{p.name:<22} {p.stat().st_size / 1024:>8.1f} KB")
print("orders", len(orders), "items", len(items), "events", len(events), "sessions", events.session_id.nunique())

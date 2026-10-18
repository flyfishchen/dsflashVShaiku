#!/usr/bin/env python3
"""Generate 200 test cases (10 levels × 20) for data processing evaluation"""

import json
import math
import statistics
import random
from datetime import date, timedelta

from decimal import Decimal, ROUND_HALF_UP

random.seed(42)

cases = []
cid = 1

def round(x, k=0):
    # 四舍五入（Python 内置 round 为银行家舍入，5.25 -> 5.2）
    v = float(Decimal(repr(float(x))).quantize(Decimal(1).scaleb(-k), rounding=ROUND_HALF_UP))
    return int(v) if k == 0 else v

def add(level, category, question, expected, atype="number"):
    global cid
    cases.append({
        "id": cid, "level": level, "category": category,
        "question": question + "\n\n只输出最终答案（数字或字符串），不要解释。",
        "expected": expected, "answer_type": atype
    })
    cid += 1

def rlist(n, lo, hi, seed):
    r = random.Random(seed)
    return [r.randint(lo, hi) for _ in range(n)]

# ============================================================
# LEVEL 1: Basic List/Array Operations
# ============================================================
L1_DATA = [
    rlist(10, 1, 50, s) for s in range(1, 21)
]

add(1,"基础运算", f"列表 {L1_DATA[0]}，求所有元素之和", sum(L1_DATA[0]))
add(1,"基础运算", f"列表 {L1_DATA[1]}，求最大值", max(L1_DATA[1]))
add(1,"基础运算", f"列表 {L1_DATA[2]}，求最小值", min(L1_DATA[2]))
add(1,"基础运算", f"列表 {L1_DATA[3]}，求元素个数", len(L1_DATA[3]), "integer")
add(1,"基础运算", f"列表 {L1_DATA[4]}，求最大值与最小值之差（范围）", max(L1_DATA[4]) - min(L1_DATA[4]))
add(1,"基础运算", f"列表 {L1_DATA[5]}，求所有偶数之和", sum(x for x in L1_DATA[5] if x % 2 == 0))
add(1,"基础运算", f"列表 {L1_DATA[6]}，求大于20的元素个数", sum(1 for x in L1_DATA[6] if x > 20), "integer")
add(1,"基础运算", f"列表 {L1_DATA[7]}，排序后第3个元素是什么", sorted(L1_DATA[7])[2])
add(1,"基础运算", f"列表 {L1_DATA[8]}，所有元素的平均值（保留2位小数）", round(sum(L1_DATA[8])/len(L1_DATA[8]), 2))
add(1,"基础运算", f"列表 {L1_DATA[9]}，中位数是多少（保留1位小数）", round(statistics.median(L1_DATA[9]), 1))
add(1,"基础运算", f"列表 {L1_DATA[10]}，值为奇数的元素有几个", sum(1 for x in L1_DATA[10] if x % 2 != 0), "integer")
add(1,"基础运算", f"列表 {L1_DATA[11]}，第二大的元素是多少", sorted(set(L1_DATA[11]), reverse=True)[1])
add(1,"基础运算", f"列表 {L1_DATA[12]}，所有元素之积对1000取模", eval('*'.join(map(str, L1_DATA[12]))) % 1000)
add(1,"基础运算", f"列表 {L1_DATA[13]}，降序排序后第一个元素是多少", sorted(L1_DATA[13], reverse=True)[0])
add(1,"基础运算", f"列表 {L1_DATA[14]}，有几个不同的值", len(set(L1_DATA[14])), "integer")
add(1,"基础运算", f"列表 {L1_DATA[15]}，出现次数最多的值是多少（若有多个取最小）", min(x for x, c in {v: L1_DATA[15].count(v) for v in L1_DATA[15]}.items() if c == max(L1_DATA[15].count(v) for v in set(L1_DATA[15]))))
add(1,"基础运算", f"列表 {L1_DATA[16]}，所有元素平方和", sum(x**2 for x in L1_DATA[16]))
add(1,"基础运算", f"列表 {L1_DATA[17]}，均值以上的元素有几个", sum(1 for x in L1_DATA[17] if x > sum(L1_DATA[17])/len(L1_DATA[17])), "integer")
add(1,"基础运算", f"列表 {L1_DATA[18]}，最大值与平均值的差（保留2位小数）", round(max(L1_DATA[18]) - sum(L1_DATA[18])/len(L1_DATA[18]), 2))
add(1,"基础运算", f"列表 {L1_DATA[19]}，所有元素之和与最大值的比值（保留2位小数）", round(sum(L1_DATA[19])/max(L1_DATA[19]), 2))

# ============================================================
# LEVEL 2: CSV Table Filtering
# ============================================================
CSV1 = """姓名,年龄,部门,薪资
Alice,28,技术,12000
Bob,35,市场,9500
Carol,42,技术,15000
Dave,31,HR,8000
Eve,26,技术,11000
Frank,38,市场,10500
Grace,29,HR,7500
Henry,45,技术,18000
Iris,33,市场,9000
Jack,27,技术,13000"""

rows1 = [r.split(',') for r in CSV1.strip().split('\n')[1:]]
employees = [{"name":r[0],"age":int(r[1]),"dept":r[2],"salary":int(r[3])} for r in rows1]

add(2,"数据过滤", f"表格数据：\n{CSV1}\n\n技术部门员工有几人？", sum(1 for e in employees if e["dept"]=="技术"), "integer")
add(2,"数据过滤", f"表格数据：\n{CSV1}\n\n年龄大于30的员工有几人？", sum(1 for e in employees if e["age"]>30), "integer")
add(2,"数据过滤", f"表格数据：\n{CSV1}\n\n薪资超过10000的员工有几人？", sum(1 for e in employees if e["salary"]>10000), "integer")
add(2,"数据过滤", f"表格数据：\n{CSV1}\n\n技术部门的平均薪资是多少（取整）？", round(sum(e["salary"] for e in employees if e["dept"]=="技术")/sum(1 for e in employees if e["dept"]=="技术")))
add(2,"数据过滤", f"表格数据：\n{CSV1}\n\n最高薪资员工的年龄是多少？", max(employees, key=lambda e: e["salary"])["age"])
add(2,"数据过滤", f"表格数据：\n{CSV1}\n\n市场部门的员工总人数？", sum(1 for e in employees if e["dept"]=="市场"), "integer")
add(2,"数据过滤", f"表格数据：\n{CSV1}\n\n年龄在28到35之间（含）的员工有几人？", sum(1 for e in employees if 28<=e["age"]<=35), "integer")
add(2,"数据过滤", f"表格数据：\n{CSV1}\n\n技术部门中薪资最高是多少？", max(e["salary"] for e in employees if e["dept"]=="技术"))
add(2,"数据过滤", f"表格数据：\n{CSV1}\n\n所有员工的平均年龄（保留1位小数）？", round(sum(e["age"] for e in employees)/len(employees), 1))
add(2,"数据过滤", f"表格数据：\n{CSV1}\n\nHR部门平均薪资是多少（取整）？", round(sum(e["salary"] for e in employees if e["dept"]=="HR")/sum(1 for e in employees if e["dept"]=="HR")))

CSV2 = """产品,类别,价格,库存,销量
苹果,水果,5.5,200,180
香蕉,水果,3.0,300,250
牛奶,乳制品,6.0,150,120
酸奶,乳制品,8.5,100,95
橙汁,饮料,12.0,80,60
矿泉水,饮料,2.0,500,480
面包,烘焙,4.5,120,100
蛋糕,烘焙,25.0,50,45
鸡蛋,蛋类,0.8,800,750
豆腐,豆制品,3.5,200,170"""

rows2 = [r.split(',') for r in CSV2.strip().split('\n')[1:]]
products = [{"name":r[0],"cat":r[1],"price":float(r[2]),"stock":int(r[3]),"sales":int(r[4])} for r in rows2]

add(2,"数据过滤", f"表格数据：\n{CSV2}\n\n价格超过10元的产品有几种？", sum(1 for p in products if p["price"]>10), "integer")
add(2,"数据过滤", f"表格数据：\n{CSV2}\n\n水果类产品的总销量是多少？", sum(p["sales"] for p in products if p["cat"]=="水果"))
add(2,"数据过滤", f"表格数据：\n{CSV2}\n\n库存大于销量的差值最大的产品，其差值是多少？", max(p["stock"]-p["sales"] for p in products))
add(2,"数据过滤", f"表格数据：\n{CSV2}\n\n饮料类产品的平均价格（保留1位小数）？", round(sum(p["price"] for p in products if p["cat"]=="饮料")/sum(1 for p in products if p["cat"]=="饮料"), 1))
add(2,"数据过滤", f"表格数据：\n{CSV2}\n\n销售额（价格×销量）最高的产品，其销售额是多少（保留0位小数）？", round(max(p["price"]*p["sales"] for p in products)))
add(2,"数据过滤", f"表格数据：\n{CSV2}\n\n库存超过200的产品有几种？", sum(1 for p in products if p["stock"]>200), "integer")
add(2,"数据过滤", f"表格数据：\n{CSV2}\n\n所有产品总库存是多少？", sum(p["stock"] for p in products))
add(2,"数据过滤", f"表格数据：\n{CSV2}\n\n乳制品的库存总量是多少？", sum(p["stock"] for p in products if p["cat"]=="乳制品"))
add(2,"数据过滤", f"表格数据：\n{CSV2}\n\n价格低于5元的产品有几种？", sum(1 for p in products if p["price"]<5), "integer")
add(2,"数据过滤", f"表格数据：\n{CSV2}\n\n销售率（销量/库存）最高的是哪类（水果/乳制品/饮料/烘焙/蛋类/豆制品）？给出类别名",
    max(set(p["cat"] for p in products), key=lambda c: sum(p["sales"] for p in products if p["cat"]==c)/sum(p["stock"] for p in products if p["cat"]==c)), "string")

# ============================================================
# LEVEL 3: Groupby Aggregation
# ============================================================
SALES_DATA = """月份,区域,产品,销售额
1,北区,A,8500
1,南区,A,7200
1,北区,B,6300
1,南区,B,5800
2,北区,A,9100
2,南区,A,7800
2,北区,B,6800
2,南区,B,6200
3,北区,A,9500
3,南区,A,8100
3,北区,B,7200
3,南区,B,6700
4,北区,A,10200
4,南区,A,8800
4,北区,B,7800
4,南区,B,7100
5,北区,A,11000
5,南区,A,9400
5,北区,B,8300
5,南区,B,7600
6,北区,A,11500
6,南区,A,9800
6,北区,B,8700
6,南区,B,7900"""

srows = [r.split(',') for r in SALES_DATA.strip().split('\n')[1:]]
sales = [{"month":int(r[0]),"region":r[1],"product":r[2],"revenue":int(r[3])} for r in srows]

add(3,"聚合统计", f"销售数据：\n{SALES_DATA}\n\n北区所有月份的总销售额是多少？", sum(s["revenue"] for s in sales if s["region"]=="北区"))
add(3,"聚合统计", f"销售数据：\n{SALES_DATA}\n\n产品A的总销售额是多少？", sum(s["revenue"] for s in sales if s["product"]=="A"))
add(3,"聚合统计", f"销售数据：\n{SALES_DATA}\n\n第3个月的总销售额是多少？", sum(s["revenue"] for s in sales if s["month"]==3))
add(3,"聚合统计", f"销售数据：\n{SALES_DATA}\n\n南区产品B的平均月销售额（保留0位小数）？", round(sum(s["revenue"] for s in sales if s["region"]=="南区" and s["product"]=="B")/sum(1 for s in sales if s["region"]=="南区" and s["product"]=="B")))
add(3,"聚合统计", f"销售数据：\n{SALES_DATA}\n\n哪个月的总销售额最高？回答月份数字。", max(range(1,7), key=lambda m: sum(s["revenue"] for s in sales if s["month"]==m)))
add(3,"聚合统计", f"销售数据：\n{SALES_DATA}\n\n北区与南区的总销售额之差是多少？", abs(sum(s["revenue"] for s in sales if s["region"]=="北区")-sum(s["revenue"] for s in sales if s["region"]=="南区")))
add(3,"聚合统计", f"销售数据：\n{SALES_DATA}\n\n产品A占总销售额的百分比（保留1位小数，如45.3）？", round(100*sum(s["revenue"] for s in sales if s["product"]=="A")/sum(s["revenue"] for s in sales), 1))
add(3,"聚合统计", f"销售数据：\n{SALES_DATA}\n\n前3个月（1-3月）的总销售额是多少？", sum(s["revenue"] for s in sales if s["month"]<=3))
add(3,"聚合统计", f"销售数据：\n{SALES_DATA}\n\n北区产品A每月平均销售额（保留0位小数）？", round(sum(s["revenue"] for s in sales if s["region"]=="北区" and s["product"]=="A")/6))
add(3,"聚合统计", f"销售数据：\n{SALES_DATA}\n\n所有记录中最小的单条销售额是多少？", min(s["revenue"] for s in sales))

SCORE_DATA = """学生,语文,数学,英语,物理,化学
张三,85,92,78,88,90
李四,72,68,85,75,80
王五,95,88,92,85,87
赵六,60,75,70,65,72
陈七,88,95,80,92,85
刘八,78,82,75,80,78
周九,92,78,88,70,82
吴十,65,70,68,75,68"""

srows2 = [r.split(',') for r in SCORE_DATA.strip().split('\n')[1:]]
students = [{"name":r[0],"chinese":int(r[1]),"math":int(r[2]),"english":int(r[3]),"physics":int(r[4]),"chemistry":int(r[5])} for r in srows2]

add(3,"聚合统计", f"成绩表：\n{SCORE_DATA}\n\n数学成绩最高的学生，其语文成绩是多少？", max(students, key=lambda s: s["math"])["chinese"])
add(3,"聚合统计", f"成绩表：\n{SCORE_DATA}\n\n全班语文平均分（保留1位小数）？", round(sum(s["chinese"] for s in students)/len(students), 1))
add(3,"聚合统计", f"成绩表：\n{SCORE_DATA}\n\n五科总分最高的学生，其总分是多少？", max(s["chinese"]+s["math"]+s["english"]+s["physics"]+s["chemistry"] for s in students))
add(3,"聚合统计", f"成绩表：\n{SCORE_DATA}\n\n总分低于400的学生有几人？", sum(1 for s in students if s["chinese"]+s["math"]+s["english"]+s["physics"]+s["chemistry"]<400), "integer")
add(3,"聚合统计", f"成绩表：\n{SCORE_DATA}\n\n全班数学与物理成绩差的绝对值的平均值（保留1位小数）？", round(sum(abs(s["math"]-s["physics"]) for s in students)/len(students), 1))
add(3,"聚合统计", f"成绩表：\n{SCORE_DATA}\n\n五科中，全班平均分最高的科目的平均分（保留1位小数）？",
    round(max(
        sum(s[k] for s in students)/len(students)
        for k in ["chinese","math","english","physics","chemistry"]
    ), 1))
add(3,"聚合统计", f"成绩表：\n{SCORE_DATA}\n\n五科均分超过80分的学生有几人？", sum(1 for s in students if (s["chinese"]+s["math"]+s["english"]+s["physics"]+s["chemistry"])/5 > 80), "integer")
add(3,"聚合统计", f"成绩表：\n{SCORE_DATA}\n\n语文和数学都超过85分的学生有几人？", sum(1 for s in students if s["chinese"]>85 and s["math"]>85), "integer")
add(3,"聚合统计", f"成绩表：\n{SCORE_DATA}\n\n物理成绩的最大值与最小值之差是多少？", max(s["physics"] for s in students)-min(s["physics"] for s in students))
add(3,"聚合统计", f"成绩表：\n{SCORE_DATA}\n\n英语全班总分是多少？", sum(s["english"] for s in students))

# ============================================================
# LEVEL 4: String Processing
# ============================================================
EMAILS = ["alice@gmail.com","bob@yahoo.com","carol@gmail.com","dave@hotmail.com",
          "eve@gmail.com","frank@yahoo.com","grace@outlook.com","henry@gmail.com",
          "iris@hotmail.com","jack@gmail.com","kate@yahoo.com","liam@outlook.com",
          "mia@gmail.com","noah@hotmail.com","olivia@gmail.com"]

add(4,"字符串处理", f"邮件列表：{EMAILS}\n\ngmail.com域名的邮件有几个？", sum(1 for e in EMAILS if '@gmail.com' in e), "integer")
add(4,"字符串处理", f"邮件列表：{EMAILS}\n\nyahoo.com域名的邮件有几个？", sum(1 for e in EMAILS if '@yahoo.com' in e), "integer")
add(4,"字符串处理", f"邮件列表：{EMAILS}\n\n用户名（@前面部分）最长的有几个字符？", max(len(e.split('@')[0]) for e in EMAILS))
add(4,"字符串处理", f"邮件列表：{EMAILS}\n\n用户名以字母a开头的邮件有几个？", sum(1 for e in EMAILS if e[0]=='a'), "integer")

LOGS = [
    "2024-01-15 08:23:11 ERROR Database connection failed",
    "2024-01-15 08:24:05 INFO Service started successfully",
    "2024-01-15 08:25:33 WARN Memory usage at 85%",
    "2024-01-15 09:01:22 ERROR Timeout on request /api/users",
    "2024-01-15 09:15:44 INFO Cache refreshed",
    "2024-01-15 09:32:10 ERROR Failed to write to disk",
    "2024-01-15 10:05:55 INFO Backup completed",
    "2024-01-15 10:22:18 WARN CPU spike detected",
    "2024-01-15 10:45:30 ERROR Authentication service unreachable",
    "2024-01-15 11:00:00 INFO Daily report generated",
    "2024-01-15 11:30:45 WARN Disk space below 20%",
    "2024-01-15 12:15:22 INFO New user registered",
    "2024-01-15 12:45:10 ERROR Payment processing failed",
]
log_str = '\n'.join(LOGS)

add(4,"字符串处理", f"日志文件：\n{log_str}\n\nERROR级别的日志有几条？", sum(1 for l in LOGS if 'ERROR' in l), "integer")
add(4,"字符串处理", f"日志文件：\n{log_str}\n\nWARN级别的日志有几条？", sum(1 for l in LOGS if 'WARN' in l), "integer")
add(4,"字符串处理", f"日志文件：\n{log_str}\n\n10点以后（10:00:00起）的日志有几条？", sum(1 for l in LOGS if l[11:13] >= '10'), "integer")
add(4,"字符串处理", f"日志文件：\n{log_str}\n\nINFO级别的日志有几条？", sum(1 for l in LOGS if 'INFO' in l), "integer")

WORDS = "数据分析是现代商业决策的重要工具，通过对大量数据进行处理分析，可以发现隐藏在数据背后的规律和趋势。数据科学家使用各种统计方法和机器学习算法来挖掘数据价值，从而为企业提供数据驱动的洞察和建议。数据质量是数据分析的基础，没有高质量的数据，任何分析都会得到不可靠的结果。"

add(4,"字符串处理", f"文本：\n{WORDS}\n\n文本中'数据'出现了几次？", WORDS.count('数据'), "integer")
add(4,"字符串处理", f"文本：\n{WORDS}\n\n文本总字符数是多少？", len(WORDS))
add(4,"字符串处理", f"文本：\n{WORDS}\n\n文本中'分析'出现了几次？", WORDS.count('分析'), "integer")

CODES = ["A-1023-X", "B-2045-Y", "A-3011-Z", "C-1099-X", "B-4055-Y",
         "A-2033-X", "C-3077-Z", "B-1044-Y", "A-4022-Z", "C-2088-X"]
codes_str = str(CODES)

add(4,"字符串处理", f"编码列表：{CODES}\n\n以'A'开头的编码有几个？", sum(1 for c in CODES if c.startswith('A')), "integer")
add(4,"字符串处理", f"编码列表：{CODES}\n\n以'-X'结尾的编码有几个？", sum(1 for c in CODES if c.endswith('-X')), "integer")
add(4,"字符串处理", f"编码列表：{CODES}\n\n编码中间数字部分（如1023）大于2000的有几个？", sum(1 for c in CODES if int(c.split('-')[1]) > 2000), "integer")
add(4,"字符串处理", f"编码列表：{CODES}\n\n所有编码中间数字部分的总和是多少？", sum(int(c.split('-')[1]) for c in CODES))

# ============================================================
# LEVEL 5: Date/Time Analysis
# ============================================================
base_date = date(2024, 1, 1)
DATES = [(base_date + timedelta(days=d*7 + d%3)).isoformat() for d in range(20)]
dates_str = str(DATES)

add(5,"日期时间", f"日期列表（ISO格式）：{DATES}\n\n其中有几个日期在2024年2月？", sum(1 for d in DATES if d.startswith('2024-02')), "integer")
add(5,"日期时间", f"日期列表（ISO格式）：{DATES}\n\n最早和最晚日期相差几天？", (date.fromisoformat(max(DATES))-date.fromisoformat(min(DATES))).days)
add(5,"日期时间", f"日期列表（ISO格式）：{DATES}\n\n其中有几个日期在2024年1月？", sum(1 for d in DATES if d.startswith('2024-01')), "integer")
add(5,"日期时间", f"日期列表（ISO格式）：{DATES}\n\n3月份的日期有几个？", sum(1 for d in DATES if d[5:7]=='03'), "integer")

TIME_SERIES = """日期,销售量
2024-03-01,120
2024-03-08,135
2024-03-15,128
2024-03-22,142
2024-03-29,155
2024-04-05,149
2024-04-12,162
2024-04-19,170
2024-04-26,158
2024-05-03,175
2024-05-10,182
2024-05-17,168
2024-05-24,190
2024-05-31,195"""

ts_rows = [r.split(',') for r in TIME_SERIES.strip().split('\n')[1:]]
ts_data = [{"date":r[0],"sales":int(r[1])} for r in ts_rows]

add(5,"日期时间", f"时间序列：\n{TIME_SERIES}\n\n3月份（2024-03）的总销售量是多少？", sum(r["sales"] for r in ts_data if r["date"].startswith('2024-03')))
add(5,"日期时间", f"时间序列：\n{TIME_SERIES}\n\n4月份的平均销售量（保留1位小数）？", round(sum(r["sales"] for r in ts_data if r["date"].startswith('2024-04'))/sum(1 for r in ts_data if r["date"].startswith('2024-04')), 1))
add(5,"日期时间", f"时间序列：\n{TIME_SERIES}\n\n5月份与3月份总销售量的差值是多少？", sum(r["sales"] for r in ts_data if r["date"].startswith('2024-05'))-sum(r["sales"] for r in ts_data if r["date"].startswith('2024-03')))
add(5,"日期时间", f"时间序列：\n{TIME_SERIES}\n\n最高单周销售量是多少？", max(r["sales"] for r in ts_data))
add(5,"日期时间", f"时间序列：\n{TIME_SERIES}\n\n从第一条到最后一条记录相差几天？", (date.fromisoformat(ts_data[-1]["date"])-date.fromisoformat(ts_data[0]["date"])).days)
add(5,"日期时间", f"时间序列：\n{TIME_SERIES}\n\n前5周（3月）的平均销售量（保留1位小数）？", round(sum(r["sales"] for r in ts_data[:5])/5, 1))
add(5,"日期时间", f"时间序列：\n{TIME_SERIES}\n\n后5周（5月）的总销售量是多少？", sum(r["sales"] for r in ts_data[-5:]))
add(5,"日期时间", f"时间序列：\n{TIME_SERIES}\n\n销售量超过160的周次有几个？", sum(1 for r in ts_data if r["sales"]>160), "integer")
add(5,"日期时间", f"时间序列：\n{TIME_SERIES}\n\n整个时期的销售量增长率（最后值/第一值-1，保留3位小数，如0.625）？", round(ts_data[-1]["sales"]/ts_data[0]["sales"]-1, 3))
add(5,"日期时间", f"时间序列：\n{TIME_SERIES}\n\n相邻两周销售量差的最大值是多少？", max(abs(ts_data[i]["sales"]-ts_data[i-1]["sales"]) for i in range(1, len(ts_data))))

EVENTS = """事件,开始时间,结束时间
项目A启动,2024-01-15,2024-03-20
产品B上线,2024-02-01,2024-04-30
系统C升级,2024-03-10,2024-04-15
活动D举办,2024-04-01,2024-04-07
迁移E完成,2024-05-15,2024-07-30"""

ev_rows = [r.split(',') for r in EVENTS.strip().split('\n')[1:]]
events = [{"name":r[0],"start":date.fromisoformat(r[1]),"end":date.fromisoformat(r[2])} for r in ev_rows]

add(5,"日期时间", f"事件列表：\n{EVENTS}\n\n（持续天数 = 结束日期 − 开始日期）\n持续时间最长的事件持续多少天？只回答天数。", max((e["end"]-e["start"]).days for e in events))
add(5,"日期时间", f"事件列表：\n{EVENTS}\n\n（持续天数 = 结束日期 − 开始日期）\n持续时间最短的事件持续多少天？只回答天数。", min((e["end"]-e["start"]).days for e in events))
add(5,"日期时间", f"事件列表：\n{EVENTS}\n\n（持续天数 = 结束日期 − 开始日期）\n所有事件的平均持续时间（保留1位小数）？", round(sum((e["end"]-e["start"]).days for e in events)/len(events), 1))
add(5,"日期时间", f"事件列表：\n{EVENTS}\n\n（持续天数 = 结束日期 − 开始日期）\n在2024年4月内活跃（开始≤4月30日 且 结束≥4月1日）的事件有几个？", sum(1 for e in events if e["start"]<=date(2024,4,30) and e["end"]>=date(2024,4,1)), "integer")
add(5,"日期时间", f"事件列表：\n{EVENTS}\n\n（持续天数 = 结束日期 − 开始日期）\n开始时间在2024年2月之前（不含2月）的事件有几个？", sum(1 for e in events if e["start"]<date(2024,2,1)), "integer")

# ============================================================
# LEVEL 6: Statistical Calculations
# ============================================================
import statistics as stats

DATA6_1 = [23, 45, 12, 67, 34, 89, 56, 78, 23, 45, 67, 34, 56, 89, 12, 45, 78, 34, 56, 23]
add(6,"统计分析", f"数据集：{DATA6_1}\n\n样本标准差（保留2位小数）？", round(stats.stdev(DATA6_1), 2))
add(6,"统计分析", f"数据集：{DATA6_1}\n\n用线性插值法（numpy.percentile 默认方法）计算25%分位数（保留2位小数）？", round(stats.quantiles(DATA6_1, n=4, method='inclusive')[0], 2))
add(6,"统计分析", f"数据集：{DATA6_1}\n\n用线性插值法（numpy.percentile 默认方法）计算75%分位数（保留2位小数）？", round(stats.quantiles(DATA6_1, n=4, method='inclusive')[2], 2))
add(6,"统计分析", f"数据集：{DATA6_1}\n\n用线性插值法（numpy.percentile 默认方法）计算四分位距 IQR=Q3-Q1（保留2位小数）？", round(stats.quantiles(DATA6_1, n=4, method='inclusive')[2]-stats.quantiles(DATA6_1, n=4, method='inclusive')[0], 2))
add(6,"统计分析", f"数据集：{DATA6_1}\n\n按 1.5×IQR 规则（Q1、Q3 用线性插值法），有几个异常值？",
    sum(1 for x in DATA6_1 if x < (q:=stats.quantiles(DATA6_1, n=4, method='inclusive'))[0]-1.5*(q[2]-q[0]) or x > q[2]+1.5*(q[2]-q[0])), "integer")
add(6,"统计分析", f"数据集：{DATA6_1}\n\n众数是多少（若有多个取最小）？", min(x for x in DATA6_1 if DATA6_1.count(x)==max(DATA6_1.count(v) for v in DATA6_1)))
add(6,"统计分析", f"数据集：{DATA6_1}\n\n方差（样本方差，保留2位小数）？", round(stats.variance(DATA6_1), 2))

DATA6_X = [1,2,3,4,5,6,7,8,9,10]
DATA6_Y = [2.1,4.0,5.9,8.1,10.2,12.0,14.1,15.9,18.0,20.1]

n = len(DATA6_X)
mean_x = sum(DATA6_X)/n
mean_y = sum(DATA6_Y)/n
cov = sum((DATA6_X[i]-mean_x)*(DATA6_Y[i]-mean_y) for i in range(n))/n
std_x = (sum((x-mean_x)**2 for x in DATA6_X)/n)**0.5
std_y = (sum((y-mean_y)**2 for y in DATA6_Y)/n)**0.5
corr = round(cov/(std_x*std_y), 3)

add(6,"统计分析", f"X={DATA6_X}\nY={DATA6_Y}\n\n两个序列的皮尔逊相关系数（保留3位小数）？", corr)
add(6,"统计分析", f"X={DATA6_X}\nY={DATA6_Y}\n\n用最小二乘法拟合 Y=aX+b，斜率 a 是多少（保留4位小数）？",
    round(sum((DATA6_X[i]-mean_x)*(DATA6_Y[i]-mean_y) for i in range(n))/sum((x-mean_x)**2 for x in DATA6_X), 4))

DATA6_2 = [12.5, 13.2, 11.8, 14.1, 12.9, 13.5, 11.2, 14.8, 12.1, 13.8,
           11.5, 14.2, 12.7, 13.1, 12.3, 14.5, 11.9, 13.7, 12.6, 13.4]
add(6,"统计分析", f"数据集：{DATA6_2}\n\n均值（保留2位小数）？", round(sum(DATA6_2)/len(DATA6_2), 2))
add(6,"统计分析", f"数据集：{DATA6_2}\n\n标准差（样本，保留3位小数）？", round(stats.stdev(DATA6_2), 3))
add(6,"统计分析", f"数据集：{DATA6_2}\n\n中位数（保留2位小数）？", round(stats.median(DATA6_2), 2))

DATA6_3 = list(range(1, 51))  # 1 to 50
add(6,"统计分析", f"数据集：{DATA6_3}（即1到50的整数）\n\n均值是多少？", 25.5)
add(6,"统计分析", f"数据集：{DATA6_3}（即1到50的整数）\n\n总体标准差（保留4位小数）？", round(stats.pstdev(DATA6_3), 4))

DATA6_HIST = [5,5,5,7,7,8,8,8,8,9,9,9,10,10,10,10,11,11,12,12,12,13,13,14,15]
add(6,"统计分析", f"数据集：{DATA6_HIST}\n\n众数（出现频率最高的值，若有多个取最小）？", min(x for x in DATA6_HIST if DATA6_HIST.count(x)==max(DATA6_HIST.count(v) for v in DATA6_HIST)))
add(6,"统计分析", f"数据集：{DATA6_HIST}\n\n比较均值与中位数判断偏态：均值>中位数输出'右偏'，均值<中位数输出'左偏'，相等输出'对称'。",
    '右偏' if sum(DATA6_HIST)/len(DATA6_HIST)>stats.median(DATA6_HIST) else ('左偏' if sum(DATA6_HIST)/len(DATA6_HIST)<stats.median(DATA6_HIST) else '对称'), "string")

DATA6_NORM = [98,102,99,101,100,98,103,97,102,100,99,101,100,102,98,103,99,101,100,98]
mean6 = sum(DATA6_NORM)/len(DATA6_NORM)
std6 = stats.stdev(DATA6_NORM)
add(6,"统计分析", f"数据集：{DATA6_NORM}\n\n（标准差均指样本标准差）\n在均值±1个标准差范围内的数据点有几个？", sum(1 for x in DATA6_NORM if abs(x-mean6)<=std6), "integer")
add(6,"统计分析", f"数据集：{DATA6_NORM}\n\n（标准差均指样本标准差）\n变异系数（CV=标准差/均值，保留4位小数）？", round(std6/mean6, 4))
add(6,"统计分析", f"数据集：{DATA6_NORM}\n\n（标准差均指样本标准差）\n最大值与最小值的差除以标准差（保留2位小数）？", round((max(DATA6_NORM)-min(DATA6_NORM))/std6, 2))
add(6,"统计分析", f"数据集：{DATA6_NORM}\n\n（标准差均指样本标准差）\n均值（保留2位小数）？", round(mean6, 2))

# ============================================================
# LEVEL 7: Multi-dataset Join Operations
# ============================================================
ORDERS = """订单ID,客户ID,产品ID,数量,日期
O001,C001,P003,2,2024-01-10
O002,C002,P001,1,2024-01-12
O003,C001,P002,3,2024-01-15
O004,C003,P003,1,2024-01-18
O005,C002,P002,2,2024-01-20
O006,C004,P001,4,2024-01-22
O007,C003,P003,2,2024-01-25
O008,C001,P001,1,2024-01-28
O009,C004,P002,3,2024-02-01
O010,C002,P003,1,2024-02-03"""

PRODUCTS_TABLE = """产品ID,产品名,价格,类别
P001,笔记本,5999,电子
P002,鼠标,299,配件
P003,键盘,459,配件"""

CUSTOMERS_TABLE = """客户ID,姓名,城市,等级
C001,张伟,北京,金
C002,李娜,上海,银
C003,王磊,广州,铜
C004,赵敏,深圳,金"""

o_rows = [r.split(',') for r in ORDERS.strip().split('\n')[1:]]
orders = [{"oid":r[0],"cid":r[1],"pid":r[2],"qty":int(r[3]),"date":r[4]} for r in o_rows]

p_rows = [r.split(',') for r in PRODUCTS_TABLE.strip().split('\n')[1:]]
prods = {r[0]:{"name":r[1],"price":float(r[2]),"cat":r[3]} for r in p_rows}

c_rows = [r.split(',') for r in CUSTOMERS_TABLE.strip().split('\n')[1:]]
custs = {r[0]:{"name":r[1],"city":r[2],"level":r[3]} for r in c_rows}

context7 = f"订单表：\n{ORDERS}\n\n产品表：\n{PRODUCTS_TABLE}\n\n客户表：\n{CUSTOMERS_TABLE}\n\n"

add(7,"多表联结", context7+"客户C001的总订单金额（数量×价格之和）是多少（保留0位小数）？",
    round(sum(o["qty"]*prods[o["pid"]]["price"] for o in orders if o["cid"]=="C001")))
add(7,"多表联结", context7+"配件类产品的订单总数量是多少？",
    sum(o["qty"] for o in orders if prods[o["pid"]]["cat"]=="配件"))
add(7,"多表联结", context7+"北京客户的订单总金额是多少（保留0位小数）？",
    round(sum(o["qty"]*prods[o["pid"]]["price"] for o in orders if custs[o["cid"]]["city"]=="北京")))
add(7,"多表联结", context7+"金级客户的订单数量（条数）是多少？",
    sum(1 for o in orders if custs[o["cid"]]["level"]=="金"), "integer")
add(7,"多表联结", context7+"哪个产品ID的订单数量（条数）最多？",
    max(set(o["pid"] for o in orders), key=lambda p: sum(1 for o in orders if o["pid"]==p)), "string")
add(7,"多表联结", context7+"键盘（P003）的总销售额是多少（保留0位小数）？",
    round(sum(o["qty"]*prods["P003"]["price"] for o in orders if o["pid"]=="P003")))
add(7,"多表联结", context7+"2月份（2024-02开头）的订单总金额是多少（保留0位小数）？",
    round(sum(o["qty"]*prods[o["pid"]]["price"] for o in orders if o["date"].startswith("2024-02"))))
add(7,"多表联结", context7+"平均每个客户的订单金额（总金额/客户数，保留0位小数）？",
    round(sum(o["qty"]*prods[o["pid"]]["price"] for o in orders)/len(set(o["cid"] for o in orders))))
add(7,"多表联结", context7+"订单总金额最高的客户ID是哪个？",
    max(set(o["cid"] for o in orders), key=lambda c: sum(o["qty"]*prods[o["pid"]]["price"] for o in orders if o["cid"]==c)), "string")
add(7,"多表联结", context7+"电子产品（笔记本P001）被几个不同客户购买过？",
    len(set(o["cid"] for o in orders if o["pid"]=="P001")), "integer")

DEPT_TABLE = """部门ID,部门名,预算
D001,研发,500000
D002,市场,300000
D003,销售,250000
D004,运营,200000"""

EMP_TABLE = """员工ID,姓名,部门ID,薪资,工龄
E001,陈明,D001,15000,5
E002,刘芳,D002,12000,3
E003,张强,D001,18000,8
E004,王静,D003,10000,2
E005,李勇,D001,16000,6
E006,赵琳,D002,11000,4
E007,周涛,D003,9500,1
E008,吴丽,D004,13000,7
E009,郑浩,D001,14000,4
E010,黄梅,D004,12500,5"""

d_rows = [r.split(',') for r in DEPT_TABLE.strip().split('\n')[1:]]
depts = {r[0]:{"name":r[1],"budget":int(r[2])} for r in d_rows}
e_rows = [r.split(',') for r in EMP_TABLE.strip().split('\n')[1:]]
emps = [{"eid":r[0],"name":r[1],"did":r[2],"salary":int(r[3]),"years":int(r[4])} for r in e_rows]

context7b = f"部门表：\n{DEPT_TABLE}\n\n员工表：\n{EMP_TABLE}\n\n"
add(7,"多表联结", context7b+"研发部门（D001）的薪资总额是多少？", sum(e["salary"] for e in emps if e["did"]=="D001"))
add(7,"多表联结", context7b+"薪资超过预算1/30的部门有几个（即该部门所有员工薪资之和>预算/30）？",
    sum(1 for did in set(e["did"] for e in emps)
        if sum(e["salary"] for e in emps if e["did"]==did) > depts[did]["budget"]/30), "integer")
add(7,"多表联结", context7b+"工龄最长的员工所在部门的平均薪资是多少（保留0位小数）？",
    round(sum(e["salary"] for e in emps if e["did"]==max(emps, key=lambda x: x["years"])["did"])/
          sum(1 for e in emps if e["did"]==max(emps, key=lambda x: x["years"])["did"])))
add(7,"多表联结", context7b+"哪个部门的人均薪资最高？输出部门名称。",
    depts[max(set(e["did"] for e in emps), key=lambda d: sum(e["salary"] for e in emps if e["did"]==d)/sum(1 for e in emps if e["did"]==d))]["name"], "string")
add(7,"多表联结", context7b+"运营部门（D004）员工的平均工龄（保留1位小数）？",
    round(sum(e["years"] for e in emps if e["did"]=="D004")/sum(1 for e in emps if e["did"]=="D004"), 1))
add(7,"多表联结", context7b+"薪资最高的前3名员工的薪资总和是多少？",
    sum(sorted([e["salary"] for e in emps], reverse=True)[:3]))
add(7,"多表联结", context7b+"工龄超过5年的员工有几人？",
    sum(1 for e in emps if e["years"]>5), "integer")
add(7,"多表联结", context7b+"研发部门的人均预算分配（预算/人数，保留0位小数）？",
    round(depts["D001"]["budget"]/sum(1 for e in emps if e["did"]=="D001")))
add(7,"多表联结", context7b+"市场和销售部门的员工总人数是多少？",
    sum(1 for e in emps if e["did"] in ["D002","D003"]), "integer")
add(7,"多表联结", context7b+"薪资低于部门平均薪资的员工有几人？",
    sum(1 for e in emps
        if e["salary"] < sum(x["salary"] for x in emps if x["did"]==e["did"])/sum(1 for x in emps if x["did"]==e["did"])), "integer")

# ============================================================
# LEVEL 8: Data Quality & Cleaning
# ============================================================
DIRTY_DATA = """ID,姓名,年龄,邮箱,薪资
1,张三,28,zhangsan@email.com,12000
2,李四,,lisi@email.com,9500
3,王五,35,wangwu@email.com,
4,赵六,28,zhangsan@email.com,12000
5,陈七,42,chenqi@email.com,15000
6,刘八,-1,liuba@email.com,8000
7,张三,28,zhangsan@email.com,12000
8,周九,999,zhoujiu@email.com,7500
9,吴十,33,,11000
10,郑十一,45,zhengshiyi@email.com,250000
11,黄十二,29,huangshier@email.com,10000
12,马十三,,mashi@email.com,9000"""

dd_rows = [r.split(',') for r in DIRTY_DATA.strip().split('\n')[1:]]
dd = [{"id":int(r[0]),"name":r[1],"age":r[2],"email":r[3],"salary":r[4]} for r in dd_rows]

add(8,"数据质量", f"数据集：\n{DIRTY_DATA}\n\n年龄字段有几个缺失值（空字符串）？", sum(1 for r in dd if r["age"]==''), "integer")
add(8,"数据质量", f"数据集：\n{DIRTY_DATA}\n\n薪资字段有几个缺失值？", sum(1 for r in dd if r["salary"]==''), "integer")
add(8,"数据质量", f"数据集：\n{DIRTY_DATA}\n\n邮箱字段有几个缺失值？", sum(1 for r in dd if r["email"]==''), "integer")
add(8,"数据质量", f"数据集：\n{DIRTY_DATA}\n\n有几行数据完全重复（姓名、年龄、邮箱、薪资都相同）？（重复的行数，不含第一次出现）",
    sum(1 for i, r in enumerate(dd)
        for r2 in dd[:i] if r["name"]==r2["name"] and r["age"]==r2["age"] and r["email"]==r2["email"] and r["salary"]==r2["salary"]), "integer")

valid_ages = [int(r["age"]) for r in dd if r["age"] not in ('','999') and int(r["age"] if r["age"] else -999) > 0 and int(r["age"]) < 100]
add(8,"数据质量", f"数据集：\n{DIRTY_DATA}\n\n异常年龄值（负数或超过150）有几个？", sum(1 for r in dd if r["age"] not in ('',) and r["age"] != '' and (int(r["age"]) < 0 or int(r["age"]) > 150)), "integer")

valid_salaries = [int(r["salary"]) for r in dd if r["salary"]!='']
mean_sal = sum(valid_salaries)/len(valid_salaries)
std_sal = stats.stdev(valid_salaries)
add(8,"数据质量", f"数据集：\n{DIRTY_DATA}\n\n薪资字段中，有效值（非空）的均值是多少（保留0位小数）？", round(mean_sal))
add(8,"数据质量", f"数据集：\n{DIRTY_DATA}\n\n使用Z-score（|z|>3）方法，薪资中有几个异常值（忽略空值）？",
    sum(1 for s in valid_salaries if abs(s-mean_sal)/std_sal > 3), "integer")

DUPDATA = """交易ID,金额,商户,时间
T001,150.00,超市A,2024-01-10 10:25:30
T002,89.50,餐厅B,2024-01-10 12:10:00
T003,150.00,超市A,2024-01-10 10:25:30
T004,230.00,电商C,2024-01-11 09:15:00
T005,89.50,餐厅B,2024-01-10 12:10:00
T006,520.00,电商C,2024-01-11 14:30:00
T007,75.00,超市A,2024-01-12 11:00:00
T008,230.00,电商C,2024-01-11 09:15:00
T009,310.00,商场D,2024-01-12 15:45:00
T010,75.00,超市A,2024-01-12 11:00:00"""

dup_rows = [r.split(',') for r in DUPDATA.strip().split('\n')[1:]]
trans = [{"tid":r[0],"amount":r[1],"merchant":r[2],"time":r[3]} for r in dup_rows]

add(8,"数据质量", f"交易数据：\n{DUPDATA}\n\n有几笔重复交易（金额+商户+时间完全相同，不含第一次出现）？",
    sum(1 for i, t in enumerate(trans)
        for t2 in trans[:i] if t["amount"]==t2["amount"] and t["merchant"]==t2["merchant"] and t["time"]==t2["time"]), "integer")
add(8,"数据质量", f"交易数据：\n{DUPDATA}\n\n去重后有几笔唯一交易（按金额+商户+时间去重）？",
    len(set((t["amount"],t["merchant"],t["time"]) for t in trans)), "integer")
add(8,"数据质量", f"交易数据：\n{DUPDATA}\n\n超市A的交易中，去重后的总金额是多少（保留2位小数）？",
    round(sum(float(t["amount"]) for t in {(t["amount"],t["merchant"],t["time"]):t for t in trans}.values() if t["merchant"]=="超市A"), 2))

MISSING_DATA = """产品ID,名称,价格,库存,评分
P001,商品A,99.9,100,4.5
P002,商品B,,200,4.2
P003,商品C,149.0,,3.8
P004,商品D,199.0,50,
P005,商品E,,150,4.7
P006,商品F,79.0,300,4.1
P007,商品G,259.0,,4.9
P008,商品H,89.0,80,
P009,商品I,,120,3.5
P010,商品J,119.0,60,4.3"""

md_rows = [r.split(',') for r in MISSING_DATA.strip().split('\n')[1:]]
mdata = [{"pid":r[0],"name":r[1],"price":r[2],"stock":r[3],"rating":r[4]} for r in md_rows]

add(8,"数据质量", f"产品数据：\n{MISSING_DATA}\n\n总共有几个缺失值（空字段）？", sum(1 for r in mdata for v in [r["price"],r["stock"],r["rating"]] if v==''), "integer")
add(8,"数据质量", f"产品数据：\n{MISSING_DATA}\n\n价格字段缺失的产品有几个？", sum(1 for r in mdata if r["price"]==''), "integer")
add(8,"数据质量", f"产品数据：\n{MISSING_DATA}\n\n有效价格的平均值（保留2位小数）？", round(sum(float(r["price"]) for r in mdata if r["price"]!='')/sum(1 for r in mdata if r["price"]!=''), 2))
add(8,"数据质量", f"产品数据：\n{MISSING_DATA}\n\n所有字段均完整（无缺失）的产品有几个？",
    sum(1 for r in mdata if all(v!='' for v in [r["price"],r["stock"],r["rating"]])), "integer")
add(8,"数据质量", f"产品数据：\n{MISSING_DATA}\n\n有效评分的最高分是多少？", max(float(r["rating"]) for r in mdata if r["rating"]!=''))
add(8,"数据质量", f"产品数据：\n{MISSING_DATA}\n\n库存字段缺失的产品有几个？", sum(1 for r in mdata if r["stock"]==''), "integer")
add(8,"数据质量", f"产品数据：\n{MISSING_DATA}\n\n评分字段的缺失率（缺失数/总数，保留2位小数）？", round(sum(1 for r in mdata if r["rating"]=='')/len(mdata), 2))

# ============================================================
# LEVEL 9: Complex Transformations
# ============================================================
MONTHLY_SALES = """月份,产品,销售额
1,A,10000
1,B,8000
1,C,6000
2,A,11000
2,B,7500
2,C,6500
3,A,12000
3,B,9000
3,C,7000
4,A,10500
4,B,8500
4,C,7500
5,A,13000
5,B,10000
5,C,8000
6,A,14000
6,B,11000
6,C,8500"""

ms_rows = [r.split(',') for r in MONTHLY_SALES.strip().split('\n')[1:]]
ms = [{"month":int(r[0]),"product":r[1],"sales":int(r[2])} for r in ms_rows]

# Running total for product A
a_sales = sorted([r for r in ms if r["product"]=="A"], key=lambda x: x["month"])
running_total_a = [sum(r["sales"] for r in a_sales[:i+1]) for i in range(len(a_sales))]

add(9,"复杂变换", f"月销售数据：\n{MONTHLY_SALES}\n\n产品A在前3个月的累计销售额是多少？", sum(r["sales"] for r in ms if r["product"]=="A" and r["month"]<=3))
add(9,"复杂变换", f"月销售数据：\n{MONTHLY_SALES}\n\n每个产品的6个月总销售额中，最高的产品总销售额是多少？",
    max(sum(r["sales"] for r in ms if r["product"]==p) for p in ["A","B","C"]))
add(9,"复杂变换", f"月销售数据：\n{MONTHLY_SALES}\n\n产品A从1月到6月的销售增长额（6月-1月）是多少？",
    next(r["sales"] for r in ms if r["product"]=="A" and r["month"]==6) - next(r["sales"] for r in ms if r["product"]=="A" and r["month"]==1))
add(9,"复杂变换", f"月销售数据：\n{MONTHLY_SALES}\n\n每月三个产品的总销售额中，最高月份的总额是多少？",
    max(sum(r["sales"] for r in ms if r["month"]==m) for m in range(1,7)))
add(9,"复杂变换", f"月销售数据：\n{MONTHLY_SALES}\n\n产品B在偶数月（2、4、6月）的总销售额是多少？",
    sum(r["sales"] for r in ms if r["product"]=="B" and r["month"]%2==0))
c_s = sorted([r for r in ms if r["product"]=="C"], key=lambda x: x["month"])
add(9,"复杂变换", f"月销售数据：\n{MONTHLY_SALES}\n\n计算产品C的月环比增长率，其中增长最多的月份（相比上月）增长了多少元？",
    max(c_s[i]["sales"]-c_s[i-1]["sales"] for i in range(1,len(c_s))))

add(9,"复杂变换", f"月销售数据：\n{MONTHLY_SALES}\n\n后3个月（4-6月）的总销售额与前3个月（1-3月）的总销售额之差是多少？",
    sum(r["sales"] for r in ms if r["month"]>=4)-sum(r["sales"] for r in ms if r["month"]<=3))
add(9,"复杂变换", f"月销售数据：\n{MONTHLY_SALES}\n\n所有月份中，产品A的市场份额（A销售额/当月总销售额）的平均值（保留3位小数）？",
    round(sum(next(r["sales"] for r in ms if r["product"]=="A" and r["month"]==m)/sum(r["sales"] for r in ms if r["month"]==m) for m in range(1,7))/6, 3))
add(9,"复杂变换", f"月销售数据：\n{MONTHLY_SALES}\n\n产品A的销售额在每月三个产品中排名第一的月份有几个？",
    sum(1 for m in range(1,7) if next(r["sales"] for r in ms if r["product"]=="A" and r["month"]==m)==max(r["sales"] for r in ms if r["month"]==m)), "integer")

RANK_DATA = """员工ID,季度,绩效分
E001,Q1,85
E002,Q1,92
E003,Q1,78
E004,Q1,88
E005,Q1,95
E001,Q2,88
E002,Q2,87
E003,Q2,82
E004,Q2,91
E005,Q2,94
E001,Q3,90
E002,Q3,85
E003,Q3,86
E004,Q3,93
E005,Q3,96"""

rd_rows = [r.split(',') for r in RANK_DATA.strip().split('\n')[1:]]
rd = [{"eid":r[0],"quarter":r[1],"score":int(r[2])} for r in rd_rows]

add(9,"复杂变换", f"绩效数据：\n{RANK_DATA}\n\nQ1季度排名第一的员工ID是哪个？", max([r for r in rd if r["quarter"]=="Q1"], key=lambda x: x["score"])["eid"], "string")
add(9,"复杂变换", f"绩效数据：\n{RANK_DATA}\n\n三个季度累计分数最高的员工，其总分是多少？",
    max(sum(r["score"] for r in rd if r["eid"]==e) for e in set(r["eid"] for r in rd)))
add(9,"复杂变换", f"绩效数据：\n{RANK_DATA}\n\n每个季度的平均分中，哪个季度最高？输出季度名（Q1/Q2/Q3）。",
    max(["Q1","Q2","Q3"], key=lambda q: sum(r["score"] for r in rd if r["quarter"]==q)/sum(1 for r in rd if r["quarter"]==q)), "string")
add(9,"复杂变换", f"绩效数据：\n{RANK_DATA}\n\n三个季度每次都高于90分的员工有几人？",
    sum(1 for e in set(r["eid"] for r in rd) if all(r["score"]>90 for r in rd if r["eid"]==e)), "integer")
add(9,"复杂变换", f"绩效数据：\n{RANK_DATA}\n\nE005的三季度分数方差（总体方差，保留2位小数）？",
    round(stats.pvariance([r["score"] for r in rd if r["eid"]=="E005"]), 2))
add(9,"复杂变换", f"绩效数据：\n{RANK_DATA}\n\n所有员工的整体平均分（保留2位小数）？",
    round(sum(r["score"] for r in rd)/len(rd), 2))
add(9,"复杂变换", f"绩效数据：\n{RANK_DATA}\n\n从Q1到Q3绩效分持续上升的员工有几人？",
    sum(1 for e in set(r["eid"] for r in rd)
        if (q1:=next(r["score"] for r in rd if r["eid"]==e and r["quarter"]=="Q1")) <
           (q2:=next(r["score"] for r in rd if r["eid"]==e and r["quarter"]=="Q2")) <
           next(r["score"] for r in rd if r["eid"]==e and r["quarter"]=="Q3")), "integer")
add(9,"复杂变换", f"绩效数据：\n{RANK_DATA}\n\nQ3的最高分与最低分之差是多少？",
    max(r["score"] for r in rd if r["quarter"]=="Q3")-min(r["score"] for r in rd if r["quarter"]=="Q3"))
add(9,"复杂变换", f"绩效数据：\n{RANK_DATA}\n\n三季度均分最高的员工ID是哪个？",
    max(set(r["eid"] for r in rd), key=lambda e: sum(r["score"] for r in rd if r["eid"]==e)/3), "string")

# ============================================================
# LEVEL 10: Advanced Analytics
# ============================================================
REVENUE_TS = [120, 135, 128, 142, 155, 149, 162, 170, 158, 175, 182, 168, 190, 195, 188, 205, 212, 198, 220, 225]

# 3-period moving average
def moving_avg(data, window):
    return [round(sum(data[i:i+window])/window, 2) for i in range(len(data)-window+1)]

ma3 = moving_avg(REVENUE_TS, 3)
ma5 = moving_avg(REVENUE_TS, 5)

add(10,"高级分析", f"营收时间序列（共20期）：{REVENUE_TS}\n\n3期移动平均的第5个值（即第5-7期的均值）是多少（保留2位小数）？", moving_avg(REVENUE_TS,3)[4])
add(10,"高级分析", f"营收时间序列（共20期）：{REVENUE_TS}\n\n5期移动平均的最大值是多少（保留2位小数）？", max(moving_avg(REVENUE_TS,5)))
add(10,"高级分析", f"营收时间序列（共20期）：{REVENUE_TS}\n\n相邻期环比增长率的平均值（保留4位小数，如0.0312）？",
    round(sum((REVENUE_TS[i]-REVENUE_TS[i-1])/REVENUE_TS[i-1] for i in range(1,len(REVENUE_TS)))/(len(REVENUE_TS)-1), 4))

COHORT_DATA = """用户ID,注册月,第1月收入,第2月收入,第3月收入,第4月收入
U001,2024-01,100,85,90,70
U002,2024-01,150,130,120,110
U003,2024-01,80,75,60,55
U004,2024-02,120,100,95,85
U005,2024-02,90,80,70,65
U006,2024-02,200,180,160,150
U007,2024-03,110,95,100,88
U008,2024-03,130,115,105,98
U009,2024-03,75,65,60,55
U010,2024-03,160,140,135,125"""

co_rows = [r.split(',') for r in COHORT_DATA.strip().split('\n')[1:]]
cohort = [{"uid":r[0],"month":r[1],"m1":int(r[2]),"m2":int(r[3]),"m3":int(r[4]),"m4":int(r[5])} for r in co_rows]

add(10,"高级分析", f"用户队列数据：\n{COHORT_DATA}\n\n2024-01队列的平均第1月收入（保留1位小数）？",
    round(sum(u["m1"] for u in cohort if u["month"]=="2024-01")/sum(1 for u in cohort if u["month"]=="2024-01"), 1))
add(10,"高级分析", f"用户队列数据：\n{COHORT_DATA}\n\n2024-02队列从第1月到第4月的收入留存率（第4月均值/第1月均值，保留3位小数）？",
    round(sum(u["m4"] for u in cohort if u["month"]=="2024-02")/sum(u["m1"] for u in cohort if u["month"]=="2024-02"), 3))
add(10,"高级分析", f"用户队列数据：\n{COHORT_DATA}\n\n所有用户第4月收入之和与第1月收入之和的比值（保留3位小数）？",
    round(sum(u["m4"] for u in cohort)/sum(u["m1"] for u in cohort), 3))

AB_DATA = """组别,转化率_第1周,转化率_第2周,转化率_第3周,转化率_第4周
对照组,0.120,0.118,0.122,0.119
实验组,0.135,0.142,0.138,0.145"""

ab_rows = [r.split(',') for r in AB_DATA.strip().split('\n')[1:]]
control = [float(x) for x in ab_rows[0][1:]]
treatment = [float(x) for x in ab_rows[1][1:]]

add(10,"高级分析", f"A/B测试数据：\n{AB_DATA}\n\n实验组的平均转化率（保留4位小数）？", round(sum(treatment)/len(treatment), 4))
add(10,"高级分析", f"A/B测试数据：\n{AB_DATA}\n\n实验组相比对照组的平均提升（实验组均值-对照组均值，保留4位小数）？", round(sum(treatment)/len(treatment)-sum(control)/len(control), 4))
add(10,"高级分析", f"A/B测试数据：\n{AB_DATA}\n\n对照组4周转化率的标准差（样本，保留5位小数）？", round(stats.stdev(control), 5))

FEATURE_DATA = """用户,年龄,收入,消费,登录次数,购买次数
A,25,8000,3200,45,12
B,35,15000,8500,30,25
C,28,10000,4100,55,18
D,42,20000,12000,20,35
E,22,6000,2800,60,8
F,38,18000,9500,25,30
G,31,12000,5200,40,20
H,45,25000,15000,15,42
I,27,9000,3800,50,15
J,33,14000,7200,35,22"""

feat_rows = [r.split(',') for r in FEATURE_DATA.strip().split('\n')[1:]]
feats = [{"user":r[0],"age":int(r[1]),"income":int(r[2]),"spend":int(r[3]),"logins":int(r[4]),"purchases":int(r[5])} for r in feat_rows]

# Spend/Income ratio feature
spend_ratio = [round(f["spend"]/f["income"], 3) for f in feats]
add(10,"高级分析", f"用户特征数据：\n{FEATURE_DATA}\n\n消费收入比（消费/收入）最高的用户，其比值是多少（保留3位小数）？", max(spend_ratio))
add(10,"高级分析", f"用户特征数据：\n{FEATURE_DATA}\n\n收入与消费的皮尔逊相关系数（保留3位小数）？",
    round(sum((f["income"]-sum(f2["income"] for f2 in feats)/len(feats))*(f["spend"]-sum(f2["spend"] for f2 in feats)/len(feats)) for f in feats)/
          len(feats) /
          ((sum((f["income"]-sum(f2["income"] for f2 in feats)/len(feats))**2 for f in feats)/len(feats))**0.5 *
           (sum((f["spend"]-sum(f2["spend"] for f2 in feats)/len(feats))**2 for f in feats)/len(feats))**0.5), 3))
add(10,"高级分析", f"用户特征数据：\n{FEATURE_DATA}\n\n将收入标准化（减均值除以样本标准差）后，最大的标准化值是多少（保留3位小数）？",
    round(max((f["income"]-sum(f2["income"] for f2 in feats)/len(feats))/stats.stdev(f["income"] for f in feats) for f in feats), 3))

# Pareto: top 20% users (2 users) by purchases contribute what % of total purchases
sorted_by_purchase = sorted(feats, key=lambda f: f["purchases"], reverse=True)
top20_purchases = sum(f["purchases"] for f in sorted_by_purchase[:2])
total_purchases = sum(f["purchases"] for f in feats)
add(10,"高级分析", f"用户特征数据：\n{FEATURE_DATA}\n\n前20%用户（按购买次数排名，即前2名）的购买次数占总购买次数的比例（保留3位小数）？",
    round(top20_purchases/total_purchases, 3))

# RFM: simple scoring
avg_spend = sum(f["spend"] for f in feats)/len(feats)
avg_logins = sum(f["logins"] for f in feats)/len(feats)
high_value = sum(1 for f in feats if f["spend"]>avg_spend and f["logins"]>avg_logins)
add(10,"高级分析", f"用户特征数据：\n{FEATURE_DATA}\n\n消费高于平均值且登录次数高于平均值的用户有几人？", high_value, "integer")
add(10,"高级分析", f"用户特征数据：\n{FEATURE_DATA}\n\n登录次数与购买次数的相关系数（保留3位小数）？",
    round(sum((f["logins"]-sum(f2["logins"] for f2 in feats)/len(feats))*(f["purchases"]-sum(f2["purchases"] for f2 in feats)/len(feats)) for f in feats)/
          len(feats) /
          ((sum((f["logins"]-sum(f2["logins"] for f2 in feats)/len(feats))**2 for f in feats)/len(feats))**0.5 *
           (sum((f["purchases"]-sum(f2["purchases"] for f2 in feats)/len(feats))**2 for f in feats)/len(feats))**0.5), 3))

# ============================================================
# 补充用例（使各级恰好 20 条）
# ============================================================
add(4,"字符串处理", f"邮件列表：{EMAILS}\n\n共有几种不同的邮箱域名？", len(set(e.split('@')[1] for e in EMAILS)), "integer")
add(4,"字符串处理", f"日志文件：\n{log_str}\n\n按小时（08、09、10…）统计日志条数，条数最多的小时是几点？若并列取最早的小时，输出两位数字如08。",
    max(sorted(set(l[11:13] for l in LOGS)), key=lambda h: sum(1 for l in LOGS if l[11:13]==h)), "string")
add(4,"字符串处理", f"日志文件：\n{log_str}\n\n所有ERROR日志消息（级别之后的文本）的总字符数（含空格）是多少？",
    sum(len(l.split(' ', 3)[3]) for l in LOGS if ' ERROR ' in l))
add(4,"字符串处理", f"编码列表：{CODES}\n\n按首字母分组，中间数字之和最大的组是哪个字母？",
    max("ABC", key=lambda k: sum(int(c.split('-')[1]) for c in CODES if c[0]==k)), "string")
add(4,"字符串处理", f"编码列表：{CODES}\n\n首字母与末字母组合（如A-X）共有几种不同组合？",
    len(set((c[0], c[-1]) for c in CODES)), "integer")

add(5,"日期时间", f"时间序列：\n{TIME_SERIES}\n\n记录日期中，有几个是星期五？",
    sum(1 for r in ts_data if date.fromisoformat(r["date"]).weekday()==4), "integer")

add(8,"数据质量", f"数据集：\n{DIRTY_DATA}\n\n邮箱字段（非空）中有几个邮箱被不同ID重复使用（统计重复出现的邮箱种类数）？",
    sum(1 for e in set(r["email"] for r in dd if r["email"]) if sum(1 for r in dd if r["email"]==e) > 1), "integer")
add(8,"数据质量", f"数据集：\n{DIRTY_DATA}\n\n删除重复行（除ID外其余字段完全相同视为重复，保留首次出现）、删除年龄缺失或异常（<0或>150）的行、删除薪资缺失的行后，还剩几行？",
    len([r for i, r in enumerate(dd)
         if not any(r["name"]==r2["name"] and r["age"]==r2["age"] and r["email"]==r2["email"] and r["salary"]==r2["salary"] for r2 in dd[:i])
         and r["age"]!='' and 0 <= int(r["age"]) <= 150 and r["salary"]!='']), "integer")
add(8,"数据质量", f"产品数据：\n{MISSING_DATA}\n\n用有效价格的中位数填充缺失价格后，所有产品的价格总和是多少（保留2位小数）？",
    round(sum(float(r["price"]) if r["price"] else stats.median([float(x["price"]) for x in mdata if x["price"]]) for r in mdata), 2))

add(9,"复杂变换", f"月销售数据：\n{MONTHLY_SALES}\n\n将数据透视为“行=产品、列=月份”，产品B这一行中最大值所在的月份是几月？",
    max(range(1,7), key=lambda m: next(r["sales"] for r in ms if r["product"]=="B" and r["month"]==m)))
add(9,"复杂变换", f"绩效数据：\n{RANK_DATA}\n\n每个季度内按分数降序排名（第1名=1），E004 三个季度的名次之和是多少？",
    sum(sorted([r["score"] for r in rd if r["quarter"]==q], reverse=True).index(next(r["score"] for r in rd if r["eid"]=="E004" and r["quarter"]==q))+1 for q in ["Q1","Q2","Q3"]))

# 一阶指数平滑 alpha=0.3，初值=首期
es = [REVENUE_TS[0]]
for v in REVENUE_TS[1:]:
    es.append(0.3*v + 0.7*es[-1])
add(10,"高级分析", f"营收时间序列（共20期）：{REVENUE_TS}\n\n做一阶指数平滑，α=0.3，初始平滑值=第1期实际值，第20期的平滑值是多少（保留2位小数）？", round(es[-1], 2))

tx = list(range(1, 21))
mtx, mty = sum(tx)/20, sum(REVENUE_TS)/20
slope = sum((tx[i]-mtx)*(REVENUE_TS[i]-mty) for i in range(20))/sum((t-mtx)**2 for t in tx)
icpt = mty - slope*mtx
add(10,"高级分析", f"营收时间序列（共20期，期数t=1..20）：{REVENUE_TS}\n\n用最小二乘线性回归 y=a·t+b 拟合，预测第21期的值（保留2位小数）？", round(slope*21+icpt, 2))

add(10,"高级分析", f"营收时间序列（共20期）：{REVENUE_TS}\n\n统计“比前一期下降”的期数有几个？", sum(1 for i in range(1,20) if REVENUE_TS[i] < REVENUE_TS[i-1]), "integer")

retained = {m: sum(u["m4"] for u in cohort if u["month"]==m)/sum(u["m1"] for u in cohort if u["month"]==m) for m in ["2024-01","2024-02","2024-03"]}
add(10,"高级分析", f"用户队列数据：\n{COHORT_DATA}\n\n按注册月分队列，计算各队列“第4月收入总和/第1月收入总和”，留存比最高的队列是哪个？输出如2024-01。",
    max(retained, key=retained.get), "string")

p_c, p_t = 0.12, 0.14
n_ab = 5000
p_pool = (p_c*n_ab + p_t*n_ab)/(2*n_ab)
z_ab = (p_t-p_c)/math.sqrt(p_pool*(1-p_pool)*(2/n_ab))
add(10,"高级分析", f"A/B测试：对照组 {n_ab} 人转化率 {p_c}，实验组 {n_ab} 人转化率 {p_t}。用合并比例的双比例 z 检验，z 值是多少（保留3位小数）？", round(z_ab, 3))

from collections import Counter
level_counts = Counter(c["level"] for c in cases)
print("Level distribution:", dict(level_counts))
print(f"Total cases: {len(cases)}")

from pathlib import Path
with open(Path(__file__).parent / 'test_cases.json', 'w', encoding='utf-8') as f:
    json.dump(cases, f, ensure_ascii=False, indent=2)

print("Test cases saved to test_cases.json")

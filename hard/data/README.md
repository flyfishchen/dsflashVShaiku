# 数据说明（必读）

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

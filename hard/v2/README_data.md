# 数据字典

一家跨境零售企业的数据仓库导出。目录结构即业务域，文件说明见下文。

## 业务约定

- **门店与业务日期**：门店信息见 `stores.csv`。订单的“业务日期”指门店本地时区下的日期；按日、月统计销售时默认使用业务日期。
- **夏令时**：美国门店的本地时间受夏令时影响。若某个本地时间因夏令时结束而出现两次，按第一次出现（夏令时）解释；若某个本地时间因夏令时开始而不存在，该订单的下单时间视为无效，其日期也不可用。
- **订单金额**：订单净额 = 订单原价 − 折扣。新系统订单的原价 = 各明细 qty × unit_price 之和，折扣 = 各促销 amount 之和。
- **有效订单**：状态为 completed 的订单。
- **新系统订单的多次导出**：新系统按变更导出，同一订单可能出现多条记录，以 `updated_at` 最新的一条为准。
- **汇率**：`fx_daily.csv` 为 1 美元兑人民币的汇率，只在工作日发布。把美元换算为人民币时，使用业务日期当天的汇率；当天没有汇率时，使用该日期之前最近一个有汇率的日期。
- **统计口径**：分位数默认使用线性插值（numpy.percentile / pandas.quantile 的默认方法）；标准差、方差默认使用样本统计量（ddof=1）；结果按题目要求的小数位四舍五入。

## 分析规范

- 完全相同的重复记录只保留一条。
- 同一取值的不同写法先统一再统计。
- 违反字段定义的值视为无效：只把该字段当作缺失，同一行的其他字段照常使用。
- 缺失值不参与计算，除非题目另有说明。
- 符合字段定义的数值以文件为准，不要因为“看起来异常”而修正或剔除。
- 题目给出的定义优先于本文件。

## 文件

### stores.csv —— 门店
`store_id`, `name`, `city`, `country`, `timezone`（IANA 时区名）, `currency`（该门店的结算币种）

### fx_daily.csv —— 汇率
`date`, `usd_cny`（1 美元兑人民币）

### sales/legacy/ —— 旧订单系统（2023 年）
按月导出，每个文件包含当月订单。字段依次为：订单号、门店、会员号（可为空，表示非会员）、下单时间（门店本地时间，不含时区）、币种、订单原价、折扣、订单状态（completed / cancelled）。

### sales/api/orders_2024.jsonl —— 新订单系统（2024 年）
每行一个 JSON 对象：

| 字段 | 说明 |
|---|---|
| `id` | 订单号 |
| `store.id` | 门店 |
| `channel` | 下单渠道：app / web / pos |
| `customer.member_id` | 会员号；`customer` 为 null 表示非会员 |
| `created_at` / `updated_at` | 创建时间 / 本条记录的更新时间（ISO 8601，带时区偏移） |
| `currency` | 币种 |
| `items[]` | 明细：`sku`, `qty`, `unit_price`（订单币种） |
| `promotions[]` | 促销：`code`, `amount`（订单币种） |
| `status` | completed / cancelled |

### payments/gateway_settlement.csv —— 支付网关结算
| 字段 | 说明 |
|---|---|
| `payment_id` | 支付流水号，主键 |
| `order_id` | 订单号 |
| `paid_at` | 时间（UTC） |
| `amount` | 金额（`currency` 币种），正数 |
| `fee` | 手续费：SUCCESS 为交易手续费，REVERSED 为拒付处理费，FAILED 为 0 |
| `status` | SUCCESS：扣款成功；FAILED：扣款失败（未扣款）；REVERSED：拒付冲回，`amount` 为被冲回的金额 |

### payments/refunds.csv —— 退款
`refund_id`（主键）, `order_id`, `refund_at`（UTC）, `amount`（正数）, `currency`

### crm/members_shop.csv —— 商城会员
`member_id`（主键）, `name`, `phone`（中国大陆手机号）, `email_addr`, `register_time`

### crm/contacts_crm.csv —— CRM 联系人
`crm_id`（主键）, `full_name`, `mobile`（中国大陆手机号）, `email`, `city`, `created_at`

### catalog/product_cdc.jsonl —— 商品表变更日志（CDC）
每行一个变更事件。事件按 `lsn` 从小到大依次生效。

| 字段 | 说明 |
|---|---|
| `lsn` | 日志序号，每个事件唯一 |
| `ts_ms` | 事件生效时间（UTC 毫秒时间戳） |
| `op` | r：初始快照；c：新增；u：更新；d：删除 |
| `sku` | 商品编码 |
| `before` / `after` | 变更前 / 后的整行内容：`sku`, `name`, `category`, `price_cny`（标价，人民币）, `status`；新增时 `before` 为 null，删除时 `after` 为 null |

### inventory/purchases.csv —— 采购入库批次
`lot_id`（主键）, `sku`, `received_at`（入库日期）, `qty`, `unit_cost`（单位成本，人民币）。2023-12-31 入库的批次为 2024 年期初库存。

### inventory/shipments.csv —— 出库
`shipment_id`（主键）, `sku`, `shipped_at`（出库日期）, `qty`。同一天内先入库、后出库。

### subscriptions/subscription_events.csv —— SaaS 订阅事件
| 字段 | 说明 |
|---|---|
| `account_id` | 账户 |
| `event_date` | 事件日期 |
| `seq` | 同一账户内的事件序号，越大越晚 |
| `event_type` | new / upgrade / downgrade / churn / reactivate |
| `plan` | 事件后的套餐 |
| `mrr_after` | 事件后的月度经常性收入（美元）；churn 后为 0 |

账户在某日日终的 MRR = 该日（含）之前最后一个事件的 `mrr_after`；没有事件则为 0。

### iot/devices.csv、iot/readings.csv.gz —— 仓库温度传感器
- devices：`device_id`, `site`（所在仓库）, `install_date`, `firmware`
- readings（gzip 压缩的 CSV）：`device_id`, `ts`（ISO 8601，带时区）, `temp`（温度，摄氏度，合理范围 −40 ~ 85）。设备标称每 5 分钟上报一次。

### marketing/ —— 营销
- touchpoints.csv：`user_id`, `ts`（北京时间）, `channel`, `campaign`
- conversions.csv：`conversion_id`（主键）, `user_id`, `ts`（北京时间）, `revenue`（人民币）
- spend.csv：`date`, `channel`, `spend`（人民币）

### experiments/ —— 实验
- ab_users.csv：`user_id`, `variant`（A / B）, `segment`（new / returning）, `converted`（0 / 1）, `pre_revenue`（实验前 30 天收入）, `post_revenue`（实验期收入）
- did_stores.csv：`store_id`, `week`（1–20）, `treated`（是否为处理组门店，0 / 1；处理从第 11 周开始）, `sales`
- multi_metric.csv：`user_id`, `variant`, `m01` … `m12`（12 个指标）

### logs/access.log —— Nginx 访问日志
每行格式：

```
$remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent" $request_time
```

`$time_local` 形如 `15/Oct/2024:14:05:01 +0800`（含时区偏移）；`$request` 为 “方法 路径 协议”；`$request_time` 为请求耗时（秒）。

### finance/ —— 总账
- chart_of_accounts.csv：`account`, `name`, `type`（asset / liability / equity / revenue / expense）, `normal_balance`
- gl_2024.txt：定长格式，每行一条分录。位置按字符计（不是字节），从 1 开始：

| 字段 | 位置 | 说明 |
|---|---|---|
| journal_id | 1–10 | 凭证号，左对齐 |
| line_no | 11–14 | 行号，右对齐 |
| posting_date | 15–22 | 记账日期 YYYYMMDD |
| account | 23–30 | 科目，左对齐 |
| dept | 31–34 | 部门 |
| currency | 35–37 | 币种 |
| amount | 38–53 | 金额，右对齐；最后一位为 `-` 表示贷方，为空格表示借方 |
| description | 54– | 摘要 |

每张凭证的借方合计应等于贷方合计。

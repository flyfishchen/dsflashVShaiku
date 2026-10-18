# 数据字典

## 业务约定
- 业务时区为北京时间（UTC+8）。凡是按日、周、月、小时统计，一律使用北京时间。
- “有效订单”指状态为 paid 的订单。
- 金额口径：行金额 = quantity × unit_price × (1 − discount_rate)；订单商品金额 = 该订单各明细行金额之和（没有明细则为 0）；订单 GMV = 订单商品金额 + shipping_fee。
- 汇率换算：非 CNY 金额换算成人民币时，使用订单北京时间日期当天的 rate_to_cny；当天没有汇率时，使用该日期之前最近一个有汇率的日期。CNY 的汇率为 1。
- 年龄以 2025-01-01 为基准计算周岁。
- 星期：周一 = 1 … 周日 = 7；ISO 周遵循 ISO 8601（周一为一周第一天）。
- 分位数默认使用线性插值（numpy.percentile / pandas.quantile 的默认方法）；标准差、方差默认使用样本统计量（ddof=1）。
- 结果按题目要求的小数位四舍五入。

## 分析规范
- 完全相同的重复记录只保留一条。
- 同一取值的不同写法先统一再统计。
- 违反字段定义的值视为无效：只把该字段当作缺失，同一行的其他字段照常使用。
- 缺失值不参与计算，除非题目另有说明。
- 符合字段定义的数值以文件为准，不要因为“看起来异常”而修正或剔除。

## 文件与字段

### customers.csv —— 客户表
| 字段 | 说明 |
|---|---|
| customer_id | 客户 ID，主键 |
| name | 姓名 |
| gender | 性别：M = 男，F = 女，空 = 未知 |
| birth_date | 出生日期 |
| city | 所在城市，中文城市名（不带“市”字） |
| phone | 手机号 |
| email | 邮箱 |
| signup_date | 注册日期 |
| tier | 会员等级：金 / 银 / 铜，空 = 无等级 |

### products.csv —— 商品表
| 字段 | 说明 |
|---|---|
| product_id | 商品 ID，主键 |
| product_name | 商品名称，格式为“品牌 型号”或“品牌 型号 后缀” |
| category / subcategory | 一级 / 二级类目 |
| list_price | 标价（人民币元） |
| cost | 成本（人民币元） |
| supplier_id | 供应商 ID |
| launch_date | 上架日期 |

### orders.csv —— 订单表
| 字段 | 说明 |
|---|---|
| order_id | 订单 ID，主键 |
| customer_id | 下单客户 ID |
| order_time | 下单时间 |
| status | 订单状态：paid / refunded / cancelled |
| channel | 下单渠道：app / web / mini_program |
| currency | 币种：CNY / USD / HKD |
| shipping_fee | 运费（订单币种） |
| coupon_code | 优惠码，空 = 未使用 |

### order_items.csv —— 订单明细
| 字段 | 说明 |
|---|---|
| order_id | 订单 ID |
| line_no | 行号；(order_id, line_no) 唯一 |
| product_id | 商品 ID |
| quantity | 购买数量，正整数 |
| unit_price | 成交单价（订单币种） |
| discount_rate | 折扣率，0 ≤ discount_rate < 1 |

### fx_rates.csv —— 汇率
| 字段 | 说明 |
|---|---|
| date | 日期 |
| currency | 币种 |
| rate_to_cny | 1 单位外币兑换的人民币数 |

### events.csv —— 用户行为日志
| 字段 | 说明 |
|---|---|
| user_id | 用户 ID |
| event_time | 事件时间，UTC 毫秒时间戳 |
| event_type | view / add_to_cart / checkout / purchase |
| product_id | 商品 ID |

### daily_kpi.csv —— 每日指标
| 字段 | 说明 |
|---|---|
| date | 日期，每天一行 |
| dau | 日活跃用户数 |
| revenue | 当日收入（元），非负 |

### legacy_sales.csv —— 旧门店系统导出的月度销售
| 字段 | 说明 |
|---|---|
| 门店 | 门店名称 |
| 区域 | 所属区域 |
| 月份 | YYYY-MM |
| 销售额 | 当月销售额（元） |

### ab_test.csv —— A/B 实验
| 字段 | 说明 |
|---|---|
| user_id | 用户 ID |
| group | 实验组：A / B；每个用户只属于一个组 |
| converted | 是否转化：0 / 1 |
| revenue | 转化收入（元） |

### employees.csv —— 员工表
| 字段 | 说明 |
|---|---|
| emp_id | 员工 ID，主键 |
| name | 姓名 |
| dept | 部门 |
| manager_id | 直属上级的 emp_id；CEO 为空 |
| salary | 月薪（元） |
| hire_date | 入职日期 |

### support_tickets.csv —— 客服工单
| 字段 | 说明 |
|---|---|
| ticket_id | 工单 ID，主键 |
| customer_id | 客户 ID，可为空 |
| created_at | 创建时间 |
| channel | 渠道 |
| text | 工单内容 |

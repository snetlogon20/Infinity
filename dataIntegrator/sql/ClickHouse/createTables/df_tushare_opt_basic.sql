--drop table indexsysdb.df_tushare_opt_basic
CREATE TABLE IF NOT EXISTS indexsysdb.df_tushare_opt_basic
(
    `ts_code` String COMMENT 'TS代码',
    `symbol` String COMMENT '交易代码',
    `exchange` String COMMENT '交易市场',
    `name` String COMMENT '合约名称',
    `per_unit` String COMMENT '合约单位',
    `opt_code` String COMMENT '标的合约代码',
    `opt_type` String COMMENT '合约类型',
    `call_put` String COMMENT '期权类型',
    `exercise_type` String COMMENT '行权方式',
    `exercise_price` Float64 COMMENT '行权价格，经过除权除息调整',
    `opt_multiplier` Float64 COMMENT '合约单位，经过除权除息调整',
    `s_month` String COMMENT '结算月',
    `maturity_date` String COMMENT '到期日',
    `list_price` Float64 COMMENT '挂牌基准价',
    `list_date` String COMMENT '开始交易日期',
    `delist_date` String COMMENT '最后交易日期',
    `last_edate` String COMMENT '最后行权日期',
    `last_ddate` String COMMENT '最后交割日期',
    `quote_unit` String COMMENT '报价单位',
    `min_price_chg` String COMMENT '最小价格波幅'
) ENGINE = MergeTree
ORDER BY (ts_code, exchange, list_date)
SETTINGS index_granularity = 8192;

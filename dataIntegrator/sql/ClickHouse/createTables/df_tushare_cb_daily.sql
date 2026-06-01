-- 可转债日线行情数据表
--drop table indexsysdb.df_tushare_cb_daily
CREATE TABLE IF NOT EXISTS indexsysdb.df_tushare_cb_daily
(
    `ts_code` String COMMENT '转债代码',
    `trade_date` String COMMENT '交易日期',
    `pre_close` Float64 COMMENT '昨收盘价(元)',
    `open` Float64 COMMENT '开盘价(元)',
    `high` Float64 COMMENT '最高价(元)',
    `low` Float64 COMMENT '最低价(元)',
    `close` Float64 COMMENT '收盘价(元)',
    `change` Float64 COMMENT '涨跌(元)',
    `pct_chg` Float64 COMMENT '涨跌幅(%)',
    `vol` Float64 COMMENT '成交量(手)',
    `amount` Float64 COMMENT '成交金额(万元)',
    `bond_value` Float64 COMMENT '纯债价值',
    `bond_over_rate` Float64 COMMENT '纯债溢价率(%)',
    `cb_value` Float64 COMMENT '转股价值',
    `cb_over_rate` Float64 COMMENT '转股溢价率(%)'
)
ENGINE = MergeTree()
ORDER BY (ts_code, trade_date)
SETTINGS index_granularity = 8192;

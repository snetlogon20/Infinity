--drop table indexsysdb.df_tushare_opt_daily
--ALTER TABLE indexsysdb.df_tushare_opt_daily DELETE WHERE 1=1;
--ALTER TABLE indexsysdb.df_tushare_opt_daily DELETE WHERE trade_date = '20251224';
CREATE TABLE IF NOT EXISTS indexsysdb.df_tushare_opt_daily
(
    `ts_code` String COMMENT 'TS合约代码',
    `trade_date` String COMMENT '交易日期',
    `exchange` String COMMENT '交易市场',
    `pre_settle` Float64 COMMENT '昨结算价',
    `pre_close` Float64 COMMENT '前收盘价',
    `open` Float64 COMMENT '开盘价',
    `high` Float64 COMMENT '最高价',
    `low` Float64 COMMENT '最低价',
    `close` Float64 COMMENT '收盘价',
    `settle` Float64 COMMENT '结算价',
    `vol` Float64 COMMENT '成交量(手)',
    `amount` Float64 COMMENT '成交金额(万元)',
    `oi` Float64 COMMENT '持仓量(手)'
) ENGINE = MergeTree
ORDER BY (ts_code, trade_date)
SETTINGS index_granularity = 8192;

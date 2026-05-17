--国债收益曲线
--drop table indexsysdb.df_tushare_yc_cb;
CREATE TABLE IF NOT EXISTS indexsysdb.df_tushare_yc_cb
(
    `trade_date` String COMMENT '交易日期',
    `ts_code` String COMMENT '曲线编码',
    `curve_name` String COMMENT '曲线名称',
    `curve_type` String COMMENT '曲线类型：0-到期，1-即期',
    `curve_term` Float64 COMMENT '期限(年)',
    `yield` Float64 COMMENT '收益率(%)'
) ENGINE = MergeTree
ORDER BY (trade_date, ts_code, curve_type, curve_term)
SETTINGS index_granularity = 8192;

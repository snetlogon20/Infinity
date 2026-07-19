-- D:\workspace_python\infinity\dataIntegrator\sql\ClickHouse\createTables\indexsysdb.df_cboe_vix.sql
--drop table indexsysdb.df_cboe_vix
--恐慌指数VIX历史数据（1990年至今）
CREATE TABLE indexsysdb.df_cboe_vix (
    date String,
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    pct_change Float64
)
ENGINE=SummingMergeTree(date)
ORDER BY (date)
SETTINGS index_granularity = 8192;

--drop table indexsysdb.df_nyfed_sofr_daily
CREATE TABLE IF NOT EXISTS indexsysdb.df_nyfed_sofr_daily (
    date String,
    sofr Float64,
    volume_bn Float64 DEFAULT 0,
    sofr_change_bp Float64 DEFAULT 0
)
ENGINE=ReplacingMergeTree()
ORDER BY (date)
SETTINGS index_granularity = 8192;

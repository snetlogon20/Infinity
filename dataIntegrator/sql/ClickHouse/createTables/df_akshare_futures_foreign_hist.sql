--drop table indexsysdb.df_akshare_futures_foreign_hist
CREATE TABLE indexsysdb.df_akshare_futures_foreign_hist (
    date String,
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume Int64,
    position Int64,
    settlement Float64,
    symbol String,
    pct_change Float64
)
ENGINE=SummingMergeTree(date)
ORDER BY (date)
SETTINGS index_granularity = 8192;
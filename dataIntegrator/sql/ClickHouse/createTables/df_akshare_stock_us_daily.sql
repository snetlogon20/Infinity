--drop table indexsysdb.df_akshare_stock_us_daily
CREATE TABLE indexsysdb.df_akshare_stock_us_daily (
    date String,
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume Float64,
    amount Float64 DEFAULT 0,
    symbol String,
    pct_change Float64 DEFAULT 0
)
ENGINE=SummingMergeTree(date)
ORDER BY (date, symbol)
SETTINGS index_granularity = 8192;
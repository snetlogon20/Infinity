--年报季报
--drop table indexsysdb.df_akshare_stock_yjbb_em
CREATE TABLE indexsysdb.df_akshare_stock_yjbb_em (
    date String,
    stock_code String,
    stock_name String,
    eps Float64,
    total_revenue Float64,
    total_revenue_yoy Float64,
    total_revenue_qoq Float64,
    net_profit Float64,
    net_profit_yoy Float64,
    net_profit_qoq Float64,
    bvps Float64,
    roe Float64,
    cfps Float64,
    gross_profit_margin Float64,
    industry String,
    latest_announce_date String
)
ENGINE=SummingMergeTree(date)
ORDER BY (date, stock_code)
SETTINGS index_granularity = 8192;

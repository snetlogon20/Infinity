-- D:\workspace_python\infinity\dataIntegrator\sql\ClickHouse\createTables\df_akshare_bond_zh_us_rate.sql
--drop table indexsysdb.df_akshare_bond_zh_us_rate
--中美国债收益率历史数据
CREATE TABLE indexsysdb.df_akshare_bond_zh_us_rate (
    trade_date String,
    cn_yield_2y Float64,
    cn_yield_5y Float64,
    cn_yield_10y Float64,
    cn_yield_30y Float64,
    cn_yield_spread_10y2y Float64,
    cn_gdp_yoy Float64,
    us_yield_2y Float64,
    us_yield_5y Float64,
    us_yield_10y Float64,
    us_yield_30y Float64,
    us_yield_spread_10y2y Float64,
    us_gdp_yoy Float64
)
ENGINE=SummingMergeTree(trade_date)
ORDER BY (trade_date)
SETTINGS index_granularity = 8192;

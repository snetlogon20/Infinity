drop table indexsysdb.df_tushare_shibor_daily;
CREATE TABLE indexsysdb.df_tushare_shibor_daily(
trade_date String,
tenor_on Float64,
tenor_1w Float64,
tenor_2w Float64,
tenor_1m Float64,
tenor_3m Float64,
tenor_6m Float64,
tenor_9m Float64,
tenor_1y Float64
)
ENGINE=SummingMergeTree(trade_date)
order by (trade_date)
SETTINGS index_granularity = 8192;

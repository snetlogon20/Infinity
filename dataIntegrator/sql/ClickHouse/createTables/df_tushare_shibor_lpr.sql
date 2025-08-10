drop table indexsysdb.df_tushare_shibor_lpr_daily;
CREATE TABLE indexsysdb.df_tushare_shibor_lpr_daily(
trade_date	 String,
tenor_1y Float64,
tenor_5 Float64
)
ENGINE=SummingMergeTree(trade_date)
order by (trade_date)
SETTINGS index_granularity = 8192


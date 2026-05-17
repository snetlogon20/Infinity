--全球指数
--drop table indexsysdb.df_tushare_index_global;
CREATE TABLE indexsysdb.df_tushare_index_global(
ts_code	String,
trade_date	String,
open	Float64,
close	Float64,
high	Float64,
low	Float64,
pre_close	Float64,
change	Float64,
pct_chg	Float64,
swing	Float64,
vol	Float64,
amount Float64
)
ENGINE=SummingMergeTree(ts_code)
order by (ts_code,trade_date)
SETTINGS index_granularity = 8192

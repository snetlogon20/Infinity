--step 0 create table
drop table indexsysdb.df_tushare_cn_index_daily;
CREATE TABLE indexsysdb.df_tushare_cn_index_daily(
ts_code	String,
trade_date	String,
close	Float64,
open	Float64,
high	Float64,
low	Float64,
pre_close	Float64,
change	Float64,
pct_chg	Float64,
vol	Float64,
amount Float64
)
ENGINE=SummingMergeTree(ts_code)
order by (ts_code,trade_date)
SETTINGS index_granularity = 8192
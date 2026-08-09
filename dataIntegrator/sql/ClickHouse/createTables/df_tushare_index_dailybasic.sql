--step 0 create table
drop table indexsysdb.df_tushare_index_dailybasic;
CREATE TABLE indexsysdb.df_tushare_index_dailybasic(
ts_code	String,
trade_date	String,
total_mv	Float64,
float_mv	Float64,
total_share	Float64,
float_share	Float64,
free_share	Float64,
turnover_rate	Float64,
turnover_rate_f	Float64,
pe	Float64,
pe_ttm	Float64,
pb	Float64
)
ENGINE=SummingMergeTree(ts_code)
order by (ts_code,trade_date)
SETTINGS index_granularity = 8192

--step 0 create table
drop table indexsysdb.df_tushare_future_daily;
CREATE TABLE indexsysdb.df_tushare_future_daily(
ts_code        String,
trade_date     String,
pre_close     Float64,
pre_settle    Float64,
open          Float64,
high          Float64,
low           Float64,
close         Float64,
settle        Float64,
change1       Float64,
change2       Float64,
vol           Float64,
amount        Float64,
oi            Float64,
oi_chg        Float64
)
ENGINE=SummingMergeTree(ts_code)
order by (ts_code, trade_date)
SETTINGS index_granularity = 8192

ts_code,
trade_date,
pre_close,
pre_settle,
open,
high,
low,
close,
settle,
change1,
change2,
vol,
amount,
oi,
oi_chg


'ts_code',
'symbol',
'name',
'quote_unit',
'list_date',
'delist_date'
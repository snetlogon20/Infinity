--drop table indexsysdb.cn_cpi
CREATE TABLE indexsysdb.df_tushare_hk_stock_daily(
ts_code        String,
trade_date     String,
open          Float64,
high          Float64,
low           Float64,
close         Float64,
pre_close     Float64,
change        Float64,
pct_chg       Float64,
vol           Float64,
amount        Float64
)
ENGINE=SummingMergeTree(trade_date)
order by (trade_date, ts_code )
SETTINGS index_granularity = 8192;

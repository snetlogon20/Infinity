--drop table indexsysdb.df_tushare_sge_daily
CREATE TABLE indexsysdb.df_tushare_sge_daily(
ts_code         String,
trade_date      String,
close          Float64,
open           Float64,
high           Float64,
low            Float64,
price_avg      Float64,
change         Float64,
pct_change     Float64,
vol            Float64,
amount         Float64,
oi             Float64,
settle_vol     Nullable(Float64),
settle_dire     Nullable(String)
)
ENGINE=SummingMergeTree(trade_date)
order by (trade_date, ts_code )
SETTINGS index_granularity = 8192

ts_code,
trade_date,
close,
open,
high,
low,
price_avg,
change,
pct_change,
vol,
amount,
oi,
settle_vol,
settle_dire
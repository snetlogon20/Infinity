--drop table indexsysdb.df_tushare_fx_daily
CREATE TABLE indexsysdb.df_tushare_fx_daily(
ts_code        String,
trade_date     String,
bid_open      Float64,
bid_close     Float64,
bid_high      Float64,
bid_low       Float64,
ask_open      Float64,
ask_close     Float64,
ask_high      Float64,
ask_low       Float64,
tick_qty        Int64
)
ENGINE=SummingMergeTree(trade_date)
order by (trade_date, ts_code )
SETTINGS index_granularity = 8192

ts_code,
trade_date,
bid_open,
bid_close,
bid_high,
bid_low,
ask_open,
ask_close,
ask_high,
ask_low,
tick_qty
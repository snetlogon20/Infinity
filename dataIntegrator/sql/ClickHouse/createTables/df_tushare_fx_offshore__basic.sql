--drop table indexsysdb.df_tushare_fx_offshore_basic
CREATE TABLE indexsysdb.df_tushare_fx_offshore_basic(
ts_code              String,
name                 String,
classify             String,
exchange             String,
min_unit             Float64,
max_unit             Float64,
pip                  Float64,
pip_cost             Float64,
traget_spread        Float64,
min_stop_distance    Float64,
trading_hours         Nullable(String),
break_time            Nullable(String)
)
ENGINE=SummingMergeTree(ts_code)
order by (ts_code, name )
SETTINGS index_granularity = 8192;

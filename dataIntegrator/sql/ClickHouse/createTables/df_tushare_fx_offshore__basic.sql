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
SETTINGS index_granularity = 8192

ts_code,
name,
classify ,
exchange,
min_unit ,
max_unit,
pip ,
pip_cost,
traget_spread,
min_stop_distance,
trading_hours,
break_time

'trade_date',
'nt_val',
'nt_yoy',
'nt_mom',
'nt_accu',
'town_val',
'town_yoy',
'town_mom',
'town_accu',
'cnt_val',
'cnt_yoy',
'cnt_mom',
'cnt_accu'
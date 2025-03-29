--drop table indexsysdb.cn_cpi
CREATE TABLE indexsysdb.us_stock_daily(
ts_code    String,
trade_date String,
close_point	   float,
open_point	   float,
high_point	   float,
low_point	       float,
pre_close  float,
change_point	   float,
pct_change	float,
vol	        float,
amount	    float,
vwap	    float,
turnover_ratio	float,
total_mv	float,
pe	float,
pb	float
)
ENGINE=SummingMergeTree(trade_date, ts_code)
order by (trade_date, ts_code )
SETTINGS index_granularity = 8192

trade_date,
nt_val    ,
nt_yoy    ,
nt_mom    ,
nt_accu   ,
town_val  ,
town_yoy  ,
town_mom  ,
town_accu ,
cnt_val   ,
cnt_yoy   ,
cnt_mom   ,
cnt_accu

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
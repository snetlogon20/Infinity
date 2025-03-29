--drop table indexsysdb.df_tushare_cn_cpi
CREATE TABLE indexsysdb.df_tushare_cn_cpi(
trade_date    String,
nt_val       Float64,
nt_yoy       Float64,
nt_mom       Float64,
nt_accu      Float64,
town_val     Float64,
town_yoy     Float64,
town_mom     Float64,
town_accu    Float64,
cnt_val      Float64,
cnt_yoy      Float64,
cnt_mom      Float64,
cnt_accu     Float64
)
ENGINE=SummingMergeTree(trade_date)
order by (trade_date)
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
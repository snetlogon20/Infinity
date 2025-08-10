--drop table indexsysdb.df_tushare_us_treasury_yield_cruve
CREATE TABLE indexsysdb.df_tushare_us_treasury_yield_cruve(
	trade_date    String,
    m1    float,
    m2    float,
    m3    float,
    m6    float,
    y1    float,
    y2    float,
    y3    float,
    y5    float,
    y7    float,
    y10   float,
    y20   float,
    y30   float
)
ENGINE=SummingMergeTree(trade_date)
order by (trade_date)
SETTINGS index_granularity = 8192

trade_date,
m1,
m2,
m3,
m6,
y1,
y2,
y3,
y5,
y7,
y1,
y2,
y30

'trade_date’,
'm1'    ,
'm2'    ,
'm3'    ,
'm6'    ,
'y1'    ,
'y2'    ,
'y3'    ,
'y5'    ,
'y7'    ,
'y10'   ,
'y20'   ,
'y30'
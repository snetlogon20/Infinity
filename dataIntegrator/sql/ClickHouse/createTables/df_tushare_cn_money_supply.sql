--drop table indexsysdb.cn_money_supply;
CREATE TABLE indexsysdb.cn_money_supply(
trade_date     String,
m0        Float64,
m0_yoy    Float64,
m0_mom    Float64,
m1        Float64,
m1_yoy    Float64,
m1_mom    Float64,
m2        Float64,
m2_yoy    Float64,
m2_mom    Float64
)
ENGINE=SummingMergeTree(trade_date)
order by (trade_date)
SETTINGS index_granularity = 8192

trade_date,
m0    ,
m0_yoy,
m0_mom,
m1    ,
m1_yoy,
m1_mom,
m2    ,
m2_yoy,
m2_mom

'trade_date',
'm0',
'm0_yoy',
'm0_mom',
'm1',
'm1_yoy',
'm1_mom',
'm2',
'm2_yoy',
'm2_mom'

drop table indexsysdb.df_tushare_cn_gdp;
CREATE TABLE indexsysdb.df_tushare_cn_gdp(
quarter	   String,
gdp        Float64,
gdp_yoy    Float64,
pi         Float64,
pi_yoy     Float64,
si         Float64,
si_yoy     Float64,
ti         Float64,
ti_yoy     Float64
)
ENGINE=SummingMergeTree(quarter)
order by (quarter)
SETTINGS index_granularity = 8192

quarter	   ,
gdp        ,
gdp_yoy    ,
pi         ,
pi_yoy     ,
si         ,
si_yoy     ,
ti         ,
ti_yoy

'quarter',
'gdp',
'gdp_yoy',
'pi',
'pi_yoy',
'si',
'si_yoy',
'ti',
'ti_yoy'

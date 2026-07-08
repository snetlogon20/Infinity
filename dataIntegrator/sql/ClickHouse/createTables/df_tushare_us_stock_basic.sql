--drop table indexsysdb.df_tushare_us_stock_basic
CREATE TABLE indexsysdb.df_tushare_us_stock_basic(
ts_code        String,
name           Nullable(String),
enname         String,
classify       String,
list_date      String,
delist_date    Nullable(String)
)
ENGINE=SummingMergeTree(ts_code)
order by (ts_code)
SETTINGS index_granularity = 8192


ts_code,
name,
enname,
classify,
list_date,
delist_date,

'ts_code',
'name',
'classify',
'list_date',
'delist_date'

INSERT INTO df_tushare_us_stock_basic (ts_code,name,enname,classify,list_date,delist_date) VALUES
	 ('AAPL','苹果','APPLE','EQ','19801212','Nan'),
	 ('BAC','美国银行','BANK OF AMERICA','EQ','19690102','Nan'),
	 ('C','花旗','CITIGROUP','EQ','19861029','Nan'),
	 ('JPM','JP 摩根','JP morgan','EQ','19801212','Nan'),
	 ('NVDA','英伟达','NVIDIA','EQ','19801212','Nan'),
	 ('INTC','因特尔','INTEL','EQ','19801212','Nan');
--step 0 create table
drop table indexsysdb.df_tushare_future_basic_information;
CREATE TABLE indexsysdb.df_tushare_future_basic_information(
ts_code        String,
symbol         String,
name           String,
quote_unit     String,
list_date      String,
delist_date    String
)
ENGINE=SummingMergeTree(ts_code)
order by (ts_code)
SETTINGS index_granularity = 8192;

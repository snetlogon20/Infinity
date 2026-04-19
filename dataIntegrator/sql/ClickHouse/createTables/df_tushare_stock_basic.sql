-- df_tushare_stock_basic.sql
-- stock_basic 接口：获取股票列表

CREATE TABLE indexsysdb.df_tushare_stock_basic
(
    ts_code String,
    symbol String,
    name String,
    area String,
    industry String,
    fullname String,
    enname String,
    cnspell String,
    market String,
    exchange String,
    curr_type String,
    list_status String,
    list_date String,
    delist_date String,
    is_hs String,
    act_name String,
    act_ent_type String
)
ENGINE = SummingMergeTree()
ORDER BY (ts_code, list_date);

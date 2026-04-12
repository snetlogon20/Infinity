-- D:\workspace_python\infinity\dataIntegrator\sql\ClickHouse\createTables\df_macro_china_new_house_price.sql
--drop table indexsysdb.df_macro_china_new_house_price
CREATE TABLE indexsysdb.df_macro_china_new_house_price (
    date String,
    city String,
    new_home_price_index_mom Float64,
    new_home_price_index_yoy Float64,
    new_home_price_index_fixed_base Float64,
    second_hand_home_price_index_mom Float64,
    second_hand_home_price_index_yoy Float64,
    second_hand_home_price_index_fixed_base Float64
)
ENGINE=SummingMergeTree(date)
ORDER BY (date, city)
SETTINGS index_granularity = 8192;
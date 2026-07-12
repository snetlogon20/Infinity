-- D:\workspace_python\infinity\dataIntegrator\sql\ClickHouse\createTables\indexsysdb.df_macro_china_fx_gold.sql
--drop table indexsysdb.df_macro_china_fx_gold
CREATE TABLE indexsysdb.df_macro_china_fx_gold (
    month String,
    gold_reserves_value Float64,
    gold_reserves_yoy Float64,
    gold_reserves_mom Float64,
    forex_reserves_value Float64,
    forex_reserves_yoy Float64,
    forex_reserves_mom Float64
)
ENGINE=SummingMergeTree(month)
ORDER BY (month)
SETTINGS index_granularity = 8192;

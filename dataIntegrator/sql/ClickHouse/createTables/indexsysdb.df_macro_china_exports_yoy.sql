-- D:\workspace_python\infinity\dataIntegrator\sql\ClickHouse\createTables\indexsysdb.df_macro_china_exports_yoy.sql
--drop table indexsysdb.df_macro_china_exports_yoy
CREATE TABLE indexsysdb.df_macro_china_exports_yoy (
    item String,
    date String,
    current_value Float64,
    forecast_value Float64,
    previous_value Float64
)
ENGINE=SummingMergeTree(date)
ORDER BY (date)
SETTINGS index_granularity = 8192;

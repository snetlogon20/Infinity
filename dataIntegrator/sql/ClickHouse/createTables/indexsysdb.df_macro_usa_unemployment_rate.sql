-- D:\workspace_python\infinity\dataIntegrator\sql\ClickHouse\createTables\indexsysdb.df_macro_usa_unemployment_rate.sql
--drop table indexsysdb.df_macro_usa_unemployment_rate
--美国失业率月度数据（1970年至今）
CREATE TABLE indexsysdb.df_macro_usa_unemployment_rate (
    date String,
    value Float64
)
ENGINE=SummingMergeTree(date)
ORDER BY (date)
SETTINGS index_granularity = 8192;

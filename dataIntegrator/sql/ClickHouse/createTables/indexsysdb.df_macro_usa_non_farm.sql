-- D:\workspace_python\infinity\dataIntegrator\sql\ClickHouse\createTables\indexsysdb.df_macro_usa_non_farm.sql
--drop table indexsysdb.df_macro_usa_non_farm
--美国非农就业人数月度数据（每月新增就业人数）
CREATE TABLE indexsysdb.df_macro_usa_non_farm (
    date String,
    value Float64
)
ENGINE=SummingMergeTree(date)
ORDER BY (date)
SETTINGS index_granularity = 8192;

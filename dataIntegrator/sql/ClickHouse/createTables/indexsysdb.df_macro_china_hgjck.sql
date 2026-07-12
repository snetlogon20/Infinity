-- D:\workspace_python\infinity\dataIntegrator\sql\ClickHouse\createTables\indexsysdb.df_macro_china_hgjck.sql
--drop table indexsysdb.df_macro_china_hgjck
--海关进出口增减情况一览表(进出口总额同比
CREATE TABLE indexsysdb.df_macro_china_hgjck (
    month String,
    monthly_exports_value Float64,
    monthly_exports_yoy Float64,
    monthly_exports_mom Float64,
    monthly_imports_value Float64,
    monthly_imports_yoy Float64,
    monthly_imports_mom Float64,
    cumulative_exports_value Float64,
    cumulative_exports_yoy Float64,
    cumulative_imports_value Float64,
    cumulative_imports_yoy Float64
)
ENGINE=SummingMergeTree(month)
ORDER BY (month)
SETTINGS index_granularity = 8192;

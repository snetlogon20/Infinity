--AkShare-股票数据-财务指标计算结果矩阵 (Altman Z-Score / PD / EL)
--drop table indexsysdb.df_akshare_stock_financial_analysis_indicator_matrics
CREATE TABLE indexsysdb.df_akshare_stock_financial_analysis_indicator_matrics (
    date String,
    symbol String,
    name String,
    industry String,
    z_score Float64,
    risk_level String,
    pd Float64,
    el Float64,
    ead Float64,
    total_assets Float64,
    total_equity Float64,
    total_liabilities Float64,
    profit_before_tax Float64,
    revenue Float64,
    current_assets Float64,
    current_liabilities Float64,
    retained_earnings Float64,
    x1 Float64,
    x2 Float64,
    x3 Float64,
    x4 Float64,
    x5 Float64
)
ENGINE = MergeTree()
ORDER BY (date, symbol)
SETTINGS index_granularity = 8192;

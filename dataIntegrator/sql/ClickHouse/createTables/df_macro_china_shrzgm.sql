-- D:\workspace_python\infinity\dataIntegrator\sql\ClickHouse\createTables\df_macro_china_shrzgm.sql
--drop table indexsysdb.df_macro_china_shrzgm
--社会融资规模增量统计
CREATE TABLE indexsysdb.df_macro_china_shrzgm (
    month String,
    total_shrzgm Float64,
    rmb_loan Float64,
    entrusted_loan_foreign_currency_loan Float64,
    entrusted_loan Float64,
    trust_loan Float64,
    undiscounted_bank_acceptance_bills Float64,
    corporate_bonds Float64,
    non_financial_enterprise_domestic_equity_financing Float64
)
ENGINE=SummingMergeTree(month)
ORDER BY (month)
SETTINGS index_granularity = 8192;
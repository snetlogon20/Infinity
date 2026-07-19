--drop table indexsysdb.df_tushare_cn_ppi
CREATE TABLE indexsysdb.df_tushare_cn_ppi(
trade_date         String COMMENT '月份YYYYMM',
ppi_yoy            Float64 COMMENT 'PPI：全部工业品：当月同比',
ppi_mp_yoy         Float64 COMMENT 'PPI：生产资料：当月同比',
ppi_mp_qm_yoy      Float64 COMMENT 'PPI：生产资料：采掘业：当月同比',
ppi_mp_rm_yoy      Float64 COMMENT 'PPI：生产资料：原料业：当月同比',
ppi_mp_p_yoy       Float64 COMMENT 'PPI：生产资料：加工业：当月同比',
ppi_cg_yoy         Float64 COMMENT 'PPI：生活资料：当月同比',
ppi_cg_f_yoy       Float64 COMMENT 'PPI：生活资料：食品类：当月同比',
ppi_cg_c_yoy       Float64 COMMENT 'PPI：生活资料：衣着类：当月同比',
ppi_cg_adu_yoy     Float64 COMMENT 'PPI：生活资料：一般日用品类：当月同比',
ppi_cg_dcg_yoy     Float64 COMMENT 'PPI：生活资料：耐用消费品类：当月同比',
ppi_mom            Float64 COMMENT 'PPI：全部工业品：环比',
ppi_mp_mom         Float64 COMMENT 'PPI：生产资料：环比',
ppi_mp_qm_mom      Float64 COMMENT 'PPI：生产资料：采掘业：环比',
ppi_mp_rm_mom      Float64 COMMENT 'PPI：生产资料：原料业：环比',
ppi_mp_p_mom       Float64 COMMENT 'PPI：生产资料：加工业：环比',
ppi_cg_mom         Float64 COMMENT 'PPI：生活资料：环比',
ppi_cg_f_mom       Float64 COMMENT 'PPI：生活资料：食品类：环比',
ppi_cg_c_mom       Float64 COMMENT 'PPI：生活资料：衣着类：环比',
ppi_cg_adu_mom     Float64 COMMENT 'PPI：生活资料：一般日用品类：环比',
ppi_cg_dcg_mom     Float64 COMMENT 'PPI：生活资料：耐用消费品类：环比',
ppi_accu           Float64 COMMENT 'PPI：全部工业品：累计同比',
ppi_mp_accu        Float64 COMMENT 'PPI：生产资料：累计同比',
ppi_mp_qm_accu     Float64 COMMENT 'PPI：生产资料：采掘业：累计同比',
ppi_mp_rm_accu     Float64 COMMENT 'PPI：生产资料：原料业：累计同比',
ppi_mp_p_accu      Float64 COMMENT 'PPI：生产资料：加工业：累计同比',
ppi_cg_accu        Float64 COMMENT 'PPI：生活资料：累计同比',
ppi_cg_f_accu      Float64 COMMENT 'PPI：生活资料：食品类：累计同比',
ppi_cg_c_accu      Float64 COMMENT 'PPI：生活资料：衣着类：累计同比',
ppi_cg_adu_accu    Float64 COMMENT 'PPI：生活资料：一般日用品类：累计同比',
ppi_cg_dcg_accu    Float64 COMMENT 'PPI：生活资料：耐用消费品类：累计同比'
)
ENGINE=SummingMergeTree(trade_date)
order by (trade_date)
SETTINGS index_granularity = 8192

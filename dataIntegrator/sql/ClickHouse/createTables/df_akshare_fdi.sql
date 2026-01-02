--drop table indexsysdb.df_akshare_fdi
CREATE TABLE indexsysdb.df_akshare_fdi (
    month String,
    current_month Float64,
    YoY Float64,
    MoM Float64,
    YTD_YoY Float64,
    YTD_MoM Float64
)
ENGINE=SummingMergeTree(month)
ORDER BY (month)
SETTINGS index_granularity = 8192;

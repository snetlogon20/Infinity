--drop table indexsysdb.df_akshare_spot_hist_sge
CREATE TABLE indexsysdb.df_akshare_spot_hist_sge (
    date String,
    open Float64,
    close Float64,
    low Float64,
    high Float64
)
ENGINE=SummingMergeTree(date)
ORDER BY (date)
SETTINGS index_granularity = 8192;


trade_date,
trade_year,
trade_month,
trade_day,
day_of_week,
quarter,
calendar_date,
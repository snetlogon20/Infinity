--drop table indexsysdb.df_tushare_us_stock_daily
-- indexsysdb.df_tushare_us_stock_daily definition

create table indexsysdb.df_tushare_us_stock_daily
(

    `ts_code` String,
`trade_date` String,
`close_point` Float32,
`open_point` Float32,
`high_point` Float32,
`low_point` Float32,
`pre_close` Float32,
`change_point` Float32,
`pct_change` Float32,
`vol` Float32,
`amount` Float32,
`vwap` Float32,
`turnover_ratio` Float32,
`total_mv` Float32,
`pe` Float32,
`pb` Float32
)
engine = SummingMergeTree(ts_code)
order by
(trade_date,
ts_code)
settings index_granularity = 8192;

--drop table indexsysdb.df_sys_calendar
CREATE TABLE indexsysdb.df_sys_calendar (
    trade_date String,
    trade_year String,
    trade_month String,
    trade_day String,
    day_of_week String,
    quarter String,
    calendar_date String
)
ENGINE=SummingMergeTree(trade_date)
order by (trade_date)
SETTINGS index_granularity = 8192


trade_date,
trade_year,
trade_month,
trade_day,
day_of_week,
quarter,
calendar_date,
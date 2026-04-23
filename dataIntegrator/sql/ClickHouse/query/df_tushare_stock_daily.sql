--×ÔÑ¡¹É
select 
    ts_code as ts_code,
    trade_date as trade_date,
    close as close_point
from indexsysdb.df_tushare_stock_daily
where ts_code in 
(
        '688585.SH',
        '605255.SH',
        '300476.SZ',
        '301232.SZ',
        '603226.SH',
        '600470.SH',
)
AND
        trade_date >= '20241001' AND 
        trade_date <= '20261231'
order by trade_date desc
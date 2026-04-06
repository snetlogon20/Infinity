select 
    ts_code as ts_code,
    trade_date as trade_date,
    close as close_point
from indexsysdb.df_tushare_stock_daily
where ts_code in 
(
            '002093.SZ',
            '600490.SH',
            '000902.SZ',
            '601368.SH', 
            '603839.SH'
)
AND
        trade_date >= '20241001' AND 
        trade_date <= '20261231'
order by trade_date desc
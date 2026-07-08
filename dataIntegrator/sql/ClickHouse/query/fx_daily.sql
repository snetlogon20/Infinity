select trade_date, bid_open, bid_close as close_point, bid_low, bid_high
from indexsysdb.df_tushare_fx_daily
where ts_code = 'USDJPY.FXCM'
order by trade_date desc

select trade_date, 
                     bid_open, 
                     bid_close as close_point, 
                     bid_low, 
                     bid_high
                from indexsysdb.df_tushare_fx_daily
                where ts_code = 'USDJPY.FXCM'
             and trade_date>= '2022-01-01' and trade_date<='2026-03-31'
             
             
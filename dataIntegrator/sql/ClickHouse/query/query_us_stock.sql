--美股名称
select *
from df_tushare_us_stock_basic

select SUBSTRING(ts_code, 1,1),count(1)
from df_tushare_us_stock_basic
group by SUBSTRING(ts_code, 1,1)

SELECT  * 
FROM  df_tushare_us_stock_basic
where ts_code = 'NVDA'


--美股日线
select date,count(*)
from indexsysdb.df_akshare_stock_us_daily
group by date 
order by date desc

--看具体天数下的信息
select *
from indexsysdb.df_akshare_stock_us_daily
order by date desc


select distinct(symbol)
from indexsysdb.df_akshare_stock_us_daily
where 1=1
	and date = '2026-07-23'
group by symbol


select *
from indexsysdb.df_akshare_stock_us_daily
where 1=1
	and symbol in ( 'SPY','TSLA', 'ADBE')
order by date desc


--美国股票， 由于每天只能刷新5个股票，已经放弃
SELECT DISTINCT trade_date as trade_date
FROM df_tushare_us_stock_daily
WHERE ts_code = 'SPY'
  AND trade_date >= '20240804'
  AND trade_date <= '20260725'
ORDER BY trade_date desc
            
            
SELECT  * 
FROM df_tushare_us_stock_daily
WHERE trade_date >= '20240804'
  AND trade_date <= '20260725'
ORDER BY trade_date desc



SELECT avg(y5)
FROM indexsysdb.df_tushare_us_treasury_yield_cruve
where trade_date>= '20220101' and trade_date<='20260329'
ORDER BY trade_date DESC

SELECT y5 as risk_free_rate
FROM indexsysdb.df_tushare_us_treasury_yield_cruve
WHERE trade_date <= '20260329'
ORDER BY trade_date DESC
LIMIT 1

SELECT *
FROM indexsysdb.df_tushare_us_treasury_yield_cruve
WHERE trade_date = '20260302'

--SHIBOR
select * from df_tushare_shibor_daily

--LRP
select *
from indexsysdb.df_tushare_shibor_lpr_daily
WHERE trade_date <= '20260329'
ORDER BY trade_date DESC
LIMIT 1


--国债收益曲线
select * from df_tushare_yc_cb
where trade_date = '20260508'

select curve_type,count(1) from df_tushare_yc_cb
where trade_date = '20260508'
group by curve_type

select trade_date, ts_code,	curve_name,	curve_type,	concat(ts_code, '_', curve_type) AS new_code,curve_term,	yield
from df_tushare_yc_cb
where trade_date = '20260508'


SELECT avg(y5)
FROM indexsysdb.df_tushare_us_treasury_yield_cruve
where trade_date>= '20220101' and trade_date<='20260329'
ORDER BY trade_date DESC

SELECT y5 as risk_free_rate
FROM indexsysdb.df_tushare_us_treasury_yield_cruve
WHERE trade_date <= '20260329'
ORDER BY trade_date DESC
LIMIT 1


select tenor_5y
from indexsysdb.df_tushare_shibor_lpr_daily
WHERE trade_date <= '20260329'
ORDER BY trade_date DESC
LIMIT 1


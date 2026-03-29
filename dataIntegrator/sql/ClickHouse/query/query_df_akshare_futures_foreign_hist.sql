select *
from 
(
	select
	   df_sys_calendar.trade_date AS df_sys_calendar__trade_date,
	    df_tushare_us_stock_daily.close_point AS df_tushare_us_stock_daily__close,
	    df_tushare_shibor_daily.tenor_on AS df_tushare_shibor_daily__tenor_on,
	    df_tushare_stock_daily.close AS df_tushare_stock_daily__close,
	    df_akshare_spot_hist_sge.close AS df_akshare_spot_hist_sge__close,
	    -- 新增的纽约金收盘价数据字段
	    df_akshare_futures_foreign_hist_GC.close AS df_akshare_futures_foreign_hist__GC_close,
	    -- 伦敦金收盘价数据字段
	    df_akshare_futures_foreign_hist_XAU.close AS df_akshare_futures_foreign_hist__XAU_close,
	    -- 美元指数数据字段
	    df_tushare_usd_index_daily.USDX_index AS df_tushare_usd_index_daily__USDX_index,
	    df_tushare_usd_index_daily.USDCNH_ask_close AS df_tushare_usd_index_daily__USDCNH_ask_close
	FROM df_sys_calendar
	LEFT JOIN df_tushare_us_stock_daily
	    ON df_sys_calendar.trade_date = df_tushare_us_stock_daily.trade_date
	    AND df_tushare_us_stock_daily.ts_code = 'C'
	LEFT JOIN df_tushare_shibor_daily
	    ON df_sys_calendar.trade_date = df_tushare_shibor_daily.trade_date
	LEFT JOIN df_tushare_stock_daily
	    ON df_sys_calendar.trade_date = df_tushare_stock_daily.trade_date
	    AND df_tushare_stock_daily.ts_code = '002093.SZ'
	LEFT JOIN df_akshare_spot_hist_sge
	    ON df_sys_calendar.trade_date = formatDateTime(toDate(df_akshare_spot_hist_sge.date), '%Y%m%d')
	-- 伦敦金收盘价数据连接
	LEFT JOIN (
	    SELECT
	        date,
	        open,
	        close,
	        low,
	        high,
	        volume
	    FROM indexsysdb.df_akshare_futures_foreign_hist
	    WHERE symbol = 'XAU'
	) AS df_akshare_futures_foreign_hist_XAU
	    ON df_sys_calendar.trade_date = formatDateTime(toDate(df_akshare_futures_foreign_hist_XAU.date), '%Y%m%d')
	-- 新增的纽约金收盘价数据连接
	LEFT JOIN (
	    SELECT
	        date,
	        open,
	        close,
	        low,
	        high,
	        volume
	    FROM indexsysdb.df_akshare_futures_foreign_hist
	    WHERE symbol = 'GC' AND close > 0
	) AS df_akshare_futures_foreign_hist_GC
	    ON df_sys_calendar.trade_date = formatDateTime(toDate(df_akshare_futures_foreign_hist_GC.date), '%Y%m%d')
	-- 新增的美元指数数据连接
	LEFT JOIN indexsysdb.df_tushare_usd_index_daily
	    ON df_sys_calendar.trade_date = df_tushare_usd_index_daily.trade_date
	WHERE
	    df_sys_calendar.trade_date BETWEEN '20241202' AND '20260328' and   
	    df_akshare_spot_hist_sge__close <> 0
	    AND df_akshare_spot_hist_sge.close <> 0
	    AND df_tushare_us_stock_daily.close_point <> 0
	    AND df_akshare_futures_foreign_hist_GC.close > 0    
	    -- 排除NaN值
	    AND NOT isNaN(df_akshare_spot_hist_sge.close)
	    AND NOT isNaN(df_tushare_us_stock_daily.close_point)
	    AND NOT isNaN(df_tushare_shibor_daily.tenor_on)
	    AND NOT isNaN(df_tushare_stock_daily.close)
	    AND NOT isNaN(df_akshare_futures_foreign_hist_GC.close)
	    AND NOT isNaN(df_akshare_futures_foreign_hist_XAU.close)
	    AND NOT isNaN(df_tushare_usd_index_daily.USDX_index)
	    AND NOT isNaN(df_tushare_usd_index_daily.USDCNH_ask_close)
	union all
	SELECT
	    '20260426' AS df_sys_calendar__trade_date,
	    112.41 AS df_tushare_us_stock_daily__close,
	    1.32 AS df_tushare_shibor_daily__tenor_on,
	    9.42 AS df_tushare_stock_daily__close,
	    991.36 AS df_akshare_spot_hist_sge__close,
	    4482.9 AS df_akshare_futures_foreign_hist__GC_close,
	    0.0 AS df_akshare_futures_foreign_hist__XAU_close,
	    99.88 AS df_tushare_usd_index_daily__USDX_index,
	    6.91947 AS df_tushare_usd_index_daily__USDCNH_ask_close
)
ORDER BY df_sys_calendar__trade_date

	SELECT
	    '20260426' AS df_sys_calendar__trade_date,
	    90.41 AS df_tushare_us_stock_daily__close,
	    1.32 AS df_tushare_shibor_daily__tenor_on,
	    9.42 AS df_tushare_stock_daily__close,
	    991.36 AS df_akshare_spot_hist_sge__close,
	    4000.9 AS df_akshare_futures_foreign_hist__GC_close,
	    4000.85 AS df_akshare_futures_foreign_hist__XAU_close,
	    99.88 AS df_tushare_usd_index_daily__USDX_index,
	    7.01947 AS df_tushare_usd_index_daily__USDCNH_ask_close
	    
	    
select * from indexsysdb.df_akshare_spot_hist_sge order by date desc

select * from  indexsysdb.df_akshare_futures_foreign_hist order by date desc




SELECT
    date,
    open,
    close,
    low,
    high,
    volume
FROM indexsysdb.df_akshare_futures_foreign_hist
WHERE symbol = 'GC' AND close > 0 order by date desc


SELECT
    date,
    open,
    close,
    low,
    high,
    volume
FROM indexsysdb.df_akshare_futures_foreign_hist
WHERE symbol = 'XAU' order by date desc


SELECT
    date,
    open,
    close,
    low,
    high,
    volume
FROM indexsysdb.df_akshare_futures_foreign_hist
WHERE symbol = 'CL' AND close > 0 order by date desc

SELECT
    date,
    open,
    close,
    low,
    high,
    volume
FROM indexsysdb.df_akshare_futures_foreign_hist
WHERE symbol = 'OIL' AND close > 0 order by date desc

SELECT
    date,
    open,
    close,
    low,
    high,
    volume
FROM indexsysdb.df_akshare_futures_foreign_hist
WHERE symbol = 'NG' AND close > 0 order by date desc
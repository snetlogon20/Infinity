SELECT * FROM  indexsysdb.df_tushare_opt_daily
ORDER BY trade_date DESC

select * from indexsysdb.df_tushare_opt_basic b
where ts_code like 'A2611%'

select * 
FROM indexsysdb.df_tushare_opt_daily d
LEFT JOIN indexsysdb.df_tushare_opt_basic b
ON d.ts_code = b.ts_code
WHERE 1=1
 AND d.trade_date = '20260717'
 AND d.ts_code like 'A2611-C-%.DCE'

 select * 
FROM indexsysdb.df_tushare_opt_basic b
LEFT JOIN indexsysdb.df_tushare_opt_daily d
ON d.ts_code = b.ts_code
WHERE 1=1
 AND d.trade_date = '20260717'
 AND d.ts_code like 'A2611-C-%.DCE'
 
SELECT
    -- 基础信息字段（合约描述）
	b.ts_code,
    b.name,
    b.opt_type,
    b.call_put,
    b.exercise_type,
    b.exercise_price,
    b.opt_multiplier,
    b.s_month,
    b.maturity_date,
    b.list_date,
    b.delist_date,
    b.per_unit,
    b.quote_unit,
    b.min_price_chg,
    -- 日线行情字段
    d.trade_date,
    d.ts_code,
    d.exchange,
    d.pre_settle,
    d.pre_close,
    d.open,
    d.high,
    d.low,
    d.close,
    d.settle,
    d.vol,
    d.amount,
    d.oi
FROM indexsysdb.df_tushare_opt_daily d
LEFT JOIN indexsysdb.df_tushare_opt_basic b
ON d.ts_code = b.ts_code
WHERE 1=1
 AND d.trade_date >= '20260701'
 AND d.trade_date <= '20260718'
 AND b.call_put = 'C'  -- C=看涨期权, P=看跌期权
ORDER BY d.trade_date, d.ts_code

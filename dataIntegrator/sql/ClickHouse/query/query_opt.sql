SELECT * FROM  indexsysdb.df_tushare_opt_daily
ORDER BY trade_date DESC

select * from indexsysdb.df_tushare_opt_basic b
where ts_code like 'A2611%'

create view vw_tushare_opt_daily
as
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
    d.trade_date,
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
 AND d.trade_date >= '20260101'
 AND d.trade_date <= '20260718'
 AND b.call_put = 'C'  -- C=看涨期权, P=看跌期权
 AND b.exercise_type = '欧式'
 AND b.ts_code like 'HO2612%'
ORDER BY d.trade_date desc, d.ts_code


CREATE OR REPLACE VIEW indexsysdb.vw_tushare_opt_daily AS
SELECT
    d.trade_date,
    -- 基础信息字段（合约描述）
    b.ts_code            AS opt_basic_ts_code,
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
    d.ts_code            AS opt_daily_ts_code,
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
WHERE d.trade_date >= '20260101'
  AND d.trade_date <= '20260718'
ORDER BY d.trade_date DESC, d.ts_code;


SELECT * FROM vw_tushare_opt_daily
where 1=1
	AND call_put = 'C'  -- C=看涨期权, P=看跌期权
	AND exercise_type = '欧式'
	AND opt_basic_ts_code like 'HO2612%'
ORDER BY trade_date desc, opt_basic_ts_code
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
LEFT JOIN indexsysdb.vw_tushare_opt_basic_of_today b
    ON d.ts_code = b.ts_code
ORDER BY d.trade_date DESC, d.ts_code;
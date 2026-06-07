
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
--WHERE trade_date <= '20260329'
ORDER BY trade_date DESC


--国债收益曲线
select * from df_tushare_yc_cb
where trade_date = '20260508'

select curve_type,count(1) from df_tushare_yc_cb
where trade_date = '20260508'
group by curve_type

select trade_date, ts_code,	curve_name,	curve_type,	concat(ts_code, '_', curve_type) AS new_code,curve_term,	yield
from df_tushare_yc_cb
where trade_date = '20260508'

--各项商业债券 - akshare 废除 
select * from df_akshare_bond_china_close_return

SELECT distinct(date)
FROM df_akshare_bond_china_close_return
order by date

SELECT date, concat(bond_type, '-', toString(tenor)), yield_to_maturity 
FROM df_akshare_bond_china_close_return

--可转债 信息
select * from indexsysdb.df_tushare_cb_basic

select * from indexsysdb.df_tushare_cb_basic
where ts_code = '110073.SH'

select issue_rating , newest_rating,rating_comp from indexsysdb.df_tushare_cb_basic
where ts_code = '110073.SH'

select issue_rating , newest_rating,rating_comp from indexsysdb.df_tushare_cb_basic
group by issue_rating , newest_rating,rating_comp


--可转债 日交易 
select * from indexsysdb.df_tushare_cb_daily
where  ts_code = '110073.SH'

select * from indexsysdb.df_tushare_cb_daily
order by ts_code desc

select ts_code,count(1) from indexsysdb.df_tushare_cb_daily
group by ts_code
order by count(1) desc

select count(*)
from (
select trade_date,count(1) from indexsysdb.df_tushare_cb_daily
group by trade_date
order by trade_date
)

select trade_date,count(1) from indexsysdb.df_tushare_cb_daily
group by trade_date
order by trade_date


select  * from indexsysdb.df_tushare_cb_daily
where ts_code = '110073.SH'
order by trade_date desc


select  * from indexsysdb.df_tushare_cb_daily
where trade_date = '20260525'

select  * from indexsysdb.df_tushare_cb_daily
where ts_code in
(
'110073.SH',
'110074.SH',
'110075.SH',
'110076.SH',
'110077.SH'
)
order by trade_date desc


--indexsysdb.df_tushare_cb_metrics
select * from indexsysdb.df_tushare_cb_metrics


select * from indexsysdb.df_tushare_cb_metrics
where ts_code = '110073.SH'
order by trade_date


select ts_code, trade_date,count(1)  from indexsysdb.df_tushare_cb_metrics
group by ts_code, trade_date


select min(trade_date), max(trade_date), count(1)  from indexsysdb.df_tushare_cb_metrics

--看下有多少天的数据已生成
select trade_date,count(1) from indexsysdb.df_tushare_cb_metrics
group by trade_date
order by trade_date

--查看哪个最赚钱
select * from indexsysdb.df_tushare_cb_metrics
where trade_date ='20260105'
order by current_yield desc, modified_duration, convexity desc, dv01 desc, pvbp desc 

-- 可转债全景视图: df_tushare_cb_daily LEFT JOIN df_tushare_cb_basic LEFT JOIN df_tushare_cb_metrics
SELECT
	d.trade_date,
    b.ts_code,
    b.bond_full_name,
    b.bond_short_name,
    b.cb_code,
    b.cb_type,
    b.stk_code,
    b.stk_short_name,
    b.maturity,
    b.par,
    b.issue_price,
    b.issue_size,
    b.remain_size,
    b.value_date,
    b.maturity_date,
    b.rate_type,
    b.coupon_rate,
    b.add_rate,
    b.pay_per_year,
    b.list_date,
    b.delist_date,
    b.exchange,
    b.conv_start_date,
    b.conv_end_date,
    b.conv_stop_date,
    b.first_conv_price,
    b.conv_price,
    b.rate_clause,
    b.put_clause,
    b.maturity_call_price,
    b.call_clause,
    b.reset_clause,
    b.conv_clause,
    b.guarantor,
    b.guarantee_type,
    b.issue_rating,
    b.newest_rating,
    b.rating_comp,
    d.ts_code AS daily_ts_code,
    d.trade_date,
    d.pre_close,
    d.open,
    d.high,
    d.low,
    d.close,
    d.change,
    d.pct_chg,
    d.vol,
    d.amount,
    d.bond_value,
    d.bond_over_rate,
    d.cb_value,
    d.cb_over_rate,
    m.ts_code AS metrics_ts_code,
    m.trade_date AS metrics_trade_date,
    m.is_feasible,
    m.description,
    m.ytm,
    m.macaulay_duration,
    m.modified_duration,
    m.convexity,
    m.dv01,
    m.pvbp,
    m.remaining_years,
    m.current_yield,
    m.simple_ytm,
    m.market_price,
    m.par AS metrics_par,
    m.coupon_rate AS metrics_coupon_rate,
    m.pay_per_year AS metrics_pay_per_year
FROM indexsysdb.df_tushare_cb_daily d
LEFT JOIN indexsysdb.df_tushare_cb_basic b
    ON d.ts_code = b.ts_code
LEFT JOIN indexsysdb.df_tushare_cb_metrics m
    ON d.ts_code = m.ts_code AND d.trade_date = m.trade_date
WHERE d.trade_date >= '20260301' AND
		 d.trade_date <= '20260525' 
ORDER BY d.trade_date, d.ts_code;


select * from indexsysdb.vw_tushare_cb_full
where  d.trade_date = '20260522'

SELECT b.ts_code, d.bond_value, b.bond_short_name, d.trade_date, b.maturity, m.current_yield,
    m.coupon_rate,
    m.ytm,
    m.macaulay_duration,
    m.modified_duration,
    m.effective_duration,
    m.convexity,
    m.effective_convexity,
    m.dv01,
    m.pvbp,
    m.remaining_years,
    m.current_yield,
    m.simple_ytm,
    m.market_price,
    m.var_price_hist_99,
    m.var_price_param_99,
    m.es_price_99,
    m.pct_price_chg_p50bp,
    m.pct_price_chg_m50bp
FROM indexsysdb.vw_tushare_cb_full
WHERE d.trade_date = '20260522' 
  and b.ts_code in ('127033.SZ', '113037.SH', '128129.SZ', '127025.SZ', '127018.SZ', '128135.SZ', '113042.SH', '123072.SZ', '128127.SZ', '113052.SH')
  AND m.current_yield <> 0


--ALTER TABLE indexsysdb.df_tushare_cb_metrics  DELETE WHERE trade_date >= '20260101' AND trade_date <= '20260531'
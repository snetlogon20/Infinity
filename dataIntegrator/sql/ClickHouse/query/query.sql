SELECT * FROM indexsysdb.df_tushare_stock_daily dthsd
--where ts_code = '600000.SH' and trade_date>= '20220101' and trade_date<='20220521'
where ts_code = '600000.SH' and trade_date= '20220520'

--ALTER TABLE indexsysdb.df_tushare_stock_daily D
--dELETE
--where ts_code = \\'600000.SH\\' and trade_date>= \\'20220101\\' and trade_date<=\\'20220521\\'']

'insert into indexsysdb.df_tushare_stock_daily (ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount) VALUES'

drop table indexsysdb.df_tushare_us_stock_basic;
CREATE TABLE indexsysdb.df_tushare_us_stock_basic(
ts_code        String,
name           Nullable(String),
enname         Nullable(String),
classify       Nullable(String),
list_date      Nullable(String),
delist_date    Nullable(String)
)
ENGINE=SummingMergeTree(ts_code)
order by (ts_code)
SETTINGS index_granularity = 8192

select * from indexsysdb.df_tushare_us_stock_basic


CREATE TABLE indexsysdb.df_sys_calendar (
    date String,
    year String,,
    month String,,
    day String,,
    day_of_week String,
    yyyymmdd String
) ENGINE = MergeTree()
ENGINE=SummingMergeTree(date )
order by (trade_date)
SETTINGS index_granularity = 8192


select cn_money_supply.m1  as ml
from indexsysdb.df_sys_calendar calendar
left join df_tushare_shibor_daily shibor_daily
	on calendar.trade_date  = shibor_daily.trade_date 
left join indexsysdb.cn_money_supply cn_money_supply
	on SUBSTRING(calendar.trade_date,1,6) = cn_money_supply.trade_date 
left join indexsysdb.df_tushare_cn_gdp cn_gdp
	on calendar.trade_year || 'Q' || calendar.quarter    = cn_gdp.quarter 
where CAST(calendar.trade_year AS BIGINT)  >= '2018'
order by calendar.trade_date


SELECT trade_date,m1 FROM indexsysdb.cn_money_supply where trade_date >= '20000101'
select m2 from indexsysdb.cn_money_supply
where trade_date = 
(SELECT max(trade_date) FROM indexsysdb.cn_money_supply)


//Stock analysis
SELECT * FROM df_tushare_us_stock_basic
WHERE enname like '%JP%'
--where ts_code LIKE '%JPM%'

/*************************************
* 美国个股 df_tushare_us_stock_daily 
**************************************/
select trade_date, pct_change from indexsysdb.df_tushare_us_stock_daily
where ts_code = 'C' AND trade_date >= '20220101' and trade_date <='20241013'

select trade_date, pct_change from indexsysdb.df_tushare_us_stock_daily
where ts_code = 'JPM' AND trade_date >= '20220101' and trade_date <='20241013'

select trade_date, pct_change from indexsysdb.df_tushare_us_stock_daily
where ts_code = 'AAPL' AND trade_date >= '20220101' and trade_date <='20241013'

select trade_date, pct_change from indexsysdb.df_tushare_us_stock_daily
where ts_code = 'NVDA' AND trade_date >= '20220101' and trade_date <='20241013'

select count(*) from indexsysdb.df_tushare_us_stock_daily
where ts_code = 'MSFT' AND trade_date >= '20220101' and trade_date <='20241013'

select distinct(ts_code) from indexsysdb.df_tushare_us_stock_daily
where trade_date >= '20220101' and trade_date <='20241013'

select count(*) from indexsysdb.df_tushare_us_stock_daily
where ts_code = 'BGRN' AND trade_date >= '20220101' and trade_date <='20241013'

--ALTER TABLE indexsysdb.df_tushare_us_stock_daily DELETE where trade_date>= '%s' and trade_date<='%s'"
--ALTER TABLE indexsysdb.df_tushare_us_stock_daily DELETE where ts_code = 'AAPL'

CREATE TABLE indexsysdb.df_tushare_us_stock_daily_20241027 AS indexsysdb.df_tushare_us_stock_daily
ENGINE = MergeTree()
SELECT * FROM indexsysdb.df_tushare_us_stock_daily 



/* 花旗 + JPM*/
select calendar.trade_date, 
us_stock_daily_portfolio.pct_change as portfolio_pct_change,
us_stock_daily_benchmark.pct_change  as benchmark_pct_change
from indexsysdb.df_sys_calendar calendar
left join (
	select trade_date, pct_change from indexsysdb.df_tushare_us_stock_daily
	where ts_code = 'C' AND trade_date >= '20220101' and trade_date <='20241013'
	) us_stock_daily_portfolio
	on calendar.trade_date  = us_stock_daily_portfolio.trade_date 
left join (
	select trade_date, pct_change from indexsysdb.df_tushare_us_stock_daily
	where ts_code = 'JPM' AND trade_date >= '20220101' and trade_date <='20241013'
	) us_stock_daily_benchmark
	on calendar.trade_date  = us_stock_daily_benchmark.trade_date 
where calendar.trade_date >= '20220101' 

select * from indexsysdb.df_tushare_us_stock_daily DELETE where ts_code = 'SNPMF'  order by trade_date desc
--ALTER TABLE indexsysdb.df_tushare_us_stock_daily DELETE where ts_code = 'SNPMF'
select ts_code,
    trade_date,
    close_point,
    open_point,
    high_point,
    low_point,
    pre_close,
    change_point,
    pct_change,
    vol,
    amount,
    vwap,
    turnover_ratio,
    total_mv,
    pe,
    pb
    from indexsysdb.df_tushare_us_stock_daily
    where ts_code = 'C' AND 
trade_date>= '20241001' and 
trade_date <='20241216' 
order by trade_date desc
                
/* 中国股票 */
select 
    ts_code,
    trade_date,
    open,
    high,
    low,
    close,
    pre_close,
    change,
    pct_chg,
    vol,
    amount
from indexsysdb.df_tushare_stock_daily
where ts_code = '002093.SZ' AND
        trade_date >= '20241001' AND 
        trade_date <= '20241231'
order by trade_date desc

/*************************************
* 供线性回归使用
**************************************/
select 
	calendar.trade_date,
	calendar.trade_year ,
	calendar.trade_month ,
	calendar.trade_day ,
	calendar.day_of_week,
	calendar.quarter,
	cn_money_supply.m0  as m0,
	cn_money_supply.m1  as ml,
	cn_money_supply.m2  as m2,
	cn_cpi.nt_yoy,
	fx_daily.bid_close ,
	df_tushare_us_treasury_yield_cruve.m1,
	df_tushare_us_treasury_yield_cruve.m2,
	df_tushare_us_treasury_yield_cruve.m3,
	df_tushare_us_treasury_yield_cruve.m6,
	df_tushare_us_treasury_yield_cruve.y1,
	df_tushare_us_treasury_yield_cruve.y2,
	df_tushare_us_treasury_yield_cruve.y3,
	df_tushare_us_treasury_yield_cruve.y5,
	df_tushare_us_treasury_yield_cruve.y7,
	df_tushare_us_treasury_yield_cruve.y1,
	df_tushare_us_treasury_yield_cruve.y2,
	df_tushare_us_treasury_yield_cruve.y30,
	us_stock_daily_portfolio_C.pct_change,
	us_stock_daily_portfolio_C.close_point,
	us_stock_daily_portfolio_JPM.pct_change
from indexsysdb.df_sys_calendar calendar
left join df_tushare_shibor_daily shibor_daily
	on calendar.trade_date  = shibor_daily.trade_date 
left join indexsysdb.cn_money_supply cn_money_supply
	on SUBSTRING(calendar.trade_date,1,6) = cn_money_supply.trade_date 
left join indexsysdb.df_tushare_cn_gdp cn_gdp
	on calendar.trade_year || 'Q' || calendar.quarter    = cn_gdp.quarter
left join indexsysdb.df_tushare_cn_cpi cn_cpi
	on SUBSTRING(calendar.trade_date,1,6)   = cn_cpi.trade_date 
left join indexsysdb.df_tushare_fx_daily fx_daily
	on calendar.trade_date = fx_daily.trade_date 
left join (
	select * from indexsysdb.df_tushare_us_treasury_yield_cruve
	) df_tushare_us_treasury_yield_cruve
	on calendar.trade_date  = df_tushare_us_treasury_yield_cruve.trade_date 
left join (
	select trade_date, pct_change,close_point from indexsysdb.df_tushare_us_stock_daily
	where ts_code = 'C'
	) us_stock_daily_portfolio_C
	on calendar.trade_date  = us_stock_daily_portfolio_C.trade_date 
left join (
	select trade_date, pct_change from indexsysdb.df_tushare_us_stock_daily
	where ts_code = 'JPM'
	) us_stock_daily_portfolio_JPM
	on calendar.trade_date  = us_stock_daily_portfolio_JPM.trade_date 
where CAST(calendar.trade_year AS BIGINT)  >= '2022'
order by calendar.trade_date
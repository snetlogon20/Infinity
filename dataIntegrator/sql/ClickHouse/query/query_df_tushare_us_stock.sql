/*************************************
* 股票基本信息 df_tushare_us_stock_basic 
**************************************/
SELECT * FROM df_tushare_us_stock_basic
WHERE enname like '%JP%'
--where ts_code LIKE '%JPM%'

/*************************************
* 美国个股 df_tushare_us_stock_daily 
**************************************/
select * from df_tushare_us_stock_daily
order by trade_date desc

select * from df_tushare_us_stock_daily
where ts_code = 'C' AND trade_date >= '20220101' and trade_date <='20241013'

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
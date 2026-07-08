--证券名称
select * from indexsysdb.df_tushare_stock_basic 

select count(1) from indexsysdb.df_tushare_stock_basic 

select industry,count(1) from indexsysdb.df_tushare_stock_basic 
group by industry


--自选股
select 
    ts_code as ts_code,
    trade_date as trade_date,
    close as close_point
from indexsysdb.df_tushare_stock_daily
where ts_code in 
(
        '688585.SH',
        '605255.SH',
        '300476.SZ',
        '301232.SZ',
        '603226.SH',
        '600470.SH',
)
AND
        trade_date >= '20241001' AND 
        trade_date <= '20261231'
order by trade_date desc

--股票财报 年报季报 - 业绩报表（含 ROE、毛利率、每股收益、每股经营现金流）
select * from df_akshare_stock_yjbb_em
order by eps desc

--AkShare-股票数据-财务指标  每股收益(元)  总资产净利润率(%)  成本费用利润率(%)  营业利润率(%)
select * from  df_akshare_stock_financial_analysis_indicator
where symbol = '000902'
order by date

select * from  df_akshare_stock_financial_analysis_indicator
where symbol = '688498'
order by date

select symbol,count(1) from  df_akshare_stock_financial_analysis_indicator
group by symbol

--根据altman 的算法计算Z-score
select * from df_akshare_stock_financial_analysis_indicator_matrics
order by symbol, date

select *
from indexsysdb.df_sys_calendar calendar
left join df_tushare_shibor_daily dtsd
on calendar.trade_date  = dtsd.trade_date
where dtsd.tenor_on <> 0

select *
from indexsysdb.df_sys_calendar calendar
left join df_tushare_shibor_daily shibor_daily
on calendar.trade_date  = shibor_daily.trade_date
left join indexsysdb.cn_money_supply cn_money_supply
on SUBSTRING(calendar.trade_date,1,6) = cn_money_supply.trade_date
where shibor_daily.tenor_on <> 0
order by calendar.trade_date

select *
from indexsysdb.df_sys_calendar calendar
left join df_tushare_shibor_daily shibor_daily
on calendar.trade_date  = shibor_daily.trade_date
left join indexsysdb.cn_money_supply cn_money_supply
on SUBSTRING(calendar.trade_date,1,6) = cn_money_supply.trade_date
left join indexsysdb.df_tushare_cn_gdp cn_gdp
on calendar.trade_year || 'Q' || calendar.quarter    = cn_gdp.quarter
where CAST(calendar.trade_year AS BIGINT)  >= '2018'
order by calendar.trade_date
CREATE  or replace VIEW indexsysdb.vw_tushare_opt_basic_of_today AS
select * from indexsysdb.df_tushare_opt_basic b
where trade_date in (select max(trade_date) from indexsysdb.df_tushare_opt_basic)

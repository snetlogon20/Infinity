-- ETF基金日线表（TuShare fund_daily 接口）
-- 用途: 为 ETF 期权提供标的行情（如华夏上证50ETF 510050.SH，50ETF期权标的），
--       供 OptionDailyIndicatorAnalyst 计算 spot_price / moneyness / IV / Greeks 使用
-- 数据来源: dataIntegrator.TuShareService.TuShareFundDailyService
--step 0 create table
--drop table indexsysdb.df_tushare_fund_daily;
--ALTER TABLE indexsysdb.df_tushare_fund_daily DELETE WHERE ts_code = '510050.SH';
CREATE TABLE indexsysdb.df_tushare_fund_daily(
ts_code     String          COMMENT '基金代码(如 510050.SH)',
trade_date  String          COMMENT '交易日期(YYYYMMDD)',
open        Float64         COMMENT '开盘价',
high        Float64         COMMENT '最高价',
low         Float64         COMMENT '最低价',
close       Float64         COMMENT '收盘价',
pre_close   Float64         COMMENT '昨收盘价',
change      Float64         COMMENT '涨跌(元)',
pct_chg     Float64         COMMENT '涨跌幅(%)',
volume      Float64         COMMENT '成交量(手, TuShare fund_daily 接口列名为 vol, 服务层已映射)',
amount      Float64         COMMENT '成交金额(千元)'
)
ENGINE=MergeTree()
order by (ts_code,trade_date)
SETTINGS index_granularity = 8192

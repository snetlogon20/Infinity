-- 期权日线指标分析表（含盘面指标、时间指标、价态、隐含波动率、Greeks）
-- 数据来源：df_tushare_opt_daily + df_tushare_opt_basic
-- 支持多日增量写入：按 trade_date 增量删除后插入，可追溯历史波动
--drop table indexsysdb.tb_tushare_opt_daily_indicator
--ALTER TABLE indexsysdb.tb_tushare_opt_daily_indicator DELETE WHERE 1=1;
--ALTER TABLE indexsysdb.tb_tushare_opt_daily_indicator DELETE WHERE trade_date = '20251224';

-- 增量 DDL: 已有表新增 dividend_yield 列
--ALTER TABLE indexsysdb.tb_tushare_opt_daily_indicator ADD COLUMN dividend_yield Float64 COMMENT '股息率(q): BSM模型使用的年化股息率(小数), 从PE_TTM估算 q=payout_ratio/pe_ttm';

-- 增量 DDL: 已有表新增 d1/d2/N(d1)/N(d2) 列
--ALTER TABLE indexsysdb.tb_tushare_opt_daily_indicator ADD COLUMN d1 Float64 COMMENT 'BS模型d1参数: (ln(S/K)+(r+0.5*sigma^2)*T)/(sigma*sqrt(T))';
--ALTER TABLE indexsysdb.tb_tushare_opt_daily_indicator ADD COLUMN d2 Float64 COMMENT 'BS模型d2参数: d1-sigma*sqrt(T)';
--ALTER TABLE indexsysdb.tb_tushare_opt_daily_indicator ADD COLUMN nd1 Float64 COMMENT 'BS模型N(d1): 标准正态累积分布值';
--ALTER TABLE indexsysdb.tb_tushare_opt_daily_indicator ADD COLUMN nd2 Float64 COMMENT 'BS模型N(d2): 标准正态累积分布值';
CREATE TABLE indexsysdb.tb_tushare_opt_daily_indicator (
    trade_date String COMMENT '交易日期(YYYYMMDD)',
    ts_code String COMMENT 'TS合约代码(来自opt_daily)',
    call_put String COMMENT '期权类型(C=认购/P=认沽)',
    exercise_price Float64 COMMENT '行权价',
    opt_multiplier Float64 COMMENT '合约单位(乘数)',
    s_month String COMMENT '结算月(YYYYMM)',
    maturity_date String COMMENT '到期日(YYYYMMDD)',
    pre_close Float64 COMMENT '前收盘价',
    close Float64 COMMENT '收盘价(期权)',
    pre_settle Float64 COMMENT '昨结算价',
    settle Float64 COMMENT '结算价',
    open Float64 COMMENT '开盘价',
    high Float64 COMMENT '最高价',
    low Float64 COMMENT '最低价',
    vol Float64 COMMENT '成交量(手)',
    amount Float64 COMMENT '成交金额(万元)',
    oi Float64 COMMENT '持仓量(手)',
    mtm_pnl_close Float64 COMMENT '日内浮动盈亏(按close): (close-pre_close)*opt_multiplier',
    mtm_pnl_settle Float64 COMMENT '结算盯市盈亏(按settle): (settle-pre_settle)*opt_multiplier',
    point_change Float64 COMMENT '日内涨跌(指数点): close-pre_close',
    pct_change Float64 COMMENT '日内涨跌幅(%): (close/pre_close-1)*100',
    turnover_ratio Float64 COMMENT '换手率(近似): vol/oi',
    avg_unit_price Float64 COMMENT '平均每手成交价(元): amount*10000/vol',
    days_to_maturity Int32 COMMENT '距离到期日历天数',
    years_to_maturity_calendar Float64 COMMENT '距离到期年数(日历日/365)',
    years_to_maturity_trading Float64 COMMENT '距离到期年数(交易日/252)',
    moneyness_status String COMMENT '价态标志: ITM(实值)/ATM(平值)/OTM(虚值)',
    moneyness_log Float64 COMMENT '对数价态(连续复利): ln(K/S)/sqrt(T)',
    spot_price Float64 COMMENT '标的资产当日收盘价',
    risk_free_rate Float64 COMMENT '无风险利率(用于IV计算)',
    dividend_yield Float64 COMMENT '股息率(q): BSM模型使用的年化股息率(小数), 从PE_TTM估算 q=payout_ratio/pe_ttm',
    implied_vol Float64 COMMENT '隐含波动率(BS模型,小数)',
    bs_theoretical_price Float64 COMMENT 'BS理论价(使用implied_vol回算)',
    delta Float64 COMMENT 'Delta: 标的价格变动1单位对期权价格影响',
    gamma Float64 COMMENT 'Gamma: Delta对S的敏感度',
    vega Float64 COMMENT 'Vega: IV变动1%的权利金变化',
    theta Float64 COMMENT 'Theta: 每日时间衰减(元/天)',
    rho Float64 COMMENT 'Rho: 利率敏感度',
    d1 Float64 COMMENT 'BS模型d1参数: (ln(S/K)+(r+0.5*sigma^2)*T)/(sigma*sqrt(T))',
    d2 Float64 COMMENT 'BS模型d2参数: d1-sigma*sqrt(T)',
    nd1 Float64 COMMENT 'BS模型N(d1): 标准正态累积分布值',
    nd2 Float64 COMMENT 'BS模型N(d2): 标准正态累积分布值'
)
ENGINE = MergeTree()
ORDER BY (trade_date, ts_code)
SETTINGS index_granularity = 8192;

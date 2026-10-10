-- 期权组合 Greeks 聚合与对冲建议表 (Portfolio Greeks Aggregation + Delta Hedging + P&L Explain)
-- 专业定位: 持仓组合希腊字母聚合 + 动态Delta对冲建议 + 损益归因分解
--   每行一个分组汇总: group_type=TOTAL(全组合)/UNDERLYING(按标的)/MATURITY(按到期月)
-- 对冲: 净Delta用现货/ETF/股指期货对冲, 输出对冲单位数与名义金额;
--   Gamma/Vega 剩余敞口与期限分布提示(哪个月到期集中爆发)
-- P&L Explain(最近两个交易日, 用T-1日Greeks解释T日损益):
--   pnl_delta/gamma/vega/theta 四项归因 + residual(高阶项/交叉项/模型误差)
--   coverage = 1-|residual/pnl_observed|(接近1=Greeks线性化解释力好, 残差大=数据失真需排查)
-- 数据来源: tb_tushare_opt_daily_indicator (最新两日Greeks/行情) + df_tushare_opt_basic
-- 持仓输入: config.positions = [{ts_code, direction(+1买/-1卖), quantity}] 或
--           auto ATM straddle 由聚合器自动构建
-- 增量写入: 按 trade_date + strategy_type 删除后插入
-- 审计: analysis_time/analysis_params/analysis_version

--drop table indexsysdb.tb_option_portfolio_greeks;
--ALTER TABLE indexsysdb.tb_option_portfolio_greeks DELETE WHERE 1=1;

CREATE TABLE indexsysdb.tb_option_portfolio_greeks (
    -- 策略标识与审计
    strategy_type String COMMENT '策略类型: PORTFOLIO_GREEKS(组合Greeks聚合)',
    analysis_time DateTime COMMENT '本轮分析生成时间戳',
    analysis_params String COMMENT '本轮分析参数(JSON, 含持仓明细)',
    analysis_version String COMMENT '算法版本号',
    -- 分组维度
    trade_date String COMMENT '交易日(最新持仓Greeks口径日, YYYYMMDD)',
    trade_date_prev String COMMENT 'P&L Explain 的前一交易日(T-1)',
    group_type String COMMENT '分组: TOTAL(全组合)/UNDERLYING(按标的)/MATURITY(按到期月)',
    group_key String COMMENT '分组键: TOTAL/underlying_key/s_month',
    -- 持仓结构
    n_positions UInt32 COMMENT '组内持仓(合约x方向)数量',
    sum_long_qty Float64 COMMENT '买入腿总张数',
    sum_short_qty Float64 COMMENT '卖出腿总张数',
    -- 净 Greeks(持仓口径: 买+卖-, 已乘 张数x方向x合约乘数)
    net_delta Float64 COMMENT '净Delta(标的单位): 对冲与方向敞口的核心',
    net_gamma Float64 COMMENT '净Gamma(标的单位^-1): delta对冲后的二阶残留风险',
    net_vega Float64 COMMENT '净Vega(元/1%IV): 波动率敞口',
    net_theta Float64 COMMENT '净Theta(元/天): 时间价值净收入(正)/净损耗(负)',
    net_rho Float64 COMMENT '净Rho: 利率敞口',
    -- 对冲建议(UNDERLYING行有意义; TOTAL行汇总名义金额)
    delta_hedge_units Float64 COMMENT '对冲单位数 = -net_delta(现货/ETF份额; 期货为手数见hedge_contracts)',
    delta_hedge_notional_cny Float64 COMMENT '对冲名义金额(元) = |net_delta|*spot',
    hedge_instrument String COMMENT '对冲工具: SPOT(现货/融券)/ETF_LOT(100份/手)/FUTURE(股指期货)',
    hedge_contracts Float64 COMMENT '对冲手数(ETF_LOT=units/100; FUTURE=notional/(乘数*spot))',
    -- 收入结构
    theta_carry_cny Float64 COMMENT '每日时间价值净收入(元/天, 卖方组合为正)',
    net_delta_notional_cny Float64 COMMENT '净Delta名义敞口(元) = net_delta*spot',
    -- P&L Explain(T-1 -> T, T-1日Greeks口径)
    pnl_observed_cny Float64 COMMENT '实际盯市损益(元): sum(方向*张数*乘数*(close_T-close_T-1))',
    pnl_delta_cny Float64 COMMENT 'Delta归因(元) = sum(delta_T-1 * dS)',
    pnl_gamma_cny Float64 COMMENT 'Gamma归因(元) = sum(0.5*gamma_T-1 * dS^2)',
    pnl_vega_cny Float64 COMMENT 'Vega归因(元) = sum(vega_T-1 * dIV*100)',
    pnl_theta_cny Float64 COMMENT 'Theta归因(元) = sum(theta_T-1 * dt日历天)',
    pnl_residual_cny Float64 COMMENT '残差(元) = 实际 - 四项归因(高阶/交叉/数据误差)',
    pnl_explain_coverage Float64 COMMENT '解释覆盖率 = 1-|residual/observed|(接近1=Greeks模型解释力好)'
)
ENGINE = MergeTree()
ORDER BY (strategy_type, trade_date, group_type, group_key)
SETTINGS index_granularity = 8192;

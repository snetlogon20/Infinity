-- Synthetic Long Stock(合成多头)策略分析结果表
-- 策略定义: 买Call(K,T)+卖Put(K,T), 净支出C-P, 复制现货多头(净Delta≈+1)
-- 到期损益 = S_T-K-(C-P), 盈亏平衡点 = K+(C-P), 上行不封顶; 下行非有限亏损(卖Put保证金追缴)
-- 理论定价(平价关系): C-P = S·e^(-qT)-K·e^(-rT) → 反推隐含融资利率r_impl
-- 每行一个组合(非单合约): Call腿字段不带后缀, Put腿字段带 _put 后缀
-- 组合生成: 行权价限定ATM±5档(合成对K不敏感, 只改变融资结构, 流动性决定选档)
-- 数据来源: tb_tushare_opt_daily_indicator (BS定价/Greeks) + df_tushare_opt_basic (合约名称)
-- 增量写入: 按 trade_date + symbol_filter 删除后插入(call_put 存 'CP' 不参与删除条件)
-- 审计: analysis_time/analysis_params/analysis_version 记录每轮分析的时间戳与参数

--drop table indexsysdb.tb_option_trading_strategy_synthetic_long_stock;
--ALTER TABLE indexsysdb.tb_option_trading_strategy_synthetic_long_stock DELETE WHERE 1=1;

CREATE TABLE indexsysdb.tb_option_trading_strategy_synthetic_long_stock (
    -- 策略标识与审计
    strategy_type String COMMENT '策略类型: SYNTHETIC_LONG_STOCK(合成多头: 买C卖P)',
    analysis_time DateTime COMMENT '本轮分析生成时间戳',
    analysis_params String COMMENT '本轮分析参数(JSON): symbol_filter/start_date/end_date等',
    analysis_version String COMMENT '算法版本号, 便于报表端区分口径',
    -- 组合标识(Call腿为基准, Put腿带 _put)
    trade_date String COMMENT '交易日期(YYYYMMDD)',
    ts_code String COMMENT 'Call腿TS合约代码',
    symbol String COMMENT 'Call腿合约代码(来自opt_basic)',
    opt_name String COMMENT 'Call腿合约名称',
    opt_exchange String COMMENT '交易所(如SSE)',
    call_put String COMMENT '期权类型(CP=合成双腿)',
    ts_code_put String COMMENT 'Put腿TS合约代码',
    symbol_put String COMMENT 'Put腿合约代码',
    opt_name_put String COMMENT 'Put腿合约名称',
    -- 合约要素(同到期月同行权价, 取Call腿)
    exercise_price Float64 COMMENT '双腿共同行权价 K',
    opt_multiplier Float64 COMMENT '合约单位(乘数)',
    s_month String COMMENT '结算月(YYYYMM)',
    maturity_date String COMMENT '到期日(YYYYMMDD)',
    days_to_maturity Int32 COMMENT '距离到期日历天数',
    -- 标的市场
    spot_price Float64 COMMENT '标的资产当日收盘价S0',
    moneyness_status String COMMENT 'Call腿价态: ITM/ATM/OTM',
    risk_free_rate Float64 COMMENT '无风险利率r',
    dividend_yield Float64 COMMENT '股息率q',
    -- 双腿行情与定价
    premium Float64 COMMENT 'Call腿权利金C(收盘价close)',
    premium_put Float64 COMMENT 'Put腿权利金P(收盘价close)',
    implied_vol Float64 COMMENT 'Call腿隐含波动率',
    implied_vol_put Float64 COMMENT 'Put腿隐含波动率',
    iv_rank Float64 COMMENT 'Call腿IV分位数(0~1, 近60日)',
    iv_rank_put Float64 COMMENT 'Put腿IV分位数(0~1, 近60日)',
    -- 双腿 Greeks(原始腿口径: 买方Greeks)
    delta Float64 COMMENT 'Call腿Delta(正值)',
    gamma Float64 COMMENT 'Call腿Gamma',
    theta Float64 COMMENT 'Call腿Theta(买方为负)',
    vega Float64 COMMENT 'Call腿Vega',
    delta_put Float64 COMMENT 'Put腿Delta(负值)',
    gamma_put Float64 COMMENT 'Put腿Gamma',
    theta_put Float64 COMMENT 'Put腿Theta(买方为负)',
    vega_put Float64 COMMENT 'Put腿Vega',
    -- 双腿定价偏差
    bs_theoretical_price Float64 COMMENT 'Call腿BS理论价',
    close_vs_theoretical Float64 COMMENT 'Call腿市价-理论价(负值=买入便宜)',
    close_vs_theoretical_pct Float64 COMMENT 'Call腿市价偏离(%)',
    price_bias String COMMENT 'Call腿定价偏差: 严重低估/低估/公允/高估/严重高估',
    bs_theoretical_price_put Float64 COMMENT 'Put腿BS理论价',
    close_vs_theoretical_put Float64 COMMENT 'Put腿市价-理论价(负值=买入便宜)',
    close_vs_theoretical_pct_put Float64 COMMENT 'Put腿市价偏离(%)',
    price_bias_put String COMMENT 'Put腿定价偏差',
    -- 合成结构核心
    synthetic_net_cost Float64 COMMENT '合成净成本C-P(多头为净支出, 可为负=净收入)',
    synthetic_net_cost_cny Float64 COMMENT '合成净成本(元/组): (C-P)*乘数',
    synthetic_net_cost_pct_of_spot Float64 COMMENT '净成本占现价(%): (C-P)/S0*100',
    synthetic_theoretical Float64 COMMENT '理论合成成本 = S·e^(-qT)-K·e^(-rT)(平价关系)',
    synth_deviation Float64 COMMENT '合成偏离 = (C-P)-理论(正=合成贵/隐含融资利率高)',
    synth_deviation_pct Float64 COMMENT '合成偏离占现价(%): deviation/S0*100(评分核心)',
    -- 隐含资金利率
    implied_financing_rate Float64 COMMENT '隐含融资利率r_impl = -ln((S·e^(-qT)-(C-P))/K)/T年(市场资金价格)',
    financing_spread_bp Float64 COMMENT '融资利差(bp) = (r_impl-r)*1e4(多头视角越负合成越便宜)',
    -- 净 Greeks(持仓口径: 买腿+, 卖腿取反) 与 Delta 校验
    net_delta Float64 COMMENT '组合净Delta(合成多头应≈+1, 买C的Delta减卖P的Delta贡献)',
    delta_check_passed Float64 COMMENT 'Delta校验: |net_delta-1|<=0.15为1(净超阈判为脏配对一票否决)',
    net_gamma Float64 COMMENT '组合净Gamma(买C卖P基本对冲, 近似为小负值)',
    net_theta Float64 COMMENT '组合净Theta(买C损耗-卖P收入, 时间价值近似自平衡)',
    net_vega Float64 COMMENT '组合净Vega(双腿IV同涨同跌基本抵消, 合成成本对波动率不敏感)',
    -- 资金效率(卖出腿保证金粗估)
    margin_est Float64 COMMENT '卖出Put腿保证金粗估(每单位): P+max(12%*S-虚值, 7%*S)(交易所公式近似)',
    capital_occupied_cny Float64 COMMENT '资金占用(元/组): (保证金+买入Call权利金)*乘数',
    margin_vs_spot_capital Float64 COMMENT '资金效率 = 资金占用/现货全额(越低杠杆越高, <0.3为高效率)',
    -- 收益结构
    breakeven Float64 COMMENT '盈亏平衡点 = K+(C-P)(多头: S_T高于此点盈利)',
    breakeven_pct Float64 COMMENT '平衡点距现价(%): (breakeven-S0)/S0*100',
    -- 评分
    score Float64 COMMENT '综合评分 = -合成偏离%(多头: 合成越便宜分越高, 同日排名依据)',
    combo_rank UInt32 COMMENT '同日内组合评分排名(1=最优)',
    -- 多情景盈亏: S_T=S0*factor, 组合P&L=(S_T-K-(C-P)); 现货对照P&L=S_T-S0
    scenario_pnl_0_85S Float64 COMMENT '情景盈亏(S_T=0.85*S0)',
    scenario_pnl_0_85S_cny Float64 COMMENT '情景盈亏元/组(S_T=0.85*S0)',
    scenario_pnl_0_85S_pct Float64 COMMENT '情景收益率(S_T=0.85*S0): pnl/资金占用*100(以资金占用为本金)',
    unhedged_pnl_0_85S Float64 COMMENT '买现货对照(S_T=0.85*S0): S_T-S0',
    unhedged_pnl_0_85S_pct Float64 COMMENT '买现货对照%(S_T=0.85*S0)',
    scenario_pnl_0_90S Float64 COMMENT '情景盈亏(S_T=0.90*S0)',
    scenario_pnl_0_90S_cny Float64 COMMENT '情景盈亏元/组(S_T=0.90*S0)',
    scenario_pnl_0_90S_pct Float64 COMMENT '情景收益率(S_T=0.90*S0)',
    unhedged_pnl_0_90S Float64 COMMENT '买现货对照(S_T=0.90*S0)',
    unhedged_pnl_0_90S_pct Float64 COMMENT '买现货对照%(S_T=0.90*S0)',
    scenario_pnl_0_95S Float64 COMMENT '情景盈亏(S_T=0.95*S0)',
    scenario_pnl_0_95S_cny Float64 COMMENT '情景盈亏元/组(S_T=0.95*S0)',
    scenario_pnl_0_95S_pct Float64 COMMENT '情景收益率(S_T=0.95*S0)',
    unhedged_pnl_0_95S Float64 COMMENT '买现货对照(S_T=0.95*S0)',
    unhedged_pnl_0_95S_pct Float64 COMMENT '买现货对照%(S_T=0.95*S0)',
    scenario_pnl_1_00S Float64 COMMENT '情景盈亏(S_T=S0)',
    scenario_pnl_1_00S_cny Float64 COMMENT '情景盈亏元/组(S_T=S0)',
    scenario_pnl_1_00S_pct Float64 COMMENT '情景收益率(S_T=S0)',
    unhedged_pnl_1_00S Float64 COMMENT '买现货对照(S_T=S0)',
    unhedged_pnl_1_00S_pct Float64 COMMENT '买现货对照%(S_T=S0)',
    scenario_pnl_1_05S Float64 COMMENT '情景盈亏(S_T=1.05*S0)',
    scenario_pnl_1_05S_cny Float64 COMMENT '情景盈亏元/组(S_T=1.05*S0)',
    scenario_pnl_1_05S_pct Float64 COMMENT '情景收益率(S_T=1.05*S0)',
    unhedged_pnl_1_05S Float64 COMMENT '买现货对照(S_T=1.05*S0)',
    unhedged_pnl_1_05S_pct Float64 COMMENT '买现货对照%(S_T=1.05*S0)',
    scenario_pnl_1_10S Float64 COMMENT '情景盈亏(S_T=1.10*S0)',
    scenario_pnl_1_10S_cny Float64 COMMENT '情景盈亏元/组(S_T=1.10*S0)',
    scenario_pnl_1_10S_pct Float64 COMMENT '情景收益率(S_T=1.10*S0)',
    unhedged_pnl_1_10S Float64 COMMENT '买现货对照(S_T=1.10*S0)',
    unhedged_pnl_1_10S_pct Float64 COMMENT '买现货对照%(S_T=1.10*S0)',
    scenario_pnl_1_15S Float64 COMMENT '情景盈亏(S_T=1.15*S0)',
    scenario_pnl_1_15S_cny Float64 COMMENT '情景盈亏元/组(S_T=1.15*S0)',
    scenario_pnl_1_15S_pct Float64 COMMENT '情景收益率(S_T=1.15*S0)',
    unhedged_pnl_1_15S Float64 COMMENT '买现货对照(S_T=1.15*S0)',
    unhedged_pnl_1_15S_pct Float64 COMMENT '买现货对照%(S_T=1.15*S0)',
    -- 交易信号
    trade_signal String COMMENT '交易信号: STRONG_BUY/BUY/CONSIDER/NEUTRAL/AVOID(指是否用合成替代买现货)',
    signal_reason String COMMENT '信号原因说明'
)
ENGINE = MergeTree()
ORDER BY (strategy_type, trade_date, exercise_price)
SETTINGS index_granularity = 8192;

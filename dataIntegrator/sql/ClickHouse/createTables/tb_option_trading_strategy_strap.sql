-- Strap（带式组合）策略分析结果表
-- 策略定义: 买入同一行权价 K 的 2 份认购 Call + 1 份认沽 Put, 同到期月
-- 净支出 T = 2C + P(三腿权利金合计, 也是最大亏损, S_T=K 时谷底)
-- 到期组合收益 = 2*max(0,S_T-K) + max(0,K-S_T) - T(不对称 V 形, 上行斜率加倍)
-- 盈利无上限(双向), 盈亏平衡点: 上=K+T/2(2份Call涨半程即回本), 下=K-T(1份Put需跌过全成本)
-- 每行一个组合(非单合约): Call腿字段不带后缀, Put腿字段带 _put 后缀
-- premium/premium_put 为单份收盘价, 2:1 腿权重在 total_premium/net_* 等聚合字段体现
-- 组合生成: 行权价限定 ATM±2 档(约束剪枝控制组合爆炸), 且同档同时存在 Call 与 Put
-- 数据来源: tb_tushare_opt_daily_indicator (BS定价/Greeks) + df_tushare_opt_basic (合约名称)
-- 增量写入: 按 trade_date + symbol_filter 删除后插入(call_put 存 'CP' 不参与删除条件)
-- 审计: analysis_time/analysis_params/analysis_version 记录每轮分析的时间戳与参数

--drop table indexsysdb.tb_option_trading_strategy_strap;
--ALTER TABLE indexsysdb.tb_option_trading_strategy_strap DELETE WHERE 1=1;

CREATE TABLE indexsysdb.tb_option_trading_strategy_strap (
    -- 策略标识与审计
    strategy_type String COMMENT '策略类型: STRAP(带式组合, 2份Call+1份Put, 看波动且偏多)',
    analysis_time DateTime COMMENT '本轮分析生成时间戳',
    analysis_params String COMMENT '本轮分析参数(JSON): symbol_filter/start_date/end_date等',
    analysis_version String COMMENT '算法版本号, 便于报表端区分口径',
    -- 组合标识(Call腿为基准, Put腿带 _put)
    trade_date String COMMENT '交易日期(YYYYMMDD)',
    ts_code String COMMENT 'Call腿TS合约代码',
    symbol String COMMENT 'Call腿合约代码(来自opt_basic)',
    opt_name String COMMENT 'Call腿合约名称',
    opt_exchange String COMMENT '交易所(如SSE)',
    call_put String COMMENT '期权类型(CP=带式双腿2C+1P)',
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
    risk_free_rate Float64 COMMENT '无风险利率',
    dividend_yield Float64 COMMENT '股息率q',
    -- 双腿行情与定价(单份价格, 组合权重2:1)
    premium Float64 COMMENT 'Call腿单份权利金 C(收盘价close)',
    premium_put Float64 COMMENT 'Put腿单份权利金 P(收盘价close)',
    implied_vol Float64 COMMENT 'Call腿隐含波动率',
    implied_vol_put Float64 COMMENT 'Put腿隐含波动率',
    iv_rank Float64 COMMENT 'Call腿IV分位数(0~1, 近60日)',
    iv_rank_put Float64 COMMENT 'Put腿IV分位数(0~1, 近60日)',
    -- 双腿 Greeks(单份, 净敞口按2:1加权)
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
    -- 组合净 Greeks(2C+1P加权: 净Delta为正=偏多敞口, 三腿theta/vega叠加)
    net_delta Float64 COMMENT '组合净Delta = 2*delta_call+delta_put(ATM附近约+0.5, 偏多波动率的量化表达)',
    net_gamma Float64 COMMENT '组合净Gamma(三份叠加为正, 临近到期损益对现货极敏感)',
    net_theta Float64 COMMENT '组合净Theta(三腿同为负, 时间损耗重于跨式双腿)',
    net_vega Float64 COMMENT '组合净Vega(三份叠加为正, IV回升双向受益)',
    -- 带式结构(花了多少)
    total_premium Float64 COMMENT '总成本 T = 2C+P(三腿合计, 也是最大亏损)',
    total_premium_cny Float64 COMMENT '总成本(元/组): T*乘数',
    total_premium_pct_of_spot Float64 COMMENT '总成本占现价(%): T/S0*100, 越低买得越便宜',
    expected_move_1sigma_pct Float64 COMMENT '1σ预期波动(%): σ√T年*100(σ为2:1加权IV, 模型隐含到期波动半径)',
    -- 收益结构(亏损封底T, 盈利无上限, 上行斜率加倍的不对称V形)
    max_loss Float64 COMMENT '组合最大亏损(每单位): T=S_T=K时锁定(谷底)',
    max_loss_cny Float64 COMMENT '组合最大亏损(元/组)',
    max_loss_pct_of_spot Float64 COMMENT '最大亏损占现价(%): T/S0*100',
    breakeven_up Float64 COMMENT '上盈亏平衡点 = K + T/2(2份Call涨半程即回本, 上行结构优势)',
    breakeven_up_pct Float64 COMMENT '上平衡所需涨幅(%): (K+T/2-S0)/S0*100',
    breakeven_down Float64 COMMENT '下盈亏平衡点 = K - T(1份Put需跌过全成本)',
    breakeven_down_pct Float64 COMMENT '下平衡所需跌幅(%): (K-T-S0)/S0*100',
    breakeven_range_pct Float64 COMMENT '盈亏平衡区间宽度(%): 1.5T/S0*100(比同成本跨式2T/S0更窄)',
    -- 概率与评分(最佳组合排序)
    win_prob Float64 COMMENT '胜率(近似): P(S_T>K+T/2)+P(S_T<K-T), 对数正态+2:1加权IV(上行门槛减半是结构优势)',
    expected_value Float64 COMMENT '期望值(每单位): 2*(BS_C-C)+(BS_P-P), 市价比理论便宜的幅度(Call权重加倍)',
    score Float64 COMMENT '综合评分 = 期望值/总成本(风险调整后收益, 同日排名依据)',
    combo_rank UInt32 COMMENT '同日内组合评分排名(1=最优)',
    -- 多情景盈亏: S_T=S0*factor, 组合P&L=2*max(0,S_T-K)+max(0,K-S_T)-T(上行双倍杠杆)
    scenario_pnl_0_85S Float64 COMMENT '情景盈亏(S_T=0.85*S0, 1份Put单倍盈利)',
    scenario_pnl_0_85S_cny Float64 COMMENT '情景盈亏元/组(S_T=0.85*S0)',
    scenario_pnl_0_85S_pct Float64 COMMENT '情景收益率(S_T=0.85*S0): pnl/T*100(以总成本为本金)',
    unhedged_pnl_0_85S Float64 COMMENT '买现货对照(S_T=0.85*S0): S_T-S0',
    unhedged_pnl_0_85S_pct Float64 COMMENT '买现货对照%(S_T=0.85*S0)',
    scenario_pnl_0_90S Float64 COMMENT '情景盈亏(S_T=0.90*S0, 1份Put单倍盈利)',
    scenario_pnl_0_90S_cny Float64 COMMENT '情景盈亏元/组(S_T=0.90*S0)',
    scenario_pnl_0_90S_pct Float64 COMMENT '情景收益率(S_T=0.90*S0)',
    unhedged_pnl_0_90S Float64 COMMENT '买现货对照(S_T=0.90*S0)',
    unhedged_pnl_0_90S_pct Float64 COMMENT '买现货对照%(S_T=0.90*S0)',
    scenario_pnl_0_95S Float64 COMMENT '情景盈亏(S_T=0.95*S0, 1份Put单倍盈利)',
    scenario_pnl_0_95S_cny Float64 COMMENT '情景盈亏元/组(S_T=0.95*S0)',
    scenario_pnl_0_95S_pct Float64 COMMENT '情景收益率(S_T=0.95*S0)',
    unhedged_pnl_0_95S Float64 COMMENT '买现货对照(S_T=0.95*S0)',
    unhedged_pnl_0_95S_pct Float64 COMMENT '买现货对照%(S_T=0.95*S0)',
    scenario_pnl_1_00S Float64 COMMENT '情景盈亏(S_T=S0)',
    scenario_pnl_1_00S_cny Float64 COMMENT '情景盈亏元/组(S_T=S0)',
    scenario_pnl_1_00S_pct Float64 COMMENT '情景收益率(S_T=S0)',
    unhedged_pnl_1_00S Float64 COMMENT '买现货对照(S_T=S0)',
    unhedged_pnl_1_00S_pct Float64 COMMENT '买现货对照%(S_T=S0)',
    scenario_pnl_1_05S Float64 COMMENT '情景盈亏(S_T=1.05*S0, 2份Call双倍盈利)',
    scenario_pnl_1_05S_cny Float64 COMMENT '情景盈亏元/组(S_T=1.05*S0)',
    scenario_pnl_1_05S_pct Float64 COMMENT '情景收益率(S_T=1.05*S0)',
    unhedged_pnl_1_05S Float64 COMMENT '买现货对照(S_T=1.05*S0)',
    unhedged_pnl_1_05S_pct Float64 COMMENT '买现货对照%(S_T=1.05*S0)',
    scenario_pnl_1_10S Float64 COMMENT '情景盈亏(S_T=1.10*S0, 2份Call双倍盈利)',
    scenario_pnl_1_10S_cny Float64 COMMENT '情景盈亏元/组(S_T=1.10*S0)',
    scenario_pnl_1_10S_pct Float64 COMMENT '情景收益率(S_T=1.10*S0)',
    unhedged_pnl_1_10S Float64 COMMENT '买现货对照(S_T=1.10*S0)',
    unhedged_pnl_1_10S_pct Float64 COMMENT '买现货对照%(S_T=1.10*S0)',
    scenario_pnl_1_15S Float64 COMMENT '情景盈亏(S_T=1.15*S0, 2份Call双倍盈利)',
    scenario_pnl_1_15S_cny Float64 COMMENT '情景盈亏元/组(S_T=1.15*S0)',
    scenario_pnl_1_15S_pct Float64 COMMENT '情景收益率(S_T=1.15*S0)',
    unhedged_pnl_1_15S Float64 COMMENT '买现货对照(S_T=1.15*S0)',
    unhedged_pnl_1_15S_pct Float64 COMMENT '买现货对照%(S_T=1.15*S0)',
    -- 交易信号
    trade_signal String COMMENT '交易信号: STRONG_BUY/BUY/CONSIDER/NEUTRAL/AVOID(指是否执行该带式组合)',
    signal_reason String COMMENT '信号原因说明'
)
ENGINE = MergeTree()
ORDER BY (strategy_type, trade_date, exercise_price)
SETTINGS index_granularity = 8192;

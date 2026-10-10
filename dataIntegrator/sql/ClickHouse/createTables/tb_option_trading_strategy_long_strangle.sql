-- Long Strangle（买入宽跨式）策略分析结果表
-- 策略定义: 买入低行权价认沽 Put(K1) + 买入高行权价认购 Call(K2), K1 < K2, 同到期月
-- 净支出 T = P + C(双腿均为虚值 OTM, 比同月跨式便宜)
-- 到期组合收益 = max(0,S_T-K2) + max(0,K1-S_T) - T
-- S_T ∈ [K1,K2] 时双腿同时归零: 亏损平坦封底 T(跨式是 V 形尖底, 宽跨式是"死区"平底)
-- 盈利无上限(双向), 盈亏平衡点: 上=K2+T, 下=K1-T(缺口 K2-K1 拉宽回本区间=便宜的对价)
-- 每行一个组合(非单合约): Call腿(高行权价K2)字段不带后缀, Put腿(低行权价K1)带 _put 后缀
-- 组合生成: Put腿 K1 ∈ ATM下方0~2档, Call腿 K2 ∈ ATM上方0~2档, 且 K2>K1(跨档配对借鉴价差类)
-- 数据来源: tb_tushare_opt_daily_indicator (BS定价/Greeks) + df_tushare_opt_basic (合约名称)
-- 增量写入: 按 trade_date + symbol_filter 删除后插入(call_put 存 'CP' 不参与删除条件)
-- 审计: analysis_time/analysis_params/analysis_version 记录每轮分析的时间戳与参数

--drop table indexsysdb.tb_option_trading_strategy_long_strangle;
--ALTER TABLE indexsysdb.tb_option_trading_strategy_long_strangle DELETE WHERE 1=1;

CREATE TABLE indexsysdb.tb_option_trading_strategy_long_strangle (
    -- 策略标识与审计
    strategy_type String COMMENT '策略类型: LONG_STRANGLE(买入宽跨式, 买Put(K1)+买Call(K2), K1<K2)',
    analysis_time DateTime COMMENT '本轮分析生成时间戳',
    analysis_params String COMMENT '本轮分析参数(JSON): symbol_filter/start_date/end_date等',
    analysis_version String COMMENT '算法版本号, 便于报表端区分口径',
    -- 组合标识(Call腿=高行权价K2, Put腿=低行权价K1 带 _put)
    trade_date String COMMENT '交易日期(YYYYMMDD)',
    ts_code String COMMENT 'Call腿TS合约代码(K2)',
    symbol String COMMENT 'Call腿合约代码(来自opt_basic)',
    opt_name String COMMENT 'Call腿合约名称',
    opt_exchange String COMMENT '交易所(如SSE)',
    call_put String COMMENT '期权类型(CP=宽跨式双腿K1<K2)',
    ts_code_put String COMMENT 'Put腿TS合约代码(K1)',
    symbol_put String COMMENT 'Put腿合约代码',
    opt_name_put String COMMENT 'Put腿合约名称',
    -- 合约要素(同到期月, 双腿行权价不同)
    exercise_price Float64 COMMENT 'Call腿行权价 K2(高)',
    exercise_price_put Float64 COMMENT 'Put腿行权价 K1(低), K1 < K2',
    opt_multiplier Float64 COMMENT '合约单位(乘数)',
    s_month String COMMENT '结算月(YYYYMM)',
    maturity_date String COMMENT '到期日(YYYYMMDD)',
    days_to_maturity Int32 COMMENT '距离到期日历天数',
    -- 标的市场
    spot_price Float64 COMMENT '标的资产当日收盘价S0',
    moneyness_status String COMMENT 'Call腿价态: ITM/ATM/OTM',
    risk_free_rate Float64 COMMENT '无风险利率',
    dividend_yield Float64 COMMENT '股息率q',
    -- 双腿行情与定价
    premium Float64 COMMENT 'Call腿权利金 C(收盘价close)',
    premium_put Float64 COMMENT 'Put腿权利金 P(收盘价close)',
    implied_vol Float64 COMMENT 'Call腿隐含波动率',
    implied_vol_put Float64 COMMENT 'Put腿隐含波动率',
    iv_rank Float64 COMMENT 'Call腿IV分位数(0~1, 近60日)',
    iv_rank_put Float64 COMMENT 'Put腿IV分位数(0~1, 近60日)',
    -- 双腿 Greeks
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
    -- 组合净 Greeks(双腿同为买入: theta双负, vega双正, delta近似对冲)
    net_delta Float64 COMMENT '组合净Delta = delta_call+delta_put(两腿对称OTM时约0, 方向中性)',
    net_gamma Float64 COMMENT '组合净Gamma(双腿叠加为正, 但OTM腿Gamma弱于ATM)',
    net_theta Float64 COMMENT '组合净Theta(双腿同为负, 时间损耗双份)',
    net_vega Float64 COMMENT '组合净Vega(双腿叠加为正, IV回升双向受益)',
    -- 宽跨式结构(花了多少)
    strike_gap Float64 COMMENT '行权价缺口 K2-K1(拉宽平坦亏损区与回本区间的结构性因素)',
    strike_gap_pct Float64 COMMENT '缺口占现价(%): (K2-K1)/S0*100',
    total_premium Float64 COMMENT '总成本 T = P+C(双腿OTM合计, 也是最大亏损, 通常低于同月跨式)',
    total_premium_cny Float64 COMMENT '总成本(元/组): T*乘数',
    total_premium_pct_of_spot Float64 COMMENT '总成本占现价(%): T/S0*100',
    expected_move_1sigma_pct Float64 COMMENT '1σ预期波动(%): σ√T年*100(σ为双腿IV均值, 模型隐含到期波动半径)',
    -- 收益结构(平坦亏损区[K1,K2], 盈利无上限)
    max_loss Float64 COMMENT '组合最大亏损(每单位): T, S_T∈[K1,K2]时双腿同时归零锁定(平坦亏损区而非V形谷底)',
    max_loss_cny Float64 COMMENT '组合最大亏损(元/组)',
    max_loss_pct_of_spot Float64 COMMENT '最大亏损占现价(%): T/S0*100',
    breakeven_up Float64 COMMENT '上盈亏平衡点 = K2+T(需涨过Call腿行权价+全成本)',
    breakeven_up_pct Float64 COMMENT '上平衡所需涨幅(%): (K2+T-S0)/S0*100',
    breakeven_down Float64 COMMENT '下盈亏平衡点 = K1-T(需跌过Put腿行权价-全成本)',
    breakeven_down_pct Float64 COMMENT '下平衡所需跌幅(%): (K1-T-S0)/S0*100',
    breakeven_range_pct Float64 COMMENT '盈亏平衡区间宽度(%): (K2-K1+2T)/S0*100, 比跨式(2T/S0)更宽=便宜的对价',
    -- 概率与评分(最佳组合排序)
    win_prob Float64 COMMENT '胜率(近似): P(S_T>K2+T)+P(S_T<K1-T), 对数正态+双腿IV均值(缺口拉宽双侧门槛, 天然低于跨式)',
    expected_value Float64 COMMENT '期望值(每单位): (BS_C-C)+(BS_P-P), 市价比理论便宜的幅度(双腿均为OTM)',
    score Float64 COMMENT '综合评分 = 期望值/总成本(风险调整后收益, 同日排名依据)',
    combo_rank UInt32 COMMENT '同日内组合评分排名(1=最优)',
    -- 多情景盈亏: S_T=S0*factor, 组合P&L=max(0,S_T-K2)+max(0,K1-S_T)-T(平坦亏损区)
    scenario_pnl_0_85S Float64 COMMENT '情景盈亏(S_T=0.85*S0, Put腿深度实值)',
    scenario_pnl_0_85S_cny Float64 COMMENT '情景盈亏元/组(S_T=0.85*S0)',
    scenario_pnl_0_85S_pct Float64 COMMENT '情景收益率(S_T=0.85*S0): pnl/T*100(以总成本为本金)',
    unhedged_pnl_0_85S Float64 COMMENT '买现货对照(S_T=0.85*S0): S_T-S0',
    unhedged_pnl_0_85S_pct Float64 COMMENT '买现货对照%(S_T=0.85*S0)',
    scenario_pnl_0_90S Float64 COMMENT '情景盈亏(S_T=0.90*S0)',
    scenario_pnl_0_90S_cny Float64 COMMENT '情景盈亏元/组(S_T=0.90*S0)',
    scenario_pnl_0_90S_pct Float64 COMMENT '情景收益率(S_T=0.90*S0)',
    unhedged_pnl_0_90S Float64 COMMENT '买现货对照(S_T=0.90*S0)',
    unhedged_pnl_0_90S_pct Float64 COMMENT '买现货对照%(S_T=0.90*S0)',
    scenario_pnl_0_95S Float64 COMMENT '情景盈亏(S_T=0.95*S0, 或仍处平坦亏损区)',
    scenario_pnl_0_95S_cny Float64 COMMENT '情景盈亏元/组(S_T=0.95*S0)',
    scenario_pnl_0_95S_pct Float64 COMMENT '情景收益率(S_T=0.95*S0)',
    unhedged_pnl_0_95S Float64 COMMENT '买现货对照(S_T=0.95*S0)',
    unhedged_pnl_0_95S_pct Float64 COMMENT '买现货对照%(S_T=0.95*S0)',
    scenario_pnl_1_00S Float64 COMMENT '情景盈亏(S_T=S0, 通常处平坦亏损区, 亏损=T)',
    scenario_pnl_1_00S_cny Float64 COMMENT '情景盈亏元/组(S_T=S0)',
    scenario_pnl_1_00S_pct Float64 COMMENT '情景收益率(S_T=S0)',
    unhedged_pnl_1_00S Float64 COMMENT '买现货对照(S_T=S0)',
    unhedged_pnl_1_00S_pct Float64 COMMENT '买现货对照%(S_T=S0)',
    scenario_pnl_1_05S Float64 COMMENT '情景盈亏(S_T=1.05*S0, 或仍处平坦亏损区)',
    scenario_pnl_1_05S_cny Float64 COMMENT '情景盈亏元/组(S_T=1.05*S0)',
    scenario_pnl_1_05S_pct Float64 COMMENT '情景收益率(S_T=1.05*S0)',
    unhedged_pnl_1_05S Float64 COMMENT '买现货对照(S_T=1.05*S0)',
    unhedged_pnl_1_05S_pct Float64 COMMENT '买现货对照%(S_T=1.05*S0)',
    scenario_pnl_1_10S Float64 COMMENT '情景盈亏(S_T=1.10*S0, Call腿开始贡献)',
    scenario_pnl_1_10S_cny Float64 COMMENT '情景盈亏元/组(S_T=1.10*S0)',
    scenario_pnl_1_10S_pct Float64 COMMENT '情景收益率(S_T=1.10*S0)',
    unhedged_pnl_1_10S Float64 COMMENT '买现货对照(S_T=1.10*S0)',
    unhedged_pnl_1_10S_pct Float64 COMMENT '买现货对照%(S_T=1.10*S0)',
    scenario_pnl_1_15S Float64 COMMENT '情景盈亏(S_T=1.15*S0, Call腿深度实值)',
    scenario_pnl_1_15S_cny Float64 COMMENT '情景盈亏元/组(S_T=1.15*S0)',
    scenario_pnl_1_15S_pct Float64 COMMENT '情景收益率(S_T=1.15*S0)',
    unhedged_pnl_1_15S Float64 COMMENT '买现货对照(S_T=1.15*S0)',
    unhedged_pnl_1_15S_pct Float64 COMMENT '买现货对照%(S_T=1.15*S0)',
    -- 交易信号
    trade_signal String COMMENT '交易信号: STRONG_BUY/BUY/CONSIDER/NEUTRAL/AVOID(指是否执行该宽跨式组合)',
    signal_reason String COMMENT '信号原因说明'
)
ENGINE = MergeTree()
ORDER BY (strategy_type, trade_date, exercise_price, exercise_price_put)
SETTINGS index_granularity = 8192;

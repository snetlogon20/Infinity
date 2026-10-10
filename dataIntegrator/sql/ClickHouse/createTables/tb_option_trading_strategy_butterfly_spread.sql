-- Butterfly Spread（蝴蝶价差，Long Call Butterfly）策略分析结果表
-- 策略定义: 买入低行权价认购 Call(K1) + 卖出2张中间行权价认购 Call(K2) + 买入高行权价认购 Call(K3)
--           K1 < K2 < K3, 同到期月, K2 尽量居中(对称: K2-K1 ≈ K3-K2)
-- 净支出 D = C1 - 2*C2 + C3; 组合到期收益 = max(0,S_T-K1) - 2*max(0,S_T-K2) + max(0,S_T-K3) - D
-- 特点(与方向性价差的本质差异):
--   非方向性: 赚"盘整"(S_T 钉在 K2 附近), 两侧突破都亏 —— 山形(尖顶)收益图, 非厂字形
--   双盈亏平衡点: B1 = K1+D(下平衡), B2 = K3-D(上平衡), 盈利区间 (B1, B2)
--   净 Theta 为正(时间站在卖方/持有者一边), 净 Vega 为负(做空波动率, IV 回落获利)
--   最大盈利 = min(K2-K1, K3-K2) - D (S_T=K2 时取得, 非对称时取窄翼)
--   最大亏损 = D (S_T<=K1 或 S_T>=K3, 两侧平台)
-- 每行一个组合(三腿): 买入腿1(低翼)字段不带后缀, 卖出腿(身体x2)带 _short, 买入腿2(高翼)带 _long2
-- 组合生成: K2 = ATM档, K1 在 K2 下方 1~3 档, K3 在 K2 上方 1~3 档,
--           对称性约束 |(K2-K1)-(K3-K2)|/(K3-K1) <= 25%(教科书等宽蝴蝶), 净支出 D>0
-- 数据来源: tb_tushare_opt_daily_indicator (BS定价/Greeks) + df_tushare_opt_basic (合约名称)
-- 增量写入: 按 trade_date + symbol_filter + call_put 删除后插入
-- 审计: analysis_time/analysis_params/analysis_version 记录每轮分析的时间戳与参数

--drop table indexsysdb.tb_option_trading_strategy_butterfly_spread;
--ALTER TABLE indexsysdb.tb_option_trading_strategy_butterfly_spread DELETE WHERE 1=1;
--ALTER TABLE indexsysdb.tb_option_trading_strategy_butterfly_spread DELETE WHERE trade_date = '20251224';

CREATE TABLE indexsysdb.tb_option_trading_strategy_butterfly_spread (
    -- 策略标识与审计
    strategy_type String COMMENT '策略类型: BUTTERFLY_SPREAD(蝴蝶价差/多头 call butterfly)',
    analysis_time DateTime COMMENT '本轮分析生成时间戳',
    analysis_params String COMMENT '本轮分析参数(JSON): symbol_filter/start_date/end_date/call_put等',
    analysis_version String COMMENT '算法版本号, 便于报表端区分口径',
    -- 组合标识(买入腿1为基准, 卖出腿带 _short, 买入腿2带 _long2)
    trade_date String COMMENT '交易日期(YYYYMMDD)',
    ts_code String COMMENT '买入腿1(低翼)TS合约代码',
    symbol String COMMENT '买入腿1合约代码(来自opt_basic)',
    opt_name String COMMENT '买入腿1合约名称',
    opt_exchange String COMMENT '交易所(如SSE)',
    call_put String COMMENT '期权类型(C=认购, 三腿同为Call)',
    ts_code_short String COMMENT '卖出腿(身体x2)TS合约代码',
    symbol_short String COMMENT '卖出腿合约代码',
    opt_name_short String COMMENT '卖出腿合约名称',
    ts_code_long2 String COMMENT '买入腿2(高翼)TS合约代码',
    symbol_long2 String COMMENT '买入腿2合约代码',
    opt_name_long2 String COMMENT '买入腿2合约名称',
    -- 合约要素(同到期月, 取买入腿1)
    exercise_price Float64 COMMENT '买入腿1行权价 K1(低翼)',
    exercise_price_short Float64 COMMENT '卖出腿行权价 K2(身体, K1 < K2 < K3)',
    exercise_price_long2 Float64 COMMENT '买入腿2行权价 K3(高翼)',
    opt_multiplier Float64 COMMENT '合约单位(乘数)',
    s_month String COMMENT '结算月(YYYYMM)',
    maturity_date String COMMENT '到期日(YYYYMMDD)',
    days_to_maturity Int32 COMMENT '距离到期日历天数',
    -- 标的市场
    spot_price Float64 COMMENT '标的资产当日收盘价S0',
    moneyness_status String COMMENT '买入腿1价态: ITM/ATM/OTM',
    risk_free_rate Float64 COMMENT '无风险利率',
    dividend_yield Float64 COMMENT '股息率q',
    -- 三腿行情与定价
    premium Float64 COMMENT '买入腿1权利金 C1(收盘价close)',
    premium_short Float64 COMMENT '卖出腿权利金 C2(收盘价close, 卖出2张)',
    premium_long2 Float64 COMMENT '买入腿2权利金 C3(收盘价close)',
    implied_vol Float64 COMMENT '买入腿1隐含波动率',
    implied_vol_short Float64 COMMENT '卖出腿隐含波动率',
    implied_vol_long2 Float64 COMMENT '买入腿2隐含波动率',
    iv_rank Float64 COMMENT '买入腿1 IV分位数(0~1, 近60日)',
    iv_rank_short Float64 COMMENT '卖出腿 IV分位数(0~1, 近60日)',
    iv_rank_long2 Float64 COMMENT '买入腿2 IV分位数(0~1, 近60日)',
    -- 三腿 Greeks
    delta Float64 COMMENT '买入腿1 Delta(正值)',
    gamma Float64 COMMENT '买入腿1 Gamma',
    theta Float64 COMMENT '买入腿1 Theta(买方为负)',
    vega Float64 COMMENT '买入腿1 Vega',
    delta_short Float64 COMMENT '卖出腿 Delta(正值)',
    gamma_short Float64 COMMENT '卖出腿 Gamma',
    theta_short Float64 COMMENT '卖出腿 Theta(买方为负)',
    vega_short Float64 COMMENT '卖出腿 Vega',
    delta_long2 Float64 COMMENT '买入腿2 Delta(正值)',
    gamma_long2 Float64 COMMENT '买入腿2 Gamma',
    theta_long2 Float64 COMMENT '买入腿2 Theta(买方为负)',
    vega_long2 Float64 COMMENT '买入腿2 Vega',
    -- 三腿定价偏差
    bs_theoretical_price Float64 COMMENT '买入腿1 BS理论价',
    close_vs_theoretical Float64 COMMENT '买入腿1市价-理论价(负值=买入便宜)',
    close_vs_theoretical_pct Float64 COMMENT '买入腿1市价偏离(%)',
    price_bias String COMMENT '买入腿1定价偏差: 严重低估/低估/公允/高估/严重高估',
    bs_theoretical_price_short Float64 COMMENT '卖出腿BS理论价',
    close_vs_theoretical_short Float64 COMMENT '卖出腿市价-理论价(正值=卖出有利)',
    close_vs_theoretical_pct_short Float64 COMMENT '卖出腿市价偏离(%)',
    price_bias_short String COMMENT '卖出腿定价偏差',
    bs_theoretical_price_long2 Float64 COMMENT '买入腿2 BS理论价',
    close_vs_theoretical_long2 Float64 COMMENT '买入腿2市价-理论价',
    close_vs_theoretical_pct_long2 Float64 COMMENT '买入腿2市价偏离(%)',
    price_bias_long2 String COMMENT '买入腿2定价偏差',
    -- 组合净 Greeks(蝴蝶核心: 净Delta≈0方向中性, 净Theta为正时间帮持有者, 净Vega为负做空波动率)
    net_delta Float64 COMMENT '组合净Delta = delta1 - 2*delta2 + delta3, 接近0(非方向性)',
    net_gamma Float64 COMMENT '组合净Gamma = gamma1 - 2*gamma2 + gamma3',
    net_theta Float64 COMMENT '组合净Theta = theta1 - 2*theta_short + theta3(正值=时间衰减有利)',
    net_vega Float64 COMMENT '组合净Vega = vega1 - 2*vega2 + vega3(负值=做空波动率)',
    -- 蝴蝶结构(花了多少/结构对称性)
    wing_low Float64 COMMENT '下翼宽 = K2 - K1',
    wing_high Float64 COMMENT '上翼宽 = K3 - K2',
    wing_min Float64 COMMENT '窄翼宽 = min(K2-K1, K3-K2), 非对称时决定峰值高度',
    spread_width Float64 COMMENT '总宽 = K3 - K1',
    spread_width_pct Float64 COMMENT '总宽占现价(%): (K3-K1)/S0*100',
    asymmetry_pct Float64 COMMENT '不对称度(%): |(K2-K1)-(K3-K2)|/(K3-K1)*100, 0=教科书等宽',
    net_debit Float64 COMMENT '净支出 D = C1 - 2*C2 + C3(也是最大亏损)',
    net_debit_cny Float64 COMMENT '净支出(元/组): D*乘数',
    net_debit_pct_of_spot Float64 COMMENT '净支出占现价(%): D/S0*100',
    net_debit_pct_of_width Float64 COMMENT '净支出占总宽(%): D/(K3-K1)*100, 越低资本效率越高',
    -- 收益结构(山形: 峰值在K2, 两侧平台)
    max_profit Float64 COMMENT '组合最大盈利(每单位): min(K2-K1,K3-K2)-D, S_T=K2时取得',
    max_profit_cny Float64 COMMENT '组合最大盈利(元/组)',
    max_profit_pct_of_spot Float64 COMMENT '最大盈利占现价(%): 峰值高度/S0*100',
    roi_max_pct Float64 COMMENT '最大资金收益率(%): max_profit/D*100, 以净支出为本金',
    max_loss Float64 COMMENT '组合最大亏损(每单位): D, S_T<=K1或S_T>=K3时锁定',
    max_loss_cny Float64 COMMENT '组合最大亏损(元/组)',
    max_loss_pct_of_spot Float64 COMMENT '最大亏损占现价(%): D/S0*100',
    reward_risk_ratio Float64 COMMENT '回报风险比 = max_profit/D',
    breakeven_S_T Float64 COMMENT '下盈亏平衡点 B1 = K1 + D(跌穿开始亏损)',
    breakeven_upside_pct Float64 COMMENT '下平衡点偏离现价(%): (K1+D-S0)/S0*100',
    breakeven_S_T_high Float64 COMMENT '上盈亏平衡点 B2 = K3 - D(涨过开始亏损, 蝴蝶独有双平衡)',
    breakeven_high_pct Float64 COMMENT '上平衡点偏离现价(%): (K3-D-S0)/S0*100',
    profit_zone_width Float64 COMMENT '盈利区间宽度 = B2 - B1 = (K3-K1) - 2*D',
    -- 概率与评分(最佳组合排序)
    win_prob Float64 COMMENT '胜率(近似): P(B1 < S_T < B2) = P(S_T>K1)-P(S_T>K3) ≈ delta1-delta3, 区间概率',
    expected_value Float64 COMMENT '期望值(每单位): win_prob*max_profit - (1-win_prob)*D',
    score Float64 COMMENT '综合评分 = 期望值/净支出(风险调整后收益)',
    combo_rank UInt32 COMMENT '同日内组合评分排名(1=最优)',
    -- 多情景盈亏: S_T=K2*factor, 组合P&L=max(0,S_T-K1)-2*max(0,S_T-K2)+max(0,S_T-K3)-D
    scenario_pnl_0_85K Float64 COMMENT '情景盈亏(S_T=0.85*K2)',
    scenario_pnl_0_85K_cny Float64 COMMENT '情景盈亏元/组(S_T=0.85*K2)',
    scenario_pnl_0_85K_pct Float64 COMMENT '情景收益率(S_T=0.85*K2): pnl/D*100(以净支出为本金)',
    unhedged_pnl_0_85K Float64 COMMENT '买现货对照(S_T=0.85*K2): S_T-S0',
    unhedged_pnl_0_85K_pct Float64 COMMENT '买现货对照%(S_T=0.85*K2)',
    scenario_pnl_0_90K Float64 COMMENT '情景盈亏(S_T=0.90*K2)',
    scenario_pnl_0_90K_cny Float64 COMMENT '情景盈亏元/组(S_T=0.90*K2)',
    scenario_pnl_0_90K_pct Float64 COMMENT '情景收益率(S_T=0.90*K2)',
    unhedged_pnl_0_90K Float64 COMMENT '买现货对照(S_T=0.90*K2)',
    unhedged_pnl_0_90K_pct Float64 COMMENT '买现货对照%(S_T=0.90*K2)',
    scenario_pnl_0_95K Float64 COMMENT '情景盈亏(S_T=0.95*K2)',
    scenario_pnl_0_95K_cny Float64 COMMENT '情景盈亏元/组(S_T=0.95*K2)',
    scenario_pnl_0_95K_pct Float64 COMMENT '情景收益率(S_T=0.95*K2)',
    unhedged_pnl_0_95K Float64 COMMENT '买现货对照(S_T=0.95*K2)',
    unhedged_pnl_0_95K_pct Float64 COMMENT '买现货对照%(S_T=0.95*K2)',
    scenario_pnl_1_00K Float64 COMMENT '情景盈亏(S_T=K2, 峰值情景)',
    scenario_pnl_1_00K_cny Float64 COMMENT '情景盈亏元/组(S_T=K2)',
    scenario_pnl_1_00K_pct Float64 COMMENT '情景收益率(S_T=K2)',
    unhedged_pnl_1_00K Float64 COMMENT '买现货对照(S_T=K2)',
    unhedged_pnl_1_00K_pct Float64 COMMENT '买现货对照%(S_T=K2)',
    scenario_pnl_1_03K Float64 COMMENT '情景盈亏(S_T=1.03*K2)',
    scenario_pnl_1_03K_cny Float64 COMMENT '情景盈亏元/组(S_T=1.03*K2)',
    scenario_pnl_1_03K_pct Float64 COMMENT '情景收益率(S_T=1.03*K2)',
    unhedged_pnl_1_03K Float64 COMMENT '买现货对照(S_T=1.03*K2)',
    unhedged_pnl_1_03K_pct Float64 COMMENT '买现货对照%(S_T=1.03*K2)',
    scenario_pnl_1_05K Float64 COMMENT '情景盈亏(S_T=1.05*K2)',
    scenario_pnl_1_05K_cny Float64 COMMENT '情景盈亏元/组(S_T=1.05*K2)',
    scenario_pnl_1_05K_pct Float64 COMMENT '情景收益率(S_T=1.05*K2)',
    unhedged_pnl_1_05K Float64 COMMENT '买现货对照(S_T=1.05*K2)',
    unhedged_pnl_1_05K_pct Float64 COMMENT '买现货对照%(S_T=1.05*K2)',
    scenario_pnl_1_10K Float64 COMMENT '情景盈亏(S_T=1.10*K2)',
    scenario_pnl_1_10K_cny Float64 COMMENT '情景盈亏元/组(S_T=1.10*K2)',
    scenario_pnl_1_10K_pct Float64 COMMENT '情景收益率(S_T=1.10*K2)',
    unhedged_pnl_1_10K Float64 COMMENT '买现货对照(S_T=1.10*K2)',
    unhedged_pnl_1_10K_pct Float64 COMMENT '买现货对照%(S_T=1.10*K2)',
    scenario_pnl_1_15K Float64 COMMENT '情景盈亏(S_T=1.15*K2)',
    scenario_pnl_1_15K_cny Float64 COMMENT '情景盈亏元/组(S_T=1.15*K2)',
    scenario_pnl_1_15K_pct Float64 COMMENT '情景收益率(S_T=1.15*K2)',
    unhedged_pnl_1_15K Float64 COMMENT '买现货对照(S_T=1.15*K2)',
    unhedged_pnl_1_15K_pct Float64 COMMENT '买现货对照%(S_T=1.15*K2)',
    -- 交易信号
    trade_signal String COMMENT '交易信号: STRONG_BUY/BUY/CONSIDER/NEUTRAL/AVOID(指是否执行该蝴蝶组合)',
    signal_reason String COMMENT '信号原因说明'
)
ENGINE = MergeTree()
ORDER BY (strategy_type, trade_date, exercise_price, exercise_price_short, exercise_price_long2)
SETTINGS index_granularity = 8192;

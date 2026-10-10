-- Calendar Spread（日历价差/时间价差）策略分析结果表
-- 策略定义: 卖出近月认购 Call(K, T_near) + 买入远月认购 Call(K, T_far), 同行权价同方向跨月
-- 净支出 D = C_far - C_near(也是最大亏损, 亏损封顶)
-- 近月到期日组合价值 V(S_T) = C_near - max(0,S_T-K) + BS_far(S_T) - C_far
--   —— 远月腿用 BS 残值定价(IV_far+剩余期限), 最大盈利/盈亏平衡/胜率均为数值解(尖峰结构)
-- 每行一个组合(近月/远月腿对称 _near/_far 后缀, 时间维度是唯一结构差异)
-- 组合生成: 近月剩余7~45天 × 远月间隔<=95天 × K∈ATM±2档(跨月配对)
-- 数据来源: tb_tushare_opt_daily_indicator (BS定价/Greeks) + df_tushare_opt_basic (合约名称)
-- 增量写入: 按 trade_date + symbol_near LIKE + call_put='C' 删除后插入(基类 DELETE_SYMBOL_COLUMN=symbol_near)
-- 审计: analysis_time/analysis_params/analysis_version 记录每轮分析的时间戳与参数

--drop table indexsysdb.tb_option_trading_strategy_calendar;
--ALTER TABLE indexsysdb.tb_option_trading_strategy_calendar DELETE WHERE 1=1;

CREATE TABLE indexsysdb.tb_option_trading_strategy_calendar (
    -- 策略标识与审计
    strategy_type String COMMENT '策略类型: CALENDAR(日历价差, 卖近月Call+买远月Call, 同行权价跨月)',
    analysis_time DateTime COMMENT '本轮分析生成时间戳',
    analysis_params String COMMENT '本轮分析参数(JSON): symbol_filter/start_date/end_date等',
    analysis_version String COMMENT '算法版本号, 便于报表端区分口径',
    -- 组合标识(近月/远月腿对称后缀)
    trade_date String COMMENT '交易日期(YYYYMMDD)',
    ts_code_near String COMMENT '近月腿TS合约代码(卖出)',
    symbol_near String COMMENT '近月腿合约代码(增量删除过滤列)',
    opt_name_near String COMMENT '近月腿合约名称',
    opt_exchange_near String COMMENT '近月腿交易所(如SSE)',
    ts_code_far String COMMENT '远月腿TS合约代码(买入)',
    symbol_far String COMMENT '远月腿合约代码',
    opt_name_far String COMMENT '远月腿合约名称',
    call_put String COMMENT '期权类型(C=Call Calendar基线, Put版由平价关系冗余)',
    -- 合约要素(同行权价, 跨月)
    exercise_price Float64 COMMENT '行权价 K(两腿相同)',
    opt_multiplier Float64 COMMENT '合约单位(乘数)',
    s_month_near String COMMENT '近月结算月(YYYYMM)',
    maturity_date_near String COMMENT '近月到期日(YYYYMMDD, 即情景/估值日)',
    days_to_maturity_near Int32 COMMENT '近月剩余日历天数',
    s_month_far String COMMENT '远月结算月(YYYYMM)',
    maturity_date_far String COMMENT '远月到期日(YYYYMMDD)',
    days_to_maturity_far Int32 COMMENT '远月剩余日历天数',
    month_gap_days Int32 COMMENT '远近月到期日间隔天数(结构参数, 约1~3个月)',
    -- 标的市场
    spot_price Float64 COMMENT '标的资产当日收盘价S0',
    moneyness_status String COMMENT '近月腿价态: ITM/ATM/OTM',
    risk_free_rate Float64 COMMENT '无风险利率',
    dividend_yield Float64 COMMENT '股息率q(远月BS残值定价输入, 分红季敏感)',
    -- 双腿行情与定价
    premium_near Float64 COMMENT '近月腿权利金 C_near(收盘价close, 卖出收入)',
    premium_far Float64 COMMENT '远月腿权利金 C_far(收盘价close, 买入成本)',
    implied_vol_near Float64 COMMENT '近月腿隐含波动率',
    implied_vol_far Float64 COMMENT '远月腿隐含波动率',
    iv_rank_near Float64 COMMENT '近月腿IV分位数(0~1, 近60日)',
    iv_rank_far Float64 COMMENT '远月腿IV分位数(0~1, 近60日)',
    -- 双腿 Greeks
    delta_near Float64 COMMENT '近月腿Delta(正值, 买入口径)',
    gamma_near Float64 COMMENT '近月腿Gamma(近月大, 负gamma敞口来源)',
    theta_near Float64 COMMENT '近月腿Theta(负值, 绝对值大=衰减快)',
    vega_near Float64 COMMENT '近月腿Vega',
    delta_far Float64 COMMENT '远月腿Delta(正值)',
    gamma_far Float64 COMMENT '远月腿Gamma',
    theta_far Float64 COMMENT '远月腿Theta(负值, 绝对值小)',
    vega_far Float64 COMMENT '远月腿Vega(大, 正vega敞口来源)',
    -- 双腿定价偏差
    bs_theoretical_price_near Float64 COMMENT '近月腿BS理论价',
    close_vs_theoretical_near Float64 COMMENT '近月腿市价-理论价(正值=卖贵占优)',
    close_vs_theoretical_pct_near Float64 COMMENT '近月腿市价偏离(%)',
    price_bias_near String COMMENT '近月腿定价偏差: 严重低估/低估/公允/高估/严重高估',
    bs_theoretical_price_far Float64 COMMENT '远月腿BS理论价',
    close_vs_theoretical_far Float64 COMMENT '远月腿市价-理论价(负值=买便宜占优)',
    close_vs_theoretical_pct_far Float64 COMMENT '远月腿市价偏离(%)',
    price_bias_far String COMMENT '远月腿定价偏差',
    -- 组合净 Greeks(买远卖近)
    net_delta Float64 COMMENT '组合净Delta = delta_far-delta_near(准中性, 两腿同K同向)',
    net_gamma Float64 COMMENT '组合净Gamma(负值: 现货快速移动时近月腿亏损加速)',
    net_theta Float64 COMMENT '组合净Theta(正值: 近月衰减快于远月, 时间是朋友)',
    net_vega Float64 COMMENT '组合净Vega(正值: 买远月波动率, IV整体下行受损)',
    -- 期限结构专属指标
    iv_term_spread Float64 COMMENT 'IV期限结构差 = IV_near-IV_far(小数, >0即近贵远贱, +0.01=1个vol点)',
    theta_differential Float64 COMMENT 'Theta时间差 = |Theta_near|-|Theta_far|(正值=时间站在日历价差这边)',
    -- 日历价差结构(花了多少)
    net_debit Float64 COMMENT '净支出 D = C_far-C_near(也是最大亏损, 亏损封顶)',
    net_debit_cny Float64 COMMENT '净支出(元/组): D*乘数',
    net_debit_pct_of_spot Float64 COMMENT '净支出占现价(%): D/S0*100',
    expected_move_1sigma_pct Float64 COMMENT '1σ预期波动(%): 近月IV*sqrt(T_near年)*100(近月到期分布半径)',
    -- 收益结构(亏损封顶D, 盈利尖峰数值解)
    max_loss Float64 COMMENT '组合最大亏损(每单位): = 净支出D(S_T大幅偏离K时两腿内在价值相抵)',
    max_loss_cny Float64 COMMENT '组合最大亏损(元/组)',
    max_loss_pct_of_spot Float64 COMMENT '最大亏损占现价(%): D/S0*100',
    max_profit Float64 COMMENT '组合最大盈利(每单位): 近月到期日S_T网格数值解(S_T约等于K处, 近月归零+远月残值最大)',
    max_profit_cny Float64 COMMENT '组合最大盈利(元/组)',
    max_profit_pct_of_spot Float64 COMMENT '最大盈利占现价(%): 数值解/S0*100',
    breakeven_down Float64 COMMENT '下盈亏平衡点(数值解, 近月到期日组合价值曲线与0交点)',
    breakeven_down_pct Float64 COMMENT '下平衡偏离(%): (be_down-S0)/S0*100',
    breakeven_up Float64 COMMENT '上盈亏平衡点(数值解)',
    breakeven_up_pct Float64 COMMENT '上平衡偏离(%): (be_up-S0)/S0*100',
    -- 概率与评分(最佳组合排序)
    win_prob Float64 COMMENT '胜率(近似): P(V(S_T)>0), 近月到期日S_T网格x对数正态权重(σ=IV_near)数值积分',
    expected_value Float64 COMMENT '期望值(每单位): (C_near-BS_near)+(BS_far-C_far), 近月卖贵+远月买便宜',
    score Float64 COMMENT '综合评分 = 期望值/净支出(风险调整后收益, 同日排名依据)',
    combo_rank UInt32 COMMENT '同日内组合评分排名(1=最优)',
    -- 多情景盈亏: S_T=S0*factor为近月到期日价格, 近月腿封闭payoff+远月腿BS残值定价
    scenario_pnl_0_85S Float64 COMMENT '情景盈亏(S_T=0.85*S0, 近月到期日, 远月BS残值定价)',
    scenario_pnl_0_85S_cny Float64 COMMENT '情景盈亏元/组(S_T=0.85*S0)',
    scenario_pnl_0_85S_pct Float64 COMMENT '情景收益率(S_T=0.85*S0): pnl/D*100(以净支出为基准)',
    unhedged_pnl_0_85S Float64 COMMENT '买现货对照(S_T=0.85*S0): S_T-S0',
    unhedged_pnl_0_85S_pct Float64 COMMENT '买现货对照%(S_T=0.85*S0)',
    scenario_pnl_0_90S Float64 COMMENT '情景盈亏(S_T=0.90*S0)',
    scenario_pnl_0_90S_cny Float64 COMMENT '情景盈亏元/组(S_T=0.90*S0)',
    scenario_pnl_0_90S_pct Float64 COMMENT '情景收益率(S_T=0.90*S0)',
    unhedged_pnl_0_90S Float64 COMMENT '买现货对照(S_T=0.90*S0)',
    unhedged_pnl_0_90S_pct Float64 COMMENT '买现货对照%(S_T=0.90*S0)',
    scenario_pnl_0_95S Float64 COMMENT '情景盈亏(S_T=0.95*S0, 或已处尖峰盈利区)',
    scenario_pnl_0_95S_cny Float64 COMMENT '情景盈亏元/组(S_T=0.95*S0)',
    scenario_pnl_0_95S_pct Float64 COMMENT '情景收益率(S_T=0.95*S0)',
    unhedged_pnl_0_95S Float64 COMMENT '买现货对照(S_T=0.95*S0)',
    unhedged_pnl_0_95S_pct Float64 COMMENT '买现货对照%(S_T=0.95*S0)',
    scenario_pnl_1_00S Float64 COMMENT '情景盈亏(S_T=S0, 通常接近尖峰盈利区)',
    scenario_pnl_1_00S_cny Float64 COMMENT '情景盈亏元/组(S_T=S0)',
    scenario_pnl_1_00S_pct Float64 COMMENT '情景收益率(S_T=S0)',
    unhedged_pnl_1_00S Float64 COMMENT '买现货对照(S_T=S0)',
    unhedged_pnl_1_00S_pct Float64 COMMENT '买现货对照%(S_T=S0)',
    scenario_pnl_1_05S Float64 COMMENT '情景盈亏(S_T=1.05*S0, 或仍处尖峰盈利区)',
    scenario_pnl_1_05S_cny Float64 COMMENT '情景盈亏元/组(S_T=1.05*S0)',
    scenario_pnl_1_05S_pct Float64 COMMENT '情景收益率(S_T=1.05*S0)',
    unhedged_pnl_1_05S Float64 COMMENT '买现货对照(S_T=1.05*S0)',
    unhedged_pnl_1_05S_pct Float64 COMMENT '买现货对照%(S_T=1.05*S0)',
    scenario_pnl_1_10S Float64 COMMENT '情景盈亏(S_T=1.10*S0, 逼近上平衡点)',
    scenario_pnl_1_10S_cny Float64 COMMENT '情景盈亏元/组(S_T=1.10*S0)',
    scenario_pnl_1_10S_pct Float64 COMMENT '情景收益率(S_T=1.10*S0)',
    unhedged_pnl_1_10S Float64 COMMENT '买现货对照(S_T=1.10*S0)',
    unhedged_pnl_1_10S_pct Float64 COMMENT '买现货对照%(S_T=1.10*S0)',
    scenario_pnl_1_15S Float64 COMMENT '情景盈亏(S_T=1.15*S0, 或已击穿上平衡进入亏损区)',
    scenario_pnl_1_15S_cny Float64 COMMENT '情景盈亏元/组(S_T=1.15*S0)',
    scenario_pnl_1_15S_pct Float64 COMMENT '情景收益率(S_T=1.15*S0)',
    unhedged_pnl_1_15S Float64 COMMENT '买现货对照(S_T=1.15*S0)',
    unhedged_pnl_1_15S_pct Float64 COMMENT '买现货对照%(S_T=1.15*S0)',
    -- 交易信号
    trade_signal String COMMENT '交易信号: STRONG_BUY/BUY/CONSIDER/NEUTRAL/AVOID(期限结构驱动: 近贵远贱+时间差确认)',
    signal_reason String COMMENT '信号原因说明'
)
ENGINE = MergeTree()
ORDER BY (strategy_type, trade_date, s_month_near, s_month_far, exercise_price)
SETTINGS index_granularity = 8192;

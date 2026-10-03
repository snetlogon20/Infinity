-- Bear Put Spread（熊市看跌价差）策略分析结果表
-- 策略定义: 买入高行权价认沽 Put(K2) + 卖出低行权价认沽 Put(K1), K1 < K2, 同到期月
-- 净支出 D = P2 - P1; 组合到期收益 = max(0,K2-S_T) - max(0,K1-S_T) - D
-- 亏损封底 D (S_T>=K2), 盈利封顶 (K2-K1)-D (S_T<=K1), 盈亏平衡点 K2-D (教科书厂字形截头镜像版)
-- 每行一个组合(非单合约): 买入腿字段不带后缀(高行权价K2), 卖出腿字段带 _short 后缀(低行权价K1)
-- 组合生成: 买入腿 K2 限定 ATM±1 档, 卖出腿 K1 = K2 下方 1~4 档(约束剪枝控制组合爆炸)
-- 数据来源: tb_tushare_opt_daily_indicator (BS定价/Greeks) + df_tushare_opt_basic (合约名称)
-- 增量写入: 按 trade_date + symbol_filter + call_put 删除后插入
-- 审计: analysis_time/analysis_params/analysis_version 记录每轮分析的时间戳与参数

--drop table indexsysdb.tb_option_trading_strategy_bear_put_spread;
--ALTER TABLE indexsysdb.tb_option_trading_strategy_bear_put_spread DELETE WHERE 1=1;
--ALTER TABLE indexsysdb.tb_option_trading_strategy_bear_put_spread DELETE WHERE trade_date = '20251224';

CREATE TABLE indexsysdb.tb_option_trading_strategy_bear_put_spread (
    -- 策略标识与审计
    strategy_type String COMMENT '策略类型: BEAR_PUT_SPREAD(熊市看跌价差)',
    analysis_time DateTime COMMENT '本轮分析生成时间戳',
    analysis_params String COMMENT '本轮分析参数(JSON): symbol_filter/start_date/end_date/call_put等',
    analysis_version String COMMENT '算法版本号, 便于报表端区分口径',
    -- 组合标识(买入腿为基准=高行权价K2, 卖出腿带 _short=低行权价K1)
    trade_date String COMMENT '交易日期(YYYYMMDD)',
    ts_code String COMMENT '买入腿TS合约代码(高行权价K2)',
    symbol String COMMENT '买入腿合约代码(来自opt_basic)',
    opt_name String COMMENT '买入腿合约名称',
    opt_exchange String COMMENT '交易所(如SSE)',
    call_put String COMMENT '期权类型(P=认沽, 两腿同为Put)',
    ts_code_short String COMMENT '卖出腿TS合约代码(低行权价K1)',
    symbol_short String COMMENT '卖出腿合约代码',
    opt_name_short String COMMENT '卖出腿合约名称',
    -- 合约要素(同到期月, 取买入腿)
    exercise_price Float64 COMMENT '买入腿行权价 K2 (高)',
    exercise_price_short Float64 COMMENT '卖出腿行权价 K1 (低, K1 < K2)',
    opt_multiplier Float64 COMMENT '合约单位(乘数)',
    s_month String COMMENT '结算月(YYYYMM)',
    maturity_date String COMMENT '到期日(YYYYMMDD)',
    days_to_maturity Int32 COMMENT '距离到期日历天数',
    -- 标的市场
    spot_price Float64 COMMENT '标的资产当日收盘价S0',
    moneyness_status String COMMENT '买入腿价态: ITM/ATM/OTM',
    risk_free_rate Float64 COMMENT '无风险利率',
    dividend_yield Float64 COMMENT '股息率q',
    -- 双腿行情与定价
    premium Float64 COMMENT '买入腿权利金 P2(收盘价close)',
    premium_short Float64 COMMENT '卖出腿权利金 P1(收盘价close)',
    implied_vol Float64 COMMENT '买入腿隐含波动率',
    implied_vol_short Float64 COMMENT '卖出腿隐含波动率',
    iv_rank Float64 COMMENT '买入腿IV分位数(0~1, 近60日)',
    iv_rank_short Float64 COMMENT '卖出腿IV分位数(0~1, 近60日)',
    -- 双腿 Greeks
    delta Float64 COMMENT '买入腿Delta(负值)',
    gamma Float64 COMMENT '买入腿Gamma',
    theta Float64 COMMENT '买入腿Theta(买方为负)',
    vega Float64 COMMENT '买入腿Vega',
    delta_short Float64 COMMENT '卖出腿Delta(负值)',
    gamma_short Float64 COMMENT '卖出腿Gamma',
    theta_short Float64 COMMENT '卖出腿Theta(买方为负)',
    vega_short Float64 COMMENT '卖出腿Vega',
    -- 双腿定价偏差
    bs_theoretical_price Float64 COMMENT '买入腿BS理论价',
    close_vs_theoretical Float64 COMMENT '买入腿市价-理论价(负值=买入便宜)',
    close_vs_theoretical_pct Float64 COMMENT '买入腿市价偏离(%)',
    price_bias String COMMENT '买入腿定价偏差: 严重低估/低估/公允/高估/严重高估',
    bs_theoretical_price_short Float64 COMMENT '卖出腿BS理论价',
    close_vs_theoretical_short Float64 COMMENT '卖出腿市价-理论价(正值=卖出有利)',
    close_vs_theoretical_pct_short Float64 COMMENT '卖出腿市价偏离(%)',
    price_bias_short String COMMENT '卖出腿定价偏差',
    -- 组合净 Greeks(价差的核心优势: theta/vega 大幅抵消)
    net_delta Float64 COMMENT '组合净Delta = delta_long - delta_short(负值=空头方向敞口)',
    net_gamma Float64 COMMENT '组合净Gamma',
    net_theta Float64 COMMENT '组合净Theta = theta_long - theta_short(负值=残余时间损耗)',
    net_vega Float64 COMMENT '组合净Vega(接近0=波动率中性)',
    -- 价差结构(花了多少)
    spread_width Float64 COMMENT '价差宽度 = K2 - K1',
    spread_width_pct Float64 COMMENT '宽度占现价(%): (K2-K1)/S0*100',
    net_debit Float64 COMMENT '净支出 D = P2 - P1(也是最大亏损)',
    net_debit_cny Float64 COMMENT '净支出(元/组): D*乘数',
    net_debit_pct_of_spot Float64 COMMENT '净支出占现价(%): D/S0*100',
    net_debit_pct_of_width Float64 COMMENT '净支出占宽度(%): D/(K2-K1)*100, 越低资本效率越高',
    -- 收益结构(赚了多少/亏了多少)
    max_profit Float64 COMMENT '组合最大盈利(每单位): (K2-K1)-D, S_T<=K1时取得',
    max_profit_cny Float64 COMMENT '组合最大盈利(元/组)',
    max_profit_pct_of_spot Float64 COMMENT '最大盈利占现价(%): ((K2-K1)-D)/S0*100',
    roi_max_pct Float64 COMMENT '最大资金收益率(%): max_profit/D*100, 以净支出为本金',
    max_loss Float64 COMMENT '组合最大亏损(每单位): D, S_T>=K2时锁定',
    max_loss_cny Float64 COMMENT '组合最大亏损(元/组)',
    max_loss_pct_of_spot Float64 COMMENT '最大亏损占现价(%): D/S0*100',
    reward_risk_ratio Float64 COMMENT '回报风险比 = max_profit/D',
    breakeven_S_T Float64 COMMENT '盈亏平衡点 = K2 - D',
    breakeven_downside_pct Float64 COMMENT '盈亏平衡所需跌幅(%): (K2-D-S0)/S0*100',
    -- 概率与评分(最佳组合排序)
    win_prob Float64 COMMENT '胜率(近似): P(S_T < K2-D), 两腿|delta|线性插值',
    expected_value Float64 COMMENT '期望值(每单位): win_prob*max_profit - (1-win_prob)*D',
    score Float64 COMMENT '综合评分 = 期望值/净支出(风险调整后收益)',
    combo_rank UInt32 COMMENT '同日内组合评分排名(1=最优)',
    -- 多情景盈亏: S_T=K2*factor, 组合P&L=max(0,K2-S_T)-max(0,K1-S_T)-D
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
    scenario_pnl_1_00K Float64 COMMENT '情景盈亏(S_T=K2)',
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
    trade_signal String COMMENT '交易信号: STRONG_BUY/BUY/CONSIDER/NEUTRAL/AVOID(指是否执行该价差组合)',
    signal_reason String COMMENT '信号原因说明'
)
ENGINE = MergeTree()
ORDER BY (strategy_type, trade_date, exercise_price, exercise_price_short)
SETTINGS index_granularity = 8192;

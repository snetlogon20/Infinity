-- Short Strangle（卖出宽跨式）策略分析结果表
-- 策略定义: 卖出低行权价认沽 Put(K1) + 卖出高行权价认购 Call(K2), K1 < K2, 同到期月
-- 净收入 T = P + C(双腿均为虚值 OTM, 比同月跨式收得少)
-- 到期组合收益 = T - max(0,S_T-K2) - max(0,K1-S_T)
-- S_T ∈ [K1,K2] 时双腿同时归零: 盈利平坦封顶 T(跨式卖方只有 S_T=K 单点顶, 宽跨式卖方是"平台"收租区)
-- 亏损无上限(双向裸卖), 盈亏平衡点: 上=K2+T, 下=K1-T(缺口 K2-K1 加厚安全垫)
-- 每行一个组合(非单合约): Call腿(高行权价K2)字段不带后缀, Put腿(低行权价K1)带 _put 后缀
-- 组合生成: Put腿 K1 ∈ ATM下方0~2档, Call腿 K2 ∈ ATM上方0~2档, 且 K2>K1(跨档配对借鉴价差类)
-- 数据来源: tb_tushare_opt_daily_indicator (BS定价/Greeks) + df_tushare_opt_basic (合约名称)
-- 增量写入: 按 trade_date + symbol_filter 删除后插入(call_put 存 'CP' 不参与删除条件)
-- 审计: analysis_time/analysis_params/analysis_version 记录每轮分析的时间戳与参数

--drop table indexsysdb.tb_option_trading_strategy_short_strangle;
--ALTER TABLE indexsysdb.tb_option_trading_strategy_short_strangle DELETE WHERE 1=1;

CREATE TABLE indexsysdb.tb_option_trading_strategy_short_strangle (
    -- 策略标识与审计
    strategy_type String COMMENT '策略类型: SHORT_STRANGLE(卖出宽跨式, 卖Put(K1)+卖Call(K2), K1<K2)',
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
    premium Float64 COMMENT 'Call腿权利金 C(收盘价close, 卖出收入)',
    premium_put Float64 COMMENT 'Put腿权利金 P(收盘价close, 卖出收入)',
    implied_vol Float64 COMMENT 'Call腿隐含波动率',
    implied_vol_put Float64 COMMENT 'Put腿隐含波动率',
    iv_rank Float64 COMMENT 'Call腿IV分位数(0~1, 近60日)',
    iv_rank_put Float64 COMMENT 'Put腿IV分位数(0~1, 近60日)',
    -- 双腿 Greeks
    delta Float64 COMMENT 'Call腿Delta(正值, 买入口径)',
    gamma Float64 COMMENT 'Call腿Gamma',
    theta Float64 COMMENT 'Call腿Theta(买方为负, 卖方取负后为收入)',
    vega Float64 COMMENT 'Call腿Vega',
    delta_put Float64 COMMENT 'Put腿Delta(负值, 买入口径)',
    gamma_put Float64 COMMENT 'Put腿Gamma',
    theta_put Float64 COMMENT 'Put腿Theta(买方为负)',
    vega_put Float64 COMMENT 'Put腿Vega',
    -- 双腿定价偏差
    bs_theoretical_price Float64 COMMENT 'Call腿BS理论价',
    close_vs_theoretical Float64 COMMENT 'Call腿市价-理论价(正值=卖出便宜占优)',
    close_vs_theoretical_pct Float64 COMMENT 'Call腿市价偏离(%)',
    price_bias String COMMENT 'Call腿定价偏差: 严重低估/低估/公允/高估/严重高估',
    bs_theoretical_price_put Float64 COMMENT 'Put腿BS理论价',
    close_vs_theoretical_put Float64 COMMENT 'Put腿市价-理论价(正值=卖出便宜占优)',
    close_vs_theoretical_pct_put Float64 COMMENT 'Put腿市价偏离(%)',
    price_bias_put String COMMENT 'Put腿定价偏差',
    -- 组合净 Greeks(双腿同为卖出, 敞口取负叠加)
    net_delta Float64 COMMENT '组合净Delta = -(delta_call+delta_put)(两腿对称OTM时约0, 方向中性)',
    net_gamma Float64 COMMENT '组合净Gamma(卖方为负, 现货贴近任一腿行权价时绝对值骤增)',
    net_theta Float64 COMMENT '组合净Theta(卖出取负: 双腿时间双倍收入, 横盘即收租)',
    net_vega Float64 COMMENT '组合净Vega(双倍为负, IV回升双腿同时受损)',
    -- 宽跨式结构(收了多少)
    strike_gap Float64 COMMENT '行权价缺口 K2-K1(拉宽平坦盈利区与安全垫的结构性因素)',
    strike_gap_pct Float64 COMMENT '缺口占现价(%): (K2-K1)/S0*100',
    total_premium Float64 COMMENT '总租金 T = P+C(双腿OTM合计, 也是最大盈利, 通常低于同月跨式)',
    total_premium_cny Float64 COMMENT '总租金(元/组): T*乘数',
    total_premium_pct_of_spot Float64 COMMENT '总租金占现价(%): T/S0*100',
    expected_move_1sigma_pct Float64 COMMENT '1σ预期波动(%): σ√T年*100(σ为双腿IV均值, 模型隐含到期波动半径)',
    -- 收益结构(平坦盈利区[K1,K2], 亏损无上限)
    max_profit Float64 COMMENT '组合最大盈利(每单位): T, S_T∈[K1,K2]时双腿同时归零锁定(平台收租区而非单点顶)',
    max_profit_cny Float64 COMMENT '组合最大盈利(元/组)',
    max_profit_pct_of_spot Float64 COMMENT '最大盈利占现价(%): T/S0*100',
    breakeven_up Float64 COMMENT '上盈亏平衡点 = K2+T(涨过Call腿行权价+全租金即亏损)',
    breakeven_up_pct Float64 COMMENT '上平衡所需涨幅(%): (K2+T-S0)/S0*100',
    breakeven_down Float64 COMMENT '下盈亏平衡点 = K1-T(跌过Put腿行权价-全租金即亏损)',
    breakeven_down_pct Float64 COMMENT '下平衡所需跌幅(%): (K1-T-S0)/S0*100',
    breakeven_range_pct Float64 COMMENT '安全垫区间宽度(%): (K2-K1+2T)/S0*100, 比跨式(2T/S0)更宽=缺口加厚的收租安全垫',
    -- 概率与评分(最佳组合排序)
    win_prob Float64 COMMENT '胜率(近似): P(K1-T<=S_T<=K2+T), 对数正态+双腿IV均值(缺口加厚安全垫, 天然高于跨式卖方)',
    expected_value Float64 COMMENT '期望值(每单位): (C-BS_C)+(P-BS_P), 市价比理论贵的幅度(卖方正期望, 双腿均为OTM)',
    score Float64 COMMENT '综合评分 = 期望值/总租金(风险调整后收益, 同日排名依据)',
    combo_rank UInt32 COMMENT '同日内组合评分排名(1=最优)',
    -- 多情景盈亏: S_T=S0*factor, 组合P&L=T-max(0,S_T-K2)-max(0,K1-S_T)(平坦盈利区)
    scenario_pnl_0_85S Float64 COMMENT '情景盈亏(S_T=0.85*S0, Put腿深度实值, 亏损区)',
    scenario_pnl_0_85S_cny Float64 COMMENT '情景盈亏元/组(S_T=0.85*S0)',
    scenario_pnl_0_85S_pct Float64 COMMENT '情景收益率(S_T=0.85*S0): pnl/T*100(以总租金为基准)',
    unhedged_pnl_0_85S Float64 COMMENT '买现货对照(S_T=0.85*S0): S_T-S0',
    unhedged_pnl_0_85S_pct Float64 COMMENT '买现货对照%(S_T=0.85*S0)',
    scenario_pnl_0_90S Float64 COMMENT '情景盈亏(S_T=0.90*S0)',
    scenario_pnl_0_90S_cny Float64 COMMENT '情景盈亏元/组(S_T=0.90*S0)',
    scenario_pnl_0_90S_pct Float64 COMMENT '情景收益率(S_T=0.90*S0)',
    unhedged_pnl_0_90S Float64 COMMENT '买现货对照(S_T=0.90*S0)',
    unhedged_pnl_0_90S_pct Float64 COMMENT '买现货对照%(S_T=0.90*S0)',
    scenario_pnl_0_95S Float64 COMMENT '情景盈亏(S_T=0.95*S0, 或已处平坦盈利区)',
    scenario_pnl_0_95S_cny Float64 COMMENT '情景盈亏元/组(S_T=0.95*S0)',
    scenario_pnl_0_95S_pct Float64 COMMENT '情景收益率(S_T=0.95*S0)',
    unhedged_pnl_0_95S Float64 COMMENT '买现货对照(S_T=0.95*S0)',
    unhedged_pnl_0_95S_pct Float64 COMMENT '买现货对照%(S_T=0.95*S0)',
    scenario_pnl_1_00S Float64 COMMENT '情景盈亏(S_T=S0, 通常处平坦盈利区, 恒收T)',
    scenario_pnl_1_00S_cny Float64 COMMENT '情景盈亏元/组(S_T=S0)',
    scenario_pnl_1_00S_pct Float64 COMMENT '情景收益率(S_T=S0)',
    unhedged_pnl_1_00S Float64 COMMENT '买现货对照(S_T=S0)',
    unhedged_pnl_1_00S_pct Float64 COMMENT '买现货对照%(S_T=S0)',
    scenario_pnl_1_05S Float64 COMMENT '情景盈亏(S_T=1.05*S0, 或仍处平坦盈利区)',
    scenario_pnl_1_05S_cny Float64 COMMENT '情景盈亏元/组(S_T=1.05*S0)',
    scenario_pnl_1_05S_pct Float64 COMMENT '情景收益率(S_T=1.05*S0)',
    unhedged_pnl_1_05S Float64 COMMENT '买现货对照(S_T=1.05*S0)',
    unhedged_pnl_1_05S_pct Float64 COMMENT '买现货对照%(S_T=1.05*S0)',
    scenario_pnl_1_10S Float64 COMMENT '情景盈亏(S_T=1.10*S0, Call腿开始亏损)',
    scenario_pnl_1_10S_cny Float64 COMMENT '情景盈亏元/组(S_T=1.10*S0)',
    scenario_pnl_1_10S_pct Float64 COMMENT '情景收益率(S_T=1.10*S0)',
    unhedged_pnl_1_10S Float64 COMMENT '买现货对照(S_T=1.10*S0)',
    unhedged_pnl_1_10S_pct Float64 COMMENT '买现货对照%(S_T=1.10*S0)',
    scenario_pnl_1_15S Float64 COMMENT '情景盈亏(S_T=1.15*S0, Call腿深度实值, 亏损区)',
    scenario_pnl_1_15S_cny Float64 COMMENT '情景盈亏元/组(S_T=1.15*S0)',
    scenario_pnl_1_15S_pct Float64 COMMENT '情景收益率(S_T=1.15*S0)',
    unhedged_pnl_1_15S Float64 COMMENT '买现货对照(S_T=1.15*S0)',
    unhedged_pnl_1_15S_pct Float64 COMMENT '买现货对照%(S_T=1.15*S0)',
    -- 交易信号
    trade_signal String COMMENT '交易信号: STRONG_BUY/BUY/CONSIDER/NEUTRAL/AVOID(指是否执行该卖宽跨式组合, 须配合止损纪律)',
    signal_reason String COMMENT '信号原因说明'
)
ENGINE = MergeTree()
ORDER BY (strategy_type, trade_date, exercise_price, exercise_price_put)
SETTINGS index_granularity = 8192;

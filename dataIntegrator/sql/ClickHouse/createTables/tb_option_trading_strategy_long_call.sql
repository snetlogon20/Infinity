-- Long Call（牛市买购）策略分析结果表
-- 策略定义: 买入认购 Call(K), 支付权利金 C（单腿买方, 经典牛市策略）
-- 组合到期价值 = max(0, S_T - K) - C, 上行收益无限, 下行最大亏损 = C(权利金)
-- 数据来源: tb_tushare_opt_daily_indicator (BS定价/Greeks) + df_tushare_opt_basic (合约名称)
-- 增量写入: 按 trade_date + symbol_filter + call_put 删除后插入
-- 审计: analysis_time/analysis_params/analysis_version 记录每轮分析的时间戳与参数

--drop table indexsysdb.tb_option_trading_strategy_long_call;
--ALTER TABLE indexsysdb.tb_option_trading_strategy_long_call DELETE WHERE 1=1;
--ALTER TABLE indexsysdb.tb_option_trading_strategy_long_call DELETE WHERE trade_date = '20251224';

CREATE TABLE indexsysdb.tb_option_trading_strategy_long_call (
    -- 策略标识与审计
    strategy_type String COMMENT '策略类型: LONG_CALL(牛市买购)',
    analysis_time DateTime COMMENT '本轮分析生成时间戳',
    analysis_params String COMMENT '本轮分析参数(JSON): symbol_filter/start_date/end_date/call_put等',
    analysis_version String COMMENT '算法版本号, 便于报表端区分口径',
    -- 合约标识
    trade_date String COMMENT '交易日期(YYYYMMDD)',
    ts_code String COMMENT 'TS合约代码',
    symbol String COMMENT '合约代码(如510050C2612M03000, 来自opt_basic)',
    opt_name String COMMENT '合约名称(来自opt_basic)',
    opt_exchange String COMMENT '交易所(如SSE)',
    call_put String COMMENT '期权类型(C=认购)',
    -- 合约要素
    exercise_price Float64 COMMENT '行权价K',
    opt_multiplier Float64 COMMENT '合约单位(乘数)',
    s_month String COMMENT '结算月(YYYYMM)',
    maturity_date String COMMENT '到期日(YYYYMMDD)',
    days_to_maturity Int32 COMMENT '距离到期日历天数',
    -- 标的市场
    spot_price Float64 COMMENT '标的资产当日收盘价S0',
    moneyness_status String COMMENT '价态: ITM/ATM/OTM',
    risk_free_rate Float64 COMMENT '无风险利率',
    dividend_yield Float64 COMMENT '股息率q',
    -- 期权行情与定价
    premium Float64 COMMENT '期权权利金(收盘价close, 买方所付成本)',
    implied_vol Float64 COMMENT '隐含波动率',
    iv_rank Float64 COMMENT 'IV分位数(0~1): 当日IV在合约近60日IV历史中的分位, 越低买方越有利',
    delta Float64 COMMENT 'Call Delta(正值, 近似到期实值概率)',
    gamma Float64 COMMENT 'Gamma',
    theta Float64 COMMENT 'Theta(买方为负, 时间衰减成本)',
    vega Float64 COMMENT 'Vega',
    bs_theoretical_price Float64 COMMENT 'BS理论价',
    close_vs_theoretical Float64 COMMENT '市价-理论价(负值=买入价低于理论价, 对买方有利)',
    close_vs_theoretical_pct Float64 COMMENT '市价相对理论价偏离(%)',
    price_bias String COMMENT '定价偏差: 严重低估/低估/公允/高估/严重高估(低估对买方有利)',
    -- 买方成本(花了多少)
    premium_ratio_pct Float64 COMMENT '权利金占现价比例(%): C/S0*100',
    annualized_premium_cost_pct Float64 COMMENT '年化权利金成本(%): C/S0/T*100, 滚动续买的真实成本',
    theta_cost_daily Float64 COMMENT '每日时间衰减成本: |theta|(买方支付)',
    theta_cost_total Float64 COMMENT '持有到期时间衰减总成本: |theta|*天数',
    theta_cost_pct_of_premium Float64 COMMENT '时间衰减成本占权利金比例(%)',
    -- 盈亏平衡(涨多少回本)
    breakeven_S_T Float64 COMMENT '盈亏平衡点: K+C, 到期S_T超过此点买方开始盈利',
    breakeven_required_upside_pct Float64 COMMENT '回本所需涨幅(%): (K+C-S0)/S0*100',
    -- 风险结构(亏得起多少)
    max_loss Float64 COMMENT '最大亏损(每单位): C, S_T<=K时权利金全损',
    max_loss_cny Float64 COMMENT '最大亏损(元/张): C*乘数',
    max_loss_pct_of_spot Float64 COMMENT '最大亏损占现价比例(%): C/S0*100',
    itm_prob Float64 COMMENT '到期实值概率(近似): delta=N(d1), 到期S_T>K概率',
    -- 杠杆(撬了多少)
    capital_leverage Float64 COMMENT '资金杠杆: S0/C, 同等敞口占用资金之比',
    delta_leverage Float64 COMMENT '弹性杠杆: delta*S0/C, 现货涨1%时买方资金收益率(%)',
    effective_delta_exposure Float64 COMMENT '有效方向敞口: delta, 每单位现货敞口等效',
    -- 多情景盈亏: S_T=K*factor, 买方P&L=max(0,S_T-K)-C, 对照=直接买现货
    scenario_pnl_0_90K Float64 COMMENT '情景盈亏(S_T=0.90K)',
    scenario_pnl_0_90K_cny Float64 COMMENT '情景盈亏元/张(S_T=0.90K)',
    scenario_pnl_0_90K_pct Float64 COMMENT '情景收益率(S_T=0.90K): pnl/C*100, 买方资金收益率',
    unhedged_pnl_0_90K Float64 COMMENT '现货对照盈亏(S_T=0.90K): S_T-S0',
    unhedged_pnl_0_90K_pct Float64 COMMENT '现货对照盈亏%(S_T=0.90K)',
    scenario_pnl_0_95K Float64 COMMENT '情景盈亏(S_T=0.95K)',
    scenario_pnl_0_95K_cny Float64 COMMENT '情景盈亏元/张(S_T=0.95K)',
    scenario_pnl_0_95K_pct Float64 COMMENT '情景收益率(S_T=0.95K)',
    unhedged_pnl_0_95K Float64 COMMENT '现货对照盈亏(S_T=0.95K)',
    unhedged_pnl_0_95K_pct Float64 COMMENT '现货对照盈亏%(S_T=0.95K)',
    scenario_pnl_1_00K Float64 COMMENT '情景盈亏(S_T=K)',
    scenario_pnl_1_00K_cny Float64 COMMENT '情景盈亏元/张(S_T=K)',
    scenario_pnl_1_00K_pct Float64 COMMENT '情景收益率(S_T=K)',
    unhedged_pnl_1_00K Float64 COMMENT '现货对照盈亏(S_T=K)',
    unhedged_pnl_1_00K_pct Float64 COMMENT '现货对照盈亏%(S_T=K)',
    scenario_pnl_1_03K Float64 COMMENT '情景盈亏(S_T=1.03K)',
    scenario_pnl_1_03K_cny Float64 COMMENT '情景盈亏元/张(S_T=1.03K)',
    scenario_pnl_1_03K_pct Float64 COMMENT '情景收益率(S_T=1.03K)',
    unhedged_pnl_1_03K Float64 COMMENT '现货对照盈亏(S_T=1.03K)',
    unhedged_pnl_1_03K_pct Float64 COMMENT '现货对照盈亏%(S_T=1.03K)',
    scenario_pnl_1_05K Float64 COMMENT '情景盈亏(S_T=1.05K)',
    scenario_pnl_1_05K_cny Float64 COMMENT '情景盈亏元/张(S_T=1.05K)',
    scenario_pnl_1_05K_pct Float64 COMMENT '情景收益率(S_T=1.05K)',
    unhedged_pnl_1_05K Float64 COMMENT '现货对照盈亏(S_T=1.05K)',
    unhedged_pnl_1_05K_pct Float64 COMMENT '现货对照盈亏%(S_T=1.05K)',
    scenario_pnl_1_10K Float64 COMMENT '情景盈亏(S_T=1.10K)',
    scenario_pnl_1_10K_cny Float64 COMMENT '情景盈亏元/张(S_T=1.10K)',
    scenario_pnl_1_10K_pct Float64 COMMENT '情景收益率(S_T=1.10K)',
    unhedged_pnl_1_10K Float64 COMMENT '现货对照盈亏(S_T=1.10K)',
    unhedged_pnl_1_10K_pct Float64 COMMENT '现货对照盈亏%(S_T=1.10K)',
    scenario_pnl_1_15K Float64 COMMENT '情景盈亏(S_T=1.15K)',
    scenario_pnl_1_15K_cny Float64 COMMENT '情景盈亏元/张(S_T=1.15K)',
    scenario_pnl_1_15K_pct Float64 COMMENT '情景收益率(S_T=1.15K)',
    unhedged_pnl_1_15K Float64 COMMENT '现货对照盈亏(S_T=1.15K)',
    unhedged_pnl_1_15K_pct Float64 COMMENT '现货对照盈亏%(S_T=1.15K)',
    scenario_pnl_1_20K Float64 COMMENT '情景盈亏(S_T=1.20K)',
    scenario_pnl_1_20K_cny Float64 COMMENT '情景盈亏元/张(S_T=1.20K)',
    scenario_pnl_1_20K_pct Float64 COMMENT '情景收益率(S_T=1.20K)',
    unhedged_pnl_1_20K Float64 COMMENT '现货对照盈亏(S_T=1.20K)',
    unhedged_pnl_1_20K_pct Float64 COMMENT '现货对照盈亏%(S_T=1.20K)',
    upside_capture Float64 COMMENT '上行捕获率(1.10K情景): 买方盈亏/现货盈亏, >1=杠杆跑赢现货',
    -- 交易信号
    trade_signal String COMMENT '交易信号: STRONG_BUY/BUY/CONSIDER/NEUTRAL/AVOID(指是否执行买购)',
    signal_reason String COMMENT '信号原因说明'
)
ENGINE = MergeTree()
ORDER BY (strategy_type, trade_date, ts_code)
SETTINGS index_granularity = 8192;

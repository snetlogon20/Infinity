-- Protective Put（保护性认沽）策略分析结果专表
-- 策略定义: 持有现货 S0 + 买入认沽 Put(K), 支付权利金 P
-- 组合到期价值 = S_T + max(0, K - S_T) - P - S0, 下行锁定价值底 K-P
-- 数据来源: tb_tushare_opt_daily_indicator (BS定价/Greeks) + df_tushare_opt_basic (合约名称)
-- 增量写入: 按 strategy_type + trade_date + symbol_filter + call_put 删除后插入
-- 审计: analysis_time/analysis_params/analysis_version 记录每轮分析的时间戳与参数
-- 跨策略查询: vw_option_trading_strategy_union (union 视图, 含公共可合并字段)

-- 由旧表改名而来(存量数据保留):
-- RENAME TABLE indexsysdb.tb_option_trading_strategy TO indexsysdb.tb_option_trading_strategy_protective_put;

-- 存量表升级(免重建):
--ALTER TABLE indexsysdb.tb_option_trading_strategy_protective_put ADD COLUMN IF NOT EXISTS score Float64;
--ALTER TABLE indexsysdb.tb_option_trading_strategy_protective_put ADD COLUMN IF NOT EXISTS contract_rank UInt32;

--drop table indexsysdb.tb_option_trading_strategy_protective_put;
--ALTER TABLE indexsysdb.tb_option_trading_strategy_protective_put DELETE WHERE strategy_type = 'PROTECTIVE_PUT';
--ALTER TABLE indexsysdb.tb_option_trading_strategy_protective_put DELETE WHERE strategy_type = 'PROTECTIVE_PUT' AND trade_date = '20251224';

CREATE TABLE indexsysdb.tb_option_trading_strategy_protective_put (
    -- 策略标识与审计
    strategy_type String COMMENT '策略类型: PROTECTIVE_PUT(保护性认沽)',
    analysis_time DateTime COMMENT '本轮分析生成时间戳',
    analysis_params String COMMENT '本轮分析参数(JSON): symbol_filter/start_date/end_date/call_put等',
    analysis_version String COMMENT '算法版本号, 便于报表端区分口径',
    -- 合约标识
    trade_date String COMMENT '交易日期(YYYYMMDD)',
    ts_code String COMMENT 'TS合约代码',
    symbol String COMMENT '合约代码(如510050P2612M03000, 来自opt_basic)',
    opt_name String COMMENT '合约名称(来自opt_basic)',
    opt_exchange String COMMENT '交易所(如SSE)',
    call_put String COMMENT '期权类型(P=认沽)',
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
    premium Float64 COMMENT '期权权利金(收盘价close)',
    implied_vol Float64 COMMENT '隐含波动率',
    iv_rank Float64 COMMENT 'IV分位数(0~1): 当日IV在合约近60日IV历史中的分位, 越低保险越便宜',
    delta Float64 COMMENT 'Put Delta(负值)',
    gamma Float64 COMMENT 'Gamma',
    theta Float64 COMMENT 'Theta(每日时间衰减, 元/天)',
    vega Float64 COMMENT 'Vega',
    bs_theoretical_price Float64 COMMENT 'BS理论价',
    close_vs_theoretical Float64 COMMENT '市价-理论价',
    close_vs_theoretical_pct Float64 COMMENT '市价相对理论价偏离(%)',
    price_bias String COMMENT '定价偏差: 严重低估/低估/公允/高估/严重高估',
    -- 下行保护(保了多少)
    protected_floor Float64 COMMENT '组合到期价值硬底: K-P(S_T<=K时组合价值恒为K-P)',
    protected_floor_pct_of_spot Float64 COMMENT '价值底占现价比例(%): (K-P)/S0*100',
    max_loss Float64 COMMENT '组合最大亏损(每单位): K-P-S0',
    max_loss_cny Float64 COMMENT '组合最大亏损(元/张): (K-P-S0)*乘数',
    max_loss_pct_of_spot Float64 COMMENT '最大亏损占现价比例(%): 对冲后最大回撤',
    protection_per_cost Float64 COMMENT '保险杠杆: (K-P)/P, 每1元保费锁定的下行价值',
    downside_capture Float64 COMMENT '下跌捕获率(0.90K情景): 对冲后亏损/未对冲亏损, 0=完全保护 1=无保护',
    -- 对冲成本(花了多少)
    hedge_cost_ratio Float64 COMMENT '对冲成本比: P/S0, 保护成本占持仓比例',
    annualized_hedge_cost_pct Float64 COMMENT '年化对冲成本(%): P/S0/T*100, 滚动续保真实成本',
    theta_cost_daily Float64 COMMENT '每日时间衰减成本: |theta|',
    theta_cost_total Float64 COMMENT '持有到期时间衰减总成本: |theta|*天数',
    theta_cost_pct_of_premium Float64 COMMENT '时间衰减占权利金比例(%)',
    -- 上行代价(让了多少)
    breakeven_S_T Float64 COMMENT '盈亏平衡点: S0+P, 上行需涨过此点组合才盈利',
    breakeven_S_T_pct Float64 COMMENT '盈亏平衡涨幅(%)',
    upside_giveup_pct Float64 COMMENT '上行让渡(%): P/S0*100',
    -- 对冲后敞口
    portfolio_delta Float64 COMMENT '组合净Delta: 1+delta_put, 剩余方向性敞口',
    residual_exposure_pct Float64 COMMENT '剩余敞口(%): (1+delta_put)*100',
    -- 评分与排名(同日候选行权价横向比较)
    score Float64 COMMENT '综合评分(=(S0-(K-P))/P): 保险效率, 每1元保费保护的下行幅度, 同日候选合约排名依据',
    contract_rank UInt32 COMMENT '同日按score降序排名(1=当日保险效率最高的行权价)',
    -- 多情景盈亏: S_T=K*factor, 组合P&L=(S_T-S0)+max(0,K-S_T)-P
    scenario_pnl_0_80K Float64 COMMENT '情景盈亏(S_T=0.80K)',
    scenario_pnl_0_80K_cny Float64 COMMENT '情景盈亏元/张(S_T=0.80K)',
    scenario_pnl_0_80K_pct Float64 COMMENT '情景收益率(S_T=0.80K): pnl/(S0+P)*100',
    unhedged_pnl_0_80K Float64 COMMENT '未对冲盈亏(S_T=0.80K): S_T-S0',
    unhedged_pnl_0_80K_pct Float64 COMMENT '未对冲盈亏%(S_T=0.80K)',
    scenario_pnl_0_85K Float64 COMMENT '情景盈亏(S_T=0.85K)',
    scenario_pnl_0_85K_cny Float64 COMMENT '情景盈亏元/张(S_T=0.85K)',
    scenario_pnl_0_85K_pct Float64 COMMENT '情景收益率(S_T=0.85K)',
    unhedged_pnl_0_85K Float64 COMMENT '未对冲盈亏(S_T=0.85K)',
    unhedged_pnl_0_85K_pct Float64 COMMENT '未对冲盈亏%(S_T=0.85K)',
    scenario_pnl_0_90K Float64 COMMENT '情景盈亏(S_T=0.90K)',
    scenario_pnl_0_90K_cny Float64 COMMENT '情景盈亏元/张(S_T=0.90K)',
    scenario_pnl_0_90K_pct Float64 COMMENT '情景收益率(S_T=0.90K)',
    unhedged_pnl_0_90K Float64 COMMENT '未对冲盈亏(S_T=0.90K)',
    unhedged_pnl_0_90K_pct Float64 COMMENT '未对冲盈亏%(S_T=0.90K)',
    scenario_pnl_0_95K Float64 COMMENT '情景盈亏(S_T=0.95K)',
    scenario_pnl_0_95K_cny Float64 COMMENT '情景盈亏元/张(S_T=0.95K)',
    scenario_pnl_0_95K_pct Float64 COMMENT '情景收益率(S_T=0.95K)',
    unhedged_pnl_0_95K Float64 COMMENT '未对冲盈亏(S_T=0.95K)',
    unhedged_pnl_0_95K_pct Float64 COMMENT '未对冲盈亏%(S_T=0.95K)',
    scenario_pnl_1_00K Float64 COMMENT '情景盈亏(S_T=K)',
    scenario_pnl_1_00K_cny Float64 COMMENT '情景盈亏元/张(S_T=K)',
    scenario_pnl_1_00K_pct Float64 COMMENT '情景收益率(S_T=K)',
    unhedged_pnl_1_00K Float64 COMMENT '未对冲盈亏(S_T=K)',
    unhedged_pnl_1_00K_pct Float64 COMMENT '未对冲盈亏%(S_T=K)',
    scenario_pnl_1_03K Float64 COMMENT '情景盈亏(S_T=1.03K)',
    scenario_pnl_1_03K_cny Float64 COMMENT '情景盈亏元/张(S_T=1.03K)',
    scenario_pnl_1_03K_pct Float64 COMMENT '情景收益率(S_T=1.03K)',
    unhedged_pnl_1_03K Float64 COMMENT '未对冲盈亏(S_T=1.03K)',
    unhedged_pnl_1_03K_pct Float64 COMMENT '未对冲盈亏%(S_T=1.03K)',
    scenario_pnl_1_05K Float64 COMMENT '情景盈亏(S_T=1.05K)',
    scenario_pnl_1_05K_cny Float64 COMMENT '情景盈亏元/张(S_T=1.05K)',
    scenario_pnl_1_05K_pct Float64 COMMENT '情景收益率(S_T=1.05K)',
    unhedged_pnl_1_05K Float64 COMMENT '未对冲盈亏(S_T=1.05K)',
    unhedged_pnl_1_05K_pct Float64 COMMENT '未对冲盈亏%(S_T=1.05K)',
    scenario_pnl_1_10K Float64 COMMENT '情景盈亏(S_T=1.10K)',
    scenario_pnl_1_10K_cny Float64 COMMENT '情景盈亏元/张(S_T=1.10K)',
    scenario_pnl_1_10K_pct Float64 COMMENT '情景收益率(S_T=1.10K)',
    unhedged_pnl_1_10K Float64 COMMENT '未对冲盈亏(S_T=1.10K)',
    unhedged_pnl_1_10K_pct Float64 COMMENT '未对冲盈亏%(S_T=1.10K)',
    -- 交易信号
    trade_signal String COMMENT '交易信号: STRONG_BUY/BUY/CONSIDER/NEUTRAL/AVOID',
    signal_reason String COMMENT '信号原因说明'
)
ENGINE = MergeTree()
ORDER BY (strategy_type, trade_date, ts_code)
SETTINGS index_granularity = 8192;

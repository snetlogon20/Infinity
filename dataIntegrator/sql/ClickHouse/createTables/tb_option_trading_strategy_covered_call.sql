-- Covered Call（备兑开仓）策略分析结果表
-- 策略定义: 持有现货 S0 + 卖出认购 Call(K), 收取权利金 C
-- 组合到期价值 = S_T - max(0, S_T - K) + C, 上行封顶于 K+C, 下行有权利金缓冲
-- 数据来源: tb_tushare_opt_daily_indicator (BS定价/Greeks) + df_tushare_opt_basic (合约名称)
-- 增量写入: 按 trade_date + symbol_filter + call_put 删除后插入
-- 审计: analysis_time/analysis_params/analysis_version 记录每轮分析的时间戳与参数

-- 存量表升级(免重建):
--ALTER TABLE indexsysdb.tb_option_trading_strategy_covered_call ADD COLUMN IF NOT EXISTS score Float64;
--ALTER TABLE indexsysdb.tb_option_trading_strategy_covered_call ADD COLUMN IF NOT EXISTS contract_rank UInt32;

--drop table indexsysdb.tb_option_trading_strategy_covered_call;
--ALTER TABLE indexsysdb.tb_option_trading_strategy_covered_call DELETE WHERE 1=1;
--ALTER TABLE indexsysdb.tb_option_trading_strategy_covered_call DELETE WHERE trade_date = '20251224';

CREATE TABLE indexsysdb.tb_option_trading_strategy_covered_call (
    -- 策略标识与审计
    strategy_type String COMMENT '策略类型: COVERED_CALL(备兑开仓)',
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
    premium Float64 COMMENT '期权权利金(收盘价close, 卖出Call所收)',
    implied_vol Float64 COMMENT '隐含波动率',
    iv_rank Float64 COMMENT 'IV分位数(0~1): 当日IV在合约近60日IV历史中的分位, 越高卖方越有利',
    delta Float64 COMMENT 'Call Delta(正值, 近似被行权概率)',
    gamma Float64 COMMENT 'Gamma',
    theta Float64 COMMENT 'Theta(买方为负, 卖方收入为|theta|)',
    vega Float64 COMMENT 'Vega',
    bs_theoretical_price Float64 COMMENT 'BS理论价',
    close_vs_theoretical Float64 COMMENT '市价-理论价(正值=卖出价高于理论价, 对卖方有利)',
    close_vs_theoretical_pct Float64 COMMENT '市价相对理论价偏离(%)',
    price_bias String COMMENT '定价偏差: 严重低估/低估/公允/高估/严重高估(高估对卖方有利)',
    -- 上行封顶(让了多少)
    max_profit Float64 COMMENT '组合最大盈利(每单位): K-S0+C, S_T>=K时取得',
    max_profit_cny Float64 COMMENT '组合最大盈利(元/张): (K-S0+C)*乘数',
    max_profit_pct_of_spot Float64 COMMENT '最大盈利占现价比例(%): (K-S0+C)/S0*100',
    upside_cap_S_T Float64 COMMENT '上行封顶点: K, 到期组合价值不随S_T超过K继续增长',
    upside_giveup_pct Float64 COMMENT '上行让渡(%): 超过K的涨幅全部放弃, 以(K-S0)/S0*100计',
    -- 下行缓冲(保了多少)
    premium_cushion Float64 COMMENT '权利金缓冲: C, 下跌C以内组合不亏',
    premium_cushion_pct_of_spot Float64 COMMENT '缓冲占现价比例(%): C/S0*100',
    downside_breakeven_S_T Float64 COMMENT '下行盈亏平衡点: S0-C, 跌破此点组合开始亏损',
    downside_breakeven_S_T_pct Float64 COMMENT '下行盈亏平衡跌幅(%): -C/S0*100',
    max_loss Float64 COMMENT '组合最大亏损(每单位, S_T=0): C-S0',
    max_loss_cny Float64 COMMENT '组合最大亏损(元/张): (C-S0)*乘数',
    max_loss_pct_of_spot Float64 COMMENT '最大亏损占现价比例(%): (C-S0)/S0*100',
    cushion_effect Float64 COMMENT '缓冲效果(0.95K情景): (未对冲亏损-对冲后亏损)/未对冲亏损, 1=完全吸收',
    -- 收益增强(赚了多少)
    premium_yield_pct Float64 COMMENT '静态收益率(%): C/S0*100, 持有到期不轧平的租金收益',
    annualized_premium_yield_pct Float64 COMMENT '年化静态收益率(%): C/S0/T*100',
    theta_income_daily Float64 COMMENT '每日时间衰减收入: |theta|(卖方收取)',
    theta_income_total Float64 COMMENT '持有到期时间衰减总收入: |theta|*天数',
    theta_income_pct_of_premium Float64 COMMENT '时间衰减收入占权利金比例(%)',
    assignment_prob Float64 COMMENT '被行权概率(近似): delta=N(d1), 到期S_T>K概率',
    -- 对冲后敞口
    portfolio_delta Float64 COMMENT '组合净Delta: 1-delta_call, 剩余方向性敞口',
    residual_exposure_pct Float64 COMMENT '剩余敞口(%): (1-delta_call)*100',
    -- 评分与排名(同日候选行权价横向比较)
    score Float64 COMMENT '综合评分(=年化时间价值收益率%=(C-max(0,S0-K))/S0/T): 备兑真正的租金(剔除内在价值), 同日候选合约的排名依据',
    contract_rank UInt32 COMMENT '同日按score降序排名(1=当日最优备兑合约)',
    -- 多情景盈亏: S_T=K*factor, 组合P&L=(S_T-S0)-max(0,S_T-K)+C
    scenario_pnl_0_85K Float64 COMMENT '情景盈亏(S_T=0.85K)',
    scenario_pnl_0_85K_cny Float64 COMMENT '情景盈亏元/张(S_T=0.85K)',
    scenario_pnl_0_85K_pct Float64 COMMENT '情景收益率(S_T=0.85K): pnl/S0*100',
    unhedged_pnl_0_85K Float64 COMMENT '未备兑盈亏(S_T=0.85K): S_T-S0',
    unhedged_pnl_0_85K_pct Float64 COMMENT '未备兑盈亏%(S_T=0.85K)',
    scenario_pnl_0_90K Float64 COMMENT '情景盈亏(S_T=0.90K)',
    scenario_pnl_0_90K_cny Float64 COMMENT '情景盈亏元/张(S_T=0.90K)',
    scenario_pnl_0_90K_pct Float64 COMMENT '情景收益率(S_T=0.90K)',
    unhedged_pnl_0_90K Float64 COMMENT '未备兑盈亏(S_T=0.90K)',
    unhedged_pnl_0_90K_pct Float64 COMMENT '未备兑盈亏%(S_T=0.90K)',
    scenario_pnl_0_95K Float64 COMMENT '情景盈亏(S_T=0.95K)',
    scenario_pnl_0_95K_cny Float64 COMMENT '情景盈亏元/张(S_T=0.95K)',
    scenario_pnl_0_95K_pct Float64 COMMENT '情景收益率(S_T=0.95K)',
    unhedged_pnl_0_95K Float64 COMMENT '未备兑盈亏(S_T=0.95K)',
    unhedged_pnl_0_95K_pct Float64 COMMENT '未备兑盈亏%(S_T=0.95K)',
    scenario_pnl_1_00K Float64 COMMENT '情景盈亏(S_T=K)',
    scenario_pnl_1_00K_cny Float64 COMMENT '情景盈亏元/张(S_T=K)',
    scenario_pnl_1_00K_pct Float64 COMMENT '情景收益率(S_T=K)',
    unhedged_pnl_1_00K Float64 COMMENT '未备兑盈亏(S_T=K)',
    unhedged_pnl_1_00K_pct Float64 COMMENT '未备兑盈亏%(S_T=K)',
    scenario_pnl_1_03K Float64 COMMENT '情景盈亏(S_T=1.03K)',
    scenario_pnl_1_03K_cny Float64 COMMENT '情景盈亏元/张(S_T=1.03K)',
    scenario_pnl_1_03K_pct Float64 COMMENT '情景收益率(S_T=1.03K)',
    unhedged_pnl_1_03K Float64 COMMENT '未备兑盈亏(S_T=1.03K)',
    unhedged_pnl_1_03K_pct Float64 COMMENT '未备兑盈亏%(S_T=1.03K)',
    scenario_pnl_1_05K Float64 COMMENT '情景盈亏(S_T=1.05K)',
    scenario_pnl_1_05K_cny Float64 COMMENT '情景盈亏元/张(S_T=1.05K)',
    scenario_pnl_1_05K_pct Float64 COMMENT '情景收益率(S_T=1.05K)',
    unhedged_pnl_1_05K Float64 COMMENT '未备兑盈亏(S_T=1.05K)',
    unhedged_pnl_1_05K_pct Float64 COMMENT '未备兑盈亏%(S_T=1.05K)',
    scenario_pnl_1_10K Float64 COMMENT '情景盈亏(S_T=1.10K)',
    scenario_pnl_1_10K_cny Float64 COMMENT '情景盈亏元/张(S_T=1.10K)',
    scenario_pnl_1_10K_pct Float64 COMMENT '情景收益率(S_T=1.10K)',
    unhedged_pnl_1_10K Float64 COMMENT '未备兑盈亏(S_T=1.10K)',
    unhedged_pnl_1_10K_pct Float64 COMMENT '未备兑盈亏%(S_T=1.10K)',
    scenario_pnl_1_15K Float64 COMMENT '情景盈亏(S_T=1.15K)',
    scenario_pnl_1_15K_cny Float64 COMMENT '情景盈亏元/张(S_T=1.15K)',
    scenario_pnl_1_15K_pct Float64 COMMENT '情景收益率(S_T=1.15K)',
    unhedged_pnl_1_15K Float64 COMMENT '未备兑盈亏(S_T=1.15K)',
    unhedged_pnl_1_15K_pct Float64 COMMENT '未备兑盈亏%(S_T=1.15K)',
    -- 交易信号
    trade_signal String COMMENT '交易信号: STRONG_BUY/BUY/CONSIDER/NEUTRAL/AVOID(指是否执行备兑)',
    signal_reason String COMMENT '信号原因说明'
)
ENGINE = MergeTree()
ORDER BY (strategy_type, trade_date, ts_code)
SETTINGS index_granularity = 8192;

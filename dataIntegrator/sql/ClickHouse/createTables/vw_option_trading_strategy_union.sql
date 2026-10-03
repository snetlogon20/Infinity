-- 期权交易策略分析结果 联合视图（跨策略统一查询入口）
-- 合并来源:
--   tb_option_trading_strategy_protective_put (strategy_type='PROTECTIVE_PUT', 现货+买入Put)
--   tb_option_trading_strategy_covered_call   (strategy_type='COVERED_CALL',  现货+卖出Call)
-- 仅包含两表结构一致、口径可直接合并的字段(公共 7 档情景: 0.85K~1.10K)
--
-- ⚠ 口径混合列说明(同名列在两个策略中公式不同, 跨策略比较时注意):
--   scenario_pnl_*_pct : PP 分母为 S0+P(成本含保费), CC 分母为 S0(权利金是收入)
--                        → 跨策略数值比较请使用绝对盈亏列 scenario_pnl_* / *_cny
--   upside_giveup_pct  : PP = P/S0*100(保费成本), CC = (K-S0)/S0*100(封顶以上涨幅)
--   max_loss*          : 语义一致(各策略最大亏损), 公式本就该不同(PP: K-P-S0, CC: C-S0)
--   unhedged_pnl_*     : 两策略口径完全一致(纯现货 S_T-S0), 可直接跨策略比较
--
-- 维护注意:
--   ClickHouse UNION ALL 按位置对齐(不按列名), 两边 SELECT 列清单必须完全一致;
--   底表加列后本视图不会自动同步, 需 DROP VIEW 后重建。
--   各策略专有列不在此视图:
--     PP: protected_floor*/protection_per_cost/downside_capture/hedge_cost*/
--         theta_cost*/breakeven_S_T*/scenario_pnl_0_80K*
--     CC: max_profit*/upside_cap_S_T/premium_cushion*/downside_breakeven_S_T*/
--         cushion_effect/premium_yield*/theta_income*/assignment_prob/scenario_pnl_1_15K*

--drop view indexsysdb.vw_option_trading_strategy_union;

CREATE VIEW indexsysdb.vw_option_trading_strategy_union AS
-- ============ 策略一: Protective Put (保护性认沽) ============
SELECT
    -- 策略标识与审计
    strategy_type, analysis_time, analysis_params, analysis_version,
    -- 合约标识
    trade_date, ts_code, symbol, opt_name, opt_exchange, call_put,
    -- 合约要素
    exercise_price, opt_multiplier, s_month, maturity_date, days_to_maturity,
    -- 标的市场
    spot_price, moneyness_status, risk_free_rate, dividend_yield,
    -- 期权行情与定价
    premium, implied_vol, iv_rank, delta, gamma, theta, vega,
    bs_theoretical_price, close_vs_theoretical, close_vs_theoretical_pct, price_bias,
    -- 通用策略指标(口径见文件头说明)
    max_loss, max_loss_cny, max_loss_pct_of_spot, upside_giveup_pct,
    portfolio_delta, residual_exposure_pct,
    -- 公共情景盈亏: S_T = 0.85K
    scenario_pnl_0_85K, scenario_pnl_0_85K_cny, scenario_pnl_0_85K_pct,
    unhedged_pnl_0_85K, unhedged_pnl_0_85K_pct,
    -- 公共情景盈亏: S_T = 0.90K
    scenario_pnl_0_90K, scenario_pnl_0_90K_cny, scenario_pnl_0_90K_pct,
    unhedged_pnl_0_90K, unhedged_pnl_0_90K_pct,
    -- 公共情景盈亏: S_T = 0.95K
    scenario_pnl_0_95K, scenario_pnl_0_95K_cny, scenario_pnl_0_95K_pct,
    unhedged_pnl_0_95K, unhedged_pnl_0_95K_pct,
    -- 公共情景盈亏: S_T = 1.00K
    scenario_pnl_1_00K, scenario_pnl_1_00K_cny, scenario_pnl_1_00K_pct,
    unhedged_pnl_1_00K, unhedged_pnl_1_00K_pct,
    -- 公共情景盈亏: S_T = 1.03K
    scenario_pnl_1_03K, scenario_pnl_1_03K_cny, scenario_pnl_1_03K_pct,
    unhedged_pnl_1_03K, unhedged_pnl_1_03K_pct,
    -- 公共情景盈亏: S_T = 1.05K
    scenario_pnl_1_05K, scenario_pnl_1_05K_cny, scenario_pnl_1_05K_pct,
    unhedged_pnl_1_05K, unhedged_pnl_1_05K_pct,
    -- 公共情景盈亏: S_T = 1.10K
    scenario_pnl_1_10K, scenario_pnl_1_10K_cny, scenario_pnl_1_10K_pct,
    unhedged_pnl_1_10K, unhedged_pnl_1_10K_pct,
    -- 交易信号
    trade_signal, signal_reason
FROM indexsysdb.tb_option_trading_strategy_protective_put
UNION ALL
-- ============ 策略二: Covered Call (备兑开仓) ============
SELECT
    -- 策略标识与审计
    strategy_type, analysis_time, analysis_params, analysis_version,
    -- 合约标识
    trade_date, ts_code, symbol, opt_name, opt_exchange, call_put,
    -- 合约要素
    exercise_price, opt_multiplier, s_month, maturity_date, days_to_maturity,
    -- 标的市场
    spot_price, moneyness_status, risk_free_rate, dividend_yield,
    -- 期权行情与定价
    premium, implied_vol, iv_rank, delta, gamma, theta, vega,
    bs_theoretical_price, close_vs_theoretical, close_vs_theoretical_pct, price_bias,
    -- 通用策略指标(口径见文件头说明)
    max_loss, max_loss_cny, max_loss_pct_of_spot, upside_giveup_pct,
    portfolio_delta, residual_exposure_pct,
    -- 公共情景盈亏: S_T = 0.85K
    scenario_pnl_0_85K, scenario_pnl_0_85K_cny, scenario_pnl_0_85K_pct,
    unhedged_pnl_0_85K, unhedged_pnl_0_85K_pct,
    -- 公共情景盈亏: S_T = 0.90K
    scenario_pnl_0_90K, scenario_pnl_0_90K_cny, scenario_pnl_0_90K_pct,
    unhedged_pnl_0_90K, unhedged_pnl_0_90K_pct,
    -- 公共情景盈亏: S_T = 0.95K
    scenario_pnl_0_95K, scenario_pnl_0_95K_cny, scenario_pnl_0_95K_pct,
    unhedged_pnl_0_95K, unhedged_pnl_0_95K_pct,
    -- 公共情景盈亏: S_T = 1.00K
    scenario_pnl_1_00K, scenario_pnl_1_00K_cny, scenario_pnl_1_00K_pct,
    unhedged_pnl_1_00K, unhedged_pnl_1_00K_pct,
    -- 公共情景盈亏: S_T = 1.03K
    scenario_pnl_1_03K, scenario_pnl_1_03K_cny, scenario_pnl_1_03K_pct,
    unhedged_pnl_1_03K, unhedged_pnl_1_03K_pct,
    -- 公共情景盈亏: S_T = 1.05K
    scenario_pnl_1_05K, scenario_pnl_1_05K_cny, scenario_pnl_1_05K_pct,
    unhedged_pnl_1_05K, unhedged_pnl_1_05K_pct,
    -- 公共情景盈亏: S_T = 1.10K
    scenario_pnl_1_10K, scenario_pnl_1_10K_cny, scenario_pnl_1_10K_pct,
    unhedged_pnl_1_10K, unhedged_pnl_1_10K_pct,
    -- 交易信号
    trade_signal, signal_reason
FROM indexsysdb.tb_option_trading_strategy_covered_call;

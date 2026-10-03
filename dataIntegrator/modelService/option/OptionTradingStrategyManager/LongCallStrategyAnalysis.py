r"""
Long Call（牛市买购）策略分析 — 高级交易员/风控视角

策略定义：买入认购期权 Call(K)，支付权利金 C（单腿买方，经典牛市策略）
组合到期价值 = max(0, S_T - K) - C，上行收益无限，下行最大亏损 = C（权利金）

买方三问（与 Covered Call 对偶——付保费买"便宜的杠杆"）：
  1. 花了多少（买方成本）：premium_ratio_pct / annualized_premium_cost_pct / theta_cost_*
  2. 涨多少回本（盈亏平衡）：breakeven_S_T / breakeven_required_upside_pct
  3. 撬了多少（杠杆弹性）：capital_leverage / delta_leverage / effective_delta_exposure

数据源：
  - tb_tushare_opt_daily_indicator : 现货价、BS定价、Greeks（原料）
  - df_tushare_opt_basic           : symbol/name 反查（ETF 期权 ts_code 为8位数字）

落库：
  - tb_option_trading_strategy_long_call : strategy_type='LONG_CALL'，
    每行带 analysis_time / analysis_params / analysis_version

使用（symbol 直接指定标的+方向+到期月）：
  config = {
      "name": "华夏上证50ETF认购期权（Long Call 牛市买购）",
      "start_date": "20251222",
      "end_date": CommonParameters.today,
      "call_put": "C",
      "symbol_filter": "510050C2612%",
  }
  LongCallStrategyAnalysis().run(config)
"""

import numpy as np
import pandas as pd

from dataIntegrator import CommonLib
from dataIntegrator.modelService.option.OptionTradingStrategyManager.OptionStrategyBase import OptionStrategyBase

logger = CommonLib.logger


class LongCallStrategyAnalysis(OptionStrategyBase):
    """Long Call（牛市买购）策略分析器（买入认购，单腿买方）

    分析维度：买方成本、盈亏平衡、风险结构、杠杆弹性、多情景盈亏（含现货对照）。
    """

    # === 策略标识 ===
    STRATEGY_TYPE = 'LONG_CALL'
    ANALYSIS_VERSION = 'v1'
    TABLE_TARGET = 'tb_option_trading_strategy_long_call'

    # === 目标表字段（与 tb_option_trading_strategy_long_call.sql 建表一致） ===
    TARGET_COLUMNS = [
        # 策略标识与审计
        'strategy_type', 'analysis_time', 'analysis_params', 'analysis_version',
        # 合约标识
        'trade_date', 'ts_code', 'symbol', 'opt_name', 'opt_exchange', 'call_put',
        # 合约要素
        'exercise_price', 'opt_multiplier', 's_month', 'maturity_date', 'days_to_maturity',
        # 标的市场
        'spot_price', 'moneyness_status', 'risk_free_rate', 'dividend_yield',
        # 期权行情与定价
        'premium', 'implied_vol', 'iv_rank',
        'delta', 'gamma', 'theta', 'vega',
        'bs_theoretical_price', 'close_vs_theoretical', 'close_vs_theoretical_pct', 'price_bias',
        # 买方成本（花了多少）
        'premium_ratio_pct', 'annualized_premium_cost_pct',
        'theta_cost_daily', 'theta_cost_total', 'theta_cost_pct_of_premium',
        # 盈亏平衡（涨多少回本）
        'breakeven_S_T', 'breakeven_required_upside_pct',
        # 风险结构（亏得起多少）
        'max_loss', 'max_loss_cny', 'max_loss_pct_of_spot', 'itm_prob',
        # 杠杆（撬了多少）
        'capital_leverage', 'delta_leverage', 'effective_delta_exposure',
        # 多情景盈亏（上行为主）
        'scenario_pnl_0_90K', 'scenario_pnl_0_90K_cny', 'scenario_pnl_0_90K_pct',
        'unhedged_pnl_0_90K', 'unhedged_pnl_0_90K_pct',
        'scenario_pnl_0_95K', 'scenario_pnl_0_95K_cny', 'scenario_pnl_0_95K_pct',
        'unhedged_pnl_0_95K', 'unhedged_pnl_0_95K_pct',
        'scenario_pnl_1_00K', 'scenario_pnl_1_00K_cny', 'scenario_pnl_1_00K_pct',
        'unhedged_pnl_1_00K', 'unhedged_pnl_1_00K_pct',
        'scenario_pnl_1_03K', 'scenario_pnl_1_03K_cny', 'scenario_pnl_1_03K_pct',
        'unhedged_pnl_1_03K', 'unhedged_pnl_1_03K_pct',
        'scenario_pnl_1_05K', 'scenario_pnl_1_05K_cny', 'scenario_pnl_1_05K_pct',
        'unhedged_pnl_1_05K', 'unhedged_pnl_1_05K_pct',
        'scenario_pnl_1_10K', 'scenario_pnl_1_10K_cny', 'scenario_pnl_1_10K_pct',
        'unhedged_pnl_1_10K', 'unhedged_pnl_1_10K_pct',
        'scenario_pnl_1_15K', 'scenario_pnl_1_15K_cny', 'scenario_pnl_1_15K_pct',
        'unhedged_pnl_1_15K', 'unhedged_pnl_1_15K_pct',
        'scenario_pnl_1_20K', 'scenario_pnl_1_20K_cny', 'scenario_pnl_1_20K_pct',
        'unhedged_pnl_1_20K', 'unhedged_pnl_1_20K_pct',
        # 上行捕获
        'upside_capture',
        # 交易信号
        'trade_signal', 'signal_reason',
    ]

    # === 情景系数（上行为主，牛市策略收益端在上行显现） ===
    DEFAULT_SCENARIOS = [0.90, 0.95, 1.00, 1.03, 1.05, 1.10, 1.15, 1.20]

    # === 杠杆效果参考情景 ===
    UPSIDE_CAPTURE_FACTOR = 1.10

    # ================================================================
    # Step 4: 核心策略盈亏（买方三问）
    # ================================================================
    def calc_strategy_pnl(self, df):
        """Long Call 核心盈亏指标

        组合: 多 Call(K, 付权利金C)
        到期 P&L = max(0, S_T - K) - C，盈亏平衡点 = K + C，最大亏损 = C
        """
        logger.info("Calculating Long Call strategy P&L metrics...")

        S = df['spot_price'].values
        K = df['exercise_price'].values
        C = df['close'].values                      # Call 权利金（买方所付）
        mult = df['opt_multiplier'].values
        days = df['days_to_maturity'].values.astype(float)
        years = df['years_to_maturity_calendar'].values.astype(float)
        delta = df['delta'].values.astype(float)    # Call delta > 0
        theta = df['theta'].values.astype(float)    # 买方 theta < 0，成本 = |theta|
        bs = df['bs_theoretical_price'].values.astype(float)

        df['premium'] = C

        # ---------- 1. 买方成本（花了多少） ----------
        # 权利金占现价比例：每一份"现货敞口"支付的成本
        df['premium_ratio_pct'] = np.where(S > 0, C / S * 100, np.nan)
        # 年化权利金成本：滚动续买（到期换下月）的真实成本口径
        df['annualized_premium_cost_pct'] = np.where(
            (S > 0) & (years > 0), C / S / years * 100, np.nan
        )
        # 时间衰减成本（买方支付 theta）
        df['theta_cost_daily'] = np.abs(theta)
        df['theta_cost_total'] = np.where(
            pd.notna(theta) & pd.notna(days), np.abs(theta) * days, np.nan
        )
        df['theta_cost_pct_of_premium'] = np.where(
            (C > 0) & pd.notna(df['theta_cost_total']),
            df['theta_cost_total'] / C * 100, np.nan
        )

        # ---------- 2. 盈亏平衡（涨多少回本） ----------
        # 到期 S_T = K + C 时买方打平
        df['breakeven_S_T'] = np.where(
            pd.notna(K) & pd.notna(C), K + C, np.nan
        )
        # 回本所需涨幅（相对现价）：越小说明买方越"占便宜"
        df['breakeven_required_upside_pct'] = np.where(
            S > 0, (K + C - S) / S * 100, np.nan
        )

        # ---------- 3. 风险结构（亏得起多少） ----------
        # 最大亏损（S_T <= K 时权利金全损）
        df['max_loss'] = np.where(pd.notna(C), C, np.nan)
        df['max_loss_cny'] = df['max_loss'] * mult
        df['max_loss_pct_of_spot'] = np.where(S > 0, C / S * 100, np.nan)
        # 到期实值概率近似：delta = N(d1) ≈ P(S_T > K)
        df['itm_prob'] = delta

        # ---------- 4. 杠杆（撬了多少） ----------
        # 资金杠杆：同等敞口，买权 vs 买现货的资金占用比
        df['capital_leverage'] = np.where(
            (S > 0) & (C > 0), S / C, np.nan
        )
        # 弹性杠杆：现货涨1%时买方资金收益率(%)
        df['delta_leverage'] = np.where(
            (S > 0) & (C > 0) & pd.notna(delta), delta * S / C, np.nan
        )
        # 有效方向敞口
        df['effective_delta_exposure'] = delta

        # ---------- 5. 市价 vs BS 理论价（买入价低于理论价 = 买方有利） ----------
        df['close_vs_theoretical'] = np.where(
            pd.notna(bs) & pd.notna(C), C - bs, np.nan
        )
        df['close_vs_theoretical_pct'] = np.where(
            pd.notna(bs) & (bs > 0), (C - bs) / bs * 100, np.nan
        )
        df['price_bias'] = np.select(
            [
                df['close_vs_theoretical_pct'] < -5,
                (df['close_vs_theoretical_pct'] >= -5) & (df['close_vs_theoretical_pct'] < -1),
                (df['close_vs_theoretical_pct'] >= -1) & (df['close_vs_theoretical_pct'] <= 1),
                (df['close_vs_theoretical_pct'] > 1) & (df['close_vs_theoretical_pct'] <= 5),
                df['close_vs_theoretical_pct'] > 5,
            ],
            ['严重低估', '低估', '公允', '高估', '严重高估'],
            default='N/A'
        )

        # ---------- 摘要日志 ----------
        logger.info(f"Strategy P&L calculated for {len(df)} rows")
        valid = df['capital_leverage'].notna().sum()
        if valid > 0:
            logger.info(f"  capital_leverage: mean={df['capital_leverage'].mean():.1f}x, "
                        f"max={df['capital_leverage'].max():.1f}x")
            logger.info(f"  premium_ratio_pct: mean={df['premium_ratio_pct'].mean():.2f}%")
            logger.info(f"  breakeven_required_upside_pct: mean={df['breakeven_required_upside_pct'].mean():.2f}%")
        return df

    # ================================================================
    # Step 5: 多情景盈亏（含现货对照）
    # ================================================================
    def calc_scenario_pnl(self, df, scenarios=None):
        """多情景盈亏：S_T = K * factor

        买方 P&L   = max(0, S_T - K) - C
        现货对照   = S_T - S0（对照组，衡量杠杆效率与下行亏损差异）
        收益率基准 = 投入资金 C（权利金，买方资金收益率）

        upside_capture 在 1.10K 情景计算：买方盈亏 / 现货盈亏，
        > 1 = 杠杆跑赢直接买现货。
        """
        if scenarios is None:
            scenarios = self.DEFAULT_SCENARIOS

        logger.info(f"Calculating multi-scenario P&L for {len(scenarios)} scenarios: {scenarios}")

        S = df['spot_price'].values
        K = df['exercise_price'].values
        C = df['close'].values
        mult = df['opt_multiplier'].values

        for factor in scenarios:
            s_T = K * factor

            # 买方盈亏
            call_payoff = np.maximum(s_T - K, 0)
            long_call_pnl = call_payoff - C
            long_call_pnl_cny = long_call_pnl * mult
            # 收益率分母 = 权利金 C（买方投入）
            long_call_pnl_pct = np.where(
                C > 0, long_call_pnl / C * 100, np.nan
            )

            # 现货对照（直接买现货）
            unhedged_pnl = s_T - S
            unhedged_pnl_pct = np.where(S > 0, unhedged_pnl / S * 100, np.nan)

            label = f'{factor:.2f}'.replace('.', '_')
            df[f'scenario_pnl_{label}K'] = long_call_pnl
            df[f'scenario_pnl_{label}K_cny'] = long_call_pnl_cny
            df[f'scenario_pnl_{label}K_pct'] = long_call_pnl_pct
            df[f'unhedged_pnl_{label}K'] = unhedged_pnl
            df[f'unhedged_pnl_{label}K_pct'] = unhedged_pnl_pct

        # 上行捕获率（1.10K 情景）：买方盈亏 / 现货盈亏（同单位口径）
        cap_label = f'{self.UPSIDE_CAPTURE_FACTOR:.2f}'.replace('.', '_')
        long_call = df[f'scenario_pnl_{cap_label}K'].values
        unhedged = df[f'unhedged_pnl_{cap_label}K'].values
        df['upside_capture'] = np.where(
            (unhedged > 0) & pd.notna(long_call) & pd.notna(unhedged),
            long_call / unhedged, np.nan
        )

        valid = df['upside_capture'].notna().sum()
        if valid > 0:
            logger.info(f"  upside_capture(1.10K): mean={df['upside_capture'].mean():.2f}, "
                        f"median={df['upside_capture'].median():.2f}")
        logger.info("Multi-scenario P&L calculated")
        return df

    # ================================================================
    # Step 6: 交易信号（买方视角：IV 便宜 + 杠杆足 = 好买购）
    # ================================================================
    def _assign_trade_signals(self, df):
        """分配交易信号

        综合三个维度（与 Covered Call 相反——找"便宜的杠杆"买入）：
          1. capital_leverage：资金杠杆，越高买方越划算
          2. iv_rank：IV 分位，越低买方越有利（与备兑相反）
          3. close_vs_theoretical_pct：定价偏差，负值 = Call 被低估（买方有利）
        """
        leverage = df['capital_leverage'].values
        ivr = df['iv_rank'].values
        bias = df['close_vs_theoretical_pct'].values
        days = df['days_to_maturity'].values
        dlt = df['delta'].values
        ann_cost = df['annualized_premium_cost_pct'].values

        signals = np.full(len(df), 'AVOID', dtype=object)
        signal_reasons = np.full(len(df), '', dtype=object)

        for i in range(len(df)):
            lev_i = leverage[i]
            ivr_i = ivr[i]
            bias_i = bias[i]
            days_i = days[i]
            d_i = dlt[i]
            ac_i = ann_cost[i]

            if pd.isna(lev_i):
                signals[i] = 'N/A'
                signal_reasons[i] = '数据不足'
                continue

            reasons = []

            if (not pd.isna(ivr_i)) and (not pd.isna(bias_i)) \
                    and lev_i >= 15 and ivr_i <= 0.35 and bias_i < -1:
                signals[i] = 'STRONG_BUY'
                reasons.append(f'资金杠杆={lev_i:.1f}x>=15')
                reasons.append(f'IV分位={ivr_i:.2f}<=0.35(买方定价有利)')
                reasons.append(f'Call低估{bias_i:.1f}%')
            elif (not pd.isna(ivr_i)) and lev_i >= 10 and ivr_i <= 0.50:
                signals[i] = 'BUY'
                reasons.append(f'资金杠杆={lev_i:.1f}x>=10')
                reasons.append(f'IV分位={ivr_i:.2f}<=0.50')
            elif lev_i >= 5:
                signals[i] = 'CONSIDER'
                reasons.append(f'资金杠杆={lev_i:.1f}x>=5(可小仓位参与)')
            elif lev_i >= 3:
                signals[i] = 'NEUTRAL'
                reasons.append(f'资金杠杆={lev_i:.1f}x(实值程度高, 性价比一般)')
            else:
                signals[i] = 'AVOID'
                reasons.append(f'资金杠杆={lev_i:.1f}x<3(权利金太贵, 不如持有现货)')

            # 补充风控理由
            if pd.notna(ivr_i) and ivr_i > 0.80:
                reasons.append(f'IV分位={ivr_i:.2f}>0.8(高位买波, 权利金贵)')
            if pd.notna(bias_i) and bias_i > 5:
                reasons.append('Call市价严重高于理论价(买贵)')
            if pd.notna(days_i) and days_i < 14:
                reasons.append(f'仅剩{days_i:.0f}天到期, theta衰减加速, 建议换远月')
            if pd.notna(d_i) and d_i < 0.10:
                reasons.append(f'delta={d_i:.2f}<0.10(深度虚值, 彩票合约)')
            if pd.notna(ac_i) and ac_i > 30:
                reasons.append(f'年化权利金成本={ac_i:.1f}%>30%(续买成本过高)')

            signal_reasons[i] = '; '.join(reasons)

        df['trade_signal'] = signals
        df['signal_reason'] = signal_reasons

        signal_counts = pd.Series(signals).value_counts()
        logger.info(f"Trade signals: {signal_counts.to_dict()}")

        return df

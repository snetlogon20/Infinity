r"""
Covered Call（备兑开仓）策略分析 — 高级交易员/风控视角

策略定义：持有现货 S0 + 卖出认购期权 Call(K)，收取权利金 C
组合到期价值 = S_T - max(0, S_T - K) + C，上行封顶于 K+C，下行有权利金缓冲 C

风控三问（与 Protective Put 对偶，方向相反——卖保险收保费）：
  1. 让了多少（上行封顶）：max_profit / upside_cap / upside_giveup_pct
  2. 保了多少（下行缓冲）：premium_cushion / downside_breakeven_S_T / max_loss / cushion_effect
  3. 赚了多少（收益增强）：premium_yield_pct / annualized_premium_yield_pct / theta_income_*

数据源：
  - tb_tushare_opt_daily_indicator : 现货价、BS定价、Greeks（原料）
  - df_tushare_opt_basic           : symbol/name 反查（ETF 期权 ts_code 为8位数字）

落库：
  - tb_option_trading_strategy_covered_call : strategy_type='COVERED_CALL'，
    每行带 analysis_time / analysis_params / analysis_version

使用（symbol 直接指定标的+方向+到期月）：
  config = {
      "name": "华夏上证50ETF认购期权（Covered Call）",
      "start_date": "20251222",
      "end_date": CommonParameters.today,
      "call_put": "C",
      "symbol_filter": "510050C2612%",
  }
  CoveredCallStrategyAnalysis().run(config)
"""

import numpy as np
import pandas as pd

from dataIntegrator import CommonLib
from dataIntegrator.modelService.option.OptionTradingStrategyManager.OptionStrategyBase import OptionStrategyBase

logger = CommonLib.logger


class CoveredCallStrategyAnalysis(OptionStrategyBase):
    """Covered Call 策略分析器（现货 + 卖出认购）

    分析维度：上行封顶、下行缓冲、收益增强、对冲后残余敞口、多情景盈亏（含未备兑对照）。
    """

    # === 策略标识 ===
    STRATEGY_TYPE = 'COVERED_CALL'
    ANALYSIS_VERSION = 'v1'
    TABLE_TARGET = 'tb_option_trading_strategy_covered_call'

    # === 目标表字段（与 tb_option_trading_strategy_covered_call.sql 建表一致） ===
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
        # 上行封顶（让了多少）
        'max_profit', 'max_profit_cny', 'max_profit_pct_of_spot',
        'upside_cap_S_T', 'upside_giveup_pct',
        # 下行缓冲（保了多少）
        'premium_cushion', 'premium_cushion_pct_of_spot',
        'downside_breakeven_S_T', 'downside_breakeven_S_T_pct',
        'max_loss', 'max_loss_cny', 'max_loss_pct_of_spot', 'cushion_effect',
        # 收益增强（赚了多少）
        'premium_yield_pct', 'annualized_premium_yield_pct',
        'theta_income_daily', 'theta_income_total', 'theta_income_pct_of_premium',
        'assignment_prob',
        # 对冲后敞口
        'portfolio_delta', 'residual_exposure_pct',
        # 多情景盈亏（上行为主）
        'scenario_pnl_0_85K', 'scenario_pnl_0_85K_cny', 'scenario_pnl_0_85K_pct',
        'unhedged_pnl_0_85K', 'unhedged_pnl_0_85K_pct',
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
        # 交易信号
        'trade_signal', 'signal_reason',
    ]

    # === 情景系数（上行为主，封顶效果在上行端显现） ===
    DEFAULT_SCENARIOS = [0.85, 0.90, 0.95, 1.00, 1.03, 1.05, 1.10, 1.15]

    # === 缓冲效果参考情景 ===
    CUSHION_EFFECT_FACTOR = 0.95

    # ================================================================
    # Step 4: 核心策略盈亏（风控三问）
    # ================================================================
    def calc_strategy_pnl(self, df):
        """Covered Call 核心盈亏指标

        组合: 多现货 S0 + 空 Call(K, 收权利金C)
        到期组合价值 = S_T - max(0, S_T-K) + C，恒 <= K + C（上行封顶）
        组合到期 P&L = (S_T - S0) - max(0, S_T-K) + C，最大值 = K - S0 + C
        """
        logger.info("Calculating Covered Call strategy P&L metrics...")

        S = df['spot_price'].values
        K = df['exercise_price'].values
        C = df['close'].values                      # Call 权利金（卖出所收）
        mult = df['opt_multiplier'].values
        days = df['days_to_maturity'].values.astype(float)
        years = df['years_to_maturity_calendar'].values.astype(float)
        delta = df['delta'].values.astype(float)    # Call delta > 0
        theta = df['theta'].values.astype(float)    # 买方 theta < 0，卖方收入 = |theta|
        bs = df['bs_theoretical_price'].values.astype(float)

        df['premium'] = C

        # ---------- 1. 上行封顶（让了多少） ----------
        # S_T >= K 时组合价值封顶于 K + C，最大盈利 = K - S0 + C
        df['max_profit'] = np.where(S > 0, K - S + C, np.nan)
        df['max_profit_cny'] = df['max_profit'] * mult
        df['max_profit_pct_of_spot'] = np.where(
            S > 0, (K - S + C) / S * 100, np.nan
        )
        # 上行封顶点 = K
        df['upside_cap_S_T'] = K
        # 上行让渡：超过 K 的涨幅全部放弃（以 K 相对 S0 的涨幅计）
        df['upside_giveup_pct'] = np.where(S > 0, (K - S) / S * 100, np.nan)

        # ---------- 2. 下行缓冲（保了多少） ----------
        # 权利金缓冲：下跌 C 以内组合不亏
        df['premium_cushion'] = C
        df['premium_cushion_pct_of_spot'] = np.where(S > 0, C / S * 100, np.nan)
        # 下行盈亏平衡点：跌至 S0 - C 以下组合开始亏损
        df['downside_breakeven_S_T'] = np.where(S > 0, S - C, np.nan)
        df['downside_breakeven_S_T_pct'] = np.where(S > 0, -C / S * 100, np.nan)
        # 最大亏损（S_T = 0）：现货全亏但保留权利金
        df['max_loss'] = np.where(S > 0, C - S, np.nan)
        df['max_loss_cny'] = df['max_loss'] * mult
        df['max_loss_pct_of_spot'] = np.where(S > 0, (C - S) / S * 100, np.nan)

        # ---------- 3. 收益增强（赚了多少） ----------
        # 静态收益率：持有到期不轧平的"租金收益"
        df['premium_yield_pct'] = np.where(S > 0, C / S * 100, np.nan)
        # 年化静态收益率
        df['annualized_premium_yield_pct'] = np.where(
            (S > 0) & (years > 0), C / S / years * 100, np.nan
        )
        # 时间衰减收入（卖方收取 theta）
        df['theta_income_daily'] = np.abs(theta)
        df['theta_income_total'] = np.where(
            pd.notna(theta) & pd.notna(days), np.abs(theta) * days, np.nan
        )
        df['theta_income_pct_of_premium'] = np.where(
            (C > 0) & pd.notna(df['theta_income_total']),
            df['theta_income_total'] / C * 100, np.nan
        )
        # 被行权概率近似：delta = N(d1) ≈ P(S_T > K)
        df['assignment_prob'] = delta

        # ---------- 4. 对冲后残余敞口 ----------
        # 组合净 Delta = 1 - delta_call（卖 Call 削减上行敞口）
        df['portfolio_delta'] = np.where(
            pd.notna(delta), 1 - delta, np.nan
        )
        df['residual_exposure_pct'] = np.where(
            pd.notna(delta), (1 - delta) * 100, np.nan
        )

        # ---------- 5. 市价 vs BS 理论价（卖出价高于理论价 = 卖方有利） ----------
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
        valid = df['premium_yield_pct'].notna().sum()
        if valid > 0:
            logger.info(f"  premium_yield_pct: mean={df['premium_yield_pct'].mean():.2f}%, "
                        f"max={df['premium_yield_pct'].max():.2f}%")
            logger.info(f"  max_profit_pct_of_spot: mean={df['max_profit_pct_of_spot'].mean():.2f}%, "
                        f"best={df['max_profit_pct_of_spot'].max():.2f}%")
            logger.info(f"  premium_cushion_pct: mean={df['premium_cushion_pct_of_spot'].mean():.2f}%")
        return df

    # ================================================================
    # Step 5: 多情景盈亏（含未备兑对照）
    # ================================================================
    def calc_scenario_pnl(self, df, scenarios=None):
        """多情景盈亏：S_T = K * factor

        备兑组合 P&L = (S_T - S0) - max(0, S_T - K) + C
        未备兑 P&L   = S_T - S0（对照组，衡量封顶让渡与下行缓冲）
        收益率基准 = 投入资金 S0（权利金为收入，不占用本金）

        cushion_effect 在 0.95K 情景计算：(未对冲亏损 - 对冲后亏损) / 未对冲亏损，
        1 = 亏损被权利金完全吸收。
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

            # 备兑组合盈亏
            call_payoff = np.maximum(s_T - K, 0)
            covered_pnl = (s_T - S) - call_payoff + C
            covered_pnl_cny = covered_pnl * mult
            covered_pnl_pct = np.where(
                (S > 0) & (C >= 0), covered_pnl / S * 100, np.nan
            )

            # 未备兑对照
            unhedged_pnl = s_T - S
            unhedged_pnl_pct = np.where(S > 0, unhedged_pnl / S * 100, np.nan)

            label = f'{factor:.2f}'.replace('.', '_')
            df[f'scenario_pnl_{label}K'] = covered_pnl
            df[f'scenario_pnl_{label}K_cny'] = covered_pnl_cny
            df[f'scenario_pnl_{label}K_pct'] = covered_pnl_pct
            df[f'unhedged_pnl_{label}K'] = unhedged_pnl
            df[f'unhedged_pnl_{label}K_pct'] = unhedged_pnl_pct

        # 缓冲效果（0.95K 情景）：权利金吸收亏损的比例
        cap_label = f'{self.CUSHION_EFFECT_FACTOR:.2f}'.replace('.', '_')
        covered = df[f'scenario_pnl_{cap_label}K'].values
        unhedged = df[f'unhedged_pnl_{cap_label}K'].values
        df['cushion_effect'] = np.where(
            (unhedged < 0) & pd.notna(covered) & pd.notna(unhedged),
            (unhedged - covered) / np.abs(unhedged),
            np.nan
        )

        valid = df['cushion_effect'].notna().sum()
        if valid > 0:
            logger.info(f"  cushion_effect(0.95K): mean={df['cushion_effect'].mean():.2f}, "
                        f"median={df['cushion_effect'].median():.2f}")
        logger.info("Multi-scenario P&L calculated")
        return df

    # ================================================================
    # Step 6: 交易信号（卖方视角：IV 贵 + 收益厚 = 好备兑）
    # ================================================================
    def _assign_trade_signals(self, df):
        """分配交易信号

        综合三个维度（与 Protective Put 相反——找"贵的保险"卖出）：
          1. premium_yield_pct：静态收益率，越高备兑越划算
          2. iv_rank：IV 分位，越高卖方越有利（与买保护相反）
          3. close_vs_theoretical_pct：定价偏差，正值 = Call 被高估（卖方有利）
        """
        yield_pct = df['premium_yield_pct'].values
        ivr = df['iv_rank'].values
        bias = df['close_vs_theoretical_pct'].values
        days = df['days_to_maturity'].values
        assign_prob = df['assignment_prob'].values
        upside_giveup = df['upside_giveup_pct'].values

        signals = np.full(len(df), 'AVOID', dtype=object)
        signal_reasons = np.full(len(df), '', dtype=object)

        for i in range(len(df)):
            y_i = yield_pct[i]
            ivr_i = ivr[i]
            bias_i = bias[i]
            days_i = days[i]
            ap_i = assign_prob[i]
            ug_i = upside_giveup[i]

            if pd.isna(y_i):
                signals[i] = 'N/A'
                signal_reasons[i] = '数据不足'
                continue

            reasons = []

            if (not pd.isna(ivr_i)) and (not pd.isna(bias_i)) \
                    and y_i >= 2.0 and ivr_i >= 0.65 and bias_i > 1:
                signals[i] = 'STRONG_BUY'
                reasons.append(f'静态收益率={y_i:.2f}%>=2')
                reasons.append(f'IV分位={ivr_i:.2f}>=0.65(卖方定价有利)')
                reasons.append(f'Call高估{bias_i:.1f}%')
            elif (not pd.isna(ivr_i)) and y_i >= 1.5 and ivr_i >= 0.50:
                signals[i] = 'BUY'
                reasons.append(f'静态收益率={y_i:.2f}%>=1.5')
                reasons.append(f'IV分位={ivr_i:.2f}>=0.50')
            elif y_i >= 1.0:
                signals[i] = 'CONSIDER'
                reasons.append(f'静态收益率={y_i:.2f}%>=1.0')
            elif y_i >= 0.5:
                signals[i] = 'NEUTRAL'
                reasons.append(f'静态收益率={y_i:.2f}%')
            else:
                signals[i] = 'AVOID'
                reasons.append(f'静态收益率={y_i:.2f}%<0.5(保费太薄)')

            # 补充风控理由
            if pd.notna(ivr_i) and ivr_i < 0.2:
                reasons.append(f'IV分位={ivr_i:.2f}<0.2(波动率枯竭, 卖方不利)')
            if pd.notna(bias_i) and bias_i < -5:
                reasons.append('Call市价严重低于理论价(卖出吃亏)')
            if pd.notna(days_i) and days_i < 10:
                reasons.append(f'仅剩{days_i:.0f}天到期, Gamma风险高, 建议移仓')
            if pd.notna(ap_i) and ap_i > 0.85:
                reasons.append(f'被行权概率≈{ap_i:.2f}(深度实值, 上行全部让渡)')
            if pd.notna(ug_i) and ug_i < 0.5:
                reasons.append(f'行权价贴近平值(让渡仅{ug_i:.1f}%), 上涨即被行权')

            signal_reasons[i] = '; '.join(reasons)

        df['trade_signal'] = signals
        df['signal_reason'] = signal_reasons

        signal_counts = pd.Series(signals).value_counts()
        logger.info(f"Trade signals: {signal_counts.to_dict()}")

        return df

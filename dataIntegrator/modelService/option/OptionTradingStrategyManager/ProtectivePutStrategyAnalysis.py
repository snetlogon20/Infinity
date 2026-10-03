r"""
Protective Put（保护性认沽）策略分析 — 高级交易员/风控视角

策略定义：持有现货 S0 + 买入认沽期权 Put(K)，支付权利金 P
组合到期价值 = S_T + max(0, K - S_T) - P - S0

风控三问：
  1. 保了多少（下行保护）：protected_floor / max_loss / protection_per_cost / downside_capture
  2. 花了多少（对冲成本）：hedge_cost_ratio / annualized_hedge_cost / theta_cost_*
  3. 让了多少（上行代价）：breakeven_S_T / upside_giveup_pct

数据源：
  - tb_tushare_opt_daily_indicator : 现货价、BS定价、Greeks（原料）
  - df_tushare_opt_basic           : symbol/name 反查（ETF 期权 ts_code 为8位数字）

落库：
  - tb_option_trading_strategy_protective_put : strategy_type='PROTECTIVE_PUT'，
                                     每行带 analysis_time / analysis_params / analysis_version
  - 跨策略查询走 vw_option_trading_strategy_union 联合视图

使用（symbol 直接指定标的+方向+到期月，如华夏上证50ETF 2612 认沽）：
  config = {
      "name": "华夏上证50ETF认沽期权（Protective Put）",
      "start_date": "20251222",
      "end_date": CommonParameters.today,
      "call_put": "P",
      "symbol_filter": "510050P2612%",
  }
  ProtectivePutStrategyAnalysis().run(config)
"""

import numpy as np
import pandas as pd

from dataIntegrator import CommonLib
from dataIntegrator.modelService.option.OptionTradingStrategyManager.OptionStrategyBase import OptionStrategyBase

logger = CommonLib.logger


class ProtectivePutStrategyAnalysis(OptionStrategyBase):
    """Protective Put 策略分析器（现货 + 买入认沽）

    分析维度：下行保护、对冲成本、上行代价、对冲后残余敞口、多情景盈亏（含未对冲对照）。
    """

    # === 策略标识 ===
    STRATEGY_TYPE = 'PROTECTIVE_PUT'
    ANALYSIS_VERSION = 'v1'

    # === 目标专表（基类 TABLE_TARGET 已抽象化，必须显式指定） ===
    TABLE_TARGET = 'tb_option_trading_strategy_protective_put'

    # === 目标表字段（与 tb_option_trading_strategy_protective_put.sql 建表一致） ===
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
        # 下行保护（保了多少）
        'protected_floor', 'protected_floor_pct_of_spot',
        'max_loss', 'max_loss_cny', 'max_loss_pct_of_spot',
        'protection_per_cost', 'downside_capture',
        # 对冲成本（花了多少）
        'hedge_cost_ratio', 'annualized_hedge_cost_pct',
        'theta_cost_daily', 'theta_cost_total', 'theta_cost_pct_of_premium',
        # 上行代价（让了多少）
        'breakeven_S_T', 'breakeven_S_T_pct', 'upside_giveup_pct',
        # 对冲后敞口
        'portfolio_delta', 'residual_exposure_pct',
        # 多情景盈亏（下行为主 + 少量上行）
        'scenario_pnl_0_80K', 'scenario_pnl_0_80K_cny', 'scenario_pnl_0_80K_pct',
        'unhedged_pnl_0_80K', 'unhedged_pnl_0_80K_pct',
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
        # 交易信号
        'trade_signal', 'signal_reason',
    ]

    # === 情景系数（下行为主） ===
    DEFAULT_SCENARIOS = [0.80, 0.85, 0.90, 0.95, 1.00, 1.03, 1.05, 1.10]

    # === 下跌捕获率参考情景 ===
    DOWNSIDE_CAPTURE_FACTOR = 0.90

    # === 信号阈值 ===
    SIGNAL_MAP = {
        'STRONG_BUY': ('强烈买入', 'FF0000'),   # 便宜买保护：ppc高 + iv_rank低 + put低估
        'BUY':        ('买入', 'FF6600'),
        'CONSIDER':   ('关注', 'FF9900'),
        'NEUTRAL':    ('中性', '808080'),
        'AVOID':      ('回避', '3399FF'),       # 保险贵且保护弱
    }

    # ================================================================
    # Step 4: 核心策略盈亏（风控三问）
    # ================================================================
    def calc_strategy_pnl(self, df):
        """Protective Put 核心盈亏指标

        组合: 多现货 S0 + 多 Put(K, 权利金P)
        到期组合价值 = S_T + max(0, K-S_T)，最小值 = K（S_T<=K 时 Put 补齐差额）
        组合到期 P&L = S_T + max(0, K-S_T) - P - S0，最小值 = K - P - S0（价值硬底）
        """
        logger.info("Calculating Protective Put strategy P&L metrics...")

        S = df['spot_price'].values
        K = df['exercise_price'].values
        P = df['close'].values                      # Put 权利金
        mult = df['opt_multiplier'].values
        days = df['days_to_maturity'].values.astype(float)
        years = df['years_to_maturity_calendar'].values.astype(float)
        delta = df['delta'].values.astype(float)    # Put delta < 0
        theta = df['theta'].values.astype(float)
        bs = df['bs_theoretical_price'].values.astype(float)

        df['premium'] = P

        # ---------- 1. 下行保护（保了多少） ----------
        # 价值硬底：S_T<=K 时组合价值恒为 K，扣除权利金后 = K-P
        df['protected_floor'] = np.where(K > 0, K - P, np.nan)
        df['protected_floor_pct_of_spot'] = np.where(
            S > 0, (K - P) / S * 100, np.nan
        )
        # 最大亏损（对冲后最大回撤）= K - P - S0
        df['max_loss'] = np.where(S > 0, K - P - S, np.nan)
        df['max_loss_cny'] = df['max_loss'] * mult
        df['max_loss_pct_of_spot'] = np.where(
            S > 0, (K - P - S) / S * 100, np.nan
        )
        # 保险杠杆：每 1 元保费锁定的下行价值 = (K-P)/P
        df['protection_per_cost'] = np.where(
            P > 0, (K - P) / P, np.nan
        )

        # ---------- 2. 对冲成本（花了多少） ----------
        df['hedge_cost_ratio'] = np.where(S > 0, P / S, np.nan)
        # 年化对冲成本：滚动续保的真实成本
        df['annualized_hedge_cost_pct'] = np.where(
            (S > 0) & (years > 0), P / S / years * 100, np.nan
        )
        # 时间衰减成本
        df['theta_cost_daily'] = np.abs(theta)
        df['theta_cost_total'] = np.where(
            pd.notna(theta) & pd.notna(days), np.abs(theta) * days, np.nan
        )
        df['theta_cost_pct_of_premium'] = np.where(
            (P > 0) & pd.notna(df['theta_cost_total']),
            df['theta_cost_total'] / P * 100, np.nan
        )

        # ---------- 3. 上行代价（让了多少） ----------
        # 组合上行需涨过 S0+P 才盈利（Put 到期作废，只损失权利金）
        df['breakeven_S_T'] = np.where(S > 0, S + P, np.nan)
        df['breakeven_S_T_pct'] = np.where(S > 0, P / S * 100, np.nan)
        df['upside_giveup_pct'] = np.where(S > 0, P / S * 100, np.nan)

        # ---------- 4. 对冲后残余敞口 ----------
        # 组合净 Delta = 1 + delta_put（剩余方向性风险）
        df['portfolio_delta'] = np.where(
            pd.notna(delta), 1 + delta, np.nan
        )
        df['residual_exposure_pct'] = np.where(
            pd.notna(delta), (1 + delta) * 100, np.nan
        )

        # ---------- 5. 市价 vs BS 理论价（Put 贵还是便宜） ----------
        df['close_vs_theoretical'] = np.where(
            pd.notna(bs) & pd.notna(P), P - bs, np.nan
        )
        df['close_vs_theoretical_pct'] = np.where(
            pd.notna(bs) & (bs > 0), (P - bs) / bs * 100, np.nan
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
        valid = df['protection_per_cost'].notna().sum()
        if valid > 0:
            logger.info(f"  protection_per_cost: mean={df['protection_per_cost'].mean():.2f}, "
                        f"median={df['protection_per_cost'].median():.2f}")
            logger.info(f"  hedge_cost_ratio: mean={df['hedge_cost_ratio'].mean()*100:.2f}%, "
                        f"max={df['hedge_cost_ratio'].max()*100:.2f}%")
            logger.info(f"  max_loss_pct_of_spot: mean={df['max_loss_pct_of_spot'].mean():.2f}%, "
                        f"worst={df['max_loss_pct_of_spot'].min():.2f}%")
        return df

    # ================================================================
    # Step 5: 多情景盈亏（含未对冲对照）
    # ================================================================
    def calc_scenario_pnl(self, df, scenarios=None):
        """多情景盈亏：S_T = K * factor

        对冲组合 P&L = (S_T - S0) + max(0, K - S_T) - P
        未对冲 P&L   = S_T - S0（对照组，衡量保护效果）
        收益率基准 = 投入资金 (S0 + P)

        downside_capture 在 0.90K 情景计算：对冲后亏损 / 未对冲亏损。
        """
        if scenarios is None:
            scenarios = self.DEFAULT_SCENARIOS

        logger.info(f"Calculating multi-scenario P&L for {len(scenarios)} scenarios: {scenarios}")

        S = df['spot_price'].values
        K = df['exercise_price'].values
        P = df['close'].values
        mult = df['opt_multiplier'].values

        for factor in scenarios:
            s_T = K * factor

            # 对冲组合盈亏
            put_payoff = np.maximum(K - s_T, 0)
            hedged_pnl = (s_T - S) + put_payoff - P
            hedged_pnl_cny = hedged_pnl * mult
            hedged_pnl_pct = np.where(
                (S > 0) & (P >= 0), hedged_pnl / (S + P) * 100, np.nan
            )

            # 未对冲对照
            unhedged_pnl = s_T - S
            unhedged_pnl_pct = np.where(S > 0, unhedged_pnl / S * 100, np.nan)

            label = f'{factor:.2f}'.replace('.', '_')
            df[f'scenario_pnl_{label}K'] = hedged_pnl
            df[f'scenario_pnl_{label}K_cny'] = hedged_pnl_cny
            df[f'scenario_pnl_{label}K_pct'] = hedged_pnl_pct
            df[f'unhedged_pnl_{label}K'] = unhedged_pnl
            df[f'unhedged_pnl_{label}K_pct'] = unhedged_pnl_pct

        # 下跌捕获率（0.90K 情景）：对冲后亏损 / 未对冲亏损
        # 0 = 完全保护；越接近 1 保护越弱
        cap_label = f'{self.DOWNSIDE_CAPTURE_FACTOR:.2f}'.replace('.', '_')
        hedged = df[f'scenario_pnl_{cap_label}K'].values
        unhedged = df[f'unhedged_pnl_{cap_label}K'].values
        df['downside_capture'] = np.where(
            (unhedged < 0) & pd.notna(hedged) & pd.notna(unhedged),
            hedged / unhedged,
            np.nan
        )

        valid = df['downside_capture'].notna().sum()
        if valid > 0:
            logger.info(f"  downside_capture(0.90K): mean={df['downside_capture'].mean():.2f}, "
                        f"median={df['downside_capture'].median():.2f}")
        logger.info("Multi-scenario P&L calculated")
        return df

    # ================================================================
    # Step 6: 交易信号（保险性价比：便宜 + 保护强 = 好对冲）
    # ================================================================
    def _assign_trade_signals(self, df):
        """分配交易信号

        综合三个维度（语义与 Long Call 相反——找"便宜的保险"）：
          1. protection_per_cost：保险杠杆，越高保护越强
          2. iv_rank：IV 分位，越低保险越便宜
          3. close_vs_theoretical_pct：定价偏差，负值 = Put 被低估
        """
        ppc = df['protection_per_cost'].values
        ivr = df['iv_rank'].values
        bias = df['close_vs_theoretical_pct'].values
        days = df['days_to_maturity'].values

        signals = np.full(len(df), 'AVOID', dtype=object)
        signal_reasons = np.full(len(df), '', dtype=object)

        for i in range(len(df)):
            ppc_i = ppc[i]
            ivr_i = ivr[i]
            bias_i = bias[i]
            days_i = days[i]

            if pd.isna(ppc_i):
                signals[i] = 'N/A'
                signal_reasons[i] = '数据不足'
                continue

            reasons = []

            if (not pd.isna(ivr_i)) and (not pd.isna(bias_i)) \
                    and ppc_i >= 3.0 and ivr_i <= 0.35 and bias_i < -1:
                signals[i] = 'STRONG_BUY'
                reasons.append(f'保险杠杆={ppc_i:.1f}>=3')
                reasons.append(f'IV分位={ivr_i:.2f}<=0.35(保险便宜)')
                reasons.append(f'Put低估{bias_i:.1f}%')
            elif (not pd.isna(ivr_i)) and ppc_i >= 2.0 and ivr_i <= 0.55:
                signals[i] = 'BUY'
                reasons.append(f'保险杠杆={ppc_i:.1f}>=2')
                reasons.append(f'IV分位={ivr_i:.2f}<=0.55')
            elif ppc_i >= 1.5:
                signals[i] = 'CONSIDER'
                reasons.append(f'保险杠杆={ppc_i:.1f}>=1.5')
            elif ppc_i >= 1.0:
                signals[i] = 'NEUTRAL'
                reasons.append(f'保险杠杆={ppc_i:.1f}')
            else:
                signals[i] = 'AVOID'
                reasons.append(f'保险杠杆={ppc_i:.1f}<1(保费相对保护过贵)')

            # 补充风控理由
            if pd.notna(ivr_i) and ivr_i > 0.8:
                reasons.append(f'IV分位={ivr_i:.2f}>0.8(恐慌定价, 保险昂贵)')
            if pd.notna(bias_i) and bias_i > 5:
                reasons.append('Put市价严重高于理论价')
            if pd.notna(days_i) and days_i < 10:
                reasons.append(f'仅剩{days_i:.0f}天到期, Gamma风险高, 建议移仓')
            if ppc_i < 0:
                reasons.append('K<P(深度异常, 保护无意义)')

            signal_reasons[i] = '; '.join(reasons)

        df['trade_signal'] = signals
        df['signal_reason'] = signal_reasons

        signal_counts = pd.Series(signals).value_counts()
        logger.info(f"Trade signals: {signal_counts.to_dict()}")

        return df

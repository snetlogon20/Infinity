r"""
Bear Put Spread（熊市看跌价差）策略分析 — 高级交易员/风控视角

策略定义：买入高行权价认沽 Put(K2) + 卖出低行权价认沽 Put(K1)，K1 < K2，同到期月
净支出 D = P2 - P1；组合到期收益 = max(0,K2-S_T) - max(0,K1-S_T) - D
亏损封底 D（S_T>=K2），盈利封顶 (K2-K1)-D（S_T<=K1），盈亏平衡点 K2-D
—— 教科书厂字形（截头镜像版）：牺牲下行无限空间，换取成本下降与盈亏双封顶
是 Bull Call Spread 的完美镜像（方向反转，Put 侧）

组合配对（三层漏斗第1层——约束剪枝，控制组合爆炸）：
  1. 同一到期月（symbol_filter 保证）
  2. 买入腿 K2 限定 ATM ± 1 档（浅实值/平值/浅虚值，教科书标准）
  3. 卖出腿 K1 = K2 下方 1~4 档（控制宽度：太窄利润薄，太宽成本高）
  每日约 3x4=12 个候选组合全量落库（透明可回溯），信号端按综合评分排序

风控三问（价差视角）：
  1. 花了多少（成本）：net_debit / net_debit_pct_of_spot / net_debit_pct_of_width
  2. 最多赚多少（封顶）：max_profit / roi_max_pct / reward_risk_ratio
  3. 多大概率赚（胜率）：win_prob（盈亏平衡点两腿|delta|插值）/ expected_value / score

数据源：
  - tb_tushare_opt_daily_indicator : 现货价、BS定价、Greeks（原料）
  - df_tushare_opt_basic           : symbol/name 反查（ETF 期权 ts_code 为8位数字）

落库：
  - tb_option_trading_strategy_bear_put_spread : strategy_type='BEAR_PUT_SPREAD'，
    每行一个组合（买入腿=高行权价K2 无后缀，卖出腿=低行权价K1 带 _short 后缀）

使用（symbol 直接指定标的+方向+到期月，注意 P）：
  config = {
      "name": "华夏上证50ETF认沽期权（Bear Put Spread）",
      "start_date": "20251222",
      "end_date": CommonParameters.today,
      "call_put": "P",
      "symbol_filter": "510050P2612%",
  }
  BearPutSpreadStrategyAnalysis().run(config)
"""

import numpy as np
import pandas as pd

from dataIntegrator import CommonLib
from dataIntegrator.modelService.option.OptionTradingStrategyManager.OptionStrategyBase import OptionStrategyBase

logger = CommonLib.logger


class BearPutSpreadStrategyAnalysis(OptionStrategyBase):
    """Bear Put Spread 策略分析器（买 Put(K2) + 卖 Put(K1)，熊市看跌价差）

    分析维度：组合配对（约束剪枝）、净支出、盈亏双封顶、胜率与评分排序、
    净 Greeks（theta/vega 抵消优势）、多情景盈亏（含买现货对照）。
    """

    # === 策略标识 ===
    STRATEGY_TYPE = 'BEAR_PUT_SPREAD'
    ANALYSIS_VERSION = 'v1'
    TABLE_TARGET = 'tb_option_trading_strategy_bear_put_spread'

    # === 目标表字段（与 tb_option_trading_strategy_bear_put_spread.sql 建表一致） ===
    TARGET_COLUMNS = [
        # 策略标识与审计
        'strategy_type', 'analysis_time', 'analysis_params', 'analysis_version',
        # 组合标识（买入腿=高行权价K2 无后缀，卖出腿=低行权价K1 带 _short）
        'trade_date', 'ts_code', 'symbol', 'opt_name', 'opt_exchange', 'call_put',
        'ts_code_short', 'symbol_short', 'opt_name_short',
        # 合约要素
        'exercise_price', 'exercise_price_short', 'opt_multiplier', 's_month',
        'maturity_date', 'days_to_maturity',
        # 标的市场
        'spot_price', 'moneyness_status', 'risk_free_rate', 'dividend_yield',
        # 双腿行情与定价
        'premium', 'premium_short', 'implied_vol', 'implied_vol_short',
        'iv_rank', 'iv_rank_short',
        # 双腿 Greeks
        'delta', 'gamma', 'theta', 'vega',
        'delta_short', 'gamma_short', 'theta_short', 'vega_short',
        # 双腿定价偏差
        'bs_theoretical_price', 'close_vs_theoretical', 'close_vs_theoretical_pct', 'price_bias',
        'bs_theoretical_price_short', 'close_vs_theoretical_short',
        'close_vs_theoretical_pct_short', 'price_bias_short',
        # 组合净 Greeks
        'net_delta', 'net_gamma', 'net_theta', 'net_vega',
        # 价差结构（花了多少）
        'spread_width', 'spread_width_pct',
        'net_debit', 'net_debit_cny', 'net_debit_pct_of_spot', 'net_debit_pct_of_width',
        # 收益结构（赚了多少/亏了多少）
        'max_profit', 'max_profit_cny', 'max_profit_pct_of_spot', 'roi_max_pct',
        'max_loss', 'max_loss_cny', 'max_loss_pct_of_spot', 'reward_risk_ratio',
        'breakeven_S_T', 'breakeven_downside_pct',
        # 概率与评分
        'win_prob', 'expected_value', 'score', 'combo_rank',
        # 多情景盈亏（S_T = K2 * factor，含买现货对照）
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

    # === 情景系数（S_T = K2 × factor，下行为主） ===
    DEFAULT_SCENARIOS = [0.85, 0.90, 0.95, 1.00, 1.03, 1.05, 1.10, 1.15]

    # === 组合配对参数（约束剪枝） ===
    LONG_LEG_ATM_RANGE = 1     # 买入腿 K2 限定 ATM ± 1 档
    MAX_WIDTH_STEPS = 4        # 卖出腿 K1 = K2 下方 1~4 档

    # ================================================================
    # Step 4: 组合配对 + 核心策略盈亏（风控三问）
    # ================================================================
    def calc_strategy_pnl(self, df):
        """Bear Put Spread 核心盈亏指标（组合粒度）

        配对: 买入 Put(K2) + 卖出 Put(K1)，K1 < K2，净支出 D = P2 - P1
        到期组合收益 = max(0,K2-S_T) - max(0,K1-S_T) - D
        最大亏损 = D（S_T>=K2），最大盈利 = (K2-K1)-D（S_T<=K1），盈亏平衡 = K2-D
        """
        logger.info("Building bear put spread pairs "
                    f"(long leg ATM±{self.LONG_LEG_ATM_RANGE}档 × width 1~{self.MAX_WIDTH_STEPS}档)...")

        # ---------- 0. 组合配对（约束剪枝：ATM±1档 × 下方1~4档） ----------
        df = self._build_pairs(df)
        if df.empty:
            logger.warning("No bear put spread pairs built, skip P&L calculation")
            return df
        logger.info(f"Built {len(df)} combo rows "
                    f"({df.groupby('trade_date').size().max()} combos/day max)")

        S = df['spot_price'].values.astype(float)
        K2 = df['exercise_price'].values.astype(float)       # 买入腿（高）
        K1 = df['exercise_price_short'].values.astype(float) # 卖出腿（低）
        P2 = df['premium'].values.astype(float)
        P1 = df['premium_short'].values.astype(float)
        mult = df['opt_multiplier'].values.astype(float)

        delta_long = df['delta'].values.astype(float)
        delta_short = df['delta_short'].values.astype(float)

        # ---------- 1. 价差结构（花了多少） ----------
        width = K2 - K1
        D = P2 - P1
        df['spread_width'] = width
        df['spread_width_pct'] = np.where(S > 0, width / S * 100, np.nan)
        df['net_debit'] = D
        df['net_debit_cny'] = D * mult
        df['net_debit_pct_of_spot'] = np.where(S > 0, D / S * 100, np.nan)
        df['net_debit_pct_of_width'] = np.where(width > 0, D / width * 100, np.nan)

        # ---------- 2. 收益结构（赚了多少/亏了多少） ----------
        max_profit = width - D
        df['max_profit'] = max_profit
        df['max_profit_cny'] = max_profit * mult
        df['max_profit_pct_of_spot'] = np.where(S > 0, max_profit / S * 100, np.nan)
        # 最大资金收益率：以净支出 D 为本金（价差的杠杆来源）
        df['roi_max_pct'] = np.where(D > 0, max_profit / D * 100, np.nan)

        df['max_loss'] = D
        df['max_loss_cny'] = D * mult
        df['max_loss_pct_of_spot'] = np.where(S > 0, D / S * 100, np.nan)
        df['reward_risk_ratio'] = np.where(D > 0, max_profit / D, np.nan)

        breakeven = K2 - D
        df['breakeven_S_T'] = breakeven
        # 熊市价差：需下跌至 K2-D 才开始盈利（通常为负值=所需跌幅）
        df['breakeven_downside_pct'] = np.where(S > 0, (breakeven - S) / S * 100, np.nan)

        # ---------- 3. 组合净 Greeks（价差核心优势：theta/vega 抵消） ----------
        # 持仓符号: 买入腿 +1，卖出腿 -1（theta/vega 取负号）
        df['net_delta'] = np.where(pd.notna(delta_long) & pd.notna(delta_short),
                                   delta_long - delta_short, np.nan)
        df['net_gamma'] = np.where(pd.notna(df['gamma']) & pd.notna(df['gamma_short']),
                                   df['gamma'] - df['gamma_short'], np.nan)
        df['net_theta'] = np.where(pd.notna(df['theta']) & pd.notna(df['theta_short']),
                                   df['theta'] - df['theta_short'], np.nan)
        df['net_vega'] = np.where(pd.notna(df['vega']) & pd.notna(df['vega_short']),
                                  df['vega'] - df['vega_short'], np.nan)

        # ---------- 4. 胜率与评分（最佳组合排序） ----------
        # 胜率近似: P(S_T < K2-D)，用两腿 |delta|（≈P(S_T<K)）在盈亏平衡点线性插值
        # B=K2-D 介于 K1 与 K2 之间：从 K1 处的 p_short 插值到 K2 处的 p_long
        p_long = np.abs(delta_long)   # ≈ P(S_T < K2)
        p_short = np.abs(delta_short) # ≈ P(S_T < K1)
        frac = np.where(width > 0, (breakeven - K1) / width, np.nan)
        win_prob = p_short + (p_long - p_short) * frac
        win_prob = np.clip(win_prob, 0.0, 1.0)
        df['win_prob'] = np.where(pd.notna(p_long) & pd.notna(p_short) & pd.notna(frac),
                                  win_prob, np.nan)

        # 期望值 = 胜率×最大盈利 - (1-胜率)×最大亏损；评分 = 期望值/净支出（风险调整）
        wp = df['win_prob'].values.astype(float)
        ev = wp * max_profit - (1 - wp) * D
        df['expected_value'] = np.where(pd.notna(wp), ev, np.nan)
        df['score'] = np.where((pd.notna(ev)) & (D > 0), ev / D, np.nan)

        # 同日组合排名（1=评分最高）
        df['combo_rank'] = df.groupby('trade_date')['score'].rank(
            ascending=False, method='first').fillna(0).astype(int)

        # ---------- 5. 双腿定价偏差（买腿低估有利买，卖腿高估有利卖） ----------
        bs1 = df['bs_theoretical_price'].values.astype(float)
        bs2 = df['bs_theoretical_price_short'].values.astype(float)
        df['close_vs_theoretical'] = np.where(pd.notna(bs1) & pd.notna(P2), P2 - bs1, np.nan)
        df['close_vs_theoretical_pct'] = np.where(
            pd.notna(bs1) & (bs1 > 0), (P2 - bs1) / bs1 * 100, np.nan)
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
        df['close_vs_theoretical_short'] = np.where(
            pd.notna(bs2) & pd.notna(P1), P1 - bs2, np.nan)
        df['close_vs_theoretical_pct_short'] = np.where(
            pd.notna(bs2) & (bs2 > 0), (P1 - bs2) / bs2 * 100, np.nan)
        df['price_bias_short'] = np.select(
            [
                df['close_vs_theoretical_pct_short'] < -5,
                (df['close_vs_theoretical_pct_short'] >= -5) & (df['close_vs_theoretical_pct_short'] < -1),
                (df['close_vs_theoretical_pct_short'] >= -1) & (df['close_vs_theoretical_pct_short'] <= 1),
                (df['close_vs_theoretical_pct_short'] > 1) & (df['close_vs_theoretical_pct_short'] <= 5),
                df['close_vs_theoretical_pct_short'] > 5,
            ],
            ['严重低估', '低估', '公允', '高估', '严重高估'],
            default='N/A'
        )

        # ---------- 摘要日志 ----------
        logger.info(f"Strategy P&L calculated for {len(df)} combo rows")
        valid = df['score'].notna().sum()
        if valid > 0:
            logger.info(f"  reward_risk_ratio: mean={df['reward_risk_ratio'].mean():.2f}, "
                        f"best={df['reward_risk_ratio'].max():.2f}")
            logger.info(f"  roi_max_pct: mean={df['roi_max_pct'].mean():.1f}%, "
                        f"best={df['roi_max_pct'].max():.1f}%")
            logger.info(f"  win_prob: mean={df['win_prob'].mean():.2f}")
            best = df[df['combo_rank'] == 1]
            if not best.empty:
                last = best.iloc[-1]
                logger.info(f"  latest best combo: K2={last['exercise_price']:.4g}/"
                            f"K1={last['exercise_price_short']:.4g}, "
                            f"score={last['score']:.3f}")
        return df

    # ================================================================
    # 组合配对（约束剪枝）
    # ================================================================
    def _build_pairs(self, df):
        """按交易日配对生成熊市价差组合

        约束: K2(买入腿) ∈ ATM±1 档（行权价贴近现货），K1(卖出腿) = K2 下方第 1~4 档，
        净支出 D>0
        输出: 每行一个组合（买入腿=高行权价K2 字段无后缀，卖出腿=低行权价K1 带 _short）
        """
        frames = []
        n_dates = 0
        for trade_date, g in df.groupby('trade_date', sort=True):
            n_dates += 1
            g = g.dropna(subset=['exercise_price', 'close'])
            if g.empty:
                continue

            # 按行权价索引合约（同月同方向每档一条）
            by_strike = {}
            for _, row in g.iterrows():
                by_strike[float(row['exercise_price'])] = row
            strikes = sorted(by_strike.keys())
            if len(strikes) < 2:
                continue

            S0 = float(g['spot_price'].iloc[0])
            atm_idx = int(np.abs(np.array(strikes) - S0).argmin())

            # 买入腿 K2: ATM ± 1 档
            lo = max(0, atm_idx - self.LONG_LEG_ATM_RANGE)
            hi = min(len(strikes) - 1, atm_idx + self.LONG_LEG_ATM_RANGE)

            for i in range(lo, hi + 1):
                row_long = by_strike[strikes[i]]      # 买入腿（高行权价 K2）
                K2 = strikes[i]
                P2 = float(row_long['close'])
                # 卖出腿 K1: 买入腿下方 1~4 档
                for j in range(max(0, i - self.MAX_WIDTH_STEPS), i):
                    row_short = by_strike[strikes[j]]  # 卖出腿（低行权价 K1）
                    K1 = strikes[j]
                    P1 = float(row_short['close'])
                    if P2 - P1 <= 0:  # 净支出<=0 的退化组合跳过
                        continue
                    frames.append({
                        'trade_date': trade_date,
                        # 买入腿（无后缀，K2 高）
                        'ts_code': row_long['ts_code'],
                        'symbol': row_long['symbol'],
                        'opt_name': row_long['opt_name'],
                        'opt_exchange': row_long['opt_exchange'],
                        'call_put': row_long['call_put'],
                        # 卖出腿（_short，K1 低）
                        'ts_code_short': row_short['ts_code'],
                        'symbol_short': row_short['symbol'],
                        'opt_name_short': row_short['opt_name'],
                        # 合约要素（同到期月）
                        'exercise_price': K2,
                        'exercise_price_short': K1,
                        'opt_multiplier': row_long['opt_multiplier'],
                        's_month': row_long['s_month'],
                        'maturity_date': row_long['maturity_date'],
                        'days_to_maturity': row_long['days_to_maturity'],
                        # 标的市场
                        'spot_price': S0,
                        'moneyness_status': row_long['moneyness_status'],
                        'risk_free_rate': row_long['risk_free_rate'],
                        'dividend_yield': row_long['dividend_yield'],
                        # 双腿行情与定价
                        'premium': P2,
                        'premium_short': P1,
                        'implied_vol': row_long['implied_vol'],
                        'implied_vol_short': row_short['implied_vol'],
                        'iv_rank': row_long['iv_rank'],
                        'iv_rank_short': row_short['iv_rank'],
                        # 双腿 Greeks
                        'delta': row_long['delta'],
                        'gamma': row_long['gamma'],
                        'theta': row_long['theta'],
                        'vega': row_long['vega'],
                        'delta_short': row_short['delta'],
                        'gamma_short': row_short['gamma'],
                        'theta_short': row_short['theta'],
                        'vega_short': row_short['vega'],
                        # 双腿理论价
                        'bs_theoretical_price': row_long['bs_theoretical_price'],
                        'bs_theoretical_price_short': row_short['bs_theoretical_price'],
                    })

        logger.info(f"Pairing done: {n_dates} trade dates -> {len(frames)} combos")
        return pd.DataFrame(frames)

    # ================================================================
    # Step 5: 多情景盈亏（含买现货对照）
    # ================================================================
    def calc_scenario_pnl(self, df, scenarios=None):
        """多情景盈亏：S_T = K2 * factor

        价差组合 P&L = max(0,K2-S_T) - max(0,K1-S_T) - D
        买现货对照 P&L = S_T - S0（对照组，衡量封顶让渡与亏损封底）
        收益率基准 = 净支出 D（价差的本金即最大风险）
        """
        if df.empty:
            return df
        if scenarios is None:
            scenarios = self.DEFAULT_SCENARIOS

        logger.info(f"Calculating multi-scenario P&L for {len(scenarios)} scenarios: {scenarios}")

        S = df['spot_price'].values.astype(float)
        K2 = df['exercise_price'].values.astype(float)       # 买入腿（高）
        K1 = df['exercise_price_short'].values.astype(float) # 卖出腿（低）
        D = df['net_debit'].values.astype(float)
        mult = df['opt_multiplier'].values.astype(float)

        for factor in scenarios:
            s_T = K2 * factor

            # 价差组合盈亏（熊市：跌得越深盈利越大，但封顶于宽度）
            combo_pnl = np.maximum(K2 - s_T, 0) - np.maximum(K1 - s_T, 0) - D
            label = f'{factor:.2f}'.replace('.', '_')
            df[f'scenario_pnl_{label}K'] = combo_pnl
            df[f'scenario_pnl_{label}K_cny'] = combo_pnl * mult
            df[f'scenario_pnl_{label}K_pct'] = np.where(
                D > 0, combo_pnl / D * 100, np.nan)

            # 买现货对照（下跌时现货亏损无限，价差亏损封底）
            unhedged_pnl = s_T - S
            df[f'unhedged_pnl_{label}K'] = unhedged_pnl
            df[f'unhedged_pnl_{label}K_pct'] = np.where(
                S > 0, unhedged_pnl / S * 100, np.nan)

        logger.info("Multi-scenario P&L calculated")
        return df

    # ================================================================
    # Step 6: 交易信号（价差视角：高回报风险比 + 高胜率 = 好价差）
    # ================================================================
    def _assign_trade_signals(self, df):
        """分配交易信号

        综合三个维度（找"便宜且赔得起"的价差）：
          1. reward_risk_ratio：最大盈利/最大亏损，越高越优
          2. win_prob：跌破盈亏平衡点的概率（两腿|delta|插值）
          3. roi_max_pct：以净支出为本金的最大资金收益率
        """
        if df.empty:
            return df

        rr = df['reward_risk_ratio'].values
        wp = df['win_prob'].values
        roi = df['roi_max_pct'].values
        days = df['days_to_maturity'].values
        width_pct = df['spread_width_pct'].values
        debit_pct_width = df['net_debit_pct_of_width'].values
        debit_pct_spot = df['net_debit_pct_of_spot'].values
        ivr_long = df['iv_rank'].values

        signals = np.full(len(df), 'AVOID', dtype=object)
        signal_reasons = np.full(len(df), '', dtype=object)

        for i in range(len(df)):
            rr_i = rr[i]
            wp_i = wp[i]
            roi_i = roi[i]
            days_i = days[i]
            w_i = width_pct[i]
            dw_i = debit_pct_width[i]
            ds_i = debit_pct_spot[i]
            ivr_i = ivr_long[i]

            if pd.isna(rr_i):
                signals[i] = 'N/A'
                signal_reasons[i] = '数据不足'
                continue

            reasons = []

            if (not pd.isna(wp_i)) and rr_i >= 2.0 and wp_i >= 0.60 and \
                    (not pd.isna(roi_i)) and roi_i >= 15:
                signals[i] = 'STRONG_BUY'
                reasons.append(f'回报风险比={rr_i:.2f}>=2')
                reasons.append(f'胜率={wp_i:.2f}>=0.60')
                reasons.append(f'最大收益率={roi_i:.1f}%>=15%')
            elif (not pd.isna(wp_i)) and rr_i >= 1.5 and wp_i >= 0.50:
                signals[i] = 'BUY'
                reasons.append(f'回报风险比={rr_i:.2f}>=1.5')
                reasons.append(f'胜率={wp_i:.2f}>=0.50')
            elif rr_i >= 1.2:
                signals[i] = 'CONSIDER'
                reasons.append(f'回报风险比={rr_i:.2f}>=1.2')
            elif rr_i >= 1.0:
                signals[i] = 'NEUTRAL'
                reasons.append(f'回报风险比={rr_i:.2f}')
            else:
                signals[i] = 'AVOID'
                reasons.append(f'回报风险比={rr_i:.2f}<1(盈亏比不划算)')

            # 补充风控理由
            if pd.notna(days_i) and days_i < 10:
                reasons.append(f'仅剩{days_i:.0f}天到期, Gamma风险高, 建议移仓')
            if pd.notna(w_i) and w_i < 1.0:
                reasons.append(f'宽度仅{w_i:.1f}%<1%(利润空间太薄)')
            if pd.notna(dw_i) and dw_i > 90:
                reasons.append(f'净支出占宽度{dw_i:.0f}%>90%(资本效率低)')
            if pd.notna(ds_i) and ds_i > 3.0:
                reasons.append(f'净支出占现价{ds_i:.1f}%>3%(成本偏高)')
            if pd.notna(ivr_i) and ivr_i >= 0.65:
                reasons.append(f'买入腿IV分位={ivr_i:.2f}>=0.65(买贵了)')
            if pd.notna(wp_i) and wp_i < 0.40:
                reasons.append(f'胜率{wp_i:.2f}<0.40(需大跌才回本)')

            signal_reasons[i] = '; '.join(reasons)

        df['trade_signal'] = signals
        df['signal_reason'] = signal_reasons

        signal_counts = pd.Series(signals).value_counts()
        logger.info(f"Trade signals: {signal_counts.to_dict()}")

        return df

r"""
Butterfly Spread（蝴蝶价差，Long Call Butterfly）策略分析 — 高级交易员/风控视角

策略定义：买入低行权价认购 Call(K1) + 卖出 2 张中间行权价认购 Call(K2) + 买入高行权价认购 Call(K3)，
K1 < K2 < K3，同到期月，K2 尽量居中（对称：K2-K1 ≈ K3-K2）
净支出 D = C1 - 2*C2 + C3；组合到期收益 = max(0,S_T-K1) - 2*max(0,S_T-K2) + max(0,S_T-K3) - D

蝴蝶价差的特点（与方向性价差的本质差异，分析端逐一体现）：
  1. 非方向性：赚"盘整"（S_T 钉在 K2 附近），两侧突破都亏 —— 山形（尖顶）收益图，非厂字形
  2. 双盈亏平衡点：B1 = K1+D（下平衡）、B2 = K3-D（上平衡），盈利区间 (B1, B2)
  3. 净 Theta 为正：卖 2 张中间腿收的时间价值超过买两翼的损耗，时间站在持有者一边
     —— 与单腿买方/bull-bear 价差相反（它们 theta 是损耗）
  4. 净 Vega 为负：做空波动率，IV 回落获利、IV 飙升受伤 —— 本质是"卖尾部保险+买翼保护"
  5. 胜率为区间概率：win_prob = P(B1 < S_T < B2) ≈ delta(K1) - delta(K3)，
     数值上远低于单边策略（区间窄），与 bull/bear 的单边胜率不可直接比较
  6. 对称性要求：峰值高度 = min(K2-K1, K3-K2) - D（非对称时取窄翼），
     配对时用不对称度约束保证接近教科书等宽结构

组合配对（约束剪枝，控制组合爆炸）：
  1. 同一到期月（symbol_filter 保证）
  2. 中间腿 K2 = ATM 档（|K2-S0| 最小，峰值对准当前价格——盘整策略的中心）
  3. 低翼 K1 = K2 下方 1~3 档，高翼 K3 = K2 上方 1~3 档
  4. 对称性约束：|(K2-K1)-(K3-K2)| / (K3-K1) <= 25%（不对称度）
  每日最多 3x3=9 个候选组合全量落库（透明可回溯），信号端按综合评分排序

风控三问（蝴蝶视角）：
  1. 花了多少（成本）：net_debit / net_debit_pct_of_spot / net_debit_pct_of_width
  2. 最多赚多少（峰值）：max_profit（S_T=K2 时）/ roi_max_pct / reward_risk_ratio
  3. 多大概率赚（区间胜率）：win_prob（双平衡点区间概率）/ expected_value / score

数据源：
  - tb_tushare_opt_daily_indicator : 现货价、BS定价、Greeks（原料）
  - df_tushare_opt_basic           : symbol/name 反查（ETF 期权 ts_code 为8位数字）

落库：
  - tb_option_trading_strategy_butterfly_spread : strategy_type='BUTTERFLY_SPREAD'，
    每行一个组合（买入腿1字段无后缀，卖出腿带 _short，买入腿2带 _long2）

使用（symbol 直接指定标的+方向+到期月）：
  config = {
      "name": "华夏上证50ETF认购期权（Butterfly Spread）",
      "start_date": "20251222",
      "end_date": CommonParameters.today,
      "call_put": "C",
      "symbol_filter": "510050C2612%",
  }
  ButterflySpreadStrategyAnalysis().run(config)
"""

import numpy as np
import pandas as pd

from dataIntegrator import CommonLib
from dataIntegrator.modelService.option.OptionTradingStrategyManager.OptionStrategyBase import OptionStrategyBase

logger = CommonLib.logger


class ButterflySpreadStrategyAnalysis(OptionStrategyBase):
    """Butterfly Spread 策略分析器（买 Call(K1) + 卖 2×Call(K2) + 买 Call(K3)，盘整市策略）

    分析维度：三腿配对（对称性剪枝）、净支出、山形双封顶、区间胜率与评分排序、
    净 Greeks（正 theta/负 vega——时间有利、做空波动率）、多情景盈亏（含买现货对照）。
    """

    # === 策略标识 ===
    STRATEGY_TYPE = 'BUTTERFLY_SPREAD'
    ANALYSIS_VERSION = 'v1'
    TABLE_TARGET = 'tb_option_trading_strategy_butterfly_spread'

    # === 目标表字段（与 tb_option_trading_strategy_butterfly_spread.sql 建表一致） ===
    TARGET_COLUMNS = [
        # 策略标识与审计
        'strategy_type', 'analysis_time', 'analysis_params', 'analysis_version',
        # 组合标识（买入腿1无后缀，卖出腿带 _short，买入腿2带 _long2）
        'trade_date', 'ts_code', 'symbol', 'opt_name', 'opt_exchange', 'call_put',
        'ts_code_short', 'symbol_short', 'opt_name_short',
        'ts_code_long2', 'symbol_long2', 'opt_name_long2',
        # 合约要素
        'exercise_price', 'exercise_price_short', 'exercise_price_long2',
        'opt_multiplier', 's_month', 'maturity_date', 'days_to_maturity',
        # 标的市场
        'spot_price', 'moneyness_status', 'risk_free_rate', 'dividend_yield',
        # 三腿行情与定价
        'premium', 'premium_short', 'premium_long2',
        'implied_vol', 'implied_vol_short', 'implied_vol_long2',
        'iv_rank', 'iv_rank_short', 'iv_rank_long2',
        # 三腿 Greeks
        'delta', 'gamma', 'theta', 'vega',
        'delta_short', 'gamma_short', 'theta_short', 'vega_short',
        'delta_long2', 'gamma_long2', 'theta_long2', 'vega_long2',
        # 三腿定价偏差
        'bs_theoretical_price', 'close_vs_theoretical', 'close_vs_theoretical_pct', 'price_bias',
        'bs_theoretical_price_short', 'close_vs_theoretical_short',
        'close_vs_theoretical_pct_short', 'price_bias_short',
        'bs_theoretical_price_long2', 'close_vs_theoretical_long2',
        'close_vs_theoretical_pct_long2', 'price_bias_long2',
        # 组合净 Greeks
        'net_delta', 'net_gamma', 'net_theta', 'net_vega',
        # 蝴蝶结构（对称性）
        'wing_low', 'wing_high', 'wing_min', 'spread_width', 'spread_width_pct',
        'asymmetry_pct',
        'net_debit', 'net_debit_cny', 'net_debit_pct_of_spot', 'net_debit_pct_of_width',
        # 收益结构（山形）
        'max_profit', 'max_profit_cny', 'max_profit_pct_of_spot', 'roi_max_pct',
        'max_loss', 'max_loss_cny', 'max_loss_pct_of_spot', 'reward_risk_ratio',
        'breakeven_S_T', 'breakeven_upside_pct',
        'breakeven_S_T_high', 'breakeven_high_pct', 'profit_zone_width',
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

    # === 情景系数（S_T = K2 × factor，K2 为山形峰值中心） ===
    DEFAULT_SCENARIOS = [0.85, 0.90, 0.95, 1.00, 1.03, 1.05, 1.10, 1.15]

    # === 组合配对参数（约束剪枝） ===
    MAX_WING_STEPS = 3        # 两翼各在 K2 上下 1~3 档
    MAX_ASYMMETRY = 0.25       # 不对称度上限: |w1-w3|/(K3-K1) <= 25%（教科书等宽蝴蝶）

    # ================================================================
    # Step 4: 三腿配对 + 核心策略盈亏（风控三问）
    # ================================================================
    def calc_strategy_pnl(self, df):
        """Butterfly Spread 核心盈亏指标（组合粒度）

        配对: 买 Call(K1) + 卖 2×Call(K2) + 买 Call(K3)，净支出 D = C1 - 2*C2 + C3
        到期组合收益 = max(0,S_T-K1) - 2*max(0,S_T-K2) + max(0,S_T-K3) - D
        最大亏损 = D（S_T<=K1 或 S_T>=K3，两侧平台）
        最大盈利 = min(K2-K1, K3-K2) - D（S_T=K2 时，山形峰值）
        双盈亏平衡点 B1 = K1+D、B2 = K3-D，盈利区间 (B1, B2)
        """
        logger.info("Building butterfly spread pairs "
                    f"(mid leg = ATM, wings 1~{self.MAX_WING_STEPS}档, "
                    f"asymmetry <= {self.MAX_ASYMMETRY*100:.0f}%)...")

        # ---------- 0. 三腿配对（对称性剪枝） ----------
        df = self._build_pairs(df)
        if df.empty:
            logger.warning("No butterfly spread pairs built, skip P&L calculation")
            return df
        logger.info(f"Built {len(df)} combo rows "
                    f"({df.groupby('trade_date').size().max()} combos/day max)")

        S = df['spot_price'].values.astype(float)
        K1 = df['exercise_price'].values.astype(float)
        K2 = df['exercise_price_short'].values.astype(float)
        K3 = df['exercise_price_long2'].values.astype(float)
        C1 = df['premium'].values.astype(float)
        C2 = df['premium_short'].values.astype(float)
        C3 = df['premium_long2'].values.astype(float)
        mult = df['opt_multiplier'].values.astype(float)

        delta1 = df['delta'].values.astype(float)
        delta2 = df['delta_short'].values.astype(float)
        delta3 = df['delta_long2'].values.astype(float)

        # ---------- 1. 蝴蝶结构（花了多少 + 对称性） ----------
        wing_low = K2 - K1
        wing_high = K3 - K2
        wing_min = np.minimum(wing_low, wing_high)
        total_width = K3 - K1
        D = C1 - 2.0 * C2 + C3
        df['wing_low'] = wing_low
        df['wing_high'] = wing_high
        df['wing_min'] = wing_min
        df['spread_width'] = total_width
        df['spread_width_pct'] = np.where(S > 0, total_width / S * 100, np.nan)
        df['asymmetry_pct'] = np.where(
            total_width > 0, np.abs(wing_low - wing_high) / total_width * 100, np.nan)
        df['net_debit'] = D
        df['net_debit_cny'] = D * mult
        df['net_debit_pct_of_spot'] = np.where(S > 0, D / S * 100, np.nan)
        df['net_debit_pct_of_width'] = np.where(total_width > 0, D / total_width * 100, np.nan)

        # ---------- 2. 收益结构（山形：峰值在 K2，两侧平台） ----------
        max_profit = wing_min - D
        df['max_profit'] = max_profit
        df['max_profit_cny'] = max_profit * mult
        df['max_profit_pct_of_spot'] = np.where(S > 0, max_profit / S * 100, np.nan)
        # 最大资金收益率：以净支出 D 为本金
        df['roi_max_pct'] = np.where(D > 0, max_profit / D * 100, np.nan)

        df['max_loss'] = D
        df['max_loss_cny'] = D * mult
        df['max_loss_pct_of_spot'] = np.where(S > 0, D / S * 100, np.nan)
        df['reward_risk_ratio'] = np.where(D > 0, max_profit / D, np.nan)

        # 双盈亏平衡点（蝴蝶独有）
        B1 = K1 + D
        B2 = K3 - D
        df['breakeven_S_T'] = B1
        df['breakeven_upside_pct'] = np.where(S > 0, (B1 - S) / S * 100, np.nan)
        df['breakeven_S_T_high'] = B2
        df['breakeven_high_pct'] = np.where(S > 0, (B2 - S) / S * 100, np.nan)
        df['profit_zone_width'] = B2 - B1

        # ---------- 3. 组合净 Greeks（蝴蝶核心：Delta≈0 方向中性，Theta 为正，Vega 为负） ----------
        # 持仓符号: 买 K1(+1) + 卖 2×K2(-2) + 买 K3(+1)
        d_ok = pd.notna(delta1) & pd.notna(delta2) & pd.notna(delta3)
        df['net_delta'] = np.where(d_ok, delta1 - 2.0 * delta2 + delta3, np.nan)
        g_ok = pd.notna(df['gamma']) & pd.notna(df['gamma_short']) & pd.notna(df['gamma_long2'])
        df['net_gamma'] = np.where(g_ok, df['gamma'] - 2.0 * df['gamma_short']
                                   + df['gamma_long2'], np.nan)
        t_ok = pd.notna(df['theta']) & pd.notna(df['theta_short']) & pd.notna(df['theta_long2'])
        # theta 为买方口径（负值），持仓 1-2+1 → 净 theta = theta1 - 2*theta2 + theta3
        df['net_theta'] = np.where(t_ok, df['theta'] - 2.0 * df['theta_short']
                                   + df['theta_long2'], np.nan)
        v_ok = pd.notna(df['vega']) & pd.notna(df['vega_short']) & pd.notna(df['vega_long2'])
        df['net_vega'] = np.where(v_ok, df['vega'] - 2.0 * df['vega_short']
                                  + df['vega_long2'], np.nan)

        # ---------- 4. 区间胜率与评分（蝴蝶独有：P(B1 < S_T < B2)） ----------
        # call delta ≈ P(S_T > K)：区间概率 = P(S_T>K1) - P(S_T>K3) ≈ delta1 - delta3
        win_prob = np.clip(delta1 - delta3, 0.0, 1.0)
        df['win_prob'] = np.where(d_ok, win_prob, np.nan)

        # 期望值 = 胜率×峰值盈利 - (1-胜率)×最大亏损；评分 = 期望值/净支出
        # 注意：区间内盈利从 0 渐变到峰值，线性近似会高估端点附近收益（保守解读）
        wp = df['win_prob'].values.astype(float)
        ev = wp * max_profit - (1 - wp) * D
        df['expected_value'] = np.where(pd.notna(wp), ev, np.nan)
        df['score'] = np.where((pd.notna(ev)) & (D > 0), ev / D, np.nan)

        # 同日组合排名（1=评分最高）
        df['combo_rank'] = df.groupby('trade_date')['score'].rank(
            ascending=False, method='first').fillna(0).astype(int)

        # ---------- 5. 三腿定价偏差 ----------
        bs1 = df['bs_theoretical_price'].values.astype(float)
        bs2 = df['bs_theoretical_price_short'].values.astype(float)
        bs3 = df['bs_theoretical_price_long2'].values.astype(float)
        df['close_vs_theoretical'] = np.where(pd.notna(bs1) & pd.notna(C1), C1 - bs1, np.nan)
        df['close_vs_theoretical_pct'] = np.where(
            pd.notna(bs1) & (bs1 > 0), (C1 - bs1) / bs1 * 100, np.nan)
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
            pd.notna(bs2) & pd.notna(C2), C2 - bs2, np.nan)
        df['close_vs_theoretical_pct_short'] = np.where(
            pd.notna(bs2) & (bs2 > 0), (C2 - bs2) / bs2 * 100, np.nan)
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
        df['close_vs_theoretical_long2'] = np.where(
            pd.notna(bs3) & pd.notna(C3), C3 - bs3, np.nan)
        df['close_vs_theoretical_pct_long2'] = np.where(
            pd.notna(bs3) & (bs3 > 0), (C3 - bs3) / bs3 * 100, np.nan)
        df['price_bias_long2'] = np.select(
            [
                df['close_vs_theoretical_pct_long2'] < -5,
                (df['close_vs_theoretical_pct_long2'] >= -5) & (df['close_vs_theoretical_pct_long2'] < -1),
                (df['close_vs_theoretical_pct_long2'] >= -1) & (df['close_vs_theoretical_pct_long2'] <= 1),
                (df['close_vs_theoretical_pct_long2'] > 1) & (df['close_vs_theoretical_pct_long2'] <= 5),
                df['close_vs_theoretical_pct_long2'] > 5,
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
            logger.info(f"  win_prob(区间): mean={df['win_prob'].mean():.2f}")
            logger.info(f"  net_theta(时间衰减): mean={df['net_theta'].mean():.6f} "
                        f"(正值=时间有利)")
            best = df[df['combo_rank'] == 1]
            if not best.empty:
                last = best.iloc[-1]
                logger.info(f"  latest best combo: K1={last['exercise_price']:.4g}/"
                            f"K2={last['exercise_price_short']:.4g}/"
                            f"K3={last['exercise_price_long2']:.4g}, "
                            f"score={last['score']:.3f}")
        return df

    # ================================================================
    # 三腿配对（对称性剪枝）
    # ================================================================
    def _build_pairs(self, df):
        """按交易日配对生成蝴蝶价差组合

        约束: K2 = ATM 档（峰值对准现价），K1 在 K2 下方 1~3 档，K3 在 K2 上方 1~3 档，
              不对称度 |(K2-K1)-(K3-K2)|/(K3-K1) <= 25%，净支出 D > 0（净借方蝴蝶）
        输出: 每行一个组合（买入腿1无后缀，卖出腿带 _short，买入腿2带 _long2）
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
            if len(strikes) < 3:
                continue

            S0 = float(g['spot_price'].iloc[0])
            mid_idx = int(np.abs(np.array(strikes) - S0).argmin())

            # 中间腿 K2 = ATM 档
            row_mid = by_strike[strikes[mid_idx]]
            K2 = strikes[mid_idx]
            C2 = float(row_mid['close'])

            # 两翼：K2 下方/上方各 1~3 档
            lo_max = max(0, mid_idx - self.MAX_WING_STEPS)
            hi_min = min(len(strikes) - 1, mid_idx + self.MAX_WING_STEPS)

            for i in range(mid_idx - 1, lo_max - 1, -1):
                row_low = by_strike[strikes[i]]
                K1 = strikes[i]
                C1 = float(row_low['close'])
                w_low = K2 - K1
                if w_low <= 0:
                    continue
                for j in range(mid_idx + 1, hi_min + 1):
                    row_high = by_strike[strikes[j]]
                    K3 = strikes[j]
                    C3 = float(row_high['close'])
                    w_high = K3 - K2
                    if w_high <= 0:
                        continue
                    # 对称性剪枝：不对称度超限跳过（保持教科书等宽结构）
                    asym = abs(w_low - w_high) / (K3 - K1)
                    if asym > self.MAX_ASYMMETRY:
                        continue
                    if C1 - 2.0 * C2 + C3 <= 0:  # 净收入/零成本组合跳过（非标准净借方蝴蝶）
                        continue
                    frames.append({
                        'trade_date': trade_date,
                        # 买入腿1（低翼，无后缀）
                        'ts_code': row_low['ts_code'],
                        'symbol': row_low['symbol'],
                        'opt_name': row_low['opt_name'],
                        'opt_exchange': row_low['opt_exchange'],
                        'call_put': row_low['call_put'],
                        # 卖出腿（身体 ×2，_short）
                        'ts_code_short': row_mid['ts_code'],
                        'symbol_short': row_mid['symbol'],
                        'opt_name_short': row_mid['opt_name'],
                        # 买入腿2（高翼，_long2）
                        'ts_code_long2': row_high['ts_code'],
                        'symbol_long2': row_high['symbol'],
                        'opt_name_long2': row_high['opt_name'],
                        # 合约要素（同到期月）
                        'exercise_price': K1,
                        'exercise_price_short': K2,
                        'exercise_price_long2': K3,
                        'opt_multiplier': row_low['opt_multiplier'],
                        's_month': row_low['s_month'],
                        'maturity_date': row_low['maturity_date'],
                        'days_to_maturity': row_low['days_to_maturity'],
                        # 标的市场
                        'spot_price': S0,
                        'moneyness_status': row_low['moneyness_status'],
                        'risk_free_rate': row_low['risk_free_rate'],
                        'dividend_yield': row_low['dividend_yield'],
                        # 三腿行情与定价
                        'premium': C1,
                        'premium_short': C2,
                        'premium_long2': C3,
                        'implied_vol': row_low['implied_vol'],
                        'implied_vol_short': row_mid['implied_vol'],
                        'implied_vol_long2': row_high['implied_vol'],
                        'iv_rank': row_low['iv_rank'],
                        'iv_rank_short': row_mid['iv_rank'],
                        'iv_rank_long2': row_high['iv_rank'],
                        # 三腿 Greeks
                        'delta': row_low['delta'],
                        'gamma': row_low['gamma'],
                        'theta': row_low['theta'],
                        'vega': row_low['vega'],
                        'delta_short': row_mid['delta'],
                        'gamma_short': row_mid['gamma'],
                        'theta_short': row_mid['theta'],
                        'vega_short': row_mid['vega'],
                        'delta_long2': row_high['delta'],
                        'gamma_long2': row_high['gamma'],
                        'theta_long2': row_high['theta'],
                        'vega_long2': row_high['vega'],
                        # 三腿理论价
                        'bs_theoretical_price': row_low['bs_theoretical_price'],
                        'bs_theoretical_price_short': row_mid['bs_theoretical_price'],
                        'bs_theoretical_price_long2': row_high['bs_theoretical_price'],
                    })

        logger.info(f"Pairing done: {n_dates} trade dates -> {len(frames)} combos")
        return pd.DataFrame(frames)

    # ================================================================
    # Step 5: 多情景盈亏（含买现货对照）
    # ================================================================
    def calc_scenario_pnl(self, df, scenarios=None):
        """多情景盈亏：S_T = K2 * factor（K2 为山形峰值中心）

        蝴蝶组合 P&L = max(0,S_T-K1) - 2*max(0,S_T-K2) + max(0,S_T-K3) - D
        买现货对照 P&L = S_T - S0（对照组，衡量盘整收益与突破亏损）
        收益率基准 = 净支出 D（蝴蝶的本金即最大风险）
        """
        if df.empty:
            return df
        if scenarios is None:
            scenarios = self.DEFAULT_SCENARIOS

        logger.info(f"Calculating multi-scenario P&L for {len(scenarios)} scenarios: {scenarios}")

        S = df['spot_price'].values.astype(float)
        K1 = df['exercise_price'].values.astype(float)
        K2 = df['exercise_price_short'].values.astype(float)
        K3 = df['exercise_price_long2'].values.astype(float)
        D = df['net_debit'].values.astype(float)
        mult = df['opt_multiplier'].values.astype(float)

        for factor in scenarios:
            s_T = K2 * factor

            # 蝴蝶组合盈亏（三腿）
            combo_pnl = (np.maximum(s_T - K1, 0) - 2.0 * np.maximum(s_T - K2, 0)
                         + np.maximum(s_T - K3, 0) - D)
            label = f'{factor:.2f}'.replace('.', '_')
            df[f'scenario_pnl_{label}K'] = combo_pnl
            df[f'scenario_pnl_{label}K_cny'] = combo_pnl * mult
            df[f'scenario_pnl_{label}K_pct'] = np.where(
                D > 0, combo_pnl / D * 100, np.nan)

            # 买现货对照
            unhedged_pnl = s_T - S
            df[f'unhedged_pnl_{label}K'] = unhedged_pnl
            df[f'unhedged_pnl_{label}K_pct'] = np.where(
                S > 0, unhedged_pnl / S * 100, np.nan)

        logger.info("Multi-scenario P&L calculated")
        return df

    # ================================================================
    # Step 6: 交易信号（盘整市策略：找"便宜且区间概率高"的蝴蝶）
    # ================================================================
    def _assign_trade_signals(self, df):
        """分配交易信号

        蝴蝶是非方向性做空波动率策略，信号逻辑与 bull/bear 价差相反：
          1. reward_risk_ratio：峰值盈利/最大亏损，越高越优
          2. win_prob：P(B1 < S_T < B2) 区间概率（数值天然低于单边策略）
          3. 环境加分：IV 分位高（卖 2×中间腿收得贵，建仓便宜）
          4. 结构加分：净 theta > 0（时间站在持有者一边）、不对称度低
        """
        if df.empty:
            return df

        rr = df['reward_risk_ratio'].values
        wp = df['win_prob'].values
        roi = df['roi_max_pct'].values
        days = df['days_to_maturity'].values
        width_pct = df['spread_width_pct'].values
        asym = df['asymmetry_pct'].values
        debit_pct_width = df['net_debit_pct_of_width'].values
        debit_pct_spot = df['net_debit_pct_of_spot'].values
        ivr_mid = df['iv_rank_short'].values
        ntheta = df['net_theta'].values

        signals = np.full(len(df), 'AVOID', dtype=object)
        signal_reasons = np.full(len(df), '', dtype=object)

        for i in range(len(df)):
            rr_i = rr[i]
            wp_i = wp[i]
            roi_i = roi[i]
            days_i = days[i]
            w_i = width_pct[i]
            asym_i = asym[i]
            dw_i = debit_pct_width[i]
            ds_i = debit_pct_spot[i]
            ivr_i = ivr_mid[i]
            nt_i = ntheta[i]

            if pd.isna(rr_i):
                signals[i] = 'N/A'
                signal_reasons[i] = '数据不足'
                continue

            reasons = []

            # 区间胜率阈值低于单边策略（区间窄、概率天然低）
            if (not pd.isna(wp_i)) and rr_i >= 2.0 and wp_i >= 0.30 and \
                    (not pd.isna(roi_i)) and roi_i >= 25:
                signals[i] = 'STRONG_BUY'
                reasons.append(f'回报风险比={rr_i:.2f}>=2')
                reasons.append(f'区间胜率={wp_i:.2f}>=0.30')
                reasons.append(f'峰值收益率={roi_i:.1f}%>=25%')
            elif (not pd.isna(wp_i)) and rr_i >= 1.5 and wp_i >= 0.22:
                signals[i] = 'BUY'
                reasons.append(f'回报风险比={rr_i:.2f}>=1.5')
                reasons.append(f'区间胜率={wp_i:.2f}>=0.22')
            elif rr_i >= 1.2:
                signals[i] = 'CONSIDER'
                reasons.append(f'回报风险比={rr_i:.2f}>=1.2')
            elif rr_i >= 1.0:
                signals[i] = 'NEUTRAL'
                reasons.append(f'回报风险比={rr_i:.2f}')
            else:
                signals[i] = 'AVOID'
                reasons.append(f'回报风险比={rr_i:.2f}<1(峰值不划算)')

            # 环境与结构加分/风险理由（蝴蝶特有视角）
            if pd.notna(nt_i) and nt_i > 0:
                reasons.append(f'净Theta>0({nt_i:.5f}, 时间衰减有利)')
            if pd.notna(ivr_i) and ivr_i >= 0.65:
                reasons.append(f'中间腿IV分位={ivr_i:.2f}>=0.65(卖2张收得贵, 建仓有利)')
            if pd.notna(days_i) and days_i < 10:
                reasons.append(f'仅剩{days_i:.0f}天到期, 尾部Gamma风险高, 建议移仓')
            if pd.notna(w_i) and w_i < 1.5:
                reasons.append(f'总宽仅{w_i:.1f}%<1.5%(盈利区间太窄)')
            if pd.notna(asym_i) and asym_i > 15:
                reasons.append(f'不对称度{asym_i:.0f}%>15%(偏离教科书等宽)')
            if pd.notna(dw_i) and dw_i > 50:
                reasons.append(f'净支出占总宽{dw_i:.0f}%>50%(资本效率低)')
            if pd.notna(ds_i) and ds_i > 2.0:
                reasons.append(f'净支出占现价{ds_i:.1f}%>2%(成本偏高)')

            signal_reasons[i] = '; '.join(reasons)

        df['trade_signal'] = signals
        df['signal_reason'] = signal_reasons

        signal_counts = pd.Series(signals).value_counts()
        logger.info(f"Trade signals: {signal_counts.to_dict()}")

        return df

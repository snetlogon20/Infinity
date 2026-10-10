r"""
Strip（条式组合）策略分析 — 高级交易员/风控视角

策略定义：买入同一行权价 K 的 1 份认购 Call + 2 份认沽 Put，同到期月
净支出 T = C + 2P（三腿权利金合计，也是最大亏损，S_T=K 时谷底）
组合到期收益 = max(0,S_T-K) + 2*max(0,K-S_T) - T（不对称 V 形，下行斜率加倍）
亏损封底 T（S_T=K），盈利无上限（双向）——但下行斜率是上行的 2 倍

策略特点（与 Long Straddle 的本质差异）：
  1. 看波动 + 偏空：Long Straddle 是方向中性的纯波动率买方，
     Strip 则在买波动的同时押注"若波动兑现、更可能向下"——
     下跌时 2 份 Put 赚双倍，上涨时仅 1 份 Call 赚单倍
  2. 不对称盈亏平衡点：
     下平衡点 = K - T/2（2 份 Put 只需跌一半成本的距离即回本， favoured side）
     上平衡点 = K + T（1 份 Call 需涨过整个成本才回本， unflavoured side）
     盈亏平衡区间宽度 = 1.5T/S0（比同成本 Straddle 的 2T/S0 更窄）
  3. 净 Delta 为负（ATM 附近约 -0.5）：保留部分方向敞口——
     这是"偏空波动率"的量化表达，不是对冲残余
  4. 三腿 Theta 损耗（1C+2P 共 3 份）：比 Straddle 双腿更贵的时间成本，
     横盘失血更快——事件兑现即了结，不宜持有至到期
  5. 三腿净 Vega 为正（约 1.5 倍单腿叠加）：IV 回升双向受益

组合配对（三层漏斗第1层——约束剪枝，控制组合爆炸）：
  1. 同一到期月（symbol_filter 保证，方向不限 C+P）
  2. Call 腿与 Put 腿行权价相同（条式定义）
  3. 行权价限定 ATM ± 2 档（价值集中在平值附近）
  每日约 5 个候选行权价全量落库（透明可回溯），信号端按综合评分排序

风控三问（条式视角）：
  1. 花了多少（成本）：total_premium = C + 2P（三腿合计，也是最大亏损）
  2. 多大概率赚（胜率）：win_prob = P(S_T>K+T) + P(S_T<K-T/2)
     —— 注意下行只需跌 T/2 即盈利，下行"更容易"回本是 Strip 的结构优势
  3. 值不值（定价）：expected_value = (BS_C−C) + 2*(BS_P−P)
     —— Put 腿占权重 2/3，定价偏差重点看 Put 是否便宜

数据源：
  - tb_tushare_opt_daily_indicator : 现货价、BS定价、Greeks（原料）
  - df_tushare_opt_basic           : symbol/name 反查（ETF 期权 ts_code 为8位数字）

落库：
  - tb_option_trading_strategy_strip : strategy_type='STRIP'，
    每行一个组合（Call腿字段无后缀，Put腿字段带 _put 后缀；
    premium/premium_put 为单份收盘价，组合权重 1:2 在 total_premium 等聚合字段体现）

使用（symbol 直接指定标的+到期月，方向传 None 同时取 C/P）：
  config = {
      "name": "华夏上证50ETF期权（Strip）",
      "start_date": "20251222",
      "end_date": CommonParameters.today,
      "call_put": None,
      "symbol_filter": "510050%2612%",
  }
  StripStrategyAnalysis().run(config)
"""

from scipy.special import erf

import numpy as np
import pandas as pd

from dataIntegrator import CommonLib
from dataIntegrator.modelService.option.OptionTradingStrategyManager.OptionStrategyBase import OptionStrategyBase

logger = CommonLib.logger


def _norm_cdf(z):
    """标准正态分布 CDF（scipy.special.erf，标量与 numpy 数组通用）"""
    return 0.5 * (1.0 + erf(z / np.sqrt(2.0)))


class StripStrategyAnalysis(OptionStrategyBase):
    """Strip 策略分析器（买 1 份 Call(K) + 买 2 份 Put(K)，条式组合）

    分析维度：条式配对（约束剪枝）、三腿总成本、对数正态胜率（不对称平衡点）、
    定价偏差期望值（Put 权重加倍）与评分排序、净 Greeks（1C+2P 加权）、
    多情景盈亏（下行双倍杠杆，含买现货对照）。
    """

    # === 策略标识 ===
    STRATEGY_TYPE = 'STRIP'
    ANALYSIS_VERSION = 'v1'
    TABLE_TARGET = 'tb_option_trading_strategy_strip'

    # === 腿权重（条式定义：1 份 Call + 2 份 Put） ===
    W_CALL = 1
    W_PUT = 2

    # === 目标表字段（与 tb_option_trading_strategy_strip.sql 建表一致） ===
    TARGET_COLUMNS = [
        # 策略标识与审计
        'strategy_type', 'analysis_time', 'analysis_params', 'analysis_version',
        # 组合标识（Call腿无后缀，Put腿带 _put）
        'trade_date', 'ts_code', 'symbol', 'opt_name', 'opt_exchange', 'call_put',
        'ts_code_put', 'symbol_put', 'opt_name_put',
        # 合约要素
        'exercise_price', 'opt_multiplier', 's_month',
        'maturity_date', 'days_to_maturity',
        # 标的市场
        'spot_price', 'moneyness_status', 'risk_free_rate', 'dividend_yield',
        # 双腿行情与定价（单份价格，组合权重 1:2）
        'premium', 'premium_put', 'implied_vol', 'implied_vol_put',
        'iv_rank', 'iv_rank_put',
        # 双腿 Greeks（单份，净敞口按 1:2 加权）
        'delta', 'gamma', 'theta', 'vega',
        'delta_put', 'gamma_put', 'theta_put', 'vega_put',
        # 双腿定价偏差
        'bs_theoretical_price', 'close_vs_theoretical', 'close_vs_theoretical_pct', 'price_bias',
        'bs_theoretical_price_put', 'close_vs_theoretical_put',
        'close_vs_theoretical_pct_put', 'price_bias_put',
        # 组合净 Greeks（1C + 2P 加权：净Delta为负=偏空敞口）
        'net_delta', 'net_gamma', 'net_theta', 'net_vega',
        # 条式结构（花了多少：三腿合计）
        'total_premium', 'total_premium_cny', 'total_premium_pct_of_spot',
        'expected_move_1sigma_pct',
        # 收益结构（亏损封底 T，盈利无上限，下行斜率加倍的不对称 V 形）
        'max_loss', 'max_loss_cny', 'max_loss_pct_of_spot',
        'breakeven_up', 'breakeven_up_pct',
        'breakeven_down', 'breakeven_down_pct', 'breakeven_range_pct',
        # 概率与评分
        'win_prob', 'expected_value', 'score', 'combo_rank',
        # 多情景盈亏（S_T = S0 * factor，下行双倍杠杆，含买现货对照）
        'scenario_pnl_0_85S', 'scenario_pnl_0_85S_cny', 'scenario_pnl_0_85S_pct',
        'unhedged_pnl_0_85S', 'unhedged_pnl_0_85S_pct',
        'scenario_pnl_0_90S', 'scenario_pnl_0_90S_cny', 'scenario_pnl_0_90S_pct',
        'unhedged_pnl_0_90S', 'unhedged_pnl_0_90S_pct',
        'scenario_pnl_0_95S', 'scenario_pnl_0_95S_cny', 'scenario_pnl_0_95S_pct',
        'unhedged_pnl_0_95S', 'unhedged_pnl_0_95S_pct',
        'scenario_pnl_1_00S', 'scenario_pnl_1_00S_cny', 'scenario_pnl_1_00S_pct',
        'unhedged_pnl_1_00S', 'unhedged_pnl_1_00S_pct',
        'scenario_pnl_1_05S', 'scenario_pnl_1_05S_cny', 'scenario_pnl_1_05S_pct',
        'unhedged_pnl_1_05S', 'unhedged_pnl_1_05S_pct',
        'scenario_pnl_1_10S', 'scenario_pnl_1_10S_cny', 'scenario_pnl_1_10S_pct',
        'unhedged_pnl_1_10S', 'unhedged_pnl_1_10S_pct',
        'scenario_pnl_1_15S', 'scenario_pnl_1_15S_cny', 'scenario_pnl_1_15S_pct',
        'unhedged_pnl_1_15S', 'unhedged_pnl_1_15S_pct',
        # 交易信号
        'trade_signal', 'signal_reason',
    ]

    # === 情景系数（S_T = S0 × factor） ===
    DEFAULT_SCENARIOS = [0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15]

    # === 组合配对参数（约束剪枝） ===
    STRIKE_RANGE = 2      # 行权价限定 ATM ± 2 档（条式价值集中在平值附近）

    # ================================================================
    # Step 4: 组合配对 + 核心策略盈亏（风控三问）
    # ================================================================
    def calc_strategy_pnl(self, df):
        """Strip 核心盈亏指标（组合粒度）

        配对: 买入 1 份 Call(K) + 买入 2 份 Put(K)，同价同行权价，净支出 T = C + 2P
        到期组合收益 = max(0,S_T-K) + 2*max(0,K-S_T) - T
        （不对称 V 形：下行斜率 2 倍、上行斜率 1 倍，亏损封底 T，盈利无上限）
        盈亏平衡点: 上 = K+T（1份Call需涨过全成本），下 = K-T/2（2份Put跌半程即回本）
        """
        logger.info("Building strip pairs "
                    f"(same-strike 1C+2P, ATM±{self.STRIKE_RANGE}档)...")

        # ---------- 0. 组合配对（约束剪枝：ATM±2档的同价 Call+Put） ----------
        df = self._build_pairs(df)
        if df.empty:
            logger.warning("No strip pairs built, skip P&L calculation")
            return df
        logger.info(f"Built {len(df)} combo rows "
                    f"({df.groupby('trade_date').size().max()} combos/day max)")

        S = df['spot_price'].values.astype(float)
        K = df['exercise_price'].values.astype(float)
        C = df['premium'].values.astype(float)
        P = df['premium_put'].values.astype(float)
        mult = df['opt_multiplier'].values.astype(float)

        delta_c = df['delta'].values.astype(float)
        gamma_c = df['gamma'].values.astype(float)
        theta_c = df['theta'].values.astype(float)
        vega_c = df['vega'].values.astype(float)
        delta_p = df['delta_put'].values.astype(float)
        gamma_p = df['gamma_put'].values.astype(float)
        theta_p = df['theta_put'].values.astype(float)
        vega_p = df['vega_put'].values.astype(float)

        # ---------- 1. 条式结构（花了多少：三腿合计 T = C + 2P） ----------
        T = self.W_CALL * C + self.W_PUT * P
        df['total_premium'] = T
        df['total_premium_cny'] = T * mult
        df['total_premium_pct_of_spot'] = np.where(S > 0, T / S * 100, np.nan)

        # ---------- 2. 收益结构（亏损封底 T，盈利无上限，不对称 V 形） ----------
        df['max_loss'] = T
        df['max_loss_cny'] = T * mult
        df['max_loss_pct_of_spot'] = np.where(S > 0, T / S * 100, np.nan)
        # max_profit 不适用（盈利无上限），不落列，报表用收益结构图与情景列刻画

        # 不对称盈亏平衡点（条式的结构特征）：
        #   上行仅 1 份 Call 盈利 → 需涨过整个成本 T
        #   下行 2 份 Put 盈利双倍 → 只需跌过 T/2
        be_up = K + T
        be_dn = K - T / self.W_PUT
        df['breakeven_up'] = be_up
        df['breakeven_up_pct'] = np.where(S > 0, (be_up - S) / S * 100, np.nan)
        df['breakeven_down'] = be_dn
        df['breakeven_down_pct'] = np.where(S > 0, (be_dn - S) / S * 100, np.nan)
        # 盈亏平衡区间宽度 = 1.5T/S0：条式比同成本跨式(2T/S0)更窄（下行半程即回本）
        df['breakeven_range_pct'] = np.where(S > 0, 1.5 * T / S * 100, np.nan)

        # ---------- 3. 组合净 Greeks（1C + 2P 加权） ----------
        # 净 Delta 为负（ATM 附近约 -0.5）：偏空波动率的量化表达
        df['net_delta'] = np.where(pd.notna(delta_c) & pd.notna(delta_p),
                                   self.W_CALL * delta_c + self.W_PUT * delta_p, np.nan)
        df['net_gamma'] = np.where(pd.notna(gamma_c) & pd.notna(gamma_p),
                                   self.W_CALL * gamma_c + self.W_PUT * gamma_p, np.nan)
        # 三腿 theta 同为负：时间损耗比跨式双腿更重（条式买方的时间敌人）
        df['net_theta'] = np.where(pd.notna(theta_c) & pd.notna(theta_p),
                                   self.W_CALL * theta_c + self.W_PUT * theta_p, np.nan)
        df['net_vega'] = np.where(pd.notna(vega_c) & pd.notna(vega_p),
                                  self.W_CALL * vega_c + self.W_PUT * vega_p, np.nan)

        # ---------- 4. 胜率与评分（偏空波动率买方视角） ----------
        # σ = 双腿 IV 加权均值（Put 权重 2/3，条式下行的主引擎）
        iv_c = df['implied_vol'].values.astype(float)
        iv_p = df['implied_vol_put'].values.astype(float)
        years = df['years_to_maturity_calendar'].values.astype(float)
        w_sum = self.W_CALL + self.W_PUT
        sigma = np.where(pd.notna(iv_c) & pd.notna(iv_p),
                         (self.W_CALL * iv_c + self.W_PUT * iv_p) / w_sum, np.nan)

        # 1σ 预期波动幅度 = σ√T年（模型隐含的到期波动半径）
        with np.errstate(invalid='ignore'):
            sig_t = sigma * np.sqrt(np.where(years > 0, years, np.nan))
        df['expected_move_1sigma_pct'] = np.where(pd.notna(sig_t), sig_t * 100, np.nan)

        # 胜率 = P(S_T > K+T) + P(S_T < K-T/2)，对数正态（风险中性近似）
        # 注意下行门槛 T/2 是下行侧的结构优势：跌更容易回本
        lnS = np.log(np.where(S > 0, S, np.nan))
        p_up = np.full(len(df), np.nan)
        p_dn = np.full(len(df), np.nan)
        ok = (pd.notna(sigma)) & (sigma > 0) & pd.notna(sig_t) & (sig_t > 0) & pd.notna(lnS)
        for i in np.where(ok)[0]:
            z_up = (np.log(be_up[i]) - lnS[i]) / sig_t[i]
            p_up[i] = 1.0 - _norm_cdf(z_up)
            if be_dn[i] > 0:
                z_dn = (np.log(be_dn[i]) - lnS[i]) / sig_t[i]
                p_dn[i] = _norm_cdf(z_dn)
            else:  # 下平衡点跌破 0：下行必然盈利（极端保护价情形）
                p_dn[i] = 1.0
        df['win_prob'] = np.where(ok, p_up + p_dn, np.nan)

        # 期望值 = (BS_C − C) + 2*(BS_P − P)：Put 腿权重加倍（占 2/3 成本）
        bs_c = df['bs_theoretical_price'].values.astype(float)
        bs_p = df['bs_theoretical_price_put'].values.astype(float)
        ev = np.where(pd.notna(bs_c) & pd.notna(bs_p) & pd.notna(C) & pd.notna(P),
                      (bs_c - C) * self.W_CALL + (bs_p - P) * self.W_PUT, np.nan)
        df['expected_value'] = ev
        # 评分 = 期望值/总成本（风险调整后收益，同日候选行权价排名依据）
        df['score'] = np.where(pd.notna(ev) & (T > 0), ev / T, np.nan)

        # 同日组合排名（1=评分最高）
        df['combo_rank'] = df.groupby('trade_date')['score'].rank(
            ascending=False, method='first').fillna(0).astype(int)

        # ---------- 5. 双腿定价偏差（买条式：双腿均便宜才有利，Put 更关键） ----------
        df['close_vs_theoretical'] = np.where(pd.notna(bs_c) & pd.notna(C), C - bs_c, np.nan)
        df['close_vs_theoretical_pct'] = np.where(
            pd.notna(bs_c) & (bs_c > 0), (C - bs_c) / bs_c * 100, np.nan)
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
        df['close_vs_theoretical_put'] = np.where(
            pd.notna(bs_p) & pd.notna(P), P - bs_p, np.nan)
        df['close_vs_theoretical_pct_put'] = np.where(
            pd.notna(bs_p) & (bs_p > 0), (P - bs_p) / bs_p * 100, np.nan)
        df['price_bias_put'] = np.select(
            [
                df['close_vs_theoretical_pct_put'] < -5,
                (df['close_vs_theoretical_pct_put'] >= -5) & (df['close_vs_theoretical_pct_put'] < -1),
                (df['close_vs_theoretical_pct_put'] >= -1) & (df['close_vs_theoretical_pct_put'] <= 1),
                (df['close_vs_theoretical_pct_put'] > 1) & (df['close_vs_theoretical_pct_put'] <= 5),
                df['close_vs_theoretical_pct_put'] > 5,
            ],
            ['严重低估', '低估', '公允', '高估', '严重高估'],
            default='N/A'
        )

        # ---------- 摘要日志 ----------
        logger.info(f"Strategy P&L calculated for {len(df)} combo rows")
        valid = df['score'].notna().sum()
        if valid > 0:
            logger.info(f"  total_premium_pct_of_spot: mean={df['total_premium_pct_of_spot'].mean():.2f}%, "
                        f"best={df['total_premium_pct_of_spot'].min():.2f}%")
            logger.info(f"  win_prob: mean={df['win_prob'].mean():.2f}")
            logger.info(f"  net_delta: mean={df['net_delta'].mean():.3f} (负值=偏空敞口)")
            best = df[df['combo_rank'] == 1]
            if not best.empty:
                last = best.iloc[-1]
                logger.info(f"  latest best combo: K={last['exercise_price']:.4g}, "
                            f"score={last['score']:.3f}")
        return df

    # ================================================================
    # 组合配对（约束剪枝）
    # ================================================================
    def _build_pairs(self, df):
        """按交易日配对生成条式组合（Call 腿 + 同行权价 Put 腿，权重 1:2）

        约束: 行权价 ∈ ATM±2 档，且该档位同时存在 Call 与 Put（同月同价）
        输出: 每行一个组合（Call腿字段无后缀，Put腿字段带 _put 后缀，
              premium/premium_put 为单份收盘价，1:2 权重在聚合字段体现）
        """
        frames = []
        n_dates = 0
        for trade_date, g in df.groupby('trade_date', sort=True):
            n_dates += 1
            g = g.dropna(subset=['exercise_price', 'close'])
            if g.empty:
                continue

            # 分方向按行权价索引（同月同方向每档一条）
            by_strike_c = {float(row['exercise_price']): row
                           for _, row in g[g['call_put'] == 'C'].iterrows()}
            by_strike_p = {float(row['exercise_price']): row
                           for _, row in g[g['call_put'] == 'P'].iterrows()}
            common = sorted(set(by_strike_c.keys()) & set(by_strike_p.keys()))
            if not common:
                continue

            S0 = float(g['spot_price'].iloc[0])
            atm_idx = int(np.abs(np.array(common) - S0).argmin())

            lo = max(0, atm_idx - self.STRIKE_RANGE)
            hi = min(len(common) - 1, atm_idx + self.STRIKE_RANGE)

            for i in range(lo, hi + 1):
                row_c = by_strike_c[common[i]]
                row_p = by_strike_p[common[i]]
                frames.append({
                    'trade_date': trade_date,
                    # Call 腿（无后缀）
                    'ts_code': row_c['ts_code'],
                    'symbol': row_c['symbol'],
                    'opt_name': row_c['opt_name'],
                    'opt_exchange': row_c['opt_exchange'],
                    # Put 腿（_put）
                    'ts_code_put': row_p['ts_code'],
                    'symbol_put': row_p['symbol'],
                    'opt_name_put': row_p['opt_name'],
                    # 条式双腿（1C+2P）
                    'call_put': 'CP',
                    # 合约要素（同到期月同行权价）
                    'exercise_price': common[i],
                    'opt_multiplier': row_c['opt_multiplier'],
                    's_month': row_c['s_month'],
                    'maturity_date': row_c['maturity_date'],
                    'days_to_maturity': row_c['days_to_maturity'],
                    'years_to_maturity_calendar': row_c['years_to_maturity_calendar'],
                    # 标的市场
                    'spot_price': S0,
                    'moneyness_status': row_c['moneyness_status'],
                    'risk_free_rate': row_c['risk_free_rate'],
                    'dividend_yield': row_c['dividend_yield'],
                    # 双腿行情与定价（单份价格）
                    'premium': float(row_c['close']),
                    'premium_put': float(row_p['close']),
                    'implied_vol': row_c['implied_vol'],
                    'implied_vol_put': row_p['implied_vol'],
                    'iv_rank': row_c['iv_rank'],
                    'iv_rank_put': row_p['iv_rank'],
                    # 双腿 Greeks（单份，净敞口按 1:2 加权）
                    'delta': row_c['delta'],
                    'gamma': row_c['gamma'],
                    'theta': row_c['theta'],
                    'vega': row_c['vega'],
                    'delta_put': row_p['delta'],
                    'gamma_put': row_p['gamma'],
                    'theta_put': row_p['theta'],
                    'vega_put': row_p['vega'],
                    # 双腿理论价
                    'bs_theoretical_price': row_c['bs_theoretical_price'],
                    'bs_theoretical_price_put': row_p['bs_theoretical_price'],
                })

        logger.info(f"Pairing done: {n_dates} trade dates -> {len(frames)} combos")
        return pd.DataFrame(frames)

    # ================================================================
    # Step 5: 多情景盈亏（含买现货对照）
    # ================================================================
    def calc_scenario_pnl(self, df, scenarios=None):
        """多情景盈亏：S_T = S0 * factor

        条式组合 P&L = max(0,S_T-K) + 2*max(0,K-S_T) - T（不对称 V 形）
        —— 下行情景盈利双倍放大（2 份 Put），上行情景单倍（1 份 Call）
        买现货对照 P&L = S_T - S0（对照组，衡量条式相对纯多头的差异）
        收益率基准 = 总成本 T（条式的本金即最大风险）
        """
        if df.empty:
            return df
        if scenarios is None:
            scenarios = self.DEFAULT_SCENARIOS

        logger.info(f"Calculating multi-scenario P&L for {len(scenarios)} scenarios: {scenarios}")

        S = df['spot_price'].values.astype(float)
        K = df['exercise_price'].values.astype(float)
        T = df['total_premium'].values.astype(float)
        mult = df['opt_multiplier'].values.astype(float)

        for factor in scenarios:
            s_T = S * factor

            # 条式组合盈亏（下行斜率 2 倍、上行 1 倍，谷底亏损 T）
            combo_pnl = (self.W_CALL * np.maximum(s_T - K, 0)
                         + self.W_PUT * np.maximum(K - s_T, 0) - T)
            label = f'{factor:.2f}'.replace('.', '_')
            df[f'scenario_pnl_{label}S'] = combo_pnl
            df[f'scenario_pnl_{label}S_cny'] = combo_pnl * mult
            df[f'scenario_pnl_{label}S_pct'] = np.where(
                T > 0, combo_pnl / T * 100, np.nan)

            # 买现货对照
            unhedged_pnl = s_T - S
            df[f'unhedged_pnl_{label}S'] = unhedged_pnl
            df[f'unhedged_pnl_{label}S_pct'] = np.where(
                S > 0, unhedged_pnl / S * 100, np.nan)

        logger.info("Multi-scenario P&L calculated")
        return df

    # ================================================================
    # Step 6: 交易信号（偏空波动率买方视角）
    # ================================================================
    def _assign_trade_signals(self, df):
        """分配交易信号

        条式买方三个维度（找"便宜的波动率 + 偏空的事件窗口"）：
          1. iv_rank（加权）：IV 分位按腿权重 1:2 加权（Put 占 2/3，
             下行是条式的主引擎，Put 的贵贱更关键）
          2. expected_value：(BS_C−C) + 2*(BS_P−P)，市价低于理论价的幅度
          3. 天数：距到期太近三腿 theta 加速损耗，太远时间成本过高
        注意：条式胜率天然 < 50%（小概率高赔率），信号不依赖胜率；
        且净 Delta 为负——信号隐含"波动兑现时更看跌"的判断。
        """
        if df.empty:
            return df

        ivr_c = df['iv_rank'].values
        ivr_p = df['iv_rank_put'].values
        ev = df['expected_value'].values
        days = df['days_to_maturity'].values
        tp_pct = df['total_premium_pct_of_spot'].values
        wp = df['win_prob'].values
        em = df['expected_move_1sigma_pct'].values
        nd = df['net_delta'].values

        # IV 分位按腿权重加权（Put 占 2/3——条式下行的主引擎）
        w_sum = self.W_CALL + self.W_PUT
        ivr_avg = np.where(pd.notna(ivr_c) & pd.notna(ivr_p),
                           (self.W_CALL * ivr_c + self.W_PUT * ivr_p) / w_sum, np.nan)

        signals = np.full(len(df), 'AVOID', dtype=object)
        signal_reasons = np.full(len(df), '', dtype=object)

        for i in range(len(df)):
            ic, ip = ivr_c[i], ivr_p[i]
            ia = ivr_avg[i]
            ev_i = ev[i]
            days_i = days[i]
            tp_i = tp_pct[i]
            wp_i = wp[i]
            em_i = em[i]
            nd_i = nd[i]

            if pd.isna(ia) and pd.isna(ev_i):
                signals[i] = 'N/A'
                signal_reasons[i] = '数据不足'
                continue

            reasons = []

            if (not pd.isna(ic)) and (not pd.isna(ip)) and ic <= 0.35 and ip <= 0.35 \
                    and (not pd.isna(ev_i)) and ev_i > 0:
                signals[i] = 'STRONG_BUY'
                reasons.append(f'Call IV分位={ic:.2f}<=0.35')
                reasons.append(f'Put IV分位={ip:.2f}<=0.35(占2/3成本, 更关键)')
                reasons.append(f'期望值={ev_i:+.4g}>0(市价低于理论价)')
            elif (not pd.isna(ia)) and ia <= 0.50 and \
                    ((pd.isna(ev_i)) or ev_i >= 0):
                signals[i] = 'BUY'
                reasons.append(f'加权IV分位={ia:.2f}<=0.50(Put权重2/3)')
                if not pd.isna(ev_i):
                    reasons.append(f'期望值={ev_i:+.4g}')
            elif (not pd.isna(ia)) and ia <= 0.65:
                signals[i] = 'CONSIDER'
                reasons.append(f'加权IV分位={ia:.2f}<=0.65')
            elif (not pd.isna(ia)) and ia <= 0.80:
                signals[i] = 'NEUTRAL'
                reasons.append(f'加权IV分位={ia:.2f}')
            else:
                signals[i] = 'AVOID'
                reasons.append(f'加权IV分位={ia if not pd.isna(ia) else np.nan:.2f}>=0.80'
                               if not pd.isna(ia) else 'IV分位缺失')

            # 补充风控理由（条式买方专属）
            if pd.notna(nd_i) and nd_i >= 0:
                reasons.append(f'净Delta={nd_i:+.3f}>=0(偏空敞口不足, 与条式定位不符, 请核对行情)')
            if pd.notna(days_i) and days_i < 10:
                reasons.append(f'仅剩{days_i:.0f}天到期, 三腿Theta加速损耗, 建议了结或移仓')
            elif pd.notna(days_i) and days_i > 60:
                reasons.append(f'距到期{days_i:.0f}天>60(三腿时间成本高, 优选事件窗口)')
            if pd.notna(tp_i) and tp_i > 8:
                reasons.append(f'三腿成本占现价{tp_i:.1f}%>8%(上行需涨>{tp_i:.1f}%才回本)')
            if pd.notna(wp_i) and wp_i < 0.25:
                reasons.append(f'胜率{wp_i:.2f}<0.25(小概率高赔率, 需严格止损=-T)')
            if (not pd.isna(ic)) and ic >= 0.65:
                reasons.append(f'Call IV分位={ic:.2f}>=0.65(波动率买贵了)')
            if (not pd.isna(ip)) and ip >= 0.65:
                reasons.append(f'Put IV分位={ip:.2f}>=0.65(占2/3成本, 买贵影响更大)')
            if pd.notna(em_i) and pd.notna(tp_i) and tp_i / 2 > em_i:
                reasons.append(f'下行回本距离T/2={tp_i/2:.1f}%>1σ波动{em_i:.1f}%'
                               f'(即便有利侧也需超1σ波动才回本, 定价偏贵)')

            signal_reasons[i] = '; '.join(reasons)

        df['trade_signal'] = signals
        df['signal_reason'] = signal_reasons

        signal_counts = pd.Series(signals).value_counts()
        logger.info(f"Trade signals: {signal_counts.to_dict()}")

        return df

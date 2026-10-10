r"""
Short Strangle（卖出宽跨式）策略分析 — 高级交易员/风控视角

策略定义：卖出低行权价认沽 Put(K1) + 卖出高行权价认购 Call(K2)，K1 < K2，同到期月
净收入 T = P + C（双腿均为虚值 OTM，比同月跨式 Straddle 收得少）
组合到期收益 = T - max(0,S_T-K2) - max(0,K1-S_T)
—— 教科书"倒 V 平顶"（截顶版）：S_T ∈ [K1,K2] 时双腿同时归零，
   盈利平坦封顶 T（跨式卖方只有 S_T=K 单点顶，宽跨式卖方是"平台"收租区）

策略特点（与 Short Straddle 的本质差异）：
  1. 双腿行权价不同（K1 < K2）：与买宽跨式的唯一结构差异——
     卖出的是"缺口两侧的 OTM 保险"，双腿天然虚值
  2. 平坦盈利区 [K1, K2]：到期价落在两腿之间时双腿同时归零、
     盈利恒为 T（跨式只有 S_T=K 一个顶点）——收租"平台"而非"尖顶"，
     这是卖宽跨式相对卖跨式的核心卖点
  3. 更高的胜率：安全垫区间 [K1-T, K2+T] 宽度 = (K2-K1)+2T
     （跨式仅 2T）——缺口加厚了安全垫，胜率天然高于卖跨式
  4. 更薄的权利金：OTM 双腿收到的租比 ATM 跨式少——
     用"收得更少"换"击穿概率更低"，与买宽跨式的权衡完全镜像
  5. 净 Delta ≈ 0（方向中性卖波动率）、双腿净 Theta 为正（时间双倍收入）、
     双腿净 Vega 为负（IV 回升双腿同时受损）——亏损无上限（双向裸卖），
     风险管理优先级高于收益追求

组合配对（三层漏斗第1层——约束剪枝，控制组合爆炸，跨档配对借鉴价差类）：
  1. 同一到期月（symbol_filter 保证，方向不限 C+P）
  2. Put 腿 K1 ∈ ATM 下方 0~2 档（虚值/平值）
  3. Call 腿 K2 ∈ ATM 上方 0~2 档（平值/虚值），且 K2 > K1（宽跨式定义）
  每日至多 3x3-1=8 个候选组合全量落库（透明可回溯），信号端按综合评分排序

风控三问（宽跨式卖方视角）：
  1. 收了多少（租金）：total_premium = P + C（即最大盈利，也是安全垫的"半宽"基础）
  2. 多大概率赚（胜率）：win_prob = P(K1-T <= S_T <= K2+T)
     —— 缺口 K2-K1 加厚安全垫，宽跨式卖方胜率天然高于跨式卖方
  3. 值不值（定价）：expected_value = (C-BS_C) + (P-BS_P)
     —— 双腿均卖出虚值：市价比理论贵（微笑曲线两端的斜率）才有正期望

数据源：
  - tb_tusharse_opt_daily_indicator : 现货价、BS定价、Greeks（原料）
  - df_tushare_opt_basic           : symbol/name 反查（ETF 期权 ts_code 为8位数字）

落库：
  - tb_option_trading_strategy_short_strangle : strategy_type='SHORT_STRANGLE'，
    每行一个组合（Call腿字段无后缀，Put腿字段带 _put 后缀；
    exercise_price = K2(Call腿)，exercise_price_put = K1(Put腿)，K1 < K2）

使用（symbol 直接指定标的+到期月，方向传 None 同时取 C/P）：
  config = {
      "name": "华夏上证50ETF期权（Short Strangle）",
      "start_date": "20251222",
      "end_date": CommonParameters.today,
      "call_put": None,
      "symbol_filter": "510050%2612%",
  }
  ShortStrangleStrategyAnalysis().run(config)
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


class ShortStrangleStrategyAnalysis(OptionStrategyBase):
    """Short Strangle 策略分析器（卖 Put(K1) + 卖 Call(K2)，K1<K2，卖出宽跨式）

    分析维度：跨档配对（约束剪枝，借鉴价差类）、行权价缺口、双腿总租金、
    对数正态胜率（缺口加厚安全垫）、定价偏差期望值与评分排序、
    净 Greeks（卖方敞口取负叠加）、多情景盈亏（平坦盈利区，含买现货对照）。
    """

    # === 策略标识 ===
    STRATEGY_TYPE = 'SHORT_STRANGLE'
    ANALYSIS_VERSION = 'v1'
    TABLE_TARGET = 'tb_option_trading_strategy_short_strangle'

    # === 目标表字段（与 tb_option_trading_strategy_short_strangle.sql 建表一致） ===
    TARGET_COLUMNS = [
        # 策略标识与审计
        'strategy_type', 'analysis_time', 'analysis_params', 'analysis_version',
        # 组合标识（Call腿无后缀，Put腿带 _put）
        'trade_date', 'ts_code', 'symbol', 'opt_name', 'opt_exchange', 'call_put',
        'ts_code_put', 'symbol_put', 'opt_name_put',
        # 合约要素（宽跨式双腿行权价不同：K2 > K1）
        'exercise_price', 'exercise_price_put', 'opt_multiplier', 's_month',
        'maturity_date', 'days_to_maturity',
        # 标的市场
        'spot_price', 'moneyness_status', 'risk_free_rate', 'dividend_yield',
        # 双腿行情与定价
        'premium', 'premium_put', 'implied_vol', 'implied_vol_put',
        'iv_rank', 'iv_rank_put',
        # 双腿 Greeks
        'delta', 'gamma', 'theta', 'vega',
        'delta_put', 'gamma_put', 'theta_put', 'vega_put',
        # 双腿定价偏差
        'bs_theoretical_price', 'close_vs_theoretical', 'close_vs_theoretical_pct', 'price_bias',
        'bs_theoretical_price_put', 'close_vs_theoretical_put',
        'close_vs_theoretical_pct_put', 'price_bias_put',
        # 组合净 Greeks（双腿同为卖出，敞口取负叠加）
        'net_delta', 'net_gamma', 'net_theta', 'net_vega',
        # 宽跨式结构（收了多少：行权价缺口 + 双腿合计租金）
        'strike_gap', 'strike_gap_pct',
        'total_premium', 'total_premium_cny', 'total_premium_pct_of_spot',
        'expected_move_1sigma_pct',
        # 收益结构（平坦盈利区 [K1,K2]，亏损无上限）
        'max_profit', 'max_profit_cny', 'max_profit_pct_of_spot',
        'breakeven_up', 'breakeven_up_pct',
        'breakeven_down', 'breakeven_down_pct', 'breakeven_range_pct',
        # 概率与评分
        'win_prob', 'expected_value', 'score', 'combo_rank',
        # 多情景盈亏（S_T = S0 * factor，平坦盈利区，含买现货对照）
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

    # === 组合配对参数（约束剪枝，跨档配对借鉴价差类） ===
    PUT_LEG_ATM_RANGE = 2    # Put 腿 K1 ∈ ATM 下方 0~2 档（虚值/平值）
    CALL_LEG_ATM_RANGE = 2   # Call 腿 K2 ∈ ATM 上方 0~2 档（平值/虚值）

    # ================================================================
    # Step 4: 组合配对 + 核心策略盈亏（风控三问）
    # ================================================================
    def calc_strategy_pnl(self, df):
        """Short Strangle 核心盈亏指标（组合粒度）

        配对: 卖出 Put(K1) + 卖出 Call(K2)，K1 < K2，净收入 T = P + C
        到期组合收益 = T - max(0,S_T-K2) - max(0,K1-S_T)
        （S_T∈[K1,K2] 时双腿同时归零——平坦盈利区，恒收 T；双侧亏损无上限）
        盈亏平衡点: 上 = K2+T，下 = K1-T（缺口 K2-K1 加厚安全垫）
        """
        logger.info("Building short strangle pairs "
                    f"(Put leg ATM-0~{self.PUT_LEG_ATM_RANGE}档 × "
                    f"Call leg ATM+0~{self.CALL_LEG_ATM_RANGE}档, K1<K2)...")

        # ---------- 0. 组合配对（约束剪枝：Put下方×Call上方跨档配对） ----------
        df = self._build_pairs(df)
        if df.empty:
            logger.warning("No short strangle pairs built, skip P&L calculation")
            return df
        logger.info(f"Built {len(df)} combo rows "
                    f"({df.groupby('trade_date').size().max()} combos/day max)")

        S = df['spot_price'].values.astype(float)
        K2 = df['exercise_price'].values.astype(float)        # Call 腿（高行权价）
        K1 = df['exercise_price_put'].values.astype(float)    # Put 腿（低行权价）
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

        # ---------- 1. 宽跨式结构（收了多少：缺口 + 双腿合计租金） ----------
        gap = K2 - K1
        T = P + C
        # 行权价缺口 K2-K1：拉宽平坦盈利区、也加厚安全垫的结构性因素
        df['strike_gap'] = gap
        df['strike_gap_pct'] = np.where(S > 0, gap / S * 100, np.nan)
        df['total_premium'] = T
        df['total_premium_cny'] = T * mult
        df['total_premium_pct_of_spot'] = np.where(S > 0, T / S * 100, np.nan)

        # ---------- 2. 收益结构（平坦盈利区 [K1,K2]，亏损无上限） ----------
        # S_T ∈ [K1,K2] 时双腿同时归零：盈利恒为 T（不是跨式卖方的单点顶，是"平台"收租区）
        df['max_profit'] = T
        df['max_profit_cny'] = T * mult
        df['max_profit_pct_of_spot'] = np.where(S > 0, T / S * 100, np.nan)
        # max_loss 不适用（亏损无上限），不落列，报表用倒V平顶图与情景列刻画

        # 双侧盈亏平衡点（缺口加厚：上=K2+T，下=K1-T）
        be_up = K2 + T
        be_dn = K1 - T
        df['breakeven_up'] = be_up
        df['breakeven_up_pct'] = np.where(S > 0, (be_up - S) / S * 100, np.nan)
        df['breakeven_down'] = be_dn
        df['breakeven_down_pct'] = np.where(S > 0, (be_dn - S) / S * 100, np.nan)
        # 安全垫区间宽度 = (K2-K1) + 2T（跨式仅 2T）：缺口加厚了收租安全垫
        df['breakeven_range_pct'] = np.where(
            S > 0, (gap + 2 * T) / S * 100, np.nan)

        # ---------- 3. 组合净 Greeks（双腿同为卖出，敞口取负叠加） ----------
        # 净 Delta ≈ 0（两腿对称 OTM 时近似对冲，方向中性）
        df['net_delta'] = np.where(pd.notna(delta_c) & pd.notna(delta_p),
                                   -(delta_c + delta_p), np.nan)
        df['net_gamma'] = np.where(pd.notna(gamma_c) & pd.notna(gamma_p),
                                   -(gamma_c + gamma_p), np.nan)
        # 双腿 theta 同为负，卖出取负：时间双倍收入（宽跨式卖方的时间朋友）
        df['net_theta'] = np.where(pd.notna(theta_c) & pd.notna(theta_p),
                                   -(theta_c + theta_p), np.nan)
        df['net_vega'] = np.where(pd.notna(vega_c) & pd.notna(vega_p),
                                  -(vega_c + vega_p), np.nan)

        # ---------- 4. 胜率与评分（波动率卖方视角，缺口加厚安全垫） ----------
        # σ = 双腿 IV 均值（1:1，两腿对称）
        iv_c = df['implied_vol'].values.astype(float)
        iv_p = df['implied_vol_put'].values.astype(float)
        years = df['years_to_maturity_calendar'].values.astype(float)
        sigma = np.where(pd.notna(iv_c) & pd.notna(iv_p), (iv_c + iv_p) / 2, np.nan)

        # 1σ 预期波动幅度 = σ√T年（模型隐含的到期波动半径）
        with np.errstate(invalid='ignore'):
            sig_t = sigma * np.sqrt(np.where(years > 0, years, np.nan))
        df['expected_move_1sigma_pct'] = np.where(pd.notna(sig_t), sig_t * 100, np.nan)

        # 卖方胜率 = P(K1-T <= S_T <= K2+T)，对数正态（风险中性近似）
        # = 1 - 买宽跨式胜率：缺口 K2-K1 加厚安全垫——宽跨式卖方胜率天然高于跨式卖方
        lnS = np.log(np.where(S > 0, S, np.nan))
        p_win = np.full(len(df), np.nan)
        ok = (pd.notna(sigma)) & (sigma > 0) & pd.notna(sig_t) & (sig_t > 0) & pd.notna(lnS)
        for i in np.where(ok)[0]:
            z_up = (np.log(be_up[i]) - lnS[i]) / sig_t[i]
            p_out_up = 1.0 - _norm_cdf(z_up)
            if be_dn[i] > 0:
                z_dn = (np.log(be_dn[i]) - lnS[i]) / sig_t[i]
                p_out_dn = _norm_cdf(z_dn)
            else:  # 下平衡点跌破 0：下行不可能击穿（极端深度 OTM 情形）
                p_out_dn = 0.0
            p_win[i] = 1.0 - p_out_up - p_out_dn
        df['win_prob'] = np.where(ok, p_win, np.nan)

        # 期望值 = (C − BS_C) + (P − BS_P)：双腿均贵才有利（卖方正期望）
        bs_c = df['bs_theoretical_price'].values.astype(float)
        bs_p = df['bs_theoretical_price_put'].values.astype(float)
        ev = np.where(pd.notna(bs_c) & pd.notna(bs_p) & pd.notna(C) & pd.notna(P),
                      (C - bs_c) + (P - bs_p), np.nan)
        df['expected_value'] = ev
        # 评分 = 期望值/总租金（风险调整后收益，同日候选组合排名依据）
        df['score'] = np.where(pd.notna(ev) & (T > 0), ev / T, np.nan)

        # 同日组合排名（1=评分最高）
        df['combo_rank'] = df.groupby('trade_date')['score'].rank(
            ascending=False, method='first').fillna(0).astype(int)

        # ---------- 5. 双腿定价偏差（卖宽跨式：双腿均贵才有利，OTM腿看微笑两端） ----------
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
                        f"best={df['total_premium_pct_of_spot'].max():.2f}%")
            logger.info(f"  breakeven_range_pct(safety): mean={df['breakeven_range_pct'].mean():.2f}%")
            logger.info(f"  win_prob: mean={df['win_prob'].mean():.2f}")
            best = df[df['combo_rank'] == 1]
            if not best.empty:
                last = best.iloc[-1]
                logger.info(f"  latest best combo: K1={last['exercise_price_put']:.4g}/"
                            f"K2={last['exercise_price']:.4g}, "
                            f"score={last['score']:.3f}")
        return df

    # ================================================================
    # 组合配对（约束剪枝，跨档配对借鉴价差类）
    # ================================================================
    def _build_pairs(self, df):
        """按交易日配对生成宽跨式组合（低行权价 Put 腿 + 高行权价 Call 腿）

        约束: K1(Put) ∈ ATM 下方 0~2 档，K2(Call) ∈ ATM 上方 0~2 档，且 K2 > K1
        输出: 每行一个组合（Call腿字段无后缀，Put腿字段带 _put 后缀，
              exercise_price = K2，exercise_price_put = K1）
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

            # Put 腿 K1: ATM 下方 0~2 档（含 ATM）
            p_lo = max(0, atm_idx - self.PUT_LEG_ATM_RANGE)
            p_hi = atm_idx
            # Call 腿 K2: ATM 上方 0~2 档（含 ATM）
            c_lo = atm_idx
            c_hi = min(len(common) - 1, atm_idx + self.CALL_LEG_ATM_RANGE)

            for ip in range(p_lo, p_hi + 1):
                row_p = by_strike_p[common[ip]]
                K1 = common[ip]
                for ic in range(c_lo, c_hi + 1):
                    if ic <= ip:  # 宽跨式定义：K2 > K1（等价于跨式的组合跳过）
                        continue
                    row_c = by_strike_c[common[ic]]
                    K2 = common[ic]
                    frames.append({
                        'trade_date': trade_date,
                        # Call 腿（无后缀，K2 高行权价）
                        'ts_code': row_c['ts_code'],
                        'symbol': row_c['symbol'],
                        'opt_name': row_c['opt_name'],
                        'opt_exchange': row_c['opt_exchange'],
                        # Put 腿（_put，K1 低行权价）
                        'ts_code_put': row_p['ts_code'],
                        'symbol_put': row_p['symbol'],
                        'opt_name_put': row_p['opt_name'],
                        # 宽跨式双腿（K1 < K2）
                        'call_put': 'CP',
                        # 合约要素（同到期月，双腿行权价不同）
                        'exercise_price': K2,
                        'exercise_price_put': K1,
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
                        # 双腿行情与定价
                        'premium': float(row_c['close']),
                        'premium_put': float(row_p['close']),
                        'implied_vol': row_c['implied_vol'],
                        'implied_vol_put': row_p['implied_vol'],
                        'iv_rank': row_c['iv_rank'],
                        'iv_rank_put': row_p['iv_rank'],
                        # 双腿 Greeks
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

        宽跨式卖方组合 P&L = T - max(0,S_T-K2) - max(0,K1-S_T)
        —— S_T ∈ [K1,K2] 时盈利恒为 T（平坦盈利区，比跨式卖方单点顶的收租面更宽）
        买现货对照 P&L = S_T - S0（对照组，衡量卖方相对纯多头的差异）
        收益率基准 = 总租金 T（宽跨式卖方的最大收益/保证金 proxy）
        """
        if df.empty:
            return df
        if scenarios is None:
            scenarios = self.DEFAULT_SCENARIOS

        logger.info(f"Calculating multi-scenario P&L for {len(scenarios)} scenarios: {scenarios}")

        S = df['spot_price'].values.astype(float)
        K2 = df['exercise_price'].values.astype(float)
        K1 = df['exercise_price_put'].values.astype(float)
        T = df['total_premium'].values.astype(float)
        mult = df['opt_multiplier'].values.astype(float)

        for factor in scenarios:
            s_T = S * factor

            # 宽跨式卖方组合盈亏（平坦盈利区 + 双侧亏损无上限）
            combo_pnl = T - np.maximum(s_T - K2, 0) - np.maximum(K1 - s_T, 0)
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
    # Step 6: 交易信号（宽跨式卖方视角：贵卖波动 + 缺口加厚的安全垫）
    # ================================================================
    def _assign_trade_signals(self, df):
        """分配交易信号

        宽跨式卖方三个维度（找"贵的波动率 + 缺口加厚的安全垫"）：
          1. iv_rank（双腿均值）：IV 分位越高，波动率卖得越贵（vega 双倍为负）
          2. expected_value：(C-BS_C)+(P-BS_P)，市价高于理论价的幅度
          3. 安全垫：缺口 K2-K1 + 2T 构成的 [K1-T, K2+T] 收租区间
        注意：宽跨式卖方胜率天然 > 跨式卖方（缺口加厚安全垫，大概率小赔率），
        但亏损无上限（双向裸卖），任何信号都必须配合止损纪律执行。
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
        gap_pct = df['strike_gap_pct'].values

        # 双腿 IV 分位均值（1:1，两腿对称）
        ivr_avg = np.where(pd.notna(ivr_c) & pd.notna(ivr_p),
                           (ivr_c + ivr_p) / 2, np.nan)

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
            gap_i = gap_pct[i]

            if pd.isna(ia) and pd.isna(ev_i):
                signals[i] = 'N/A'
                signal_reasons[i] = '数据不足'
                continue

            reasons = []

            if (not pd.isna(ic)) and (not pd.isna(ip)) and ic >= 0.65 and ip >= 0.65 \
                    and (not pd.isna(ev_i)) and ev_i > 0:
                signals[i] = 'STRONG_BUY'
                reasons.append(f'Call IV分位={ic:.2f}>=0.65')
                reasons.append(f'Put IV分位={ip:.2f}>=0.65')
                reasons.append(f'期望值={ev_i:+.4g}>0(市价高于理论价)')
            elif (not pd.isna(ia)) and ia >= 0.50 and \
                    ((pd.isna(ev_i)) or ev_i >= 0):
                signals[i] = 'BUY'
                reasons.append(f'双腿IV分位均值={ia:.2f}>=0.50')
                if not pd.isna(ev_i):
                    reasons.append(f'期望值={ev_i:+.4g}')
            elif (not pd.isna(ia)) and ia >= 0.35:
                signals[i] = 'CONSIDER'
                reasons.append(f'双腿IV分位均值={ia:.2f}>=0.35')
            elif (not pd.isna(ia)) and ia >= 0.20:
                signals[i] = 'NEUTRAL'
                reasons.append(f'双腿IV分位均值={ia:.2f}')
            else:
                signals[i] = 'AVOID'
                reasons.append(f'双腿IV分位均值={ia if not pd.isna(ia) else np.nan:.2f}<0.20'
                               if not pd.isna(ia) else 'IV分位缺失')

            # 补充风控理由（宽跨式卖方专属——风险提示优先）
            reasons.append('亏损无上限(双向裸卖), 必须纪律止损')
            if pd.notna(days_i) and days_i < 10:
                reasons.append(f'仅剩{days_i:.0f}天到期, Gamma风险放大, 现货贴近任一腿行权价为风险区')
            elif pd.notna(days_i) and days_i > 60:
                reasons.append(f'距到期{days_i:.0f}天>60(租期过长, 尾部风险敞口累积)')
            if pd.notna(tp_i) and tp_i < 1.5:
                reasons.append(f'双腿租金占现价{tp_i:.1f}%<1.5%(OTM腿收得太薄, 失去卖方收益意义)')
            if pd.notna(wp_i) and wp_i < 0.60:
                reasons.append(f'胜率{wp_i:.2f}<0.60(安全垫偏薄, 慎卖)')
            if (not pd.isna(ic)) and ic <= 0.35:
                reasons.append(f'Call IV分位={ic:.2f}<=0.35(波动率卖便宜了)')
            if (not pd.isna(ip)) and ip <= 0.35:
                reasons.append(f'Put IV分位={ip:.2f}<=0.35(波动率卖便宜了)')
            # 1σ 波动 vs 安全垫半宽：缺口+租金是否足以覆盖正常波动
            if pd.notna(em_i) and pd.notna(gap_i) and pd.notna(tp_i):
                half_cushion = (gap_i + 2 * tp_i) / 2
                if half_cushion < em_i:
                    reasons.append(f'安全垫半宽{half_cushion:.1f}%<1σ波动{em_i:.1f}%'
                                   f'(正常波动即可击穿平衡点)')
            if pd.notna(gap_i) and gap_i > 6:
                reasons.append(f'缺口K2-K1={gap_i:.1f}%>6%(安全垫宽但租太薄, 谨防尾部跳空)')

            signal_reasons[i] = '; '.join(reasons)

        df['trade_signal'] = signals
        df['signal_reason'] = signal_reasons

        signal_counts = pd.Series(signals).value_counts()
        logger.info(f"Trade signals: {signal_counts.to_dict()}")

        return df

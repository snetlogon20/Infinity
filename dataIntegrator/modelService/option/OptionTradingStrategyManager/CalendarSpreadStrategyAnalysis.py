r"""
Calendar Spread（日历价差/时间价差）策略分析 — 高级交易员/风控视角

策略定义：卖出近月认购 Call(K, T_near) + 买入远月认购 Call(K, T_far)，
同行权价、同方向、跨到期月（Call Calendar 基线，Put 版本由平价关系冗余）
净支出 D = C_far - C_near（远月时间价值更多，天然净买方支出）

组合在近月到期日的价值（本策略与同月策略族的计算本质差异）：
    V(S_T) = C_near - max(0, S_T-K) + BS_call(S_T; K, r, q, IV_far, T_far-T_near) - C_far
    —— 远月腿在近月到期日仍存活，价值必须用 BS 重新定价（IV_far + 剩余期限），
       而非到期 payoff。因此最大盈利与双侧盈亏平衡点均无解析解，需 S_T 网格数值求解。

收益结构（教科书"尖峰"形）：
    S_T ≈ K 处盈利峰值（近月腿归零 + 远月残值最大）
    双侧收敛至 -D（两腿内在价值相抵）——最大亏损封顶 = 净支出 D
    两个盈亏平衡点（数值解）

策略特点（与现有策略族的本质差异）：
    1. 跨月配对：唯一以"时间维度"为结构差异的策略——近月/远月腿对称 _near/_far 后缀
    2. 赚时间差：净 Theta 为正（近月衰减快于远月）——时间是朋友
    3. 买远月波动率：净 Vega 为正（远月 vega 大）——期限结构走阔时受益
    4. 负 Gamma 敞口：近月 gamma 大——现货快速移动时近月腿亏损加速（与买跨式完全镜像）
    5. IV 期限结构驱动：iv_term_spread = IV_near - IV_far > 0（近贵远贱）是正期望入场条件
    6. 分红敞口：远月存续期内除息使远月 Call 跌价——2612 远月覆盖 11~12 月分红季，需显式提示

组合配对（三层漏斗第1层——约束剪枝，控制组合爆炸）：
    1. 同一交易日、同一到期月分组（symbol_filter 取全月份，call_put='C'）
    2. 近月：剩余 7~45 天（<7 天 gamma/pin 风险；>45 天 theta 差不明显）
    3. 远月：同 K 的更晚月份，月间隔 <= 95 天（约 3 个月，资金效率约束）
    4. 行权价 K ∈ ATM ± 2 档（尖峰收益在平值附近最厚）
    每日候选组合全量落库（透明可回溯），信号端按综合评分排序

风控三问（日历价差视角）：
    1. 花了多少（成本）：net_debit = C_far - C_near（也是最大亏损）
    2. 多大概率赚（胜率）：win_prob = P(V(S_T) > 0)，近月到期日 S_T 网格
       × 对数正态权重（σ=IV_near）数值积分
    3. 值不值（定价）：expected_value = (C_near-BS_near) + (BS_far-C_far)
       —— 近月卖贵 + 远月买便宜，双腿均为有利定价才有正期望

数据源：
    - tb_tushare_opt_daily_indicator : 现货价、BS定价、Greeks（原料）
    - df_tushare_opt_basic           : symbol/name 反查（ETF 期权 ts_code 为8位数字）

落库：
    - tb_option_trading_strategy_calendar : strategy_type='CALENDAR'，
      近月/远月腿对称 _near/_far 后缀（symbol 列不存在，基类 DELETE_SYMBOL_COLUMN
      覆写为 symbol_near 以兼容增量删除逻辑）

使用（symbol_filter 不带月份取全部到期月，方向固定 'C'）：
    config = {
        "name": "华夏上证50ETF期权（Calendar Spread）",
        "start_date": "20251222",
        "end_date": CommonParameters.today,
        "call_put": "C",
        "symbol_filter": "510050%",
    }
    CalendarSpreadStrategyAnalysis().run(config)
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


def _bs_call_price(S, K, r, q, sigma, T):
    """欧式 Call BS 定价（S 可为数组，其余为标量）"""
    S = np.asarray(S, dtype=float)
    sigma_t = sigma * np.sqrt(T)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / sigma_t
    d2 = d1 - sigma_t
    return S * np.exp(-q * T) * _norm_cdf(d1) - K * np.exp(-r * T) * _norm_cdf(d2)


class CalendarSpreadStrategyAnalysis(OptionStrategyBase):
    """Calendar Spread 策略分析器（卖近月 Call(K) + 买远月 Call(K)，同行权价跨月）

    分析维度：跨月配对（近月剩余天数/月份间隔约束剪枝）、IV 期限结构、
    净支出、近月到期日组合价值曲线（远月 BS 残值定价）、数值盈亏平衡与胜率、
    定价偏差期望值与评分排序、净 Greeks（正 theta/正 vega/负 gamma）、
    多情景盈亏（情景日=近月到期日，含买现货对照）。
    """

    # === 策略标识 ===
    STRATEGY_TYPE = 'CALENDAR'
    ANALYSIS_VERSION = 'v1'
    TABLE_TARGET = 'tb_option_trading_strategy_calendar'
    # 增量删除按近月腿 symbol 过滤（本表无无后缀 symbol 列）
    DELETE_SYMBOL_COLUMN = 'symbol_near'

    # === 目标表字段（与 tb_option_trading_strategy_calendar.sql 建表一致） ===
    TARGET_COLUMNS = [
        # 策略标识与审计
        'strategy_type', 'analysis_time', 'analysis_params', 'analysis_version',
        # 组合标识（近月/远月腿对称 _near/_far 后缀——时间维度是唯一结构差异）
        'trade_date',
        'ts_code_near', 'symbol_near', 'opt_name_near', 'opt_exchange_near',
        'ts_code_far', 'symbol_far', 'opt_name_far',
        'call_put',
        # 合约要素（同行权价，跨月）
        'exercise_price', 'opt_multiplier',
        's_month_near', 'maturity_date_near', 'days_to_maturity_near',
        's_month_far', 'maturity_date_far', 'days_to_maturity_far', 'month_gap_days',
        # 标的市场
        'spot_price', 'moneyness_status', 'risk_free_rate', 'dividend_yield',
        # 双腿行情与定价
        'premium_near', 'premium_far', 'implied_vol_near', 'implied_vol_far',
        'iv_rank_near', 'iv_rank_far',
        # 双腿 Greeks
        'delta_near', 'gamma_near', 'theta_near', 'vega_near',
        'delta_far', 'gamma_far', 'theta_far', 'vega_far',
        # 双腿定价偏差
        'bs_theoretical_price_near', 'close_vs_theoretical_near',
        'close_vs_theoretical_pct_near', 'price_bias_near',
        'bs_theoretical_price_far', 'close_vs_theoretical_far',
        'close_vs_theoretical_pct_far', 'price_bias_far',
        # 组合净 Greeks（买远卖近：theta正/vega正/gamma负）
        'net_delta', 'net_gamma', 'net_theta', 'net_vega',
        # 期限结构专属指标（本策略的灵魂）
        'iv_term_spread', 'theta_differential',
        # 日历价差结构（花了多少）
        'net_debit', 'net_debit_cny', 'net_debit_pct_of_spot',
        'expected_move_1sigma_pct',
        # 收益结构（亏损封顶 D，盈利尖峰数值解）
        'max_loss', 'max_loss_cny', 'max_loss_pct_of_spot',
        'max_profit', 'max_profit_cny', 'max_profit_pct_of_spot',
        'breakeven_down', 'breakeven_down_pct',
        'breakeven_up', 'breakeven_up_pct',
        # 概率与评分
        'win_prob', 'expected_value', 'score', 'combo_rank',
        # 多情景盈亏（情景日=近月到期日，含买现货对照）
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

    # === 情景系数（S_T = S0 × factor，情景日 = 近月到期日） ===
    DEFAULT_SCENARIOS = [0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15]

    # === 近月到期日组合价值曲线的 S_T 网格（数值求解 max_profit/盈亏平衡/胜率） ===
    GRID_LO, GRID_HI, GRID_N = 0.80, 1.20, 81

    # === 组合配对参数（约束剪枝） ===
    NEAR_MIN_DAYS = 7       # 近月剩余下限（<7 天 gamma/pin 风险）
    NEAR_MAX_DAYS = 45      # 近月剩余上限（>45 天 theta 差不明显）
    MAX_MONTH_GAP_DAYS = 95  # 远近月到期日间隔上限（约 3 个月，资金效率）
    STRIKE_RANGE = 2        # 行权价限定 ATM ± 2 档（尖峰收益在平值附近最厚）

    # ================================================================
    # Step 4: 组合配对 + 核心策略盈亏（风控三问）
    # ================================================================
    def calc_strategy_pnl(self, df):
        """Calendar Spread 核心盈亏指标（组合粒度）

        配对: 卖出近月 Call(K) + 买入远月 Call(K)，同行权价跨月，净支出 D = C_far - C_near
        近月到期日组合价值 V(S_T) = C_near - max(0,S_T-K) + BS_far(S_T) - C_far
        —— 远月 BS 残值定价是本策略的计算核心：最大盈利/盈亏平衡/胜率均为数值解
        """
        logger.info("Building calendar pairs "
                    f"(near {self.NEAR_MIN_DAYS}~{self.NEAR_MAX_DAYS}天, "
                    f"gap<={self.MAX_MONTH_GAP_DAYS}天, ATM±{self.STRIKE_RANGE}档)...")

        # ---------- 0. 组合配对（约束剪枝：近月×远月跨月配对，同行权价） ----------
        df = self._build_pairs(df)
        if df.empty:
            logger.warning("No calendar pairs built, skip P&L calculation")
            return df
        logger.info(f"Built {len(df)} combo rows "
                    f"({df.groupby('trade_date').size().max()} combos/day max)")

        S = df['spot_price'].values.astype(float)
        K = df['exercise_price'].values.astype(float)
        C_near = df['premium_near'].values.astype(float)
        C_far = df['premium_far'].values.astype(float)
        mult = df['opt_multiplier'].values.astype(float)
        r = df['risk_free_rate'].values.astype(float)
        q = df['dividend_yield'].values.astype(float)
        iv_near = df['implied_vol_near'].values.astype(float)
        iv_far = df['implied_vol_far'].values.astype(float)
        years_near = df['years_to_maturity_calendar_near'].values.astype(float)
        years_far = df['years_to_maturity_calendar_far'].values.astype(float)

        # ---------- 1. 日历价差结构（花了多少：净支出） ----------
        D = C_far - C_near
        df['net_debit'] = D
        df['net_debit_cny'] = D * mult
        df['net_debit_pct_of_spot'] = np.where(S > 0, D / S * 100, np.nan)

        # ---------- 2. 期限结构专属指标（本策略的灵魂） ----------
        # IV 期限结构差：>0 即"近贵远贱"，正期望入场条件（1 个 vol 点 = 0.01）
        df['iv_term_spread'] = np.where(pd.notna(iv_near) & pd.notna(iv_far),
                                        iv_near - iv_far, np.nan)
        # theta 时间差：>0 即近月衰减快于远月（时间站在日历价差这边）
        theta_near = df['theta_near'].values.astype(float)
        theta_far = df['theta_far'].values.astype(float)
        df['theta_differential'] = np.where(pd.notna(theta_near) & pd.notna(theta_far),
                                            np.abs(theta_near) - np.abs(theta_far), np.nan)

        # ---------- 3. 组合净 Greeks（买远卖近：theta正/vega正/gamma负） ----------
        delta_near = df['delta_near'].values.astype(float)
        gamma_near = df['gamma_near'].values.astype(float)
        vega_near = df['vega_near'].values.astype(float)
        delta_far = df['delta_far'].values.astype(float)
        gamma_far = df['gamma_far'].values.astype(float)
        vega_far = df['vega_far'].values.astype(float)
        # 净 Delta：两腿同 K 同向，远月 delta 略小于近月，净敞口很小（准中性）
        df['net_delta'] = np.where(pd.notna(delta_far) & pd.notna(delta_near),
                                   delta_far - delta_near, np.nan)
        # 净 Gamma 为负：近月 gamma 大——现货快速移动时近月腿亏损加速
        df['net_gamma'] = np.where(pd.notna(gamma_far) & pd.notna(gamma_near),
                                   gamma_far - gamma_near, np.nan)
        # 净 Theta 为正：近月衰减快于远月（日历价差的时间朋友）
        df['net_theta'] = np.where(pd.notna(theta_far) & pd.notna(theta_near),
                                   theta_far - theta_near, np.nan)
        # 净 Vega 为正：远月 vega 大——买远月波动率，IV 整体上行受益/下行受损
        df['net_vega'] = np.where(pd.notna(vega_far) & pd.notna(vega_near),
                                  vega_far - vega_near, np.nan)

        # ---------- 4. 收益结构（亏损封顶 D，盈利尖峰数值解） ----------
        df['max_loss'] = D
        df['max_loss_cny'] = D * mult
        df['max_loss_pct_of_spot'] = np.where(S > 0, D / S * 100, np.nan)

        # 近月到期日 S_T 网格数值求解：max_profit / 双侧盈亏平衡 / 胜率
        grid = np.linspace(self.GRID_LO, self.GRID_HI, self.GRID_N)
        n = len(df)
        max_profit = np.full(n, np.nan)
        be_dn = np.full(n, np.nan)
        be_up = np.full(n, np.nan)
        win_prob = np.full(n, np.nan)

        for i in range(n):
            # 数值求解前置条件：远月 IV/剩余期限有效
            t_rem = years_far[i] - years_near[i]
            if pd.isna(iv_far[i]) or pd.isna(t_rem) or t_rem <= 0 or S[i] <= 0:
                continue
            s_T = S[i] * grid
            v_far = _bs_call_price(s_T, K[i], r[i], q[i], iv_far[i], t_rem)
            pnl = C_near[i] - np.maximum(s_T - K[i], 0) + v_far - C_far[i]

            # 尖峰最大盈利（网格极值）
            j_max = int(np.nanargmax(pnl))
            max_profit[i] = pnl[j_max]

            # 双侧盈亏平衡（符号变化处线性插值；可能 0/1/2 个）
            crossings = []
            for j in range(len(pnl) - 1):
                if (pnl[j] > 0) >= (pnl[j + 1] > 0) and pnl[j] != pnl[j + 1]:
                    t0 = pnl[j] / (pnl[j] - pnl[j + 1])
                    crossings.append(s_T[j] + t0 * (s_T[j + 1] - s_T[j]))
            if crossings:
                be_dn[i] = min(crossings)
                be_up[i] = max(crossings)

            # 胜率：S_T 对数正态权重（σ=IV_near，期限=近月剩余）数值积分
            if pd.isna(iv_near[i]) or pd.isna(years_near[i]) or years_near[i] <= 0:
                continue
            sig_t = iv_near[i] * np.sqrt(years_near[i])
            if sig_t <= 0:
                continue
            z_edges = np.log(grid) / sig_t          # ln(s_T/S0)/σT，S0=1 归一
            cdf_edges = _norm_cdf(z_edges)
            weights = np.diff(cdf_edges)              # 各 bin 概率（区间外忽略，近似）
            win_prob[i] = float(np.sum(weights[pnl[:-1] > 0]))

        df['max_profit'] = max_profit
        df['max_profit_cny'] = max_profit * mult
        df['max_profit_pct_of_spot'] = np.where(S > 0, max_profit / S * 100, np.nan)
        df['breakeven_down'] = be_dn
        df['breakeven_down_pct'] = np.where(S > 0, (be_dn - S) / S * 100, np.nan)
        df['breakeven_up'] = be_up
        df['breakeven_up_pct'] = np.where(S > 0, (be_up - S) / S * 100, np.nan)
        df['win_prob'] = win_prob

        # ---------- 5. 1σ 预期波动（近月 IV，近月期限内） ----------
        with np.errstate(invalid='ignore'):
            sig_t_near = iv_near * np.sqrt(np.where(years_near > 0, years_near, np.nan))
        df['expected_move_1sigma_pct'] = np.where(pd.notna(sig_t_near),
                                                  sig_t_near * 100, np.nan)

        # ---------- 6. 期望值与评分（近月卖贵 + 远月买便宜） ----------
        bs_near = df['bs_theoretical_price_near'].values.astype(float)
        bs_far = df['bs_theoretical_price_far'].values.astype(float)
        ev = np.where(pd.notna(bs_near) & pd.notna(bs_far) & pd.notna(C_near) & pd.notna(C_far),
                      (C_near - bs_near) + (bs_far - C_far), np.nan)
        df['expected_value'] = ev
        # 评分 = 期望值/净支出（风险调整后收益，同日候选组合排名依据）
        df['score'] = np.where(pd.notna(ev) & (D > 0), ev / D, np.nan)

        # 同日组合排名（1=评分最高）
        df['combo_rank'] = df.groupby('trade_date')['score'].rank(
            ascending=False, method='first').fillna(0).astype(int)

        # ---------- 7. 双腿定价偏差（近月卖贵 + 远月买便宜才有利） ----------
        df['close_vs_theoretical_near'] = np.where(
            pd.notna(bs_near) & pd.notna(C_near), C_near - bs_near, np.nan)
        df['close_vs_theoretical_pct_near'] = np.where(
            pd.notna(bs_near) & (bs_near > 0), (C_near - bs_near) / bs_near * 100, np.nan)
        df['price_bias_near'] = np.select(
            [
                df['close_vs_theoretical_pct_near'] < -5,
                (df['close_vs_theoretical_pct_near'] >= -5) & (df['close_vs_theoretical_pct_near'] < -1),
                (df['close_vs_theoretical_pct_near'] >= -1) & (df['close_vs_theoretical_pct_near'] <= 1),
                (df['close_vs_theoretical_pct_near'] > 1) & (df['close_vs_theoretical_pct_near'] <= 5),
                df['close_vs_theoretical_pct_near'] > 5,
            ],
            ['严重低估', '低估', '公允', '高估', '严重高估'],
            default='N/A'
        )
        df['close_vs_theoretical_far'] = np.where(
            pd.notna(bs_far) & pd.notna(C_far), C_far - bs_far, np.nan)
        df['close_vs_theoretical_pct_far'] = np.where(
            pd.notna(bs_far) & (bs_far > 0), (C_far - bs_far) / bs_far * 100, np.nan)
        df['price_bias_far'] = np.select(
            [
                df['close_vs_theoretical_pct_far'] < -5,
                (df['close_vs_theoretical_pct_far'] >= -5) & (df['close_vs_theoretical_pct_far'] < -1),
                (df['close_vs_theoretical_pct_far'] >= -1) & (df['close_vs_theoretical_pct_far'] <= 1),
                (df['close_vs_theoretical_pct_far'] > 1) & (df['close_vs_theoretical_pct_far'] <= 5),
                df['close_vs_theoretical_pct_far'] > 5,
            ],
            ['严重低估', '低估', '公允', '高估', '严重高估'],
            default='N/A'
        )

        # ---------- 摘要日志 ----------
        logger.info(f"Strategy P&L calculated for {len(df)} combo rows")
        valid = df['score'].notna().sum()
        if valid > 0:
            logger.info(f"  net_debit_pct_of_spot: mean={df['net_debit_pct_of_spot'].mean():.2f}%, "
                        f"best={df['net_debit_pct_of_spot'].min():.2f}%")
            logger.info(f"  iv_term_spread: mean={df['iv_term_spread'].mean():.4f}")
            logger.info(f"  win_prob: mean={df['win_prob'].mean():.2f}")
            best = df[df['combo_rank'] == 1]
            if not best.empty:
                last = best.iloc[-1]
                logger.info(f"  latest best combo: {last['s_month_near']}/{last['s_month_far']}"
                            f"@K{last['exercise_price']:.4g}, score={last['score']:.3f}")
        return df

    # ================================================================
    # 组合配对（约束剪枝，跨月配对——本策略族唯一的时间维度配对）
    # ================================================================
    def _build_pairs(self, df):
        """按交易日配对生成日历价差组合（近月腿 + 远月腿，同行权价同方向）

        约束:
          近月: 剩余 7~45 天；远月: 同 K 的更晚月份，间隔 <= 95 天；K ∈ ATM±2 档
        输出: 每行一个组合（近月/远月腿对称 _near/_far 后缀）
        """
        frames = []
        n_dates = 0
        for trade_date, g in df.groupby('trade_date', sort=True):
            n_dates += 1
            g = g.dropna(subset=['exercise_price', 'close'])
            if g.empty:
                continue

            # 按到期月分组（同月同档行权价一条）
            by_month = {}
            month_days = {}
            for s_month, gm in g.groupby('s_month'):
                by_month[s_month] = {float(row['exercise_price']): row
                                     for _, row in gm.iterrows()}
                month_days[s_month] = float(gm['days_to_maturity'].iloc[0])

            S0 = float(g['spot_price'].iloc[0])
            months = sorted(by_month.keys())

            for m_near in months:
                d_near = month_days[m_near]
                if not (self.NEAR_MIN_DAYS <= d_near <= self.NEAR_MAX_DAYS):
                    continue  # 近月剩余天数约束（gamma/pin 与 theta 差的平衡）
                for m_far in months:
                    gap_days = month_days[m_far] - d_near
                    if not (0 < gap_days <= self.MAX_MONTH_GAP_DAYS):
                        continue  # 远月约束：更晚且间隔不超过约 3 个月

                    # 两月共同行权价（同 K 才构成日历价差）
                    common = sorted(set(by_month[m_near].keys()) & set(by_month[m_far].keys()))
                    if not common:
                        continue
                    atm_idx = int(np.abs(np.array(common) - S0).argmin())
                    lo = max(0, atm_idx - self.STRIKE_RANGE)
                    hi = min(len(common) - 1, atm_idx + self.STRIKE_RANGE)

                    for i in range(lo, hi + 1):
                        K = common[i]
                        rn = by_month[m_near][K]
                        rf_leg = by_month[m_far][K]
                        frames.append({
                            'trade_date': trade_date,
                            # 近月腿（_near，卖出的时间衰减主力）
                            'ts_code_near': rn['ts_code'],
                            'symbol_near': rn['symbol'],
                            'opt_name_near': rn['opt_name'],
                            'opt_exchange_near': rn['opt_exchange'],
                            # 远月腿（_far，买入的残值载体）
                            'ts_code_far': rf_leg['ts_code'],
                            'symbol_far': rf_leg['symbol'],
                            'opt_name_far': rf_leg['opt_name'],
                            # 同方向（Call Calendar 基线）
                            'call_put': 'C',
                            # 合约要素（同行权价，跨月）
                            'exercise_price': K,
                            'opt_multiplier': rn['opt_multiplier'],
                            's_month_near': rn['s_month'],
                            'maturity_date_near': rn['maturity_date'],
                            'days_to_maturity_near': rn['days_to_maturity'],
                            'years_to_maturity_calendar_near': rn['years_to_maturity_calendar'],
                            's_month_far': rf_leg['s_month'],
                            'maturity_date_far': rf_leg['maturity_date'],
                            'days_to_maturity_far': rf_leg['days_to_maturity'],
                            'years_to_maturity_calendar_far': rf_leg['years_to_maturity_calendar'],
                            'month_gap_days': int(round(gap_days)),
                            # 标的市场（同标的同日）
                            'spot_price': S0,
                            'moneyness_status': rn['moneyness_status'],
                            'risk_free_rate': rn['risk_free_rate'],
                            'dividend_yield': rn['dividend_yield'],
                            # 双腿行情与定价
                            'premium_near': float(rn['close']),
                            'premium_far': float(rf_leg['close']),
                            'implied_vol_near': rn['implied_vol'],
                            'implied_vol_far': rf_leg['implied_vol'],
                            'iv_rank_near': rn['iv_rank'],
                            'iv_rank_far': rf_leg['iv_rank'],
                            # 双腿 Greeks
                            'delta_near': rn['delta'],
                            'gamma_near': rn['gamma'],
                            'theta_near': rn['theta'],
                            'vega_near': rn['vega'],
                            'delta_far': rf_leg['delta'],
                            'gamma_far': rf_leg['gamma'],
                            'theta_far': rf_leg['theta'],
                            'vega_far': rf_leg['vega'],
                            # 双腿理论价
                            'bs_theoretical_price_near': rn['bs_theoretical_price'],
                            'bs_theoretical_price_far': rf_leg['bs_theoretical_price'],
                        })

        logger.info(f"Pairing done: {n_dates} trade dates -> {len(frames)} combos")
        return pd.DataFrame(frames)

    # ================================================================
    # Step 5: 多情景盈亏（情景日 = 近月到期日，含买现货对照）
    # ================================================================
    def calc_scenario_pnl(self, df, scenarios=None):
        """多情景盈亏：S_T = S0 * factor（S_T 为近月到期日的标的价）

        近月腿 payoff = C_near - max(S_T-K, 0)（封闭形式，卖方）
        远月腿 = BS_call(S_T; K, r, q, IV_far, 剩余期限) - C_far（BS 残值定价，买方）
        —— 与同月策略族的情景计算本质不同：远月腿不能按到期 payoff 计算
        买现货对照 P&L = S_T - S0（对照组）
        收益率基准 = 净支出 D（日历价差的本金即最大风险）
        """
        if df.empty:
            return df
        if scenarios is None:
            scenarios = self.DEFAULT_SCENARIOS

        logger.info(f"Calculating multi-scenario P&L for {len(scenarios)} scenarios: {scenarios}")

        S = df['spot_price'].values.astype(float)
        K = df['exercise_price'].values.astype(float)
        C_near = df['premium_near'].values.astype(float)
        C_far = df['premium_far'].values.astype(float)
        D = df['net_debit'].values.astype(float)
        r = df['risk_free_rate'].values.astype(float)
        q = df['dividend_yield'].values.astype(float)
        iv_far = df['implied_vol_far'].values.astype(float)
        years_near = df['years_to_maturity_calendar_near'].values.astype(float)
        years_far = df['years_to_maturity_calendar_far'].values.astype(float)
        mult = df['opt_multiplier'].values.astype(float)

        for factor in scenarios:
            s_T = S * factor
            combo_pnl = np.full(len(df), np.nan)
            for i in range(len(df)):
                t_rem = years_far[i] - years_near[i]
                if pd.isna(iv_far[i]) or pd.isna(t_rem) or t_rem <= 0 or S[i] <= 0:
                    continue
                v_far = _bs_call_price(s_T[i], K[i], r[i], q[i], iv_far[i], t_rem)
                combo_pnl[i] = C_near[i] - max(s_T[i] - K[i], 0) + v_far - C_far[i]

            label = f'{factor:.2f}'.replace('.', '_')
            df[f'scenario_pnl_{label}S'] = combo_pnl
            df[f'scenario_pnl_{label}S_cny'] = combo_pnl * mult
            df[f'scenario_pnl_{label}S_pct'] = np.where(
                D > 0, combo_pnl / D * 100, np.nan)

            # 买现货对照
            unhedged_pnl = s_T - S
            df[f'unhedged_pnl_{label}S'] = unhedged_pnl
            df[f'unhedged_pnl_{label}S_pct'] = np.where(
                S > 0, unhedged_pnl / S * 100, np.nan)

        logger.info("Multi-scenario P&L calculated")
        return df

    # ================================================================
    # Step 6: 交易信号（期限结构驱动：近贵远贱 + 时间差确认）
    # ================================================================
    def _assign_trade_signals(self, df):
        """分配交易信号

        日历价差三个维度（找"近贵远贱的期限结构 + 时间差站在这边"）：
          1. iv_term_spread：IV_near - IV_far > 0 即近月贵（卖近买远的正期望条件）
          2. expected_value：近月卖贵 + 远月买便宜（双腿均有利定价）
          3. theta_differential：近月衰减快于远月（结构收益的来源确认）
        注意：亏损封顶 = 净支出 D（买方结构），但盈利区间窄（尖峰）且负 gamma——
        现货快速移动与 IV 整体下行是两大风险，任何信号都需配合风险管理执行。
        """
        if df.empty:
            return df

        ivs = df['iv_term_spread'].values
        ev = df['expected_value'].values
        days_near = df['days_to_maturity_near'].values
        td = df['theta_differential'].values
        wp = df['win_prob'].values
        gap_days = df['month_gap_days'].values
        ivr_near = df['iv_rank_near'].values
        ivr_far = df['iv_rank_far'].values
        nd_pct = df['net_debit_pct_of_spot'].values
        maturity_far = df['maturity_date_far'].values

        signals = np.full(len(df), 'AVOID', dtype=object)
        signal_reasons = np.full(len(df), '', dtype=object)

        for i in range(len(df)):
            ivs_i = ivs[i]
            ev_i = ev[i]
            days_i = days_near[i]
            td_i = td[i]
            wp_i = wp[i]
            gap_i = gap_days[i]
            irn = ivr_near[i]
            irf = ivr_far[i]
            nd_i = nd_pct[i]
            mat_far = str(maturity_far[i])

            if pd.isna(ivs_i) and pd.isna(ev_i):
                signals[i] = 'N/A'
                signal_reasons[i] = '数据不足'
                continue

            reasons = []

            if (not pd.isna(ivs_i)) and ivs_i >= 0.01 \
                    and (not pd.isna(irn)) and irn >= 0.60 \
                    and (not pd.isna(irf)) and irf <= 0.40 \
                    and (not pd.isna(ev_i)) and ev_i > 0:
                signals[i] = 'STRONG_BUY'
                reasons.append(f'期限结构差={ivs_i:+.4f}>=+0.01(近月显著贵)')
                reasons.append(f'近月IV分位={irn:.2f}>=0.60且远月IV分位={irf:.2f}<=0.40(错配)')
                reasons.append(f'期望值={ev_i:+.4g}>0(近月卖贵+远月买便宜)')
            elif (not pd.isna(ivs_i)) and ivs_i > 0 and \
                    ((pd.isna(ev_i)) or ev_i >= 0):
                signals[i] = 'BUY'
                reasons.append(f'期限结构差={ivs_i:+.4f}>0(近贵远贱)')
                if not pd.isna(ev_i):
                    reasons.append(f'期望值={ev_i:+.4g}')
            elif (not pd.isna(ivs_i)) and ivs_i > 0:
                signals[i] = 'CONSIDER'
                reasons.append(f'期限结构差={ivs_i:+.4f}>0但定价未占优')
            elif (not pd.isna(ivs_i)) and ivs_i >= -0.01:
                signals[i] = 'NEUTRAL'
                reasons.append(f'期限结构差={ivs_i:+.4f}(结构平坦)')
            else:
                signals[i] = 'AVOID'
                reasons.append(f'期限结构差={ivs_i if not pd.isna(ivs_i) else np.nan:+.4f}倒挂'
                               if not pd.isna(ivs_i) else '期限结构数据缺失')
                if not pd.isna(ivs_i) and ivs_i < -0.01:
                    reasons.append('(远月贵——属 reverse calendar 场景, 应卖远买近)')

            # 补充风控理由（日历价差专属）
            reasons.append('亏损封顶=净支出D, 但盈利区间窄(尖峰结构)')
            if pd.notna(days_i) and days_i < 7:
                reasons.append(f'近月仅剩{days_i:.0f}天到期, Gamma/Pin风险放大, 建议了结或展期')
            elif pd.notna(days_i) and days_i > 45:
                reasons.append(f'近月剩余{days_i:.0f}天>45(Theta时间差尚不明显)')
            if pd.notna(td_i) and td_i <= 0:
                reasons.append(f'Theta时间差{td_i:+.5f}<=0(近月衰减不快于远月, 结构收益来源缺失)')
            if pd.notna(wp_i) and wp_i < 0.50:
                reasons.append(f'胜率{wp_i:.2f}<0.50(尖峰盈利区间偏窄)')
            if pd.notna(gap_i) and gap_i > 91:
                reasons.append(f'月份间隔{gap_i:.0f}天>3个月(净支出大, 资金效率低)')
            if (not pd.isna(irf)) and irf >= 0.65:
                reasons.append(f'远月IV分位={irf:.2f}>=0.65(远月波动率买贵了)')
            if (not pd.isna(irn)) and irn <= 0.30:
                reasons.append(f'近月IV分位={irn:.2f}<=0.30(近月租收得便宜, 卖方端不利)')
            if pd.notna(nd_i) and nd_i > 3:
                reasons.append(f'净支出占现价{nd_i:.1f}%>3%(尖峰盈利需更大波动兑现, 成本偏高)')
            # 分红敞口：远月存续期覆盖 11~12 月除息季 → 远月 Call 因除息跌价（Call Calendar 受损）
            if len(mat_far) >= 6 and mat_far[4:6] in ('11', '12'):
                reasons.append(f'远月到期{mat_far}覆盖分红季(除息使远月Call跌价, 关注分红公告)')

            signal_reasons[i] = '; '.join(reasons)

        df['trade_signal'] = signals
        df['signal_reason'] = signal_reasons

        signal_counts = pd.Series(signals).value_counts()
        logger.info(f"Trade signals: {signal_counts.to_dict()}")

        return df

r"""
合成股票(Synthetic Stock)策略分析 共享核心 — 资深交易员/风控视角

策略定义(同K同T的Call/Put一买一卖, 复制现货方向敞口):
    合成多头(Synthetic Long)  = 买 Call(K,T) + 卖 Put(K,T), 净支出 C-P
    合成空头(Synthetic Short) = 卖 Call(K,T) + 买 Put(K,T), 净收入 C-P
    到期损益(多头) = S_T - K - (C-P), 与持有现货 S_T - S_0 几乎等价; 空头取反号

理论定价(期权平价关系):
    C - P = S·e^(-qT) - K·e^(-rT)
    由此可从市场价反推"隐含融资利率":
        r_impl = -ln((S·e^(-qT) - (C-P)) / K) / T
    financing_spread_bp = (r_impl - r)×1e4, 是合成头寸"贵/便宜"的核心刻度

与其它策略的本质差异(信号维度不同):
    C-P 对波动率天然不敏感(同K同T的C、P随IV同涨同跌基本抵消),
    合成成本主要敏感于 资金利率r 与 股息率q —— 因此本策略信号不看IV分位,
    而看: ①合成价差对理论值的偏离 ②隐含融资利率利差 ③净Delta校验(防脏数据配对)

交易员用途:
    1. 融券替代: A股券源紧、成本高, 合成空头是可规模化的做空渠道
    2. 资金效率: 保证金占用 vs 现货全额资金(margin_vs_spot_capital)
    3. 隐含融资利率监控: 合成多头成本反推市场资金价格, 与回购/两融利率对照

风控关注(必须落指标):
    1. 卖出腿保证金追缴(非有限亏损): margin_est粗估 + 资金占用对比 + 情景亏损
    2. 提前行权/指派: 美式合约警示(ETF期权为欧式; CFFEX股指期权为美式, 配对时注意)
    3. 股息估计误差直接进入合成成本: 分红季(ETF 11~12月)自动标注股息噪声
    4. Pin risk: 距到期<10天提示强平/展期
    5. 双腿流动性: 净Delta校验(|net_delta-±1|>0.15判为脏配对) + 成交量兜底

数据源/落库/审计: 同 OptionStrategyBase 框架约定, 每方向一张专表。

使用(子类化后):
    config = {
        "name": "华夏上证50ETF期权(合成多头)",
        "start_date": "20251222",
        "end_date": CommonParameters.today,
        "call_put": None,               # 合成需要同时取 C/P 双腿
        "symbol_filter": "510050%2612%",
    }
    SyntheticLongStockStrategyAnalysis().run(config)
"""

import numpy as np
import pandas as pd

from dataIntegrator import CommonLib
from dataIntegrator.modelService.option.OptionTradingStrategyManager.OptionStrategyBase import OptionStrategyBase

logger = CommonLib.logger


class SyntheticStockStrategyAnalysisBase(OptionStrategyBase):
    """合成股票策略分析器 共享核心

    子类只需覆写: STRATEGY_TYPE / TABLE_TARGET / DIRECTION(+1多头, -1空头)。
    两方向表结构完全一致(仅 strategy_type 不同), TARGET_COLUMNS 共用一份。

    分析维度: 同月同K的C+P配对(ATM±5档)、合成净成本与理论成本偏离、
    隐含融资利率与利差、净Greeks与Delta校验、卖出腿保证金粗估与资金效率、
    多情景盈亏(对照组=直接持有/融券现货)、方向化交易信号。
    """

    # === 子类必须覆写 ===
    DIRECTION = None            # +1=合成多头(买C卖P), -1=合成空头(卖C买P)

    # === 组合配对参数 ===
    # 合成头寸对K不敏感(任意K经平价等价, K只改变融资结构), 由流动性决定选档,
    # 故比跨式(ATM±2)放宽到 ATM±5 档
    STRIKE_RANGE = 5

    # === 风控参数 ===
    DELTA_CHECK_TOL = 0.15      # |net_delta - (±1)| 超过此值判为脏配对
    MARGIN_RATE = 0.12          # 卖出腿保证金率粗估(交易所公式: 标的×12% - 虚值)
    MARGIN_FLOOR_RATE = 0.07    # 保证金下限(标的×7%)
    SHORT_BORROW_COST_BP = 600.0  # A股融券年化成本粗略基准(6%), 空头对照用

    # === 目标表字段(两方向一致, 与建表SQL逐列对齐) ===
    TARGET_COLUMNS = [
        # 策略标识与审计
        'strategy_type', 'analysis_time', 'analysis_params', 'analysis_version',
        # 组合标识(Call腿无后缀, Put腿带 _put)
        'trade_date', 'ts_code', 'symbol', 'opt_name', 'opt_exchange', 'call_put',
        'ts_code_put', 'symbol_put', 'opt_name_put',
        # 合约要素(同到期月同行权价)
        'exercise_price', 'opt_multiplier', 's_month',
        'maturity_date', 'days_to_maturity',
        # 标的市场
        'spot_price', 'moneyness_status', 'risk_free_rate', 'dividend_yield',
        # 双腿行情与定价
        'premium', 'premium_put', 'implied_vol', 'implied_vol_put',
        'iv_rank', 'iv_rank_put',
        # 双腿 Greeks(原始腿口径: 买方Greeks)
        'delta', 'gamma', 'theta', 'vega',
        'delta_put', 'gamma_put', 'theta_put', 'vega_put',
        # 双腿定价偏差
        'bs_theoretical_price', 'close_vs_theoretical', 'close_vs_theoretical_pct', 'price_bias',
        'bs_theoretical_price_put', 'close_vs_theoretical_put',
        'close_vs_theoretical_pct_put', 'price_bias_put',
        # 合成结构核心
        'synthetic_net_cost', 'synthetic_net_cost_cny', 'synthetic_net_cost_pct_of_spot',
        'synthetic_theoretical', 'synth_deviation', 'synth_deviation_pct',
        # 隐含资金利率
        'implied_financing_rate', 'financing_spread_bp',
        # 净 Greeks(持仓口径: 买腿+, 卖腿-) 与 Delta 校验
        'net_delta', 'delta_check_passed', 'net_gamma', 'net_theta', 'net_vega',
        # 资金效率(卖出腿保证金粗估)
        'margin_est', 'capital_occupied_cny', 'margin_vs_spot_capital',
        # 收益结构
        'breakeven', 'breakeven_pct',
        # 评分
        'score', 'combo_rank',
        # 多情景盈亏(S_T = S0*factor, 含直接持有/融券现货对照)
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

    # === 情景系数(S_T = S0 × factor) ===
    DEFAULT_SCENARIOS = [0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15]

    # ================================================================
    # Step 4: 组合配对 + 核心策略盈亏
    # ================================================================
    def calc_strategy_pnl(self, df):
        """合成股票核心指标(组合粒度)

        配对: 同月同K的Call+Put(ATM±5档), 与Long Straddle同构但方向语义不同:
        合成 = 一买一卖, 净成本 C-P; 平价关系给出理论成本与隐含融资利率。
        """
        if self.DIRECTION is None:
            raise NotImplementedError(f"{type(self).__name__} 未覆写 DIRECTION(+1/-1)")
        dirn = float(self.DIRECTION)

        logger.info(f"Building synthetic stock pairs "
                    f"(same-strike C+P, ATM±{self.STRIKE_RANGE}档, "
                    f"direction={'LONG' if dirn > 0 else 'SHORT'})...")

        # ---------- 0. 组合配对 ----------
        df = self._build_pairs(df)
        if df.empty:
            logger.warning("No synthetic pairs built, skip P&L calculation")
            return df
        logger.info(f"Built {len(df)} combo rows "
                    f"({df.groupby('trade_date').size().max()} combos/day max)")

        S = df['spot_price'].values.astype(float)
        K = df['exercise_price'].values.astype(float)
        C = df['premium'].values.astype(float)
        P = df['premium_put'].values.astype(float)
        mult = df['opt_multiplier'].values.astype(float)
        years = df['years_to_maturity_calendar'].values.astype(float)
        r = df['risk_free_rate'].values.astype(float)
        q = df['dividend_yield'].values.astype(float)

        # ---------- 1. 合成净成本 C-P(多头=净支出, 空头=净收入) ----------
        net_cost = C - P
        df['synthetic_net_cost'] = net_cost
        df['synthetic_net_cost_cny'] = net_cost * mult
        df['synthetic_net_cost_pct_of_spot'] = np.where(S > 0, net_cost / S * 100, np.nan)

        # ---------- 2. 理论合成成本与偏离(平价关系, 含股息贴现) ----------
        # theo = S·e^(-qT) - K·e^(-rT);  dev = 净成本 - 理论(正=合成贵)
        with np.errstate(invalid='ignore'):
            disc_s = S * np.exp(-q * years)
            disc_k = K * np.exp(-r * years)
        theo = np.where(pd.notna(disc_s) & pd.notna(disc_k), disc_s - disc_k, np.nan)
        df['synthetic_theoretical'] = theo
        dev = np.where(pd.notna(net_cost) & pd.notna(theo), net_cost - theo, np.nan)
        df['synth_deviation'] = dev
        df['synth_deviation_pct'] = np.where(
            pd.notna(dev) & (S > 0), dev / S * 100, np.nan)

        # ---------- 3. 隐含融资利率(从市场价反推的资金价格) ----------
        # r_impl = -ln((S·e^(-qT) - (C-P))/K)/T, 要求分子>0
        with np.errstate(invalid='ignore', divide='ignore'):
            disc_residual = disc_s - net_cost
            ok_rate = (disc_residual > 0) & (K > 0) & (years > 0) & pd.notna(disc_residual)
            r_impl = np.where(ok_rate, -np.log(disc_residual / K) / years, np.nan)
        df['implied_financing_rate'] = r_impl
        # 利差(bp): 多头视角越负合成越便宜; 空头视角越正卖出收得越多
        df['financing_spread_bp'] = np.where(
            pd.notna(r_impl) & pd.notna(r), (r_impl - r) * 1e4, np.nan)

        # ---------- 4. 净Greeks(持仓口径: 买腿+, 卖腿取反) 与 Delta 校验 ----------
        delta_c = df['delta'].values.astype(float)
        gamma_c = df['gamma'].values.astype(float)
        theta_c = df['theta'].values.astype(float)
        vega_c = df['vega'].values.astype(float)
        delta_p = df['delta_put'].values.astype(float)
        gamma_p = df['gamma_put'].values.astype(float)
        theta_p = df['theta_put'].values.astype(float)
        vega_p = df['vega_put'].values.astype(float)

        # 多头(买C卖P): net = g_c - g_p; 空头(卖C买P): net = g_p - g_c = -(g_c - g_p)
        raw_delta = np.where(pd.notna(delta_c) & pd.notna(delta_p), delta_c - delta_p, np.nan)
        df['net_delta'] = dirn * raw_delta
        df['net_gamma'] = dirn * np.where(pd.notna(gamma_c) & pd.notna(gamma_p),
                                          gamma_c - gamma_p, np.nan)
        # theta: 多头买C(-theta)卖P(+theta)净损耗小; 符号随方向翻转
        df['net_theta'] = dirn * np.where(pd.notna(theta_c) & pd.notna(theta_p),
                                          theta_c - theta_p, np.nan)
        df['net_vega'] = dirn * np.where(pd.notna(vega_c) & pd.notna(vega_p),
                                         vega_c - vega_p, np.nan)
        # Delta校验: 合成头寸净Delta应≈±1, 偏离过大=脏配对(虚值档/数据错位)
        df['delta_check_passed'] = np.where(
            pd.notna(df['net_delta']),
            (np.abs(df['net_delta'] - dirn) <= self.DELTA_CHECK_TOL).astype(float),
            np.nan)

        # ---------- 5. 卖出腿保证金粗估与资金效率 ----------
        # 交易所公式粗估: 卖出腿权利金 + max(12%×S - 虚值额, 7%×S)
        # 多头卖Put(虚值=max(K-S,0)); 空头卖Call(虚值=max(S-K,0))
        if dirn > 0:
            short_leg_price, otm, buy_leg_price = P, np.maximum(K - S, 0), C
        else:
            short_leg_price, otm, buy_leg_price = C, np.maximum(S - K, 0), P
        margin_est = short_leg_price + np.maximum(
            self.MARGIN_RATE * S - otm, self.MARGIN_FLOOR_RATE * S)
        df['margin_est'] = margin_est
        # 资金占用 = 卖出腿保证金 + 买入腿全额权利金(每单位), 对比现货全额S
        capital_per_unit = np.where(
            pd.notna(margin_est) & pd.notna(buy_leg_price),
            margin_est + buy_leg_price, np.nan)
        df['capital_occupied_cny'] = capital_per_unit * mult
        df['margin_vs_spot_capital'] = np.where(
            pd.notna(capital_per_unit) & (S > 0), capital_per_unit / S, np.nan)

        # ---------- 6. 收益结构 ----------
        # 到期损益(多头) = S_T - K - (C-P), 盈亏平衡点 = K + (C-P); 空头镜像
        be = K + dirn * net_cost
        df['breakeven'] = np.where(pd.notna(net_cost) & (K > 0), be, np.nan)
        df['breakeven_pct'] = np.where(
            pd.notna(be) & (S > 0), (be - S) / S * 100, np.nan)

        # ---------- 7. 评分与排名 ----------
        # 多头: dev越负越便宜 → score=-dev%; 空头: dev越正卖出收得越多 → score=+dev%
        dev_pct = df['synth_deviation_pct'].values
        df['score'] = np.where(pd.notna(dev_pct), -dirn * dev_pct, np.nan)
        df['combo_rank'] = df.groupby('trade_date')['score'].rank(
            ascending=False, method='first').fillna(0).astype(int)

        # ---------- 8. 双腿定价偏差(框架惯例, 落库供报告端展示) ----------
        bs_c = df['bs_theoretical_price'].values.astype(float)
        bs_p = df['bs_theoretical_price_put'].values.astype(float)
        df['close_vs_theoretical'] = np.where(pd.notna(bs_c) & pd.notna(C), C - bs_c, np.nan)
        df['close_vs_theoretical_pct'] = np.where(
            pd.notna(bs_c) & (bs_c > 0), (C - bs_c) / bs_c * 100, np.nan)
        df['close_vs_theoretical_put'] = np.where(pd.notna(bs_p) & pd.notna(P), P - bs_p, np.nan)
        df['close_vs_theoretical_pct_put'] = np.where(
            pd.notna(bs_p) & (bs_p > 0), (P - bs_p) / bs_p * 100, np.nan)
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
        valid = df['score'].notna() & (df['delta_check_passed'] == 1)
        if valid.sum() > 0:
            v = df[valid]
            logger.info(f"  delta_check passed: {len(v)}/{len(df)} combos")
            logger.info(f"  synth_deviation_pct: mean={v['synth_deviation_pct'].mean():.3f}%, "
                        f"best={v['synth_deviation_pct'].min():.3f}%, "
                        f"worst={v['synth_deviation_pct'].max():.3f}%")
            logger.info(f"  financing_spread_bp: mean={v['financing_spread_bp'].mean():.1f}bp, "
                        f"min={v['financing_spread_bp'].min():.1f}bp")
            logger.info(f"  margin_vs_spot_capital: mean={v['margin_vs_spot_capital'].mean():.3f}")
        return df

    # ================================================================
    # 组合配对(与Long Straddle同构, 行权价档位放宽至ATM±5)
    # ================================================================
    def _build_pairs(self, df):
        """按交易日配对同月同K的Call+Put, 输出每行一个组合

        Call腿字段无后缀, Put腿带 _put 后缀(与框架惯例一致);
        合成对K不敏感, 取ATM±5档控制组合数量的同时保留选档自由度。
        """
        frames = []
        n_dates = 0
        for trade_date, g in df.groupby('trade_date', sort=True):
            n_dates += 1
            g = g.dropna(subset=['exercise_price', 'close'])
            if g.empty:
                continue

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
                    'ts_code': row_c['ts_code'],
                    'symbol': row_c['symbol'],
                    'opt_name': row_c['opt_name'],
                    'opt_exchange': row_c['opt_exchange'],
                    'ts_code_put': row_p['ts_code'],
                    'symbol_put': row_p['symbol'],
                    'opt_name_put': row_p['opt_name'],
                    'call_put': 'CP',
                    'exercise_price': common[i],
                    'opt_multiplier': row_c['opt_multiplier'],
                    's_month': row_c['s_month'],
                    'maturity_date': row_c['maturity_date'],
                    'days_to_maturity': row_c['days_to_maturity'],
                    'years_to_maturity_calendar': row_c['years_to_maturity_calendar'],
                    'spot_price': S0,
                    'moneyness_status': row_c['moneyness_status'],
                    'risk_free_rate': row_c['risk_free_rate'],
                    'dividend_yield': row_c['dividend_yield'],
                    'premium': float(row_c['close']),
                    'premium_put': float(row_p['close']),
                    'implied_vol': row_c['implied_vol'],
                    'implied_vol_put': row_p['implied_vol'],
                    'iv_rank': row_c['iv_rank'],
                    'iv_rank_put': row_p['iv_rank'],
                    'delta': row_c['delta'],
                    'gamma': row_c['gamma'],
                    'theta': row_c['theta'],
                    'vega': row_c['vega'],
                    'delta_put': row_p['delta'],
                    'gamma_put': row_p['gamma'],
                    'theta_put': row_p['theta'],
                    'vega_put': row_p['vega'],
                    'bs_theoretical_price': row_c['bs_theoretical_price'],
                    'bs_theoretical_price_put': row_p['bs_theoretical_price'],
                })

        logger.info(f"Pairing done: {n_dates} trade dates -> {len(frames)} combos")
        return pd.DataFrame(frames)

    # ================================================================
    # Step 5: 多情景盈亏(对照组=直接持有/融券现货)
    # ================================================================
    def calc_scenario_pnl(self, df, scenarios=None):
        """多情景盈亏: S_T = S0 * factor

        统一方向化公式: 组合P&L = DIRECTION × (S_T - K - (C-P))
        现货对照 P&L = DIRECTION × (S_T - S0)  (多头=买现货, 空头=融券做空)
        收益率基准 = 资金占用(保证金+买入腿权利金), 非5%权利金口径——
        合成股票的"本金"是占用资金, 这是其资金效率叙事的核心。
        """
        if df.empty:
            return df
        if scenarios is None:
            scenarios = self.DEFAULT_SCENARIOS

        logger.info(f"Calculating multi-scenario P&L for {len(scenarios)} scenarios: {scenarios}")

        dirn = float(self.DIRECTION)
        S = df['spot_price'].values.astype(float)
        K = df['exercise_price'].values.astype(float)
        net_cost = df['synthetic_net_cost'].values.astype(float)
        mult = df['opt_multiplier'].values.astype(float)
        # 资金占用(每单位): margin_est + 买入腿权利金
        if 'capital_per_unit' not in df.columns:
            if dirn > 0:
                buy_leg = df['premium'].values.astype(float)
            else:
                buy_leg = df['premium_put'].values.astype(float)
            df['capital_per_unit'] = df['margin_est'].values + buy_leg
        capital = df['capital_per_unit'].values.astype(float)

        for factor in scenarios:
            s_T = S * factor
            combo_pnl = dirn * (s_T - K - net_cost)
            unhedged_pnl = dirn * (s_T - S)
            label = f'{factor:.2f}'.replace('.', '_')
            df[f'scenario_pnl_{label}S'] = combo_pnl
            df[f'scenario_pnl_{label}S_cny'] = combo_pnl * mult
            # 收益率以资金占用为本金(合成股票的资金效率视角)
            df[f'scenario_pnl_{label}S_pct'] = np.where(
                capital > 0, combo_pnl / capital * 100, np.nan)
            df[f'unhedged_pnl_{label}S'] = unhedged_pnl
            df[f'unhedged_pnl_{label}S_pct'] = np.where(
                S > 0, unhedged_pnl / S * 100, np.nan)

        # capital_per_unit 为临时列, 不在 TARGET_COLUMNS, 落库时自动丢弃
        logger.info("Multi-scenario P&L calculated")
        return df

    # ================================================================
    # Step 6: 交易信号(方向化叙事: 多头比融资成本, 空头比融券成本)
    # ================================================================
    def _assign_trade_signals(self, df):
        """分配交易信号 — 合成成本偏离 + 隐含资金利率 + 风控校验

        多头视角(用合成替代买入现货):
            financing_spread_bp <= -10 且偏离<0: 隐含融资利率显著低于基准, 合成便宜
        空头视角(用合成替代融券做空):
            synth_deviation_pct > 0: 卖出合成收价高于理论, 且对照融券年化成本
        共同风控: Delta校验失败→降级; 临近到期→展期; 分红季→股息噪声标注。
        """
        if df.empty:
            return df

        dirn = float(self.DIRECTION)
        dev_pct = df['synth_deviation_pct'].values
        spread_bp = df['financing_spread_bp'].values
        dcheck = df['delta_check_passed'].values
        days = df['days_to_maturity'].values
        years = df['years_to_maturity_calendar'].values
        margin_ratio = df['margin_vs_spot_capital'].values
        vol_c = df['implied_vol'].values
        vol_p = df['implied_vol_put'].values
        trade_dates = df['trade_date'].astype(str).values

        signals = np.full(len(df), 'AVOID', dtype=object)
        signal_reasons = np.full(len(df), '', dtype=object)

        for i in range(len(df)):
            reasons = []

            # ---- 0. Delta 校验(脏配对一票否决) ----
            if pd.isna(dev_pct[i]) and pd.isna(spread_bp[i]):
                signals[i] = 'N/A'
                signal_reasons[i] = '数据不足'
                continue
            if pd.notna(dcheck[i]) and dcheck[i] < 1:
                signals[i] = 'AVOID'
                signal_reasons[i] = (f'净Delta={df["net_delta"].iloc[i]:.3f}'
                                     f'偏离±{self.DELTA_CHECK_TOL}, 配对脏数据')
                continue

            # ---- 1. 方向化信号 ----
            if dirn > 0:
                # 合成多头: 隐含融资利率 vs 基准利率
                sp = spread_bp[i]
                if pd.notna(sp) and sp <= -10 and pd.notna(dev_pct[i]) and dev_pct[i] < 0:
                    signals[i] = 'STRONG_BUY'
                    reasons.append(f'融资利差={sp:+.1f}bp<=-10(隐含融资利率显著低于基准)')
                    reasons.append(f'合成偏离={dev_pct[i]:+.3f}%S<0(比买现货便宜)')
                elif pd.notna(sp) and sp <= 0:
                    signals[i] = 'BUY'
                    reasons.append(f'融资利差={sp:+.1f}bp<=0(合成不劣于融资买现货)')
                elif pd.notna(sp) and sp <= 20:
                    signals[i] = 'CONSIDER'
                    reasons.append(f'融资利差={sp:+.1f}bp(合成略贵, 需资金效率补偿)')
                elif pd.notna(sp) and sp <= 50:
                    signals[i] = 'NEUTRAL'
                    reasons.append(f'融资利差={sp:+.1f}bp(合成明显贵于基准资金)')
                else:
                    signals[i] = 'AVOID'
                    reasons.append(f'融资利差={sp if pd.notna(sp) else np.nan:+.1f}bp>50'
                                   if pd.notna(sp) else '融资利差缺失')
            else:
                # 合成空头: 卖出收价偏离 + 年化成本对照融券
                dp = dev_pct[i]
                if pd.notna(dp) and dp >= 0.5:
                    signals[i] = 'STRONG_BUY'
                    reasons.append(f'合成偏离={dp:+.3f}%S>=0.5%(卖出收价显著高于理论)')
                elif pd.notna(dp) and dp > 0:
                    signals[i] = 'BUY'
                    reasons.append(f'合成偏离={dp:+.3f}%S>0(卖出收价高于理论)')
                elif pd.notna(dp) and dp >= -0.2:
                    signals[i] = 'CONSIDER'
                    reasons.append(f'合成偏离={dp:+.3f}%S(接近公允)')
                elif pd.notna(dp) and dp >= -0.5:
                    signals[i] = 'NEUTRAL'
                    reasons.append(f'合成偏离={dp:+.3f}%S(做空成本偏高)')
                else:
                    signals[i] = 'AVOID'
                    reasons.append(f'合成偏离={dp:+.3f}%S<-0.5%(合成的做空成本过高)')
                # 对照融券成本: 年化做空成本 = -dev/S/T
                if pd.notna(dp) and pd.notna(years[i]) and years[i] > 0:
                    annual_cost_bp = -dp / 100 / years[i] * 1e4
                    if annual_cost_bp < self.SHORT_BORROW_COST_BP:
                        reasons.append(f'合成年化做空成本≈{annual_cost_bp:.0f}bp'
                                       f'<融券基准{self.SHORT_BORROW_COST_BP:.0f}bp(融券替代有效)')

            # ---- 2. 共同风控理由 ----
            if pd.notna(days[i]) and days[i] < 10:
                reasons.append(f'仅剩{days[i]:.0f}天到期(Pin risk, 建议强平或展期)')
            elif pd.notna(days[i]) and days[i] > 120:
                reasons.append(f'距到期{days[i]:.0f}天>120(远月流动性差, 优选近月)')
            month = str(trade_dates[i])[4:6]
            if month in ('11', '12'):
                reasons.append('ETF分红季(11~12月): 股息率q估计误差直接进入合成成本, 偏离解读需谨慎')
            if pd.notna(margin_ratio[i]) and margin_ratio[i] > 0.5:
                reasons.append(f'资金占用/现货={margin_ratio[i]:.2f}>0.5(资金效率优势有限)')
            if pd.notna(margin_ratio[i]) and margin_ratio[i] > 0 and margin_ratio[i] < 0.3:
                reasons.append(f'资金占用/现货={margin_ratio[i]:.2f}(约{1 / margin_ratio[i]:.1f}倍资金效率)')
            if (pd.notna(vol_c[i])) and (pd.notna(vol_p[i])) \
                    and abs(vol_c[i] - vol_p[i]) / max(vol_c[i], vol_p[i], 1e-9) > 0.15:
                reasons.append('双腿IV差异>15%(报价失真或单腿无流动性, 偏离不可交易)')

            signal_reasons[i] = '; '.join(reasons)

        df['trade_signal'] = signals
        df['signal_reason'] = signal_reasons

        signal_counts = pd.Series(signals).value_counts()
        logger.info(f"Trade signals: {signal_counts.to_dict()}")

        return df

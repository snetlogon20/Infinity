r"""
期权 Greeks 效率扫描器 (Greeks Efficiency Scanner) — 波动率风险溢价交易 + 期权性价比筛选

专业定位:
    Volatility Risk Premium (VRP) + Greeks efficiency ratios —— 回答
    "今天该做买方还是卖方、哪几个合约性价比最高":
        1. vrp = IV - HV20: 隐含贵于实际 → 偏卖方收租; 倒挂 → 偏买方做多波动率
        2. gamma_breakeven_move = sqrt(2*|theta|/gamma): 日平衡波幅 ——
           delta 对冲持仓下, 当日标的真实波幅超过此值, gamma 损失吃掉 theta 收入
           (卖方核心刻度, 与 HV/sqrt(252) 的"已实现日波幅"对照)
        3. gamma/vega_per_premium: 买方性价比(每元权利金换多少 gamma/vega 敞口)
        4. PCP z-score / deviation_type 联查: 结构性错价配对直接标记(不可交易的"假便宜")
        5. 流动性闸门(oi/amount): 落单前必过滤

数据流:
    tb_tushare_opt_daily_indicator (C+P, BS Greeks/IV/moneyness)
      + HV 现算(spot_price 序列, 20/60日)
      + tb_option_pcp_monitor (call_ts_code/put_ts_code 精确联查)
      + df_tushare_opt_basic (symbol/name)
    → tb_option_greeks_efficiency (每行 = 合约 x 交易日, 含卖方分/买方分/角色推荐/信号)

使用:
    config = {
        "name": "华夏上证50ETF期权 Greeks效率扫描",
        "start_date": "20250901",
        "end_date": CommonParameters.today,
        "symbol_filter": "510050%",
    }
    GreeksEfficiencyAnalysis().run(config)

注意:
    call_put 固定取 None(双腿都扫), 卖方/买方选腿在报告端按 role_recommend 过滤。
"""

import json
from datetime import datetime

import numpy as np
import pandas as pd

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.common.ReportJobLogger import ReportJobLogger
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.modelService.option.OptionTradingStrategyManager.OptionStrategyBase import (
    OptionStrategyBase
)

logger = CommonLib.logger


class GreeksEfficiencyAnalysis(OptionStrategyBase):
    """期权 Greeks 效率扫描器"""

    # === 策略标识 ===
    STRATEGY_TYPE = 'GREEKS_EFFICIENCY'
    ANALYSIS_VERSION = 'v1'
    TABLE_TARGET = 'tb_option_greeks_efficiency'

    # === 表名常量 ===
    TABLE_PCP = 'tb_option_pcp_monitor'

    # === HV 参数(实际波动率现算) ===
    HV_WINDOWS = (20, 60)          # 短/长窗口(交易日)
    HV_LOOKBACK_CAL_DAYS = 400     # HV 取数回看日历天数(覆盖 60 交易日 + 新合约缓冲)
    HV_MIN_OBS = 10                # 每窗口最少样本数, 不足置 NaN

    # === 过滤闸门 ===
    LIQ_MIN_OI = 500               # 持仓量下限(手)
    LIQ_MIN_AMOUNT = 20            # 当日成交额下限(万元)
    MIN_DAYS_TO_MATURITY = 5       # 距到期下限(太近 theta/gamma 失真, Pin risk)
    MAX_DAYS_TO_MATURITY = 270     # 距到期上限(远月流动性差)

    # === 信号阈值 ===
    ROLE_DIFF_THRESHOLD = 10.0     # 卖方分-买方分超过此值判定角色
    SIGNAL_SCORE_THRESHOLD = 65.0  # 角色分超过此值才给 SELL_VOL/BUY_VOL 信号

    # === 目标表字段(与建表 SQL 逐列对齐) ===
    TARGET_COLUMNS = [
        # 策略标识与审计
        'strategy_type', 'analysis_time', 'analysis_params', 'analysis_version',
        # 合约标识
        'trade_date', 'ts_code', 'symbol', 'opt_name', 'opt_exchange', 'call_put',
        'underlying_key',
        # 合约要素
        'exercise_price', 'opt_multiplier', 's_month', 'maturity_date',
        'days_to_maturity', 'years_to_maturity_calendar',
        'moneyness_status', 'moneyness_log',
        # 标的市场
        'spot_price', 'risk_free_rate', 'dividend_yield',
        # 行情与波动率
        'close', 'implied_vol', 'iv_rank', 'hv20', 'hv60',
        # 波动率风险溢价
        'vrp', 'vrp_bp', 'vrp_ratio',
        # 单腿 Greeks
        'delta', 'gamma', 'theta', 'vega', 'rho',
        # Greeks 效率比
        'gamma_breakeven_move', 'gamma_breakeven_move_pct',
        'theta_gamma_ratio', 'vega_theta_ratio',
        'gamma_per_premium', 'vega_per_premium',
        # 定价偏差
        'bs_theoretical_price', 'close_vs_theoretical_pct', 'price_bias',
        # PCP 结构性错价过滤
        'pcp_z_score', 'pcp_deviation_type',
        # 流动性闸门
        'oi', 'vol', 'amount', 'turnover_ratio', 'liq_flag',
        # 评分与排名
        'seller_score', 'buyer_score', 'seller_rank', 'buyer_rank', 'role_recommend',
        # 交易信号
        'trade_signal', 'signal_reason',
    ]

    # save_to_clickhouse 字符串列覆写(本表专有)
    STR_COLUMNS = {
        'strategy_type', 'analysis_params', 'analysis_version',
        'trade_date', 'ts_code', 'symbol', 'opt_name', 'opt_exchange',
        'call_put', 'underlying_key', 's_month', 'maturity_date', 'moneyness_status',
        'price_bias', 'pcp_deviation_type', 'liq_flag',
        'role_recommend', 'trade_signal', 'signal_reason',
    }

    # ================================================================
    # 标的键提取: ETF 取 symbol 前6位, 股指期权取 ts_code 前缀(HO/IO/MO)
    # ================================================================
    @staticmethod
    def _underlying_key(symbol, ts_code):
        s = str(symbol or '')
        if len(s) >= 6 and s[:6].isdigit():
            return s[:6]
        tc = str(ts_code or '')
        if len(tc) >= 2 and tc[:2].isalpha():
            return tc[:2]
        return s or tc

    @staticmethod
    def _underlying_prefix_from_filter(symbol_filter):
        """从 symbol_filter 提取标的前缀(去月份限定, 供 HV 现货序列取数用)

        '510050%2612%' → '510050', 'HO2612%' → 'HO', None → None
        """
        if not symbol_filter:
            return None
        token = symbol_filter.split('%')[0].strip()
        return token if token else None

    # ================================================================
    # Step 1: 拉取 C+P 双腿指标(含 turnover_ratio, 全窗口)
    # ================================================================
    def fetch_data(self, start_date, end_date, symbol_filter=None, exercise_type=None):
        """从 indicator 表拉取双腿全量指标, join basic 补充 symbol/name"""
        logger.info("=" * 80)
        logger.info(f"Fetching C+P option data: [{start_date}, {end_date}], "
                    f"symbol_filter={symbol_filter}")

        where_clauses = [
            f"ind.trade_date >= '{start_date}'",
            f"ind.trade_date <= '{end_date}'",
        ]
        if symbol_filter:
            where_clauses.append(
                f"ind.ts_code IN ("
                f"SELECT DISTINCT ts_code FROM indexsysdb.{self.TABLE_BASIC} "
                f"WHERE symbol LIKE '{symbol_filter}' OR ts_code LIKE '{symbol_filter}'"
                f")"
            )
        if exercise_type:
            where_clauses.append(f"b.exercise_type = '{exercise_type}'")
        where_str = "\n              AND ".join(where_clauses)

        sql = f"""
        SELECT
            ind.trade_date, ind.ts_code, ind.call_put,
            ind.exercise_price, ind.opt_multiplier, ind.s_month, ind.maturity_date,
            ind.days_to_maturity, ind.years_to_maturity_calendar,
            ind.moneyness_status, ind.moneyness_log,
            ind.spot_price, ind.risk_free_rate, ind.dividend_yield,
            ind.close, ind.settle, ind.vol, ind.amount, ind.oi, ind.turnover_ratio,
            ind.implied_vol, ind.bs_theoretical_price,
            ind.delta, ind.gamma, ind.theta, ind.vega, ind.rho,
            b.symbol       AS symbol,
            b.name         AS opt_name,
            b.exchange     AS opt_exchange
        FROM indexsysdb.{self.TABLE_INDICATOR} ind
        LEFT JOIN (
            SELECT ts_code,
                   any(symbol)   AS symbol,
                   any(name)     AS name,
                   any(exchange) AS exchange
            FROM indexsysdb.{self.TABLE_BASIC}
            GROUP BY ts_code
        ) b ON ind.ts_code = b.ts_code
        WHERE {where_str}
        ORDER BY ind.trade_date, ind.call_put, ind.exercise_price
        """
        logger.info(f"SQL:\n{sql}")
        df_raw = ClickhouseService.getDataFrameWithoutColumnsName(sql)

        if len(df_raw) == 0:
            logger.warning("No data fetched, returning empty DataFrame")
            return pd.DataFrame()

        logger.info(f"Fetched {len(df_raw)} rows, {len(df_raw.columns)} columns")
        numeric_cols = [
            'exercise_price', 'opt_multiplier', 'days_to_maturity',
            'years_to_maturity_calendar', 'moneyness_log',
            'spot_price', 'risk_free_rate', 'dividend_yield',
            'close', 'settle', 'vol', 'amount', 'oi', 'turnover_ratio',
            'implied_vol', 'bs_theoretical_price',
            'delta', 'gamma', 'theta', 'vega', 'rho',
        ]
        for col in numeric_cols:
            if col in df_raw.columns:
                df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce')
        for col in ['trade_date', 'ts_code', 'call_put', 's_month', 'maturity_date',
                    'moneyness_status', 'symbol', 'opt_name', 'opt_exchange']:
            if col in df_raw.columns:
                df_raw[col] = df_raw[col].fillna('').astype(str)

        df_raw['underlying_key'] = [
            self._underlying_key(sym, tc)
            for sym, tc in zip(df_raw['symbol'], df_raw['ts_code'])
        ]
        return df_raw

    # ================================================================
    # Step 2: HV 实际波动率现算(spot_price 序列, 年化)
    # ================================================================
    def _fetch_spot_history(self, end_date, underlying_prefix=None):
        """拉取标的现货日序列(经 symbol 前缀过滤, 去月份限定避免新合约截断历史)"""
        where_clauses = [
            f"toDate(ind.trade_date) <= toDate('{end_date}')",
            f"toDate(ind.trade_date) >= "
            f"subtractDays(toDate('{end_date}'), {self.HV_LOOKBACK_CAL_DAYS})",
            "ind.spot_price > 0",
        ]
        if underlying_prefix:
            where_clauses.append(
                f"(b.symbol LIKE '{underlying_prefix}%' OR ind.ts_code LIKE '{underlying_prefix}%')"
            )
        sql = f"""
        SELECT DISTINCT ind.trade_date AS trade_date,
                        b.symbol       AS symbol,
                        ind.spot_price AS spot_price,
                        ind.ts_code    AS ts_code
        FROM indexsysdb.{self.TABLE_INDICATOR} ind
        INNER JOIN (
            SELECT ts_code, any(symbol) AS symbol
            FROM indexsysdb.{self.TABLE_BASIC}
            GROUP BY ts_code
        ) b ON ind.ts_code = b.ts_code
        WHERE {' AND '.join(where_clauses)}
        """
        logger.info(f"Fetching spot history for HV (prefix={underlying_prefix})")
        df_spot = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        if len(df_spot) == 0:
            logger.warning("No spot history fetched")
            return pd.DataFrame()
        df_spot['spot_price'] = pd.to_numeric(df_spot['spot_price'], errors='coerce')
        df_spot['underlying_key'] = [
            self._underlying_key(sym, tc)
            for sym, tc in zip(df_spot['symbol'], df_spot['ts_code'])
        ]
        # 每标的每交易日取一条(多合约重复)
        df_spot = (df_spot.dropna(subset=['spot_price'])
                   .drop_duplicates(subset=['underlying_key', 'trade_date']))
        logger.info(f"Spot history: {len(df_spot)} obs, "
                    f"{df_spot['underlying_key'].nunique()} underlyings")
        return df_spot

    def _calc_hv(self, df, end_date, underlying_prefix=None):
        """按 (underlying_key, trade_date) 计算 HV20/HV60(年化对数收益std x sqrt(252))"""
        logger.info(f"Calculating HV (windows={self.HV_WINDOWS})...")
        df_spot = self._fetch_spot_history(end_date, underlying_prefix)
        hv_map = {}
        if len(df_spot) > 0:
            for key, g in df_spot.groupby('underlying_key'):
                g = g.sort_values('trade_date')
                s = pd.to_numeric(g['spot_price'], errors='coerce')
                ret = np.log(s / s.shift(1)).dropna()
                for win in self.HV_WINDOWS:
                    h = (ret.rolling(win, min_periods=min(win, self.HV_MIN_OBS))
                         .std() * np.sqrt(252.0))
                    # ret[0] 为 NaN, 日期与窗口值都从第 2 个观测起对齐
                    for d, v in zip(g['trade_date'].values[1:], h.values[1:]):
                        if pd.notna(v):
                            hv_map.setdefault((key, str(d)), {})[win] = float(v)
        n_hit = df.apply(
            lambda r: 1 if (r['underlying_key'], str(r['trade_date'])) in hv_map else 0,
            axis=1).sum() if len(df) else 0
        logger.info(f"HV map built: {len(hv_map)} keys, matched {n_hit}/{len(df)} rows")

        hv20, hv60 = [], []
        for _, r in df.iterrows():
            info = hv_map.get((r['underlying_key'], str(r['trade_date'])), {})
            hv20.append(info.get(20, np.nan))
            hv60.append(info.get(60, np.nan))
        df['hv20'] = hv20
        df['hv60'] = hv60
        return df

    # ================================================================
    # Step 3: PCP 结构性错价联查(call_ts_code/put_ts_code 精确匹配)
    # ================================================================
    def _join_pcp(self, df, start_date, end_date):
        """联查 tb_option_pcp_monitor: z_score / deviation_type(结构性错价标记)"""
        logger.info("Joining PCP monitor (z_score / deviation_type)...")
        sql = f"""
        SELECT trade_date, call_ts_code, put_ts_code, z_score, deviation_type
        FROM indexsysdb.{self.TABLE_PCP}
        WHERE trade_date >= '{start_date}' AND trade_date <= '{end_date}'
        """
        df_pcp = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        if len(df_pcp) == 0:
            logger.warning("No PCP monitor data in range, pcp columns set to NaN")
            df['pcp_z_score'] = np.nan
            df['pcp_deviation_type'] = ''
            return df

        pcp_map = {}
        for _, r in df_pcp.iterrows():
            z, dt = float(r['z_score']) if pd.notna(r['z_score']) else np.nan, \
                str(r['deviation_type'] or '')
            pcp_map[(str(r['trade_date']), str(r['call_ts_code']))] = (z, dt)
            pcp_map[(str(r['trade_date']), str(r['put_ts_code']))] = (z, dt)

        z_col, t_col = [], []
        for _, r in df.iterrows():
            z, dt = pcp_map.get((str(r['trade_date']), str(r['ts_code'])),
                                (np.nan, ''))
            z_col.append(z)
            t_col.append(dt)
        df['pcp_z_score'] = z_col
        df['pcp_deviation_type'] = t_col
        n_hit = df['pcp_z_score'].notna().sum()
        logger.info(f"PCP joined: {n_hit}/{len(df)} rows matched")
        return df

    # ================================================================
    # Step 4: 核心指标(VRP / Greeks 效率比 / 流动性闸门 / 定价偏差)
    # ================================================================
    def _calc_efficiency_metrics(self, df):
        """Greeks 效率核心指标计算"""
        logger.info("Calculating Greeks efficiency metrics...")
        S = df['spot_price'].values.astype(float)
        close = df['close'].values.astype(float)
        iv = df['implied_vol'].values.astype(float)
        hv20 = df['hv20'].values.astype(float)
        gamma = df['gamma'].values.astype(float)
        theta = df['theta'].values.astype(float)
        vega = df['vega'].values.astype(float)
        theo = df['bs_theoretical_price'].values.astype(float)

        # ---- 1. VRP(波动率风险溢价) ----
        df['vrp'] = np.where(pd.notna(iv) & pd.notna(hv20), iv - hv20, np.nan)
        df['vrp_bp'] = df['vrp'] * 1e4
        df['vrp_ratio'] = np.where(
            pd.notna(iv) & pd.notna(hv20) & (hv20 > 0), iv / hv20, np.nan)

        # ---- 2. 日平衡波幅 sqrt(2|theta|/gamma) ----
        # delta 对冲持仓: gamma 损失 0.5*G*dS^2 与 theta 收入 |theta| 打平的 dS
        with np.errstate(invalid='ignore', divide='ignore'):
            be_move = np.where(
                (gamma > 1e-12) & (np.abs(theta) > 0),
                np.sqrt(2.0 * np.abs(theta) / np.where(gamma > 1e-12, gamma, np.nan)),
                np.nan)
        df['gamma_breakeven_move'] = be_move
        df['gamma_breakeven_move_pct'] = np.where(
            pd.notna(be_move) & (S > 0), be_move / S * 100, np.nan)

        # ---- 3. 效率比 ----
        with np.errstate(invalid='ignore', divide='ignore'):
            df['theta_gamma_ratio'] = np.where(
                gamma > 1e-12, np.abs(theta) / np.where(gamma > 1e-12, gamma, np.nan),
                np.nan)
            df['vega_theta_ratio'] = np.where(
                np.abs(theta) > 1e-12,
                vega / np.where(np.abs(theta) > 1e-12, np.abs(theta), np.nan), np.nan)
            df['gamma_per_premium'] = np.where(
                close > 1e-12, gamma / np.where(close > 1e-12, close, np.nan), np.nan)
            df['vega_per_premium'] = np.where(
                close > 1e-12, vega / np.where(close > 1e-12, close, np.nan), np.nan)

        # ---- 4. 定价偏差(相对 BS 理论价) ----
        df['close_vs_theoretical_pct'] = np.where(
            pd.notna(theo) & (theo > 0) & pd.notna(close),
            (close - theo) / theo * 100, np.nan)
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

        # ---- 5. 流动性闸门 ----
        oi = df['oi'].values
        amount = df['amount'].values
        days = df['days_to_maturity'].values
        liq = np.full(len(df), 'PASS', dtype=object)
        liq[(oi < self.LIQ_MIN_OI) | (amount < self.LIQ_MIN_AMOUNT)] = 'FAIL'
        liq[(days < self.MIN_DAYS_TO_MATURITY) | (days > self.MAX_DAYS_TO_MATURITY)] = 'FAIL'
        df['liq_flag'] = liq
        logger.info(f"Liquidity gate: PASS={np.sum(liq == 'PASS')}, "
                    f"FAIL={np.sum(liq == 'FAIL')}")

        # ---- 6. 评分(百分位合成, 0~100, 仅有效行) ----
        valid = (
            (df['liq_flag'] == 'PASS')
            & df['vrp'].notna() & df['iv_rank'].notna()
            & df['gamma_breakeven_move_pct'].notna()
            & df['close_vs_theoretical_pct'].notna()
        )
        for col in ['vrp_pct', 'ivr_pct', 'be_pct', 'rich_pct', 'gpp_pct']:
            df[col] = np.nan

        sub = df[valid]
        if len(sub) > 0:
            g = sub.groupby('trade_date')
            df.loc[valid, 'vrp_pct'] = g['vrp'].rank(pct=True)
            df.loc[valid, 'ivr_pct'] = g['iv_rank'].rank(pct=True)
            df.loc[valid, 'be_pct'] = g['gamma_breakeven_move_pct'].rank(pct=True)
            df.loc[valid, 'rich_pct'] = g['close_vs_theoretical_pct'].rank(pct=True)
            df.loc[valid, 'gpp_pct'] = g['gamma_per_premium'].rank(pct=True)

            # 卖方: 高VRP + 高IV分位 + 高日平衡波幅 + 市价贵于理论(卖出收得多)
            df.loc[valid, 'seller_score'] = 100.0 * (
                0.40 * df.loc[valid, 'vrp_pct']
                + 0.20 * df.loc[valid, 'ivr_pct']
                + 0.20 * df.loc[valid, 'be_pct']
                + 0.20 * df.loc[valid, 'rich_pct'])
            # 买方: 低VRP(负溢价) + 低IV分位 + 高gamma/权利金 + 市价便宜于理论
            df.loc[valid, 'buyer_score'] = 100.0 * (
                0.40 * (1 - df.loc[valid, 'vrp_pct'])
                + 0.20 * (1 - df.loc[valid, 'ivr_pct'])
                + 0.20 * df.loc[valid, 'gpp_pct']
                + 0.20 * (1 - df.loc[valid, 'rich_pct']))
        else:
            df['seller_score'] = np.nan
            df['buyer_score'] = np.nan

        # ---- 7. 角色推荐 ----
        seller, buyer = df['seller_score'], df['buyer_score']
        role = np.full(len(df), 'AVOID', dtype=object)
        both = df['seller_score'].notna() & df['buyer_score'].notna()
        role[both & ((seller - buyer) >= self.ROLE_DIFF_THRESHOLD)] = 'SELLER'
        role[both & ((buyer - seller) >= self.ROLE_DIFF_THRESHOLD)] = 'BUYER'
        role[both & (np.abs(seller - buyer) < self.ROLE_DIFF_THRESHOLD)] = 'NEUTRAL'
        df['role_recommend'] = role

        # ---- 8. 排名(同日同角色) ----
        df['seller_rank'] = (df[df['seller_score'].notna()]
                             .groupby('trade_date')['seller_score']
                             .rank(ascending=False, method='first'))
        df['seller_rank'] = df['seller_rank'].fillna(0).astype(int)
        df['buyer_rank'] = (df[df['buyer_score'].notna()]
                            .groupby('trade_date')['buyer_score']
                            .rank(ascending=False, method='first'))
        df['buyer_rank'] = df['buyer_rank'].fillna(0).astype(int)

        n_valid = int(valid.sum())
        if n_valid:
            v = df[valid]
            logger.info(f"  valid rows: {n_valid}/{len(df)}")
            logger.info(f"  vrp_bp: mean={v['vrp_bp'].mean():.1f}, "
                        f"max={v['vrp_bp'].max():.1f}, min={v['vrp_bp'].min():.1f}")
            logger.info(f"  role: SELLER={np.sum(v['role_recommend'] == 'SELLER')}, "
                        f"BUYER={np.sum(v['role_recommend'] == 'BUYER')}, "
                        f"NEUTRAL={np.sum(v['role_recommend'] == 'NEUTRAL')}")
        return df

    # ================================================================
    # Step 5: 交易信号(SELL_VOL / BUY_VOL / NEUTRAL / AVOID)
    # ================================================================
    def _assign_trade_signals(self, df):
        """分配交易信号 — VRP方向 + Greeks效率 + 流动性/PCP/到期风控闸门"""
        if df.empty:
            return df

        signals = np.full(len(df), 'AVOID', dtype=object)
        reasons = np.full(len(df), '', dtype=object)
        iv, hv, vrp = (df['implied_vol'].values, df['hv20'].values,
                       df['vrp_bp'].values)
        iv_rank = df['iv_rank'].values
        be_pct = df['gamma_breakeven_move_pct'].values
        realized_daily = np.where(pd.notna(hv) & (hv > 0), hv / np.sqrt(252.0) * 100,
                                  np.nan)
        rich = df['close_vs_theoretical_pct'].values
        pcp_z = df['pcp_z_score'].values
        pcp_type = df['pcp_deviation_type'].values
        days = df['days_to_maturity'].values
        seller, buyer = df['seller_score'].values, df['buyer_score'].values
        role = df['role_recommend'].values
        liq = df['liq_flag'].values

        for i in range(len(df)):
            rs = []

            # ---- 0. 无效行 ----
            if pd.isna(seller[i]) or pd.isna(iv[i]) or pd.isna(hv[i]):
                signals[i] = 'AVOID'
                rs.append('数据不足(IV/HV/评分缺失)' if liq[i] == 'PASS' else '流动性闸门FAIL')
                reasons[i] = '; '.join(rs)
                continue

            # ---- 1. 方向信号: VRP + 角色分 ----
            if role[i] == 'SELLER' and seller[i] >= self.SIGNAL_SCORE_THRESHOLD:
                signals[i] = 'SELL_VOL'
                rs.append(f'VRP={vrp[i]:+.0f}bp(隐含贵于实际, 卖方收租)')
                rs.append(f'日平衡波幅{be_pct[i]:.2f}% vs 已实现日波幅'
                          f'{realized_daily[i]:.2f}%(theta安全垫覆盖)')
                if pd.notna(rich[i]) and rich[i] > 1:
                    rs.append(f'市价高于理论{rich[i]:+.1f}%(卖出收得多)')
            elif role[i] == 'BUYER' and buyer[i] >= self.SIGNAL_SCORE_THRESHOLD:
                signals[i] = 'BUY_VOL'
                rs.append(f'VRP={vrp[i]:+.0f}bp(隐含便宜/倒挂, 买方占优)')
                rs.append(f'IV分位{iv_rank[i]:.2f}(历史低位)')
                if pd.notna(rich[i]) and rich[i] < -1:
                    rs.append(f'市价低于理论{rich[i]:+.1f}%(买入便宜)')
            else:
                signals[i] = 'NEUTRAL'
                rs.append(f'VRP={vrp[i]:+.0f}bp, 卖方分{seller[i]:.0f}/买方分{buyer[i]:.0f}'
                          f'(方向不明确)')

            # ---- 2. 风控理由 ----
            if pd.notna(pcp_z[i]) and abs(pcp_z[i]) > 2:
                rs.append(f'PCP z={pcp_z[i]:+.1f}(|z|>2, 该K档C/P配对存在结构性错价, 报价可信度低)')
            if str(pcp_type[i]) in ('REAL_ARBITRAGE', 'STRONG_ARBITRAGE'):
                rs.append(f'PCP分类={pcp_type[i]}(结构性错价档, 谨慎对待)')
            if pd.notna(days[i]) and days[i] < 10:
                rs.append(f'仅剩{days[i]:.0f}天到期(Pin risk, gamma集中)')
            if pd.notna(be_pct[i]) and pd.notna(realized_daily[i]) \
                    and be_pct[i] < realized_daily[i] and role[i] == 'SELLER':
                rs.append('日平衡波幅<已实现日波幅(theta收入覆盖不了gamma风险, 卖方危险)')

            reasons[i] = '; '.join(rs)

        df['trade_signal'] = signals
        df['signal_reason'] = reasons
        counts = pd.Series(signals).value_counts()
        logger.info(f"Trade signals: {counts.to_dict()}")
        return df

    # ================================================================
    # Step 6: 落库覆写(支持本表字符串列 + 排名整型)
    # ================================================================
    def save_to_clickhouse(self, df, config):
        """写入 tb_option_greeks_efficiency(增量: trade_date + symbol LIKE)"""
        if len(df) == 0:
            logger.warning("Empty DataFrame, nothing to save")
            return

        logger.info(f"Saving {len(df)} rows to {self.TABLE_TARGET}")
        df = df.copy()
        df['strategy_type'] = self.STRATEGY_TYPE
        df['analysis_time'] = datetime.now().replace(microsecond=0)
        df['analysis_params'] = json.dumps(config, ensure_ascii=False, default=str)
        df['analysis_version'] = self.ANALYSIS_VERSION

        available_cols = [c for c in self.TARGET_COLUMNS if c in df.columns]
        df_output = df[available_cols].copy()

        for col in df_output.columns:
            if col == 'analysis_time':
                continue
            if col in self.STR_COLUMNS:
                df_output[col] = df_output[col].fillna('').astype(str)
            elif col in ('days_to_maturity', 'seller_rank', 'buyer_rank'):
                df_output[col] = pd.to_numeric(
                    df_output[col], errors='coerce').fillna(0).astype(int)
            else:
                df_output[col] = pd.to_numeric(df_output[col], errors='coerce')
                df_output[col] = df_output[col].where(pd.notna(df_output[col]), None)

        # 增量删除: 按 trade_date + symbol LIKE(与既有策略表口径一致)
        symbol_filter = config.get('symbol_filter')
        trade_dates = df_output['trade_date'].unique().tolist()
        dates_str = "','".join(trade_dates)
        delete_conditions = [
            f"strategy_type = '{self.STRATEGY_TYPE}'",
            f"trade_date IN ('{dates_str}')",
        ]
        if symbol_filter:
            delete_conditions.append(f"symbol LIKE '{symbol_filter}'")
        del_sql = (f"ALTER TABLE indexsysdb.{self.TABLE_TARGET} DELETE WHERE "
                   f"{' AND '.join(delete_conditions)}")
        logger.info(f"SQL:\n{del_sql}")
        ClickhouseService.execute_sql(del_sql)
        logger.info(f"Deleted data for trade_dates: {len(trade_dates)} dates")

        ClickhouseService.save_dataframe_to_clickhouse(
            dataframe=df_output, table_name=self.TABLE_TARGET, database='indexsysdb')
        logger.info(f"Saved {len(df_output)} rows to {self.TABLE_TARGET}")
        return df_output

    # ================================================================
    # 主流程
    # ================================================================
    def run(self, config):
        """主流程: 拉取 → HV → IV分位 → PCP联查 → 效率指标/评分 → 信号 → 落库

        Args:
            config: name / start_date / end_date / symbol_filter / exercise_type
        """
        name = config.get('name', 'Unknown')
        start_date = config.get('start_date')
        end_date = config.get('end_date') or CommonParameters.today
        symbol_filter = config.get('symbol_filter')
        exercise_type = config.get('exercise_type')

        logger.info("\n" + "=" * 80)
        logger.info(f"{self.__class__.__name__}.run: {name}")
        logger.info(f"  Period: [{start_date}, {end_date}], symbol_filter={symbol_filter}")
        logger.info("=" * 80)

        job_logger = ReportJobLogger()
        job_logger.start_job(self.__class__.__name__, 'OptionStrategyAnalysis',
                             params={'report_name': name, 'start_date': start_date,
                                     'end_date': end_date, 'symbol_filter': symbol_filter})
        try:
            # Step 1: 拉取双腿指标
            logger.info("\nStep 1/6: Fetching C+P indicator data...")
            df = self.fetch_data(start_date=start_date, end_date=end_date,
                                 symbol_filter=symbol_filter,
                                 exercise_type=exercise_type)
            if len(df) == 0:
                logger.warning(f"[{name}] No data found, skipping")
                job_logger.end_job_success(records_processed=0)
                return None

            # Step 2: 清洗(spot/close/K 有效)
            logger.info("\nStep 2/6: Cleaning...")
            df = self._clean_and_filter(df)
            if len(df) == 0:
                logger.warning(f"[{name}] No valid data after cleaning, skipping")
                job_logger.end_job_success(records_processed=0)
                return None

            # Step 3: HV 实际波动率现算
            logger.info("\nStep 3/6: Calculating realized vol (HV20/HV60)...")
            prefix = self._underlying_prefix_from_filter(symbol_filter)
            df = self._calc_hv(df, end_date, prefix)

            # Step 4: IV 分位(复用基类 60 日窗口)
            logger.info("\nStep 4/6: Calculating IV rank...")
            df = self.calc_iv_rank(df, end_date)

            # Step 5: PCP 联查 + 效率指标/评分 + 信号
            logger.info("\nStep 5/6: Joining PCP & calculating efficiency metrics...")
            df = self._join_pcp(df, start_date, end_date)
            df = self._calc_efficiency_metrics(df)
            df = self._assign_trade_signals(df)

            # Step 6: 落库
            logger.info("\nStep 6/6: Saving to ClickHouse...")
            self.save_to_clickhouse(df, config)

            logger.info(f"\n{'='*80}")
            logger.info(f"[{name}] Analysis done: {len(df)} rows -> {self.TABLE_TARGET}")
            logger.info(f"{'='*80}")
            job_logger.end_job_success(records_processed=len(df))
            return df

        except Exception as e:
            import traceback
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise

"""
期权日线指标计算服务

专业分类：
  Level 1 - 盘面硬指标（Trading P&L）
  Level 2 - 时间指标（Time Metrics）
  Level 3 - 价态（Moneyness）
  Level 4 - 隐含波动率（Implied Volatility）
  Level 5 - Greeks（风险暴露）

数据流：
  df_tushare_opt_daily
    + df_tushare_opt_basic (ON ts_code)
    + df_tushare_cn_index_daily (ON trade_date + opt_code→ts_code)
    ↓
  计算指标
    ↓
  tb_tushare_opt_daily_indicator
"""

import sys
import math
import numpy as np
import pandas as pd
from datetime import datetime, date
from scipy.stats import norm
from scipy.optimize import fsolve
from py_vollib.black_scholes.implied_volatility import implied_volatility as vollib_iv
from py_vollib.black_scholes import black_scholes as vollib_bs

from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator import CommonLib
from dataIntegrator.modelService.derivatives.options.Greeks.OptionGreeks import OptionGreeks

logger = CommonLib.logger
commonLib = CommonLib()


class TuShareOptDailyIndicatorService:
    """期权日线指标计算服务"""

    # === 表名常量 ===
    TABLE_DAILY = 'df_tushare_opt_daily'
    TABLE_BASIC = 'df_tushare_opt_basic'
    TABLE_INDEX_DAILY = 'df_tushare_cn_index_daily'
    TABLE_TARGET = 'tb_tushare_opt_daily_indicator'

    # === 默认参数 ===
    DEFAULT_RISK_FREE_RATE = 0.03          # 3% 默认无风险利率
    DEFAULT_DIVIDEND_YIELD = 0.0           # 默认股息率
    TRADING_DAYS_PER_YEAR = 252            # 年化交易天数
    CALENDAR_DAYS_PER_YEAR = 365           # 年化日历天数
    ATM_THRESHOLD = 0.01                   # 平值判定阈值 (|S-K|/K < 1%)

    # === 合约前缀 → 标的指数代码映射 ===
    # CFFEX 指数期权前缀与对应指数
    CONTRACT_INDEX_MAP = {
        'HO': '000016.SH',  # 上证50（cn_index_daily中可能缺失）
        'IO': '000300.SH',  # 沪深300
        'MO': '000852.SH',  # 中证1000
        # SSE/SZSE ETF期权：合约代码包含标的ETF代码，暂不自动映射
    }

    # === 目标表字段顺序 ===
    TARGET_COLUMNS = [
        'ts_code', 'trade_date',
        'call_put', 'exercise_price', 'opt_multiplier', 's_month', 'maturity_date',
        'pre_close', 'close', 'pre_settle', 'settle', 'open', 'high', 'low',
        'vol', 'amount', 'oi',
        'mtm_pnl_close', 'mtm_pnl_settle', 'point_change', 'pct_change',
        'turnover_ratio', 'avg_unit_price',
        'days_to_maturity', 'years_to_maturity_calendar', 'years_to_maturity_trading',
        'moneyness_status', 'moneyness_log',
        'spot_price', 'risk_free_rate',
        'implied_vol', 'bs_theoretical_price',
        'delta', 'gamma', 'vega', 'theta', 'rho',
    ]

    def __init__(self):
        self.writeLogInfo(
            className=self.__class__.__name__,
            functionName=sys._getframe().f_code.co_name,
            event="TuShareOptDailyIndicatorService initialized"
        )

    # ================================================================
    # Logging
    # ================================================================
    def writeLogInfo(self, className="unknown", functionName="unknown", event="unknown"):
        print("%s.%s: %s" % (className, functionName, event))
        logger.info("%s.%s: %s" % (className, functionName, event))

    # ================================================================
    # Level 0: 数据获取
    # ================================================================
    def fetch_data(self, start_date=None, end_date=None):
        """从 ClickHouse 获取期权日线 + 基础信息，并通过合约前缀匹配标的指数行情

        Args:
            start_date: 开始日期 YYYYMMDD，默认90天前
            end_date: 结束日期 YYYYMMDD，默认今天

        Returns:
            pd.DataFrame: 合并后的原始数据
        """
        self.writeLogInfo(
            className=self.__class__.__name__,
            functionName=sys._getframe().f_code.co_name,
            event="Fetching option daily data from ClickHouse"
        )

        if end_date is None:
            end_date = date.today().strftime('%Y%m%d')
        if start_date is None:
            from datetime import timedelta
            start_date = (date.today() - timedelta(days=90)).strftime('%Y%m%d')

        # ---- Step 1: 拉取期权日线 + 基础信息（LEFT JOIN，仅匹配当前活跃合约）----
        sql = f"""
        SELECT
            opt.ts_code                                       AS ts_code,
            opt.trade_date                                    AS trade_date,
            opt.pre_settle                                    AS pre_settle,
            opt.pre_close                                     AS pre_close,
            opt.open                                          AS open,
            opt.high                                          AS high,
            opt.low                                           AS low,
            opt.close                                         AS close,
            opt.settle                                        AS settle,
            opt.vol                                           AS vol,
            opt.amount                                        AS amount,
            opt.oi                                            AS oi,
            basic.call_put                                    AS call_put,
            basic.exercise_price                              AS exercise_price,
            basic.opt_multiplier                              AS opt_multiplier,
            basic.s_month                                     AS s_month,
            basic.maturity_date                               AS maturity_date,
            basic.exchange                                    AS exchange
        FROM indexsysdb.{self.TABLE_DAILY} opt
        LEFT JOIN indexsysdb.{self.TABLE_BASIC} basic
            ON opt.ts_code = basic.ts_code
        WHERE opt.trade_date >= '20260717'
          AND opt.trade_date <= '20260717'
          	AND call_put = 'C'  -- C=看涨期权, P=看跌期权
            AND exercise_type = '欧式'
            AND basic.ts_code like 'HO2612%'
        ORDER BY opt.trade_date, opt.ts_code
        """

        print(sql)

        df = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        logger.info(f"Fetched {len(df)} rows of option daily data")
        logger.info(f"Columns: {list(df.columns)}")

        if len(df) == 0:
            logger.warning("No data fetched, returning empty DataFrame")
            return df

        # ---- Step 2: 拉取指数行情数据 ----
        logger.info("Fetching index daily data for spot price...")
        idx_sql = f"""
        SELECT trade_date, ts_code, close
        FROM indexsysdb.{self.TABLE_INDEX_DAILY}
        WHERE trade_date >= '{start_date}'
          AND trade_date <= '{end_date}'
        ORDER BY trade_date, ts_code
        """
        df_idx = ClickhouseService.getDataFrameWithoutColumnsName(idx_sql)
        logger.info(f"Fetched {len(df_idx)} rows of index daily data")

        # 构建 (trade_date, ts_code) → close 的映射字典
        idx_dict = {}
        if len(df_idx) > 0:
            df_idx.columns = ['trade_date', 'ts_code', 'close']
            for _, row in df_idx.iterrows():
                key = (str(row['trade_date']), str(row['ts_code']))
                idx_dict[key] = float(row['close']) if pd.notna(row['close']) else np.nan

        # ---- Step 3: 类型转换 ----
        numeric_cols = [
            'pre_settle', 'pre_close', 'open', 'high', 'low',
            'close', 'settle', 'vol', 'amount', 'oi',
            'exercise_price', 'opt_multiplier'
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # String 列填充
        for col in ['call_put', 's_month', 'maturity_date', 'exchange']:
            if col in df.columns:
                df[col] = df[col].fillna('').astype(str)

        # ---- Step 3b: 从 ts_code 回退解析 call_put 和 exercise_price ----
        # 当 LEFT JOIN 匹配不到 basic 表时，直接从 ts_code 提取
        # 格式: PREFIXYYMM-C/P-STRIKE.EXCHANGE，如 A2609-C-3400.DCE 或 HO2612-C-2500.CFX
        parsed = df['ts_code'].astype(str).str.extract(
            r'^[A-Za-z]+\d{4}-([CP])-(\d+)\..*$', expand=True
        )
        parsed.columns = ['_parsed_cp', '_parsed_strike']
        parsed['_parsed_strike'] = pd.to_numeric(parsed['_parsed_strike'], errors='coerce')

        # 填补缺失的 call_put（basic 表未匹配到时为 ''）
        mask_cp = df['call_put'].isna() | (df['call_put'] == '')
        df.loc[mask_cp, 'call_put'] = parsed.loc[mask_cp, '_parsed_cp']

        # 填补缺失的 exercise_price
        mask_k = df['exercise_price'].isna() | (df['exercise_price'] == 0)
        df.loc[mask_k, 'exercise_price'] = parsed.loc[mask_k, '_parsed_strike']

        # 统计填补情况
        logger.info(f"call_put available: {df['call_put'].notna().sum()}/{len(df)}, "
                    f"exercise_price available: {df['exercise_price'].notna().sum()}/{len(df)}")

        # ---- Step 4: 通过合约前缀映射获取标的指数代码 ----
        # CFFEX 指数期权 ts_code 格式：HO2612-C-2500.CFX
        # 前缀 HO→000016.SH, IO→000300.SH, MO→000852.SH
        def _get_index_code(ts_code):
            """从合约代码中提取指数代码"""
            ts_str = str(ts_code).strip()
            for prefix, index_code in self.CONTRACT_INDEX_MAP.items():
                if ts_str.startswith(prefix):
                    return index_code
            return None

        df['_index_code'] = df['ts_code'].apply(_get_index_code)

        # ---- Step 5: 匹配标的 spot_price ----
        spot_prices = []
        for _, row in df.iterrows():
            trade_date = str(row['trade_date'])
            index_code = row['_index_code']
            if pd.notna(index_code) and index_code is not None:
                key = (trade_date, index_code)
                spot = idx_dict.get(key, np.nan)
            else:
                spot = np.nan
            spot_prices.append(spot)

        df['spot_price'] = spot_prices

        # ---- Step 5b: 对缺失 spot_price 的行，逐个指数代码回退查询 ----
        missing_mask = df['spot_price'].isna() & df['_index_code'].notna()
        if missing_mask.any():
            missing_index_codes = df.loc[missing_mask, '_index_code'].unique()
            logger.info(f"Spot price missing for {missing_mask.sum()} rows, "
                        f"missing index codes: {list(missing_index_codes)}. Attempting fallback query...")

            for index_code in missing_index_codes:
                fallback_sql = f"""
                SELECT trade_date, close
                FROM indexsysdb.{self.TABLE_INDEX_DAILY}
                WHERE ts_code = '{index_code}'
                  AND trade_date >= '{start_date}'
                  AND trade_date <= '{end_date}'
                ORDER BY trade_date
                """
                try:
                    df_fallback = ClickhouseService.getDataFrameWithoutColumnsName(fallback_sql)
                    if len(df_fallback) > 0:
                        df_fallback.columns = ['trade_date', 'close']
                        fallback_dict = {}
                        for _, fb_row in df_fallback.iterrows():
                            key = str(fb_row['trade_date'])
                            fallback_dict[key] = float(fb_row['close']) if pd.notna(fb_row['close']) else np.nan

                        # 用 fallback 数据填补
                        for idx in df.index[missing_mask]:
                            if df.loc[idx, '_index_code'] == index_code:
                                td = str(df.loc[idx, 'trade_date'])
                                if td in fallback_dict:
                                    df.loc[idx, 'spot_price'] = fallback_dict[td]
                except Exception as e:
                    logger.warning(f"Fallback query failed for index {index_code}: {e}")

            logger.info(f"After fallback: spot_price available for {df['spot_price'].notna().sum()}/{len(df)} rows")

        df.drop(columns=['_index_code'], inplace=True)

        # 统计 spot 覆盖率
        spot_count = df['spot_price'].notna().sum()
        total = len(df)
        logger.info(f"spot_price available for {spot_count}/{total} rows ({spot_count/total*100:.1f}%)")

        logger.info(f"Data fetch completed. Shape: {df.shape}")
        return df

    # ================================================================
    # Level 1: 盘面硬指标 (Trading P&L)
    # ================================================================
    def _calc_trading_metrics(self, df):
        """计算盘面硬指标

        1. mtm_pnl_close: 日内浮动盈亏 (close - pre_close) * opt_multiplier
        2. mtm_pnl_settle: 结算盯市盈亏 (settle - pre_settle) * opt_multiplier
        3. point_change: 日内涨跌(指数点) close - pre_close
        4. pct_change: 日内涨跌幅(%)
        5. turnover_ratio: 换手率(近似) vol / oi
        6. avg_unit_price: 平均每手成交均价
        """
        self.writeLogInfo(
            className=self.__class__.__name__,
            functionName=sys._getframe().f_code.co_name,
            event="Calculating trading P&L metrics"
        )

        df['mtm_pnl_close'] = (df['close'] - df['pre_close']) * df['opt_multiplier']
        df['mtm_pnl_settle'] = (df['settle'] - df['pre_settle']) * df['opt_multiplier']
        df['point_change'] = df['close'] - df['pre_close']
        df['pct_change'] = np.where(
            (df['pre_close'].notna()) & (df['pre_close'] != 0),
            (df['close'] / df['pre_close'] - 1) * 100,
            np.nan
        )

        # 换手率：vol / oi（持仓量可能为 0）
        df['turnover_ratio'] = np.where(
            (df['oi'].notna()) & (df['oi'] > 0),
            df['vol'] / df['oi'],
            np.nan
        )

        # 平均每手成交均价：amount(万元) * 10000 / vol(手) → 元/手
        df['avg_unit_price'] = np.where(
            (df['vol'].notna()) & (df['vol'] > 0),
            df['amount'] * 10000 / df['vol'],
            np.nan
        )

        logger.info(f"Trading metrics calculated. NaN counts:\n{df[['mtm_pnl_close','mtm_pnl_settle','point_change','pct_change','turnover_ratio','avg_unit_price']].isna().sum()}")
        return df

    # ================================================================
    # Level 2: 时间指标 (Time Metrics)
    # ================================================================
    def _calc_time_metrics(self, df):
        """计算时间指标

        1. days_to_maturity: 距离到期日历天数
        2. years_to_maturity_calendar: 日历/365
        3. years_to_maturity_trading: 交易日/252
        """
        self.writeLogInfo(
            className=self.__class__.__name__,
            functionName=sys._getframe().f_code.co_name,
            event="Calculating time to maturity metrics"
        )

        # 解析日期
        df['_trade_date_dt'] = pd.to_datetime(df['trade_date'], format='%Y%m%d', errors='coerce')
        df['_maturity_date_dt'] = pd.to_datetime(df['maturity_date'], format='%Y%m%d', errors='coerce')

        # 天数 = maturity - trade_date
        df['days_to_maturity'] = (df['_maturity_date_dt'] - df['_trade_date_dt']).dt.days
        df['days_to_maturity'] = df['days_to_maturity'].clip(lower=0)  # 已到期的设为0

        df['years_to_maturity_calendar'] = df['days_to_maturity'] / self.CALENDAR_DAYS_PER_YEAR
        df['years_to_maturity_trading'] = df['days_to_maturity'] / self.TRADING_DAYS_PER_YEAR

        # 清理临时列
        df.drop(columns=['_trade_date_dt', '_maturity_date_dt'], inplace=True)

        logger.info(f"Time metrics calculated. Days range: [{df['days_to_maturity'].min()}, {df['days_to_maturity'].max()}]")
        return df

    # ================================================================
    # Level 3: 价态 (Moneyness)
    # ================================================================
    def _calc_moneyness(self, df):
        """计算价态

        1. moneyness_status: ITM(实值)/ATM(平值)/OTM(虚值)
           - Call: S>K → ITM, S≈K → ATM, S<K → OTM
           - Put:  S<K → ITM, S≈K → ATM, S>K → OTM
        2. moneyness_log: ln(K/S) / sqrt(T) 【按用户指定公式】
        """
        self.writeLogInfo(
            className=self.__class__.__name__,
            functionName=sys._getframe().f_code.co_name,
            event="Calculating moneyness"
        )

        def _moneyness_status(row):
            s = row.get('spot_price')
            k = row.get('exercise_price')
            cp = str(row.get('call_put', '')).upper()
            if pd.isna(s) or pd.isna(k) or s == 0 or k == 0:
                return 'N/A'
            ratio = abs(s - k) / k
            if ratio < self.ATM_THRESHOLD:
                return 'ATM'
            if cp == 'C':
                return 'ITM' if s > k else 'OTM'
            elif cp == 'P':
                return 'ITM' if s < k else 'OTM'
            return 'N/A'

        df['moneyness_status'] = df.apply(_moneyness_status, axis=1)

        # 对数价态: ln(K/S) / sqrt(T)
        t = df['years_to_maturity_calendar']
        s = df['spot_price']
        k = df['exercise_price']
        df['moneyness_log'] = np.where(
            (s.notna()) & (k > 0) & (t > 0),
            np.log(k / s) / np.sqrt(t),
            np.nan
        )

        status_counts = df['moneyness_status'].value_counts()
        logger.info(f"Moneyness distribution:\n{status_counts}")
        return df

    # ================================================================
    # Level 4 & 5: 隐含波动率 & Greeks
    # ================================================================
    def _calc_implied_vol_and_greeks(self, df):
        """计算隐含波动率和 Greeks

        使用 py_vollib（若可用）或 scipy.fsolve 计算隐含波动率，
        使用现有 OptionGreeks 计算希腊值。

        依赖：spot_price, exercise_price, years_to_maturity_calendar
        """
        self.writeLogInfo(
            className=self.__class__.__name__,
            functionName=sys._getframe().f_code.co_name,
            event="Calculating implied volatility and Greeks"
        )

        # 预填默认无风险利率
        df['risk_free_rate'] = self.DEFAULT_RISK_FREE_RATE

        # ---- BS 定价函数 ----
        def bs_call_price(S, K, T, r, sigma):
            if T <= 0 or sigma <= 0:
                return np.nan
            d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)
            return S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)

        def bs_put_price(S, K, T, r, sigma):
            if T <= 0 or sigma <= 0:
                return np.nan
            d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)
            return K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

        # ---- 对每行计算 ----
        implied_vol_list = []
        bs_price_list = []
        delta_list = []
        gamma_list = []
        vega_list = []
        theta_list = []
        rho_list = []

        for idx, row in df.iterrows():
            s = row.get('spot_price')
            k = row.get('exercise_price')
            t = row.get('years_to_maturity_calendar')
            r = self.DEFAULT_RISK_FREE_RATE
            market_price = row.get('close')
            cp = str(row.get('call_put', '')).upper()

            # 检查必要参数是否完整
            can_calc = (
                pd.notna(s) and pd.notna(k) and pd.notna(t) and pd.notna(market_price)
                and s > 0 and k > 0 and t > 0 and market_price > 0
            )

            if not can_calc:
                implied_vol_list.append(np.nan)
                bs_price_list.append(np.nan)
                delta_list.append(np.nan)
                gamma_list.append(np.nan)
                vega_list.append(np.nan)
                theta_list.append(np.nan)
                rho_list.append(np.nan)
                continue

            # ---- 隐含波动率 ----
            iv = np.nan

            # 预检查：期权价格不能低于内在价值（否则无有效IV）
            intrinsic_value = max(s - k, 0.0) if cp == 'C' else max(k - s, 0.0)
            if market_price < intrinsic_value * 0.999:
                logger.debug(
                    f"Skip IV for {row['ts_code']} on {row['trade_date']}: "
                    f"market_price({market_price:.2f}) < intrinsic_value({intrinsic_value:.2f})"
                )
            else:
                try:
                    flag = 'c' if cp == 'C' else 'p'
                    iv = vollib_iv(market_price, s, k, t, r, flag)
                    # 限制合理范围
                    if pd.notna(iv) and (iv <= 0 or iv > 3.0):
                        iv = np.nan
                except Exception as e:
                    logger.warning(f"IV calculation failed for {row['ts_code']} on {row['trade_date']}: {e}")
                    iv = np.nan

            implied_vol_list.append(iv)

            # ---- BS 理论价 ----
            bs_price = np.nan
            if pd.notna(iv) and iv > 0:
                try:
                    flag = 'c' if cp == 'C' else 'p'
                    bs_price = vollib_bs(flag, s, k, t, r, iv)
                except Exception:
                    bs_price = np.nan
            bs_price_list.append(bs_price)

            # ---- Greeks ----
            if pd.notna(iv) and iv > 0:
                try:
                    greeks = OptionGreeks.calculate_all_greeks(
                        S=s, K=k, T=t, r=r, y=self.DEFAULT_DIVIDEND_YIELD,
                        sigma=iv, option_type='call' if cp == 'C' else 'put'
                    )
                    delta_list.append(greeks['delta'])
                    gamma_list.append(greeks['gamma'])
                    vega_list.append(greeks['vega'])
                    theta_list.append(greeks['theta'])
                    rho_list.append(greeks['rho'])
                except Exception as e:
                    logger.warning(f"Greeks calculation failed for {row['ts_code']} on {row['trade_date']}: {e}")
                    delta_list.append(np.nan)
                    gamma_list.append(np.nan)
                    vega_list.append(np.nan)
                    theta_list.append(np.nan)
                    rho_list.append(np.nan)
            else:
                delta_list.append(np.nan)
                gamma_list.append(np.nan)
                vega_list.append(np.nan)
                theta_list.append(np.nan)
                rho_list.append(np.nan)

        df['implied_vol'] = implied_vol_list
        df['bs_theoretical_price'] = bs_price_list
        df['delta'] = delta_list
        df['gamma'] = gamma_list
        df['vega'] = vega_list
        df['theta'] = theta_list
        df['rho'] = rho_list

        iv_count = df['implied_vol'].notna().sum()
        logger.info(f"Implied volatility calculated for {iv_count}/{len(df)} rows")
        greeks_count = df['delta'].notna().sum()
        logger.info(f"Greeks calculated for {greeks_count}/{len(df)} rows")

        return df

    # ================================================================
    # 主流程
    # ================================================================
    def calculate_indicators(self, df):
        """依次计算所有指标"""
        self.writeLogInfo(
            className=self.__class__.__name__,
            functionName=sys._getframe().f_code.co_name,
            event="Calculating all option indicators"
        )

        if len(df) == 0:
            logger.warning("Empty DataFrame, skipping calculations")
            return df

        df = self._calc_trading_metrics(df)
        df = self._calc_time_metrics(df)
        df = self._calc_moneyness(df)
        df = self._calc_implied_vol_and_greeks(df)

        return df

    def save_to_clickhouse(self, df):
        """写入 ClickHouse 目标表

        策略：先 DELETE WHERE 1=1 清空（不删表），再批量 INSERT
        """
        self.writeLogInfo(
            className=self.__class__.__name__,
            functionName=sys._getframe().f_code.co_name,
            event=f"Saving {len(df)} rows to {self.TABLE_TARGET}"
        )

        if len(df) == 0:
            logger.warning("Empty DataFrame, nothing to save")
            return

        # 确保只保存目标表字段
        available_cols = [c for c in self.TARGET_COLUMNS if c in df.columns]
        df_to_save = df[available_cols].copy()

        # 处理 NaN → 0.0 或空字符串
        for col in df_to_save.columns:
            if col in ('ts_code', 'trade_date', 'call_put', 's_month', 'maturity_date', 'moneyness_status'):
                df_to_save[col] = df_to_save[col].fillna('').astype(str)
            elif col in ('days_to_maturity',):
                df_to_save[col] = pd.to_numeric(df_to_save[col], errors='coerce').fillna(0).astype(int)
            else:
                df_to_save[col] = pd.to_numeric(df_to_save[col], errors='coerce').fillna(0.0)

        # 全量覆写：删除旧数据
        del_sql = f"ALTER TABLE indexsysdb.{self.TABLE_TARGET} DELETE WHERE 1=1"
        ClickhouseService.execute_sql(del_sql)
        logger.info(f"Deleted all data from {self.TABLE_TARGET}")

        # 写入
        ClickhouseService.save_dataframe_to_clickhouse(
            dataframe=df_to_save,
            table_name=self.TABLE_TARGET,
            database='indexsysdb'
        )
        logger.info(f"Saved {len(df_to_save)} rows to {self.TABLE_TARGET}")

    def run(self, start_date=None, end_date=None):
        """主流程：拉取 → 计算 → 保存

        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            pd.DataFrame: 计算后的完整数据
        """
        self.writeLogInfo(
            className=self.__class__.__name__,
            functionName=sys._getframe().f_code.co_name,
            event="=" * 80
        )
        self.writeLogInfo(
            className=self.__class__.__name__,
            functionName=sys._getframe().f_code.co_name,
            event="Starting option daily indicator generation"
        )
        self.writeLogInfo(
            className=self.__class__.__name__,
            functionName=sys._getframe().f_code.co_name,
            event="=" * 80
        )

        # Step 1: 拉取数据
        logger.info("\nStep 1/3: Fetching option daily data from ClickHouse...")
        df = self.fetch_data(start_date=start_date, end_date=end_date)

        if len(df) == 0:
            logger.warning("No data fetched, aborting")
            return df

        # Step 2: 计算指标
        logger.info("\nStep 2/3: Calculating option indicators...")
        df = self.calculate_indicators(df)

        # Step 3: 保存
        logger.info("\nStep 3/3: Saving to ClickHouse...")
        self.save_to_clickhouse(df)

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("Option daily indicator generation completed!")
        logger.info(f"   Total rows: {len(df)}, Total columns: {len(df.columns)}")
        iv_count = df['implied_vol'].notna().sum()
        logger.info(f"   Implied Vol calculated: {iv_count}/{len(df)}")
        logger.info("=" * 80)

        return df


# ================================================================
# 独立运行入口
# ================================================================
if __name__ == "__main__":
    service = TuShareOptDailyIndicatorService()
    df = service.run(start_date='20260701', end_date='20260719')
    print(f"Done. DataFrame shape: {df.shape}")

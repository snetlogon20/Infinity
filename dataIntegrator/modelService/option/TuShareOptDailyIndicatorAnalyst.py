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
    + vw_tushare_opt_basic_of_today (ON ts_code, Tushare仅提供每日最新快照无历史)
    + df_tushare_cn_index_daily (ON trade_date + opt_code→ts_code)
    ↓
  计算指标
    ↓
  tb_tushare_opt_daily_indicator
"""

import math
import numpy as np
import pandas as pd
from datetime import datetime, date
from scipy.stats import norm
from scipy.optimize import brentq

from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator import CommonLib
from dataIntegrator.modelService.derivatives.options.Greeks.OptionGreeks import OptionGreeks

logger = CommonLib.logger


class TuShareOptDailyIndicatorAnalyst:
    """期权日线指标计算服务"""

    # === 表名常量 ===
    TABLE_DAILY = 'df_tushare_opt_daily'
    TABLE_BASIC = 'vw_tushare_opt_basic_of_today'  # Tushare仅提供每日最新快照，无历史数据，用 VIEW 取最新
    TABLE_INDEX_DAILY = 'df_tushare_cn_index_daily'
    TABLE_INDEX_DAILYBASIC = 'df_tushare_index_dailybasic'
    TABLE_TARGET = 'tb_tushare_opt_daily_indicator'

    # === 默认参数 ===
    DEFAULT_RISK_FREE_RATE = 0.03          # 3% 默认无风险利率
    DEFAULT_DIVIDEND_YIELD = 0.0           # 默认股息率（fallback，当无股息率数据时使用）
    DEFAULT_PAYOUT_RATIO = 0.30            # 默认分红比例，用于从 PE_TTM 估算股息率
    TRADING_DAYS_PER_YEAR = 252            # 年化交易天数

    # === 指数分红比例映射: dividend_yield ≈ payout_ratio / pe_ttm ===
    INDEX_DIVIDEND_PAYOUT_RATIO = {
        '000016.SH': 0.32,  # 上证50（HO期权标的）
        '000300.SH': 0.30,  # 沪深300（IO期权标的）
        '000852.SH': 0.25,  # 中证1000（MO期权标的）
    }
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

    # === 目标表字段顺序（trade_date 在首位，与建表 SQL 一致） ===
    TARGET_COLUMNS = [
        'trade_date', 'ts_code',
        'call_put', 'exercise_price', 'opt_multiplier', 's_month', 'maturity_date',
        'pre_close', 'close', 'pre_settle', 'settle', 'open', 'high', 'low',
        'vol', 'amount', 'oi',
        'mtm_pnl_close', 'mtm_pnl_settle', 'point_change', 'pct_change',
        'turnover_ratio', 'avg_unit_price',
        'days_to_maturity', 'years_to_maturity_calendar', 'years_to_maturity_trading',
        'moneyness_status', 'moneyness_log',
        'spot_price', 'risk_free_rate', 'dividend_yield',
        'implied_vol', 'bs_theoretical_price',
        'delta', 'gamma', 'vega', 'theta', 'rho',
        'd1', 'd2', 'nd1', 'nd2',
    ]

    def __init__(self):
        logger.info("TuShareOptDailyIndicatorService.__init__: initialized")

    # ================================================================
    # Level 0: 数据获取 — 子步骤
    # ================================================================
    def _build_where_clause(self, call_put=None, exercise_type=None,
                            ts_code_filter=None,
                            start_date=None, end_date=None):
        """构建期权日线查询的动态 WHERE 子句"""
        where_clauses = [
            f"opt.trade_date >= '{start_date}'",
            f"opt.trade_date <= '{end_date}'"
        ]
        if call_put:
            where_clauses.append(f"call_put = '{call_put}'")
        if exercise_type:
            where_clauses.append(f"exercise_type = '{exercise_type}'")
        if ts_code_filter:
            where_clauses.append(f"basic.ts_code like '{ts_code_filter}'")

        return "\n            AND ".join(where_clauses)

    def _fetch_option_daily_with_basic(self, where_str):
        """拉取期权日线 + 基础信息（LEFT JOIN 最新快照）"""
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
        WHERE {where_str}
        ORDER BY opt.trade_date, opt.ts_code
        """

        logger.info(f"SQL:\n{sql}")

        df_opt_daily = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        logger.info(f"Fetched {len(df_opt_daily)} rows of option daily data")
        logger.info(f"Columns: {list(df_opt_daily.columns)}")

        return df_opt_daily

    def _fetch_index_daily_dict(self, start_date, end_date):
        """拉取指数行情并构建 (trade_date, ts_code) → close 映射字典"""
        logger.info("Fetching index daily data for spot price...")
        idx_sql = f"""
        SELECT trade_date, ts_code, close
        FROM indexsysdb.{self.TABLE_INDEX_DAILY}
        WHERE trade_date >= '{start_date}'
          AND trade_date <= '{end_date}'
        ORDER BY trade_date, ts_code
        """
        logger.info(f"SQL:\n{idx_sql}")
        df_index_daily = ClickhouseService.getDataFrameWithoutColumnsName(idx_sql)
        logger.info(f"Fetched {len(df_index_daily)} rows of index daily data")

        idx_dict = {}
        if len(df_index_daily) > 0:
            df_index_daily.columns = ['trade_date', 'ts_code', 'close']
            for _, row in df_index_daily.iterrows():
                key = (str(row['trade_date']), str(row['ts_code']))
                idx_dict[key] = float(row['close']) if pd.notna(row['close']) else np.nan

        return idx_dict

    def _convert_types(self, df_opt_daily):
        """类型转换：数值列 → float，文本列 → str"""
        numeric_cols = [
            'pre_settle', 'pre_close', 'open', 'high', 'low',
            'close', 'settle', 'vol', 'amount', 'oi',
            'exercise_price', 'opt_multiplier'
        ]
        for col in numeric_cols:
            if col in df_opt_daily.columns:
                df_opt_daily[col] = pd.to_numeric(df_opt_daily[col], errors='coerce')

        for col in ['call_put', 's_month', 'maturity_date', 'exchange']:
            if col in df_opt_daily.columns:
                df_opt_daily[col] = df_opt_daily[col].fillna('').astype(str)

        return df_opt_daily

    def _enrich_from_ts_code(self, df_opt_daily):
        """从 ts_code 回退解析 call_put 和 exercise_price

        当 LEFT JOIN basic 表未匹配到时，从合约代码正则提取。
        格式: PREFIXYYMM-C/P-STRIKE.EXCHANGE, 如 A2609-C-3400.DCE 或 HO2612-C-2500.CFX
        """
        parsed = df_opt_daily['ts_code'].astype(str).str.extract(
            r'^[A-Za-z]+\d{4}-([CP])-(\d+)\..*$', expand=True
        )
        parsed.columns = ['_parsed_cp', '_parsed_strike']
        parsed['_parsed_strike'] = pd.to_numeric(parsed['_parsed_strike'], errors='coerce')

        mask_cp = df_opt_daily['call_put'].isna() | (df_opt_daily['call_put'] == '')
        df_opt_daily.loc[mask_cp, 'call_put'] = parsed.loc[mask_cp, '_parsed_cp']

        mask_k = df_opt_daily['exercise_price'].isna() | (df_opt_daily['exercise_price'] == 0)
        df_opt_daily.loc[mask_k, 'exercise_price'] = parsed.loc[mask_k, '_parsed_strike']

        logger.info(f"call_put available: {df_opt_daily['call_put'].notna().sum()}/{len(df_opt_daily)}, "
                    f"exercise_price available: {df_opt_daily['exercise_price'].notna().sum()}/{len(df_opt_daily)}")

        return df_opt_daily

    def _enrich_spot_prices(self, df_opt_daily, idx_dict, start_date, end_date):
        """通过合约前缀映射获取标的 spot_price（含回退查询）

        三步合一:
        1. 合约前缀 → 指数代码映射 (CONTRACT_INDEX_MAP)
        2. 用 idx_dict 主查询结果匹配 spot_price
        3. 缺失的逐个指数代码回退查询
        """
        # ---- Step 1: 合约前缀 → 指数代码 ----
        def _get_index_code(ts_code):
            ts_str = str(ts_code).strip()
            for prefix, index_code in self.CONTRACT_INDEX_MAP.items():
                if ts_str.startswith(prefix):
                    return index_code
            return None

        df_opt_daily['_index_code'] = df_opt_daily['ts_code'].apply(_get_index_code)

        # ---- Step 2: 用 idx_dict 匹配 spot_price ----
        spot_prices = []
        for _, row in df_opt_daily.iterrows():
            trade_date = str(row['trade_date'])
            index_code = row['_index_code']
            if pd.notna(index_code) and index_code is not None:
                spot = idx_dict.get((trade_date, index_code), np.nan)
            else:
                spot = np.nan
            spot_prices.append(spot)

        df_opt_daily['spot_price'] = spot_prices

        # ---- Step 3: 缺失 spot_price 的，逐个指数代码回退查询 ----
        missing_mask = df_opt_daily['spot_price'].isna() & df_opt_daily['_index_code'].notna()
        if missing_mask.any():
            missing_index_codes = df_opt_daily.loc[missing_mask, '_index_code'].unique()
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
                logger.info(f"SQL:\n{fallback_sql}")
                try:
                    df_index_fallback = ClickhouseService.getDataFrameWithoutColumnsName(fallback_sql)
                    if len(df_index_fallback) > 0:
                        df_index_fallback.columns = ['trade_date', 'close']
                        fallback_dict = {}
                        for _, fb_row in df_index_fallback.iterrows():
                            fallback_dict[str(fb_row['trade_date'])] = (
                                float(fb_row['close']) if pd.notna(fb_row['close']) else np.nan
                            )

                        for idx in df_opt_daily.index[missing_mask]:
                            if df_opt_daily.loc[idx, '_index_code'] == index_code:
                                td = str(df_opt_daily.loc[idx, 'trade_date'])
                                if td in fallback_dict:
                                    df_opt_daily.loc[idx, 'spot_price'] = fallback_dict[td]
                except Exception as e:
                    logger.warning(f"Fallback query failed for index {index_code}: {e}")

            logger.info(f"After fallback: spot_price available for "
                        f"{df_opt_daily['spot_price'].notna().sum()}/{len(df_opt_daily)} rows")

        # 清理临时列 + 统计
        df_opt_daily.drop(columns=['_index_code'], inplace=True)

        spot_count = df_opt_daily['spot_price'].notna().sum()
        total = len(df_opt_daily)
        if total > 0:
            logger.info(f"spot_price available for {spot_count}/{total} rows ({spot_count/total*100:.1f}%)")

        return df_opt_daily

    @staticmethod
    def _export_debug_excel(df_opt_daily):
        """Debug: 导出原始数据到 Excel"""
        df_opt_daily.to_excel(r"e:\tmp\df_opt_daily_debug.xlsx")
        logger.info(f"Debug Excel exported. Shape: {df_opt_daily.shape}")

    # ================================================================
    # Level 0: 数据获取 — 主入口
    # ================================================================
    def fetch_data(self, start_date=None, end_date=None,
                   call_put=None, exercise_type=None, ts_code_filter=None,
                   debug_export=False):
        """从 ClickHouse 获取期权日线 + 基础信息，并通过合约前缀匹配标的指数行情

        Args:
            start_date: 期权日线 & 指数行情起始日期 YYYYMMDD，默认90天前
            end_date: 期权日线 & 指数行情截止日期 YYYYMMDD，默认今天
            call_put: 行权方向 'C'(看涨) / 'P'(看跌)，None 表示不过滤
            exercise_type: 行权方式 '欧式' / '美式'，None 表示不过滤
            ts_code_filter: 合约代码过滤条件（LIKE 模式），如 'HO2612%'，None 表示不过滤
            debug_export: 是否导出 debug Excel，默认 False

        Returns:
            pd.DataFrame: 合并后的原始数据
        """
        logger.info("TuShareOptDailyIndicatorService.fetch_data: Fetching option daily data from ClickHouse")

        # 1. 参数默认值
        if end_date is None:
            end_date = date.today().strftime('%Y%m%d')
        if start_date is None:
            from datetime import timedelta
            start_date = (date.today() - timedelta(days=90)).strftime('%Y%m%d')

        # 2. 构建 WHERE + 拉取期权日线
        where_str = self._build_where_clause(
            call_put=call_put, exercise_type=exercise_type,
            ts_code_filter=ts_code_filter,
            start_date=start_date, end_date=end_date
        )
        df_opt_daily = self._fetch_option_daily_with_basic(where_str)

        if len(df_opt_daily) == 0:
            logger.warning("No data fetched, returning empty DataFrame")
            return df_opt_daily

        # 3. 拉取指数行情映射字典
        idx_dict = self._fetch_index_daily_dict(start_date, end_date)

        # 4. 数据清洗
        df_opt_daily = self._convert_types(df_opt_daily)
        df_opt_daily = self._enrich_from_ts_code(df_opt_daily)

        # 5. Spot 价格匹配（前缀映射 → dict 匹配 → 回退查询，三步合一）
        df_opt_daily = self._enrich_spot_prices(df_opt_daily, idx_dict, start_date, end_date)

        # 6. Debug 导出（受 debug_export 开关控制）
        if debug_export:
            self._export_debug_excel(df_opt_daily)

        logger.info(f"Data fetch completed. Shape: {df_opt_daily.shape}")
        return df_opt_daily

    # ================================================================
    # Level 1: 盘面硬指标 (Trading P&L)
    # ================================================================
    def _calc_trading_metrics(self, df_option):
        """计算盘面硬指标

        1. mtm_pnl_close: 日内浮动盈亏 (close - pre_close) * opt_multiplier
        2. mtm_pnl_settle: 结算盯市盈亏 (settle - pre_settle) * opt_multiplier
        3. point_change: 日内涨跌(指数点) close - pre_close
        4. pct_change: 日内涨跌幅(%)
        5. turnover_ratio: 换手率(近似) vol / oi
        6. avg_unit_price: 平均每手成交均价
        """
        logger.info("TuShareOptDailyIndicatorService._calc_trading_metrics: Calculating trading P&L metrics")

        df_option['mtm_pnl_close'] = (df_option['close'] - df_option['pre_close']) * df_option['opt_multiplier']
        df_option['mtm_pnl_settle'] = (df_option['settle'] - df_option['pre_settle']) * df_option['opt_multiplier']
        df_option['point_change'] = df_option['close'] - df_option['pre_close']
        df_option['pct_change'] = np.where(
            (df_option['pre_close'].notna()) & (df_option['pre_close'] != 0),
            (df_option['close'] / df_option['pre_close'] - 1) * 100,
            np.nan
        )

        # 换手率：vol / oi（持仓量可能为 0）
        df_option['turnover_ratio'] = np.where(
            (df_option['oi'].notna()) & (df_option['oi'] > 0),
            df_option['vol'] / df_option['oi'],
            np.nan
        )

        # 平均每手成交均价：amount(万元) * 10000 / vol(手) → 元/手
        df_option['avg_unit_price'] = np.where(
            (df_option['vol'].notna()) & (df_option['vol'] > 0),
            df_option['amount'] * 10000 / df_option['vol'],
            np.nan
        )

        logger.info(f"Trading metrics calculated. NaN counts:\n{df_option[['mtm_pnl_close','mtm_pnl_settle','point_change','pct_change','turnover_ratio','avg_unit_price']].isna().sum()}")
        return df_option

    # ================================================================
    # Level 2: 时间指标 (Time Metrics)
    # ================================================================
    def _calc_time_metrics(self, df_option):
        """计算时间指标

        1. days_to_maturity: 距离到期日历天数
        2. years_to_maturity_calendar: 日历/365
        3. years_to_maturity_trading: 交易日/252
        """
        logger.info("TuShareOptDailyIndicatorService._calc_time_metrics: Calculating time to maturity metrics")

        # 解析日期
        df_option['_trade_date_dt'] = pd.to_datetime(df_option['trade_date'], format='%Y%m%d', errors='coerce')
        df_option['_maturity_date_dt'] = pd.to_datetime(df_option['maturity_date'], format='%Y%m%d', errors='coerce')

        # 天数 = maturity - trade_date
        df_option['days_to_maturity'] = (df_option['_maturity_date_dt'] - df_option['_trade_date_dt']).dt.days
        df_option['days_to_maturity'] = df_option['days_to_maturity'].clip(lower=0)  # 已到期的设为0

        df_option['years_to_maturity_calendar'] = df_option['days_to_maturity'] / self.CALENDAR_DAYS_PER_YEAR
        df_option['years_to_maturity_trading'] = df_option['days_to_maturity'] / self.TRADING_DAYS_PER_YEAR

        # 清理临时列
        df_option.drop(columns=['_trade_date_dt', '_maturity_date_dt'], inplace=True)

        logger.info(f"Time metrics calculated. Days range: [{df_option['days_to_maturity'].min()}, {df_option['days_to_maturity'].max()}]")
        return df_option

    # ================================================================
    # Level 3: 价态 (Moneyness)
    # ================================================================
    def _calc_moneyness(self, df_option):
        """计算价态

        1. moneyness_status: ITM(实值)/ATM(平值)/OTM(虚值)
           - Call: S>K → ITM, S≈K → ATM, S<K → OTM
           - Put:  S<K → ITM, S≈K → ATM, S>K → OTM
        2. moneyness_log: ln(K/S) / sqrt(T) 【按用户指定公式】
        """
        logger.info("TuShareOptDailyIndicatorService._calc_moneyness: Calculating moneyness")

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

        df_option['moneyness_status'] = df_option.apply(_moneyness_status, axis=1)

        # 对数价态: ln(K/S) / sqrt(T)
        t = df_option['years_to_maturity_calendar']
        s = df_option['spot_price']
        k = df_option['exercise_price']
        df_option['moneyness_log'] = np.where(
            (s.notna()) & (k > 0) & (t > 0),
            np.log(k / s) / np.sqrt(t),
            np.nan
        )

        status_counts = df_option['moneyness_status'].value_counts()
        logger.info(f"Moneyness distribution:\n{status_counts}")
        return df_option

    # ================================================================
    # Level 4 & 5: 隐含波动率 & Greeks
    # ================================================================
    def _fetch_shibor_data(self, start_date, end_date):
        """从 ClickHouse 拉取 SHIBOR 日数据，构建 trade_date -> {tenor_col: rate/100} 查找表

        Args:
            start_date: 起始日期 YYYYMMDD
            end_date: 截止日期 YYYYMMDD

        Returns:
            dict: {trade_date_str: {'tenor_on': rate, 'tenor_1w': rate, ...}}
            所有利率均除以 100（SHIBOR 原值如 1.8 → 0.018）
        """
        logger.info("Fetching SHIBOR daily data for risk-free rate...")
        sql = f"""
        SELECT trade_date, tenor_on, tenor_1w, tenor_2w, tenor_1m, tenor_3m, tenor_6m, tenor_9m, tenor_1y
        FROM indexsysdb.df_tushare_shibor_daily
        WHERE trade_date >= '{start_date}'
          AND trade_date <= '{end_date}'
        ORDER BY trade_date
        """
        logger.info(f"SQL:\n{sql}")

        try:
            df_shibor = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        except Exception as e:
            logger.warning(f"Failed to fetch SHIBOR data: {e}, will fallback to DEFAULT_RISK_FREE_RATE")
            return None

        if len(df_shibor) == 0:
            logger.warning("No SHIBOR data found, will fallback to DEFAULT_RISK_FREE_RATE")
            return None

        df_shibor.columns = ['trade_date', 'tenor_on', 'tenor_1w', 'tenor_2w',
                             'tenor_1m', 'tenor_3m', 'tenor_6m', 'tenor_9m', 'tenor_1y']

        tenor_cols = ['tenor_on', 'tenor_1w', 'tenor_2w', 'tenor_1m',
                      'tenor_3m', 'tenor_6m', 'tenor_9m', 'tenor_1y']
        shibor_dict = {}
        for _, row in df_shibor.iterrows():
            td = str(row['trade_date'])
            # 统一为 YYYYMMDD 格式（兼容 YYYY-MM-DD / Timestamp 等）
            try:
                td = pd.to_datetime(td).strftime('%Y%m%d')
            except Exception:
                pass
            shibor_dict[td] = {}
            for col in tenor_cols:
                val = row[col]
                shibor_dict[td][col] = float(val) / 100.0 if pd.notna(val) else np.nan

        logger.info(f"SHIBOR data loaded: {len(shibor_dict)} trade_dates, "
                    f"range [{min(shibor_dict.keys())} ~ {max(shibor_dict.keys())}]")
        return shibor_dict

    @staticmethod
    def _match_shibor_rate(trade_date_str, days_to_maturity, shibor_dict):
        """根据交易日期和剩余到期天数，从 SHIBOR 查找表中匹配最近似期限利率

        Args:
            trade_date_str: 交易日字符串 YYYYMMDD
            days_to_maturity: 剩余到期日历天数
            shibor_dict: SHIBOR 查找表

        Returns:
            float or np.nan: 匹配到的年化利率（小数形式），如 0.018；数据缺失返回 np.nan
        """
        if shibor_dict is None:
            return np.nan

        # 统一 trade_date_str 为 YYYYMMDD 格式（兼容 YYYY-MM-DD / Timestamp 等）
        try:
            trade_date_str = pd.to_datetime(str(trade_date_str)).strftime('%Y%m%d')
        except Exception:
            trade_date_str = str(trade_date_str)

        if trade_date_str not in shibor_dict:
            return np.nan

        term_columns = {
            'tenor_on': 1,
            'tenor_1w': 7,
            'tenor_2w': 14,
            'tenor_1m': 30,
            'tenor_3m': 90,
            'tenor_6m': 180,
            'tenor_9m': 270,
            'tenor_1y': 365
        }

        best_term = min(term_columns.keys(), key=lambda x: abs(term_columns[x] - days_to_maturity))
        rate = shibor_dict[trade_date_str].get(best_term, np.nan)
        return rate if pd.notna(rate) else np.nan

    @staticmethod
    def _match_dividend_yield(trade_date_str, index_code, dividend_yield_dict):
        """根据交易日期和标的指数代码，从股息率查找表中匹配股息率

        Args:
            trade_date_str: 交易日字符串 YYYYMMDD
            index_code: 标的指数代码，如 '000300.SH'
            dividend_yield_dict: 股息率查找表 {(trade_date, index_code): yield}

        Returns:
            float or np.nan: 股息率（小数形式），如 0.026；数据缺失返回 np.nan
        """
        if dividend_yield_dict is None:
            return np.nan

        try:
            trade_date_str = pd.to_datetime(str(trade_date_str)).strftime('%Y%m%d')
        except Exception:
            trade_date_str = str(trade_date_str)

        key = (trade_date_str, index_code)
        return dividend_yield_dict.get(key, np.nan)

    def _fetch_dividend_yield_data(self, start_date, end_date):
        """从 ClickHouse 拉取指数日频基本指标，用 PE_TTM 估算股息率

        股息率估算公式: dividend_yield = payout_ratio / pe_ttm

        各指数的 payout_ratio 从 INDEX_DIVIDEND_PAYOUT_RATIO 获取，
        未配置的指数使用 DEFAULT_PAYOUT_RATIO。

        Args:
            start_date: 起始日期 YYYYMMDD
            end_date: 截止日期 YYYYMMDD

        Returns:
            dict or None: {(trade_date_str, index_code_str): dividend_yield_float}
            所有股息率为小数形式（如 0.026 代表 2.6%），
            若数据为空返回 None，调用方将 fallback 到 DEFAULT_DIVIDEND_YIELD
        """
        logger.info("Fetching index daily basic data for dividend yield estimation...")
        sql = f"""
        SELECT trade_date, ts_code, pe_ttm
        FROM indexsysdb.{self.TABLE_INDEX_DAILYBASIC}
        WHERE trade_date >= '{start_date}'
          AND trade_date <= '{end_date}'
        ORDER BY trade_date, ts_code
        """
        logger.info(f"SQL:\n{sql}")

        try:
            df_index_basic = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        except Exception as e:
            logger.warning(f"Failed to fetch index daily basic data: {e}, "
                           f"will fallback to DEFAULT_DIVIDEND_YIELD={self.DEFAULT_DIVIDEND_YIELD}")
            return None

        if len(df_index_basic) == 0:
            logger.warning("No index daily basic data found, "
                           f"will fallback to DEFAULT_DIVIDEND_YIELD={self.DEFAULT_DIVIDEND_YIELD}")
            return None

        df_index_basic.columns = ['trade_date', 'ts_code', 'pe_ttm']

        dividend_yield_dict = {}
        stat_total = 0
        stat_skip = 0
        for _, row in df_index_basic.iterrows():
            td = str(row['trade_date'])
            try:
                td = pd.to_datetime(td).strftime('%Y%m%d')
            except Exception:
                pass

            ts_code = str(row['ts_code'])
            pe_ttm = row['pe_ttm']

            if pd.isna(pe_ttm) or pe_ttm <= 0:
                stat_skip += 1
                continue

            # 获取该指数的分红比例
            payout_ratio = self.INDEX_DIVIDEND_PAYOUT_RATIO.get(
                ts_code, self.DEFAULT_PAYOUT_RATIO
            )
            dividend_yield = payout_ratio / pe_ttm

            key = (td, ts_code)
            dividend_yield_dict[key] = float(dividend_yield)
            stat_total += 1

        logger.info(f"Dividend yield data loaded: {stat_total} valid entries, "
                    f"{stat_skip} skipped (pe_ttm <= 0 or NaN), "
                    f"range [{min(dividend_yield_dict.keys())} ~ {max(dividend_yield_dict.keys())}]"
                    if dividend_yield_dict else "Dividend yield data empty")
        return dividend_yield_dict if dividend_yield_dict else None

    @staticmethod
    def _solve_iv_brentq(price, S, K, T, r, q, flag):
        """使用 scipy.brentq 求解隐含波动率（含股息率 q 的 BSM 模型）

        搜索区间: sigma ∈ [1e-6, 5.0]

        Args:
            price: 期权市场价格
            S: 标的现价
            K: 行权价
            T: 剩余到期时间（年）
            r: 无风险利率
            q: 股息率
            flag: 'c' 看涨 / 'p' 看跌
        """
        def _obj_call(sigma):
            if sigma <= 0:
                return 1e10
            d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)
            return S * math.exp(-q * T) * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2) - price

        def _obj_put(sigma):
            if sigma <= 0:
                return 1e10
            d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)
            return K * math.exp(-r * T) * norm.cdf(-d2) - S * math.exp(-q * T) * norm.cdf(-d1) - price

        try:
            obj = _obj_call if flag == 'c' else _obj_put
            iv = brentq(obj, 1e-6, 5.0, maxiter=200)
            return float(iv)
        except Exception:
            return np.nan

    def _calc_implied_vol_and_greeks(self, df_option, shibor_dict=None, dividend_yield_dict=None):
        """计算隐含波动率和 Greeks（含股息率 q 的完整 BSM 模型）

        IV 求解: scipy.brentq（已移除 py_vollib，因其不支持股息率 q）
        Greeks: OptionGreeks（传入真实股息率 y=q）
        无套利下界: Call: S*e^(-qT)-K*e^(-rT), Put: K*e^(-rT)-S*e^(-qT)
        d1 公式: (ln(S/K) + (r-q+0.5*sigma^2)*T) / (sigma*sqrt(T))

        依赖：spot_price, exercise_price, years_to_maturity_calendar

        Args:
            df_option: 期权数据 DataFrame
            shibor_dict: SHIBOR 查找表 {trade_date: {tenor_col: rate}}，
                         若为 None 则 fallback 到 DEFAULT_RISK_FREE_RATE
            dividend_yield_dict: 股息率查找表 {(trade_date, index_code): yield}，
                                 若为 None 则 fallback 到 DEFAULT_DIVIDEND_YIELD
        """
        logger.info("TuShareOptDailyIndicatorService._calc_implied_vol_and_greeks: Calculating implied volatility and Greeks")

        # 预填默认值（逐行将被 SHIBOR / 股息率覆盖）
        df_option['risk_free_rate'] = self.DEFAULT_RISK_FREE_RATE

        shibor_hit_count = 0
        shibor_miss_count = 0
        dividend_hit_count = 0
        dividend_miss_count = 0

        # ---- BSM 定价函数（含股息率 q） ----
        def bs_call_price(S, K, T, r, q, sigma):
            if T <= 0 or sigma <= 0:
                return np.nan
            d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)
            return S * math.exp(-q * T) * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)

        def bs_put_price(S, K, T, r, q, sigma):
            if T <= 0 or sigma <= 0:
                return np.nan
            d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)
            return K * math.exp(-r * T) * norm.cdf(-d2) - S * math.exp(-q * T) * norm.cdf(-d1)

        # ---- 对每行计算 ----
        implied_vol_list = []
        dividend_yield_list = []
        bs_price_list = []
        delta_list = []
        gamma_list = []
        vega_list = []
        theta_list = []
        rho_list = []
        d1_list = []
        d2_list = []
        nd1_list = []
        nd2_list = []

        skip_lower_bound_count = 0  # 因市价 < 欧式期权无套利下界跳过
        skip_param_count = 0        # 因参数缺失跳过
        iv_brentq_fail_count = 0     # brentq IV 求解失败

        for idx, row in df_option.iterrows():
            s = row.get('spot_price')
            k = row.get('exercise_price')
            t = row.get('years_to_maturity_calendar')
            market_price = row.get('close')
            cp = str(row.get('call_put', '')).upper()

            # ---- 逐行匹配 SHIBOR 无风险利率 r ----
            trade_date_str = str(row.get('trade_date', ''))
            days_mat = row.get('days_to_maturity', 0)
            r = self.DEFAULT_RISK_FREE_RATE  # fallback 默认值
            if shibor_dict is not None and pd.notna(days_mat):
                shibor_rate = self._match_shibor_rate(trade_date_str, days_mat, shibor_dict)
                if pd.notna(shibor_rate):
                    r = shibor_rate
                    shibor_hit_count += 1
                else:
                    shibor_miss_count += 1
            df_option.at[idx, 'risk_free_rate'] = r

            # ---- 逐行匹配股息率 q ----
            ts_code_val = str(row.get('ts_code', ''))
            # 从合约代码推导标的指数代码
            index_code_for_div = None
            for prefix, idx_code in self.CONTRACT_INDEX_MAP.items():
                if ts_code_val.startswith(prefix):
                    index_code_for_div = idx_code
                    break

            q = self.DEFAULT_DIVIDEND_YIELD  # fallback 默认股息率
            if dividend_yield_dict is not None and index_code_for_div is not None:
                dy = self._match_dividend_yield(trade_date_str, index_code_for_div, dividend_yield_dict)
                if pd.notna(dy) and dy > 0:
                    q = dy
                    dividend_hit_count += 1
                else:
                    dividend_miss_count += 1

            # 检查必要参数是否完整
            can_calc = (
                pd.notna(s) and pd.notna(k) and pd.notna(t) and pd.notna(market_price)
                and s > 0 and k > 0 and t > 0 and market_price > 0
            )

            if not can_calc:
                implied_vol_list.append(np.nan)
                dividend_yield_list.append(np.nan)
                bs_price_list.append(np.nan)
                delta_list.append(np.nan)
                gamma_list.append(np.nan)
                vega_list.append(np.nan)
                theta_list.append(np.nan)
                rho_list.append(np.nan)
                d1_list.append(np.nan)
                d2_list.append(np.nan)
                nd1_list.append(np.nan)
                nd2_list.append(np.nan)
                skip_param_count += 1
                continue

            # 记录本行的股息率 q
            dividend_yield_list.append(q)

            # ---- 隐含波动率（brentq + 含 q） ----
            iv = np.nan

            # 欧式期权无套利下界检查（含股息率 q）
            # Call:  max(0, S*e^(-qT) - K*e^(-rT))
            # Put:   max(0, K*e^(-rT) - S*e^(-qT))
            # 深度实值期权因流动性差/收盘时差可能出现市价低于下界，
            # 此时 BSM 方程无实数解（市场价 < 理论下界），IV 保留 NaN
            discount_r = math.exp(-r * t)
            discount_q = math.exp(-q * t)
            if cp == 'C':
                lower_bound = max(s * discount_q - k * discount_r, 0.0)
            else:
                lower_bound = max(k * discount_r - s * discount_q, 0.0)
            if lower_bound > 0 and market_price < lower_bound * 0.9999:
                iv = np.nan
                skip_lower_bound_count += 1
            else:
                flag = 'c' if cp == 'C' else 'p'
                iv = self._solve_iv_brentq(market_price, s, k, t, r, q, flag)
                if pd.notna(iv) and (iv <= 0 or iv > 3.0):
                    iv = np.nan
                if pd.isna(iv):
                    iv_brentq_fail_count += 1

            implied_vol_list.append(iv)

            # ---- BS 理论价（含 q） ----
            bs_price = np.nan
            if pd.notna(iv) and iv > 0:
                try:
                    if cp == 'C':
                        bs_price = bs_call_price(s, k, t, r, q, iv)
                    else:
                        bs_price = bs_put_price(s, k, t, r, q, iv)
                except Exception:
                    bs_price = np.nan
            bs_price_list.append(bs_price)

            # ---- d1, d2, N(d1), N(d2)（含 q: d1 = (ln(S/K) + (r-q+σ²/2)T) / (σ√T)） ----
            if pd.notna(iv) and iv > 0:
                try:
                    sigma_sqrt_t = iv * math.sqrt(t)
                    _d1 = (math.log(s / k) + (r - q + 0.5 * iv ** 2) * t) / sigma_sqrt_t
                    _d2 = _d1 - sigma_sqrt_t
                    d1_list.append(_d1)
                    d2_list.append(_d2)
                    nd1_list.append(norm.cdf(_d1))
                    nd2_list.append(norm.cdf(_d2))
                except Exception:
                    d1_list.append(np.nan)
                    d2_list.append(np.nan)
                    nd1_list.append(np.nan)
                    nd2_list.append(np.nan)
            else:
                d1_list.append(np.nan)
                d2_list.append(np.nan)
                nd1_list.append(np.nan)
                nd2_list.append(np.nan)

            # ---- Greeks（传入真实股息率 y=q） ----
            if pd.notna(iv) and iv > 0:
                try:
                    greeks = OptionGreeks.calculate_all_greeks(
                        S=s, K=k, T=t, r=r, y=q,
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

        df_option['implied_vol'] = implied_vol_list
        df_option['dividend_yield'] = dividend_yield_list
        df_option['bs_theoretical_price'] = bs_price_list
        df_option['d1'] = d1_list
        df_option['d2'] = d2_list
        df_option['nd1'] = nd1_list
        df_option['nd2'] = nd2_list
        df_option['delta'] = delta_list
        df_option['gamma'] = gamma_list
        df_option['vega'] = vega_list
        df_option['theta'] = theta_list
        df_option['rho'] = rho_list

        iv_count = df_option['implied_vol'].notna().sum()
        total = len(df_option)
        logger.info(f"Implied volatility calculated for {iv_count}/{total} rows")
        if skip_lower_bound_count > 0:
            logger.info(f"  Skipped {skip_lower_bound_count}/{total} rows: market_price < no-arbitrage lower bound "
                        f"(Call: S*e^(-qT)-K*e^(-rT), Put: K*e^(-rT)-S*e^(-qT)) — IV has no real solution")
        if iv_brentq_fail_count > 0:
            logger.info(f"  IV calculation failed for {iv_brentq_fail_count}/{total} rows (brentq exhausted)")
        if skip_param_count > 0:
            logger.info(f"  Skipped {skip_param_count}/{total} rows: missing S/K/T/price")
        greeks_count = df_option['delta'].notna().sum()
        logger.info(f"Greeks calculated for {greeks_count}/{total} rows")
        if shibor_dict is not None:
            logger.info(f"  SHIBOR risk-free rate: hit={shibor_hit_count}/{total}, "
                        f"miss={shibor_miss_count}/{total} (fallback to {self.DEFAULT_RISK_FREE_RATE})")
        if dividend_yield_dict is not None:
            logger.info(f"  Dividend yield: hit={dividend_hit_count}/{total}, "
                        f"miss={dividend_miss_count}/{total} (fallback to {self.DEFAULT_DIVIDEND_YIELD})")

        return df_option

    # ================================================================
    # 主流程
    # ================================================================
    def calculate_indicators(self, df_option, shibor_dict=None, dividend_yield_dict=None):
        """依次计算所有指标

        Args:
            df_option: 期权数据 DataFrame
            shibor_dict: SHIBOR 查找表，若为 None 则 fallback 到 DEFAULT_RISK_FREE_RATE
            dividend_yield_dict: 股息率查找表，若为 None 则 fallback 到 DEFAULT_DIVIDEND_YIELD
        """
        logger.info("TuShareOptDailyIndicatorService.calculate_indicators: Calculating all option indicators")

        if len(df_option) == 0:
            logger.warning("Empty DataFrame, skipping calculations")
            return df_option

        df_option = self._calc_trading_metrics(df_option)
        df_option = self._calc_time_metrics(df_option)
        df_option = self._calc_moneyness(df_option)
        df_option = self._calc_implied_vol_and_greeks(df_option, shibor_dict=shibor_dict,
                                                      dividend_yield_dict=dividend_yield_dict)

        return df_option

    def save_to_clickhouse(self, df_option, call_put=None, ts_code_filter=None):
        """写入 ClickHouse 目标表

        策略：按 trade_date + 可选过滤条件 增量删除后插入（保留历史数据）。
              传入 call_put / ts_code_filter 确保只删除同批数据，不会误删其他配置的历史记录。

        Args:
            df_option: 待写入的 DataFrame
            call_put: 行权方向 'C'/'P'，与 fetch 一致，用于缩小 DELETE 范围
            ts_code_filter: 合约代码过滤（LIKE），与 fetch 一致，用于缩小 DELETE 范围
        """
        logger.info(f"TuShareOptDailyIndicatorService.save_to_clickhouse: Saving {len(df_option)} rows to {self.TABLE_TARGET}")

        if len(df_option) == 0:
            logger.warning("Empty DataFrame, nothing to save")
            return

        # 确保只保存目标表字段
        available_cols = [c for c in self.TARGET_COLUMNS if c in df_option.columns]
        df_output = df_option[available_cols].copy()

        # 处理 NaN：IV/Greeks 保留 NaN（ClickHouse 存 NULL），其余字段填默认值
        greek_and_iv_cols = {'implied_vol', 'bs_theoretical_price',
                             'dividend_yield',
                             'delta', 'gamma', 'vega', 'theta', 'rho',
                             'd1', 'd2', 'nd1', 'nd2'}
        for col in df_output.columns:
            if col in ('trade_date', 'ts_code', 'call_put', 's_month', 'maturity_date', 'moneyness_status'):
                df_output[col] = df_output[col].fillna('').astype(str)
            elif col in ('days_to_maturity',):
                df_output[col] = pd.to_numeric(df_output[col], errors='coerce').fillna(0).astype(int)
            elif col in greek_and_iv_cols:
                # 保留 NaN 但显式替换为 None，确保 ClickHouse 存 NULL
                df_output[col] = pd.to_numeric(df_output[col], errors='coerce')
                df_output[col] = df_output[col].where(pd.notna(df_output[col]), None)
            else:
                df_output[col] = pd.to_numeric(df_output[col], errors='coerce').fillna(0.0)

        # 增量删除：仅删除本次涉及的 trade_date + 过滤条件匹配的数据
        trade_dates = df_output['trade_date'].unique().tolist()
        dates_str = "','".join(trade_dates)
        delete_conditions = [f"trade_date IN ('{dates_str}')"]

        if call_put:
            delete_conditions.append(f"call_put = '{call_put}'")
        if ts_code_filter:
            delete_conditions.append(f"ts_code LIKE '{ts_code_filter}'")

        del_sql = f"ALTER TABLE indexsysdb.{self.TABLE_TARGET} DELETE WHERE {' AND '.join(delete_conditions)}"
        logger.info(f"SQL:\n{del_sql}")
        ClickhouseService.execute_sql(del_sql)
        logger.info(f"Deleted data for trade_dates: {trade_dates}"
                    f"{', call_put=' + call_put if call_put else ''}"
                    f"{', ts_code like ' + ts_code_filter if ts_code_filter else ''}")

        # 写入
        ClickhouseService.save_dataframe_to_clickhouse(
            dataframe=df_output,
            table_name=self.TABLE_TARGET,
            database='indexsysdb'
        )
        logger.info(f"Saved {len(df_output)} rows to {self.TABLE_TARGET}")

    def run(self, start_date=None, end_date=None,
            call_put=None, exercise_type=None, ts_code_filter=None):
        """主流程：拉取 → 计算 → 保存

        Args:
            start_date: 期权日线 & 指数行情起始日期 YYYYMMDD
            end_date: 期权日线 & 指数行情截止日期 YYYYMMDD
            call_put: 行权方向 'C'/'P'，None 不过滤
            exercise_type: 行权方式 '欧式'/'美式'，None 不过滤
            ts_code_filter: 合约代码过滤（LIKE），如 'HO2612%'

        Returns:
            pd.DataFrame: 计算后的完整数据
        """
        logger.info("\n" + "=" * 80)
        logger.info("TuShareOptDailyIndicatorService.run: Starting option daily indicator generation")
        logger.info("=" * 80)

        # Step 1: 拉取数据
        logger.info("\nStep 1/5: Fetching option daily data from ClickHouse...")
        df_option = self.fetch_data(
            start_date=start_date, end_date=end_date,
            call_put=call_put, exercise_type=exercise_type, ts_code_filter=ts_code_filter
        )

        if len(df_option) == 0:
            logger.warning("No data fetched, aborting")
            return df_option

        # Step 2: 拉取 SHIBOR 数据作为无风险利率 r
        logger.info("\nStep 2/5: Fetching SHIBOR data for risk-free rate r...")
        shibor_dict = self._fetch_shibor_data(start_date, end_date)

        # Step 3: 拉取指数日频基本指标，估算股息率 q (= payout_ratio / pe_ttm)
        logger.info("\nStep 3/5: Fetching index daily basic data for dividend yield q (estimated from PE_TTM)...")
        dividend_yield_dict = self._fetch_dividend_yield_data(start_date, end_date)

        # Step 4: 计算指标（含 r 和 q）
        logger.info("\nStep 4/5: Calculating option indicators (BSM with r & q)...")
        df_option = self.calculate_indicators(df_option, shibor_dict=shibor_dict,
                                              dividend_yield_dict=dividend_yield_dict)

        # Step 5: 保存
        logger.info("\nStep 5/5: Saving to ClickHouse...")
        self.save_to_clickhouse(df_option, call_put=call_put, ts_code_filter=ts_code_filter)

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("Option daily indicator generation completed!")
        logger.info(f"   Total rows: {len(df_option)}, Total columns: {len(df_option.columns)}")
        iv_count = df_option['implied_vol'].notna().sum()
        logger.info(f"   Implied Vol calculated: {iv_count}/{len(df_option)}")
        logger.info("=" * 80)

        return df_option


# ================================================================
# 独立运行入口
# ================================================================
if __name__ == "__main__":
    from dataIntegrator import CommonParameters

    # 定义报告配置
    report_configs = [
        {
            "name": "HO2612看涨欧式期权",
            "start_date": "20260717",
            "end_date": "20260717",
            "call_put": "C",
            "exercise_type": "欧式",
            "ts_code_filter": "HO2612%",
        },
    ]

    service = TuShareOptDailyIndicatorAnalyst()

    for config in report_configs:
        name = config.pop("name")
        logger.info(f"\n{'='*80}")
        logger.info(f"Running report: {name}")
        logger.info(f"{'='*80}")
        try:
            df_result = service.run(**config)
            logger.info(f"[{name}] Done. Shape: {df_result.shape}")
        except Exception as e:
            logger.error(f"[{name}] Failed: {e}", exc_info=True)
        finally:
            config["name"] = name

"""
Put-Call Parity 实时监控服务

核心功能：
1. 从 tb_tushare_opt_daily_indicator 拉取 C/P 数据并按 (trade_date, exercise_price, maturity_date, underlying) 配对
2. 计算 PCP 偏差: ε = P - C - K*e^(-rT) + S*e^(-qT)
3. 滚动统计 (20日窗口): μ, σ, z-score
4. 股息噪声分解: 区分股息噪声 vs 真实套利
5. 分级告警: 2σ WARNING / 3σ ALERT

数据流：
  tb_tushare_opt_daily_indicator (日频, 含 BSM full fields)
    ↓ 配对 + PCP 计算 + 偏差分解
  tb_option_pcp_monitor

依赖：
  - spot_price, risk_free_rate, dividend_yield 由上游 Analyst 已写入 indicator 表
  - 合约前缀映射: HO→000016.SH, IO→000300.SH, MO→000852.SH（股指期权）
  - ETF 期权: ts_code 为 8 位数字、不含标的信息，需通过 df_tushare_opt_basic 的
    symbol 前 6 位反查真实标的（如 510050C2612M02600 → 510050.SH）
"""

import math
import re
import traceback

import numpy as np
import pandas as pd

from dataIntegrator import CommonLib
from dataIntegrator.common.ReportJobLogger import ReportJobLogger
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

logger = CommonLib.logger


class OptionPutCallParityMonitor:
    """Put-Call Parity 实时监控器"""

    # === 表名常量 ===
    TABLE_INDICATOR = 'tb_tushare_opt_daily_indicator'
    TABLE_TARGET = 'tb_option_pcp_monitor'
    # 合约基础信息快照（ts_code → symbol/name 反查，ETF 期权 ts_code 无语义）
    TABLE_BASIC = 'df_tushare_opt_basic'

    # === 合约前缀 → 标的指数代码映射 ===
    CONTRACT_INDEX_MAP = {
        'HO': '000016.SH',
        'IO': '000300.SH',
        'MO': '000852.SH',
    }

    # === SSE/SZSE ETF期权标的提取 ===
    # basic.symbol 前6位即标的ETF代码（如 510050C2609M03000 → 510050），
    # 5xxxxx → .SH, 1xxxxx → .SZ（与 OptionDailyIndicatorAnalyst 口径一致）
    ETF_SYMBOL_PATTERN = re.compile(r'^(\d{6})[CP]')

    # === 默认参数 ===
    LOOKBACK_DAYS = 20              # 滚动窗口天数
    ALERT_THRESHOLD = 2.0           # z-score WARNING 阈值
    STRONG_ALERT_THRESHOLD = 3.0    # z-score ALERT 阈值
    NOISE_RATIO = 0.70              # 股息贡献占比 > 此值归类为 DIVIDEND_NOISE
    Q_MIN_UNCERTAINTY = 0.005       # q 最低不确定度 0.5%
    MIN_VOLUME = 10                 # 最低成交量过滤

    # === 目标表字段顺序 ===
    TARGET_COLUMNS = [
        'trade_date', 'underlying_code', 'exercise_price', 'maturity_date', 'days_to_maturity',
        'call_settle', 'put_settle', 'spot_price', 'risk_free_rate', 'dividend_yield',
        'pcp_deviation', 'pcp_deviation_pct', 'pcp_theoretical_put',
        'rolling_mean', 'rolling_std', 'z_score',
        'dividend_q_std', 'dividend_contribution', 'residual_deviation',
        'alert_level', 'deviation_type',
        'call_ts_code', 'put_ts_code',
    ]

    def __init__(self, lookback_days=None, alert_threshold=None,
                 strong_alert_threshold=None, noise_ratio=None,
                 q_min_uncertainty=None, min_volume=None):
        if lookback_days is not None:
            self.LOOKBACK_DAYS = lookback_days
        if alert_threshold is not None:
            self.ALERT_THRESHOLD = alert_threshold
        if strong_alert_threshold is not None:
            self.STRONG_ALERT_THRESHOLD = strong_alert_threshold
        if noise_ratio is not None:
            self.NOISE_RATIO = noise_ratio
        if q_min_uncertainty is not None:
            self.Q_MIN_UNCERTAINTY = q_min_uncertainty
        if min_volume is not None:
            self.MIN_VOLUME = min_volume

        logger.info(f"OptionPutCallParityMonitor initialized: lookback={self.LOOKBACK_DAYS}d, "
                    f"alert_threshold={self.ALERT_THRESHOLD}σ, "
                    f"strong_alert_threshold={self.STRONG_ALERT_THRESHOLD}σ, "
                    f"noise_ratio={self.NOISE_RATIO}, "
                    f"q_min_uncertainty={self.Q_MIN_UNCERTAINTY}, "
                    f"min_volume={self.MIN_VOLUME}")

    # ================================================================
    # 工具方法：从 ts_code / symbol 推导 underlying_code
    # ================================================================
    @classmethod
    def _load_opt_basic_map(cls):
        """从 opt_basic 最新快照加载 ts_code → symbol 映射

        ETF 期权 ts_code 为 8 位数字（无语义规律），真实标的信息只在
        symbol 字段中（如 510050C2609M03000），必须通过本表反查。

        Returns:
            dict: {ts_code: symbol}，快照不可用时返回 {}（标的将退化为 UNKNOWN）
        """
        sql = f"""
        SELECT ts_code, argMax(symbol, trade_date) AS symbol
        FROM indexsysdb.{cls.TABLE_BASIC}
        GROUP BY ts_code
        """
        logger.info(f"SQL:\n{sql}")
        try:
            df_basic = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        except Exception as e:
            logger.warning(f"Failed to load opt_basic snapshot: {e}, "
                           f"underlying_code may degrade to UNKNOWN")
            return {}
        if df_basic is None or len(df_basic) == 0:
            logger.warning(f"{cls.TABLE_BASIC} snapshot is empty, "
                           f"underlying_code may degrade to UNKNOWN")
            return {}
        symbol_map = {str(row['ts_code']): str(row['symbol'] or '')
                      for _, row in df_basic.iterrows()}
        logger.info(f"Loaded ts_code->symbol map for {len(symbol_map)} contracts "
                    f"from {cls.TABLE_BASIC}")
        return symbol_map

    @classmethod
    def _get_underlying_code(cls, ts_code, symbol=''):
        """从合约代码/符号推导标的代码

        - 股指期权: 前缀映射 HO→000016.SH, IO→000300.SH, MO→000852.SH
        - ETF 期权: ts_code 为 8 位数字不含标的信息，用 opt_basic 的 symbol
          前 6 位推导（如 510050C2609M03000 → 510050.SH），
          沪市 ETF 以 5 开头、深市以 1 开头
        - 兜底返回 'UNKNOWN'（绝不返回 None，避免 groupby 丢弃 NaN 键的行）
        """
        ts_str = str(ts_code).strip().upper()
        for prefix, index_code in cls.CONTRACT_INDEX_MAP.items():
            if ts_str.startswith(prefix):
                return index_code
        symbol_str = str(symbol or '').strip()
        m = cls.ETF_SYMBOL_PATTERN.match(symbol_str)
        if m:
            fund_code = m.group(1)
            return fund_code + ('.SH' if fund_code.startswith('5') else '.SZ')
        return 'UNKNOWN'

    # ================================================================
    # Step 1: 拉取数据
    # ================================================================
    def _fetch_indicator_data(self, start_date, end_date, underlying_code=None):
        """从 indicator 表拉取 C 和 P 数据，用于配对

        Args:
            start_date: 起始日期 YYYYMMDD（含滚动窗口所需历史数据）
            end_date: 截止日期 YYYYMMDD
            underlying_code: 可选标的过滤（如 510050.SH / 000016.SH）

        Returns:
            tuple (df_call, df_put): 分别过滤后的 DataFrame
        """
        logger.info(f"Fetching indicator data from {start_date} to {end_date}...")

        sql = f"""
        SELECT trade_date, ts_code, call_put, exercise_price, maturity_date,
               settle, close, vol, spot_price, risk_free_rate, dividend_yield
        FROM indexsysdb.{self.TABLE_INDICATOR}
        WHERE trade_date >= '{start_date}'
          AND trade_date <= '{end_date}'
        ORDER BY trade_date, ts_code
        """

        logger.info(f"SQL:\n{sql}")
        df_raw = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        logger.info(f"Fetched {len(df_raw)} rows from indicator table")

        if len(df_raw) == 0:
            logger.warning("No data fetched, returning empty DataFrames")
            return pd.DataFrame(), pd.DataFrame()

        # 类型转换
        for col in ['exercise_price', 'settle', 'close', 'vol',
                     'spot_price', 'risk_free_rate', 'dividend_yield']:
            if col in df_raw.columns:
                df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce')

        for col in ['trade_date', 'ts_code', 'call_put', 'maturity_date']:
            if col in df_raw.columns:
                df_raw[col] = df_raw[col].astype(str)

        # 推导 underlying_code（ETF 期权 ts_code 无语义，需通过 opt_basic 的
        # symbol 前 6 位反查真实标的，与 OptionDailyIndicatorAnalyst 口径一致）
        opt_basic_map = self._load_opt_basic_map()
        df_raw['underlying_code'] = df_raw['ts_code'].apply(
            lambda tc: self._get_underlying_code(tc, opt_basic_map.get(str(tc), '')))

        # 可选标的过滤
        if underlying_code:
            before = len(df_raw)
            df_raw = df_raw[df_raw['underlying_code'] == underlying_code].copy()
            logger.info(f"Filtered by underlying_code={underlying_code}: "
                        f"{before} -> {len(df_raw)} rows")

        # 拆分 C / P
        df_call = df_raw[df_raw['call_put'].str.upper() == 'C'].copy()
        df_put = df_raw[df_raw['call_put'].str.upper() == 'P'].copy()

        logger.info(f"Split into Call: {len(df_call)} rows, Put: {len(df_put)} rows")
        return df_call, df_put

    # ================================================================
    # Step 2: 配对引擎
    # ================================================================
    @staticmethod
    def _pair_put_call(df_call, df_put):
        """一对一配对 C 和 P

        配对维度: trade_date + exercise_price + maturity_date + underlying_code

        Args:
            df_call: Call DataFrame
            df_put: Put DataFrame

        Returns:
            pd.DataFrame: 配对后的数据，每行一对 C/P
        """
        logger.info("Pairing Call and Put records...")

        pair_keys = ['trade_date', 'underlying_code', 'exercise_price', 'maturity_date']

        # 价格列优先使用 settle，fallback 到 close
        df_call['_price'] = df_call['settle'].fillna(df_call['close'])
        df_put['_price'] = df_put['settle'].fillna(df_put['close'])

        # 合并价格列
        call_cols = pair_keys + ['_price', 'vol', 'spot_price', 'risk_free_rate',
                                  'dividend_yield', 'ts_code']
        put_cols = pair_keys + ['_price', 'vol', 'ts_code']

        df_pair = df_call[call_cols].merge(
            df_put[put_cols],
            on=pair_keys,
            how='inner',
            suffixes=('_call', '_put')
        )

        logger.info(f"Paired {len(df_pair)} C/P pairs from "
                    f"{len(df_call)} Call and {len(df_put)} Put records")
        return df_pair

    # ================================================================
    # Step 3: 流动性过滤
    # ================================================================
    def _filter_liquidity(self, df_pair):
        """过滤流动性不足的配对

        条件: call_vol >= MIN_VOLUME AND put_vol >= MIN_VOLUME
               AND spot_price > 0 AND _price_call > 0 AND _price_put > 0
        """
        before = len(df_pair)

        mask = (
            (df_pair['vol_call'] >= self.MIN_VOLUME) &
            (df_pair['vol_put'] >= self.MIN_VOLUME) &
            (df_pair['spot_price'].notna()) & (df_pair['spot_price'] > 0) &
            (df_pair['_price_call'].notna()) & (df_pair['_price_call'] > 0) &
            (df_pair['_price_put'].notna()) & (df_pair['_price_put'] >= 0)
        )
        df_pair = df_pair[mask].copy()

        logger.info(f"Liquidity filter: {before} -> {len(df_pair)} pairs "
                    f"(vol >= {self.MIN_VOLUME})")
        return df_pair

    # ================================================================
    # Step 4: PCP 偏差计算
    # ================================================================
    @staticmethod
    def _calc_pcp_deviation(df_pair):
        """计算每条配对的 PCP 偏差

        ε = P_market - [C_market + K*e^(-rT) - S*e^(-qT)]
          = P_market - C_market - K*e^(-rT) + S*e^(-qT)

        理论 Put 价 = C_market + K*e^(-rT) - S*e^(-qT)
        """
        logger.info("Calculating PCP deviation...")

        S = df_pair['spot_price'].values
        K = df_pair['exercise_price'].values
        r = df_pair['risk_free_rate'].fillna(0.03).values
        q = df_pair['dividend_yield'].fillna(0.0).values
        C = df_pair['_price_call'].values
        P = df_pair['_price_put'].values

        # 计算 days_to_maturity
        trade_dates = pd.to_datetime(df_pair['trade_date'], format='%Y%m%d', errors='coerce')
        mat_dates = pd.to_datetime(df_pair['maturity_date'], format='%Y%m%d', errors='coerce')
        T_days = np.maximum((mat_dates - trade_dates).dt.days.values, 1)
        T = T_days / 365.0  # 年化

        # PV(K) 和 PV(S)
        pv_K = K * np.exp(-r * T)
        pv_S = S * np.exp(-q * T)

        # 理论 Put 价（从 Call 反推）
        pcp_theoretical_put = C + pv_K - pv_S

        # PCP 偏差
        pcp_deviation = P - pcp_theoretical_put

        # 百分比偏差
        pcp_deviation_pct = np.where(S > 0, pcp_deviation / S * 100, np.nan)

        df_pair['days_to_maturity'] = T_days.astype(int)
        df_pair['pcp_theoretical_put'] = pcp_theoretical_put
        df_pair['pcp_deviation'] = pcp_deviation
        df_pair['pcp_deviation_pct'] = pcp_deviation_pct

        # 使用 settle 价格（已为 _price）
        df_pair['call_settle'] = C
        df_pair['put_settle'] = P

        valid_count = (~np.isnan(pcp_deviation)).sum()
        logger.info(f"PCP deviation calculated for {valid_count}/{len(df_pair)} pairs")
        if valid_count > 0:
            logger.info(f"  ε stats: mean={np.nanmean(pcp_deviation):.4f}, "
                        f"std={np.nanstd(pcp_deviation):.4f}, "
                        f"min={np.nanmin(pcp_deviation):.4f}, max={np.nanmax(pcp_deviation):.4f}")

        return df_pair

    # ================================================================
    # Step 5: 滚动统计 & 偏差分解
    # ================================================================
    def _calc_rolling_stats_and_decompose(self, df_pair):
        """按配对组 (underlying_code, exercise_price, maturity_date) 计算滚动统计

        1. 20日滚动 μ, σ, z-score
        2. 每个 underlying 的股息率滚动标准差 σ_q
        3. 偏差分解: dividend_contribution = S * T * max(σ_q, Q_MIN_UNCERTAINTY)
        4. 分类: NORMAL / DIVIDEND_NOISE / REAL_ARBITRAGE / STRONG_ARBITRAGE
        """
        logger.info("Computing rolling statistics and deviation decomposition...")

        if len(df_pair) == 0:
            return df_pair

        # 确保按日期排序
        df_pair = df_pair.sort_values(['underlying_code', 'exercise_price', 'maturity_date', 'trade_date']).copy()

        group_key = ['underlying_code', 'exercise_price', 'maturity_date']

        # ---- 1. 计算每个 underlying 的股息率滚动标准差 ----
        # 按 (trade_date, underlying_code) 聚合 q 的标准差
        q_std_map = {}
        for uc, grp in df_pair.groupby('underlying_code'):
            q_series = grp.groupby('trade_date')['dividend_yield'].mean().sort_index()
            if len(q_series) >= 5:
                q_rolling = q_series.rolling(window=self.LOOKBACK_DAYS, min_periods=5).std()
                for td, val in q_rolling.items():
                    q_std_map[(td, uc)] = val if pd.notna(val) else self.Q_MIN_UNCERTAINTY

        # ---- 2. 逐组计算（按 grp_idx 索引对齐写回，不依赖行顺序） ----
        result_cols = ['rolling_mean', 'rolling_std', 'z_score',
                       'dividend_q_std', 'dividend_contribution',
                       'residual_deviation', 'alert_level', 'deviation_type']
        for col in result_cols:
            df_pair[col] = np.nan

        processed_rows = 0

        for _, grp in df_pair.groupby(group_key):
            grp_idx = grp.index
            # 按 trade_date 排序后计算滚动统计
            deviations = grp['pcp_deviation'].values

            roll_mean = pd.Series(deviations).rolling(
                window=self.LOOKBACK_DAYS, min_periods=5
            ).mean().values
            roll_std = pd.Series(deviations).rolling(
                window=self.LOOKBACK_DAYS, min_periods=5
            ).std().values

            # NaN 填充：min_periods 不足前的行
            for i in range(len(roll_mean)):
                if pd.isna(roll_std[i]) or roll_std[i] == 0:
                    roll_mean[i] = np.nanmean(deviations[:i+1]) if i >= 2 else 0.0
                    roll_std[i] = np.nanstd(deviations[:i+1]) if i >= 2 else np.nan

            z = np.where(
                pd.notna(roll_std) & (roll_std > 0),
                (deviations - roll_mean) / roll_std,
                np.nan
            )

            # ---- 3. 偏差分解（逐行） ----
            T_days = grp['days_to_maturity'].values.astype(float)
            T_years = T_days / 365.0
            S_vals = grp['spot_price'].values
            trade_dates_vals = grp['trade_date'].values
            uc_vals = grp['underlying_code'].values

            q_stds_grp = []
            div_contribs_grp = []
            residuals_grp = []
            alert_levels_grp = []
            deviation_types_grp = []

            for i in range(len(grp)):
                td = trade_dates_vals[i]
                uc = uc_vals[i]
                S_i = S_vals[i] if pd.notna(S_vals[i]) else 0
                T_i = T_years[i] if pd.notna(T_years[i]) and T_years[i] > 0 else 0

                # 股息率不确定度
                sigma_q = q_std_map.get((td, uc), self.Q_MIN_UNCERTAINTY)
                sigma_q = max(sigma_q, self.Q_MIN_UNCERTAINTY)
                q_stds_grp.append(sigma_q)

                # 股息贡献
                div_contrib = S_i * T_i * sigma_q
                div_contribs_grp.append(div_contrib)

                # 残差
                eps = deviations[i]
                residual = eps - np.sign(eps) * div_contrib if not np.isnan(eps) else np.nan
                residuals_grp.append(residual)

                # ---- 4. 分级告警 ----
                z_i = z[i]
                if pd.isna(z_i):
                    alert_levels_grp.append('NORMAL')
                    deviation_types_grp.append('NORMAL')
                elif abs(z_i) >= self.STRONG_ALERT_THRESHOLD:
                    alert_levels_grp.append('ALERT')
                    deviation_types_grp.append('STRONG_ARBITRAGE')
                elif abs(z_i) >= self.ALERT_THRESHOLD:
                    alert_levels_grp.append('WARNING')
                    # 判断是股息噪声还是真实套利
                    noise_contrib = div_contrib / (abs(eps) + 1e-10)
                    if noise_contrib >= self.NOISE_RATIO:
                        deviation_types_grp.append('DIVIDEND_NOISE')
                    else:
                        deviation_types_grp.append('REAL_ARBITRAGE')
                else:
                    alert_levels_grp.append('NORMAL')
                    deviation_types_grp.append('NORMAL')

            # 按组索引写回（即使 groupby 迭代顺序与行顺序不一致也能正确对齐）
            df_pair.loc[grp_idx, 'rolling_mean'] = roll_mean
            df_pair.loc[grp_idx, 'rolling_std'] = roll_std
            df_pair.loc[grp_idx, 'z_score'] = z
            df_pair.loc[grp_idx, 'dividend_q_std'] = q_stds_grp
            df_pair.loc[grp_idx, 'dividend_contribution'] = div_contribs_grp
            df_pair.loc[grp_idx, 'residual_deviation'] = residuals_grp
            df_pair.loc[grp_idx, 'alert_level'] = alert_levels_grp
            df_pair.loc[grp_idx, 'deviation_type'] = deviation_types_grp

            processed_rows += len(grp)

        if processed_rows != len(df_pair):
            raise ValueError(
                f"Rolling stats processed {processed_rows} rows but df has {len(df_pair)} "
                f"(groupby dropped rows with NaN group keys, check underlying_code)"
            )

        # 统计
        alert_counts = df_pair['alert_level'].value_counts()
        logger.info(f"Alert distribution: {alert_counts.to_dict()}")
        type_counts = df_pair['deviation_type'].value_counts()
        logger.info(f"Deviation type distribution: {type_counts.to_dict()}")

        return df_pair

    # ================================================================
    # Step 6: 保存到 ClickHouse
    # ================================================================
    def save_to_clickhouse(self, df_pair):
        """写入 ClickHouse 目标表

        策略：按本次涉及的 trade_date 增量删除后插入
        """
        logger.info(f"Saving {len(df_pair)} PCP records to {self.TABLE_TARGET}")

        if len(df_pair) == 0:
            logger.warning("Empty DataFrame, nothing to save")
            return

        # 准备输出字段
        df_output = pd.DataFrame()
        df_output['trade_date'] = df_pair['trade_date'].astype(str)
        df_output['underlying_code'] = df_pair['underlying_code'].fillna('').astype(str)
        df_output['exercise_price'] = pd.to_numeric(df_pair['exercise_price'], errors='coerce')
        df_output['maturity_date'] = df_pair['maturity_date'].astype(str)
        df_output['days_to_maturity'] = pd.to_numeric(df_pair['days_to_maturity'], errors='coerce').fillna(0).astype(int)

        df_output['call_settle'] = pd.to_numeric(df_pair['call_settle'], errors='coerce').fillna(0.0)
        df_output['put_settle'] = pd.to_numeric(df_pair['put_settle'], errors='coerce').fillna(0.0)
        df_output['spot_price'] = pd.to_numeric(df_pair['spot_price'], errors='coerce').fillna(0.0)
        df_output['risk_free_rate'] = pd.to_numeric(df_pair['risk_free_rate'], errors='coerce').fillna(0.03)
        df_output['dividend_yield'] = pd.to_numeric(df_pair['dividend_yield'], errors='coerce').fillna(0.0)

        # PCP 偏差字段：保留 NaN → ClickHouse NULL
        for col in ['pcp_deviation', 'pcp_deviation_pct', 'pcp_theoretical_put',
                     'rolling_mean', 'rolling_std', 'z_score',
                     'dividend_q_std', 'dividend_contribution', 'residual_deviation']:
            df_output[col] = pd.to_numeric(df_pair[col], errors='coerce')
            df_output[col] = df_output[col].where(pd.notna(df_output[col]), None)

        df_output['alert_level'] = df_pair['alert_level'].fillna('NORMAL').astype(str)
        df_output['deviation_type'] = df_pair['deviation_type'].fillna('NORMAL').astype(str)
        df_output['call_ts_code'] = df_pair['ts_code_call'].fillna('').astype(str)
        df_output['put_ts_code'] = df_pair['ts_code_put'].fillna('').astype(str)

        # 增量删除
        trade_dates = df_output['trade_date'].unique().tolist()
        dates_str = "','".join(trade_dates)
        del_sql = f"ALTER TABLE indexsysdb.{self.TABLE_TARGET} DELETE WHERE trade_date IN ('{dates_str}')"
        logger.info(f"Deleting existing data: {del_sql}")
        ClickhouseService.execute_sql(del_sql)
        logger.info(f"Deleted data for trade_dates: {trade_dates}")

        # 写入
        ClickhouseService.save_dataframe_to_clickhouse(
            dataframe=df_output,
            table_name=self.TABLE_TARGET,
            database='indexsysdb'
        )
        logger.info(f"Saved {len(df_output)} rows to {self.TABLE_TARGET}")

    # ================================================================
    # 主流程
    # ================================================================
    def run(self, trade_date=None, start_date=None, end_date=None, underlying_code=None):
        """主流程：拉取 → 配对 → PCP 计算 → 滚动统计 → 偏差分解 → 保存

        Args:
            trade_date: 单日监控 YYYYMMDD（优先级最高）
            start_date: 自定义起始日期 YYYYMMDD
            end_date: 自定义截止日期 YYYYMMDD
            underlying_code: 可选标的过滤（如 510050.SH / 000016.SH），空=全部

        Returns:
            pd.DataFrame: PCP 监控结果
        """
        logger.info("\n" + "=" * 80)
        logger.info("OptionPutCallParityMonitor.run: Starting PCP monitoring")
        logger.info("=" * 80)

        # 确定日期范围
        if trade_date:
            end_date = trade_date
            # end_date 当天需要 LOOKBACK_DAYS 天历史数据做滚动统计
            import datetime
            end_dt = datetime.datetime.strptime(end_date, '%Y%m%d')
            start_dt = end_dt - datetime.timedelta(days=self.LOOKBACK_DAYS + 5)
            start_date = start_dt.strftime('%Y%m%d')
            logger.info(f"Mode: single day monitoring {trade_date}, "
                        f"fetch history [{start_date}, {end_date}] for rolling stats")
        elif start_date and end_date:
            logger.info(f"Mode: batch monitoring [{start_date}, {end_date}]")
        else:
            import datetime
            end_date = datetime.date.today().strftime('%Y%m%d')
            end_dt = datetime.datetime.strptime(end_date, '%Y%m%d')
            start_dt = end_dt - datetime.timedelta(days=self.LOOKBACK_DAYS + 5)
            start_date = start_dt.strftime('%Y%m%d')
            logger.info(f"Mode: default (today), fetch history [{start_date}, {end_date}]")

        # 报表任务日志（与 BondYieldComparator 相同的 ReportJobLogger 机制）
        job_logger = ReportJobLogger()
        job_logger.start_job('OptionPutCallParityMonitor', 'OptionPCPMonitor',
                             params={'start_date': start_date,
                                     'end_date': end_date,
                                     'trade_date': trade_date,
                                     'underlying_code': underlying_code})

        try:
            # Step 1: 拉取数据
            logger.info("\nStep 1/4: Fetching indicator data...")
            df_call, df_put = self._fetch_indicator_data(start_date, end_date,
                                                         underlying_code=underlying_code)

            if len(df_call) == 0 or len(df_put) == 0:
                logger.warning("Insufficient Call/Put data, aborting")
                job_logger.end_job_success(records_processed=0)
                return pd.DataFrame()

            # Step 2: 配对
            logger.info("\nStep 2/4: Pairing Call and Put...")
            df_pair = self._pair_put_call(df_call, df_put)

            if len(df_pair) == 0:
                logger.warning("No C/P pairs found, aborting")
                job_logger.end_job_success(records_processed=0)
                return pd.DataFrame()

            # Step 3: 流动性过滤
            logger.info("\nStep 3/4: Filtering by liquidity...")
            df_pair = self._filter_liquidity(df_pair)

            if len(df_pair) == 0:
                logger.warning("No pairs pass liquidity filter, aborting")
                job_logger.end_job_success(records_processed=0)
                return pd.DataFrame()

            # Step 4: PCP 偏差计算 + 滚动统计 + 偏差分解
            logger.info("\nStep 4/4: PCP deviation, rolling stats, decomposition...")
            df_pair = self._calc_pcp_deviation(df_pair)
            df_pair = self._calc_rolling_stats_and_decompose(df_pair)

            # 保存
            logger.info("\nSaving to ClickHouse...")
            self.save_to_clickhouse(df_pair)

            # 如果指定了 trade_date，只返回当天的结果
            if trade_date:
                df_result = df_pair[df_pair['trade_date'] == trade_date].copy()
            else:
                df_result = df_pair.copy()

            # Summary
            logger.info("\n" + "=" * 80)
            logger.info("PCP monitoring completed!")
            logger.info(f"   Total pairs: {len(df_result)}")
            alert_df = df_result[df_result['alert_level'] != 'NORMAL']
            if len(alert_df) > 0:
                logger.warning(f"   ⚠️  Alerts: {len(alert_df)} pairs with deviation exceeding threshold")
                for _, row in alert_df.iterrows():
                    logger.warning(f"       {row['trade_date']} | {row['underlying_code']} | "
                                   f"K={row['exercise_price']:.0f} | "
                                   f"T={row['maturity_date']} | "
                                   f"ε={row['pcp_deviation']:.2f} | "
                                   f"z={row['z_score']:.2f}σ | "
                                   f"type={row['deviation_type']}")
            logger.info("=" * 80)

            job_logger.end_job_success(records_processed=len(df_result))
            return df_result

        except Exception as e:
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise


# ================================================================
# 独立运行入口
# ================================================================
if __name__ == "__main__":
    monitor = OptionPutCallParityMonitor(lookback_days=20)
    df_result = monitor.run(trade_date='20260717')
    print(f"\nResult shape: {df_result.shape}")
    if len(df_result) > 0:
        print(df_result[['trade_date', 'underlying_code', 'exercise_price',
                          'pcp_deviation', 'z_score', 'alert_level', 'deviation_type']].head(20))

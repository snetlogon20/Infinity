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
  - 合约前缀映射: HO→000016.SH, IO→000300.SH, MO→000852.SH
"""

import math
import numpy as np
import pandas as pd

from dataIntegrator import CommonLib
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

logger = CommonLib.logger


class OptionPutCallParityMonitor:
    """Put-Call Parity 实时监控器"""

    # === 表名常量 ===
    TABLE_INDICATOR = 'tb_tushare_opt_daily_indicator'
    TABLE_TARGET = 'tb_option_pcp_monitor'

    # === 合约前缀 → 标的指数代码映射 ===
    CONTRACT_INDEX_MAP = {
        'HO': '000016.SH',
        'IO': '000300.SH',
        'MO': '000852.SH',
    }

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
    # 工具方法：从 ts_code 推导 underlying_code
    # ================================================================
    @classmethod
    def _get_underlying_code(cls, ts_code):
        """从合约代码推导标的指数代码"""
        ts_str = str(ts_code).strip()
        for prefix, index_code in cls.CONTRACT_INDEX_MAP.items():
            if ts_str.startswith(prefix):
                return index_code
        return None

    # ================================================================
    # Step 1: 拉取数据
    # ================================================================
    def _fetch_indicator_data(self, start_date, end_date):
        """从 indicator 表拉取 C 和 P 数据，用于配对

        Args:
            start_date: 起始日期 YYYYMMDD（含滚动窗口所需历史数据）
            end_date: 截止日期 YYYYMMDD

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

        # 推导 underlying_code
        df_raw['underlying_code'] = df_raw['ts_code'].apply(self._get_underlying_code)

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

        rolling_means = []
        rolling_stds = []
        z_scores = []
        q_stds = []
        dividend_contributions = []
        residual_deviations = []
        alert_levels = []
        deviation_types = []

        # ---- 1. 计算每个 underlying 的股息率滚动标准差 ----
        # 按 (trade_date, underlying_code) 聚合 q 的标准差
        q_std_map = {}
        for uc, grp in df_pair.groupby('underlying_code'):
            q_series = grp.groupby('trade_date')['dividend_yield'].mean().sort_index()
            if len(q_series) >= 5:
                q_rolling = q_series.rolling(window=self.LOOKBACK_DAYS, min_periods=5).std()
                for td, val in q_rolling.items():
                    q_std_map[(td, uc)] = val if pd.notna(val) else self.Q_MIN_UNCERTAINTY

        # ---- 2. 逐组计算 ----
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

            # ---- 3. 偏差分解 ----
            T_days = grp['days_to_maturity'].values.astype(float)
            T_years = T_days / 365.0
            S_vals = grp['spot_price'].values
            trade_dates_vals = grp['trade_date'].values
            uc_vals = grp['underlying_code'].values

            for i in range(len(grp)):
                td = trade_dates_vals[i]
                uc = uc_vals[i]
                S_i = S_vals[i] if pd.notna(S_vals[i]) else 0
                T_i = T_years[i] if pd.notna(T_years[i]) and T_years[i] > 0 else 0

                # 股息率不确定度
                sigma_q = q_std_map.get((td, uc), self.Q_MIN_UNCERTAINTY)
                sigma_q = max(sigma_q, self.Q_MIN_UNCERTAINTY)
                q_stds.append(sigma_q)

                # 股息贡献
                div_contrib = S_i * T_i * sigma_q
                dividend_contributions.append(div_contrib)

                # 残差
                eps = deviations[i]
                residual = eps - np.sign(eps) * div_contrib if not np.isnan(eps) else np.nan
                residual_deviations.append(residual)

                # ---- 4. 分级告警 ----
                z_i = z[i]
                if pd.isna(z_i):
                    alert_levels.append('NORMAL')
                    deviation_types.append('NORMAL')
                elif abs(z_i) >= self.STRONG_ALERT_THRESHOLD:
                    alert_levels.append('ALERT')
                    deviation_types.append('STRONG_ARBITRAGE')
                elif abs(z_i) >= self.ALERT_THRESHOLD:
                    alert_levels.append('WARNING')
                    # 判断是股息噪声还是真实套利
                    noise_contrib = div_contrib / (abs(eps) + 1e-10)
                    if noise_contrib >= self.NOISE_RATIO:
                        deviation_types.append('DIVIDEND_NOISE')
                    else:
                        deviation_types.append('REAL_ARBITRAGE')
                else:
                    alert_levels.append('NORMAL')
                    deviation_types.append('NORMAL')

            rolling_means.extend(roll_mean.tolist())
            rolling_stds.extend(roll_std.tolist())
            z_scores.extend(z.tolist())

        df_pair['rolling_mean'] = rolling_means
        df_pair['rolling_std'] = rolling_stds
        df_pair['z_score'] = z_scores
        df_pair['dividend_q_std'] = q_stds
        df_pair['dividend_contribution'] = dividend_contributions
        df_pair['residual_deviation'] = residual_deviations
        df_pair['alert_level'] = alert_levels
        df_pair['deviation_type'] = deviation_types

        # 统计
        alert_counts = pd.Series(alert_levels).value_counts()
        logger.info(f"Alert distribution: {alert_counts.to_dict()}")
        type_counts = pd.Series(deviation_types).value_counts()
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
    def run(self, trade_date=None, start_date=None, end_date=None):
        """主流程：拉取 → 配对 → PCP 计算 → 滚动统计 → 偏差分解 → 保存

        Args:
            trade_date: 单日监控 YYYYMMDD（优先级最高）
            start_date: 自定义起始日期 YYYYMMDD
            end_date: 自定义截止日期 YYYYMMDD

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

        # Step 1: 拉取数据
        logger.info("\nStep 1/4: Fetching indicator data...")
        df_call, df_put = self._fetch_indicator_data(start_date, end_date)

        if len(df_call) == 0 or len(df_put) == 0:
            logger.warning("Insufficient Call/Put data, aborting")
            return pd.DataFrame()

        # Step 2: 配对
        logger.info("\nStep 2/4: Pairing Call and Put...")
        df_pair = self._pair_put_call(df_call, df_put)

        if len(df_pair) == 0:
            logger.warning("No C/P pairs found, aborting")
            return pd.DataFrame()

        # Step 3: 流动性过滤
        logger.info("\nStep 3/4: Filtering by liquidity...")
        df_pair = self._filter_liquidity(df_pair)

        if len(df_pair) == 0:
            logger.warning("No pairs pass liquidity filter, aborting")
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

        return df_result


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

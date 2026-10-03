r"""
期权策略分析 抽象基类（模板方法模式）

定位：
    统一 "拉取 → 清洗 → IV分位 → 策略盈亏 → 情景盈亏 → 信号 → 落库" 流程，
    子类只需实现策略专属钩子（calc_strategy_pnl / calc_scenario_pnl / _assign_trade_signals）。

数据源：
    - tb_tushare_opt_daily_indicator : BS定价/Greeks/价态等通用指标
    - df_tushare_opt_basic           : symbol/name/exchange 反查（ETF期权 ts_code 为8位数字）

落库（每策略一张专表 + 联合视图）：
    - tb_option_trading_strategy_protective_put : strategy_type='PROTECTIVE_PUT'
    - tb_option_trading_strategy_covered_call   : strategy_type='COVERED_CALL'
    - vw_option_trading_strategy_union          : 两表公共字段 UNION 视图（跨策略查询入口）
    每行记录 analysis_time / analysis_params / analysis_version 审计字段。
    子类必须覆写 TABLE_TARGET 指明自己的专表，未覆写运行时报错。

后续策略（collar 等）接入步骤：
    1. 建专表 tb_option_trading_strategy_<strategy>（含审计字段）
    2. 继承 OptionStrategyBase，填 STRATEGY_TYPE / TABLE_TARGET / TARGET_COLUMNS / DEFAULT_SCENARIOS
    3. 实现三个钩子方法
    4. 在 OptionStrategyFactory 注册
    5. （可选）把公共字段补进 vw_option_trading_strategy_union（注意 UNION ALL 按位置对齐，需重建视图）
"""

import json
from datetime import datetime

import numpy as np
import pandas as pd

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

logger = CommonLib.logger


class OptionStrategyBase:
    """期权策略分析器 抽象基类"""

    # === 表名常量 ===
    TABLE_INDICATOR = 'tb_tushare_opt_daily_indicator'
    TABLE_BASIC = 'df_tushare_opt_basic'
    # 目标专表：子类必须覆写（每策略一张表），未覆写在 save_to_clickhouse 中报错
    TABLE_TARGET = None

    # === 子类必须覆盖的钩子常量 ===
    STRATEGY_TYPE = 'BASE'          # 策略类型标识（落库分区键）
    TARGET_COLUMNS = []             # 目标表字段顺序（与建表 SQL 一致）
    DEFAULT_SCENARIOS = []          # 多情景系数
    ANALYSIS_VERSION = 'v1'         # 算法版本

    # === IV 分位窗口 ===
    IV_RANK_WINDOW = 60
    IV_RANK_MIN_OBS = 5

    # ================================================================
    # Step 1: 数据拉取（通用，symbol_filter 方式）
    # ================================================================
    def fetch_data(self, start_date, end_date, call_put='P',
                   symbol_filter=None, exercise_type=None):
        """从 indicator 表拉取数据，join basic 表补充 symbol/name/exchange

        Args:
            start_date: 起始日期 YYYYMMDD
            end_date: 截止日期 YYYYMMDD
            call_put: 'C' 看涨 / 'P' 看跌
            symbol_filter: 标的+方向过滤（LIKE），如 '510050P2612%'（华夏上证50ETF 2612认沽）
                           目标表无 symbol 列，通过 df_tushare_opt_basic 反查合约清单
            exercise_type: 行权方式 '欧式'/'美式'，None 不过滤
        """
        logger.info("=" * 80)
        logger.info(f"Fetching option data: [{start_date}, {end_date}], "
                    f"call_put={call_put}, symbol_filter={symbol_filter}, exercise_type={exercise_type}")

        where_clauses = [
            f"ind.trade_date >= '{start_date}'",
            f"ind.trade_date <= '{end_date}'",
        ]
        if call_put:
            where_clauses.append(f"ind.call_put = '{call_put}'")
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
            ind.trade_date,
            ind.ts_code,
            ind.call_put,
            ind.exercise_price,
            ind.opt_multiplier,
            ind.s_month,
            ind.maturity_date,
            ind.days_to_maturity,
            ind.years_to_maturity_calendar,
            ind.moneyness_status,
            ind.moneyness_log,
            ind.spot_price,
            ind.risk_free_rate,
            ind.dividend_yield,
            ind.open,
            ind.high,
            ind.low,
            ind.close,
            ind.settle,
            ind.pre_close,
            ind.vol,
            ind.amount,
            ind.oi,
            ind.implied_vol,
            ind.bs_theoretical_price,
            ind.delta,
            ind.gamma,
            ind.theta,
            ind.vega,
            ind.rho,
            b.symbol       AS symbol,
            b.name         AS opt_name,
            b.exchange     AS opt_exchange,
            b.exercise_type
        FROM indexsysdb.{self.TABLE_INDICATOR} ind
        LEFT JOIN (
            SELECT ts_code,
                   any(symbol)        AS symbol,
                   any(name)          AS name,
                   any(exchange)      AS exchange,
                   any(exercise_type) AS exercise_type
            FROM indexsysdb.{self.TABLE_BASIC}
            GROUP BY ts_code
        ) b ON ind.ts_code = b.ts_code
        WHERE {where_str}
        ORDER BY ind.trade_date, ind.exercise_price
        """

        logger.info(f"SQL:\n{sql}")
        df_raw = ClickhouseService.getDataFrameWithoutColumnsName(sql)

        if len(df_raw) == 0:
            logger.warning("No data fetched, returning empty DataFrame")
            return pd.DataFrame()

        logger.info(f"Fetched {len(df_raw)} rows, {len(df_raw.columns)} columns")

        numeric_cols = [
            'exercise_price', 'opt_multiplier',
            'close', 'settle', 'pre_close', 'open', 'high', 'low', 'vol', 'amount', 'oi',
            'days_to_maturity', 'years_to_maturity_calendar', 'moneyness_log',
            'spot_price', 'risk_free_rate', 'dividend_yield',
            'implied_vol', 'bs_theoretical_price',
            'delta', 'gamma', 'theta', 'vega', 'rho',
        ]
        for col in numeric_cols:
            if col in df_raw.columns:
                df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce')

        str_cols = ['trade_date', 'ts_code', 'call_put', 's_month', 'maturity_date',
                    'moneyness_status', 'symbol', 'opt_name', 'opt_exchange', 'exercise_type']
        for col in str_cols:
            if col in df_raw.columns:
                df_raw[col] = df_raw[col].fillna('').astype(str)

        return df_raw

    # ================================================================
    # Step 2: 数据清洗（通用）
    # ================================================================
    def _clean_and_filter(self, df):
        """数据清洗：过滤无效行（spot/close/K 缺失或非正）"""
        before = len(df)

        mask = (
            df['spot_price'].notna() & (df['spot_price'] > 0) &
            df['close'].notna() & (df['close'] > 0) &
            df['exercise_price'].notna() & (df['exercise_price'] > 0)
        )
        df = df[mask].copy()

        logger.info(f"Data cleaning: {before} -> {len(df)} rows "
                    f"(removed {before - len(df)} rows with missing S/K/premium)")
        return df

    # ================================================================
    # Step 3: IV 分位数（通用，"保险贵不贵"）
    # ================================================================
    def calc_iv_rank(self, df, end_date):
        """计算当日 IV 在该合约近 N=60 日 IV 历史中的分位数 (0~1)

        说明：
            - 该指标为通用指标，covered call / collar 均可复用；
              暂在策略层现算，后续稳定后可物化回 tb_tushare_opt_daily_indicator。
            - 历史窗口取 end_date 前最近 60 条（LIMIT BY），对窗口内逐日计算
              截至当日的经验分位（样本不足 IV_RANK_MIN_OBS 条时置 NaN）。
        """
        logger.info(f"Calculating IV rank (window={self.IV_RANK_WINDOW})...")

        if len(df) == 0:
            df['iv_rank'] = np.nan
            return df

        ts_codes = df['ts_code'].unique().tolist()
        codes_str = ",".join(f"'{c}'" for c in ts_codes)

        sql = f"""
        SELECT ts_code, trade_date, implied_vol
        FROM indexsysdb.{self.TABLE_INDICATOR}
        WHERE trade_date <= '{end_date}'
          AND ts_code IN ({codes_str})
          AND implied_vol > 0
        ORDER BY ts_code ASC, trade_date ASC
        LIMIT {self.IV_RANK_WINDOW} BY ts_code
        """
        df_hist = ClickhouseService.getDataFrameWithoutColumnsName(sql)

        if len(df_hist) == 0:
            logger.warning("No IV history fetched, iv_rank set to NaN")
            df['iv_rank'] = np.nan
            return df

        df_hist['implied_vol'] = pd.to_numeric(df_hist['implied_vol'], errors='coerce')
        # ts_code -> 按日期升序的 (trade_date, iv) 列表
        hist_map = {}
        for ts_code, group in df_hist.groupby('ts_code'):
            g = group.sort_values('trade_date')
            hist_map[ts_code] = list(zip(g['trade_date'].astype(str),
                                         g['implied_vol'].values))

        def _rank_of(ts_code, trade_date, iv_now):
            series = hist_map.get(ts_code)
            if not series or pd.isna(iv_now):
                return np.nan
            # 截至当日（含当日）的观测
            obs = [iv for d, iv in series if d <= trade_date]
            n = len(obs)
            if n < self.IV_RANK_MIN_OBS:
                return np.nan
            return float(np.sum(np.array(obs) <= iv_now) / n)

        df['iv_rank'] = [
            _rank_of(tc, td, iv)
            for tc, td, iv in zip(df['ts_code'], df['trade_date'], df['implied_vol'])
        ]

        valid = pd.Series(df['iv_rank']).notna().sum()
        logger.info(f"IV rank calculated for {valid}/{len(df)} rows")
        return df

    # ================================================================
    # Step 4/5/6: 策略钩子（子类必须实现）
    # ================================================================
    def calc_strategy_pnl(self, df):
        """策略核心盈亏计算 — 子类实现"""
        raise NotImplementedError

    def calc_scenario_pnl(self, df, scenarios=None):
        """多情景盈亏计算 — 子类实现"""
        raise NotImplementedError

    def _assign_trade_signals(self, df):
        """交易信号分配 — 子类实现"""
        raise NotImplementedError

    # ================================================================
    # Step 7: 落库（通用，含审计字段与增量删除）
    # ================================================================
    def save_to_clickhouse(self, df, config):
        """写入策略专表（含分析时间戳与参数）

        增量删除范围：strategy_type + trade_date + call_put + symbol LIKE，
        确保只删除同批数据，不误删其他策略/其他配置的历史记录。
        """
        if not self.TABLE_TARGET:
            raise NotImplementedError(
                f"{type(self).__name__} 未覆写 TABLE_TARGET，"
                f"请为策略 '{self.STRATEGY_TYPE}' 指定专表 "
                f"(如 tb_option_trading_strategy_<strategy>)"
            )

        logger.info(f"Saving {len(df)} rows to {self.TABLE_TARGET} "
                    f"(strategy_type={self.STRATEGY_TYPE})")

        if len(df) == 0:
            logger.warning("Empty DataFrame, nothing to save")
            return

        # 审计字段（每轮分析统一填写）
        df = df.copy()
        df['strategy_type'] = self.STRATEGY_TYPE
        df['analysis_time'] = datetime.now().replace(microsecond=0)
        df['analysis_params'] = json.dumps(config, ensure_ascii=False, default=str)
        df['analysis_version'] = self.ANALYSIS_VERSION

        available_cols = [c for c in self.TARGET_COLUMNS if c in df.columns]
        df_output = df[available_cols].copy()

        str_cols = {'strategy_type', 'analysis_params', 'analysis_version',
                    'trade_date', 'ts_code', 'symbol', 'opt_name', 'opt_exchange',
                    'call_put', 's_month', 'maturity_date',
                    'moneyness_status', 'price_bias', 'trade_signal', 'signal_reason',
                    # 价差组合的卖出腿字符串字段（Bull Call Spread 等）
                    'ts_code_short', 'symbol_short', 'opt_name_short', 'price_bias_short'}
        for col in df_output.columns:
            if col == 'analysis_time':
                continue  # datetime 对象直接写入 DateTime 列
            if col in str_cols:
                df_output[col] = df_output[col].fillna('').astype(str)
            elif col in ('days_to_maturity',):
                df_output[col] = pd.to_numeric(df_output[col], errors='coerce').fillna(0).astype(int)
            else:
                df_output[col] = pd.to_numeric(df_output[col], errors='coerce')
                df_output[col] = df_output[col].where(pd.notna(df_output[col]), None)

        # 增量删除
        symbol_filter = config.get('symbol_filter')
        call_put = config.get('call_put')
        trade_dates = df_output['trade_date'].unique().tolist()
        dates_str = "','".join(trade_dates)

        delete_conditions = [
            f"strategy_type = '{self.STRATEGY_TYPE}'",
            f"trade_date IN ('{dates_str}')",
        ]
        if call_put:
            delete_conditions.append(f"call_put = '{call_put}'")
        if symbol_filter:
            delete_conditions.append(f"symbol LIKE '{symbol_filter}'")

        del_sql = (f"ALTER TABLE indexsysdb.{self.TABLE_TARGET} DELETE WHERE "
                   f"{' AND '.join(delete_conditions)}")
        logger.info(f"SQL:\n{del_sql}")
        ClickhouseService.execute_sql(del_sql)
        logger.info(f"Deleted data for trade_dates: {len(trade_dates)} dates, "
                    f"strategy_type={self.STRATEGY_TYPE}, symbol_filter={symbol_filter}")

        # 写入
        ClickhouseService.save_dataframe_to_clickhouse(
            dataframe=df_output,
            table_name=self.TABLE_TARGET,
            database='indexsysdb'
        )
        logger.info(f"Saved {len(df_output)} rows to {self.TABLE_TARGET} "
                    f"(analysis_time={df['analysis_time'].iloc[0]})")

    # ================================================================
    # 主流程（模板方法，子类不要覆盖）
    # ================================================================
    def run(self, config):
        """主流程：拉取 → 清洗 → IV分位 → 策略盈亏 → 情景盈亏 → 信号 → 落库

        Args:
            config: dict with keys:
                - name: str, 报告/批次名称
                - start_date: str YYYYMMDD
                - end_date: str YYYYMMDD
                - call_put: str 'C'/'P'
                - symbol_filter: str LIKE pattern, 如 '510050P2612%'
                - exercise_type: str '欧式'/'美式' (optional)

        Returns:
            pd.DataFrame or None: 计算结果（已含审计字段），空数据返回 None
        """
        name = config.get('name', 'Unknown')
        start_date = config.get('start_date')
        end_date = config.get('end_date')
        call_put = config.get('call_put')
        symbol_filter = config.get('symbol_filter')
        exercise_type = config.get('exercise_type')

        logger.info("\n" + "=" * 80)
        logger.info(f"{self.__class__.__name__}.run: {name}")
        logger.info(f"  Period: [{start_date}, {end_date}], call_put={call_put}, "
                    f"symbol_filter={symbol_filter}, exercise_type={exercise_type}")
        logger.info(f"  Strategy: {self.STRATEGY_TYPE}, version={self.ANALYSIS_VERSION}")
        logger.info("=" * 80)

        # Step 1: 拉取数据
        logger.info("\nStep 1/6: Fetching data...")
        df = self.fetch_data(
            start_date=start_date, end_date=end_date,
            call_put=call_put, symbol_filter=symbol_filter,
            exercise_type=exercise_type,
        )
        if len(df) == 0:
            logger.warning(f"[{name}] No data found, skipping")
            return None

        # Step 2: 清洗
        logger.info("\nStep 2/6: Cleaning and filtering...")
        df = self._clean_and_filter(df)
        if len(df) == 0:
            logger.warning(f"[{name}] No valid data after cleaning, skipping")
            return None

        # Step 3: IV 分位（保险贵不贵，信号输入）
        logger.info("\nStep 3/6: Calculating IV rank...")
        df = self.calc_iv_rank(df, end_date)

        # Step 4: 策略核心盈亏（子类钩子）
        logger.info("\nStep 4/6: Calculating strategy P&L...")
        df = self.calc_strategy_pnl(df)

        # Step 5: 多情景盈亏（子类钩子）
        logger.info("\nStep 5/6: Calculating scenario P&L...")
        df = self.calc_scenario_pnl(df)

        # Step 6: 交易信号 + 落库（含审计字段）
        logger.info("\nStep 6/6: Assigning trade signals and saving to ClickHouse...")
        df = self._assign_trade_signals(df)
        self.save_to_clickhouse(df, config)

        logger.info(f"\n{'='*80}")
        logger.info(f"[{name}] Analysis done: {len(df)} rows -> {self.TABLE_TARGET}")
        logger.info(f"{'='*80}")

        return df

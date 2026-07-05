"""
BaseAssetAnalyzer — Abstract base class and AnalyzerFactory.

Factory Pattern:
    New trading instruments only need to:
    1. Subclass BaseAssetAnalyzer
    2. Implement get_sql() and get_asset_name()
    3. Register via AnalyzerFactory.register()
"""

from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from typing import Tuple, List, Optional
import logging

logger = logging.getLogger(__name__)


class BaseAssetAnalyzer(ABC):
    """
    Abstract base for all asset analyzers.

    Subclasses must implement:
        - get_sql(symbol, start_date, end_date) -> str
        - get_asset_name() -> str
    """

    def __init__(
        self,
        symbol: str,
        start_date: str,
        end_date: Optional[str] = None,
        analysis_column: str = 'pct_change',
        analysis_column_label: str = '涨跌幅',
        limit_date: int = 600,
        next_n_working_days: int = 5,
        simulate_params: dict = None,
    ):
        self.symbol = symbol
        self.start_date = self._normalize_date(start_date)

        if end_date is None:
            from dataIntegrator.common.CommonParameters import CommonParameters
            self.end_date = self._normalize_date(CommonParameters.today)
        else:
            self.end_date = self._normalize_date(end_date)

        self.analysis_column = analysis_column
        self.analysis_column_label = analysis_column_label
        self.limit_date = limit_date
        self.next_n_working_days = next_n_working_days

        default_params = {
            'init_value': 'pct_change',
            'analysis_column': 'pct_change',
            't': 0.01,
            'times': next_n_working_days,
            'series': 5000,
            'alpha': 0.05,
            'distribution_type': 'normal',
            'segma_calculation_type': 'normal',
        }
        if simulate_params:
            default_params.update(simulate_params)
        self.simulate_params = default_params

        # Data holders
        self.raw_data: Optional[pd.DataFrame] = None
        self.calendar_data: Optional[pd.DataFrame] = None

        logger.info(
            f"BaseAssetAnalyzer initialized: symbol={self.symbol}, "
            f"start_date={self.start_date}, end_date={self.end_date}, "
            f"analysis_column={self.analysis_column}, limit_date={self.limit_date}, "
            f"next_n_working_days={self.next_n_working_days}"
        )
        logger.info(
            f"Simulate params: distribution_type={self.simulate_params['distribution_type']}, "
            f"segma_calculation_type={self.simulate_params['segma_calculation_type']}, "
            f"series={self.simulate_params['series']}, alpha={self.simulate_params['alpha']}, "
            f"times={self.simulate_params['times']}"
        )

    # ------------------------------------------------------------------
    #  Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_date(date_str: str) -> str:
        """Ensure date string is in yyyy-mm-dd format."""
        date_str = str(date_str).strip().replace('-', '')
        if len(date_str) == 8:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return date_str  # already formatted

    # ------------------------------------------------------------------
    #  Abstract methods – subclasses MUST implement
    # ------------------------------------------------------------------

    @abstractmethod
    def get_sql(self, symbol: str, start_date: str, end_date: str) -> str:
        """Return the ClickHouse SQL query for this asset."""
        ...

    @abstractmethod
    def get_asset_name(self) -> str:
        """Return a human-readable asset name for titles/labels."""
        ...

    # ------------------------------------------------------------------
    #  Data fetching
    # ------------------------------------------------------------------

    def fetch_data(self) -> pd.DataFrame:
        """Fetch raw data from ClickHouse."""
        sql = self.get_sql(self.symbol, self.start_date, self.end_date)
        logger.info(f"Fetching data for {self.get_asset_name()} ({self.symbol})")
        logger.debug(f"SQL: {sql}")
        from dataIntegrator.analysisService.InquiryManager import InquiryManager
        self.raw_data = InquiryManager.get_sql_dataset(sql)

        if self.raw_data is None or self.raw_data.empty:
            raise ValueError(f"No data returned for {self.symbol} from {self.start_date} to {self.end_date}")

        # Ensure trade_date column
        if 'trade_date' not in self.raw_data.columns and 'date' in self.raw_data.columns:
            self.raw_data['trade_date'] = self.raw_data['date']

        # Ensure numeric columns
        for col in ['open', 'close', 'low', 'high', 'pct_change']:
            if col in self.raw_data.columns:
                self.raw_data[col] = pd.to_numeric(self.raw_data[col], errors='coerce')

        self.raw_data = self.raw_data.sort_values('trade_date').reset_index(drop=True)
        logger.info(f"Fetched {len(self.raw_data)} rows for {self.symbol}, "
                     f"columns={list(self.raw_data.columns)}, "
                     f"pct_change range=[{self.raw_data['pct_change'].min():.4f}, {self.raw_data['pct_change'].max():.4f}]")
        return self.raw_data

    def fetch_calendar(self) -> pd.DataFrame:
        """Fetch calendar data from ClickHouse."""
        sql = """
            SELECT trade_date, trade_year, trade_month, trade_day, day_of_week, quarter, calendar_date
            FROM indexsysdb.df_sys_calendar
            ORDER BY trade_date
        """
        logger.info("Fetching calendar data")
        from dataIntegrator.analysisService.InquiryManager import InquiryManager
        self.calendar_data = InquiryManager.get_sql_dataset(sql)
        logger.info(f"Fetched {len(self.calendar_data)} calendar rows")
        return self.calendar_data

    def get_future_working_days(self, last_date: str, n: int) -> List[str]:
        """
        Get the next `n` working days from the calendar after `last_date`.

        Args:
            last_date: reference date (string YYYYMMDD or YYYY-MM-DD).
            n: number of future working days to retrieve.

        Returns:
            List of trade_date strings.
        """
        if self.calendar_data is None:
            self.fetch_calendar()

        # Normalize date format
        last_date_clean = last_date.replace('-', '')
        cal = self.calendar_data.copy()
        cal['trade_date_clean'] = cal['trade_date'].astype(str).str.replace('-', '')

        cal_sorted = cal.sort_values('trade_date_clean')
        future = cal_sorted[cal_sorted['trade_date_clean'] > last_date_clean]
        future_dates = future['trade_date'].head(n).tolist()
        logger.info(f"Future working days: last_data_date={last_date}, requested={n}, "
                     f"found={len(future_dates)}, dates={future_dates}")
        return future_dates

    # ------------------------------------------------------------------
    #  Analysis helpers
    # ------------------------------------------------------------------

    def get_analysis_returns(self) -> pd.Series:
        """Extract the analysis column as a returns series."""
        if self.raw_data is None:
            self.fetch_data()
        col = self.simulate_params.get('analysis_column', 'pct_change')
        if col in self.raw_data.columns:
            return self.raw_data[col].copy()
        raise ValueError(f"Column '{col}' not found in raw data. Available columns: {list(self.raw_data.columns)}")

    # ------------------------------------------------------------------
    #  Run analysis
    # ------------------------------------------------------------------

    def run(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Execute the full analysis pipeline.

        Returns:
            (original_analysis_df, prediction_df, final_merged_df)
        """
        from .MonteCarloEngine import MonteCarloEngine
        from .RiskMetrics import RiskMetrics
        from .ResultAggregator import ResultAggregator

        logger.info("=" * 50)
        logger.info(f"Starting Monte Carlo analysis for {self.get_asset_name()}")
        logger.info("=" * 50)

        if self.raw_data is None:
            self.fetch_data()

        df = self.raw_data.copy()
        returns = self.get_analysis_returns().dropna()
        analysis_col = self.simulate_params.get('analysis_column', 'pct_change')
        limit = self.limit_date
        n_series = self.simulate_params.get('series', 5000)
        alpha = self.simulate_params.get('alpha', 0.05)
        next_n = self.simulate_params.get('times', self.next_n_working_days)

        n_data = len(df)
        returns_array = returns.values

        logger.info(f"Data: {n_data} rows, returns: {len(returns_array)} valid, "
                     f"limit={limit}, alpha={alpha}, next_n={next_n}")

        # --- Sigma series ---
        logger.info("Stage 1/4: Computing sigma series (normal/GARCH/EGARCH)...")
        normal_segma = np.full(n_data, np.nan)
        garch_segma = np.full(n_data, np.nan)
        egarch_segma = np.full(n_data, np.nan)

        # Normal sigma: rolling window std (use available history when limit > n_data)
        for i in range(1, n_data):
            window = returns_array[max(0, i - limit):i]
            if len(window) > 1:
                normal_segma[i] = float(np.std(window, ddof=1))
        logger.info(f"  Normal sigma computed for {n_data - 1} rows (window up to {limit})")

        # GARCH / EGARCH sigma: one-shot fit for conditional vol series
        # Fit on the full returns to get daily conditional vols
        for sigma_type, storage in [('garch', garch_segma), ('egarch', egarch_segma)]:
            try:
                params_copy = self.simulate_params.copy()
                params_copy['segma_calculation_type'] = sigma_type
                engine = MonteCarloEngine(pd.Series(returns_array), params_copy)
                cond_vol = engine.get_conditional_volatility()
                if cond_vol is not None:
                    # cond_vol is daily; align it to df indices
                    min_len = min(len(cond_vol), n_data)
                    storage[n_data - min_len:] = cond_vol[-min_len:]
                    logger.info(f"  {sigma_type.upper()} sigma computed: {min_len} values, "
                                 f"range=[{np.nanmin(storage):.6f}, {np.nanmax(storage):.6f}]")
                else:
                    logger.info(f"  {sigma_type.upper()} sigma: skipped (using normal only)")
            except Exception as e:
                logger.warning(f"  Could not compute {sigma_type} sigma: {e}")

        # --- Risk stats (rolling window simulation) ---
        logger.info(f"Stage 2/4: Computing risk stats (rolling window, {n_data} iterations)...")
        risk_stats_list = []
        nan_entry = {
            'var_lower_bound': np.nan, 'var_upper_bound': np.nan,
            'es_lower_bound': np.nan, 'es_upper_bound': np.nan,
            'average': np.nan, 'median_value': np.nan,
        }
        for i in range(n_data):
            if i < 2:
                # Need at least 2 historical points for meaningful stats
                risk_stats_list.append(nan_entry.copy())
                continue

            window_returns = returns_array[max(0, i - limit):i]
            if len(window_returns) < 5:
                risk_stats_list.append(nan_entry.copy())
                continue

            try:
                engine = MonteCarloEngine(pd.Series(window_returns), self.simulate_params)
                engine.fit_distribution()
                engine.calculate_sigma()
                simulated = engine.simulate_single_step()
                stats = RiskMetrics.calculate_all_stats(simulated, alpha)
                risk_stats_list.append(stats)
            except Exception as e:
                logger.debug(f"    skip i={i} (window={len(window_returns)}): {e}")
                risk_stats_list.append(nan_entry.copy())

            if (i - 1) % 100 == 0:
                logger.info(f"  Risk stats progress: {i}/{n_data}")

        logger.info(f"  Risk stats completed: {len(risk_stats_list)} entries, "
                     f"{sum(1 for s in risk_stats_list if not np.isnan(s.get('average', np.nan)))} valid")

        # --- EMAs ---
        logger.info("Stage 3/4: Computing EMAs (5/10/20/60)...")
        ema_df = ResultAggregator.compute_ema(returns)

        # --- Build original analysis ---
        original_df = ResultAggregator.build_original_analysis(
            raw_data=df,
            risk_stats_list=risk_stats_list,
            ema_df=ema_df,
            normal_segma=normal_segma,
            garch_segma=garch_segma,
            egarch_segma=egarch_segma,
            step_num=0,
            analysis_column=analysis_col,
        )
        logger.info(f"  Original analysis built: {len(original_df)} rows, {len(original_df.columns)} columns")

        # --- Future prediction ---
        logger.info(f"Stage 4/4: Predicting next {next_n} working days...")
        last_date = str(df['trade_date'].iloc[-1])
        future_dates = self.get_future_working_days(last_date, next_n)

        # Use the most recent limit_date returns for prediction.
        # Daily returns are independently drawn from the fitted distribution,
        # not accumulated as a GBM path.
        engine_pred = MonteCarloEngine(pd.Series(returns_array[-limit:]), self.simulate_params)
        engine_pred.fit_distribution()
        engine_pred.calculate_sigma()
        simulated_pred = engine_pred.simulate_single_step()

        predict_values = np.random.choice(simulated_pred, size=next_n, replace=True).tolist()

        prediction_df = ResultAggregator.build_prediction_results(
            dates=future_dates,
            predict_values=predict_values,
            analysis_column=analysis_col,
        )
        logger.info(f"  Predictions: {predict_values}")

        # --- Merge ---
        final_df = ResultAggregator.merge_results(original_df, prediction_df)
        logger.info(f"  Final merged: {len(final_df)} rows")
        logger.info("=" * 50)
        logger.info(f"Analysis complete: original={len(original_df)}, "
                     f"prediction={len(prediction_df)}, final={len(final_df)}")
        logger.info("=" * 50)

        return original_df, prediction_df, final_df


class AnalyzerFactory:
    """Factory for creating asset analyzers by symbol."""

    _registry: dict = {}

    @classmethod
    def register(cls, symbol: str, analyzer_class: type):
        """Register an analyzer class for a given symbol."""
        if not issubclass(analyzer_class, BaseAssetAnalyzer):
            raise TypeError(f"{analyzer_class.__name__} must be a subclass of BaseAssetAnalyzer")
        cls._registry[symbol.upper()] = analyzer_class
        logger.info(f"Registered analyzer {analyzer_class.__name__} for symbol '{symbol.upper()}'")

    @classmethod
    def create(cls, symbol: str, **kwargs) -> BaseAssetAnalyzer:
        """
        Create an analyzer instance for the given symbol.

        Args:
            symbol: trading symbol (e.g. 'GC', 'SI', 'CL').
            **kwargs: forwarded to the analyzer constructor.

        Returns:
            BaseAssetAnalyzer instance.
        """
        sym = symbol.upper()
        if sym not in cls._registry:
            raise KeyError(f"No analyzer registered for symbol '{sym}'. Registered: {list(cls._registry.keys())}")
        analyzer_class = cls._registry[sym]
        return analyzer_class(symbol=symbol, **kwargs)

    @classmethod
    def list_registered(cls) -> list:
        """Return list of registered symbol strings."""
        return list(cls._registry.keys())

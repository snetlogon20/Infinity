"""
ResultAggregator — builds final DataFrames from raw data, risk stats, and predictions.
"""

import pandas as pd
import numpy as np
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class ResultAggregator:
    """Combine raw analysis, EMA calculations, and prediction results into unified DataFrames."""

    @staticmethod
    def compute_ema(series: pd.Series, periods: List[int] = None) -> pd.DataFrame:
        """
        Compute EMAs for given periods.

        Args:
            series: time series of returns.
            periods: list of EMA window sizes (default: [5, 10, 20, 60]).

        Returns:
            DataFrame with columns pct_change_ema_{period}.
        """
        if periods is None:
            periods = [5, 10, 20, 60]
        ema_df = pd.DataFrame(index=series.index)
        for p in periods:
            ema_df[f'pct_change_ema_{p}'] = series.ewm(span=p, adjust=False).mean()
        return ema_df

    @classmethod
    def build_original_analysis(
        cls,
        raw_data: pd.DataFrame,
        risk_stats_list: list,
        ema_df: pd.DataFrame,
        normal_segma: np.ndarray,
        garch_segma: np.ndarray,
        egarch_segma: np.ndarray,
        step_num: int = 0,
        analysis_column: str = 'pct_change',
    ) -> pd.DataFrame:
        """
        Build the "original data analysis" DataFrame.

        Columns:
            trade_date, open, close, low, high, pct_change,
            analysis_column, var_lower_bound, var_upper_bound,
            es_lower_bound, es_upper_bound, average, median_value,
            step_num, pct_change_ema_5, pct_change_ema_10,
            pct_change_ema_20, pct_change_ema_60,
            normal_segma, garch_segma, egarch_segma
        """
        df = raw_data.copy()

        # Ensure expected columns exist
        for col in ['trade_date', 'open', 'close', 'low', 'high', 'pct_change']:
            if col not in df.columns:
                if col == 'trade_date':
                    if 'date' in df.columns:
                        df['trade_date'] = df['date']
                    else:
                        df['trade_date'] = df.index.astype(str)
                else:
                    df[col] = np.nan

        # analysis_column — use the specified analysis column from parameters
        df['analysis_column'] = df.get(analysis_column, df.get('pct_change', np.nan))

        # Risk stats – pad if shorter than df
        n_data = len(df)
        n_stats = len(risk_stats_list) if risk_stats_list else 0

        for key in ['var_lower_bound', 'var_upper_bound', 'es_lower_bound',
                     'es_upper_bound', 'average', 'median_value']:
            if n_stats > 0:
                vals = [s.get(key, np.nan) for s in risk_stats_list]
                # Pad at the beginning (early rows may not have enough history)
                padded = [np.nan] * (n_data - n_stats) + vals
                df[key] = padded[:n_data]
            else:
                df[key] = np.nan

        df['step_num'] = step_num

        # EMAs – align index to df
        for col in ema_df.columns:
            df[col] = ema_df[col].reindex(df.index).values

        # Sigma columns
        def _pad_sigma(arr, n):
            if arr is not None and len(arr) > 0:
                padded = [np.nan] * max(0, n - len(arr)) + list(arr)
                return padded[:n]
            return [np.nan] * n

        df['normal_segma'] = _pad_sigma(normal_segma, n_data)
        df['garch_segma'] = _pad_sigma(garch_segma, n_data)
        df['egarch_segma'] = _pad_sigma(egarch_segma, n_data)

        # Ensure column order
        col_order = [
            'trade_date', 'open', 'close', 'low', 'high', 'pct_change',
            'analysis_column', 'var_lower_bound', 'var_upper_bound',
            'es_lower_bound', 'es_upper_bound', 'average', 'median_value',
            'step_num', 'pct_change_ema_5', 'pct_change_ema_10',
            'pct_change_ema_20', 'pct_change_ema_60',
            'normal_segma', 'garch_segma', 'egarch_segma',
        ]
        existing_cols = [c for c in col_order if c in df.columns]
        return df[existing_cols]

    @staticmethod
    def build_prediction_results(
        dates: List[str],
        predict_p10: List[float],
        predict_p50: List[float],
        predict_p90: List[float],
        predict_p05: Optional[List[float]] = None,
        predict_p01: Optional[List[float]] = None,
        analysis_column: str = 'pct_change',
    ) -> pd.DataFrame:
        """
        Build prediction results DataFrame.

        Columns: trade_date, analysis_column, predict_p10, predict_p50, predict_p90, predict_p05, predict_p01
        """
        result = pd.DataFrame({
            'trade_date': dates,
            'analysis_column': analysis_column,
            'predict_p10': predict_p10,
            'predict_p50': predict_p50,
            'predict_p90': predict_p90,
        })
        if predict_p05 is not None:
            result['predict_p05'] = predict_p05
        if predict_p01 is not None:
            result['predict_p01'] = predict_p01
        return result

    @staticmethod
    def merge_results(original_df: pd.DataFrame, prediction_df: pd.DataFrame) -> pd.DataFrame:
        """
        Merge original analysis and prediction results, sorted by trade_date.

        For prediction rows, only trade_date, analysis_column, predict_p10/p50/p90, step_num are populated.
        """
        # Add step_num to prediction
        if 'step_num' not in prediction_df.columns:
            prediction_df = prediction_df.copy()
            prediction_df['step_num'] = range(1, len(prediction_df) + 1)

        # Ensure trade_date is string type in both
        original_df = original_df.copy()
        prediction_df = prediction_df.copy()
        original_df['trade_date'] = original_df['trade_date'].astype(str)
        prediction_df['trade_date'] = prediction_df['trade_date'].astype(str)

        merged = pd.concat([original_df, prediction_df], axis=0, ignore_index=True, sort=False)
        merged = merged.sort_values('trade_date').reset_index(drop=True)
        return merged

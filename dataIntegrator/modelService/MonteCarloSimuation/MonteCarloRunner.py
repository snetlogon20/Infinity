"""
MonteCarloRunner — main orchestrator.
Entry point for running Monte Carlo analysis and backtesting.
"""

import os
import pandas as pd
import numpy as np
from typing import Tuple, Optional
import logging
from datetime import datetime

from dataIntegrator.common.CommonParameters import CommonParameters

# 报表输出目录，基于 CommonParameters.reportPath，避免操作系统切换硬编码
_MONTE_CARLO_REPORT_DIR = os.path.join(CommonParameters.reportPath, 'MonteCarloSimulationAnalysis')

logger = logging.getLogger(__name__)


class MonteCarloRunner:
    """
    Main orchestrator for Monte Carlo simulation-based asset analysis.

    Usage:
        runner = MonteCarloRunner(
            symbol='GC',
            start_date='2026-04-01',
            end_date=None,
            analysis_column='pct_change',
            analysis_column_label='涨跌幅',
            limit_date=600,
            next_n_working_days=5,
            simulate_params={...}
        )
        original_df, prediction_df, final_df = runner.run_analysis()
        runner.plot_all()

        # Backtesting
        backtest_results = runner.run_backtest()
    """

    def __init__(
        self,
        symbol: str = 'GC',
        start_date: str = '2026-04-01',
        end_date: Optional[str] = None,
        analysis_column: str = 'pct_change',
        analysis_column_label: str = '涨跌幅',
        limit_date: int = 600,
        next_n_working_days: int = 5,
        simulate_params: dict = None,
    ):
        self.symbol = symbol
        self.start_date = start_date
        self.end_date = end_date
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
            'segma_calculation_type': 'garch',
        }
        if simulate_params:
            default_params.update(simulate_params)
        self.simulate_params = default_params

        # Ensure times param matches next_n_working_days
        self.simulate_params['times'] = next_n_working_days

        # Lazy-initialized
        self._analyzer = None
        self._original_df: Optional[pd.DataFrame] = None
        self._prediction_df: Optional[pd.DataFrame] = None
        self._final_df: Optional[pd.DataFrame] = None

        logger.info(
            f"MonteCarloRunner created: symbol={symbol}, "
            f"start_date={start_date}, end_date={end_date}, "
            f"analysis_column={analysis_column}, limit_date={limit_date}, "
            f"next_n_working_days={next_n_working_days}"
        )
        logger.info(
            f"Simulate params: distribution_type={self.simulate_params['distribution_type']}, "
            f"segma_calculation_type={self.simulate_params['segma_calculation_type']}, "
            f"series={self.simulate_params['series']}, alpha={self.simulate_params['alpha']}"
        )

    # ------------------------------------------------------------------
    #  Initialization
    # ------------------------------------------------------------------

    def initialize(self):
        """Create the analyzer instance via factory."""
        from .BaseAssetAnalyzer import AnalyzerFactory
        self._analyzer = AnalyzerFactory.create(
            self.symbol,
            start_date=self.start_date,
            end_date=self.end_date,
            analysis_column=self.analysis_column,
            analysis_column_label=self.analysis_column_label,
            limit_date=self.limit_date,
            next_n_working_days=self.next_n_working_days,
            simulate_params=self.simulate_params,
        )
        logger.info(f"Initialized analyzer for {self.symbol}")

    @property
    def analyzer(self):
        if self._analyzer is None:
            self.initialize()
        return self._analyzer

    # ------------------------------------------------------------------
    #  Main analysis
    # ------------------------------------------------------------------

    def run_analysis(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Execute the full Monte Carlo analysis pipeline.

        Returns:
            (original_analysis_df, prediction_df, final_merged_df)
        """
        logger.info(f"Running Monte Carlo analysis for {self.symbol}...")
        self._original_df, self._prediction_df, self._final_df = self.analyzer.run()

        logger.info(f"Analysis complete:")
        logger.info(f"  Original analysis: {len(self._original_df)} rows")
        logger.info(f"  Predictions:       {len(self._prediction_df)} rows")
        logger.info(f"  Final merged:      {len(self._final_df)} rows")

        return self._original_df, self._prediction_df, self._final_df

    # ------------------------------------------------------------------
    #  Backtesting
    # ------------------------------------------------------------------

    def run_backtest(
        self,
        test_start_date: str = '2026-01-01',
        test_end_date: str = '2026-12-31',
        distribution_types: list = None,
    ) -> dict:
        """
        Run Kupiec backtest for 2026.

        Args:
            test_start_date: test period start.
            test_end_date: test period end.
            distribution_types: distributions to test; if None, tests all.

        Returns:
            dict of distribution_type -> test results.
        """
        from .BacktestEngine import BacktestEngine

        engine = BacktestEngine(
            symbol=self.symbol,
            test_start_date=test_start_date,
            test_end_date=test_end_date,
            alpha=self.simulate_params.get('alpha', 0.05),
            limit_date=self.limit_date,
            distribution_types=distribution_types,
            segma_calculation_type=self.simulate_params.get('segma_calculation_type', 'normal'),
        )

        results = engine.run_backtest()

        # Print summary
        print("\n" + "=" * 70)
        print("KUPIEC POF BACKTEST SUMMARY")
        print("=" * 70)
        print(f"Symbol: {self.symbol}")
        print(f"Period: {test_start_date} → {test_end_date}")
        print(f"Expected violation rate (alpha): {self.simulate_params.get('alpha', 0.05)}")
        print("-" * 70)
        print(f"{'Distribution':<15} {'Violations':>10} {'Total':>8} {'Rate':>10} {'P-value':>10} {'H0 Reject':>10}")
        print("-" * 70)

        for dist_type, result in results.items():
            if 'error' in result:
                print(f"{dist_type:<15} {'ERROR':>10} {result['error']}")
                continue
            print(f"{dist_type:<15} {result['violations']:>10} {result['total']:>8} "
                  f"{result['observed_rate']:>10.4f} {result.get('p_value', np.nan):>10.4f} "
                  f"{str(result['reject_h0']):>10}")

        print("-" * 70)
        recommended = BacktestEngine.recommend_distribution(results)
        print(f"\nRecommended distribution: {recommended}")
        print("=" * 70 + "\n")

        # Plot (suppressed — charts are embedded in the PDF report)
        # BacktestEngine.plot_backtest_results(results)

        return results

    # ------------------------------------------------------------------
    #  Export to Excel
    # ------------------------------------------------------------------

    def _build_filename(self, label: str, ext: str = 'xlsx') -> str:
        """Build standardized output filename with generation timestamp."""
        start_clean = self.start_date.replace('-', '')
        end_clean = (self.analyzer.end_date or '').replace('-', '')
        dist = self.simulate_params.get('distribution_type', 'normal')
        segma = self.simulate_params.get('segma_calculation_type', 'normal')
        ts = self._export_timestamp
        return (
            f"Montcarlo_simulation_{label}_{self.symbol}_"
            f"{self.analysis_column}_{dist}_{segma}_"
            f"{start_clean}_{end_clean}_{ts}.{ext}"
        )

    def export_to_excel(self, output_dir: str = _MONTE_CARLO_REPORT_DIR):
        """
        Export all 3 DataFrames to Excel files with standardized naming.

        Files:
            Montcarlo_simulation_原始数据_{symbol}_{col}_{dist}_{sigma}_{start}_{end}.xlsx
            Montcarlo_simulation_预测结果_{symbol}_{col}_{dist}_{sigma}_{start}_{end}.xlsx
            Montcarlo_simulation_最终结果_{symbol}_{col}_{dist}_{sigma}_{start}_{end}.xlsx
        """
        if self._final_df is None:
            raise RuntimeError("No analysis results. Call run_analysis() first.")

        # Generate a single timestamp for all 3 files
        self._export_timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

        import os
        os.makedirs(output_dir, exist_ok=True)

        file_original = os.path.join(output_dir, self._build_filename("原始数据"))
        file_prediction = os.path.join(output_dir, self._build_filename("预测结果"))
        file_final = os.path.join(output_dir, self._build_filename("最终结果"))

        logger.info(f"Exporting to Excel: {output_dir}")
        logger.info(f"  Original analysis: {len(self._original_df)} rows → {file_original}")
        logger.info(f"  Prediction:        {len(self._prediction_df)} rows → {file_prediction}")
        logger.info(f"  Final merged:      {len(self._final_df)} rows → {file_final}")

        self._original_df.to_excel(file_original, index=False, engine='openpyxl')
        logger.info(f"Exported: {file_original}")

        self._prediction_df.to_excel(file_prediction, index=False, engine='openpyxl')
        logger.info(f"Exported: {file_prediction}")

        self._final_df.to_excel(file_final, index=False, engine='openpyxl')
        logger.info(f"Exported: {file_final}")

        print(f"\nExcel files exported to: {output_dir}")
        print(f"  原始数据: {os.path.basename(file_original)}")
        print(f"  预测结果: {os.path.basename(file_prediction)}")
        print(f"  最终结果: {os.path.basename(file_final)}")

    def run_and_export(self, output_dir: str = _MONTE_CARLO_REPORT_DIR
                       ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Run analysis, export to Excel, then return DataFrames."""
        logger.info(">>> run_and_export: step 1/2 — running analysis...")
        self.run_analysis()
        logger.info(">>> run_and_export: step 2/2 — exporting to Excel...")
        self.export_to_excel(output_dir)
        logger.info(">>> run_and_export: done.")
        return self._original_df, self._prediction_df, self._final_df

    # ------------------------------------------------------------------
    #  Plotting
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    #  Internal helpers for date-range strings
    # ------------------------------------------------------------------

    def _get_date_range_strs(self):
        """Return (orig_start, orig_end, pred_start, pred_end, final_end) for chart titles."""
        orig_dates = self._original_df['trade_date'].astype(str).str.replace('-', '')
        orig_start = orig_dates.iloc[0] if len(orig_dates) > 0 else ""
        orig_end = orig_dates.iloc[-1] if len(orig_dates) > 0 else ""

        pred_dates = self._prediction_df['trade_date'].astype(str).str.replace('-', '')
        pred_start = pred_dates.iloc[0] if len(pred_dates) > 0 else ""
        pred_end = pred_dates.iloc[-1] if len(pred_dates) > 0 else ""

        final_end = pred_end if pred_end else orig_end
        return orig_start, orig_end, pred_start, pred_end, final_end

    # ------------------------------------------------------------------
    #  Plotting
    # ------------------------------------------------------------------

    def plot_all(self):
        """Display all 4 charts after export."""
        from .Visualizer import Visualizer
        if self._original_df is None:
            raise RuntimeError("No analysis results. Call run_analysis() first.")

        asset_name = self.analyzer.get_asset_name()
        Visualizer.show_all(
            original_df=self._original_df,
            prediction_df=self._prediction_df,
            final_df=self._final_df,
            asset_name=asset_name,
            analysis_col_label=self.analysis_column_label,
        )

    def plot_original_analysis(self):
        """Display chart 1: 原始数据的分析."""
        from .Visualizer import Visualizer
        if self._original_df is None:
            raise RuntimeError("No analysis results. Call run_analysis() first.")
        orig_start, orig_end, _, _, _ = self._get_date_range_strs()
        Visualizer.plot_original_analysis(
            self._original_df,
            f"[{self.analyzer.get_asset_name()}] 原始数据的分析",
            self.analysis_column_label,
            start_date_str=orig_start,
            end_date_str=orig_end,
        )

    def plot_volatility_analysis(self):
        """Display chart 2: 波动率分析."""
        from .Visualizer import Visualizer
        if self._original_df is None:
            raise RuntimeError("No analysis results. Call run_analysis() first.")
        orig_start, orig_end, _, _, _ = self._get_date_range_strs()
        Visualizer.plot_volatility_analysis(
            self._original_df,
            f"[{self.analyzer.get_asset_name()}] 波动率分析",
            start_date_str=orig_start,
            end_date_str=orig_end,
        )

    def plot_prediction_results(self):
        """Display chart 3: 预测结果的分析."""
        from .Visualizer import Visualizer
        if self._prediction_df is None:
            raise RuntimeError("No analysis results. Call run_analysis() first.")
        _, _, pred_start, pred_end, _ = self._get_date_range_strs()
        Visualizer.plot_prediction_results(
            self._prediction_df,
            f"[{self.analyzer.get_asset_name()}] 预测结果的分析",
            self.analysis_column_label,
            start_date_str=pred_start,
            end_date_str=pred_end,
        )

    def plot_final_results(self):
        """Display chart 4: 最终结果."""
        from .Visualizer import Visualizer
        if self._final_df is None:
            raise RuntimeError("No analysis results. Call run_analysis() first.")
        orig_start, _, _, _, final_end = self._get_date_range_strs()
        Visualizer.plot_final_results(
            self._final_df,
            f"[{self.analyzer.get_asset_name()}] 最终结果",
            self.analysis_column_label,
            start_date_str=orig_start,
            end_date_str=final_end,
        )

    # ------------------------------------------------------------------
    #  Export to PDF report
    # ------------------------------------------------------------------

    def export_to_pdf(self, backtest_results: dict = None) -> str:
        """
        Generate a comprehensive PDF report with all 4 charts and professional commentary.

        Args:
            backtest_results: optional dict from run_backtest().

        Returns:
            Absolute path to the generated PDF file.
        """
        if self._original_df is None:
            raise RuntimeError("No analysis results. Call run_analysis() first.")

        from .ReportGenerator import ReportGenerator

        logger.info("Generating PDF report...")
        pdf_path = ReportGenerator.generate(
            original_df=self._original_df,
            prediction_df=self._prediction_df,
            final_df=self._final_df,
            asset_name=self.analyzer.get_asset_name(),
            analysis_col_label=self.analysis_column_label,
            start_date=self.start_date,
            end_date=self.analyzer.end_date or "",
            simulate_params=self.simulate_params,
            backtest_results=backtest_results,
            output_dir=_MONTE_CARLO_REPORT_DIR,
        )
        logger.info(f"PDF report generated: {pdf_path}")
        return pdf_path

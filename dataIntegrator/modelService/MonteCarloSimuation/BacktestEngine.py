"""
BacktestEngine — Kupiec POF (Proportion of Failures) test for backtesting VAR models.

Usage:
    engine = BacktestEngine(analyzer, test_start_date='2026-01-01',
                            test_end_date='2026-12-31', alpha=0.05)
    results = engine.run_backtest()
    engine.plot_backtest_results(results)
    recommended_dist = engine.recommend_distribution(results)
"""

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
import matplotlib.pyplot as plt
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Chinese font support — Chinese fonts FIRST for CJK glyph coverage
try:
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans', 'Arial']
    plt.rcParams['axes.unicode_minus'] = False
    plt.rcParams['font.family'] = 'sans-serif'
except Exception:
    pass


class BacktestEngine:
    """
    Backtest VAR predictions using Kupiec's POF test.

    The test compares the observed violation rate against the expected rate (alpha).
    A violation occurs when actual return < VAR_lower_bound (for lower tail).

    Kupiec POF statistic:
        LR_POF = -2 * ln( (1-alpha)^(T-N) * alpha^N /
                          (1 - N/T)^(T-N) * (N/T)^N )
    Under H0: violation rate = alpha, LR_POF ~ chi-squared(1).
    """

    def __init__(
        self,
        symbol: str = 'GC',
        test_start_date: str = '2026-01-01',
        test_end_date: str = '2026-12-31',
        alpha: float = 0.05,
        limit_date: int = 600,
        distribution_types: list = None,
        segma_calculation_type: str = 'normal',
    ):
        """
        Args:
            symbol: trading symbol.
            test_start_date: start of test period.
            test_end_date: end of test period.
            alpha: expected violation rate (significance level).
            limit_date: rolling window size for training.
            distribution_types: list of distribution types to test.
            segma_calculation_type: sigma calculation type.
        """
        self.symbol = symbol
        self.test_start_date = test_start_date
        self.test_end_date = test_end_date
        self.alpha = alpha
        self.limit_date = limit_date
        self.segma_calculation_type = segma_calculation_type

        if distribution_types is None:
            distribution_types = ['normal', 'student', 'skewed-t', 'lognormal', 'history']
        self.distribution_types = distribution_types

        logger.info(
            f"BacktestEngine initialized: symbol={symbol}, "
            f"test_period=[{test_start_date}, {test_end_date}], "
            f"alpha={alpha}, limit_date={limit_date}, "
            f"segma_calculation_type={segma_calculation_type}, "
            f"distribution_types={self.distribution_types}"
        )

    # ------------------------------------------------------------------
    #  Kupiec POF test
    # ------------------------------------------------------------------

    @staticmethod
    def kupiec_pof_test(violations: int, total: int, alpha: float) -> dict:
        """
        Perform Kupiec's Proportion of Failures test.

        Args:
            violations: number of VAR breaches observed.
            total: total number of observations.
            alpha: expected violation rate (e.g. 0.05).

        Returns:
            dict with keys:
                - violations, total, observed_rate, expected_rate
                - lr_stat (likelihood ratio statistic)
                - p_value
                - reject_h0 (bool, True if observed rate differs significantly)
                - conclusion (string)
        """
        if total == 0:
            return {
                'violations': 0, 'total': 0,
                'observed_rate': 0.0, 'expected_rate': alpha,
                'lr_stat': np.nan, 'p_value': np.nan,
                'reject_h0': False,
                'conclusion': 'No data for testing',
            }

        observed_rate = violations / total

        # Kupiec LR statistic
        # Handle edge cases
        eps = 1e-12
        if violations == 0:
            lr_stat = -2 * np.log((1 - alpha) ** total)
        elif violations == total:
            lr_stat = -2 * np.log(alpha ** total)
        else:
            lr_stat = -2 * (
                (total - violations) * np.log((1 - alpha) / max(1 - observed_rate, eps))
                + violations * np.log(alpha / max(observed_rate, eps))
            )

        # Chi-squared(1) p-value
        p_value = 1 - scipy_stats.chi2.cdf(lr_stat, df=1)

        # Critical value at 95% confidence: chi2(1, 0.95) ≈ 3.841
        reject_h0 = p_value < 0.05

        if reject_h0:
            conclusion = (
                f"Reject H0: actual violation rate {observed_rate:.4f} "
                f"significantly differs from expected {alpha:.4f} (p={p_value:.4f})."
            )
        else:
            conclusion = (
                f"Fail to reject H0: actual violation rate {observed_rate:.4f} "
                f"is consistent with expected {alpha:.4f} (p={p_value:.4f})."
            )

        logger.info(f"Kupiec POF: violations={violations}/{total}, observed_rate={observed_rate:.4f}, "
                     f"expected_rate={alpha:.4f}, LR={lr_stat:.4f}, p_value={p_value:.4f}, "
                     f"reject_h0={reject_h0}")

        return {
            'violations': violations,
            'total': total,
            'observed_rate': observed_rate,
            'expected_rate': alpha,
            'lr_stat': lr_stat,
            'p_value': p_value,
            'reject_h0': reject_h0,
            'conclusion': conclusion,
        }

    # ------------------------------------------------------------------
    #  Run backtest across distribution types
    # ------------------------------------------------------------------

    def run_backtest(self) -> dict:
        """
        Run backtest for each distribution type.

        For each distribution:
        1. Fetch 2026 data + lookback period
        2. For each day in 2026, use rolling window to compute VAR_lower
        3. Count violations where actual pct_change < VAR_lower
        4. Run Kupiec test

        Returns:
            dict of distribution_type -> test result dict.
        """
        from .BaseAssetAnalyzer import AnalyzerFactory

        logger.info("=" * 50)
        logger.info(f"Starting Kupiec POF backtest for {self.symbol}")
        logger.info(f"Test period: [{self.test_start_date}, {self.test_end_date}], "
                     f"alpha={self.alpha}, distributions={self.distribution_types}")
        logger.info("=" * 50)

        results = {}

        for dist_type in self.distribution_types:
            logger.info(f"--- Backtesting distribution: {dist_type} ---")

            try:
                # Fetch data including lookback
                fetch_start = self._get_lookback_start()
                logger.info(f"  Fetching data from {fetch_start} to {self.test_end_date}")
                analyzer = AnalyzerFactory.create(
                    self.symbol,
                    start_date=fetch_start,
                    end_date=self.test_end_date,
                    limit_date=self.limit_date,
                    simulate_params={
                        'distribution_type': dist_type,
                        'segma_calculation_type': self.segma_calculation_type,
                        'series': 5000,
                        'alpha': self.alpha,
                        'times': 1,
                        't': 0.01,
                    }
                )
                analyzer.fetch_data()
                df = analyzer.raw_data.copy()
                returns_raw = analyzer.get_analysis_returns()
                # Keep full-length series with NaN where pct_change is missing
                returns = returns_raw.values  # numpy array, same length as df

                # Filter to test period
                test_start_clean = self.test_start_date.replace('-', '')
                test_mask = df['trade_date'].astype(str).str.replace('-', '') >= test_start_clean
                test_indices = df.index[test_mask].tolist()
                logger.info(f"  Data: {len(df)} total rows, {len(test_indices)} in test period, "
                             f"returns range=[{np.nanmin(returns):.4f}, {np.nanmax(returns):.4f}]")

                violations = 0
                total = 0
                violation_dates = []
                var_lower_series = []
                actual_series = []

                from .MonteCarloEngine import MonteCarloEngine

                for pos in test_indices:
                    # Need at least limit_date previous data points
                    if pos < self.limit_date:
                        continue

                    # Get rolling window of returns (drop NaN within window)
                    window_raw = returns[max(0, pos - self.limit_date):pos]
                    window_valid = window_raw[~np.isnan(window_raw)]
                    actual_val = returns[pos]

                    if np.isnan(actual_val) or len(window_valid) < 30:
                        continue

                    total += 1
                    window_returns = pd.Series(window_valid)

                    if len(window_returns) < 30:
                        continue

                    engine = MonteCarloEngine(window_returns, analyzer.simulate_params)
                    engine.fit_distribution()
                    engine.calculate_sigma()
                    simulated = engine.simulate_single_step()

                    var_lower = float(np.percentile(simulated, self.alpha * 100))

                    var_lower_series.append(var_lower)
                    actual_series.append(actual_val)

                    if actual_val < var_lower:
                        violations += 1
                        violation_dates.append(str(df.iloc[pos]['trade_date']))

                kupiec_result = self.kupiec_pof_test(violations, total, self.alpha)
                kupiec_result['distribution_type'] = dist_type
                kupiec_result['violation_dates'] = violation_dates
                kupiec_result['var_lower_series'] = var_lower_series
                kupiec_result['actual_series'] = actual_series

                results[dist_type] = kupiec_result
                logger.info(f"  Result: violations={violations}/{total}, "
                             f"rate={kupiec_result['observed_rate']:.4f}, "
                             f"p_value={kupiec_result.get('p_value', np.nan):.4f}, "
                             f"reject_h0={kupiec_result['reject_h0']}")

            except Exception as e:
                logger.error(f"Backtest failed for {dist_type}: {e}", exc_info=True)
                results[dist_type] = {
                    'distribution_type': dist_type,
                    'error': str(e),
                    'violations': 0,
                    'total': 0,
                    'observed_rate': 0.0,
                    'conclusion': f'Error: {e}',
                }

        logger.info("=" * 50)
        logger.info("Backtest complete for all distributions")
        logger.info("=" * 50)
        return results

    def _get_lookback_start(self) -> str:
        """Calculate the start date including enough lookback."""
        test_start_dt = pd.to_datetime(self.test_start_date)
        # Estimate ~2 years of lookback (trading days)
        lookback_start = test_start_dt - pd.DateOffset(days=self.limit_date * 2)
        return lookback_start.strftime('%Y-%m-%d')

    # ------------------------------------------------------------------
    #  Recommendation
    # ------------------------------------------------------------------

    @classmethod
    def recommend_distribution(cls, results: dict) -> str:
        """
        Recommend the best distribution based on backtest results.

        Criteria: closest observed_rate to expected alpha (lowest absolute deviation)
        among distributions that do NOT reject H0.
        If all reject H0, pick the one with the lowest LR statistic.
        """
        best_dist = None
        best_score = float('inf')

        # First pass: distributions that do NOT reject H0
        for dist_type, result in results.items():
            if 'error' in result:
                continue
            if not result.get('reject_h0', True):
                deviation = abs(result['observed_rate'] - result['expected_rate'])
                if deviation < best_score:
                    best_score = deviation
                    best_dist = dist_type

        if best_dist is not None:
            return best_dist

        # Second pass: if all reject, pick lowest LR stat
        best_lr = float('inf')
        for dist_type, result in results.items():
            if 'error' in result or 'lr_stat' not in result:
                continue
            lr = result.get('lr_stat', float('inf'))
            if not np.isnan(lr) and lr < best_lr:
                best_lr = lr
                best_dist = dist_type

        return best_dist or 'normal'

    # ------------------------------------------------------------------
    #  Plotting
    # ------------------------------------------------------------------

    @classmethod
    def plot_backtest_results(cls, results: dict, show: bool = True):
        """Plot backtest summary: violation rates per distribution vs expected alpha.
        
        Args:
            results: dict from run_backtest().
            show: if True, call plt.show(). Always returns (fig, axes).
        
        Returns:
            (fig, axes) tuple for embedding in PDF reports.
        """
        dists = []
        observed_rates = []
        p_values = []
        rejections = []

        for dist_type, result in results.items():
            if 'error' in result:
                continue
            dists.append(dist_type)
            observed_rates.append(result.get('observed_rate', 0))
            p_values.append(result.get('p_value', np.nan))
            rejections.append(result.get('reject_h0', True))

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        fig.suptitle("Kupiec POF Backtest Results", fontsize=14, fontweight='bold')

        if not dists:
            for ax in axes:
                ax.text(0.5, 0.5, "No backtest results available", ha='center', va='center',
                        transform=ax.transAxes, fontsize=12)
            if show:
                plt.show()
            return fig, axes

        # Bar chart: observed vs expected violation rate
        ax1 = axes[0]
        x = np.arange(len(dists))
        width = 0.35
        bars = ax1.bar(x - width / 2, observed_rates, width, label='Observed Rate', color='steelblue')
        ax1.axhline(y=results[list(results.keys())[0]]['expected_rate'],
                     color='red', linestyle='--', linewidth=1.5, label='Expected Rate (alpha)')
        ax1.set_xticks(x)
        ax1.set_xticklabels(dists, rotation=30)
        ax1.set_ylabel('Violation Rate')
        ax1.set_title('Observed vs Expected Violation Rate')
        ax1.legend()
        ax1.grid(True, alpha=0.3, axis='y')

        # Color bars: green if not rejected, red if rejected
        for bar, rej in zip(bars, rejections):
            bar.set_color('lightcoral' if rej else 'mediumseagreen')

        # P-values
        ax2 = axes[1]
        colors = ['lightcoral' if rej else 'mediumseagreen' for rej in rejections]
        ax2.bar(dists, p_values, color=colors, alpha=0.7)
        ax2.axhline(y=0.05, color='red', linestyle='--', linewidth=1.5, label='p=0.05 threshold')
        ax2.set_ylabel('P-value')
        ax2.set_title('Kupiec Test P-values')
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.set_yscale('log')
        ax2.set_ylim(bottom=1e-6, top=1.1)

        plt.tight_layout()
        if show:
            plt.show()
        return fig, axes

    # ------------------------------------------------------------------
    #  Detailed VAR violation plot for a specific distribution
    # ------------------------------------------------------------------

    @classmethod
    def plot_var_violations(cls, result: dict, title: str = "VAR Violation Analysis",
                            show: bool = True):
        """Plot actual returns vs VAR lower bound, highlighting violations.
        
        Args:
            result: single distribution result dict from run_backtest().
            title: chart title.
            show: if True, call plt.show(). Always returns fig.
        
        Returns:
            fig or None if no series data available.
        """
        if 'var_lower_series' not in result or 'actual_series' not in result:
            fig, ax = plt.subplots(figsize=(10, 3))
            ax.text(0.5, 0.5, "No detailed series data in result.", ha='center', va='center',
                    transform=ax.transAxes, fontsize=12)
            if show:
                plt.show()
            return fig

        var_lower = np.array(result['var_lower_series'])
        actual = np.array(result['actual_series'])
        n = len(actual)

        fig, ax = plt.subplots(figsize=(14, 6))
        ax.set_title(title, fontsize=14, fontweight='bold')

        x = np.arange(n)
        ax.plot(x, actual, 'b-', linewidth=0.6, alpha=0.7, label='Actual pct_change')
        ax.plot(x, var_lower, 'r--', linewidth=0.8, alpha=0.8, label='VAR Lower Bound')

        # Highlight violations
        violation_mask = actual < var_lower
        if violation_mask.any():
            ax.scatter(x[violation_mask], actual[violation_mask],
                       color='red', s=30, zorder=5, label=f'Violations ({violation_mask.sum()})')

        ax.set_xlabel('Observation Index')
        ax.set_ylabel('pct_change')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='gray', linewidth=0.5)

        plt.tight_layout()
        if show:
            plt.show()
        return fig

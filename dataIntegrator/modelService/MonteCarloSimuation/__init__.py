"""
Monte Carlo Simulation System for Asset Price Prediction
========================================================
Factory-pattern based extensible Monte Carlo simulation framework.
Supports multiple distribution types, GARCH/EGARCH volatility models,
VAR/ES risk metrics, and Kupiec backtesting.

Usage:
    from MonteCarloSimuation import MonteCarloRunner

    runner = MonteCarloRunner(
        symbol='GC',
        start_date='2026-04-01',
        end_date=None,  # uses today
        analysis_column='pct_change',
        analysis_column_label='涨跌幅',
        limit_date=600,
        next_n_working_days=5,
        simulate_params={
            'init_value': 'pct_change',
            'analysis_column': 'pct_change',
            't': 0.01,
            'times': 5,
            'series': 5000,
            'alpha': 0.05,
            'distribution_type': 'normal',
            'segma_calculation_type': 'garch'
        }
    )
    original_df, prediction_df, final_df = runner.run_analysis()
    runner.plot_all()

    # Backtesting
    backtest_results = runner.run_backtest()
"""

from .MonteCarloRunner import MonteCarloRunner
from .BaseAssetAnalyzer import BaseAssetAnalyzer, AnalyzerFactory
from .GoldAnalyzer import GoldAnalyzer
from .USStockAnalyzer import USStockAnalyzer
from .MonteCarloEngine import MonteCarloEngine
from .RiskMetrics import RiskMetrics
from .ResultAggregator import ResultAggregator
from .Visualizer import Visualizer
from .BacktestEngine import BacktestEngine

__all__ = [
    'MonteCarloRunner',
    'BaseAssetAnalyzer',
    'AnalyzerFactory',
    'GoldAnalyzer',
    'USStockAnalyzer',
    'MonteCarloEngine',
    'RiskMetrics',
    'ResultAggregator',
    'Visualizer',
    'BacktestEngine',
]

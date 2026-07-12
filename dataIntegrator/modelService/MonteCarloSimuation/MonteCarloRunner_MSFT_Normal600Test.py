"""
Monte Carlo Simulation Test — Microsoft (MSFT) Stock Price Prediction
======================================================================
Flow: run_and_export (analysis + Excel export) → plot_all (4 charts) → backtest → PDF report
"""
from dataIntegrator.modelService.MonteCarloSimuation import MonteCarloRunner

runner = MonteCarloRunner(
    symbol='MSFT',
    start_date='2025-04-01',
    end_date=None,  # 默认今天
    analysis_column='pct_change',
    analysis_column_label='涨跌幅',
    limit_date=600,
    next_n_working_days=5,
    simulate_params={
        'distribution_type': 'normal',
        'segma_calculation_type': 'garch',
        'series': 5000,
        'alpha': 0.05,
    }
)

# 1. 主分析 + Excel 导出（先输出数据）
original_df, prediction_df, final_df = runner.run_and_export()

# # 2. 作图（输出数据后再作图）
# runner.plot_all()

# 3. 回测验证（Kupiec 检验 2026 年）
backtest_results = runner.run_backtest(
    test_start_date='2026-01-01',
    test_end_date='2026-12-31',
)

# 4. 导出 PDF 报告（所有图表 + 专业交易员和风险分析师点评）
runner.export_to_pdf(backtest_results=backtest_results)

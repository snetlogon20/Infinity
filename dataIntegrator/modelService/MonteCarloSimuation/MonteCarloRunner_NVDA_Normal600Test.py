"""
Monte Carlo Simulation Test — NVIDIA (NVDA) Stock Price Prediction
===================================================================
Flow: run_and_export (analysis + Excel export) → plot_all (4 charts) → backtest → PDF report
"""
from dataIntegrator.modelService.MonteCarloSimuation import MonteCarloRunner
import pandas as pd
from datetime import datetime

# ============================================================
# 1. 数据日期范围检查（诊断用）
# ============================================================
print("=" * 60)
print(f"[Diagnostic] Checking NVDA data date range in ClickHouse...")
print("=" * 60)

from dataIntegrator.dataService.ClickhouseService import ClickhouseService
cs = ClickhouseService()
sql = "SELECT date FROM indexsysdb.df_akshare_stock_us_daily WHERE symbol = 'NVDA' ORDER BY date"
cursor = cs.clickhouseClient.execute_iter(sql, with_column_types=True)
columns = [col[0] for col in next(cursor)]
result = list(cursor)
df_check = pd.DataFrame(result, columns=columns)
df_check['trade_date'] = pd.to_datetime(df_check['trade_date'])

print(f"  NVDA数据总量: {len(df_check)} 行")
print(f"  首条日期:    {df_check['trade_date'].iloc[0]}")
print(f"  末条日期:    {df_check['trade_date'].iloc[-1]}")

rows_2026 = (df_check['trade_date'] >= '2026-01-01').sum()
print(f"  2026年数据:   {rows_2026} 行")

if rows_2026 == 0:
    print(f"\n  ⚠️  NVDA 没有 2026 年数据！回测期间 2026-01-01 ~ 2026-12-31 将全部为 0。")
    print(f"  💡 解决方法: 需要刷新 NVDA 数据。请运行:")
    print(f"     python -c \"from dataIntegrator.TuShareService.TuShareUSStockDailyServiceTest import TuShareUSStockDailyServiceTest; TuShareUSStockDailyServiceTest.refresh_stocks()\"")
    print(f"  (先用注释中的 ts_code_list = [\"NVDA\"] 替换 refresh_stocks() 中的列表)")
    print(f"\n  ⏩ 将使用最后 250 行数据作为替代回测期间...")
    
    # Use last 250 rows as test period
    test_start_idx = max(0, len(df_check) - 250)
    alt_start = df_check['trade_date'].iloc[test_start_idx]
    alt_end = df_check['trade_date'].iloc[-1]
    print(f"     替代回测期: {str(alt_start)[:10]} ~ {str(alt_end)[:10]}")
else:
    print(f"  ✅ NVDA 有 2026 年数据，可以使用标准回测期间。")
print("=" * 60 + "\n")

# ============================================================
# 2.  Monte Carlo 主分析
# ============================================================
runner = MonteCarloRunner(
    symbol='NVDA',
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

# 主分析 + Excel 导出
original_df, prediction_df, final_df = runner.run_and_export()

# # 作图（可选）
# runner.plot_all()

# 回测验证（Kupiec 检验）
backtest_results = runner.run_backtest(
    test_start_date='2026-01-01',
    test_end_date='2026-12-31',
)

# 导出 PDF 报告
runner.export_to_pdf(backtest_results=backtest_results)
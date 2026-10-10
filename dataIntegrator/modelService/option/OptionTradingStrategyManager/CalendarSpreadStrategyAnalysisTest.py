r"""
Calendar Spread（日历价差）策略分析 测试入口

先运行本模块落库，再运行 CalendarSpreadStrategyReportTest 生成 PDF 报告。
注意：日历价差需要跨月配对，symbol_filter 不带月份（取全部到期月），方向固定 'C'。
"""

from dataIntegrator import CommonParameters
from dataIntegrator.modelService.option.OptionTradingStrategyManager.CalendarSpreadStrategyAnalysis import CalendarSpreadStrategyAnalysis

if __name__ == "__main__":
    analyzer = CalendarSpreadStrategyAnalysis()
    analyzer.run({
        "name": "华夏上证50ETF期权（Calendar Spread）",
        "start_date": "20251222",
        "end_date": CommonParameters.today,
        "call_put": "C",
        "symbol_filter": "510050%",
    })

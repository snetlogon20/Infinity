r"""
Calendar Spread（日历价差）策略 PDF 报告 测试入口

前置条件：先运行 CalendarSpreadStrategyAnalysisTest 落库分析结果。
"""

from dataIntegrator import CommonParameters
from dataIntegrator.modelService.option.OptionTradingStrategyManager.CalendarSpreadStrategyReport import CalendarSpreadStrategyReport

if __name__ == "__main__":
    report = CalendarSpreadStrategyReport()
    report.run({
        "name": "华夏上证50ETF期权（Calendar Spread）",
        "start_date": "20251222",
        "end_date": CommonParameters.today,
        "call_put": "C",
        "symbol_filter": "510050%",
    })

r"""
Strip（条式组合）策略 PDF 报告 测试入口

前置条件：先运行 StripStrategyAnalysisTest 落库分析结果。
"""

from dataIntegrator import CommonParameters
from dataIntegrator.modelService.option.OptionTradingStrategyManager.StripStrategyReport import StripStrategyReport

if __name__ == "__main__":
    report = StripStrategyReport()
    report.run({
        "name": "华夏上证50ETF期权（Strip）",
        "start_date": "20251222",
        "end_date": CommonParameters.today,
        "call_put": None,
        "symbol_filter": "510050%2612%",
    })

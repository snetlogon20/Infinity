r"""
Strap（带式组合）策略 PDF 报告 测试入口

前置条件：先运行 StrapStrategyAnalysisTest 落库分析结果。
"""

from dataIntegrator import CommonParameters
from dataIntegrator.modelService.option.OptionTradingStrategyManager.StrapStrategyReport import StrapStrategyReport

if __name__ == "__main__":
    report = StrapStrategyReport()
    report.run({
        "name": "华夏上证50ETF期权（Strap）",
        "start_date": "20251222",
        "end_date": CommonParameters.today,
        "call_put": None,
        "symbol_filter": "510050%2612%",
    })

r"""
Bear Put Spread（熊市看跌价差）策略 PDF 报告 测试入口

前置条件：先运行 BearPutSpreadStrategyAnalysisTest 落库分析结果。
"""

from dataIntegrator import CommonParameters
from dataIntegrator.modelService.option.OptionTradingStrategyManager.BearPutSpreadStrategyReport import BearPutSpreadStrategyReport

if __name__ == "__main__":
    report = BearPutSpreadStrategyReport()
    report.run({
        "name": "华夏上证50ETF认沽期权（Bear Put Spread）",
        "start_date": "20251222",
        "end_date": CommonParameters.today,
        "call_put": "P",
        "symbol_filter": "510050P2612%",
    })

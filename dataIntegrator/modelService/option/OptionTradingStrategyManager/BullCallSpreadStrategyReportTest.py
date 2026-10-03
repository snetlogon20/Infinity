r"""
Bull Call Spread（牛市看涨价差）策略 PDF 报告 测试入口

前置条件：先运行 BullCallSpreadStrategyAnalysisTest 落库分析结果。
"""

from dataIntegrator import CommonParameters
from dataIntegrator.modelService.option.OptionTradingStrategyManager.BullCallSpreadStrategyReport import BullCallSpreadStrategyReport

if __name__ == "__main__":
    report = BullCallSpreadStrategyReport()
    report.run({
        "name": "华夏上证50ETF认购期权（Bull Call Spread）",
        "start_date": "20251222",
        "end_date": CommonParameters.today,
        "call_put": "C",
        "symbol_filter": "510050C2612%",
    })

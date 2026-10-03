r"""
Bull Call Spread（牛市看涨价差）策略分析 测试入口

先运行本模块落库，再运行 BullCallSpreadStrategyReportTest 生成 PDF 报告。
"""

from dataIntegrator import CommonParameters
from dataIntegrator.modelService.option.OptionTradingStrategyManager.BullCallSpreadStrategyAnalysis import BullCallSpreadStrategyAnalysis

if __name__ == "__main__":
    analyzer = BullCallSpreadStrategyAnalysis()
    analyzer.run({
        "name": "华夏上证50ETF认购期权（Bull Call Spread）",
        "start_date": "20251222",
        "end_date": CommonParameters.today,
        "call_put": "C",
        "symbol_filter": "510050C2612%",
    })

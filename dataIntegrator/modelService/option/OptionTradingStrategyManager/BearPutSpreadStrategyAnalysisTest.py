r"""
Bear Put Spread（熊市看跌价差）策略分析 测试入口

先运行本模块落库，再运行 BearPutSpreadStrategyReportTest 生成 PDF 报告。
"""

from dataIntegrator import CommonParameters
from dataIntegrator.modelService.option.OptionTradingStrategyManager.BearPutSpreadStrategyAnalysis import BearPutSpreadStrategyAnalysis

if __name__ == "__main__":
    analyzer = BearPutSpreadStrategyAnalysis()
    analyzer.run({
        "name": "华夏上证50ETF认沽期权（Bear Put Spread）",
        "start_date": "20251222",
        "end_date": CommonParameters.today,
        "call_put": "P",
        "symbol_filter": "510050P2612%",
    })

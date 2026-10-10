r"""
Synthetic Short Stock(合成空头 - 卖 Call + 买 Put)策略报告 测试入口

前置: 先运行 SyntheticShortStockStrategyAnalysisTest 落库分析结果。
"""

from dataIntegrator.modelService.option.OptionTradingStrategyManager.SyntheticShortStockStrategyReport import SyntheticShortStockStrategyReport

if __name__ == "__main__":
    report = SyntheticShortStockStrategyReport()
    report.run({
        "name": "合成空头（Synthetic Short Stock）策略分析报告",
        "symbol_filter": None,
    })

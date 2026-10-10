r"""
Synthetic Long Stock(合成多头 - 买 Call + 卖 Put)策略报告 测试入口

前置: 先运行 SyntheticLongStockStrategyAnalysisTest 落库分析结果。
"""

from dataIntegrator.modelService.option.OptionTradingStrategyManager.SyntheticLongStockStrategyReport import SyntheticLongStockStrategyReport

if __name__ == "__main__":
    report = SyntheticLongStockStrategyReport()
    report.run({
        "name": "合成多头（Synthetic Long Stock）策略分析报告",
        "symbol_filter": None,
    })

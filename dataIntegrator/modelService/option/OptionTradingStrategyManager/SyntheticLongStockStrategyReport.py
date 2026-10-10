r"""
Synthetic Long Stock(合成多头)策略 PDF 报告生成器

先运行 SyntheticLongStockStrategyAnalysisTest 落库, 再运行本报告。
共享 SyntheticStockStrategyReportBase 的全部图表/明细/点评/组装逻辑。
"""

from dataIntegrator.modelService.option.OptionTradingStrategyManager.SyntheticStockStrategyReportBase import (
    SyntheticStockStrategyReportBase
)


class SyntheticLongStockStrategyReport(SyntheticStockStrategyReportBase):
    """合成多头报告生成器(买C卖P, 净Delta≈+1)"""

    STRATEGY_TYPE = 'SYNTHETIC_LONG_STOCK'
    TABLE_SOURCE = 'tb_option_trading_strategy_synthetic_long_stock'
    DIRECTION = 1
    STRATEGY_CN = '合成多头'
    REPORT_TITLE = '合成多头（Synthetic Long Stock）策略分析报告'
    REPORT_SUBTITLE = 'Synthetic Long Stock Strategy Report — 买 Call + 卖 Put，复制现货多头'


if __name__ == "__main__":
    report = SyntheticLongStockStrategyReport()
    report.run({
        "name": "合成多头（Synthetic Long Stock）策略分析报告",
    })

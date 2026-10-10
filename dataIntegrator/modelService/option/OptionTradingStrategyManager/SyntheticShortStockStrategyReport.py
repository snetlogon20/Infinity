r"""
Synthetic Short Stock(合成空头)策略 PDF 报告生成器

先运行 SyntheticShortStockStrategyAnalysisTest 落库, 再运行本报告。
共享 SyntheticStockStrategyReportBase 的全部图表/明细/点评/组装逻辑。
"""

from dataIntegrator.modelService.option.OptionTradingStrategyManager.SyntheticStockStrategyReportBase import (
    SyntheticStockStrategyReportBase
)


class SyntheticShortStockStrategyReport(SyntheticStockStrategyReportBase):
    """合成空头报告生成器(卖C买P, 净Delta≈-1)"""

    STRATEGY_TYPE = 'SYNTHETIC_SHORT_STOCK'
    TABLE_SOURCE = 'tb_option_trading_strategy_synthetic_short_stock'
    DIRECTION = -1
    STRATEGY_CN = '合成空头'
    REPORT_TITLE = '合成空头（Synthetic Short Stock）策略分析报告'
    REPORT_SUBTITLE = 'Synthetic Short Stock Strategy Report — 卖 Call + 买 Put，融券替代做空'


if __name__ == "__main__":
    report = SyntheticShortStockStrategyReport()
    report.run({
        "name": "合成空头（Synthetic Short Stock）策略分析报告",
    })

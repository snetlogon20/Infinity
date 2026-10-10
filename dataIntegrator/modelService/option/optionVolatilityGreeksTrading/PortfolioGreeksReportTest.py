r"""
组合 Greeks 聚合与对冲 PDF 报告 测试入口

前置条件：先运行 PortfolioGreeksAggregatorTest 落库 tb_option_portfolio_greeks。

运行方式:
    python -m dataIntegrator.modelService.option.optionVolatilityGreeksTrading.PortfolioGreeksReportTest
"""

from dataIntegrator import CommonParameters
from dataIntegrator.modelService.option.optionVolatilityGreeksTrading.PortfolioGreeksReport import (
    PortfolioGreeksReport
)

if __name__ == "__main__":
    report = PortfolioGreeksReport()
    report.run({
        "name": "50ETF期权 组合Greeks与对冲报告",
        "end_date": CommonParameters.today,
    })

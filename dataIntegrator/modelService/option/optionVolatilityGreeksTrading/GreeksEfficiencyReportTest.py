r"""
Greeks 效率扫描 PDF 报告 测试入口

前置条件：先运行 GreeksEfficiencyAnalysisTest 落库 tb_option_greeks_efficiency。

运行方式:
    python -m dataIntegrator.modelService.option.optionVolatilityGreeksTrading.GreeksEfficiencyReportTest
"""

from dataIntegrator import CommonParameters
from dataIntegrator.modelService.option.optionVolatilityGreeksTrading.GreeksEfficiencyReport import (
    GreeksEfficiencyReport
)

if __name__ == "__main__":
    report = GreeksEfficiencyReport()
    report.run({
        "name": "华夏上证50ETF期权（Greeks效率报告）",
        "end_date": CommonParameters.today,
        "symbol_filter": "510050%",
    })

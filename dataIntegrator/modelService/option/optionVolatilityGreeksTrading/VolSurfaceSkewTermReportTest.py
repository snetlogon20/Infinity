r"""
波动率曲面 偏度/期限结构 PDF 报告 测试入口

前置条件：先运行 VolSurfaceSkewTermAnalysisTest 落库 tb_option_vol_surface。

运行方式:
    python -m dataIntegrator.modelService.option.optionVolatilityGreeksTrading.VolSurfaceReportTest
"""

from dataIntegrator import CommonParameters
from dataIntegrator.modelService.option.optionVolatilityGreeksTrading.VolSurfaceSkewTermReport import (
    VolSurfaceReport
)

if __name__ == "__main__":
    report = VolSurfaceReport()
    report.run({
        "name": "华夏上证50ETF期权（波动率曲面报告）",
        "end_date": CommonParameters.today,
        "symbol_filter": "510050%",
    })

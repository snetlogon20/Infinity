r"""
波动率曲面 偏度/期限结构 测试入口(落库)

先运行本模块落库 tb_option_vol_surface,
再运行 VolSurfaceReportTest 生成 PDF 报告。

运行方式:
    python -m dataIntegrator.modelService.option.optionVolatilityGreeksTrading.VolSurfaceSkewTermAnalysisTest
"""

from dataIntegrator import CommonParameters
from dataIntegrator.modelService.option.optionVolatilityGreeksTrading.VolSurfaceSkewTermAnalysis import (
    VolSurfaceSkewTermAnalysis
)

if __name__ == "__main__":
    analyzer = VolSurfaceSkewTermAnalysis()
    analyzer.run({
        "name": "华夏上证50ETF期权（波动率曲面偏度/期限结构）",
        "start_date": "20250901",
        "end_date": CommonParameters.today,
        "symbol_filter": "510050%",
    })

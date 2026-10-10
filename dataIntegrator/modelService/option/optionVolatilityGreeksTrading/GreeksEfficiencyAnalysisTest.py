r"""
Greeks 效率扫描 测试入口(落库)

先运行本模块落库 tb_option_greeks_efficiency,
再运行 GreeksEfficiencyReportTest 生成 PDF 报告。

运行方式:
    python -m dataIntegrator.modelService.option.optionVolatilityGreeksTrading.GreeksEfficiencyAnalysisTest
"""

from dataIntegrator import CommonParameters
from dataIntegrator.modelService.option.optionVolatilityGreeksTrading.GreeksEfficiencyAnalysis import (
    GreeksEfficiencyAnalysis
)

if __name__ == "__main__":
    analyzer = GreeksEfficiencyAnalysis()
    analyzer.run({
        "name": "华夏上证50ETF期权（Greeks效率扫描）",
        "start_date": "20250901",
        "end_date": CommonParameters.today,
        "call_put": None,           # 双腿全扫(C+P), 卖方/买方选腿在报告端按角色过滤
        "symbol_filter": "510050%",
    })

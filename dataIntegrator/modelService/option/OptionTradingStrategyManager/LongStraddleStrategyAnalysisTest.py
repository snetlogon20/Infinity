r"""
Long Straddle（买入跨式）策略分析 测试入口

先运行本模块落库，再运行 LongStraddleStrategyReportTest 生成 PDF 报告。
注意：跨式需要同时取 Call 与 Put 双腿，call_put 传 None、symbol_filter 不带方向。
"""

from dataIntegrator import CommonParameters
from dataIntegrator.modelService.option.OptionTradingStrategyManager.LongStraddleStrategyAnalysis import LongStraddleStrategyAnalysis

if __name__ == "__main__":
    analyzer = LongStraddleStrategyAnalysis()
    analyzer.run({
        "name": "华夏上证50ETF期权（Long Straddle）",
        "start_date": "20251222",
        "end_date": CommonParameters.today,
        "call_put": None,
        "symbol_filter": "510050%2612%",
    })

r"""ButterflySpreadStrategyReport 测试入口 — 华夏上证50ETF认购期权（2025年12月到期）"""
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.modelService.option.OptionTradingStrategyManager.ButterflySpreadStrategyReport import (
    ButterflySpreadStrategyReport
)

if __name__ == "__main__":
    report = ButterflySpreadStrategyReport()
    report.run({
        "name": "华夏上证50ETF认购期权（Butterfly Spread 蝴蝶价差）",
        "start_date": "20251222",
        "end_date": CommonParameters.today,
        "call_put": "C",
        "symbol_filter": "510050C2612%",
    })

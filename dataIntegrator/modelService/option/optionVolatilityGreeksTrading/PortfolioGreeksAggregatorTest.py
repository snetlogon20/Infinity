r"""
组合 Greeks 聚合与对冲 测试入口(落库)

方式一(自动示例持仓): ATM straddle —— 最新交易日 510050 的 ATM Call+Put 各买 1 张
方式二(显式持仓): 编辑 POSITIONS, 指定 ts_code / direction(+1买, -1卖) / quantity

先运行本模块落库 tb_option_portfolio_greeks,
再运行 PortfolioGreeksReportTest 生成 PDF 报告。

运行方式:
    python -m dataIntegrator.modelService.option.optionVolatilityGreeksTrading.PortfolioGreeksAggregatorTest
"""

from dataIntegrator import CommonParameters
from dataIntegrator.modelService.option.optionVolatilityGreeksTrading.PortfolioGreeksAggregator import (
    PortfolioGreeksAggregator
)

if __name__ == "__main__":
    aggregator = PortfolioGreeksAggregator()

    # ---- 方式一: 自动构建 ATM straddle 示例持仓 ----
    aggregator.run({
        "name": "50ETF期权 ATM跨式 组合Greeks监控(示例)",
        "end_date": CommonParameters.today,
        "auto_positions": "ATM_STRADDLE",
        "symbol_filter": "510050%",
        "auto_quantity": 2,
        "hedge_instrument": "ETF_LOT",
    })

    # ---- 方式二: 显式持仓(取消注释并填入实际合约) ----
    # aggregator.run({
    #     "name": "50ETF期权 组合Greeks监控(自定义持仓)",
    #     "end_date": CommonParameters.today,
    #     "positions": [
    #         {"ts_code": "10006564", "direction": +1, "quantity": 10},  # 买Call
    #         {"ts_code": "10006575", "direction": -1, "quantity": 5},   # 卖Put
    #     ],
    #     "hedge_instrument": "ETF_LOT",   # SPOT / ETF_LOT / FUTURE
    # })

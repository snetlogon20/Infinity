r"""
Synthetic Long Stock(合成多头)策略分析 — 资深交易员/风控视角

策略定义: 买 Call(K,T) + 卖 Put(K,T), 净支出 C-P, 复制现货多头(净Delta≈+1)
    到期损益 = S_T - K - (C-P), 盈亏平衡点 = K + (C-P), 上行不封顶
    下行风险非有限(S_T→0 亏损≈K+净成本), 卖出Put腿有保证金追缴义务

交易员核心问题: "借钱买现货, 市场收我多少利息?"
    理论: C-P = S·e^(-qT) - K·e^(-rT) → 反推隐含融资利率 r_impl
    financing_spread_bp = (r_impl - r)×1e4:
        显著为负 → 合成比融资买现货便宜(替代持有/套利窗口)
        显著为正 → 合成贵(资金面紧张或分红预期抬升)

落库: tb_option_trading_strategy_synthetic_long_stock, strategy_type='SYNTHETIC_LONG_STOCK'

使用:
    config = {
        "name": "华夏上证50ETF期权(合成多头)",
        "start_date": "20251222",
        "end_date": CommonParameters.today,
        "call_put": None,
        "symbol_filter": "510050%2612%",
    }
    SyntheticLongStockStrategyAnalysis().run(config)
"""

from dataIntegrator.modelService.option.OptionTradingStrategyManager.SyntheticStockStrategyBase import (
    SyntheticStockStrategyAnalysisBase
)


class SyntheticLongStockStrategyAnalysis(SyntheticStockStrategyAnalysisBase):
    """合成多头分析器(买C卖P, 净Delta≈+1)

    共享 SyntheticStockStrategyAnalysisBase 的配对/核心指标/情景/信号骨架,
    本类只声明策略标识与方向; 信号叙事=隐含融资利率 vs 基准资金成本。
    """

    # === 策略标识 ===
    STRATEGY_TYPE = 'SYNTHETIC_LONG_STOCK'
    ANALYSIS_VERSION = 'v1'
    TABLE_TARGET = 'tb_option_trading_strategy_synthetic_long_stock'
    DIRECTION = 1   # +1 = 买Call卖Put(合成多头)

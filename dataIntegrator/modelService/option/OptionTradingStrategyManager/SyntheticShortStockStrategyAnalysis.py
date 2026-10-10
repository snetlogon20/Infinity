r"""
Synthetic Short Stock(合成空头)策略分析 — 资深交易员/风控视角

策略定义: 卖 Call(K,T) + 买 Put(K,T), 净收入 C-P, 复制现货空头(净Delta≈-1)
    到期损益 = K - S_T + (C-P), 盈亏平衡点 = K - (C-P), 下行盈利不封顶
    上行风险非有限(S_T大涨亏损无界), 卖出Call腿有保证金追缴义务

交易员核心问题: "做空这个标的, 合成比融券便宜吗?"
    A股融券: 券源紧、年化成本高(粗略基准6%+)
    合成空头: 卖出收价高于理论(synth_deviation>0)即有利;
    年化做空成本 = -synth_deviation/(S·T年), 对照融券成本判断替代有效性

落库: tb_option_trading_strategy_synthetic_short_stock, strategy_type='SYNTHETIC_SHORT_STOCK'

使用:
    config = {
        "name": "华夏上证50ETF期权(合成空头)",
        "start_date": "20251222",
        "end_date": CommonParameters.today,
        "call_put": None,
        "symbol_filter": "510050%2612%",
    }
    SyntheticShortStockStrategyAnalysis().run(config)
"""

from dataIntegrator.modelService.option.OptionTradingStrategyManager.SyntheticStockStrategyBase import (
    SyntheticStockStrategyAnalysisBase
)


class SyntheticShortStockStrategyAnalysis(SyntheticStockStrategyAnalysisBase):
    """合成空头分析器(卖C买P, 净Delta≈-1)

    共享 SyntheticStockStrategyAnalysisBase 的配对/核心指标/情景/信号骨架,
    本类只声明策略标识与方向; 信号叙事=卖出收价偏离 + 融券成本对照。
    """

    # === 策略标识 ===
    STRATEGY_TYPE = 'SYNTHETIC_SHORT_STOCK'
    ANALYSIS_VERSION = 'v1'
    TABLE_TARGET = 'tb_option_trading_strategy_synthetic_short_stock'
    DIRECTION = -1  # -1 = 卖Call买Put(合成空头)

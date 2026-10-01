r"""
期权策略分析 工厂

用法：
    analyzer = OptionStrategyFactory.create('PROTECTIVE_PUT')
    analyzer.run(config)

新策略接入：
    @OptionStrategyFactory.register('COVERED_CALL')
    class CoveredCallStrategyAnalysis(OptionStrategyBase):
        ...
"""

from dataIntegrator.modelService.option.OptionTradingStrategyManager.ProtectivePutStrategyAnalysis import (
    ProtectivePutStrategyAnalysis
)
from dataIntegrator import CommonLib

logger = CommonLib.logger


class OptionStrategyFactory:
    """期权策略分析器工厂"""

    # 策略注册表: strategy_type -> 分析器类
    _registry = {}

    @classmethod
    def register(cls, strategy_type):
        """注册装饰器：@OptionStrategyFactory.register('COVERED_CALL')"""
        def decorator(analyzer_class):
            if strategy_type in cls._registry:
                logger.warning(f"Strategy '{strategy_type}' already registered, "
                               f"overwriting with {analyzer_class.__name__}")
            cls._registry[strategy_type] = analyzer_class
            return analyzer_class
        return decorator

    @classmethod
    def create(cls, strategy_type):
        """按 strategy_type 创建分析器实例"""
        analyzer_class = cls._registry.get(strategy_type)
        if analyzer_class is None:
            available = ', '.join(sorted(cls._registry.keys())) or '(none)'
            raise ValueError(f"Unknown strategy_type '{strategy_type}'. "
                             f"Available: {available}")
        logger.info(f"OptionStrategyFactory.create: {strategy_type} -> {analyzer_class.__name__}")
        return analyzer_class()

    @classmethod
    def list_strategies(cls):
        """列出已注册策略"""
        return dict(cls._registry)


# ================================================================
# 内置策略注册（新策略在此追加 import + register）
# ================================================================
OptionStrategyFactory._registry['PROTECTIVE_PUT'] = ProtectivePutStrategyAnalysis

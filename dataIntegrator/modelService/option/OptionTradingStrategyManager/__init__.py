"""OptionTradingStrategyManager 包初始化

同名冲突处理：
    本包目录与同级模块文件 OptionTradingStrategyManager.py 同名，
    Python 导入系统在同名时优先解析包目录，导致外部
    `from dataIntegrator.modelService.option.OptionTradingStrategyManager import OptionTradingStrategyManager`
    解析到本 __init__.py 而非模块文件中的类。

    此处通过 importlib 按文件路径加载同级模块文件并重导出类，
    保证外部导入语义不变（run_Report.py 等调用方无需改动）。
"""

import importlib.util
import os
import sys

_MODULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # option/
    "OptionTradingStrategyManager.py"
)
_MODULE_NAME = "dataIntegrator.modelService.option._option_trading_strategy_manager_impl"

_spec = importlib.util.spec_from_file_location(_MODULE_NAME, _MODULE_PATH)
_impl = importlib.util.module_from_spec(_spec)
sys.modules[_MODULE_NAME] = _impl
_spec.loader.exec_module(_impl)

OptionTradingStrategyManager = _impl.OptionTradingStrategyManager

__all__ = ["OptionTradingStrategyManager"]

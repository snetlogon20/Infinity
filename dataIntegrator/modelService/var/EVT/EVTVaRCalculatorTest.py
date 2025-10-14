import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import genextreme, genpareto, norm
from scipy.optimize import minimize
from typing import Tuple, Optional, Union
import warnings

from dataIntegrator.modelService.var.EVT.EVTVaRCalculator import EVTVaRCalculator

# 示例使用
if __name__ == "__main__":
    # 生成模拟收益率数据(厚尾分布)
    np.random.seed(42)
    n_points = 1000
    # 生成厚尾数据(混合正态分布和t分布)
    returns = 0.7 * np.random.normal(0, 0.01, n_points) + 0.3 * np.random.standard_t(3, n_points) * 0.02

    # 创建EVT VaR计算器
    evt_calculator = EVTVaRCalculator(returns, alpha=0.05)

    # 使用POT方法计算VaR
    var_pot, cvar, params = evt_calculator.pot_var()
    print("=== POT方法结果 ===")
    print(f"VaR(95%): {var_pot:.4f}")
    print(f"CVaR(95%): {cvar:.4f}")
    print(f"形状参数ξ: {params['xi']:.4f}")
    print(f"尺度参数β: {params['beta']:.4f}")
    print(f"阈值: {params['threshold']:.4f}")
    print(f"超过阈值样本数: {params['n_excess']}")

    # 使用Block Maxima方法计算VaR
    try:
        var_bm, params_bm = evt_calculator.block_maxima_var()
        print("\n=== Block Maxima方法结果 ===")
        print(f"VaR(95%): {var_bm:.4f}")
        print(f"形状参数ξ: {params_bm['xi']:.4f}")
    except Exception as e:
        print(f"\nBlock Maxima方法错误: {e}")

    # 历史VaR作为比较
    var_hist = evt_calculator.calculate_historical_var()
    print(f"\n=== 历史模拟法 ===")
    print(f"VaR(95%): {var_hist:.4f}")

    # 可视化分析
    print("\n生成分析图表...")
    evt_calculator.plot_pot_analysis()
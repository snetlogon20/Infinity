# 使用示例
from dataIntegrator.modelService.var.deltaNormal.VARCaculator import VARCalculator
import numpy as np


if __name__ == "__main__":
    # 示例：创建模拟收益率数据
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, 1000)  # 日均收益0.1%，波动率2%

    # 初始化VaR计算器
    var_calculator = VARCalculator(
        returns=returns,
        portfolio_value=1000000,  # 100万美元投资组合
        alpha=0.05  # 95%置信水平
    )

    # 计算不同方法的VaR
    # print("=== VaR计算结果比较 ===")
    # results = var_calculator.compare_methods(horizon=1)
    # for method, value in results.items():
    #     print(f"{method}: ${value:,.2f}")

    print("\n=== 单个方法计算 ===")
    print(f"Delta-Normal法（正态分布）: ${var_calculator.delta_normal_var(horizon=1, distribution='normal'):,.2f}")
    print(f"Delta-Normal法（t分布）: ${var_calculator.delta_normal_var(horizon=1, distribution='t'):,.2f}")
    # print(f"历史模拟法: ${var_calculator.historical_var(horizon=1):,.2f}")
    # print(f"蒙特卡罗模拟法: ${var_calculator.monte_carlo_var(horizon=1):,.2f}")

    # 可视化
    var_calculator.plot_var_distribution(method='historical', horizon=1)
import numpy as np
from scipy.stats import norm
from scipy.optimize import fsolve
import matplotlib.pyplot as plt

from dataIntegrator.modelService.derivatives.options.OptionImpliedSmileDeviation import OptionImpliedSmileDeviation


def test_case_1_calculate_implied_volatility_with_manual_program(C_market, S, K, T, r):

    optionImpliedSmileDeviation = OptionImpliedSmileDeviation()

    # 创建空列表存储S0值和对应的隐含波动率[2,5](@ref)
    S0_values = []
    iv_values = []

    # 循环计算S0从80到120的隐含波动率[1,3](@ref)
    for S0 in np.arange(10,181):  # 从80到120，包含120

        # 计算隐含波动率
        iv = optionImpliedSmileDeviation.calculate_implied_volatility_with_manual_program(C_market, S0, K, T, r)

        # 将当前S0和计算结果保存到列表中[2,5](@ref)
        S0_values.append(S0)
        iv_values.append(iv)

        # 打印每次循环的结果（可选）
        print(f"S0 = {S0}, 隐含波动率 = {iv:.4f} (即 {iv * 100:.2f}%)")

    # 绘制隐含波动率散点图
    plt.figure(figsize=(10, 6))
    plt.scatter(S0_values, iv_values, c='blue', s=30, alpha=0.7, edgecolors='black', linewidth=0.5)

    plt.title('隐含波动率散点图', fontsize=14)
    plt.xlabel('标的资产价格 (S0)', fontsize=12)
    plt.ylabel('隐含波动率', fontsize=12)
    plt.grid(True, alpha=0.3)

    # 添加特殊点标记（行权价处）
    plt.axvline(x=K, color='red', linestyle='--', alpha=0.7, label=f'行权价 K={K}')
    plt.legend()

    plt.tight_layout()
    plt.show()


def test_case_2_calculate_implied_volatility_with_vollib(C_market, S, K, T, r,  flag):

    optionImpliedSmileDeviation = OptionImpliedSmileDeviation()

    # K = 100  # 行权价
    # T = 0.25  # 到期时间（年）
    # r = 0.02  # 无风险利率
    # C_market = 5  # 看涨期权市场价格
    # flag = 'c'  # 看涨期权

    # 创建空列表存储S0值和对应的隐含波动率
    S0_values = []
    iv_values = []

    for S0 in np.arange(10, 181):  # 从80到120，包含120
        try:
            # 计算隐含波动率
            iv = optionImpliedSmileDeviation.calculate_implied_volatility_with_vollib(C_market, S0, K, T, r, flag)
            print(rf"S0:{S0}, iv:{iv}")

            # 将当前S0和计算结果保存到列表中
            S0_values.append(S0)
            iv_values.append(iv)

            # 打印每次循环的结果（可选）
            print(f"S0 = {S0}, 隐含波动率 = {iv:.4f} (即 {iv * 100:.2f}%)")

        except Exception as e:
            # 处理无法计算隐含波动率的情况（如期权价格超出合理范围）
            print(f"S0 = {S0}, 无法计算隐含波动率: {str(e)}")
            # 可以选择跳过该点或记录NaN值
            S0_values.append(S0)
            iv_values.append(np.nan)

    # 绘制隐含波动率曲线
    plt.figure(figsize=(12, 7))
    plt.plot(S0_values, iv_values, 'bo-', linewidth=2, markersize=6, label='隐含波动率')

    plt.title('隐含波动率与标的资产价格关系', fontsize=16, fontweight='bold')
    plt.xlabel('标的资产价格 (S0)', fontsize=12)
    plt.ylabel('隐含波动率', fontsize=12)
    plt.grid(True, alpha=0.3)

    # 添加特殊点标记（行权价处）
    plt.axvline(x=K, color='r', linestyle='--', alpha=0.7, label=f'行权价 K={K}')
    plt.axhline(y=0.2, color='g', linestyle=':', alpha=0.7, label='参考波动率 (20%)')

    # 添加图例
    plt.legend()

    # 美化图表
    plt.tight_layout()

    # 显示图表
    plt.show()

    # 可选：创建DataFrame以便进一步分析
    import pandas as pd

    iv_df = pd.DataFrame({
        '标的资产价格': S0_values,
        '隐含波动率': iv_values
    })
    print("\n隐含波动率数据摘要:")
    print(iv_df.describe())


if __name__ == "__main__":
    test_case_1_calculate_implied_volatility_with_manual_program(5.0, 100, 100, 0.25, 0.02)
    test_case_2_calculate_implied_volatility_with_vollib(5.0, 100, 100, 0.25, 0.02, 'c')
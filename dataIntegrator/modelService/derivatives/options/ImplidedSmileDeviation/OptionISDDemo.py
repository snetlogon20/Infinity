import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from py_vollib.black_scholes import implied_volatility
from scipy.stats import norm
import matplotlib as mpl


# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False


def create_implied_volatility_surface():
    """
    仿照 P408 Figure 17.3 作图
    创建隐含波动率曲面图
    """
    # 设置参数
    S = 1130.0  # 标的资产当前价格（根据图片中的spot price around 1,130）
    r = 0.02  # 无风险利率
    q = 0.01  # 股息率

    # 创建行权价范围（1000到1300，与图片一致）
    strike_prices = np.linspace(1000, 1300, 50)

    # 创建到期时间范围（1到8个月，与图片一致）
    maturities = np.linspace(1 / 12, 8 / 12, 30)  # 转换为年

    # 创建网格
    K_grid, T_grid = np.meshgrid(strike_prices, maturities)

    # 模拟隐含波动率曲面（基于常见的波动率微笑和期限结构）
    iv_surface = np.zeros_like(K_grid)

    for i in range(len(maturities)):
        for j in range(len(strike_prices)):
            K = strike_prices[j]
            T = maturities[i]

            # 创建波动率微笑效果：平价附近波动率最低，两边较高
            moneyness = (K - S) / S
            smile_effect = 0.15 + 0.1 * moneyness ** 2  # 微笑形状

            # 创建期限结构效果：短期波动率较高，长期较低且平坦
            term_structure = 0.05 * np.exp(-2 * T) + 0.1  # 指数衰减

            # 组合效果
            iv = smile_effect + term_structure

            iv_surface[i, j] = iv

    # 创建图表
    fig = plt.figure(figsize=(16, 12))
    ax = fig.add_subplot(111, projection='3d')

    # 绘制曲面
    surf = ax.plot_surface(K_grid, T_grid * 12, iv_surface * 100,  # T转换为月，iv转换为百分比
                           cmap='viridis', alpha=0.8,
                           edgecolor='none', antialiased=True)

    # 设置坐标轴标签
    ax.set_xlabel('Strike Price', fontsize=12, fontweight='bold', labelpad=10)
    ax.set_ylabel('Maturity (months)', fontsize=12, fontweight='bold', labelpad=10)
    ax.set_zlabel('Volatility (%)', fontsize=12, fontweight='bold', labelpad=10)

    # 设置标题
    ax.set_title('Implied Volatility Surface\nS&P 500 Stock Market Index Options',
                 fontsize=16, fontweight='bold', pad=20)

    # 设置坐标轴范围（与图片一致）
    ax.set_xlim(1000, 1300)
    ax.set_ylim(1, 8)
    ax.set_zlim(0, 30)

    # 添加颜色条
    fig.colorbar(surf, ax=ax, shrink=0.5, aspect=20, pad=0.1, label='Volatility (%)')

    # 添加网格
    ax.grid(True, alpha=0.3)

    # 设置视角
    ax.view_init(elev=25, azim=45)

    # 添加说明文本
    ax.text2D(0.05, 0.95, "ISDs seem out of line. This is illustrated in Figure 17.3,\n"
                          "which plots the surface for options on the S&P 500 stock market index.\n"
                          "At that time, the spot price was around 1,130.",
              transform=ax.transAxes, fontsize=10,
              bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

    # 添加中文注释（模仿图片中的手写注释）
    ax.text2D(0.02, 0.15, "价越高，越低\n期限越长，平坦",
              transform=ax.transAxes, fontsize=12, fontweight='bold',
              bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.7))

    plt.tight_layout()
    plt.show()

    return iv_surface


def calculate_real_iv_surface():
    """
    使用真实期权价格计算隐含波动率曲面（需要实际市场价格数据）
    这里提供一个框架，实际使用时需要接入市场数据
    """
    # 实际应用中，您需要：
    # 1. 获取不同行权价和到期日的期权市场价格
    # 2. 使用py_vollib计算每个点的隐含波动率
    # 3. 插值生成平滑的曲面

    print("实际应用时需要接入实时或历史期权市场数据")
    print("此函数需要根据具体数据源进行实现")


# 创建演示用的隐含波动率曲面
create_implied_volatility_surface()

# 如果需要基于真实数据计算（需要实际数据）
# calculate_real_iv_surface()
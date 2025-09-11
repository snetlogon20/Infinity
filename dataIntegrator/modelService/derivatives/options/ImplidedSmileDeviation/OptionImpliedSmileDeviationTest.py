import numpy as np
import matplotlib.pyplot as plt
from py_vollib.black_scholes import implied_volatility
import matplotlib as mpl
from dataIntegrator.modelService.derivatives.options.ImplidedSmileDeviation.OptionImpliedSmileDeviation import OptionImpliedSmileDeviation


def test_case_1_calculate_call_option_implied_volatility_with_manual_program(C_market, S, K, T, r):

    optionImpliedSmileDeviation = OptionImpliedSmileDeviation()

    # 创建空列表存储S0值和对应的隐含波动率[2,5](@ref)
    strike_prices = []
    iv_values = []

    for K in np.linspace(S * 0.7, S * 1.3, 50):  # 50个行权价点

        # 计算隐含波动率
        iv = optionImpliedSmileDeviation.calculate_call_option_implied_volatility_with_manual_program(C_market, S, K, T, r)

        # 将当前S0和计算结果保存到列表中[2,5](@ref)
        strike_prices.append(K)
        iv_values.append(iv)

        # 打印每次循环的结果（可选）
        print(f"K = {K:.2f}, 隐含波动率 = {iv:.4f} (即 {iv * 100:.2f}%)")

    # 绘制波动率微笑曲线
    plt.figure(figsize=(12, 8))
    plt.plot(strike_prices, iv_values, 'b-', linewidth=2, label='隐含波动率')

    # 添加平价点标记
    plt.axvline(x=S, color='red', linestyle='--', alpha=0.7,
                label=f'平价点 S={S}')
    plt.axhline(y=iv_values[len(iv_values) // 2], color='green', linestyle=':',
                alpha=0.7, label='平价波动率')

    plt.title('看涨期权波动率微笑曲线', fontsize=16)
    plt.xlabel('行权价 (K)', fontsize=14)
    plt.ylabel('隐含波动率', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.legend()

    # 添加区域标注
    plt.axvspan(min(strike_prices), S, alpha=0.1, color='red', label='价外Call')
    plt.axvspan(S, max(strike_prices), alpha=0.1, color='blue', label='价内Call')

    plt.tight_layout()
    plt.show()

def test_case_2_calculate_put_option_implied_volatility_with_manual_program(C_market, S, K, T, r):
    """
    计算并绘制看跌期权的波动率微笑曲线

    参数:
    P_market: 看跌期权的市场价格
    S: 标的资产当前价格 (固定值)
    T: 到期时间
    r: 无风险利率
    """

    optionImpliedSmileDeviation = OptionImpliedSmileDeviation()

    # 创建空列表存储S0值和对应的隐含波动率[2,5](@ref)
    strike_prices = []
    iv_values = []

    # 循环计算S0从80到120的隐含波动率[1,3](@ref)
    for K in np.linspace(S * 0.7, S * 1.3, 50):

        # 计算隐含波动率
        iv = optionImpliedSmileDeviation.calculate_put_option_implied_volatility_with_manual_program(C_market, S, K, T, r)

        # 将当前S0和计算结果保存到列表中[2,5](@ref)
        strike_prices.append(K)
        iv_values.append(iv)

        # 打印每次循环的结果（可选）
        print(f"K = {K:.2f}, Put隐含波动率 = {iv:.4f} (即 {iv * 100:.2f}%)")

    # 绘制波动率微笑曲线 - 按照您提供的图片样式
    plt.figure(figsize=(14, 8))

    # 绘制看跌期权IV曲线（红色虚线）
    plt.plot(strike_prices, np.array(iv_values) * 100, label='看跌期权 (Put) IV',
             color='red', linestyle='--', linewidth=2.5)

    # 添加平价点标记（绿色点线）
    plt.axvline(x=S, color='green', linestyle=':', linewidth=2,
                label=f'平价 (S = {S})', alpha=0.8)

    # 添加"At the Money"标注
    plt.text(S, max(np.array(iv_values) * 100) * 0.95, 'At the Money',
             ha='center', color='green', fontsize=12, fontweight='bold')

    # 设置坐标轴标签和标题
    plt.xlabel('行权价 (Strike Price)', fontsize=14, fontweight='bold')
    plt.ylabel('隐含波动率 (%)', fontsize=14, fontweight='bold')
    plt.title('看跌期权隐含波动率微笑 (Put Option Volatility Smile)',
              fontsize=16, fontweight='bold', pad=20)

    # 添加网格和图例
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=12)

    # 添加区域标注
    plt.axvspan(min(strike_prices), S, alpha=0.1, color='red', label='价内Put / 价外Call')
    plt.axvspan(S, max(strike_prices), alpha=0.1, color='blue', label='价外Put / 价内Call')

    # 设置坐标轴范围，模仿图片样式
    plt.xlim(min(strike_prices), max(strike_prices))
    plt.ylim(min(np.array(iv_values) * 100) * 0.98, max(np.array(iv_values) * 100) * 1.02)

    plt.tight_layout()
    plt.show()


def test_case_3_calculate_implied_volatility_with_vollib(option_market_price, S, K, T, r, flag):
    """
    计算并绘制隐含波动率微笑曲线

    参数:
    option_market_price: 期权市场价格
    S: 标的资产当前价格 (固定值)
    T: 到期时间
    r: 无风险利率
    flag: 期权类型 'c'=看涨, 'p'=看跌
    """
    optionImpliedSmileDeviation = OptionImpliedSmileDeviation()

    # 创建空列表存储行权价和对应的隐含波动率
    strike_prices = []
    iv_values = []

    # 正确的循环：行权价围绕标的资产价格变化（从70%到130%）
    K_range = np.linspace(S * 0.7, S * 1.3, 50)

    for K in K_range:
        try:
            # 计算隐含波动率
            iv = optionImpliedSmileDeviation.calculate_implied_volatility_with_vollib(
                option_market_price, S, K, T, r, flag
            )

            # 将当前K和计算结果保存到列表中
            strike_prices.append(K)
            iv_values.append(iv)

            # 打印每次循环的结果
            print(f"K = {K:.2f}, 隐含波动率 = {iv:.4f} (即 {iv * 100:.2f}%)")

        except Exception as e:
            # 处理无法计算隐含波动率的情况
            print(f"K = {K:.2f}, 无法计算隐含波动率: {str(e)}")
            strike_prices.append(K)
            iv_values.append(np.nan)

    # 在绘图前验证数组长度
    print(f"strike_prices 长度: {len(strike_prices)}")
    print(f"iv_values 长度: {len(iv_values)}")

    # 确保长度一致
    assert len(strike_prices) == len(
        iv_values), f"维度不匹配: strike_prices={len(strike_prices)}, iv_values={len(iv_values)}"

    # 绘制隐含波动率微笑曲线
    plt.figure(figsize=(14, 8))

    # 根据期权类型选择颜色和标签
    if flag == 'c':
        color = 'blue'
        line_style = '-'
        option_type = '看涨期权'
    else:
        color = 'red'
        line_style = '--'
        option_type = '看跌期权'

    plt.plot(strike_prices, iv_values, color=color, linestyle=line_style,
             linewidth=2.5, label=f'{option_type} IV')

    # 添加平价点标记
    plt.axvline(x=S, color='green', linestyle=':', linewidth=2,
                label=f'平价点 (S = {S})', alpha=0.8)

    # 添加"At the Money"标注
    max_iv = np.nanmax(iv_values)
    plt.text(S, max_iv * 0.95, 'At the Money', ha='center',
             color='green', fontsize=12, fontweight='bold')

    # 设置坐标轴标签和标题
    plt.xlabel('行权价 (Strike Price, K)', fontsize=14, fontweight='bold')
    plt.ylabel('隐含波动率', fontsize=14, fontweight='bold')
    plt.title(f'{option_type}隐含波动率微笑 (Volatility Smile)',
              fontsize=16, fontweight='bold', pad=20)

    # 添加网格和图例
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=12)

    # 添加区域背景色标注
    plt.axvspan(min(strike_prices), S, alpha=0.1, color='red',
                label='价内Put/价外Call' if flag == 'p' else '价外Call')
    plt.axvspan(S, max(strike_prices), alpha=0.1, color='blue',
                label='价外Put/价内Call' if flag == 'p' else '价内Call')

    plt.tight_layout()
    plt.show()

    # 创建DataFrame以便进一步分析
    import pandas as pd
    iv_df = pd.DataFrame({
        '行权价': strike_prices,
        '隐含波动率': iv_values
    })

    print(f"\n{option_type}隐含波动率数据摘要:")
    print(iv_df.describe())

    return strike_prices, iv_values

def test_case_0_calculate_implied_volatility_demo():
    """
    根据行权价、IV和BS公式，计算出看涨期权的理论市场价格
    遍历strike price, 使用py_vollib从"市场价格"中反推隐含波动率
    """

    # 设置全局样式，让图表更加饱满
    plt.style.use('default')
    mpl.rcParams['figure.figsize'] = (16, 10)  # 更大的画布尺寸
    mpl.rcParams['font.size'] = 14  # 更大的字体
    mpl.rcParams['axes.linewidth'] = 1.5  # 更粗的轴线
    mpl.rcParams['lines.linewidth'] = 3  # 更粗的线条

    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False

    # 1. 定义基本参数
    S = 100.0  # 标的资产当前价格
    T = 0.1  # 到期时间（年），例如1.5个月
    r = 0.01  # 无风险利率
    q = 0.00  # 股息率

    # 2. 创建一个行权价范围（围绕当前价格S）
    strike_prices = np.linspace(S * 0.7, S * 1.3, 100)  # 增加数据点数量，使曲线更平滑
    print(rf"strike_prices:{strike_prices}")

    # 3. 为了演示，我们人为构造一个"波动率微笑"的市场价格
    atm_iv = 0.20
    implied_vols = atm_iv + 0.05 * ((strike_prices - S) / S) ** 2
    print(rf"implied_vols:{implied_vols}")

    # 4. 根据行权价、IV和BS公式，计算出看涨期权的理论市场价格
    call_prices = []
    for K, iv in zip(strike_prices, implied_vols):
        d1 = (np.log(S / K) + (r - q + iv ** 2 / 2) * T) / (iv * np.sqrt(T))
        d2 = d1 - iv * np.sqrt(T)
        from scipy.stats import norm

        call_price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        call_prices.append(call_price)
    call_prices = np.array(call_prices)
    print(rf"call_prices:{call_prices}")

    # 5. 使用py_vollib从"市场价格"中反推隐含波动率
    calculated_ivs_call = []
    calculated_ivs_put = []

    for i, K in enumerate(strike_prices):
        try:
            iv_calc_call = implied_volatility.implied_volatility(
                call_prices[i], S, K, T, r, 'c'
            )
            calculated_ivs_call.append(iv_calc_call)
        except:
            calculated_ivs_call.append(np.nan)

        try:
            put_price = call_prices[i] - S * np.exp(-q * T) + K * np.exp(-r * T)
            iv_calc_put = implied_volatility.implied_volatility(
                put_price, S, K, T, r, 'p'
            )
            calculated_ivs_put.append(iv_calc_put)
        except:
            calculated_ivs_put.append(np.nan)

    calculated_ivs_call = np.array(calculated_ivs_call)
    calculated_ivs_put = np.array(calculated_ivs_put)

    print(rf"calculated_ivs_call:{calculated_ivs_call}")
    print(rf"calculated_ivs_put:{calculated_ivs_put}")

    # 6. 创建图表 - 使用更饱满的布局
    fig, ax = plt.subplots(figsize=(18, 12))  # 进一步增大画布尺寸

    # 绘制主要曲线
    ax.plot(strike_prices, calculated_ivs_call * 100, label='看涨期权 (Call) IV',
            color='blue', linestyle='-', linewidth=3, marker='', alpha=0.9)
    ax.plot(strike_prices, calculated_ivs_put * 100, label='看跌期权 (Put) IV',
            color='red', linestyle='--', linewidth=3, marker='', alpha=0.9)

    # 添加平价线
    ax.axvline(x=S, color='green', linestyle=':', linewidth=3, alpha=0.8, label=f'平价 (S = {S})')
    ax.text(S, np.nanmax(calculated_ivs_call * 100) * 0.97, 'At the Money',
            ha='center', color='green', fontsize=16, fontweight='bold')

    # 设置坐标轴范围，让图表更加饱满
    ax.set_xlim(strike_prices.min(), strike_prices.max())
    ax.set_ylim(np.nanmin(np.concatenate([calculated_ivs_call, calculated_ivs_put])) * 100 * 0.95,
                np.nanmax(np.concatenate([calculated_ivs_call, calculated_ivs_put])) * 100 * 1.05)

    # 添加区域标注
    ax.axvspan(strike_prices.min(), S, alpha=0.15, color='red', label='价内Put / 价外Call')
    ax.axvspan(S, strike_prices.max(), alpha=0.15, color='blue', label='价内Call / 价外Put')

    # 设置标签和标题
    ax.set_xlabel('行权价 (Strike Price)', fontsize=18, fontweight='bold')
    ax.set_ylabel('隐含波动率 (%)', fontsize=18, fontweight='bold')
    ax.set_title('期权隐含波动率微笑 (Volatility Smile)\nCall vs. Put',
                 fontsize=22, fontweight='bold', pad=20)

    # 美化网格和图例
    ax.grid(True, linestyle='--', alpha=0.7, linewidth=1.2)
    ax.legend(loc='upper center', fontsize=16, framealpha=0.9,
              bbox_to_anchor=(0.5, -0.1), ncol=4)

    # 调整刻度标签大小
    ax.tick_params(axis='both', which='major', labelsize=14)

    # 使用tight_layout确保所有元素都能显示，并调整边距
    plt.tight_layout(pad=3.0)

    # 如果需要保存为高清图片
    # plt.savefig('volatility_smile_fullscreen.png', dpi=300, bbox_inches='tight')

    plt.show()

if __name__ == "__main__":
    # test_case_1_calculate_call_option_implied_volatility_with_manual_program(5.0, 100, 100, 0.25, 0.02)
    # test_case_2_calculate_put_option_implied_volatility_with_manual_program(5.0, 100, 100, 0.25, 0.02)

    test_case_3_calculate_implied_volatility_with_vollib(5.0, 100, 100, 0.25, 0.02, 'c')
    test_case_3_calculate_implied_volatility_with_vollib(5.0, 100, 100, 0.25, 0.02, 'p')
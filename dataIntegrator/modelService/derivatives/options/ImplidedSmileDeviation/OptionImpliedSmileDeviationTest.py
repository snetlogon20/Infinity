import numpy as np
import matplotlib.pyplot as plt
from py_vollib.black_scholes import implied_volatility
import matplotlib as mpl
from dataIntegrator.modelService.derivatives.options.ImplidedSmileDeviation.OptionImpliedSmileDeviation import OptionImpliedSmileDeviation

# === 全局中文字体配置（所有 test_case 生效） ===
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei', 'Noto Sans CJK SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号 '-' 显示为方框


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

def test_case_4_multi_date_smile_evolution():
    """
    多日隐含波动率微笑曲线演变 —— 专业交易员仪表盘

    三合一布局:
      Panel A (左上): 热力图 — X: moneyness (K/S), Y: trade_date, Color: IV%
                      交易台最核心的监控图，一眼看出偏斜变化和波动率聚集
      Panel B (右上): 选取代表性日期叠加曲线 — 时间渐变着色，观察曲线形态演变
      Panel C (底部):  关键指标时间序列 — ATM IV, 偏斜度(90% vs 110%), 微笑曲率
    """

    import matplotlib.gridspec as gridspec
    from matplotlib.colors import LinearSegmentedColormap
    import matplotlib.dates as mdates
    from datetime import datetime, timedelta

    # ============================================================
    # 1. 模拟30个交易日的微笑曲面数据
    #    模拟场景: 平稳 → 市场恐慌(vol spike + skew steepen) → 恢复
    # ============================================================
    np.random.seed(42)
    n_days = 30
    base_date = datetime(2026, 6, 1)
    dates = [base_date + timedelta(days=i) for i in range(n_days)]
    date_labels = [d.strftime("%m-%d") for d in dates]

    # 标的资产价格 — 微幅上行趋势
    S_values = 100 + np.cumsum(np.random.randn(n_days) * 0.5)

    # ATM隐含波动率 — 模拟"平稳→恐慌→恢复"
    atm_vol = np.zeros(n_days)
    for i in range(n_days):
        if i < 8:
            atm_vol[i] = 0.18 + np.random.randn() * 0.01          # 平稳期 ~18%
        elif i < 18:
            trend = (i - 8) / 10.0
            atm_vol[i] = 0.18 + trend * 0.17 + np.random.randn() * 0.015  # 恐慌爬升 → 35%
        else:
            decay = np.exp(-(i - 18) * 0.2)
            atm_vol[i] = 0.18 + 0.17 * decay + np.random.randn() * 0.01   # 恢复回落

    # 偏斜度 (90% IV - 110% IV) — 恐慌时偏斜加大
    skew = np.zeros(n_days)
    for i in range(n_days):
        if i < 8:
            skew[i] = -0.015 + np.random.randn() * 0.003
        elif i < 18:
            skew[i] = -0.015 - (i - 8) * 0.006 + np.random.randn() * 0.004  # 更负
        else:
            skew[i] = -0.015 - 0.06 * np.exp(-(i - 18) * 0.15) + np.random.randn() * 0.003

    # 微笑曲率 (ATM - avg(wing)) — 恐慌时曲率更大
    curvature = np.zeros(n_days)
    for i in range(n_days):
        if i < 8:
            curvature[i] = 0.008 + np.random.randn() * 0.002
        elif i < 18:
            curvature[i] = 0.008 + (i - 8) * 0.005 + np.random.randn() * 0.003
        else:
            curvature[i] = 0.008 + 0.05 * np.exp(-(i - 18) * 0.15) + np.random.randn() * 0.002

    # 生成完整的 IV 曲面
    moneyness_grid = np.linspace(0.85, 1.15, 60)  # 60个行权价点
    strike_grid = np.outer(S_values, moneyness_grid)

    iv_surface = np.zeros((n_days, len(moneyness_grid)))
    for i in range(n_days):
        # 二次微笑 + 线性偏斜
        for j, m in enumerate(moneyness_grid):
            smile_part = curvature[i] * (m - 1.0) ** 2 * 100
            skew_part = skew[i] * (m - 1.0) * 100
            iv_surface[i, j] = atm_vol[i] + smile_part + skew_part
            iv_surface[i, j] = max(0.05, min(0.80, iv_surface[i, j]))

    # ============================================================
    # 2. 专业仪表盘布局
    # ============================================================
    fig = plt.figure(figsize=(24, 16))
    gs = gridspec.GridSpec(2, 2, height_ratios=[1.1, 1], hspace=0.35, wspace=0.30,
                           left=0.06, right=0.98, top=0.94, bottom=0.06)

    ax_heatmap = fig.add_subplot(gs[0, 0])   # Panel A: 热力图
    ax_overlay = fig.add_subplot(gs[0, 1])   # Panel B: 选取日期叠加
    ax_metrics = fig.add_subplot(gs[1, :])   # Panel C: 关键指标时间序列

    # ---- 全局颜色 ----
    heat_cmap = plt.cm.viridis
    BULL_COLOR, BEAR_COLOR, ATM_COLOR = '#1a5276', '#c0392b', '#27ae60'

    # ============================================================
    # Panel A: 热力图 — 波动率微笑曲面随时间的演变
    # ============================================================
    im = ax_heatmap.pcolormesh(moneyness_grid, np.arange(n_days), iv_surface * 100,
                                cmap=heat_cmap, shading='auto', vmin=15, vmax=45)
    cbar = plt.colorbar(im, ax=ax_heatmap, shrink=0.82, pad=0.02)
    cbar.set_label('隐含波动率 (%)', fontsize=12, fontweight='bold')

    # 标注市场阶段
    ax_heatmap.axhline(y=7.5, color='white', linestyle='-', linewidth=1.5, alpha=0.6)
    ax_heatmap.axhline(y=18.5, color='white', linestyle='-', linewidth=1.5, alpha=0.6)
    ax_heatmap.text(1.155, 3.5, '平稳期', color='white', fontsize=11, fontweight='bold',
                    va='center', bbox=dict(boxstyle='round', facecolor='black', alpha=0.3))
    ax_heatmap.text(1.155, 13, '恐慌期', color='white', fontsize=11, fontweight='bold',
                    va='center', bbox=dict(boxstyle='round', facecolor='black', alpha=0.3))
    ax_heatmap.text(1.155, 24, '恢复期', color='white', fontsize=11, fontweight='bold',
                    va='center', bbox=dict(boxstyle='round', facecolor='black', alpha=0.3))

    # ATM线标注
    ax_heatmap.axvline(x=1.0, color='white', linestyle='--', linewidth=1.2, alpha=0.7)
    ax_heatmap.text(1.0, -1.5, 'ATM', color='white', fontsize=9, ha='center', va='bottom')

    ax_heatmap.set_yticks(np.arange(0, n_days, 3))
    ax_heatmap.set_yticklabels([date_labels[i] for i in range(0, n_days, 3)], fontsize=9)
    ax_heatmap.set_xticks([0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15])
    ax_heatmap.set_xticklabels(['0.85', '0.90', '0.95', '1.00', '1.05', '1.10', '1.15'], fontsize=9)
    ax_heatmap.set_xlabel('Moneyness (K/S)', fontsize=13, fontweight='bold')
    ax_heatmap.set_ylabel('交易日', fontsize=13, fontweight='bold')
    ax_heatmap.set_title('Panel A: 波动率微笑热力图 — IV vs Moneyness × 时间',
                         fontsize=14, fontweight='bold', pad=12)

    # ============================================================
    # Panel B: 选取代表性日期叠加曲线
    # ============================================================
    selected_indices = [0, 3, 6, 12, 16, 22, 28]
    colors = plt.cm.coolwarm(np.linspace(0.15, 0.85, len(selected_indices)))

    for idx, (di, c) in enumerate(zip(selected_indices, colors)):
        alpha_val = 0.55 + 0.45 * (idx / (len(selected_indices) - 1))
        lw = 1.5 + 2.0 * (idx / (len(selected_indices) - 1))
        ax_overlay.plot(moneyness_grid, iv_surface[di] * 100,
                        color=c, linewidth=lw, alpha=alpha_val,
                        label=f'{date_labels[di]} (ATM={atm_vol[di]*100:.1f}%)')

    ax_overlay.axvline(x=1.0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax_overlay.set_xlabel('Moneyness (K/S)', fontsize=13, fontweight='bold')
    ax_overlay.set_ylabel('隐含波动率 (%)', fontsize=13, fontweight='bold')
    ax_overlay.set_title('Panel B: 代表性日期微笑曲线叠加',
                         fontsize=14, fontweight='bold', pad=12)
    ax_overlay.legend(fontsize=8.5, loc='upper left', ncol=2, framealpha=0.8)
    ax_overlay.grid(True, linestyle='--', alpha=0.3)

    # 标注高波动和低波动日期
    max_vol_day = np.argmax(atm_vol)
    min_vol_day = np.argmin(atm_vol)
    ax_overlay.annotate(f'峰值 {date_labels[max_vol_day]}',
                        xy=(1.0, atm_vol[max_vol_day] * 100),
                        xytext=(1.08, atm_vol[max_vol_day] * 100 + 3),
                        arrowprops=dict(arrowstyle='->', color=BEAR_COLOR, lw=1.5),
                        fontsize=9, color=BEAR_COLOR, fontweight='bold')
    ax_overlay.annotate(f'低点 {date_labels[min_vol_day]}',
                        xy=(1.0, atm_vol[min_vol_day] * 100),
                        xytext=(1.08, atm_vol[min_vol_day] * 100 - 1),
                        arrowprops=dict(arrowstyle='->', color=BULL_COLOR, lw=1.5),
                        fontsize=9, color=BULL_COLOR, fontweight='bold')

    # ============================================================
    # Panel C: 关键微笑指标时间序列
    # ============================================================
    ax_atm = ax_metrics
    ax_skew = ax_metrics.twinx()

    # ATM IV 填充区域 + 线
    ax_atm.fill_between(np.arange(n_days), atm_vol * 100, alpha=0.15, color=BULL_COLOR)
    ax_atm.plot(np.arange(n_days), atm_vol * 100,
                color=BULL_COLOR, linewidth=2.5, marker='o', markersize=4,
                label='ATM 隐含波动率 (%)', zorder=5)

    # 偏斜度 (右轴) — 正值越大越偏斜
    skew_plot = -skew * 100  # 转正以便直观: 正值=恐慌偏斜
    ax_skew.fill_between(np.arange(n_days), skew_plot, alpha=0.12, color=BEAR_COLOR)
    ax_skew.plot(np.arange(n_days), skew_plot,
                 color=BEAR_COLOR, linewidth=2.5, marker='s', markersize=4,
                 linestyle='--', label='偏斜度 (90%-110% IV差, %)', zorder=4)

    # 曲率标注
    ax_skew.plot(np.arange(n_days), curvature * 100 * 5,
                 color='#e67e22', linewidth=1.8, marker='^', markersize=3,
                 linestyle=':', label='曲率指标 (×5)', zorder=3, alpha=0.7)

    # X轴标注
    ax_atm.set_xticks(np.arange(0, n_days, 3))
    ax_atm.set_xticklabels([date_labels[i] for i in range(0, n_days, 3)], fontsize=9)
    ax_atm.set_xlabel('交易日', fontsize=13, fontweight='bold')

    # Y轴
    ax_atm.set_ylabel('ATM 隐含波动率 (%)', fontsize=12, fontweight='bold', color=BULL_COLOR)
    ax_skew.set_ylabel('偏斜度 / 曲率', fontsize=12, fontweight='bold', color=BEAR_COLOR)
    ax_atm.tick_params(axis='y', labelcolor=BULL_COLOR)
    ax_skew.tick_params(axis='y', labelcolor=BEAR_COLOR)

    # 市场阶段背景
    ax_atm.axvspan(-0.5, 7.5, alpha=0.06, color='green')
    ax_atm.axvspan(7.5, 18.5, alpha=0.06, color='red')
    ax_atm.axvspan(18.5, n_days - 0.5, alpha=0.06, color='green')
    ax_atm.text(3.5, ax_atm.get_ylim()[1] * 0.95, '平稳', ha='center', fontsize=10,
                color='green', fontweight='bold', alpha=0.6)
    ax_atm.text(13, ax_atm.get_ylim()[1] * 0.95, '恐慌', ha='center', fontsize=10,
                color='red', fontweight='bold', alpha=0.6)
    ax_atm.text(24, ax_atm.get_ylim()[1] * 0.95, '恢复', ha='center', fontsize=10,
                color='green', fontweight='bold', alpha=0.6)

    # 合并图例
    lines1, labels1 = ax_atm.get_legend_handles_labels()
    lines2, labels2 = ax_skew.get_legend_handles_labels()
    ax_atm.legend(lines1 + lines2, labels1 + labels2, loc='upper left',
                  fontsize=10, framealpha=0.8)

    ax_atm.set_title('Panel C: 微笑关键指标时间序列 — ATM IV / 偏斜度 / 曲率',
                     fontsize=14, fontweight='bold', pad=12)
    ax_atm.grid(True, linestyle='--', alpha=0.3)

    # ============================================================
    # 总标题 & 保存
    # ============================================================
    fig.suptitle('隐含波动率微笑曲线多日演变 — 专业交易员仪表盘\n'
                 '场景: 平稳期 → 市场恐慌(波动率飙升+偏斜加大) → 恢复回落',
                 fontsize=17, fontweight='bold', y=0.98)

    plt.savefig('ivol_smile_evolution_dashboard.png', dpi=200, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.show()
    print("图表已保存: ivol_smile_evolution_dashboard.png")
    print("\n交易员解读指南:")
    print("  Panel A (热力图): 颜色越亮 → IV越高。横看=微笑曲线形状, 竖看=某一moneyness的IV时序。")
    print("  Panel B (叠加):   观察曲线形态如何随时间平移和变形。恐慌期曲线整体上移+偏斜加剧。")
    print("  Panel C (指标):   ATM IV上升 → 市场焦虑; 偏斜度上升 → 尾部风险定价增加; 曲率上升 → 极端事件概率升高。")


if __name__ == "__main__":
    # test_case_1_calculate_call_option_implied_volatility_with_manual_program(5.0, 100, 100, 0.25, 0.02)
    # test_case_2_calculate_put_option_implied_volatility_with_manual_program(5.0, 100, 100, 0.25, 0.02)

    # test_case_3_calculate_implied_volatility_with_vollib(5.0, 100, 100, 0.25, 0.02, 'c')
    # test_case_3_calculate_implied_volatility_with_vollib(5.0, 100, 100, 0.25, 0.02, 'p')

    test_case_4_multi_date_smile_evolution()
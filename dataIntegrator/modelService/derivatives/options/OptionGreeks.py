import numpy as np
from scipy.stats import norm
from abc import ABC, abstractmethod
from dataIntegrator import CommonLib
import math
import pandas as pd
import matplotlib.pyplot as plt

logger = CommonLib.logger
commonLib = CommonLib()

class OptionGreeks(ABC):
    """希腊字母计算抽象基类"""

    def __init__(self, S, K, T, r, y, sigma, option_type='call'):
        """
        S: 标的资产现价
        K: 行权价
        T: 到期时间（年）
        r: 无风险利率
        y: 股息率
        sigma: 波动率
        option_type: 'call' 或 'put'
        """
        self.S = float(S)
        self.K = float(K)
        self.T = float(T)
        self.r = float(r)  # 无风险利率
        self.y = float(y)  # 股息率
        self.sigma = float(sigma)
        self.option_type = option_type.lower()

        self._validate_inputs()

    def _validate_inputs(self):
        if self.option_type not in ['call', 'put']:
            raise ValueError("option_type 必须是 'call' 或 'put'")
        if any(x <= 0 for x in [self.S, self.K, self.T, self.sigma]):
            raise ValueError("S, K, T, sigma 必须为正数")

    def _d1_d2(self):
        d1 = (np.log(self.S / self.K) + (self.r - self.y + 0.5 * self.sigma ** 2) * self.T) / (
                    self.sigma * np.sqrt(self.T))
        d2 = d1 - self.sigma * np.sqrt(self.T)
        return d1, d2

    @abstractmethod
    def calculate(self):
        pass

    def calculate_all_greeks(S, K, T, r, y, sigma, option_type='call'):
        """
        计算所有期权希腊值并返回字典（包含RhoYield）
        参数:
            S: 标的资产现价
            K: 行权价
            T: 到期时间（年）
            r: 无风险利率
            y: 股息率
            sigma: 波动率
            option_type: 'call' 或 'put' (默认'call')
        返回:
            dict: 包含所有希腊值的字典
        """
        option_type = option_type.lower()
        if option_type not in ['call', 'put']:
            raise ValueError("option_type 必须是 'call' 或 'put'")

        greeks = {
            'delta': Delta(S, K, T, r, y, sigma, option_type).calculate(),
            'gamma': Gamma(S, K, T, r, y, sigma).calculate(),
            'theta': Theta(S, K, T, r, y, sigma, option_type).calculate(),
            'vega': Vega(S, K, T, r, y, sigma).calculate(),
            'rho': Rho(S, K, T, r, y, sigma, option_type).calculate(),
            'rho_yield': RhoYield(S, K, T, r, y, sigma, option_type).calculate(),
            'parameters': {
                'S': S, 'K': K, 'T': T,
                'r': r, 'y': y, 'sigma': sigma,
                'option_type': option_type
            }
        }
        return greeks

    def print_greeks_information(greeks):
        """格式化输出希腊值"""
        logger.info("Option Greeks:")

        for key, value in greeks.items():
            if key == 'parameters':
                print(f"Option Type: {value['option_type']}")

        print(rf"Delta: {round(greeks['delta'], 6)}")
        print(rf"Gamma: {round(greeks['gamma'], 6)}")
        print(rf"Vega: {round(greeks['vega'], 6)}")
        print(rf"Rho: {round(greeks['rho'], 6)}")
        print(rf"Rho_yield: {round(greeks['rho_yield'], 6)}")
        print(rf"Theta: {round(greeks['theta'], 6)}")
        print("\n")

class Delta(OptionGreeks):
    """Delta计算"""

    def calculate(self):
        d1, _ = self._d1_d2()
        if self.option_type == 'call':
            normalDistribution_d1 = norm.cdf(d1)
            delta = math.exp(-1 * self.y * self.T) * normalDistribution_d1  # 仅用y调整
            return delta
        else:
            normalDistribution_d1 = norm.cdf(d1) - 1
            delta = math.exp(-1 * self.y * self.T) * normalDistribution_d1  # 仅用y调整
            return delta

class Gamma(OptionGreeks):
    """Gamma计算（call/put相同）"""

    def calculate(self):
        d1, _ = self._d1_d2()
        return norm.pdf(d1) / (self.S * self.sigma * np.sqrt(self.T))


class Theta(OptionGreeks):
    """Theta计算"""

    def calculate(self):
        d1, d2 = self._d1_d2()
        term1 = -(self.S * norm.pdf(d1) * self.sigma) / (2 * np.sqrt(self.T))

        if self.option_type == 'call':
            term2 = -self.r * self.K * np.exp(-(self.r - self.y) * self.T) * norm.cdf(d2)
            term3 = self.y * self.S * np.exp(-self.y * self.T) * norm.cdf(d1)
            return (term1 + term2 + term3) / 365  # 转换为每日theta
        else:
            term2 = self.r * self.K * np.exp(-(self.r - self.y) * self.T) * norm.cdf(-d2)
            term3 = -self.y * self.S * np.exp(-self.y * self.T) * norm.cdf(-d1)
            return (term1 + term2 + term3) / 365


class Vega(OptionGreeks):
    """Vega计算（call/put相同）"""

    def calculate(self):
        d1, _ = self._d1_d2()
        return self.S * np.sqrt(self.T) * norm.pdf(d1) * 0.01  # 波动率变化1%的影响


class Rho(OptionGreeks):
    """Rho（利率敏感度）计算"""

    def calculate(self):
        _, d2 = self._d1_d2()
        if self.option_type == 'call':
            return self.K * self.T * np.exp(-(self.r - self.y) * self.T) * norm.cdf(d2) * 0.01
        else:
            return -self.K * self.T * np.exp(-(self.r - self.y) * self.T) * norm.cdf(-d2) * 0.01


class RhoYield(OptionGreeks):
    """RhoYield（股息率敏感度）计算"""

    def calculate(self):
        d1, _ = self._d1_d2()
        if self.option_type == 'call':
            return -self.S * self.T * np.exp(-self.y * self.T) * norm.cdf(d1) * 0.01
        else:
            return self.S * self.T * np.exp(-self.y * self.T) * norm.cdf(-d1) * 0.01


def plot_greeks(greeks_df, plot_options):
    plot_axis = plot_options.get("plot_axis","K")
    plot_axis_label = plot_options.get("Strike Price","Strike Price")

    # 使用 pyplot 绘制折线图，将六个图放在一个画布上
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))

    # 为整个画布添加标题
    fig.suptitle(plot_options.get("plot_title",""), fontsize=16, fontweight='bold')

    # 将axes展平为一维数组，便于访问
    ax1, ax2, ax3, ax4, ax5, ax6 = axes.flatten()

    # 第1个子图：Delta
    ax1.plot(greeks_df[plot_axis], greeks_df['delta'], marker='o')
    ax1.set_title('Delta Value')
    ax1.set_xlabel(plot_axis_label)
    ax1.set_ylabel('Delta Values')
    ax1.grid(True)
    ax1.tick_params(axis='x', rotation=45)

    # 第2个子图：Gamma
    ax2.plot(greeks_df[plot_axis], greeks_df['gamma'], marker='o')
    ax2.set_title('Gamma Value')
    ax2.set_xlabel(plot_axis_label)
    ax2.set_ylabel('Gamma Values')
    ax2.grid(True)
    ax2.tick_params(axis='x', rotation=45)

    # 第3个子图：Vega
    ax3.plot(greeks_df[plot_axis], greeks_df['vega'], marker='o')
    ax3.set_title('Vega Value')
    ax3.set_xlabel(plot_axis_label)
    ax3.set_ylabel('Vega Values')
    ax3.grid(True)
    ax3.tick_params(axis='x', rotation=45)

    # 第4个子图：rho_rate
    ax4.plot(greeks_df[plot_axis], greeks_df['rho'], marker='o')
    ax4.set_title('Rho(rate) Value')
    ax4.set_xlabel(plot_axis_label)
    ax4.set_ylabel('Rho(rate) Values')
    ax4.grid(True)
    ax4.tick_params(axis='x', rotation=45)

    # 第5个子图：rho_yield
    ax5.plot(greeks_df[plot_axis], greeks_df['rho_yield'], marker='o')
    ax5.set_title('Rho(yield) Value')
    ax5.set_xlabel(plot_axis_label)
    ax5.set_ylabel('Rho(yield) Values')
    ax5.grid(True)
    ax5.tick_params(axis='x', rotation=45)

    # 第6个子图：theta
    ax6.plot(greeks_df[plot_axis], greeks_df['theta'], marker='o')
    ax6.set_title('Theta Value')
    ax6.set_xlabel(plot_axis_label)
    ax6.set_ylabel('Theta Values')
    ax6.grid(True)
    ax6.tick_params(axis='x', rotation=45)

    # 调整布局
    plt.tight_layout()
    plt.show()


def test_case1():
    params = {
        'S': 100,
        'K': 100,
        'T': 1,
        'r': 0.05,
        'y': 0.03,
        'sigma': 0.2
    }
    call_greeks = OptionGreeks.calculate_all_greeks(**params, option_type='call')
    OptionGreeks.print_greeks_information(call_greeks)
    put_greeks = OptionGreeks.calculate_all_greeks(**params, option_type='put')
    OptionGreeks.print_greeks_information(put_greeks)


def test_case2():
    short_term_params = {
        'S': 100,
        'K': 100,
        'T': 0.25,
        'r': 0.05,
        'y': 0.03,
        'sigma': 0.2
    }
    short_call = OptionGreeks.calculate_all_greeks(**short_term_params, option_type='call')
    OptionGreeks.print_greeks_information(short_call)

def test_case3(params_list):
    greeks_list = []
    for params in params_list:
        greeks = OptionGreeks.calculate_all_greeks(**params, option_type='call')
        OptionGreeks.print_greeks_information(greeks)

        flat_greeks = {
            'delta': greeks['delta'],
            'gamma': greeks['gamma'],
            'vega': greeks['vega'],
            'rho': greeks['rho'],
            'rho_yield': greeks['rho_yield'],
            'theta': greeks['theta'],

            'S': greeks['parameters']['S'],
            'K': greeks['parameters']['K'],
            'T': greeks['parameters']['T'],
            'r': greeks['parameters']['r'],
            'y': greeks['parameters']['y'],
            'sigma': greeks['parameters']['sigma'],
            'option_type': greeks['parameters']['option_type']
        }

        greeks_list.append(flat_greeks)
    greeks_df = pd.DataFrame(greeks_list)
    greeks_df.to_excel(rf"D:\workspace_python\infinity\dataIntegrator\data\outbound\GreeksAnalysis.xlsx")

    plot_options =  {
        'plot_axis': 'K',
        'plot_axis_label': 'Strike Price',
        'plot_title': 'Option Greeks Analysis - Strike Price'
    }
    plot_greeks(greeks_df, plot_options)


def test_case4(params_list):
    greeks_list = []
    for params in params_list:
        greeks = OptionGreeks.calculate_all_greeks(**params, option_type='call')
        OptionGreeks.print_greeks_information(greeks)

        flat_greeks = {
            'delta': greeks['delta'],
            'gamma': greeks['gamma'],
            'vega': greeks['vega'],
            'rho': greeks['rho'],
            'rho_yield': greeks['rho_yield'],
            'theta': greeks['theta'],

            'S': greeks['parameters']['S'],
            'K': greeks['parameters']['K'],
            'T': greeks['parameters']['T'],
            'r': greeks['parameters']['r'],
            'y': greeks['parameters']['y'],
            'sigma': greeks['parameters']['sigma'],
            'option_type': greeks['parameters']['option_type']
        }

        greeks_list.append(flat_greeks)
    greeks_df = pd.DataFrame(greeks_list)
    greeks_df.to_excel(rf"D:\workspace_python\infinity\dataIntegrator\data\outbound\GreeksAnalysis.xlsx")

    plot_options =  {
        'plot_axis': 'S',
        'plot_axis_label': 'Spot Price',
        'plot_title': 'Option Greeks Analysis - Spot Price'
    }
    plot_greeks(greeks_df, plot_options)


# 使用示例
if __name__ == "__main__":
    # 测试案例1（长期期权）
    # params = {
    #     'S': 100,
    #     'K': 100,
    #     'T': 1,
    #     'r': 0.05,
    #     'y': 0.03,
    #     'sigma': 0.2
    # }
    #test_case1()

    # 测试案例2（短期期权，P346 Table 14.1参数）
    # short_term_params = {
    #     'S': 100,
    #     'K': 100,
    #     'T': 0.25,
    #     'r': 0.05,
    #     'y': 0.03,
    #     'sigma': 0.2
    # }
    #test_case2()

    # 测试案例3（短期期权，P346 Table 14.1参数）
    # 遍历所有可能行权价格  90-100-110
    params_list = [
        {
            'S': 100,
            'K': K,
            'T': 0.25,
            'r': 0.05,
            'y': 0.03,
            'sigma': 0.2
        }
        for K in range(70, 131, 1)  # 从90到110（包含110），步长为1
    ]
    #test_case3(params_list)


    # 测试案例4（短期期权，P346 Table 14.1参数）
    # 遍历所有可能Spot价格  90-100-110
    params_list = [
        {
            'S': S,
            'K': 100,
            'T': 0.25,
            'r': 0.05,
            'y': 0.03,
            'sigma': 0.2
        }
        for S in range(70, 131, 1)  # 从90到110（包含110），步长为1
    ]
    #test_case4(params_list)


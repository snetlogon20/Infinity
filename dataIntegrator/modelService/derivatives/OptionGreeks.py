import numpy as np
from scipy.stats import norm
from abc import ABC, abstractmethod
from dataIntegrator import CommonLib
import math

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


# 使用示例
if __name__ == "__main__":
    # 测试案例1（长期期权）
    params = {
        'S': 100, 'K': 100, 'T': 1,
        'r': 0.05, 'y': 0.03, 'sigma': 0.2
    }
    call_greeks = calculate_all_greeks(**params, option_type='call')
    print_greeks_information(call_greeks)

    put_greeks = calculate_all_greeks(**params, option_type='put')
    print_greeks_information(put_greeks)

    # 测试案例2（短期期权，P346 Table 14.1参数）
    short_term_params = {
        'S': 100, 'K': 100, 'T': 0.25,
        'r': 0.05, 'y': 0.03, 'sigma': 0.2
    }
    short_call = calculate_all_greeks(**short_term_params, option_type='call')
    print_greeks_information(short_call)
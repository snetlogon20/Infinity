import numpy as np
from scipy.stats import norm
from abc import ABC, abstractmethod


class OptionGreeks(ABC):
    """希腊字母计算抽象基类"""

    def __init__(self, S, K, T, r, sigma, option_type='call'):
        """
        S: 标的资产现价
        K: 行权价
        T: 到期时间（年）
        r: 无风险利率
        sigma: 波动率
        option_type: 'call' 或 'put'
        """
        self.S = float(S)
        self.K = float(K)
        self.T = float(T)
        self.r = float(r)
        self.sigma = float(sigma)
        self.option_type = option_type.lower()

        self._validate_inputs()

    def _validate_inputs(self):
        if self.option_type not in ['call', 'put']:
            raise ValueError("option_type 必须是 'call' 或 'put'")
        if any(x <= 0 for x in [self.S, self.K, self.T, self.sigma]):
            raise ValueError("S, K, T, sigma 必须为正数")

    def _d1_d2(self):
        d1 = (np.log(self.S / self.K) + (self.r + 0.5 * self.sigma ** 2) * self.T) / (self.sigma * np.sqrt(self.T))
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
            return norm.cdf(d1)
        else:
            return norm.cdf(d1) - 1


class Gamma(OptionGreeks):
    """Gamma计算（call/put相同）"""

    def calculate(self):
        d1, _ = self._d1_d2()
        return norm.pdf(d1) / (self.S * self.sigma * np.sqrt(self.T))


class Theta(OptionGreeks):
    """Theta计算"""

    def calculate(self):
        d1, d2 = self._d1_d2()
        term1 = - (self.S * norm.pdf(d1) * self.sigma) / (2 * np.sqrt(self.T))

        if self.option_type == 'call':
            term2 = -self.r * self.K * np.exp(-self.r * self.T) * norm.cdf(d2)
            return (term1 + term2) / 365  # 转换为每日theta
        else:
            term2 = self.r * self.K * np.exp(-self.r * self.T) * norm.cdf(-d2)
            return (term1 + term2) / 365


class Vega(OptionGreeks):
    """Vega计算（call/put相同）"""

    def calculate(self):
        d1, _ = self._d1_d2()
        return self.S * np.sqrt(self.T) * norm.pdf(d1) * 0.01  # 波动率变化1%的影响


class Rho(OptionGreeks):
    """Rho计算"""

    def calculate(self):
        _, d2 = self._d1_d2()
        if self.option_type == 'call':
            return self.K * self.T * np.exp(-self.r * self.T) * norm.cdf(d2) * 0.01  # 利率变化1%的影响
        else:
            return -self.K * self.T * np.exp(-self.r * self.T) * norm.cdf(-d2) * 0.01


def calculate_all_greeks(S, K, T, r, sigma, option_type='call'):
    """
    计算所有期权希腊值并返回字典
    参数:
        S: 标的资产现价
        K: 行权价
        T: 到期时间（年）
        r: 无风险利率
        sigma: 波动率
        option_type: 'call' 或 'put' (默认'call')
    返回:
        dict: 包含所有希腊值的字典
    """
    # 参数校验
    option_type = option_type.lower()
    if option_type not in ['call', 'put']:
        raise ValueError("option_type 必须是 'call' 或 'put'")

    # 计算所有希腊值
    greeks = {
        'delta': Delta(S, K, T, r, sigma, option_type).calculate(),
        'gamma': Gamma(S, K, T, r, sigma).calculate(),  # gamma对call/put相同
        'theta': Theta(S, K, T, r, sigma, option_type).calculate(),
        'vega': Vega(S, K, T, r, sigma).calculate(),  # vega对call/put相同
        'rho': Rho(S, K, T, r, sigma, option_type).calculate()
    }

    # 添加计算参数信息
    greeks.update({
        'parameters': {
            'S': S,
            'K': K,
            'T': T,
            'r': r,
            'sigma': sigma,
            'option_type': option_type
        }
    })

    return greeks

# 使用示例
if __name__ == "__main__":
    # 测试数据
    params = {
        'S': 100,  # 标的现价
        'K': 100,  # 行权价
        'T': 1,  # 1年到期
        'r': 0.05,  # 5%无风险利率
        'sigma': 0.2  # 20%波动率
    }

    # 计算看涨期权
    call_greeks = calculate_all_greeks(**params, option_type='call')
    print("Call Option Greeks:")
    for key, value in call_greeks.items():
        if key != 'parameters':
            print(f"{key.capitalize():<6}: {value:.6f}")

    # 计算看跌期权
    put_greeks = calculate_all_greeks(**params, option_type='put')
    print("\nPut Option Greeks:")
    for key, value in put_greeks.items():
        if key != 'parameters':
            print(f"{key.capitalize():<6}: {value:.6f}")

    # 查看完整返回结构
    print("\n完整返回结构示例:")
    print(call_greeks)
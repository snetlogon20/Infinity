import numpy as np
from scipy.stats import norm
from scipy.optimize import fsolve
from py_vollib.black_scholes.implied_volatility import implied_volatility

class OptionImpliedSmileDeviation:
    # 定义Black-Scholes看涨期权定价函数
    def bs_call_price(self, S, K, T, r, sigma):
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        call_price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        return call_price


    # 定义计算隐含波动率的函数
    def calculate_implied_volatility_with_manual_program(self, C_market, S, K, T, r):
        # 定义一个误差函数，目标是使该函数值为0
        error_function = lambda sigma: self.bs_call_price(S, K, T, r, sigma) - C_market
        # 使用fsolve求解误差函数为0时的sigma，提供初始猜测值0.2
        iv = fsolve(error_function, 0.2)[0]
        return iv

    # 利用 volli 计算，更为精确
    def calculate_implied_volatility_with_vollib(self, C_market, S, K, T, r, flag):
        iv = implied_volatility(C_market, S, K, T, r, flag)
        return iv
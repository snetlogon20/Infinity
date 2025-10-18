import numpy as np
import pandas as pd
from scipy.stats import norm, t
import matplotlib.pyplot as plt
from typing import Union, Optional, List


class VARCalculator:
    """
    计算投资组合风险价值(VaR)的类
    支持Delta-Normal法、历史模拟法和蒙特卡罗模拟法
    """

    def __init__(self, returns: Union[pd.Series, np.ndarray],
                 portfolio_value: float = 1.0,
                 alpha: float = 0.05):
        """
        初始化VaR计算器

        参数:
            returns: 资产或投资组合的历史收益率序列
            portfolio_value: 投资组合价值，默认为1.0（返回百分比VaR）
            alpha: 显著性水平（1-置信水平），默认为0.05（95%置信水平）
        """
        self.returns = np.array(returns)
        self.portfolio_value = portfolio_value
        self.alpha = alpha
        self.mean = np.mean(self.returns)
        self.std = np.std(self.returns)

    def delta_normal_var(self, horizon: int = 1, distribution: str = 'normal') -> float:
        """
        Delta-Normal法计算VaR（参数法）

        参数:
            horizon: 时间范围（天数），默认为1天
            distribution: 分布假设，'normal'（正态分布）或't'（t分布）

        返回:
            VaR值（若portfolio_value不为None则返回绝对金额，否则返回百分比）
        """
        # 调整时间范围
        mean_horizon = self.mean * horizon
        std_horizon = self.std * np.sqrt(horizon)

        if distribution == 'normal':
            # 正态分布假设
            z_score = norm.ppf(self.alpha)
            var_percentile = mean_horizon + z_score * std_horizon
        elif distribution == 't':
            # t分布假设（考虑肥尾效应）
            # 使用最大似然估计拟合t分布
            df, loc, scale = t.fit(self.returns)
            t_score = t.ppf(self.alpha, df, loc, scale)
            var_percentile = t_score * std_horizon
        else:
            raise ValueError("分布类型必须是'normal'或't'")

        # 转换为绝对金额（如果提供了投资组合价值）
        if self.portfolio_value != 1.0:
            return -self.portfolio_value * var_percentile
        else:
            return -var_percentile

    # def historical_var(self, horizon: int = 1) -> float:
    #     """
    #     历史模拟法计算VaR[1,5](@ref)
    #
    #     参数:
    #         horizon: 时间范围（天数），默认为1天
    #
    #     返回:
    #         VaR值
    #     """
    #     # 计算时间范围内的累积收益率（如果horizon>1）
    #     if horizon > 1:
    #         # 使用滚动窗口计算多日收益[1](@ref)
    #         rolling_returns = []
    #         for i in range(len(self.returns) - horizon + 1):
    #             cumulative_return = np.prod(1 + self.returns[i:i + horizon]) - 1
    #             rolling_returns.append(cumulative_return)
    #         returns_array = np.array(rolling_returns)
    #     else:
    #         returns_array = self.returns
    #
    #     # 计算VaR（负号表示损失）
    #     var_percentile = np.percentile(returns_array, self.alpha * 100)
    #
    #     if self.portfolio_value != 1.0:
    #         return -self.portfolio_value * var_percentile
    #     else:
    #         return -var_percentile
    #
    # def monte_carlo_var(self, horizon: int = 1, num_simulations: int = 10000) -> float:
    #     """
    #     蒙特卡罗模拟法计算VaR[3](@ref)
    #
    #     参数:
    #         horizon: 时间范围（天数）
    #         num_simulations: 模拟次数，默认为10000
    #
    #     返回:
    #         VaR值
    #     """
    #     # 生成随机收益率路径（基于历史均值和波动率）
    #     simulated_returns = []
    #     for _ in range(num_simulations):
    #         # 模拟未来horizon天的收益率路径
    #         daily_returns = np.random.normal(self.mean, self.std, horizon)
    #         cumulative_return = np.prod(1 + daily_returns) - 1
    #         simulated_returns.append(cumulative_return)
    #
    #     # 计算VaR
    #     var_percentile = np.percentile(simulated_returns, self.alpha * 100)
    #
    #     if self.portfolio_value != 1.0:
    #         return -self.portfolio_value * var_percentile
    #     else:
    #         return -var_percentile
    #
    # def calculate_es(self, method: str = 'historical', horizon: int = 1) -> float:
    #     """
    #     计算预期短缺（Expected Shortfall）/条件VaR（CVaR）[1](@ref)
    #
    #     参数:
    #         method: 计算方法，'historical'（历史模拟法）或'parametric'（参数法）
    #         horizon: 时间范围（天数）
    #
    #     返回:
    #         ES值
    #     """
    #     if method == 'historical':
    #         # 历史模拟法计算ES
    #         if horizon > 1:
    #             rolling_returns = []
    #             for i in range(len(self.returns) - horizon + 1):
    #                 cumulative_return = np.prod(1 + self.returns[i:i + horizon]) - 1
    #                 rolling_returns.append(cumulative_return)
    #             returns_array = np.array(rolling_returns)
    #         else:
    #             returns_array = self.returns
    #
    #         # 计算VaR阈值
    #         var_threshold = np.percentile(returns_array, self.alpha * 100)
    #
    #         # 计算超过VaR阈值的平均损失
    #         tail_returns = returns_array[returns_array <= var_threshold]
    #         es_percentile = tail_returns.mean()
    #
    #     elif method == 'parametric':
    #         # 参数法计算ES（正态分布假设）
    #         z_score = norm.ppf(self.alpha)
    #         es_z = norm.pdf(z_score) / self.alpha
    #         mean_horizon = self.mean * horizon
    #         std_horizon = self.std * np.sqrt(horizon)
    #         es_percentile = mean_horizon - es_z * std_horizon
    #     else:
    #         raise ValueError("计算方法必须是'historical'或'parametric'")
    #
    #     if self.portfolio_value != 1.0:
    #         return -self.portfolio_value * es_percentile
    #     else:
    #         return -es_percentile
    #
    # def compare_methods(self, horizon: int = 1) -> dict:
    #     """
    #     比较不同方法的VaR计算结果[2](@ref)
    #
    #     参数:
    #         horizon: 时间范围（天数）
    #
    #     返回:
    #         包含各种方法结果的字典
    #     """
    #     results = {
    #         'delta_normal_normal': self.delta_normal_var(horizon, 'normal'),
    #         'delta_normal_t': self.delta_normal_var(horizon, 't'),
    #         'historical': self.historical_var(horizon),
    #         'monte_carlo': self.monte_carlo_var(horizon),
    #         'es_historical': self.calculate_es('historical', horizon),
    #         'es_parametric': self.calculate_es('parametric', horizon)
    #     }
    #     return results

    def plot_var_distribution(self, method: str = 'historical', horizon: int = 1):
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False  # 正确显示负号

        """
        可视化收益率分布与VaR[1](@ref)

        参数:
            method: 使用方法
            horizon: 时间范围
        """
        plt.figure(figsize=(10, 6))

        var_value = self.delta_normal_var(horizon)
        if self.portfolio_value != 1.0:
            var_percent = var_value / self.portfolio_value
        else:
            var_percent = var_value

        # 生成正态分布曲线
        x = np.linspace(self.returns.min(), self.returns.max(), 100)
        y = norm.pdf(x, self.mean, self.std)
        plt.plot(x, y, 'b-', alpha=0.7)
        plt.axvline(x=-var_percent, color='red', linestyle='--',
                    label=f'VaR({100 * (1 - self.alpha)}%) = {var_percent:.4f}')

        plt.title(f'收益率分布与VaR ({method}方法)')
        plt.xlabel('收益率')
        plt.ylabel('密度')
        plt.legend()
        plt.grid(True)
        plt.show()



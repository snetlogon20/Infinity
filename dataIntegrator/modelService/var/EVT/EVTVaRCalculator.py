import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import genextreme, genpareto, norm
from scipy.optimize import minimize
from typing import Tuple, Optional, Union
import warnings


class EVTVaRCalculator:
    """
    基于极值理论(EVT)的风险价值(VaR)计算器
    支持POT(Peaks Over Threshold)方法和Block Maxima方法
    """

    def __init__(self, returns: Union[pd.Series, np.ndarray],
                 alpha: float = 0.05):
        """
        初始化EVT VaR计算器

        参数:
            returns: 收益率序列
            alpha: 显著性水平(1-置信水平)，默认为0.05(95%置信水平)
        """
        self.returns = np.array(returns)
        self.alpha = alpha
        self.losses = -self.returns  # 将收益率转换为损失

    def pot_var(self, threshold: Optional[float] = None,
                auto_threshold: bool = True,
                threshold_quantile: float = 0.90) -> Tuple[float, float, dict]:
        """
        POT(Peaks Over Threshold)方法计算VaR[1,4,6](@ref)

        参数:
            threshold: 阈值，超过该值的损失被用于建模
            auto_threshold: 是否自动选择阈值
            threshold_quantile: 当auto_threshold=True时，用于确定阈值的分位数

        返回:
            var: VaR值
            cvar: 条件VaR(Expected Shortfall)
            params: 拟合参数字典
        """
        # 自动选择阈值[1](@ref)
        if auto_threshold:
            threshold = np.percentile(self.losses, threshold_quantile * 100)

        if threshold is None:
            raise ValueError("必须提供阈值或设置auto_threshold=True")

        # 获取超过阈值的超额损失[4](@ref)
        excess_losses = self.losses[self.losses > threshold] - threshold
        n_excess = len(excess_losses)
        n_total = len(self.losses)

        if n_excess < 10:
            warnings.warn("超过阈值的样本数较少，结果可能不可靠")

        # 使用广义帕累托分布(GPD)拟合超额损失[1,6](@ref)
        def neg_log_likelihood(params):
            """最大似然估计的负对数似然函数"""
            xi, beta = params
            if beta <= 0:
                return 1e10

            # 防止xi接近0时数值不稳定
            if abs(xi) < 1e-6:
                # 当xi=0时，GPD退化为指数分布
                return n_excess * np.log(beta) + np.sum(excess_losses) / beta
            else:
                term = 1 + xi * excess_losses / beta
                if np.any(term <= 0):
                    return 1e10
                return n_excess * np.log(beta) + (1 + 1 / xi) * np.sum(np.log(term))

        # 初始参数猜测[6](@ref)
        initial_params = [0.1, np.std(excess_losses)]
        result = minimize(neg_log_likelihood, initial_params, method='L-BFGS-B',
                          bounds=[(-0.5, 0.5), (1e-6, None)])

        if not result.success:
            warnings.warn("GPD拟合未收敛，使用矩估计")
            # 使用矩估计作为备选[1](@ref)
            mean_excess = np.mean(excess_losses)
            var_excess = np.var(excess_losses)
            xi_me = 0.5 * (1 - (mean_excess ** 2) / var_excess)
            beta_me = 0.5 * mean_excess * (1 + (mean_excess ** 2) / var_excess)
            xi, beta = xi_me, beta_me
        else:
            xi, beta = result.x

        # 计算VaR[1,6](@ref)
        fu = n_excess / n_total  # 超过阈值的概率
        var = threshold + (beta / xi) * (((1 - self.alpha) / fu) ** (-xi) - 1)

        # 计算CVaR(Expected Shortfall)[6](@ref)
        if xi < 1:
            cvar = (var + beta - xi * threshold) / (1 - xi)
        else:
            # 当xi>=1时，CVaR不存在，使用近似值
            cvar = var * 1.1

        params = {
            'threshold': threshold,
            'xi': xi,  # 形状参数
            'beta': beta,  # 尺度参数
            'n_excess': n_excess,
            'fu': fu,
            'var': var,
            'cvar': cvar
        }

        return var, cvar, params

    def block_maxima_var(self, block_size: int = 21) -> Tuple[float, dict]:
        """
        Block Maxima方法计算VaR[4,6](@ref)
        将数据分块，取每个块的最大值，用广义极值分布(GEV)拟合

        参数:
            block_size: 块大小(交易日数)，默认为21(约1个月)

        返回:
            var: VaR值
            params: 拟合参数
        """
        n_blocks = len(self.losses) // block_size
        if n_blocks < 10:
            raise ValueError("块数量太少，请减小block_size")

        # 计算每个块的最大值[6](@ref)
        block_maxima = []
        for i in range(n_blocks):
            start_idx = i * block_size
            end_idx = min((i + 1) * block_size, len(self.losses))
            block_max = np.max(self.losses[start_idx:end_idx])
            block_maxima.append(block_max)

        # 使用广义极值分布(GEV)拟合[4](@ref)
        def neg_log_likelihood_gev(params):
            """GEV的负对数似然函数"""
            xi, mu, sigma = params
            if sigma <= 0:
                return 1e10

            z = (np.array(block_maxima) - mu) / sigma

            if abs(xi) < 1e-6:
                # Gumbel分布(xi=0)
                log_f = -np.log(sigma) - z - np.exp(-z)
            else:
                condition = 1 + xi * z > 0
                if not np.all(condition):
                    return 1e10
                log_f = -np.log(sigma) - (1 + 1 / xi) * np.log(1 + xi * z) - (1 + xi * z) ** (-1 / xi)

            return -np.sum(log_f)

        # 初始参数猜测
        initial_params = [0.1, np.mean(block_maxima), np.std(block_maxima)]
        result = minimize(neg_log_likelihood_gev, initial_params, method='L-BFGS-B',
                          bounds=[(-0.5, 0.5), (None, None), (1e-6, None)])

        if result.success:
            xi, mu, sigma = result.x
        else:
            # 使用矩估计
            mu, sigma = np.mean(block_maxima), np.std(block_maxima)
            xi = 0.1  # 默认值

        # 计算VaR[6](@ref)
        if abs(xi) < 1e-6:
            # Gumbel分布
            var = mu - sigma * np.log(-np.log(1 - self.alpha))
        else:
            var = mu + (sigma / xi) * ((-np.log(1 - self.alpha)) ** (-xi) - 1)

        params = {
            'xi': xi,
            'mu': mu,
            'sigma': sigma,
            'n_blocks': n_blocks,
            'block_size': block_size,
            'var': var
        }

        return var, params

    def calculate_historical_var(self) -> float:
        """历史模拟法计算VaR作为基准[2](@ref)"""
        return np.percentile(self.losses, (1 - self.alpha) * 100)

    def plot_pot_analysis(self, threshold: Optional[float] = None):
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False  # 正确显示负号

        """可视化POT分析结果[1,6](@ref)"""
        if threshold is None:
            threshold = np.percentile(self.losses, 90)

        var_pot, cvar, params = self.pot_var(threshold, auto_threshold=False)
        var_hist = self.calculate_historical_var()

        plt.figure(figsize=(15, 10))

        # 1. 损失分布与阈值
        plt.subplot(2, 2, 1)
        plt.hist(self.losses, bins=50, density=True, alpha=0.7, color='skyblue')
        plt.axvline(threshold, color='red', linestyle='--',
                    label=f'阈值 = {threshold:.4f}')
        plt.axvline(var_pot, color='darkred', linestyle='-',
                    label=f'POT VaR = {var_pot:.4f}')
        plt.axvline(var_hist, color='orange', linestyle='-',
                    label=f'历史VaR = {var_hist:.4f}')
        plt.xlabel('损失')
        plt.ylabel('密度')
        plt.title('损失分布与VaR比较')
        plt.legend()
        plt.grid(True, alpha=0.3)

        # 2. 超过阈值的超额损失
        plt.subplot(2, 2, 2)
        excess_losses = self.losses[self.losses > threshold] - threshold
        plt.hist(excess_losses, bins=30, density=True, alpha=0.7, color='lightcoral')
        x = np.linspace(0, np.max(excess_losses), 100)
        # 绘制拟合的GPD分布
        if params['xi'] == 0:
            y = (1 / params['beta']) * np.exp(-x / params['beta'])  # 指数分布
        else:
            y = (1 / params['beta']) * (1 + params['xi'] * x / params['beta']) ** (-1 / params['xi'] - 1)
        plt.plot(x, y, 'r-', linewidth=2, label='GPD拟合')
        plt.xlabel('超额损失')
        plt.ylabel('密度')
        plt.title('超额损失的GPD拟合')
        plt.legend()
        plt.grid(True, alpha=0.3)

        # 3. 平均超额图(用于阈值选择)[1](@ref)
        plt.subplot(2, 2, 3)
        thresholds = np.percentile(self.losses, range(70, 96))
        mean_excess = []
        for t in thresholds:
            excess = self.losses[self.losses > t] - t
            mean_excess.append(np.mean(excess) if len(excess) > 0 else 0)

        plt.plot(thresholds, mean_excess, 'bo-')
        plt.axvline(threshold, color='red', linestyle='--', label='选择阈值')
        plt.xlabel('阈值')
        plt.ylabel('平均超额损失')
        plt.title('平均超额图(阈值选择)')
        plt.legend()
        plt.grid(True, alpha=0.3)

        # 4. QQ图检验拟合优度[6](@ref)
        plt.subplot(2, 2, 4)
        excess_losses_sorted = np.sort(excess_losses)
        if params['xi'] == 0:
            theoretical_quantiles = -params['beta'] * np.log(1 - np.linspace(0, 1, len(excess_losses) + 2)[1:-1])
        else:
            theoretical_quantiles = params['beta'] / params['xi'] * (
                        (np.linspace(0, 1, len(excess_losses) + 2)[1:-1] ** (-params['xi'])) - 1)

        plt.scatter(theoretical_quantiles, excess_losses_sorted, alpha=0.7)
        min_val = min(theoretical_quantiles.min(), excess_losses_sorted.min())
        max_val = max(theoretical_quantiles.max(), excess_losses_sorted.max())
        plt.plot([min_val, max_val], [min_val, max_val], 'r--', alpha=0.8)
        plt.xlabel('理论分位数')
        plt.ylabel('样本分位数')
        plt.title('GPD拟合QQ图')
        plt.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()

        return params


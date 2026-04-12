import pandas as pd

from dataIntegrator import CommonLib
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
import numpy as np

logger = CommonLib.logger
commonLib = CommonLib()

class PortfolioAnalysis(TuShareService):

    def __init__(self):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="PortfolioVolatilityCalculator started")

    def calculate_portfolio_return_and_volatility(self, weight, mean, sigma, rho):
        n = len(weight)

        # 生成协方差矩阵
        cov_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i == j:
                    cov_matrix[i][j] = sigma[i] ** 2
                else:
                    cov_matrix[i][j] = rho[i][j] * sigma[i] * sigma[j]

        # 确保协方差矩阵是对称的
        cov_matrix = (cov_matrix + cov_matrix.T) / 2

        # 检查并修正协方差矩阵的正定性
        eigenvalues = np.linalg.eigvalsh(cov_matrix)
        if np.any(eigenvalues < 0):
            # 添加一个小的正则化项使矩阵正定
            min_eigenvalue = np.min(eigenvalues)
            if min_eigenvalue < 0:
                cov_matrix += (-min_eigenvalue + 1e-8) * np.eye(n)
                logger.warning(f"协方差矩阵不是正定的，已添加正则化项: {-min_eigenvalue + 1e-8}")

        # 计算投资组合收益
        portfolio_return = np.dot(weight, mean)
        # 计算投资组合方差
        portfolio_variance = np.dot(weight, np.dot(cov_matrix, weight))

        # 数值保护：确保方差非负
        if portfolio_variance < 0:
            portfolio_variance = abs(portfolio_variance)
            logger.warning(f"投资组合方差为负数，已取绝对值: {portfolio_variance}")

        # 计算投资组合波动率
        portfolio_volatility = np.sqrt(portfolio_variance)

        return portfolio_return, portfolio_volatility



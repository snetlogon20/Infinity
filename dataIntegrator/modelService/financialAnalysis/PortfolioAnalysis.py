import pandas as pd
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
import numpy as np

class PortfolioAnalysis(TuShareService):

    def __init__(self):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="PortfolioVolatilityCalculator started")

    def calculate_portfolio_return_and_volatility(self, weight, mean, sigma, rho):
        n = len(w)

        # 生成协方差矩阵
        cov_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i == j:
                    cov_matrix[i][j] = sigma[i] ** 2
                else:
                    cov_matrix[i][j] = rho[i][j] * sigma[i] * sigma[j]

        # 计算投资组合收益
        portfolio_return = np.dot(weight, mean)
        # 计算投资组合方差
        portfolio_variance = np.dot(weight, np.dot(cov_matrix, weight))
        # 计算投资组合波动率
        portfolio_volatility = np.sqrt(portfolio_variance)

        return portfolio_return, portfolio_volatility


if __name__ == "__main__":
    protfolioAnalysis = PortfolioAnalysis()

    # 示例值 P41, Example of Computing the risk of a portfolio
    print("given 2 products")
    w = np.array([0.6, 0.4])  # 权重
    u = np.array([0.00, 1])  # 预期收益率
    sigma = np.array([5, 9.95])  # 标准差
    rho = np.array([[1, 0.3], [0.3, 1]])  # 相关系数矩阵

    portfolio_return, portfolio_volatility = protfolioAnalysis.calculate_portfolio_return_and_volatility(w, u, sigma, rho)
    print(f"投资组合的波动率为: {portfolio_return}")
    print(f"投资组合的波动率为: {portfolio_volatility}")


    # 示例值
    print("given 5 products")
    w = np.array([0.1, 0.2, 0.3, 0.25, 0.15])  # 权重
    u = np.array([0.05, 0.1, 0.15, 0.2, 0.25])  # 预期收益率
    sigma = np.array([0.1, 0.2, 0.15, 0.25, 0.18])  # 标准差
    rho = np.array([[1, 0.3, 0.2, 0.1, 0.2],
                    [0.3, 1, 0.4, 0.3, 0.25],
                    [0.2, 0.4, 1, 0.2, 0.15],
                    [0.1, 0.3, 0.2, 1, 0.2],
                    [0.2, 0.25, 0.15, 0.2, 1]])  # 相关系数矩阵

    portfolio_return, portfolio_volatility = protfolioAnalysis.calculate_portfolio_return_and_volatility(w, u, sigma, rho)
    print(f"投资组合的波动率为: {portfolio_return}")
    print(f"投资组合的波动率为: {portfolio_volatility}")
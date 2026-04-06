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
        n = len(weight)

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



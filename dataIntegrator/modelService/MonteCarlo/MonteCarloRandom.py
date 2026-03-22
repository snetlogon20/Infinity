import math
import random

import pandas
import scipy.stats as stats
from matplotlib import pyplot as plt
import statistics
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.plotService.LinePlotManager import LinePlotManager
from dataIntegrator.utility.FileUtility import FileUtility


class MonteCarloRandom:
    def __init__(self):
        pass

    @classmethod
    def caculate_monte_carlo_single_line_normal_distribute(self, S, mu, sigma, t, times):
        x = []
        y = []
        x.append(0)
        y.append(S)

        for time in range(1, times):
            random_num = random.random()
            normsvin = stats.norm.ppf(random_num, 0, 1)

            sample = S * math.exp((mu - 0.5 * sigma * sigma) * t + sigma * math.sqrt(t) * normsvin)
            S = sample

            x.append(time)
            y.append(S)
        return x, y

    @classmethod
    def caculate_monte_carlo_single_line_lognormal_distribute(self, S, mu, sigma, t, times):
        x = []
        y = []
        x.append(0)
        y.append(S)

        for time in range(1, times):
            random_num = random.random()
            lognormsvin = stats.lognorm.ppf(random_num, 1)

            sample = S * math.exp((mu - 0.5 * sigma * sigma) * t + sigma * math.sqrt(t) * lognormsvin)
            S = sample

            x.append(time)
            y.append(S)
        return x, y

    @classmethod
    def caculate_monte_carlo_single_line_historical(cls, S, historical_returns, times):
        """历史收益率重采样模拟"""
        x, y = [0], [S]
        for _ in range(1, times):
            ret = random.choice(historical_returns)  # 随机选择历史收益率
            S *= (1 + ret)  # 应用收益率
            x.append(_)
            y.append(S)
        return x, y

    @classmethod
    def simulation_multi_series(cls, dataFrame, simulat_params):
        # 参数解析
        analysis_column = simulat_params["analysis_column"]
        init_value_col = simulat_params["init_value"]

        # 获取历史收益率（转换为小数）
        historical_returns = dataFrame[analysis_column].dropna().values / 100 # 将需要分析的字段转换为百分比

        # 统计指标计算
        stats = pandas.DataFrame({
            "Mean": [historical_returns.mean()],
            "Std_Dev": [historical_returns.std()],
            "Init_Value": [dataFrame[init_value_col].iloc[-1]]  # 使用最后一天的收盘价
        })

        # 模拟参数
        S = stats["Init_Value"][0]
        times = simulat_params["times"]
        series = simulat_params["series"]
        alpha = simulat_params["alpha"]
        dist_type = simulat_params["distribution_type"]

        # 结果存储
        all_lines = []
        final_values = []
        #plt.figure(figsize=(20, 8))

        # 模拟主循环
        for line in range(series):
            if line % 100 == 0:
                print(f"Processing {line + 1}/{series}...")

            # 选择分布类型
            if dist_type == "historical":
                x, y = cls.caculate_monte_carlo_single_line_historical(S, historical_returns, times)
            elif dist_type == "normal":
                mu = historical_returns.mean()
                sigma = historical_returns.std()
                t = 1 / 252  # 假设日数据
                x, y = cls.caculate_monte_carlo_single_line_normal_distribute(S, mu, sigma, t, times)
            elif dist_type == "lognormal":
                mu = historical_returns.mean()
                sigma = historical_returns.std()
                t = 1 / 252
                x, y = cls.caculate_monte_carlo_single_line_lognormal_distribute(S, mu, sigma, t, times)

            # 存储结果
            all_lines.extend(zip([line] * len(x), x, y))
            final_values.append(y[-1])
            #plt.plot(x, y, alpha=0.5)

        # 风险值计算
        final_values = sorted(final_values)
        var_index = int(alpha * series)
        var_lower_bound = final_values[var_index]

        # 计算上界VaR (1-alpha分位数)
        upper_alpha = 1 - alpha
        var_upper_index = int(upper_alpha * series)
        var_upper_bound = final_values[var_upper_index]
        # 计算均数和中位数
        average = sum(final_values) / len(final_values)
        median_value = statistics.median(final_values)

        return dataFrame, all_lines, stats, var_lower_bound, var_upper_bound, average, median_value



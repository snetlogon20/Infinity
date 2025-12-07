import math
import scipy.stats as stats
from scipy.stats import norm
from scipy.stats import shapiro
from scipy.stats import kstest
import numpy as np


class NormalDistribution:
    def __init__(self, mean, std_dev):
        self.mean = mean
        self.std_dev = std_dev

    ##############################
    # pdf/cdf/ppf
    ##############################
    def pdf(self, x, mean=0, std_dev=1):
        """计算正态分布的概率密度函数"""
        self.mean = mean
        self.std_dev = std_dev
        return (1 / (self.std_dev * math.sqrt(2 * math.pi))) * math.exp(-0.5 * ((x - self.mean) / self.std_dev) ** 2)

    def cdf(self, x, mean=0, std_dev=1):
        """计算正态分布的累积分布函数(Cumulative Distribution Function): Percentage -> Z"""
        self.mean = mean
        self.std_dev = std_dev
        return norm.cdf(x, loc=mean, scale=std_dev)

    def ppf(self, q, mean=0, std_dev=1):
        """计算正态分布的分位数（Percent Point Function, 逆CDF）: Percentage -> Z"""
        self.mean = mean
        self.std_dev = std_dev
        return norm.ppf(q, loc=self.mean, scale=self.std_dev)

    def set_data(self, data):
        self.data = np.array(data)  # 确保数据是一个numpy数组

    ##############################
    # 参数估计， 区间估计
    ##############################
    def parameter_estimation_with_data(self, data, alpha=0.05):
        # 样本的均值和标准差
        sample_mean = np.mean(data)
        sample_std = np.std(data, ddof=1)
        # 样本大小
        n = len(data)

        # 计算置信区间
        confidence_interval = self.parameter_estimation_with_value(alpha, n, sample_mean, sample_std)

        return confidence_interval

    # 带有自由度的参数估计
    def parameter_estimation_with_value(self, alpha, n, sample_mean, sample_std):
        # 自由度
        df = n - 1
        confidence_interval = stats.t.interval(1 - alpha, df, loc=sample_mean, scale=sample_std / np.sqrt(n))
        print(f"置信区间: {confidence_interval}")
        return confidence_interval

    # 仅有均值，没有自由度的, 基于指数的参数估计
    def calculate_confidence_range(self, value, confidence_level, mean, sigma, is_exponent=True):
        # Calculate the z-score for the given confidence level
        alpha = 1 - confidence_level
        z_score = stats.norm.ppf(1 - alpha / 2)  # Two-tailed confidence interval

        # Calculate the margin of error
        margin_of_error = z_score * sigma

        # Calculate the confidence interval range
        if (is_exponent == True):

            lower_bound = value * np.exp((mean - margin_of_error))
            upper_bound = value * np.exp((mean + margin_of_error))
        else:
            # Calculate the confidence interval range
            lower_bound = value * (mean - margin_of_error)
            upper_bound = value * (mean + margin_of_error)

        return lower_bound, upper_bound

    ##############################
    # 假设分析 Hyperthesis Analysis
    ##############################
    def hyperthesis_test_with_np_data(self, mu, alpha=0.05):
        sample_mean = np.mean(self.data)
        sample_std = np.std(self.data, ddof=1)
        n = len(self.data)

        p_value, reject_null, comment = self.hyperthesis_test_with_value(alpha, mu, n, sample_mean, sample_std)
        return p_value, reject_null, comment

    ##############################
    # 回测 back test
    ##############################
    def hyperthesis_test_with_value(self, alpha, mu, n, sample_mean, sample_std):
        z_score = (sample_mean - mu) / (sample_std / np.sqrt(n))
        p = stats.norm.cdf(abs(z_score))
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))  # 双尾检验
        reject_null = p_value < alpha
        if reject_null:
            comment = "Hypothesis with Normal Distribution: 拒绝原假设，数据和假设有显著差异"
        else:
            comment = "Hypothesis with Normal Distribution: 接受原假设，数据和假设没有显著差异"
        return p_value, reject_null, comment

    def backtest_z_value_with_data(self, data, alpha):
        # Compute sample mean and std
        sample_mean = np.mean(data)
        sample_std = np.std(data, ddof=1)

        # Calculate the Z-value for each data point
        z_scores = (data - sample_mean) / sample_std

        # Calculate the critical z-value for two-tailed test (95% confidence)
        z_critical = stats.norm.ppf(1 - alpha / 2)  # for 95% confidence, z_critical ≈ ±1.96

        # Compare each z-score with the critical value
        out_of_bounds = np.abs(z_scores) > z_critical
        out_of_bounds_count = 0
        within_bounds_count = 0

        # Print the results
        for i, z in enumerate(z_scores):
            result = "Out of bounds" if out_of_bounds[i] else "Within bounds"

            if out_of_bounds[i]:
                out_of_bounds_count += 1
            else:
                within_bounds_count += 1

            #print(f"Data point {data[i]} -> Z-value: {z:.3f}, {result}")

        # Return the Z-scores
        return z_scores,within_bounds_count, out_of_bounds_count

    # 根据 x(exception number) + exception percentage + T(总数) 计算 z
    def backtest_z_value_with_value(self, x, p, T, alpha):
        caculated_z = (x- p*T) / (p * (1 - p) * T)**0.5
        expected_z = self.ppf(1 - alpha)

        if abs(caculated_z) > abs(expected_z):
            test_result = False
            result = "False, and reject the hypothesis"
        else:
            test_result = True
            result = "True, and cannot reject the hypothesis"

        return caculated_z, expected_z, test_result, result

    ##############################
    # 正态性检验
    ##############################
    # 正态性检验方法 K-S检验：Kolmogorov-Smirnov test
    def if_normal_distribution_with_K_S(self, data, mean, std_dev):
        # Perform K-S test
        result = kstest(data, 'norm', args=(mean, std_dev))  # Compare data against a normal distribution with mean=0, std=1

        # Display the result
        print("K-S Test Statistic:", result.statistic)
        print("P-value:", result.pvalue)
        pvalue = result.pvalue
        # Interpretation
        if result.pvalue > 0.05:
            result_boolean = True
            result = "Fail to reject the null hypothesis: Data follows a normal distribution."
        else:
            result_boolean = False
            result = "Reject the null hypothesis: Data does not follow a normal distribution."

        return result_boolean, pvalue, result

    # 正态性检验方法 夏皮洛-威尔克检验：Shapiro—Wilk test test
    def if_normal_distribution_with_ShapiroWilk(self, data):
        stat, p_value = shapiro(data)

        print(f'Statistic: {stat}, p-value: {p_value}')

        # Check if the dataset follows a normal distribution
        if p_value > 0.05:
            result_boolean = True
            result = "The dataset is likely normally distributed."
        else:
            result_boolean = False
            result = "The dataset is not likely normally distributed."

        return result_boolean, p_value, result

    def if_normal_distribution_bera_with_JB(self, data, significance_level=0.05):
        jb_statistic, p_value = stats.jarque_bera(data)

        # 输出检验结果
        print(f"Jarque-Bera Statistic: {jb_statistic}")
        print(f"P-Value: {p_value}")

        alpha = significance_level  # 显著性水平设置为5%
        if p_value < alpha:
            result_boolean = False
            result = ("拒绝原假设：样本数据不服从正态分布")
            print(result)
        else:
            result_boolean = True
            result = ("无法拒绝原假设：样本数据可能服从正态分布")
            print("无法拒绝原假设：样本数据可能服从正态分布")

        return result_boolean, p_value, result


    def calculate_probability_by_zHigh_zLow(self, z_high, z_low, sigma):
        """
        计算基于正态分布的概率

        参数:
        z_high_percent: z_high值（小数位形式）
        z_low_percent: z_low值（小数位形式）
        sigma_percent: 标准差（小数位形式）

        返回:
        probability: 计算得到的概率值
        z_value: 计算得到的z值
        """

        # 计算z值 (注意运算优先级，使用括号确保正确顺序)
        z = (z_high - z_low) / sigma

        # 计算概率: norm.cdf(-z) 等价于标准正态分布从负无穷到-z的累积概率
        probability = norm.cdf(-z)

        return probability, z

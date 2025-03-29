import math
from scipy.stats import lognorm
import matplotlib.pyplot as plt

class LogNormalDistribution:
    def __init__(self, mean, std_dev):
        self.mean = mean
        self.std_dev = std_dev

    def pdf(self, x, mean=None, std_dev=None):
        """计算概率密度函数 (PDF)"""
        if mean is None:
            mean = self.mean
        if std_dev is None:
            std_dev = self.std_dev
        return (1 / (std_dev * math.sqrt(2 * math.pi))) * math.exp(-0.5 * ((x - mean) / std_dev) ** 2)

    def cdf(self, x, mean=None, std_dev=None):
        """计算累积分布函数 (CDF)"""
        if mean is None:
            mean = self.mean
        if std_dev is None:
            std_dev = self.std_dev
        return lognorm.cdf(x, std_dev, loc=mean)

    def ppf(self, q, mean=None, std_dev=None):
        """计算分位数函数 (PPF)"""
        if mean is None:
            mean = self.mean
        if std_dev is None:
            std_dev = self.std_dev

        s = lognorm(s=std_dev, loc=mean)
        # 计算累积分布函数的逆，即分位数
        quantile_value = s.ppf(q)

        return quantile_value

    # 仅有均值，没有自由度的, 基于指数的参数估计
    # 仅有均值，没有自由度的, 基于指数的参数估计
    def calculate_confidence_range(self, value, mean, sigma):
        # 计算置信区间
        lower_bound = value * math.exp(mean - 0.5 * sigma**2)
        upper_bound = value *math.exp(mean + 0.5 * sigma**2)

        return lower_bound, upper_bound

def test_log_normal_distribution():
    logNormDistribution = LogNormalDistribution(0, 1)

    print("测试概率密度函数(pdf) - X在这个位置的高度")
    x_values = [-1, 0, 1]
    for x in x_values:
        expected_pdf = logNormDistribution.pdf(x)
        print(f'x={x}, expected_pdf:{expected_pdf}')

    print("测试累积分布函数(cdf)  - z->%, X在这个位置的百分比 ")
    x_values = [-1, 0, 1]
    for x in x_values:
        expected_cdf = logNormDistribution.cdf(x, 0, 1)
        print(f'x={x}, expected_cdf:{expected_cdf}')

    print("测试分位数函数(ppf) - %->z, 分位数转位置")
    q_values = [0.90, 0.95, 0.975, 0.99]
    for q in q_values:
        expected_ppf = logNormDistribution.ppf(q, 0, 1)
        print(f'q={q}, expected_ppf:{expected_ppf}')

def test_parameter_estimation():

    # P48 example 2.13
    logNormDistribution = LogNormalDistribution(0, 1)
    value =2
    mean = 0
    sigma = 0.5
    lower_bound, upper_bound = logNormDistribution.calculate_confidence_range(value, mean, sigma)
    print(f"Confidence Interval(exponential): ({lower_bound}, {upper_bound})")

    x_values = list(range(1, 101))
    lower_bounds = []
    upper_bounds = []

    # Iterate through x from 1 to 100
    for x in x_values:
        lower_bound, upper_bound = logNormDistribution.calculate_confidence_range(x, 0, 0.5)
        lower_bounds.append(lower_bound)
        upper_bounds.append(upper_bound)

    # Plot the scatter chart
    plt.scatter(x_values, lower_bounds, color='blue', label='Lower Bound')
    plt.scatter(x_values, upper_bounds, color='red', label='Upper Bound')

    plt.xlabel('X Value')
    plt.ylabel('Confidence Range')
    plt.title('Confidence Interval (LogNormal Distribution)')
    plt.legend()

    # Show the plot
    plt.show()


if __name__ == "__main__":
    test_log_normal_distribution()
    test_parameter_estimation()
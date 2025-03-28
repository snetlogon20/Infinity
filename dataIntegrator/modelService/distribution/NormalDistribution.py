import math
import scipy.stats as stats
from scipy.stats import norm
from scipy.stats import shapiro
from scipy.stats import kstest
import numpy as np


from dataIntegrator.modelService.statistics.MathmaticManger import MathmaticManager


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
        """计算正态分布的累积分布函数"""
        self.mean = mean
        self.std_dev = std_dev
        return norm.cdf(x, loc=mean, scale=std_dev)

    def ppf(self, q, mean=0, std_dev=1):
        """计算正态分布的分位数（逆CDF）"""
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

def test_normal_distribution():
    normDistribution = NormalDistribution(0, 1)

    """初始化测试数据"""
    mean = 0
    std_dev = 1

    print("测试概率密度函数(pdf) - X在这个位置的高度")
    x_values = [-1, 0, 1]
    for x in x_values:
        expected_pdf = normDistribution.pdf(x, mean, std_dev)
        print(f'x={x}, expected_pdf:{expected_pdf}')

    print("测试累积分布函数(cdf)  - z->%, X在这个位置的百分比 ")
    x_values = [-1, 0, 1]
    for x in x_values:
        expected_cdf = normDistribution.cdf(x, mean, std_dev)
        print(f'x={x}, expected_cdf:{expected_cdf}')


    print("测试分位数函数(ppf) - %->z,  分位数转位置")
    q_values = [0.90, 0.95, 0.975, 0.99]
    for x in x_values:
        expected_ppf = normDistribution.ppf(q_values, mean, std_dev)
        print(f'x={x}, expected_ppf:{expected_ppf}')

def test_parameter_estimation():
    #仅有均值，没有自由度的参数估计
    # P49 Example 2.12
    normalDistribution = NormalDistribution(0, 1)
    value = 100
    confidence_level = 0.95
    mean = 0.1
    sigma = 0.2
    is_exponent = True
    #指数增长
    lower_bound, upper_bound = normalDistribution.calculate_confidence_range(value, confidence_level, mean, sigma, is_exponent)
    print(f"Confidence Interval(exponential): ({lower_bound}, {upper_bound})")
    #非指数增长
    is_exponent = False
    lower_bound, upper_bound = normalDistribution.calculate_confidence_range(value, confidence_level, mean, sigma, is_exponent)
    print(f"Confidence Interval(non-exponential): ({lower_bound}, {upper_bound})")

    #data = [23, 21, 19, 22, 20, 24, 25, 26, 23, 22]
    mathmaticManager = MathmaticManager()
    target_mean = 3210
    standard_deviation = 80
    size = 100
    data = mathmaticManager.generate_random_by_mean_std(target_mean, standard_deviation, size)
    print(data.mean())
    print(data.std())

    normalDistribution = NormalDistribution(0, 1)
    alpha = 0.05
    parameter_estimation = normalDistribution.parameter_estimation_with_data(data, alpha)
    print(f'parameter_estimation:{parameter_estimation}')


def test_hypothesisAnalysis():
    ##############################
    # Generate Random
    ##############################
    mathmaticManager = MathmaticManager()
    target_mean = 3210
    standard_deviation = 80
    size = 100
    data = mathmaticManager.generate_random_by_mean_std(target_mean, standard_deviation, size)
    print(data.mean())
    print(data.std())

    ######################################################
    # 假设分析 normal_distribution_test + pure value 纯值输入计算
    ######################################################
    #统计书 p217
    normalDistribution = NormalDistribution(0, 1)
    normalDistribution.set_data(data) # 传入数据
    alpha=0.05
    mu=3190
    n=100
    sample_mean=3210
    sample_std=80
    p_value, reject_null, comment = normalDistribution.hyperthesis_test_with_value(alpha, mu, n, sample_mean, sample_std)
    print(f'p_value:{p_value:6f}, reject_null:{reject_null}, comment:{comment}')

    ######################################################
    # 假设分析 normal_distribution_test + data 带有np data
    ######################################################
    mu_list = [0, 3190, 3210]
    for mu in mu_list:
        normalDistribution = NormalDistribution(0, 1)
        normalDistribution.set_data(data)  # 传入数据
        p_value, reject_null, comment = normalDistribution.hyperthesis_test_with_np_data(mu, 0.05)
        print(f'p_value:{p_value:6f}, reject_null:{reject_null}, comment:{comment}')

def test_back_test():
    # Back Test with value only
    normalDistribution = NormalDistribution(0, 1)
    x = 8  #Number of exception
    p = 0.01  #Percentage of the expected exception
    T = 250 # Total number of test
    alpha = 0.025
    caculated_z, expected_z, test_result, result = normalDistribution.backtest_z_value_with_value(x, p, T, alpha)
    print(f"caculated_z:{caculated_z:.6f},\nexpected_z:{expected_z:.6f},\ntest_result:{test_result},\nresult:{result}")

    # 根据压测或者蒙特卡罗模拟数据回测 Back Test with mocked data, and assert on the hypothesis
    data = np.random.normal(loc=0, scale=1, size=100)  # Generate normal data with mean=0, std=1
    normalDistribution = NormalDistribution(0, 1)
    z_scores, within_bounds_count, out_of_bounds_count = normalDistribution.backtest_z_value_with_data(data, alpha)
    print(f"within_bounds_count:{within_bounds_count:.6f}\nout_of_bounds_count:{out_of_bounds_count:.6f}")

    x = out_of_bounds_count
    p = 0.01  #Percentage of the expected exception
    T = data.size # Total number of test
    alpha = 0.025
    caculated_z, expected_z, test_result, result = normalDistribution.backtest_z_value_with_value(x, p, T, alpha)
    print(f"caculated_z:{caculated_z:.6f}\nz_scores:{expected_z:.6f}\ntest_result:{test_result}\nresult:{result}\n")

def test_normal_distribution():
    # Test 1.1 - Test distribution with ShapiroWilk, random data is in normal distribution
    print("Test 1 - distribution with ShapiroWilk, random data is in normal distribution")
    data = np.random.normal(loc=0, scale=1, size=100)

    normalDistribution = NormalDistribution(0, 1)
    result_boolean, p_value, result = normalDistribution.if_normal_distribution_with_ShapiroWilk(data)
    print(f"result_boolean:{result_boolean}\np_value:{p_value}\nresult:{result}\n,")

    #  Test 1.2 - distribution with ShapiroWilk, random data is in lognormal distribution
    print("Test 2 - Test distribution with ShapiroWilk, random data is not in normal distributio")
    size = 1000  # Number of data points
    scale = 2.0  # Scale parameter for the exponential distribution
    data = np.random.exponential(scale, size)
    result_boolean, p_value, result = normalDistribution.if_normal_distribution_with_ShapiroWilk(data)
    print(f"result_boolean:{result_boolean}\np_value:{p_value}\nresult:{result}\n")

    #  Test 1.3 - distribution with ShapiroWilk, random data is in lognormal distribution
    print("Test 3 - Test distribution with ShapiroWilk, data is random generated")
    target_mean = 3210
    random_from = 3000
    random_to = 3300
    size = 100
    mathmaticManager = MathmaticManager()
    data = mathmaticManager.generate_random_by_mean(target_mean, random_from, random_to, size)
    result_boolean, p_value, result = normalDistribution.if_normal_distribution_with_ShapiroWilk(data)
    print(f"result_boolean:{result_boolean}\np_value:{p_value}\nresult:{result}\n")

    # Test 2.1 - Test distribution with KS, random data is in normal distribution
    print("Test 4 - Test distribution with KS, random data is in normal distribution")
    data = np.random.normal(loc=0, scale=1, size=100)

    mean = 0
    std_dev = 1
    normalDistribution = NormalDistribution(0, 1)
    result_boolean, p_value, result = normalDistribution.if_normal_distribution_with_K_S(data, mean, std_dev)
    print(f"result_boolean:{result_boolean}\np_value:{p_value}\nresult:{result}\n")

    # Test 2.2 - Test distribution with KS, data is just random generated
    print("Test 5 - Test distribution with KS, data is just random generated")
    target_mean = 3210
    random_from = 3000
    random_to = 3300
    size = 100
    mathmaticManager = MathmaticManager()
    data = mathmaticManager.generate_random_by_mean(target_mean, random_from, random_to, size)

    mean = 0
    std_dev = 1
    normalDistribution = NormalDistribution(0, 1)
    result_boolean, p_value, result = normalDistribution.if_normal_distribution_with_K_S(data, mean, std_dev)
    print(f"result_boolean:{result_boolean}\np_value:{p_value}\nresult:{result}\n")

    # Test 3.1 - Test distribution with JP, data is just random generated
    print("Test 5 - Test distribution with KS, data is just random generated")
    target_mean = 3210
    random_from = 3000
    random_to = 3300
    size = 100
    mathmaticManager = MathmaticManager()
    data = mathmaticManager.generate_random_by_mean(target_mean, random_from, random_to, size)
    normalDistribution = NormalDistribution(0, 1)
    normalDistribution.if_normal_distribution_bera_with_JB(data, significance_level=0.05)

    # Test 3.2 - Test distribution with JP, data is just normal distributed
    np.random.seed(0)  # 设置随机种子以保证结果可重复
    data = np.random.normal(loc=0, scale=1, size=1000)
    normalDistribution = NormalDistribution(0, 1)
    normalDistribution.if_normal_distribution_bera_with_JB(data, significance_level=0.05)

if __name__ == "__main__":
    test_normal_distribution()
    test_hypothesisAnalysis()
    test_parameter_estimation()
    test_back_test()
    test_normal_distribution()


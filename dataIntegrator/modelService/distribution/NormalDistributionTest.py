import numpy as np

from dataIntegrator.modelService.distribution.NormalDistribution import NormalDistribution
from dataIntegrator.modelService.statistics.MathmaticManger import MathmaticManager


def test_normal_distribution_original():
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

def test_calculate_probability_by_zHigh_zLow():
    # P41
    # 假设某债券 r=6%, T=30 year, present value=$17.41， segma=0.8%
    # 先假设价格会下跌15%，那么z_high = 6.528%

    # 给定的参数（百分比形式）
    z_high = 6.528/100  # 6.528%
    z_low = 6.0/100  # 6%
    sigma = 0.8/100  # 0.8%

    print("输入参数:")
    print(f"z_high = {z_high}%")
    print(f"z_low = {z_low}%")
    print(f"sigma = {sigma}%")
    print()

    # 计算概率
    normalDistribution = NormalDistribution(0, 1)
    probability, z_value = normalDistribution.calculate_probability_by_zHigh_zLow(z_high, z_low, sigma)

    print("计算结果:")
    print(f"z值 = ({z_high}% - {z_low}%) / {sigma}% = {z_value:.6f}")
    print(f"概率 P(Z ≤ -{z_value:.6f}) = {probability:.6f}")
    print(f"概率值: {probability:.4f} ({probability * 100:.2f}%)")

    # 附加解释
    print("\n结果解释:")
    print(f"计算得到的z值为: {z_value:.6f}")
    print(f"这意味着我们要求计算 P(Z ≤ -{z_value:.6f}) 的概率")
    print(f"在标准正态分布中，这个概率为: {probability:.6f}")

    return probability, z_value

def test_calculate_probability_by_rate_range():
    # 假设美联储利率为5.5%, 假设步长为0.25%, 分别结算range(5.5%-3.0%)的概率

    z_high = 6.528/100  # 6.528%
    z_low = 3/100  # 6%
    step = 0.25/100
    sigma = 0.8/100  # 0.8%

    z_low_sequence = np.arange(z_high, z_low - step, -step)  # 注意调整终止值
    for z_low in z_low_sequence:
        print("*" * 50)
        print(f"z_high = {z_high}%")
        print(f"z_low = {z_low}%")
        print(f"sigma = {sigma}%")
        print()

        # 计算概率
        normalDistribution = NormalDistribution(0, 1)
        probability, z_value = normalDistribution.calculate_probability_by_zHigh_zLow(z_high, z_low, sigma)

        print("计算结果:")
        print(f"z值 = ({z_high}% - {z_low}%) / {sigma}% = {z_value:.6f}")
        print(f"概率 P(Z ≤ -{z_value:.6f}) = {probability:.6f}")
        print(f"概率值: {probability:.4f} ({probability * 100:.2f}%)")

        # 附加解释
        print("\n结果解释:")
        print(f"计算得到的z值为: {z_value:.6f}")
        print(f"这意味着我们要求计算 P(Z ≤ -{z_value:.6f}) 的概率")
        print(f"在标准正态分布中，这个概率为: {probability:.6f}/{probability/100}%")




if __name__ == "__main__":
    test_normal_distribution_original()
    test_normal_distribution()
    test_hypothesisAnalysis()
    test_parameter_estimation()
    test_back_test()

    test_calculate_probability_by_zHigh_zLow()
    test_calculate_probability_by_rate_range()
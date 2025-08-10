import numpy as np
from openpyxl.styles.builtins import comma
from scipy import stats

from dataIntegrator.modelService.statistics.MathmaticManger import MathmaticManager


class HypothesisAnalysis:
    def __init__(self, data):
        self.data = np.array(data)  # 确保数据是一个numpy数组

    ##############################
    # normal_distribution_test
    ##############################
    def normal_distribution_test_with_np(self, mu, alpha=0.05):
        sample_mean = np.mean(self.data)
        sample_std = np.std(self.data, ddof=1)
        n = len(self.data)

        p_value, reject_null, comment = self.p_value_test_with_normal_distribution(alpha, mu, n, sample_mean, sample_std)
        return p_value, reject_null, comment

    def p_value_test_with_normal_distribution(self, alpha, mu, n, sample_mean, sample_std):
        z_score = (sample_mean - mu) / (sample_std / np.sqrt(n))
        p = stats.norm.cdf(abs(z_score))
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))  # 双尾检验
        reject_null = p_value < alpha
        if reject_null:
            comment = "Hypothesis with Normal Distribution: 拒绝原假设，数据和假设有显著差异"
        else:
            comment = "Hypothesis with Normal Distribution: 接受原假设，数据和假设没有显著差异"
        return p_value, reject_null, comment

    ##############################
    # Student distribution test
    ##############################
    def t_distribution_test_with_np(self, mu, alpha=0.05):
        sample_mean = np.mean(self.data)
        sample_std = np.std(self.data, ddof=1)
        n = len(self.data)

        p_value, reject_null, comment = self.p_value_test_with_t_distribution(alpha, mu, n, sample_mean, sample_std)

        return p_value, reject_null, comment

    def p_value_test_with_t_distribution(self, alpha, mu, n, sample_mean, sample_std):
        t_score = (sample_mean - mu) / (sample_std / np.sqrt(n))
        df = n - 1
        p_value = 2 * (1 - stats.t.cdf(abs(t_score), df))  # 双尾检验
        reject_null = p_value < alpha
        if reject_null:
            comment = "Hypothesis with T Distribution: 拒绝原假设，数据和假设有显著差异"
        else:
            comment = "Hypothesis with T Distribution: 接受原假设，数据和假设没有显著差异"
        return p_value, reject_null, comment


if __name__ == "__main__":
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

    ##############################
    # normal_distribution_test + pure value
    ##############################
    hypothesisAnalysis = HypothesisAnalysis(data)  # 传入数据
    p_value, reject_null, comment = hypothesisAnalysis.p_value_test_with_normal_distribution(alpha=0.05, mu=3190, n=100, sample_mean=3210, sample_std=80)
    print(f'p_value:{p_value:6f}, reject_null:{reject_null}, comment:{comment}')

    ##############################
    # normal_distribution_test + data
    ##############################
    hypothesisAnalysis = HypothesisAnalysis(data)  # 传入数据
    p_value, reject_null, comment = hypothesisAnalysis.normal_distribution_test(0, 0.05)
    print(f'p_value:{p_value:6f}, reject_null:{reject_null}, comment:{comment}')

    hypothesisAnalysis = HypothesisAnalysis(data)  # 传入数据
    p_value, reject_null, comment = hypothesisAnalysis.normal_distribution_test(3190, 0.05)
    print(f'p_value:{p_value:6f}, reject_null:{reject_null}, comment:{comment}')

    hypothesisAnalysis = HypothesisAnalysis(data)  # 传入数据
    p_value, reject_null, comment = hypothesisAnalysis.normal_distribution_test(3210, 0.05)
    print(f'p_value:{p_value:6f}, reject_null:{reject_null}, comment:{comment}')

    ##############################
    # t_distribution + pure value
    ##############################
    hypothesisAnalysis = HypothesisAnalysis(data)  # 传入数据
    p_value, reject_null, comment = hypothesisAnalysis.p_value_test_with_t_distribution(alpha=0.05, mu=3190, n=100, sample_mean=3210, sample_std=80)
    print(f'p_value:{p_value:6f}, reject_null:{reject_null}, comment:{comment}')

    ##############################
    # t_distribution_test + data
    ##############################
    hypothesisAnalysis = HypothesisAnalysis(data)  # 传入数据
    p_value, reject_null, comment = hypothesisAnalysis.t_distribution_test(0, 0.05)
    print(f'p_value:{p_value:6f}, reject_null:{reject_null}, comment:{comment}')

    hypothesisAnalysis = HypothesisAnalysis(data)  # 传入数据
    p_value, reject_null, comment = hypothesisAnalysis.t_distribution_test(3190, 0.05)
    print(f'p_value:{p_value:6f}, reject_null:{reject_null}, comment:{comment}')

    hypothesisAnalysis = HypothesisAnalysis(data)  # 传入数据
    p_value, reject_null, comment = hypothesisAnalysis.t_distribution_test(3210, 0.05)
    print(f'p_value:{p_value:6f}, reject_null:{reject_null}, comment:{comment}')
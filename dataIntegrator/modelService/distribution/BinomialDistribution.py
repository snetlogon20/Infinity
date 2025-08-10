import scipy.stats as stats
import pandas as pd
import matplotlib.pyplot as plt

class BinomialDistribution:
    def __init__(self, n, p):
        """
        Initialize the Binomial Distribution with n trials and probability p.

        Parameters:
        n (int): Number of trials.
        p (float): Probability of success in a single trial.
        """
        self.n = n
        self.p = p

    def pmf(self, k):
        """
        Probability Mass Function for the Binomial distribution.

        Parameters:
        k (int): Number of successes.

        Returns:
        float: PMF value at k.
        """
        return stats.binom.pmf(k, self.n, self.p)

    def cdf(self, k):
        """
        Cumulative Distribution Function for the Binomial distribution.

        Parameters:
        k (int): Number of successes.

        Returns:
        float: CDF value at k.
        """
        return stats.binom.cdf(k, self.n, self.p)

    def mean(self):
        """
        Mean of the Binomial distribution.

        Returns:
        float: Mean of the distribution.
        """
        return self.n * self.p

    def variance(self):
        """
        Variance of the Binomial distribution.

        Returns:
        float: Variance of the distribution.
        """
        return self.n * self.p * (1 - self.p)

    def std_dev(self):
        """
        Standard deviation of the Binomial distribution.

        Returns:
        float: Standard deviation of the distribution.
        """
        return (self.n * self.p * (1 - self.p)) ** 0.5

def test_binomial_distribution_pmf():


    # P53, 第一个公式
    p = 0.01  # 已知每次成功概率
    n = 250  # 总实验次数
    x = 0 # 求第 x 成功次的概率
    binomial_dist = BinomialDistribution(n, p)
    expected_pmf = binomial_dist.pmf(x)
    print(expected_pmf)

    # P53, Example 2.15
    p = 0.25  # 已知每次成功概率
    n = 6  # 总实验次数
    x = 0 # 求第 x 成功次的单一概率
    binomial_dist = BinomialDistribution(n, p)
    expected_pmf = binomial_dist.pmf(x)
    print(expected_pmf)

    # P53, Example 2.15 6题， 随便做对6题的概率
    p = 0.25  # 已知每次成功概率
    n = 6  # 总实验次数
    x=range(0,6,1)
    binomial_dist = BinomialDistribution(n, p)
    p = binomial_dist.pmf(x)
    df = pd.DataFrame({'x': x, 'PMF': p})
    print(df)

    # Plot the data in a bar chart
    plt.bar(df['x'], df['PMF'], color='blue')

    # Add labels and title
    plt.xlabel('Number of Successes (x)')
    plt.ylabel('Probability Mass Function (PMF)')
    plt.title('Binomial Distribution PMF')

    # Display the plot
    plt.show()

    # P53, Example 2.15 的扩展。 如果有100题， 随便做对60题的概率
    p = 0.25  # 已知每次成功概率
    n = 100  # 总实验次数
    x=range(0,60,1)
    binomial_dist = BinomialDistribution(n, p)
    p = binomial_dist.pmf(x)
    df = pd.DataFrame({'x': x, 'PMF': p})
    print(df)

    # Plot the data in a bar chart
    plt.bar(df['x'], df['PMF'], color='blue')

    # Add labels and title
    plt.xlabel('Number of Successes (x)')
    plt.ylabel('Probability Mass Function (PMF)')
    plt.title('Binomial Distribution PMF')

    # Display the plot
    plt.show()


def test_binomial_distribution_cdf():
    # 单一节点的累积概率
    p = 0.25  # 已知每次成功概率
    n = 6  # 总实验次数
    x = 1 # 求第 x 成功次的累积概率
    binomial_dist = BinomialDistribution(n, p)
    expected_cdf = binomial_dist.cdf(x)
    print(f'expected_cdf：{expected_cdf}')


    # P53, Example 2.15 的扩展。 如果有100题， 随便做对60题的概率
    p = 0.25  # 已知每次成功概率
    n = 100  # 总实验次数
    x=range(0,60,1)
    binomial_dist = BinomialDistribution(n, p)
    p = binomial_dist.cdf(x)
    df = pd.DataFrame({'x': x, 'CDF': p})
    print(df)

    # Plot the data in a bar chart
    plt.bar(df['x'], df['CDF'], color='blue')

    # Add labels and title
    plt.xlabel('Number of Successes (x)')
    plt.ylabel('Probability Mass Function (CDF)')
    plt.title('Binomial Distribution CDF')

    # Display the plot
    plt.show()


if __name__ == "__main__":
    pd.set_option('display.float_format', '{:.6f}'.format)

    test_binomial_distribution_pmf()
    test_binomial_distribution_cdf()
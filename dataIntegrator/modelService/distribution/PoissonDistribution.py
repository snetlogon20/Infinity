import scipy.stats as stats
import pandas as pd
import matplotlib.pyplot as plt

class PoissonDistribution:
    def __init__(self, lambda_):
        """
        Initialize the Poisson Distribution with rate parameter lambda_.

        Parameters:
        lambda_ (float): Rate (mean number of events) per interval.
        """
        self.lambda_ = lambda_

    def pmf(self, k):
        """
        Probability Mass Function for the Poisson distribution.

        Parameters:
        k (int): Number of events.

        Returns:
        float: PMF value at k.
        """
        return stats.poisson.pmf(k, self.lambda_)

    def cdf(self, k):
        """
        Cumulative Distribution Function for the Poisson distribution.

        Parameters:
        k (int): Number of events.

        Returns:
        float: CDF value at k.
        """
        return stats.poisson.cdf(k, self.lambda_)

    def mean(self):
        """
        Mean of the Poisson distribution.

        Returns:
        float: Mean of the distribution.
        """
        return self.lambda_

    def variance(self):
        """
        Variance of the Poisson distribution.

        Returns:
        float: Variance of the distribution.
        """
        return self.lambda_

    def std_dev(self):
        """
        Standard deviation of the Poisson distribution.

        Returns:
        float: Standard deviation of the distribution.
        """
        return self.lambda_ ** 0.5


def test_poisson_distribution_pmf():
    # 广场上平均有1万人， 论不同人数的概率
    poisson = PoissonDistribution(lambda_=10000)
    k = range(9000, 11000, 1)
    p = poisson.pmf(k)

    df = pd.DataFrame({'k': k, 'PMF': p})
    print(df)

    # Plot the data
    plt.plot(df['k'], df['PMF'], marker='o', linestyle='-', color='b')

    # Add labels and title
    plt.xlabel('k')
    plt.ylabel('PMF')
    plt.title('Poisson Distribution PMF')

    # Show the plot
    plt.show()

def test_poisson_distribution_cdf():
    # 广场上平均有1万人， 论不同人数的累积概率
    poisson = PoissonDistribution(lambda_=10000)
    k = range(9000, 11000, 1)
    p = poisson.cdf(k)

    df = pd.DataFrame({'k': k, 'PMF': p})
    print(df)

    # Plot the data
    plt.plot(df['k'], df['PMF'], marker='o', linestyle='-', color='b')

    # Add labels and title
    plt.xlabel('k')
    plt.ylabel('PMF')
    plt.title('Poisson Distribution PMF')

    # Show the plot
    plt.show()

if __name__ == '__main__':
    pd.set_option('display.float_format', '{:.6f}'.format)
    test_poisson_distribution_pmf()
    test_poisson_distribution_cdf()

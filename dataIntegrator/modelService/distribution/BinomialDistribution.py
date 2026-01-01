import math

import scipy.stats as stats
import pandas as pd
import matplotlib.pyplot as plt

from dataIntegrator import CommonLib


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

    def cdf_manual(self, T, p, x):
        T = T
        p = p
        x = x
        possibility = ((math.factorial(T) / (math.factorial(x) * math.factorial(T - x))) *
                       (p ** x) *
                       (1 - p) ** (T - x))
        return possibility

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

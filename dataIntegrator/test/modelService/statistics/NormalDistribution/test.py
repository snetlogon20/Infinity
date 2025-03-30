import unittest

import matplotlib.pyplot as plt
import numpy as np

from dataIntegrator.modelService.statistics.NormalDistribution import NormalDistribution

class TestNormalDistribution(unittest.TestCase):

    def setUp(self):
        # Initialize the distribution object with default parameters (mean=0, std_dev=1)
        self.dist = NormalDistribution()

    def test_pdf(self):
        # Test PDF at x = 0 (should return ~0.398942 for standard normal)
        self.assertAlmostEqual(self.dist.pdf(0), 0.3989422804014337, places=5)

    def test_cdf(self):
        # Test CDF at x = 0 (should return 0.5 for standard normal)
        self.assertAlmostEqual(self.dist.cdf(0), 0.5, places=5)

    def test_ppf(self):
        # Test PPF for the 95th percentile (should return ~1.64485 for standard normal)
        self.assertAlmostEqual(self.dist.ppf(0.95), 1.6448536269514722, places=5)

    def test_print_pdf_values(self):
        x_values = np.arange(-5.0, 5.0, 0.1)  # Array of x values
        y_values = [self.dist.pdf(x) for x in x_values]  # Array of corresponding y values

        # Plot the results
        plt.plot(x_values, y_values, label="PDF")
        plt.xlabel('x')
        plt.ylabel('PDF(x)')
        plt.title('Probability Density Function of Normal Distribution')
        plt.legend()
        plt.grid(True)
        plt.show(block=True)

    def test_print_cdf_values(self):
        x_values = np.arange(-5.0, 5.0, 0.1)  # Array of x values
        y_values = [self.dist.cdf(x) for x in x_values]  # Array of corresponding CDF values

        # Plot the results
        plt.plot(x_values, y_values, label="CDF")
        plt.xlabel('x')
        plt.ylabel('CDF(x)')
        plt.title('Cumulative Distribution Function of Normal Distribution')
        plt.legend()
        plt.grid(True)
        plt.show(block=True)

    def test_print_ppf_values(self):
        p_values = np.linspace(0.01, 0.99, 100)  # Array of p values between 0 and 1
        x_values = [self.dist.ppf(p) for p in p_values]  # Array of corresponding PPF values

        # Plot the results
        plt.plot(p_values, x_values, label="PPF")
        plt.xlabel('p')
        plt.ylabel('PPF(p)')
        plt.title('Percent-Point Function of Normal Distribution')
        plt.legend()
        plt.grid(True)
        plt.show(block=True)

if __name__ == '__main__':
    unittest.main()
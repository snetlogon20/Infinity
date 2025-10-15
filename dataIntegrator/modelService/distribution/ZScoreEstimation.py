import math
from scipy.stats import norm


class ZScoreEstimation():
    def __init__(self):
        pass

    def caculate_zscore_with_x_p_t(Self, x, p, T):
        zscore = (x - p*T) / math.sqrt(p*(1-p)*T)
        return zscore

    def convert_z2alpha(self, z):
        alpha_left = norm.cdf(z)
        return alpha_left

    def convert_alpha2z(self, alpha):
        z = norm.ppf(alpha)
        return z

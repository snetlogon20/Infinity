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

if __name__ == '__main__':

    # P360, 15.3 z score 推断
    zscore = ZScoreEstimation()

    x = 8 # 期望值
    p = 0.01 # 观测值
    T = 250 # 实验次数
    z = zscore.caculate_zscore_with_x_p_t(x, p, T)
    print(z)

    alpha_left = zscore.convert_z2alpha(z)
    print(alpha_left)

    z = zscore.convert_alpha2z(0.05)
    print(z)

    z = zscore.convert_alpha2z(0.95)
    print(z)
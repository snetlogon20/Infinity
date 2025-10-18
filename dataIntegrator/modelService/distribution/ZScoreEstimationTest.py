from dataIntegrator.modelService.distribution.ZScoreEstimation import ZScoreEstimation
from scipy.stats import norm

def test1_caculate_Z_by_x():

    x = 8
    p = 0.01  # 观测值
    T = 250  # 实验次数

    print("" * 50)
    print("x=", x)

    zscore = ZScoreEstimation()
    z = zscore.caculate_zscore_with_x_p_t(x, p, T)
    print("z:", z)

    p = norm.cdf(z, 0, 1)
    print("p:", p)

    alpha_left = zscore.convert_z2alpha(z)
    print("alpha_left:", alpha_left)

    z = zscore.convert_alpha2z(0.05)
    print("z0.05:", z)

    z = zscore.convert_alpha2z(0.95)
    print("z0.95:", z)

def test2_caculate_Z_by_x_range():
    # x = 8 # 期望值
    for x in range(1, 100):
        print("" * 50)
        print("x=", x)
        p = 0.01  # 观测值
        T = 250  # 实验次数

        zscore = ZScoreEstimation()
        z = zscore.caculate_zscore_with_x_p_t(x, p, T)
        print("z:", z)

        p = norm.cdf(z, 0, 1)
        print("p:", p)

        alpha_left = zscore.convert_z2alpha(z)
        print("alpha_left:", alpha_left)

        z = zscore.convert_alpha2z(0.05)
        print("z0.05:", z)

        z = zscore.convert_alpha2z(0.95)
        print("z0.95:", z)


def back_test_by_p_x_T(x, p, T, confidence_level):

    # 计算观察到的 Z 值（检验统计量）
    z_observed = estimator.caculate_zscore_with_x_p_t(x, p, T)
    print(f"观测参数: p={p}, T={T}, 异常值数量 x={x}")
    print(f"观察到的 Z 值: {z_observed:.4f}")
    # 计算临界 Z 值（99% 置信水平下的单侧检验边界）
    z_critical = estimator.convert_alpha2z(confidence_level)
    print(f"临界 Z 值 (置信水平 {confidence_level}): {z_critical:.4f}")
    # 假设检验决策
    if z_observed > z_critical:
        print("结论: 拒绝原假设（Z > Z_critical）")
        print("原假设 p=0.01 可能低估了风险，异常值比例显著高于预期。")
    else:
        print("结论: 无法拒绝原假设（Z ≤ Z_critical）")
        print("异常值数量在统计上可接受，原假设 p=0.01 可能成立。")
    # 附加分析：将观察到的 Z 值转换为显著性水平（p-value）
    alpha_observed = estimator.convert_z2alpha(z_observed)
    p_value = 2 * min(alpha_observed, 1 - alpha_observed)  # 双侧检验的 p-value
    print(f"观测 Z 值对应的显著性水平（p-value）: {p_value:.6f}")

    supposed_confidence_level = 1 - p_value

    return z_observed, z_critical, alpha_observed, p_value, supposed_confidence_level


if __name__ == '__main__':

    # test1_caculate_Z_by_x()
    # test2_caculate_Z_by_x_range()


    # P55 Simple test
    zscore = ZScoreEstimation()

    # 假设99%的VAR值，所以p=0.01, T=205天, 现在发现有8个异常值，问Z值是多少？
    # 如果Z > Z(99%) 边界，就认为原假设错误，应该拒绝原假设。所以原来的p=0.01有问题。

    # P360, 15.3 z score 推断
    # 初始化 ZScoreEstimation 实例
    estimator = ZScoreEstimation()

    # 给定参数
    x = 8  # 观察到的异常值数量
    p = 0.01  # 原假设下的异常概率（对应99% VaR）
    T = 250  # 观测天数
    confidence_level = 0.99  # 置信水平

    back_test_by_p_x_T(x, p, T, confidence_level)
import math
from scipy.stats import norm

from dataIntegrator.modelService.distribution.ZScoreEstimation import ZScoreEstimation


class ZScoreBackTestManager():
    def __init__(self):
        pass

    def back_test_by_p_x_T(self, x, p, T, confidence_level):
        estimator = ZScoreEstimation()

        # 计算观察到的 Z 值（检验统计量）
        z_observed = estimator.caculate_zscore_with_x_p_t(x, p, T)
        print(f"观测参数: p={p}, T={T}, 异常值数量 x={x}")
        print(f"观察到的 Z 值: {z_observed:.4f}")

        # 计算临界 Z 值（99% 置信水平下的单侧检验边界）
        z_critical = estimator.convert_alpha2z(confidence_level)
        print(f"临界 Z 值 (置信水平 {confidence_level}): {z_critical:.4f}")

        # 假设检验决策
        if z_observed > z_critical:
            conclusion="拒绝原假设"
            conclusion_reseason="原假设 p=0.01 可能低估了风险，异常值比例显著高于预期。"
        else:
            conclusion="无法拒绝原假设（Z ≤ Z_critical）"
            conclusion_reseason ="异常值数量在统计上可接受，原假设 p=0.01 可能成立。"
        print("结论: 拒绝原假设（Z > Z_critical）")
        print("原假设 p=0.01 可能低估了风险，异常值比例显著高于预期。")

        # 附加分析：将观察到的 Z 值转换为显著性水平（p-value）
        alpha_observed = estimator.convert_z2alpha(z_observed)
        p_value = 2 * min(alpha_observed, 1 - alpha_observed)  # 双侧检验的 p-value
        print(f"观测 Z 值对应的显著性水平（p-value）: {p_value:.6f}")

        # 观察到的 Z 值所对应的置信水平
        supposed_confidence_level = 1 - p_value

        return z_observed, z_critical, alpha_observed, p_value, supposed_confidence_level,conclusion, conclusion_reseason

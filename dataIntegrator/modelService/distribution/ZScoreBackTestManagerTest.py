import math
from scipy.stats import norm

from dataIntegrator.modelService.distribution.ZScoreBackTestManager import ZScoreBackTestManager

if __name__ == '__main__':


    zScoreBackTestManager = ZScoreBackTestManager()

    # P55 Simple test
    # 假设99%的VAR值，所以p=0.01, T=205天, 现在发现有8个异常值，问Z值是多少？
    # 如果Z > Z(99%) 边界，就认为原假设错误，应该拒绝原假设。所以原来的p=0.01有问题。


    # 给定参数
    x = 8  # 观察到的异常值数量
    p = 0.01  # 原假设下的异常概率（对应99% VaR）
    T = 250  # 观测天数
    confidence_level = 0.99  # 置信水平

    z_observed, z_critical, alpha_observed, p_value, supposed_confidence_level,conclusion, conclusion_reason = zScoreBackTestManager.back_test_by_p_x_T(x, p, T, confidence_level)

    print(f"""
    z_observed={z_observed:.6f}
    z_critical={z_critical:.6f}
    alpha_observed={z_critical:.6f}
    p_value={p_value:.6f}
    supposed_confidence_level={supposed_confidence_level:.6f}
    
    conclusion={conclusion}
    conclusion_reason={conclusion_reason}
    """)

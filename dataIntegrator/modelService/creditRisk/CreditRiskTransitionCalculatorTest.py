import numpy as np

from dataIntegrator.modelService.creditRisk.CreditRiskTransitionCalculator import CreditRiskTransitionCalculator

# 使用示例
if __name__ == "__main__":
    # 基于TABLE 20.5的转移概率矩阵
    # 状态: A, B, C, D (D为违约状态)
    transition_matrix = np.array([
        [0.97, 0.03, 0.00, 0.00],  # 从A状态转移
        [0.02, 0.93, 0.02, 0.03],  # 从B状态转移
        [0.01, 0.12, 0.64, 0.23],  # 从C状态转移
        [0.00, 0.00, 0.00, 1.00]  # 从D状态转移(吸收状态)
    ])

    rating_labels = ['A', 'B', 'C', 'D']


    calculator = CreditRiskTransitionCalculator(transition_matrix, rating_labels)

    # 示例1: 计算从A评级开始，3年后的累积违约概率
    initial_state = "A"
    years = 3
    default_prob = calculator.calculate_cumulative_default(initial_state, years)
    print(f"从{initial_state}评级开始，{years}年后的累积违约概率: {default_prob:.4f} ({default_prob * 100:.2f}%)")

    # 示例2: 获取从B评级开始，1-5年的累积违约概率
    print("\n从B评级开始的多年累积违约概率:")
    multi_year_probs = calculator.get_multi_year_default_probs("B", 3)
    for year, prob in multi_year_probs.items():
        print(f"第{year}年: {prob:.6f} ({prob * 100:.4f}%)")


    # 示例3: 验证矩阵性质
    print("\n转移矩阵验证 (每行总和应为1):")
    for i, row in enumerate(calculator.transition_matrix):
        row_sum = np.sum(row)
        print(f"{calculator.rating_labels[i]}状态行总和: {row_sum:.6f}")
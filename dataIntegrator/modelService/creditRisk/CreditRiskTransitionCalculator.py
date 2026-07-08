import numpy as np


class CreditRiskTransitionCalculator:
    def __init__(self, transition_matrix, rating_labels):
        self.transition_matrix = transition_matrix
        self.rating_labels = rating_labels

    def state_to_index(self, state):
        """将评级状态转换为矩阵索引"""
        return self.rating_labels.index(state)

    def calculate_cumulative_default(self, initial_state, years):
        """
        计算累积违约概率

        参数:
        initial_state: 初始评级状态 (A, B, C)
        years: 年数

        返回:
        累积违约概率
        """
        if initial_state == 'D':
            return 1.0  # 如果已经是违约状态，概率为100%

        initial_idx = self.state_to_index(initial_state)

        # 初始状态向量: [A概率, B概率, C概率, D概率]
        state_vector = np.zeros(4)
        state_vector[initial_idx] = 1.0

        # 计算n年后的状态分布
        for year in range(years):
            state_vector = np.dot(state_vector, self.transition_matrix)

        # 返回违约状态(D)的概率
        default_idx = self.state_to_index('D')
        return state_vector[default_idx]

    def get_multi_year_default_probs(self, initial_state, max_years):
        """获取多年累积违约概率"""
        results = {}
        for year in range(1, max_years + 1):
            prob = self.calculate_cumulative_default(initial_state, year)
            results[year] = prob
        return results


# 使用示例
if __name__ == "__main__":
    calculator = CreditRiskTransitionCalculator()

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
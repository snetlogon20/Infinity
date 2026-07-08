import pandas as pd
from scipy.stats import ks_2samp
import numpy as np

class MathmaticManager:

    #获取平均数和segma
    def get_mean_and_sigma(self, dataFrameInput: pd.DataFrame, columns):
        dataFrame = pd.DataFrame(dataFrameInput, columns=columns)
        stats = pd.DataFrame()
        stats["Mean"] = dataFrame.mean()
        cov_matrix = dataFrame.cov()
        stats["Variance"] = dataFrame.var()
        stats["Std_Dev"] = dataFrame.std()
        stats["kurt"] = dataFrame.kurt()
        stats["skew"] = dataFrame.skew()
        stats["median"] = dataFrame.median()
        stats["sem"] = dataFrame.sem()
        print(stats)
        return stats

    # 获取相关系数
    def get_rho_ab(self, dataFrameInput: pd.DataFrame, column_a: str, column_b: str) -> float:
        # 提取指定的两列
        dataFrame = dataFrameInput[[column_a, column_b]]
        # 计算皮尔逊相关系数
        rho = dataFrame.corr(method='pearson').loc[column_a, column_b]
        return rho

    # 根据给予的平均数给出随机数
    def generate_random_by_mean(self, target_mean, random_from, random_to, size):
        # 生成9个随机数据
        data = np.random.randint(random_from, random_to, size-1)
        # 计算剩余数据，使得平均值为3210
        remaining_value = target_mean * size - np.sum(data)
        # 将剩余值添加到数据中
        data = np.append(data, remaining_value)
        # 输出数据和平均值
        print("生成的数据：", data)
        print("数据的平均值：", np.mean(data))

        return data

    # 根据给予的平均数和标准差给出随机数
    def generate_random_by_mean_std(self, target_mean, std, size):
        return np.random.normal(loc=target_mean, scale=std, size=size)

    # 通过K-S检验查看两个数据是否来自同一分布
    def if_same_distribution(self, data1, data2):
        result = ks_2samp(data1, data2)

        # Display the result
        print("K-S Test Statistic:", result.statistic)
        print("P-value:", result.pvalue)
        pvalue = result.pvalue

        # Interpretation
        if result.pvalue > 0.05:
            result_boolean = True
            result = "Fail to reject the null hypothesis: The two datasets come from the same distribution."
        else:
            result_boolean = False
            result = "Reject the null hypothesis: The two datasets do not come from the same distribution."

        return result_boolean, pvalue, result


def caculate_mean_and_segma():
    global data, columns
    # Example usage with a sample DataFrame
    data = {
        'A': [1, 2, 3, 4, 5],
        'B': [5, 6, 7, 8, 9]
    }
    df = pd.DataFrame(data)
    columns = ['A']  # specify the column
    sharpRatio = MathmaticManager()
    stats = sharpRatio.get_mean_and_sigma(df, columns)
    print(f"Statistics for column {columns}:")
    print(stats)
    print(stats.loc['A']["Mean"])
    columns = ['A', 'B']  # specify the column
    sharpRatio = MathmaticManager()
    stats = sharpRatio.get_mean_and_sigma(df, columns)
    print(f"Statistics for column {columns}:")
    print(stats)
    print(stats["Mean"])

def caculate_correlation():
    data = {
        'A': [1, 2, 3, 4, 5],
        'B': [5, 4, 3, 2, 1],
        'C': [2, 3, 4, 5, 6]
    }
    df = pd.DataFrame(data)
    mathManager = MathmaticManager()
    rho = mathManager.get_rho_ab(df, 'A', 'B')
    print("相关系数矩阵：")
    print(rho)

def caculate_cov():
    data = {
        'A': [1, 2, 3, 4, 5],
        'B': [5, 4, 3, 2, 1],
        'C': [2, 3, 4, 5, 6]
    }
    columns = ['A', 'B', 'C']
    df = pd.DataFrame(data, columns =columns)
      # specify the column
    cov =df.cov()
    print("cov:\n",cov)

def test_generate_random_by_mean():
    mathmaticManager = MathmaticManager()
    target_mean = 3210
    random_from = 3000
    random_to = 3300
    size = 100
    data = mathmaticManager.generate_random_by_mean(target_mean, random_from, random_to, size)
    print(data.mean())
    print(data.std())

def generate_random_by_mean_std():
    mathmaticManager = MathmaticManager()
    target_mean = 3210
    standard_deviation = 80
    size = 100
    data = mathmaticManager.generate_random_by_mean_std(target_mean, standard_deviation, size)
    print(data.mean())
    print(data.std())

def test_if_same_distribution():
    mathmaticManager = MathmaticManager()
    data1 = np.random.normal(loc=0, scale=1, size=1000)  # Normally distributed data (mean=0, std=1)
    data2 = np.random.normal(loc=1, scale=1, size=1000)  # Normally distributed data (mean=1, std=1)
    result_boolean, pvalue, result = mathmaticManager.if_same_distribution(data1, data2)
    print(f"result_boolean:{result_boolean}, pvalue:{pvalue}, result:{result}")

if __name__ == "__main__":
    caculate_cov()
    caculate_mean_and_segma()
    caculate_correlation()

    test_generate_random_by_mean()
    generate_random_by_mean_std()

    test_if_same_distribution()
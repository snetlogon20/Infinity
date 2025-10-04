import numpy as np
from dataIntegrator.modelService.operationRisk.LDACalculator import LDACalculator


def test1_calcuate_lda():

    #page 621
    ldaCaculator = LDACalculator()
    # 根据图片内容定义输入数据
    frequency_distribution = {
        'probability': np.array([0.6, 0.3, 0.1]),  # 概率
        'frequency': np.array([0, 1, 2])  # 频率
    }
    severity_distribution = {
        'probability': np.array([0.5, 0.3, 0.2]),  # 概率
        'severity': np.array([1000, 10000, 100000])  # 严重程度（美元）
    }
    confidence_level = 0.95  # 95% 置信水平
    print("=" * 60)
    print("操作风险分析程序 - 基于TABLE 25.2和TABLE 25.3")
    print("=" * 60)
    # 执行分析
    results = ldaCaculator.calculate_operational_risk(frequency_distribution, severity_distribution, confidence_level)
    print("\n" + "=" * 60)
    print("详细损失分布表 (TABLE 25.3):")
    print("=" * 60)

    ldaCaculator.output_results(results, confidence_level)

def test2_calcuate_lda():

    #page 625, example 25.8

    ldaCaculator = LDACalculator()
    # 根据图片内容定义输入数据
    frequency_distribution = {
        'probability': np.array([0.5,0.3,0.2]),  # 概率
        'frequency': np.array([0, 1, 2])  # 频率
    }
    severity_distribution = {
        'probability': np.array([0.6, 0.3, 0.1]),  # 概率
        'severity': np.array([1000, 10000, 100000])  # 严重程度（美元）
    }
    confidence_level = 0.95  # 95% 置信水平
    print("=" * 60)
    print("操作风险分析程序")
    print("=" * 60)
    # 执行分析
    results = ldaCaculator.calculate_operational_risk(frequency_distribution, severity_distribution, confidence_level)
    print("\n" + "=" * 60)
    print("详细损失分布表:")
    print("=" * 60)

    ldaCaculator.output_results(results, confidence_level)


if __name__ == "__main__":

    #test1_calcuate_lda()
    test2_calcuate_lda()




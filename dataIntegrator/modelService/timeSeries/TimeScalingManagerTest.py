import numpy as np

from dataIntegrator.modelService.timeSeries.TimeScalingManager import TimeScalingManager


class TimeScalingManagerTest:
    def __init__(self):
        pass


def test1_time_scaling_VAR():
    # P106 Example 5.1
    print("P106 Example 5.1")
    print("-"*60)

    timeScalingManager = TimeScalingManager()
    var = timeScalingManager.calculate_scaled_var(1000000, 2, 0.1)
    print(rf"var:{var}")


def test2_calculate_scaled_sigma():
    # P107 Example 5.2
    print("P107 Example 5.2")
    print("-"*60)

    timeScalingManager = TimeScalingManager()
    segma = timeScalingManager.calculate_scaled_sigma(0.34, t=1, unit="week")
    print(rf"segma:{segma}")

    segma = timeScalingManager.calculate_scaled_sigma(0.34, t=2, unit="week")
    print(rf"segma:{segma}")

    segma = timeScalingManager.calculate_scaled_sigma(0.34, t=52, unit="week")
    print(rf"segma:{segma}")

    segma = timeScalingManager.calculate_scaled_sigma(0.34, t=1, unit="day")
    print(rf"segma:{segma}")

    segma = timeScalingManager.calculate_scaled_sigma(0.34, t=1, unit="year")
    print(rf"segma:{segma}")

def test3_1_calculate_EWMA_eta():
    # P120 Example 5.107
    print("P120 Example 5.107")
    print("-"*60)
    timeScalingManager = TimeScalingManager()
    eta = timeScalingManager.calculate_EWMA_eta(0.95, 3, eta_t_minus_1=1.1)
    print(rf"var:{eta}")

    eta = timeScalingManager.calculate_EWMA_eta(0.95, 0.03/100, eta_t_minus_1=1.1/100)
    print(rf"var:{eta}")

def test3_2_calculate_EWMA_eta_with_log_value():
    # P121 Example 5.11
    print("P121 Example 5.11")
    print("-"*60)

    timeScalingManager = TimeScalingManager()
    sigma = 1.5/100
    eta_t_minus_1 = sigma**2
    eta = timeScalingManager.calculate_EWMA_eta_with_log_value(ewma_lambda=0.90, expected_return_t0=20, expected_return_t1=18, eta_t_minus_1=eta_t_minus_1)
    sigma = eta**0.5
    print(rf"eta:{eta}")
    print(rf"sigma:{sigma}")

def test3_calculate_EWMA_rolling_eta():
    # 创建与table 5.4一致的输入数据
    print("创建与table 5.4一致的输入数据")
    print("-"*60)
    test_data = {
        'time': [0, 1, 2, 3],
        'return': [0, 3, 0, 0],
        'eta': 1.10
    }

    # 计算EWMA结果
    timeScalingManager = TimeScalingManager()
    ewma_result, conditional_variance = timeScalingManager.calculate_EWMA_rolling_eta(data_dict=test_data, lambda_param=0.95)

    # 打印结果表格
    print("EWMA Forecast Results (λ=0.95):")
    print("=" * 60)
    print(f"{'Time':<6} {'Return':<8} {'Cond Variance':<15} {'Cond Risk':<12} {'95% Limit':<12}")
    print("-" * 60)

    for i in range(len(ewma_result['time'])):
        print(f"{ewma_result['time'][i]:<6} "
              f"{ewma_result['return'][i]:<8} "
              f"{ewma_result['conditional_variance'][i]:<15} "
              f"{ewma_result['conditional_risk'][i]:<12} "
              f"±{ewma_result['conditional_95_limit'][i]:<10}")

    print("=" * 60)
    print(rf"conditional_variance={conditional_variance}")

if __name__ == "__main__":
    test1_time_scaling_VAR()
    test2_calculate_scaled_sigma()
    test3_1_calculate_EWMA_eta()
    test3_2_calculate_EWMA_eta_with_log_value()
    test3_calculate_EWMA_rolling_eta()


from dataIntegrator.modelService.creditRisk.ExpectedLossCalculator import ExpectedLossCalculator


def Test1_compute_ECL_of_swap():
    # P593 Table 24.1 Computation of expected credit Loss for a Swap
    risk_free_rate = 0.06  # 6%
    years = [1, 2, 3, 4, 5]
    dt = [0.0022, 0.00321, 0.00342, 0.00676, 0.0073]  # 边际违约率%
    ECEt = [1660000, 1497000, 1069000, 554000, 0]  # 第5年exposure为0
    recover_rate = 0.45  # 回收率 = 1 - LGD(0.55) = 0.45
    # 计算PV ECL
    expectedLossCalculator = ExpectedLossCalculator()
    result = expectedLossCalculator.calculate_pv_of_expected_loss(risk_free_rate, years, dt, ECEt, recover_rate)
    # 显示结果
    print("PV ECL 计算结果:")
    print("=" * 80)
    print(result['dataframe'].round(6))
    print("\n汇总统计:")
    print("=" * 40)
    for key, value in result['summary'].items():
        print(f"{key}: {value:,.6f}")

def Test2_compute_ECL_of_bond():
    # P594 Table 24.2 Computation of expected credit Loss for a bond
    risk_free_rate = 0.06  # 6%
    years = [1, 2, 3, 4, 5]
    dt = [0.0022, 0.00321, 0.00342, 0.00676, 0.00741]  # 边际违约率%
    ECEt = [100000000, 100000000, 100000000, 100000000, 100000000]  # 第5年exposure为0
    recover_rate = 0.45  # 回收率 = 1 - LGD(0.55) = 0.45
    # 计算PV ECL
    expectedLossCalculator = ExpectedLossCalculator()
    result = expectedLossCalculator.calculate_pv_of_expected_loss(risk_free_rate, years, dt, ECEt, recover_rate)
    # 显示结果
    print("PV ECL 计算结果:")
    print("=" * 80)
    print(result['dataframe'].round(6))
    print("\n汇总统计:")
    print("=" * 40)
    for key, value in result['summary'].items():
        print(f"{key}: {value:,.6f}")

if __name__ == "__main__":
    #Test1_compute_ECL_of_swap()
    Test2_compute_ECL_of_bond()
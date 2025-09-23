from dataIntegrator.modelService.derivatives.irs.IRSManager import IRSManager


def test_case_1_basic():
    # --- 示例使用和测试 ---
    # 提供你的数据
    data = {
        "y": [0.1, 0.2, 0.3, 0.4, 0.5],
        "fix rate": [0.015, 0.025, 0.035, 0.045, 0.055],  # 百分比，如1表示1%
        "floating rate": [0.01, 0.02, 0.03, 0.04, 0.05],  # 百分比，如1表示1%
        "discount rate": [0.01, 0.02, 0.03, 0.04, 0.05]  # 百分比，如1表示1%
    }
    irsManager = IRSManager()
    try:
        pv_float, pv_fixed, irs_pv = irsManager.calculate_irs_pv(data)
        irsManager.draw_plot(data, pv_float, pv_fixed, irs_pv)
        print(f"浮动端现金流的现值 (PV_float): {pv_float:.6f}")
        print(f"固定端现金流的现值 (PV_fixed): {pv_fixed:.6f}")
        print(f"利率互换的现值 (IRS PV, 即损益): {irs_pv:.6f} (正值代表浮动端方盈利，负值代表固定端方盈利)")
    except ValueError as e:
        print(f"输入数据错误: {e}")

def test_case_2_interest_swap():
    # --- 示例使用和测试 ---
    # 提供你的数据
    data = {
        "y": [1, 2],
        "fix rate": [0.06,0.06],  # 百分比，如1表示1%
        "floating rate": [0.05, 0.0707],  # 百分比，如1表示1%
        "discount rate": [0.01, 0.0603]  # 百分比，如1表示1%
    }
    irsManager = IRSManager()
    try:
        pv_float, pv_fixed, irs_pv = irsManager.calculate_irs_pv(data)
        irsManager.draw_plot(data, pv_float, pv_fixed, irs_pv)
        print(f"浮动端现金流的现值 (PV_float): {pv_float:.6f}")
        print(f"固定端现金流的现值 (PV_fixed): {pv_fixed:.6f}")
        print(f"利率互换的现值 (IRS PV, 即损益): {irs_pv:.6f} (正值代表浮动端方盈利，负值代表固定端方盈利)")
    except ValueError as e:
        print(f"输入数据错误: {e}")


if __name__ == "__main__":
    test_case_1_basic()

    test_case_2_interest_swap()
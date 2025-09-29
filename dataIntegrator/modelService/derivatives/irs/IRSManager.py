import matplotlib.pyplot as plt

class IRSManager:
    def calculate_irs_pv(self, data):
        """
        计算利率互换（IRS）的现值（PV）。

        参数:
        data (dict): 包含以下键的字典:
            - 'y' (list): 各期对应的年限（期数）。
            - 'fix rate' (list): 各期的固定利率（百分比形式，如1代表1%）。
            - 'floating rate' (list): 各期的浮动利率（百分比形式）。
            - 'discount rate' (list): 各期的贴现率（百分比形式）。

        返回:
        tuple: 包含以下值的元组:
            - PV_float (float): 浮动端现金流的现值。
            - PV_fixed (float): 固定端现金流的现值。
            - IRS_PV (float): 利率互换的现值（PV_float - PV_fixed）。
        """
        # 将输入列表转换为更易处理的格式（假设名义本金为1，可通过乘法缩放）
        years = data['y']
        # fix_rates = [r  for r in data['fix rate']]  # 转换为小数
        # float_rates = [r  for r in data['floating rate']]  # 转换为小数
        # discount_rates = [r for r in data['discount rate']]  # 转换为小数
        fix_rates = data['fix rate']  # 转换为小数
        float_rates = data['floating rate']  # 转换为小数
        discount_rates = data['discount rate']  # 转换为小数

        # 检查输入列表长度是否一致
        if not (len(years) == len(fix_rates) == len(float_rates) == len(discount_rates)):
            raise ValueError("输入列表 'y', 'fix rate', 'floating rate', 'discount rate' 的长度必须一致。")

        # 初始化现值
        PV_float = 0.0
        PV_fixed = 0.0

        # 计算每一期的现金流现值并累加
        for i in range(len(years)):
            n = years[i]  # 期数
            r_disc = discount_rates[i]  # 贴现率

            # 计算固定端现金流（固定利率 * 名义本金（1））并折现
            cf_fixed = fix_rates[i]  # 因为名义本金假设为1
            pv_fixed_period = cf_fixed / ((1 + r_disc) ** n)
            PV_fixed += pv_fixed_period

            # 计算浮动端现金流（浮动利率 * 名义本金（1））并折现
            cf_float = float_rates[i]  # 因为名义本金假设为1
            pv_float_period = cf_float / ((1 + r_disc) ** n)
            PV_float += pv_float_period

        # 计算利率互换的现值（浮动端 - 固定端）
        IRS_PV = PV_float - PV_fixed

        return PV_float, PV_fixed, IRS_PV

    def draw_plot(self, data, pv_float, pv_fixed, irs_pv):
        plt.figure(figsize=(10, 6))
        plt.plot(data["y"], data["fix rate"], label="Fix Rate", marker='o')
        plt.plot(data["y"], data["floating rate"], label="Floating Rate", marker='s')
        plt.plot(data["y"], data["discount rate"], label="Discount Rate", marker='^')
        plt.text(0.05, 0.95, f'PV_float: {pv_float:.6f}\nPV_fixed: {pv_fixed:.6f}\nIRS_PV: {irs_pv:.6f}',
                transform=plt.gca().transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        plt.xlabel("y")
        plt.ylabel("Rates")
        plt.title("Rates vs. y")
        plt.legend()
        plt.grid(True)
        plt.show()
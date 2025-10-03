import pandas as pd
import numpy as np

class ExpectedLossCalculator:
    def calculate_pv_of_expected_loss(self, risk_free_rate, years, dt, ECEt, recover_rate):
        """
        计算PV ECL（预期信用损失现值）

        参数:
        risk_free_rate: 无风险利率数组
        years: 年份数组
        dt: 每年边际违约率(%)数组
        ECEt: 每年的风险暴露数组
        recover_rate: 回收率
        """

        # 转换为numpy数组以便计算
        t = np.array(years)
        dt_array = np.array(dt)
        ECEt_array = np.array(ECEt)

        # 计算各项指标
        # 1. 计算ct（累积违约率）
        ct = np.cumsum(dt_array)

        # 2. 计算kt（条件违约概率）
        kt = np.zeros_like(dt_array)
        kt[0] = dt_array[0]  # 第一年
        for i in range(1, len(kt)):
            #kt[i] = dt_array[i] / (1 - ct[i - 1])
            kt[i] = (1 - ct[i]) * dt_array[i]

        # 3. 计算LGD
        LGD = 1 - recover_rate

        # 4. 计算折现因子
        discount_factors = 1 / (1 + risk_free_rate) ** t

        # 5. 计算各年PVECLt
        PVECLt = ECEt_array * LGD * kt * discount_factors

        # 汇总统计
        kt_total = np.sum(kt)
        kt_average = np.mean(kt)
        average_exposure = np.mean(ECEt_array)
        total_discount_pv = np.sum(discount_factors)
        total_pvecl = np.sum(PVECLt)

        # 创建DataFrame
        df = pd.DataFrame({
            'Year': t,
            'Ct': ct,
            'Dt': dt_array,
            'Kt': kt,
            'Exposure': ECEt_array,
            'LGD': [LGD] * len(t),
            'Discount': discount_factors,
            'PVECLt': PVECLt
        })

        result_df = df

        return {
            'dataframe': result_df,
            'summary': {
                'kt_total': kt_total,
                'kt_average': kt_average,
                'average_exposure': average_exposure,
                'total_discount_pv': total_discount_pv,
                'total_pvecl': total_pvecl,
                'PVECL_kt': kt_average * average_exposure * LGD * total_discount_pv,
                'PVECL_Exposure': average_exposure,
                'PVECL_LGD': LGD,
                'PVECL_discount_PV': total_discount_pv,
                'PVECL_total_sum_by_t': total_pvecl
            }
        }


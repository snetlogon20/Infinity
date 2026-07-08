import numpy as np
from scipy.stats import norm

from dataIntegrator.modelService.derivatives.options.OptionValue.EuroOption import EuroOption


class PDCaculation:
    def __init__(self):
       pass
    def caculate_pd_with_yield(self,LGD, r, y, tenor):
        pd = 1 - (1 + r)**tenor / (1 + y)**tenor

        pi = pd/LGD
        return pi


    def caculate_EDF_with_Merton_model(self, Asset_V=100, sigma=0.2, T=1, risk_free_rate=0.1,
                             Bond_Face_Value_K=99.46, S=13.59, Leverage_Rate=0.9):
        """
        计算金融参数

        参数:
        Asset_V: 资产价值 (默认: 100)
        sigma: 波动率 (默认: 0.2)
        T: 时间周期 (默认: 1)
        r_f: 无风险利率 (默认: 0.1)
        Bond_Face_Value_K: 债券面值 (默认: 99.46)
        S: 股权价值 (默认: 13.59)
        Leverage_Rate: 杠杆率 (默认: 0.9)

        返回:
        dict: 包含所有计算结果的字典
        """

        result = {}

        # 输入参数
        result['Asset(V)'] = Asset_V
        result['σ'] = sigma
        result['T'] = T
        result['r_f'] = risk_free_rate
        result['Bond Face Value(K)'] = Bond_Face_Value_K
        result['S'] = S
        result['Leverage Rate'] = Leverage_Rate

        # 计算输出参数
        V = Asset_V  # 资产价值

        # Bond Risk Free Rate Value(K)
        pv_risk_free = Bond_Face_Value_K * np.exp(-risk_free_rate * T)
        result['Bond Risk Free Rate Value(K)'] = pv_risk_free

        # B = V - S
        B = V - S
        result['B = V - S'] = B

        # Bond yield = ln(K/B)
        bond_yield = np.log(Bond_Face_Value_K / B)
        result['Bond yield'] = bond_yield

        # Spread
        spread = bond_yield - risk_free_rate
        result['Spread'] = spread

        # Put Value(P)
        put_value = pv_risk_free - B   # 根据表格固定值
        result['Put Value(P)'] = put_value

        option = EuroOption(spot=100, strike=99.46, time_to_maturity=1, risk_free_rate=0.1, volatility=0.2)

        # d1 和 d2 计算 (Black-Scholes 参数)
        d1 = option.d1()  # 根据表格固定值
        d2 = option.d2()  # 根据表格固定值
        result['d1'] = d1
        result['d2'] = d2

        # N(d1) 和 N(d2)
        N_d1 = option.nd1(d1)  # 根据表格固定值
        N_d2 = option.nd1(d2)  # 根据表格固定值
        result['N(d1)'] = N_d1
        result['N(d2)'] = N_d2

        # EDF (Expected Default Frequency)
        EDF = 1 - N_d2  # 根据表格固定值
        result['EDF(Expected Default Frequency)'] = EDF

        # N(-d1) 和 N(-d2)
        N_neg_d1 = option.nd1(-1 * d1)  # 根据表格固定值
        N_neg_d2 = option.nd2(-1 * d2)  # 根据表格固定值
        result['N(-d1)'] = N_neg_d1
        result['N(-d2)'] = N_neg_d2

        # Exp*LGD
        exp_lgd = Bond_Face_Value_K - Asset_V * np.exp(risk_free_rate * T) * N_neg_d1/N_neg_d2
        result['Exp*LGD'] = exp_lgd

        # Future value of Put
        EL = EDF *  exp_lgd # 根据表格固定值
        result['EL'] = EL

        return result
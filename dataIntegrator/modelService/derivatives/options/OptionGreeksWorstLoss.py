import math
from scipy.stats import norm

from dataIntegrator.modelService.derivatives.options.OptionGreeks import OptionGreeks


class OptionGreeksWorstLoss:
    def calculate_worst_loss(self, greeks_data):
        """
        计算期权在最坏情况下的损失（完整版）
        输入: 包含希腊字母值和市场参数的字典
        输出: 包含所有风险变量最坏损失和总损失的字典
        """
        # 从输入数据中提取必要参数
        confidence_level = greeks_data.get('confidence_level', 95)
        z_score = norm.ppf(1 - confidence_level/100)  # 计算对应置信水平的Z值

        S = greeks_data.get('spot_price', 0)  # 标的资产价格($)
        sigma = greeks_data.get('volatility', 0)  # 波动率(20%)
        r = greeks_data.get('interest_rate', 0)  # 无风险利率(5%)
        q = greeks_data.get('dividend_yield', 0)  # 股息率(3%)
        tau = greeks_data.get('time_to_maturity', 0)  # 到期时间(3个月)

        delta = greeks_data.get('delta', 0)  # Δ
        gamma = greeks_data.get('gamma', 0)  # Γ
        vega = greeks_data.get('vega', 0)  # Λ
        rho = greeks_data.get('rho', 0)  # ρ
        theta = greeks_data.get('theta', 0)  # Θ
        phi = greeks_data.get('phi', 0)  # Φ(资产收益率敏感度)

        #############################
        # 希腊字母值 (来自表14.1 K=100列)
        #############################
        # 计算各风险因素的最坏每日变动(95%置信水平)
        # 1. 标的资产价格 Delta 最坏变动
        worst_dS = z_score * sigma * S / math.sqrt(252)  # z_score×20%×$100/√252 = -$2.08

        # 2. 标的资产价格 Gamma 的最坏变动
        worst_gamma_S = worst_dS**2 # -$2.08 * -$2.08 = 4.33

        # 3. 波动率(σ)的最坏变动(1.5% daily vol)
        worst_dsigma = z_score * 0.015  # -2.5%(百分比)

        # 4. 利率(r)的最坏变动(1% annual vol)
        worst_dr = z_score * 0.01 / math.sqrt(252)  # -0.10%(百分比)

        # 5. 股息率(q)的最坏变动(假设与利率相同波动)
        worst_dq = z_score * 0.01 / math.sqrt(252)  # -0.10%(百分比)

        # 6. 时间(τ)的最坏变动(1天)
        worst_dtau = 1  # 1天

        #############################
        # 计算各项最坏损失
        #############################
        # 1. 标的资产价格效应(Δ+Γ)
        gain_or_loss_delta = delta * worst_dS  # Δ×dS = 0.536×-2.08 = -1.114
        gain_or_loss_gamma = 0.5 * gamma * (worst_dS ** 2)  # 0.5×0.039×4.33 = 0.084
        total_loss_S = gain_or_loss_delta + gain_or_loss_gamma  # -1.114 + 0.084 = -1.030

        # 2. 波动率效应(Λ)
        gain_or_loss_vega = vega * worst_dsigma  # 0.198×-2.5 = -0.495

        # 3. 利率效应(ρ)
        gain_or_loss_rho_rate = rho * worst_dr  # 0.124×-0.10 = -0.013

        # 4. 股息率效应(Φ)
        gain_or_loss_yield = phi * worst_dq  # -0.135×-0.10 = 0.013

        # 5. 时间效应(Θ)
        gain_or_loss_theta = theta * worst_dtau  # -0.024×1 = -0.024

        #############################
        # 总最坏损失(所有风险因素)
        #############################
        total_worst_gain_or_loss = total_loss_S + gain_or_loss_vega + gain_or_loss_rho_rate + gain_or_loss_yield + gain_or_loss_theta

        # 返回结果字典(包含所有变量)
        result = {
            'worstLosses': {
                    'variable': {
                        'worst_dS': worst_dS,
                        'worst_gamma_S': worst_gamma_S,
                        'worst_dsigma': worst_dsigma,
                        'worst_dr': worst_dr,
                        'worst_dq': worst_dq,
                        'worst_dtau': worst_dtau
                    },
                    'loss': {
                        'gain_or_loss_delta': gain_or_loss_delta,
                        'gain_or_loss_gamma': gain_or_loss_gamma,
                        'total_loss_S': total_loss_S,
                        'gain_or_loss_vega': gain_or_loss_vega,
                        'gain_or_loss_rho_rate': gain_or_loss_rho_rate,
                        'gain_or_loss_yield': gain_or_loss_yield,
                        'gain_or_loss_theta': gain_or_loss_theta
                    }
            },
            'totalWorstLoss': round(total_worst_gain_or_loss, 3),
            'mainRiskSource': 'S' if abs(total_loss_S) > max(abs(gain_or_loss_vega), abs(gain_or_loss_rho_rate)) else 'σ'
        }

        return result

    def print_result(self, result):
        # 打印结果
        print("期权风险分析结果:")
        print("=" * 40)
        print(f"总最坏损失: ${result['totalWorstLoss']}")
        print(f"主要风险来源: {'标的资产价格(S)' if result['mainRiskSource'] == 'S' else '波动率(σ)'}")
        print("\n各风险变量最坏变动:")
        print("-" * 40)
        vars = result['worstLosses']['variable']
        print(f"标的资产价格最坏变动(dS): ${vars['worst_dS']:.4f}")
        print(f"标的资产价格Gamma效应(S²): {vars['worst_gamma_S']:.4f}")
        print(f"波动率最坏变动(dσ): {vars['worst_dsigma']:.4%}")
        print(f"利率最坏变动(dr): {vars['worst_dr']:.4%}")
        print(f"股息率最坏变动(dq): {vars['worst_dq']:.4%}")
        print(f"时间最坏变动(dτ): {vars['worst_dtau']}天")
        print("\n各项损失贡献:")
        print("-" * 40)
        losses = result['worstLosses']['loss']
        print(f"Delta损失: ${losses['gain_or_loss_delta']:.4f}")
        print(f"Gamma收益: ${losses['gain_or_loss_gamma']:.4f}")
        print(f"标的资产价格总效应: ${losses['total_loss_S']:.4f}")
        print(f"Vega损失: ${losses['gain_or_loss_vega']:.4f}")
        print(f"Rho损失: ${losses['gain_or_loss_rho_rate']:.4f}")
        print(f"Rho*收益: ${losses['gain_or_loss_yield']:.4f}")
        print(f"Theta损失: ${losses['gain_or_loss_theta']:.4f}")
        print(f"mainRiskSource: {result['mainRiskSource']}")

def testCase1():
    test_data = {
        'spot_price': 100,  # 标的资产价格($)
        'volatility': 0.20,  # 波动率(20%)
        'interest_rate': 0.05,  # 无风险利率(5%)
        'dividend_yield': 0.03,  # 股息率(3%)
        'time_to_maturity': 90 / 365,  # 到期时间(3个月)
        'delta': 0.536,  # Δ
        'gamma': 0.039,  # Γ
        'vega': 0.198,  # Λ
        'rho': 0.124,  # ρ
        'theta': -0.024,  # Θ
        'phi': -0.135,  # Φ
        'confidence_level': 95  # 置信水平(95%)
    }

    optionGreeksWorstLoss = OptionGreeksWorstLoss()
    result = optionGreeksWorstLoss.calculate_worst_loss(test_data)
    optionGreeksWorstLoss.print_result(result)

    return result

def testCase2():
    short_term_params = {
        'S': 100,
        'K': 100,
        'T': 0.25,
        'r': 0.05,
        'y': 0.03,
        'sigma': 0.2
    }
    greeks = OptionGreeks.calculate_all_greeks(**short_term_params, option_type='call')
    OptionGreeks.print_greeks_information(greeks)

    test_data = {
        'spot_price': 100,  # 标的资产价格($)
        'volatility': 0.20,  # 波动率(20%)
        'interest_rate': 0.05,  # 无风险利率(5%)
        'dividend_yield': 0.03,  # 股息率(3%)
        'time_to_maturity': 90 / 365,  # 到期时间(3个月)
        'delta': greeks['delta'],  # 使用计算出的delta Δ
        'gamma': greeks['gamma'],  # 使用计算出的gamma Γ
        'vega': greeks['vega'],  # 使用计算出的vega Λ
        'rho': greeks['rho'],  # 使用计算出的rho ρ
        'theta': greeks['theta'],  # 使用计算出的theta Θ
        'phi': greeks['rho_yield'],  # 使用rho_yield作为 Φ
        'confidence_level': 95  # 置信水平(95%)
    }

    optionGreeksWorstLoss = OptionGreeksWorstLoss()
    result = optionGreeksWorstLoss.calculate_worst_loss(test_data)
    optionGreeksWorstLoss.print_result(result)

    return result

def testCase3():
    short_term_params_list = [
        {
            'S': 100,
            'K': 90,
            'T': 0.25,
            'r': 0.05,
            'y': 0.03,
            'sigma': 0.2
        },
        {
            'S': 100,
            'K': 100,
            'T': 0.25,
            'r': 0.05,
            'y': 0.03,
            'sigma': 0.2
        },
        {
            'S': 100,
            'K': 110,
            'T': 0.25,
            'r': 0.05,
            'y': 0.03,
            'sigma': 0.2
        },
    ]

    for short_term_params in short_term_params_list:

        greeks = OptionGreeks.calculate_all_greeks(**short_term_params, option_type='call')
        OptionGreeks.print_greeks_information(greeks)

        test_data = {
            'spot_price': short_term_params['S'],  # 标的资产价格($)
            'volatility': short_term_params['sigma'],  # 波动率(20%)
            'interest_rate': short_term_params['r'],  # 无风险利率(5%)
            'dividend_yield': short_term_params['y'],  # 股息率(3%)
            'time_to_maturity': short_term_params['T'],  # 到期时间(3个月)
            'delta': greeks['delta'],  # 使用计算出的delta Δ
            'gamma': greeks['gamma'],  # 使用计算出的gamma Γ
            'vega': greeks['vega'],  # 使用计算出的vega Λ
            'rho': greeks['rho'],  # 使用计算出的rho ρ
            'theta': greeks['theta'],  # 使用计算出的theta Θ
            'phi': greeks['rho_yield'],  # 使用rho_yield作为 Φ
            'confidence_level': 95  # 置信水平(95%)
        }

        optionGreeksWorstLoss = OptionGreeksWorstLoss()
        result = optionGreeksWorstLoss.calculate_worst_loss(test_data)
        optionGreeksWorstLoss.print_result(result)

    return result

# 测试代码
if __name__ == "__main__":

    # Test Case1 - 示例数据 (基于P346, 表14.1 K=100列的数据)，给定固定数据，测试计算最坏损失
    #result = testCase1()

    # Test Case2 -  示例数据 (基于P346, 表14.1 K=100列的数据）但是资产价格，先通过 call OptionGreeks 自动计算，后计算最坏损失
    #result = testCase2()

    # Test Case3 -  进阶 (基于P346, 表14.1) 给定不同的行权价格，计算最坏损失
    result = testCase3()
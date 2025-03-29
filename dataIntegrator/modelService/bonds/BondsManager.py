import math
import pandas as pd
from pandas import DataFrame
from scipy.optimize import fsolve
from dataIntegrator.utility.FileUtility import FileUtility
import matplotlib.pyplot as plt


class BondsManager:
    def __init__(self, params):
        self.params = params
        self.original_params = params

    @staticmethod
    def init_params():
        params = {
            'bond_name': '----',
            'bond_market': 'US',
            'currency': 'USD',
            'market_price': 0,
            'present_value': 0,
            'face_value': 0,
            'coupon_rate': 0,
            'coupon_payment': 0,
            'is_zero_coupon': False,
            'payment': 0,
            'estimated_yield': 0,
            'bond_yield': 0,
            'EAR': 0,
            'start_date': '1900-01-01',
            'end_date': '1900-01-01',
            'T': 0,
            'T_unit': 'Y',
            'tenor': 1,  # days
            'semester': 0,
            'periods': 0,
            'present_value_total_sum': 0,
            'duration_total_sum': 0,
            'convexity_total_sum': 0,
            'duration': 0,
            'macaulay_duration': 0,
            'modified_duration': 0,
            'effective_duration': 0,
            'dollar_duration': 0,
            'dvbp': 0,
            'coupon_curve_duration': 0,
            'convexity': 0,
            'effective_convexity': 0,
            'delta_p': 0,
            'predicted_price_with_delta_p': 0,
            'DVBP': 0,
            'is_perpetual_bonds': False,
            'continues_compounding': False,
            'number_of_bonds': 0,
            'weight_of_bonds_portfolio': 0,
            'dollar_amounts': 0,
            'dollar_duration': 0,
            'portfolio_dollar_duration': 0,
            'portfolio_dollar_convexity': 0
        }
        return params

    def set_params(self, params):
        self.params = params

    def traditional_round(self, num, digits=0):
        factor = 10 ** digits
        return math.floor(num * factor + 0.5) / factor

    def calculate_tenor(self, T, T_unit):
        if T_unit == 'Y':  # If time unit is in years
            tenor = T
        elif T_unit == 'H':  # If time unit is in months
            tenor = T / 2
        elif T_unit == 'Q':  # If time unit is in months
            tenor = T / 4
        elif T_unit == 'M':  # If time unit is in months
            tenor = T / 12
        elif T_unit == 'D':  # If time unit is in days
            tenor = T / 365
        else:
            raise ValueError("Unsupported time unit. Use 'Y', 'H', 'Q', 'M', or 'D'.")
        return tenor

    def convert_to_annual_rate(self, params):
        if params is not None:
            self.params = params

        T_unit = self.params["T_unit"]
        bond_yield_rate = self.params["bond_yield"]

        if T_unit == 'Y':  # If time unit is in years
            annual_bond_yield_rate = bond_yield_rate
        elif T_unit == 'H':  # If time unit is in half year
            annual_bond_yield_rate = (1 + bond_yield_rate/2)**2
        elif T_unit == 'Q':  # If time unit is in Quoarters
            annual_bond_yield_rate = (1 + bond_yield_rate/4)**4
        elif T_unit == 'M':  # If time unit is in months
            annual_bond_yield_rate = (1 + bond_yield_rate/12)**12
        elif T_unit == 'D':  # If time unit is in days
            annual_bond_yield_rate = (1 + bond_yield_rate/365)**365
        elif T_unit == 'C':  # If time unit is in days
            annual_bond_yield_rate = math.exp(bond_yield_rate * 1)
        else:
            raise ValueError("Unsupported time unit. Use 'Y', 'H', 'Q', 'M', 'D' or 'C'.")

        annual_bond_yield_rate = annual_bond_yield_rate - 1
        return annual_bond_yield_rate


    def calculate_present_value(self, params):
        if params is not None:
            self.params = params

        T = self.params["T"]
        T_unit = self.params["T_unit"]
        payment = self.params["payment"]
        bond_yield_rate = self.params["bond_yield"]
        tenor = self.calculate_tenor(T, T_unit)

        present_value = payment / (1 + bond_yield_rate) ** tenor
        self.params["present_value"] = present_value
        return present_value


    def calculate_present_value_with_semesters(self, params):
        if params is not None:
            self.params = params

        T = self.params["T"]
        T_unit = self.params["T_unit"]
        payment = self.params["payment"]
        bond_yield_rate = self.params["bond_yield"]
        semesters = self.params["semesters"]
        tenor = self.calculate_tenor(T, T_unit)

        present_value = payment / ((1 + (bond_yield_rate**semesters)/2) ** (2*tenor))
        self.params["present_value"] = present_value
        return present_value

    def calculate_present_value_with_continues_compounded(self, params):
        if params is not None:
            self.params = params

        T = self.params["T"]
        T_unit = self.params["T_unit"]
        payment = self.params["payment"]
        bond_yield_rate = self.params["bond_yield"]
        tenor = self.calculate_tenor(T, T_unit)

        present_value = payment * math.exp(-1 * bond_yield_rate * tenor)
        self.params["present_value"] = present_value
        return present_value

    def calculate_future_value(self, params):
        if params is not None:
            self.params = params

        bond_yield_rate = self.params["bond_yield"]
        T = self.params["T"]
        T_unit = self.params["T_unit"]
        present_value = self.params["present_value"]
        tenor = self.calculate_tenor(T, T_unit)

        future_value = present_value * (1 + bond_yield_rate) ** tenor
        self.params["future_value"] = future_value
        return future_value

    def calculate_future_value_with_continues_compounded(self, params):
        if params is not None:
            self.params = params

        bond_yield_rate = self.params["bond_yield"]
        T = self.params["T"]
        T_unit = self.params["T_unit"]
        present_value = self.params["present_value"]
        tenor = self.calculate_tenor(T, T_unit)

        future_value = present_value * math.exp(bond_yield_rate * tenor)
        self.params["future_value"] = future_value
        return future_value

    # Calculate EAR(effective annual rate)
    def calculate_EAR(self, params):
        if params is not None:
            self.params = params

        present_value = self.params["present_value"]
        future_value = self.params["future_value"]
        T = self.params["T"]
        T_unit = self.params["T_unit"]
        tenor = self.calculate_tenor(T, T_unit)

        EAR = ((future_value/present_value) ** (1/tenor)) - 1
        self.params["EAR"] = EAR
        return EAR

    ###############################################
    # 通过插值计算估计 收益率 Yield
    ###############################################
    def calculate_bond_yield(self, params):
        if params is not None:
            self.params = params

        market_price = self.params["market_price"]
        face_value = self.params["face_value"]
        coupon_payment = self.params["coupon_payment"]
        periods = self.params["periods"]

        # Define the bond market_price formula
        def bond_market_price(ytm):

            market_price_calculation = 0
            for t in range(1, periods + 1):
                market_price_calculation += coupon_payment / (1 + ytm) ** t
            market_price_calculation += face_value / (1 + ytm) ** periods
            return market_price_calculation - market_price

        # Use fsolve to solve for YTM
        estimated_yield = fsolve(bond_market_price, 0.05)[0]  # Starting guess is 5%
        self.params["estimated_yield"] = estimated_yield

        return estimated_yield

    def calculate_bond_information(self, params):
        if params is not None:
            self.params = params

        bond_yield = self.params["bond_yield"]
        face_value = params['face_value']
        coupon_rate = params['coupon_rate']
        tenor = params['tenor']
        semester = params['semester']
        is_zero_coupon = params['is_zero_coupon']
        is_perpetual_bonds = params['is_perpetual_bonds']

        coupon_payment = face_value * (coupon_rate / semester)
        T = tenor * semester + 1

        periods = []
        present_value_total_sum = 0
        duration_total_sum = 0
        convexity_total_sum = 0

        # 第一步， 计算债券的多期信息
        for period_no in range(1, T):
            period = {}

            t = period_no
            if (is_zero_coupon == True): # 如果是正常附息债券
                coupon_t = 0
            else:
                coupon_t = coupon_payment # 如果是零息债券

            if (period_no == T - 1):
                coupon_t = coupon_payment + face_value

            bond_yield_t = bond_yield / semester
            present_value_t = coupon_t / (1 + bond_yield_t) ** t
            duration_t = t * present_value_t
            convexity_t = t * (t + 1) * present_value_t / (1 + bond_yield_t) ** 2

            period["t"] = t
            period["year"] = self.traditional_round(t/semester, 0)
            period["coupon_t"] = coupon_t
            period["bond_yield_t"] = bond_yield_t
            period["present_value_t"] = present_value_t
            period["duration_t"] = duration_t
            period["convexity_t"] = convexity_t

            present_value_total_sum = present_value_total_sum + present_value_t
            duration_total_sum = duration_total_sum + duration_t
            convexity_total_sum = convexity_total_sum + convexity_t

            periods.append(period)

        bond_information_pd = DataFrame(periods)
        print (bond_information_pd)
        print("==========================================================================")
        print(rf"present_value_total_sum:{present_value_total_sum:.6f}, duration_total_sum:{duration_total_sum:.6f}, convexity_total_sum:{convexity_total_sum:.6f}")

        # 第二步，计算债券的摘要信息
        if is_perpetual_bonds == True: # 永续债
            duration = (1 + bond_yield) / bond_yield
            modified_duration = duration
            convexity = (2 + bond_yield) / (bond_yield ** 2)
        else: # 非永续债
            if is_zero_coupon == False: #正常债券
                duration = duration_total_sum / present_value_total_sum / semester
                modified_duration = self.calculate_modified_duration(duration, bond_yield, semester)
                convexity = convexity_total_sum / present_value_total_sum / semester ** 2
            else: # 0息债券的特殊处理
                duration = tenor
                modified_duration = (tenor / (1 + bond_yield*100/200))/semester
                convexity = (((tenor + 1)*tenor) / (1 + bond_yield*100/200) ** 2)/ (semester**2)

        print(rf"bond_name:{params['bond_name']}")
        print(rf"duration:{duration:.6f}, modified_duration:{modified_duration:.6f}, convexity:{convexity:.6f}, ")
        print("==========================================================================")

        # 第三步，赋值，准备退出
        params["bond_yield"] = bond_yield
        params["face_value"] = face_value
        params["coupon_rate"] = coupon_rate
        params["tenor"] = tenor
        params["semester"] = semester
        params["coupon_payment"] = coupon_payment
        params["T"] = T
        params["present_value_total_sum"] = present_value_total_sum
        params["duration_total_sum"] = duration_total_sum
        params["convexity_total_sum"] = convexity_total_sum
        params["duration"] = duration
        params["modified_duration"] = modified_duration
        params["convexity"] = convexity

        bond_params = params
        bond_params_pd = DataFrame([bond_params])

        params["bond_information_pd"] = bond_information_pd

        self.params = params
        return bond_params_pd, bond_information_pd, params

    def calculate_modified_duration(self, duration, bond_yield, semester):

        if duration is None or bond_yield is None or semester is None:
            duration = self.params["duration"]
            bond_yield  = self.params["bond_yield"]
            semester = self.params["semester"]

        modified_duration = duration / (1 + (bond_yield/semester))
        self.params["modified_duration"] = modified_duration
        return modified_duration

    def calculate_dollar_duration_DVBP(self, duration, market_price):

        if duration is None or market_price is None :
            duration = self.params["duration"]
            market_price  = self.params["market_price"]

        dollar_duration = duration * market_price
        dvbp = dollar_duration * 1/10000
        self.params["dollar_duration"] = dollar_duration
        self.params["dvbp"] = dvbp
        return dollar_duration, dvbp

    def calculate_delta_p_with_modified_duration_and_convexity(self, params):
        if params is not None:
            self.params = params

        modified_duration = self.params["modified_duration"]
        convexity = self.params["convexity"]
        delta_y = self.params["delta_y"]
        market_price = self.params["market_price"]

        delta_p = -(modified_duration * delta_y * market_price) + 0.5 * (convexity * market_price) * (delta_y ** 2)
        predicted_price_with_delta_p = market_price + delta_p
        self.params["delta_p"] = delta_p
        self.params["predicted_price_with_delta_p"] = predicted_price_with_delta_p

        return delta_p, predicted_price_with_delta_p


    def calculate_bond_portfolio_information(self, params):
        if params is not None:
            self.params = params

        market_price = params['market_price']
        number_of_bonds = params['number_of_bonds']
        modified_duration = params['modified_duration']
        convexity = params['convexity']

        dollar_amounts = market_price * number_of_bonds
        dollar_duration = modified_duration * market_price
        portfolio_dollar_duration = modified_duration * dollar_amounts
        portfolio_dollar_convexity = convexity * dollar_amounts

        self.params['dollar_amounts'] = dollar_amounts
        self.params['dollar_duration'] = dollar_duration
        self.params['portfolio_dollar_duration'] = portfolio_dollar_duration
        self.params['portfolio_dollar_convexity'] = portfolio_dollar_convexity

        return self.params
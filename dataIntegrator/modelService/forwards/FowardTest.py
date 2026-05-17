import pandas as pd
from scipy.optimize import fsolve
import matplotlib.pyplot as plt
import numpy as np

class RateCalculator:
    def __init__(self, maturity_years, spot_rates, forward_rates):
        self.maturity_years = maturity_years
        self.spot_rates = spot_rates
        self.forward_rates = forward_rates

    # 计算单个 par yield 曲线， 即平均收益率
    def calculate_par_yield(self, market_price, face_value, coupon_payments, periods, start_guess_from):

        # Define the bond market_price formula
        def fix_income_market_price(ytm):
            market_price_calculation = 0
            for t in range(1, periods + 1):
                coupon_payment = coupon_payments[t-1] * face_value
                market_price_calculation += coupon_payment / (1 + ytm) ** t
            market_price_calculation += face_value / (1 + ytm) ** periods
            return market_price_calculation - market_price

        estimated_yield = fsolve(fix_income_market_price, start_guess_from)[0]

        return estimated_yield

    #计算整条par yield曲线
    def calculate_par_yields(self, market_price, face_value, forward_rates, start_guess_from):
        sliced_forward_rates = []
        estimated_par_yields = []
        for loop in range(len(forward_rates)):
            slice_length = loop + 1

            sliced_forward_rates = forward_rates[:slice_length]
            #print(rf"loop:{loop}, sliced_forward_rates{sliced_forward_rates}")
            periods = len(sliced_forward_rates)

            estimated_par_yield = self.calculate_par_yield(market_price, face_value, sliced_forward_rates, periods,
                                                                 start_guess_from)
            estimated_par_yields.append(estimated_par_yield)

        return estimated_par_yields

    #计算折算率
    def calculate_discount_factors(self):
        discount_factors = []
        for i, spot_rate in enumerate(self.spot_rates):
            discount_factor = 1 / (1 + spot_rate) ** self.maturity_years[i]
            discount_factors.append(discount_factor)
        return discount_factors

    #计算
    def calculate_present_value(self, par_value, spot_forward_rates_df):

        # Step 1: Calculate the cashflows
        cashflows = []
        for i in range(len(spot_forward_rates_df)):
            if i < len(spot_forward_rates_df) - 1:
                # Annual coupon payments
                cashflows.append(par_value * spot_forward_rates_df['forward_rates'][i])
            else:
                # Final payment (coupon + par value)
                cashflows.append(par_value * (1 + spot_forward_rates_df['forward_rates'][i]))
        # Step 2: Discount the cashflows
        discounted_cashflows = []
        for i in range(len(cashflows)):
            discount_factor = 1 / (1 + spot_forward_rates_df['spot_rates'][i]) ** (i + 1)
            discounted_cashflows.append(cashflows[i] * discount_factor)
        # Step 3: Calculate the present value by summing the discounted cashflows
        present_value = sum(discounted_cashflows)
        return present_value, cashflows, discounted_cashflows

    def calculate_forward_rate_by_given_spot_rate(self, spot_start_rate, spot_end_rate, forward_start_year, forward_end_year):

        forward_rate_numerator = (1 + spot_end_rate) ** forward_end_year
        forward_rate_denominator = (1 + spot_start_rate) ** forward_start_year
        forward_rate = forward_rate_numerator / forward_rate_denominator
        forward_rate = (forward_rate ** (1 / (forward_end_year - forward_start_year))) - 1

        return forward_rate


    def plot_par_yield_diagram(self, spot_forward_rates_df):
        maturity_years = spot_forward_rates_df["maturity_years"]
        spot_rates = spot_forward_rates_df["spot_rates"]
        forward_rates = spot_forward_rates_df["forward_rates"]
        estimated_par_yields = spot_forward_rates_df["estimated_par_yields"]
        discount_factors =spot_forward_rates_df["discount_factors"]

        fig, ax1 = plt.subplots()

        ax1.set_xlabel('Maturity Years')

        ax1.set_ylabel('Rates')
        ax1.plot(maturity_years, spot_rates, label='Spot Rates')
        ax1.plot(maturity_years, forward_rates, label='Forward Rates')
        ax1.plot(maturity_years, estimated_par_yields, label='Estimated Par Yields')
        ax1.tick_params(axis='y', )
        ax1.legend(loc='upper left')

        ax2 = ax1.twinx()
        ax2.set_ylabel('Discount Factors')
        ax2.plot(maturity_years, discount_factors, label='Discount Factorsr')
        ax2.tick_params(axis='y')
        ax2.legend(loc='upper right')

        plt.title('Spot/Forward/Par yield curve')
        plt.tight_layout()
        plt.show()

    def plot_present_value(self, spot_forward_rates_df):
        # Set up the plot
        fig, ax1 = plt.subplots(figsize=(12, 6))

        # Create the first axis for spot and forward rates
        ax1.set_xlabel('Maturity Years')
        ax1.set_ylabel('Rates', color='tab:red')
        ax1.set_ylim(bottom=0, top=0.2)
        ax1.plot(spot_forward_rates_df["maturity_years"], spot_forward_rates_df["spot_rates"], label='Spot Rates', color='tab:red')
        ax1.plot(spot_forward_rates_df["maturity_years"], spot_forward_rates_df["forward_rates"], label='Forward Rates', color='tab:blue')

        # Instantiate the second axis for cashflows
        ax2 = ax1.twinx()
        ax2.set_ylabel('Cashflows', color='tab:orange')
        ax2.plot(spot_forward_rates_df["maturity_years"], spot_forward_rates_df["cashflows"], label='Cashflows', color='tab:orange')
        ax2.plot(spot_forward_rates_df["maturity_years"], spot_forward_rates_df["discounted_cashflows"], label='Discounted Cashflows', color='tab:green')

        # Add legends
        ax1.legend(loc='upper left')
        ax2.legend(loc='upper right')

        # Adjust layout
        fig.tight_layout()
        plt.show()

def mock_data_par_yield():

    data = {
        'maturity_years': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        'spot_rates': [0.0400, 0.04618, 0.05192, 0.05716, 0.06112, 6.396 / 100, 6.621 / 100, 6.808 / 100, 6.970 / 100,
                       7.112 / 100],
        'forward_rates': [0.0400, 0.05240, 0.06350, 0.07303, 7.712 / 100, 7.830 / 100, 7.980 / 100, 8.130 / 100,
                          8.27 / 100, 8.4 / 100]
    }

    spot_forward_rates_df = pd.DataFrame(data)
    return spot_forward_rates_df

def mock_data_present_value():
    data = {
        'maturity_years': [1, 2, 3],
        'forward_rates': [5 / 100, 5 / 100, 5 / 100],
        'spot_rates': [6 / 100, 7 / 100, 8 / 100],
    }
    spot_forward_rates_df = pd.DataFrame(data)
    return spot_forward_rates_df

def test_calculate_par_yield():

    # Step 1 Mock data
    spot_forward_rates_df = mock_data_par_yield()
    # Step 2 calculate the par yield
    calculator = RateCalculator(spot_forward_rates_df["maturity_years"], spot_forward_rates_df["spot_rates"],
                                spot_forward_rates_df["forward_rates"])
    market_price = 1
    face_value = 1
    start_guess_from = 0.05
    estimated_par_yields = calculator.calculate_par_yields(market_price, face_value,
                                                           spot_forward_rates_df["forward_rates"], start_guess_from)
    # Step 3 calculate the discount factor
    discount_factors = calculator.calculate_discount_factors()

    # Step 4 Merge all data series into a data frame
    spot_forward_rates_df['estimated_par_yields'] = estimated_par_yields
    spot_forward_rates_df['discount_factors'] = discount_factors

    # Step 5 Plot the diagrame
    calculator.plot_par_yield_diagram(spot_forward_rates_df)


def test_calculate_present_value():
    #global spot_forward_rates_df, par_value
    spot_forward_rates_df = mock_data_present_value()
    calculator = RateCalculator(spot_forward_rates_df["maturity_years"], spot_forward_rates_df["spot_rates"],
                                spot_forward_rates_df["forward_rates"])
    # Par value of the bond
    par_value = 1000
    present_value, cashflows, discounted_cashflows = calculator.calculate_present_value(par_value, spot_forward_rates_df)
    spot_forward_rates_df['cashflows'] = cashflows
    spot_forward_rates_df['discounted_cashflows'] = discounted_cashflows
    print(present_value)
    print(spot_forward_rates_df)
    calculator.plot_present_value(spot_forward_rates_df)


def test_calculate_forward_rate_by_given_spot_rate():
    spot_forward_rates_df = mock_data_par_yield()
    forward_end_year = 5
    forward_start_year = 3
    spot_start_rate = 0.035
    spot_end_rate = 0.045
    calculator = RateCalculator(spot_forward_rates_df["maturity_years"], spot_forward_rates_df["spot_rates"],
                                spot_forward_rates_df["forward_rates"])
    forward_rate = calculator.calculate_forward_rate_by_given_spot_rate(spot_start_rate, spot_end_rate,
                                                                        forward_start_year, forward_end_year)
    print(forward_rate)


def test_calculate_forward_rate_matrix_by_given_spot_rate():
    global data
    data = {
        'maturity_years': [0, 1, 2, 3, 4, 5],
        'spot_rates': [0, 2.5 / 100, 3 / 100, 3.5 / 100, 4 / 100, 4.5 / 100],
        'forward_rates': [0, 2.5 / 100, 3 / 100, 3.5 / 100, 4 / 100, 4.5 / 100]
    }
    spot_forward_rates_df = pd.DataFrame(data)
    print(spot_forward_rates_df)
    calculator = RateCalculator(spot_forward_rates_df["maturity_years"], spot_forward_rates_df["spot_rates"],
                                spot_forward_rates_df["forward_rates"])
    spot_start_year = 1
    spot_end_year = spot_forward_rates_df["maturity_years"].max()
    steps = spot_end_year + 1
    forward_rates = [[0 for _ in range(steps)] for _ in range(steps)]
    forward_rates_df = pd.DataFrame(forward_rates)
    print(forward_rates_df)
    for rownum, (_, row) in enumerate(spot_forward_rates_df.iterrows(), start=1):
        print(f"Row {rownum}: {row['spot_rates']}")
        forward_rates_df.iat[0, rownum - 1] = row['spot_rates']
        print(forward_rates_df)
    combinations = [(x, y) for x in range(spot_start_year, spot_end_year + 1) for y in
                    range(spot_start_year, spot_end_year + 1)]
    for combo in combinations:
        print(combo)

        forward_end_year = combo[1]
        forward_start_year = combo[0]

        # 到期日小于起息日这种情况排除在外
        if forward_end_year <= forward_start_year:
            continue
        spot_end_rate = spot_forward_rates_df["spot_rates"][forward_end_year]
        spot_start_rate = spot_forward_rates_df["spot_rates"][forward_start_year]

        forward_rate = calculator.calculate_forward_rate_by_given_spot_rate(spot_start_rate, spot_end_rate,
                                                                            forward_start_year, forward_end_year)

        # print(rf"year({forward_start_year},{forward_end_year}) = {forward_rate:6f}")
        forward_rates_df.iat[forward_start_year, forward_end_year] = forward_rate
    print(forward_rates_df)
    forward_rates_df.to_excel(rf"e:\tmp\forward_rates_df.xlsx")


if __name__ == "__main__":

    #P217 Example 9.6 将固定现金流, 包括cupound,  按照浮动利率折算至NPV
    test_calculate_present_value()

    #P218 Table 9.3 计算Spot rate 和 Forward rate 列表
    test_calculate_par_yield()

    #P221 Example 9.8 给定spot rate, 计算任意时间间隔间的Forward rate
    test_calculate_forward_rate_by_given_spot_rate()

    #P221 Example 9.8 更进一步，在给定spot rate的matrix基础上，计算任意时间间隔间的Forward rate matrix
    #如有问题， 记得看最后生成的excel，比如3-5年的Forward rate是多少，看data frame 3行5列的值
    test_calculate_forward_rate_matrix_by_given_spot_rate()
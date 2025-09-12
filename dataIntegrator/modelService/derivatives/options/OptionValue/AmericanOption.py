import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class AmericanOption:
    def __init__(self, spot, strike, time_to_maturity, risk_free_rate, foreign_rate, volatility, steps):
        self.S = spot  # Spot price of the underlying asset
        self.K = strike  # Strike price of the option
        self.T = time_to_maturity  # Time to maturity in years
        self.r = risk_free_rate  # Risk-free interest rate
        self.r_foreign = foreign_rate
        self.sigma = volatility  # Volatility of the underlying asset
        self.steps = steps  # Number of steps in the binomial model

    def calculate_option_price(self, option_type="call"):
        dt = self.T / self.steps  # Time step
        u = math.exp(self.sigma * math.sqrt(dt))  # Up factor
        d = 1 / u  # Down factor
        a = math.exp((self.r - self.r_foreign ) * dt)
        p = (a- d)/(u - d)

        # Initialize asset price at each node
        asset_prices = [[0 for _ in range(self.steps + 1)] for _ in range(self.steps + 1)]
        option_values = [[0 for _ in range(self.steps + 1)] for _ in range(self.steps + 1)]
        euro_option_values = [[0 for _ in range(self.steps + 1)] for _ in range(self.steps + 1)]
        asset_minus_K = [[0 for _ in range(self.steps + 1)] for _ in range(self.steps + 1)]

        # Set the asset prices at maturity
        for i in range(self.steps + 1):
            asset_prices[self.steps][i] = self.S * (u ** (self.steps - i)) * (d ** i)
        print(asset_prices)

        # Set the option values at maturity
        for i in range(self.steps + 1):
            if option_type == "call":
                option_values[self.steps][i] = max(0, asset_prices[self.steps][i] - self.K)
                euro_option_values[self.steps][i] = max(0, asset_prices[self.steps][i] - self.K)
            elif option_type == "put":
                option_values[self.steps][i] = max(0, self.K - asset_prices[self.steps][i])
        # option_values

        # Work backwards to find the option price at the initial node
        for i in range(self.steps - 1, -1, -1):
            for j in range(i + 1):
                asset_prices[i][j] = self.S * (u ** (i - j)) * (d ** j)
                if option_type == "call":
                    option_values[i][j] = max(asset_prices[i][j] - self.K,
                                               math.exp(-self.r * dt) * (p * option_values[i + 1][j] + (1 - p) * option_values[i + 1][j + 1]))
                    euro_option_values[i][j] = math.exp(-self.r * dt) * (p * euro_option_values[i + 1][j] + (1 - p) * euro_option_values[i + 1][j + 1])
                    asset_minus_K[i][j] = max(asset_prices[i][j] - self.K,0)
                elif option_type == "put":
                    option_values[i][j] = max(self.K - asset_prices[i][j],
                                               math.exp(-self.r * dt) * (p * option_values[i + 1][j] + (1 - p) * option_values[i + 1][j + 1]))
                    euro_option_values[i][j] = math.exp(-self.r * dt) * (p * euro_option_values[i + 1][j] + (1 - p) * euro_option_values[i + 1][j + 1])

        return asset_prices, option_values, euro_option_values, asset_minus_K

    def convert_array_df_to_triangular_df(self, call_option_values_df):

        df_orginal = call_option_values_df
        df_length = len(df_orginal)
        df_new = pd.DataFrame(np.zeros((df_length, df_length)))
        for i in range(df_length):
            for j in range(i + 1):
                if j <= df_length - 1:  # Ensure we don't exceed column 4
                    move_to = df_length - 1 - i + j
                    #print(rf"[{i},{j}], value={df_orginal.iat[i, j]}, move to: [{i},{move_to}]")
                    df_new.iat[i, move_to] = df_orginal.iat[i, j]

        return df_new.T


    def write_to_excel(self, data_frames):

        with pd.ExcelWriter(r'e:\tmp\1.xlsx', engine='xlsxwriter') as writer:
            current_row = 0  # Start from the first row
            for idx, df in enumerate(data_frames):
                df.to_excel(writer, sheet_name='Sheet1', startrow=current_row, index=False,
                            header=True if idx == 0 else False)
                current_row += df.shape[0] + 1  # Move to the next row, with one blank row in between


    def caculate_americanOption_value(self, ):

        asset_prices, call_option_values, euro_call_option_values, asset_minus_K = (
            self.calculate_option_price(option_type="call"))

        asset_prices_df = pd.DataFrame(asset_prices)
        call_option_values_df = pd.DataFrame(call_option_values)
        euro_call_option_values_df = pd.DataFrame(euro_call_option_values)
        asset_minus_K_df = pd.DataFrame(asset_minus_K)
        asset_prices_converted_df = option.convert_array_df_to_triangular_df(asset_prices_df)
        call_option_values_converted_df = option.convert_array_df_to_triangular_df(call_option_values_df)
        euro_call_option_values_converted_df = option.convert_array_df_to_triangular_df(euro_call_option_values_df)
        asset_minus_K__converted_df = option.convert_array_df_to_triangular_df(asset_minus_K_df)

        print(asset_prices_df)
        print(call_option_values_df)
        print(euro_call_option_values_df)
        print(asset_minus_K_df)
        print("------------***asset_prices_converted_df****------------")
        print(asset_prices_converted_df)
        print("------------***euro_call_option_values_converted_df****------------")
        print(euro_call_option_values_converted_df)
        print("------------***asset_minus_K__converted_df****------------")
        print(asset_minus_K__converted_df)
        print("------------***call_option_values_converted_df****------------")
        print(call_option_values_converted_df)
        print("Call Option price:", call_option_values[0][0])
        print("Call Euro option price:", euro_call_option_values[0][0])

        self.plot_diagram(asset_minus_K_df, asset_prices_converted_df, call_option_values_converted_df,
                          euro_call_option_values_converted_df)

        data_frames = [
            asset_prices_converted_df,
            call_option_values_converted_df,
            euro_call_option_values_converted_df,
            asset_minus_K__converted_df
        ]
        self.write_to_excel(data_frames)

    def plot_diagram(self, asset_minus_K_df, asset_prices_converted_df, call_option_values_converted_df,
                     euro_call_option_values_converted_df):
        call_option_values_converted_df_diagonal_values = call_option_values_converted_df.values[::-1].diagonal()
        asset_prices_converted_df_diagonal_values = asset_prices_converted_df.values[::-1].diagonal()
        euro_call_option_values_converted_df_diagonal_values = euro_call_option_values_converted_df.values[
                                                               ::-1].diagonal()
        asset_minus_K_df_diagonal_values = asset_minus_K_df.values[::-1].diagonal()
        print(call_option_values_converted_df_diagonal_values)
        print(asset_prices_converted_df_diagonal_values)
        print(call_option_values_converted_df_diagonal_values - asset_prices_converted_df_diagonal_values)

        plt.plot(call_option_values_converted_df_diagonal_values, label="call_option_values")
        plt.plot(euro_call_option_values_converted_df_diagonal_values, label="euro_call_option")

        plt.plot(asset_prices_converted_df_diagonal_values, label="asset_prices")
        numbers = [self.K] * len(asset_prices_converted_df_diagonal_values)
        plt.plot(numbers, label="K")

        plt.plot(call_option_values_converted_df_diagonal_values - asset_prices_converted_df_diagonal_values, label="option-stock")
        plt.plot(asset_minus_K_df_diagonal_values, label="asset_minus_K")

        plt.legend()
        plt.title('Diagonal Values Plot')
        plt.xlabel('Time Steps')
        plt.ylabel('Call Option Price')
        plt.grid(True)
        plt.show()


if __name__ == "__main__":

    option_parameters_list = [
        # {
        #     "spot": 100,
        #     "strike": 100,
        #     "time_to_maturity": 1 / 2,
        #     "risk_free_rate": 0.05,
        #     "foreign_rate": 0.08,
        #     "volatility": 0.2,
        #     "steps": 4
        # },
        # {
        #     "spot": 100,
        #     "strike": 100,
        #     "time_to_maturity": 1 / 2,
        #     "risk_free_rate": 0.05,
        #     "foreign_rate": 0.08,
        #     "volatility": 0.2,
        #     "steps": 120
        # },
        # {
        #     "spot": 100,
        #     "strike": 100,
        #     "time_to_maturity": 1,
        #     "risk_free_rate": 0.05,
        #     "foreign_rate": 0.08,
        #     "volatility": 0.2,
        #     "steps": 360
        # },
        {
            "spot": 100,
            "strike": 100,
            "time_to_maturity": 1/2,
            "risk_free_rate": 0.05,
            "foreign_rate": 0.00,
            "volatility": 0.2,
            "steps": 90
        },
    ]

    for params in option_parameters_list:
        option = AmericanOption(params["spot"], params["strike"], params["time_to_maturity"], params["risk_free_rate"], params["foreign_rate"], params["volatility"], params["steps"],)
        option.caculate_americanOption_value()
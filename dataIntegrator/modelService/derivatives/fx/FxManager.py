class FxManager:
    def __init__(self, domestic_rate, foreign_rate, spot_rate):
        self.i_d = domestic_rate  # Domestic interest rate
        self.i_f = foreign_rate  # Foreign interest rate
        self.S = spot_rate  # Spot exchange rate

    def calculate_forward_rate(self):
        # Calculate the forward rate based on Interest Rate Parity formula
        F = self.S * (1 + self.i_d) / (1 + self.i_f)
        return F

    def check_parity(self, forward_rate):
        # Check if the given forward rate matches the calculated forward rate
        calculated_forward_rate = self.calculate_forward_rate()
        return forward_rate == calculated_forward_rate


    def parity_advisor(self, market_foward_rate, caculated_forward_rate):
        if (market_foward_rate > caculated_forward_rate):
            is_parity = False
            comment = "Buy the foward contrace"
        elif (market_foward_rate == caculated_forward_rate):
            is_parity = True
            comment = "Buy the forward contract"
        else:
            is_parity = False
            comment = "Don't buy the forward contract"
        return is_parity, comment

if __name__ == '__main__':

    # Example of 7.3
    domestic_rate = 2.75/100
    foreign_rate = 4.25/100
    spot_rate = 1.0225 - (1.0225 - 1.0221) /2
    market_foward_rate = 1.0077

    fxManager = FxManager(domestic_rate, foreign_rate, spot_rate)

    # 计算forward rate
    caculated_forward_rate = fxManager.calculate_forward_rate()
    print(f"Calculated Forward Rate: {caculated_forward_rate:.4f}")
    # 通过利率平价计算投机策略
    is_parity, comment = fxManager.parity_advisor(market_foward_rate, caculated_forward_rate)
    print(f"Does the forward rate satisfy interest parity? {'Yes' if is_parity else 'No'}, Comment: {comment}")
import math
from scipy.stats import norm

class EuroOption:
    def __init__(self, spot, strike, time_to_maturity, risk_free_rate, volatility):
        self.S = spot  # Spot price of the underlying asset
        self.K = strike  # Strike price of the option
        self.T = time_to_maturity  # Time to maturity in years
        self.r = risk_free_rate  # Risk-free interest rate
        self.sigma = volatility  # Volatility of the underlying asset

    def d1(self):
        return (math.log(self.S / self.K) + (self.r + 0.5 * self.sigma ** 2) * self.T) / (self.sigma * math.sqrt(self.T))

    def d2(self):
        return self.d1() - self.sigma * math.sqrt(self.T)

    def call_option_price(self):
        # Calculate the price of a European call option using Black-Scholes formula
        d1 = self.d1()
        d2 = self.d2()
        call_price = self.S * norm.cdf(d1) - self.K * math.exp(-self.r * self.T) * norm.cdf(d2)
        return call_price

    def put_option_price(self):
        # Calculate the price of a European put option using Black-Scholes formula
        d1 = self.d1()
        d2 = self.d2()
        put_price = self.K * math.exp(-self.r * self.T) * norm.cdf(-d2) - self.S * norm.cdf(-d1)
        return put_price

    def present_value_strike(self):
        # Calculate the present value of the strike price
        return self.K * math.exp(-self.r * self.T)

if __name__ == "__main__":

    #Example 1
    print("----**-----spot=100, strike=95, time_to_maturity=1, risk_free_rate=0.05, volatility=0.2")
    option = EuroOption(spot=100, strike=95, time_to_maturity=1, risk_free_rate=0.05, volatility=0.2)
    call_price = option.call_option_price()
    print(rf"Call option price: {call_price:.6f}")

    put_price = option.put_option_price()
    print(rf"Put option price:{put_price:.6f}")

    pv_strike = option.present_value_strike()
    print(rf"Spot: {100:.6f}")
    print(rf"Present Value of Strike Price: {pv_strike:.6f}")


    print(rf"Call - Put = {call_price-  put_price:.6f}")
    print(rf"S - K= {100 - pv_strike:.6f}")

    #Example 2
    print("----**-----spot=100, strike=100, time_to_maturity=1/2, risk_free_rate=0.05, volatility=0.2")
    option = EuroOption(spot=100, strike=100, time_to_maturity=1/2, risk_free_rate=-0.03, volatility=0.2)
    call_price = option.call_option_price()
    print(rf"Call option price: {call_price:.6f}")

    put_price = option.put_option_price()
    print(rf"Put option price:{put_price:.6f}")

    pv_strike = option.present_value_strike()
    print(rf"Spot: {100:.6f}")
    print(rf"Present Value of Strike Price: {pv_strike:.6f}")

    print(rf"Call - Put = {call_price - put_price:.6f}")
    print(rf"S - K= {100 - pv_strike:.6f}")

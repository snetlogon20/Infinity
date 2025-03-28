import numpy as np

class NPVManager:

    def exponential_future_value(self, principal, rate, time):
        """
        Calculate future value using the formula:
        FV = P * exp(rate * time)

        :param principal: Initial investment or principal amount
        :param rate: Rate of growth (as a decimal, e.g., 0.05 for 5%)
        :param time: Time period over which the investment grows (in years)
        :return: Future value
        """
        return principal * np.exp(rate * time)

    def exponential_present_value(self, future_value, rate, time):
        """
        Calculate present value using the formula:
        PV = FV / exp(rate * time)

        :param future_value: Future value (FV)
        :param rate: Rate of growth (as a decimal)
        :param time: Time period over which the investment grows (in years)
        :return: Present value (PV)
        """
        return future_value / np.exp(rate * time)


    def power_future_value(self, principal, rate, time):
        """
        Calculate future value using the formula:
        FV = P * (1 + rate)^time

        :param principal: Initial investment or principal amount
        :param rate: Rate of growth (as a decimal)
        :param time: Time period over which the investment grows (in years)
        :return: Future value
        """
        return principal * (1 + rate) ** time

    def power_present_value(self, future_value, rate, time):
        """
        Calculate present value using the formula:
        PV = FV / (1 + rate)^time

        :param future_value: Future value (FV)
        :param rate: Rate of growth (as a decimal)
        :param time: Time period over which the investment grows (in years)
        :return: Present value (PV)
        """
        return future_value / (1 + rate) ** time

if __name__ == "__main__":
    npv_manager = NPVManager()
    fv = npv_manager.exponential_future_value(1000, 0.05, 10)
    pv = npv_manager.exponential_present_value(fv, 0.05, 10)
    print(f"Future Value: {fv}")
    print(f"Present Value: {pv}")

    fv = npv_manager.power_future_value(1000, 0.05, 10)
    pv = npv_manager.power_present_value(fv, 0.05, 10)
    print(f"Future Value: {fv}")
    print(f"Present Value: {pv}")
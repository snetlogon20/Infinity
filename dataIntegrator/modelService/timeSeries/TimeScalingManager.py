import numpy as np


class TimeScalingManager:

    def __init__(self):
        pass

    def calculate_scaled_var(self, var1, t, rho=1.0):

        if t <= 0:
            raise ValueError("Target time period must be positive")

        var2 = var1 * np.sqrt(2) / np.sqrt(1 + rho)

        return var2


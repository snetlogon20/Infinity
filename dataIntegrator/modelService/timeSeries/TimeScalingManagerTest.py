import numpy as np

from dataIntegrator.modelService.timeSeries.TimeScalingManager import TimeScalingManager


class TimeScalingManagerTest:
    def __init__(self):
        pass


if __name__ == "__main__":
    timeScalingManager = TimeScalingManager()
    var = timeScalingManager.calculate_scaled_var(1000000,2,0.1)
    print(rf"var:{var}")

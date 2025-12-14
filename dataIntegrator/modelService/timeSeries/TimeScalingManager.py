import numpy as np


class TimeScalingManager:

    def __init__(self):
        pass


    def calculate_scaled_var(self, var1=0, t=0, rho=1.0):
        """
        Calculate scaled variance based on time scaling factor and correlation coefficient.
        根据给定的VAR计算放大T天的VAR值

        Args:
            var1 (float): Original variance value
            t (float): Target time period, must be positive
            rho (float, optional): Correlation coefficient, defaults to 1.0

        Returns:
            float: Scaled variance value

        Raises:
            ValueError: When target time period t is not positive
            TypeError: When inputs are not numeric types
        """
        if t <= 0:
            raise ValueError("Target time period must be positive")
        var2 = var1 * np.sqrt(2) / np.sqrt(1 + rho)


        return var2

    def calculate_scaled_sigma(self, annual_sigma=0, t=1, unit="week"):
        """
        Calculate scaled variance based on time scaling factor and correlation coefficient.
        根据给定的sigma计算放大T天的sigma值
        """
        if t <= 0:
            raise ValueError("Target time period must be positive")

        # Convert unit to lowercase for case-insensitive comparison
        unit = unit.lower()

        # Define time conversion factors
        unit_factors = {
            "day": 252,
            "week": 52,
            "year": 1  # Standard trading days in a year
        }

        # Validate unit and get conversion factor
        if unit not in unit_factors:
            raise ValueError(f"Unsupported unit '{unit}'. Must be one of {list(unit_factors.keys())}")

        # Apply time scaling formula with appropriate factor
        time_factor = unit_factors[unit]
        sigma2 = annual_sigma * np.sqrt(t * (1 / time_factor))

        return sigma2


    def calculate_EWMA_eta(self, ewma_lambda=0.95, expected_return=0, eta_t_minus_1=0):
        eta = (1 - ewma_lambda) * (expected_return ** 2) + ewma_lambda * eta_t_minus_1

        return eta

    def calculate_EWMA_eta_with_log_value(self, ewma_lambda=0.95, expected_return_t0=1, expected_return_t1=1, eta_t_minus_1=0):
        expected_return = np.log(expected_return_t1/expected_return_t0)
        eta = self.calculate_EWMA_eta(ewma_lambda, expected_return,  eta_t_minus_1)

        return eta

    def calculate_EWMA_rolling_eta(self, data_dict, lambda_param=0.95):
        """
        计算EWMA模型的条件方差（eta）

        参数:
        data_dict: dict, 包含时间、回报和初始方差的字典
                  格式: {'time': [0, 1, 2, 3], 'return': [0, 3, 0, 0], 'eta': 1.10}
        lambda_param: float, 衰减因子，默认为0.95（与表格5.4一致）

        返回:
        dict: 包含完整计算结果的字典，格式与table 5.4类似
        """
        # 从输入字典中提取数据
        times = data_dict['time']
        returns = data_dict['return']
        eta_initial = data_dict['eta']

        # 初始化结果列表
        result = {
            'time': [],
            'return': [],
            'conditional_variance': [],
            'conditional_risk': [],
            'conditional_95_limit': []
        }

        # 初始状态 (t=0)
        b_t = eta_initial  # 初始条件方差
        result['time'].append(0)
        result['return'].append(returns[0])
        result['conditional_variance'].append(round(b_t, 2))
        result['conditional_risk'].append(round(b_t ** 0.5, 2))
        result['conditional_95_limit'].append(round(2 * b_t ** 0.5, 1))

        # 计算后续时间点的条件方差
        for i in range(1, len(times)):
            # 前一天的条件方差
            b_t_minus_1 = b_t

            # 前一天的回报
            #r_t_minus_1 = returns[i - 1]
            r_t_minus_1 = returns[i]

            # 根据EWMA公式更新条件方差: b_t = (1-λ)*r_{t-1}^2 + λ*b_{t-1}
            #b_t = (1 - lambda_param) * (r_t_minus_1 ** 2) + lambda_param * b_t_minus_1
            b_t = self.calculate_EWMA_eta(ewma_lambda=lambda_param, expected_return = r_t_minus_1, eta_t_minus_1=b_t_minus_1)

            # 保存结果
            result['time'].append(times[i])
            result['return'].append(returns[i])
            result['conditional_variance'].append(round(b_t, 2))
            result['conditional_risk'].append(round(b_t ** 0.5, 2))
            result['conditional_95_limit'].append(round(2 * b_t ** 0.5, 1))

        #返回最后一天的 Eta
        conditional_variance = result['conditional_variance'][-1]

        return result, conditional_variance
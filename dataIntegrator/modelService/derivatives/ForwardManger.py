from dataIntegrator.modelService.derivatives.RateManager import RateManager
import numpy as np

class ForwardManager:
    def __init__(self, params):
        self.params = params  # compounding interest_rate (annual)


    def calculate_value_of_spot(self, params):

        # Step 1 calculate_PV - Exponentional
        spot_value = params['spot_value']
        spot_rate = params['spot_rate']
        dividends = params['spot_dividends']
        interest_rate = spot_rate - dividends
        spot_tenor = params['spot_tenor']
        compounding_or_exponential = params['compounding_or_exponential']
        pv_of_spot = rate_manager.calculate_PV(FV=spot_value, periods=spot_tenor, interest_rate=interest_rate,
                                                           method=compounding_or_exponential)

        # Step 2 calculate_FV
        forward_value = params['forward_value']
        forward_rate = params['forward_rate']
        forward_dividends = params['forward_dividends']
        interest_rate = forward_rate - forward_dividends
        forward_tenor = params['forward_tenor']
        compounding_or_exponential = params['compounding_or_exponential']
        pv_of_forward = rate_manager.calculate_PV(FV=forward_value, periods=forward_tenor,
                                                              interest_rate=interest_rate,
                                                              method=compounding_or_exponential)
        # Step 3 calculate_the value of
        value_of_spot = pv_of_spot - pv_of_forward

        # 给出策略
        if value_of_spot < 0:
            strategy = "股票回报率较低，远期预测股票会涨。 所以也要么买买入远期， 买同等call期权，要么买股票"
        elif value_of_spot > 0:
            strategy = "股票回报率较高，远期预测股票会跌， 所以也要么买卖出远期， 卖同等call期权，要么卖股票"
        else:
            strategy = "巧了，股票和远期居然一样，没有套利机会"

        return pv_of_spot, pv_of_forward, value_of_spot, strategy


if __name__ == '__main__':
    # 计算 PV - FV 价值 example 7.6
    params = { 'spot_value': 990,
               'spot_rate': 4.00/100,
               'spot_dividends': 2.00/100,
               'spot_tenor': 3/12,
               'forward_value': 1000,
               'forward_rate': 4.00/100,
               'forward_dividends': 0.00,
               'forward_tenor': 3/12,
               'compounding_or_exponential': 'exponential',
               'pv_of_spot': 0,
               'pv_of_forward': 0,
               'value': 0
               }

    rate_manager = RateManager(interest_rate=0.00)
    forward_manager = ForwardManager(params=params)
    pv_of_sport = 0
    pv_of_forward = 0
    value_of_spot = 0

    pv_of_sport, pv_of_forward, value_of_spot, strategy = forward_manager.calculate_value_of_spot(params)

    print(rf"pv_of_spot({params['compounding_or_exponential']}):{pv_of_sport:6f}")
    print(rf"pv_of_forward({params['compounding_or_exponential']}):{pv_of_forward:6f}")
    print(rf"value_of_spot({params['compounding_or_exponential']}):{value_of_spot:6f}")
    print(rf"strategy({params['compounding_or_exponential']}):{strategy}")

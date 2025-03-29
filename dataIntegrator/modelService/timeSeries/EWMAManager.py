from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt

from dataIntegrator import TuShareServiceManager
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.modelService.commonService.CalendarService import CalendarService
from dataIntegrator.modelService.timeSeries.EWMAAnalyst import EWMAManager
from dataIntegrator.utility.FileUtility import FileUtility


class EWMAAnalyster:
    def __init__(self, params):
        """
        Initializes the EWMA_Prediction class.
        """
        self.params = params

    def refresh_data(self):

        if self.params['if_refresh_date'] == False:
            return

        ts_code = self.params['stock']
        start_date = self.params['start_date']
        end_date  = self.params['backtest_end_date']

        tuShareServiceManager = TuShareServiceManager()
        tuShareServiceManager.callTuShareChinaStockIndexService(ts_code=ts_code, start_date=start_date, end_date=end_date)

    def analysis_date(self):
        self.refresh_data()

        ewmaManager = EWMAManager(params)
        ewmaManager.ewma_stock_analysis()


if __name__ == "__main__":
    params_list = [
        # {
        #     'market': "CN",
        #     'stock': '000001.SH',
        #     'start_date': '20241001',
        #     'end_date': '20241218',
        #     'predict_or_backtest': 'predict',
        #     'span': 30,
        #     'analysis_column': 'pct_chg',
        #     'backtest_start_date': '20241001',
        #     'backtest_end_date': '20241220',
        #     'if_refresh_date': False,
        # },
        # {
        #     'market': "CN",
        #     'stock': '603839.SH',
        #     'start_date': '20241001',
        #     'end_date': '20241223',
        #     'predict_or_backtest': 'predict',
        #     'span': 30,
        #     'analysis_column': 'pct_chg',
        #     'backtest_start_date': '20241224',
        #     'backtest_end_date': '20241230',
        #     'if_refresh_date': False,
        # },
        {
            'market': "CN",
            'stock': '603839.SH',
            'start_date': '20241001',
            'end_date': '20241231',
            'predict_or_backtest': 'predict',
            'span': 30,
            'analysis_column': 'pct_chg',
            'backtest_start_date': '20241224',
            'backtest_end_date': '20250102',
            'if_refresh_date': False,
            'is_rolling_prediction': True,
        },
        # {
        #     'market': "US",
        #     'stock': 'C',
        #     'start_date': '20241001',
        #     'end_date': '20241221',
        #     'predict_or_backtest': 'predict',
        #     'span': 30,
        #     'analysis_column': 'close_point',
        #     'backtest_start_date': '20241223',
        #     'backtest_end_date': '20241229',
        #     'if_refresh_date': False,
        # }
        ]

    for params in params_list:
        dwmaAnalyster = EWMAAnalyster(params)
        dwmaAnalyster.analysis_date()
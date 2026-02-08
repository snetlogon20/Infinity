import pandas as pd
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.modelService.timeSeries.EWMAAnalyst import EWMAAnalyst


class EWMAAnalystTest:
    def __init__(self):
        pass

    def load_data(self, params):

        market = params["market"]
        stock = params['stock']
        start_date = params['start_date']
        end_date = params['end_date']
        predict_or_backtest = params['predict_or_backtest']
        backtest_start_date = params['backtest_start_date']
        backtest_end_date = params['backtest_end_date']

        predict_dataFrame = pd.DataFrame()
        backtest_dataFrame = pd.DataFrame()
        rolling_backtest_dataFrame = pd.DataFrame()

        if market == "US":
            sql = rf"""
                select ts_code,
                        trade_date,
                        close_point,
                        open_point,
                        high_point,
                        low_point,
                        pre_close,
                        change_point,
                        pct_change,
                        vol,
                        amount
                from indexsysdb.df_tushare_us_stock_daily
                where ts_code = '{stock}' AND
                trade_date>= '{start_date}' and
                trade_date <='{end_date}'
                order by trade_date
            """
            #columns = ['ts_code', 'trade_date', 'close_point', 'pct_change', 'vol', 'amount']
            columns = ['ts_code', 'trade_date', 'close', 'open_point', 'high_point', 'low_point', 'pre_close', 'change_point', 'pct_chg', 'vol', 'amount']
        elif market == "CN":
            sql = rf"""
                select 	
                    ts_code, trade_date, close, pct_chg, vol, amount
                from 
                (
                    select 
                        ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount
                    from indexsysdb.df_tushare_stock_daily
                    where ts_code = '{stock}' AND
                        trade_date >= '{start_date}' AND 
                        trade_date <= '{end_date}'
                    union all
                    select 
                        ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount
                    from indexsysdb.df_tushare_cn_index_daily
                    where ts_code = '{stock}' AND
                        trade_date >= '{start_date}' AND 
                        trade_date <= '{end_date}'
                )
                order by trade_date
            """
            columns = ['ts_code', 'trade_date', 'close', 'pct_chg', 'vol', 'amount']

        clickhouseService = ClickhouseService()
        dataFrame = clickhouseService.getDataFrame(sql, columns)
        dataFrame['trade_date'] = pd.to_datetime(dataFrame['trade_date']).dt.date

        # 确保trade_date为datetime类型
        dataFrame['trade_date'] = pd.to_datetime(dataFrame['trade_date'])

        # 统一 trade_date 列为 Timestamp 类型
        dataFrame['trade_date'] = pd.to_datetime(dataFrame['trade_date'])

        if predict_or_backtest == "predict":
            predict_dataFrame = dataFrame
            predict_dataFrame['trade_date'] = pd.to_datetime(predict_dataFrame['trade_date'])
        elif predict_or_backtest == "backtest":
            backtest_dataFrame = dataFrame
            backtest_dataFrame['trade_date'] = pd.to_datetime(backtest_dataFrame['trade_date'])
        elif predict_or_backtest == "rolling_backtest":
            rolling_backtest_dataFrame = dataFrame
            rolling_backtest_dataFrame['trade_date'] = pd.to_datetime(rolling_backtest_dataFrame['trade_date'])

        # 将数据帧添加到 params 字典中
        params['dataFrame'] = dataFrame
        params['predict_dataFrame'] = predict_dataFrame
        params['backtest_dataFrame'] = backtest_dataFrame
        params['rolling_backtest_dataFrame'] = rolling_backtest_dataFrame

        return params


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
        # },
        {
            'market': "CN",
            'stock': '603839.SH',
            'filter_key_column':'trade_date',
            'start_date': '20240901',
            'end_date': '20241231',
            'next_n_days':10,
            'span': 30,
            'analysis_column': 'close',
            'remark': '分析该股票的收盘价'
        },
        {
            'market': "CN",
            'stock': '603839.SH',
            'filter_key_column': 'trade_date',
            'start_date': '20240901',
            'end_date': '20241231',
            'next_n_days': 10,
            'span': 30,
            'analysis_column': 'pct_chg',
            'remark': '分析该股票的波动率'
        },
        # {
        #     'market': "CN",
        #     'stock': '002093.SZ',
        #     'start_date': '20240101',
        #     'end_date': '20241209',
        #     'predict_or_backtest': 'predict',
        #     'span': 30,
        #     'analysis_column': 'pct_chg',
        #     'backtest_start_date': '20241210',
        #     'backtest_end_date': '20241229',
        # },
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
        # }
        ]

    # ##################################
    # # 直接单条分析
    # ##################################
    for params in params_list:
        ewmaAnalyst = EWMAAnalyst()
        ewmaAnalyst.analyze_workflow(params)

    ##################################
    # 采用滚动预测分析
    ##################################
    # for params in params_list:
    #     ewmaManager = EWMAManager(params)
    #     ewmaManager.ewma_stock_analysis_with_rolling_prediction()
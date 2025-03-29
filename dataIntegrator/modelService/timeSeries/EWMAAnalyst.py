from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt
from pandas.core.interchange.dataframe_protocol import DataFrame

from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.modelService.commonService.CalendarService import CalendarService
from dataIntegrator.utility.FileUtility import FileUtility


class EWMAManager:
    def __init__(self, params):
        """
        Initializes the EWMA_Prediction class.
        """
        span = params.get('span', 30)
        self.calendar_df = None
        self.dataFrame = None
        self.predict_dataFrame = None
        self.backtest_dataFrame = None
        self.ewma_dataFrame = None
        self.ewma_df = None

        self.actual_data_aseries = None
        self.span = span
        self.ewma_series = None
        self.params = params
        self.original_params = params.copy()

    def load_data(self):
        market = self.params["market"]
        stock = self.params['stock']
        start_date = self.params['start_date']
        end_date = self.params['end_date']
        predict_or_backtest = self.params['predict_or_backtest']

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
        self.dataFrame = clickhouseService.getDataFrame(sql, columns)
        self.dataFrame['trade_date'] = pd.to_datetime(self.dataFrame['trade_date']).dt.date

        if predict_or_backtest == "predict":
            self.predict_dataFrame = self.dataFrame
            self.predict_dataFrame['trade_date'] = pd.to_datetime(self.predict_dataFrame['trade_date']).dt.date
        elif predict_or_backtest == "backtest":
            self.backtest_dataFrame = self.dataFrame
            self.backtest_dataFrame['trade_date'] = pd.to_datetime(self.backtest_dataFrame['trade_date']).dt.date
        elif predict_or_backtest == "rolling_backtest":
            self.rolling_backtest_dataFrame = self.dataFrame
            self.rolling_backtest_dataFrame['trade_date'] = pd.to_datetime(self.rolling_backtest_dataFrame['trade_date']).dt.date

        return self.dataFrame


    def actual_data_Series(self):
        actual_data_aseries = pd.Series(self.dataFrame['close'].values, index=self.dataFrame['trade_date'])
        self.actual_data_aseries = actual_data_aseries
        return actual_data_aseries

    def calculate_ewma(self):
        """
        Calculates the EWMA (Exponentially Weighted Moving Average) of the provided time series data.
        """
        ewma_dataFrame = self.predict_dataFrame
        #print(self.predict_dataFrame)
        ewma_series = ewma_dataFrame['close'].ewm(span=self.span, adjust=False).mean()

        ewma_df = pd.DataFrame({
            'trade_date': self.predict_dataFrame['trade_date'],
            'ewma': ewma_series
        })
        ewma_df.columns = ['trade_date','ewma_close']

        self.ewma_series = ewma_series
        self.ewma_df = ewma_df
        #print(ewma_df)

        return self.ewma_series, self.ewma_df

    def calculate_ewma_with_rolling(self, rolling_predict_dataFrame):
        """
        Calculates the EWMA (Exponentially Weighted Moving Average) of the provided time series data.
        """
        #print(rolling_predict_dataFrame)
        #rolling_ewma_series = rolling_predict_dataFrame['close'].ewm(span=self.span, adjust=False).mean()
        rolling_ewma_series = rolling_predict_dataFrame['close'].ewm(span=2, adjust=False).mean()

        rolling_ewma_df = pd.DataFrame({
            'trade_date': rolling_predict_dataFrame['trade_date'],
            'ewma': rolling_ewma_series
        })
        rolling_ewma_df.columns = ['trade_date','ewma_close']

        self.rolling_ewma_series = rolling_ewma_series
        self.rolling_ewma_df = rolling_ewma_df
        #print(rolling_ewma_df)

        return rolling_ewma_series, rolling_ewma_df

    def predict(self):
        """
        Predicts the next `n_steps` values based on the EWMA model.
        """
        last_ewma_value = self.ewma_series.iloc[-1]
        predictions_df = self.backtest_dataFrame[['trade_date']].copy()
        predictions_df['predicted_close'] = last_ewma_value
        #print(predictions_df)
        self.predictions_df = predictions_df

        return predictions_df

    def predict_with_rolling(self, ewma_series, rolling_ewma_df, rolling_backtest_dataFrame):
        """
        Predicts the next `n_steps` values based on the EWMA model.
        """
        last_ewma_value = ewma_series.iloc[-1]
        rolling_predictions_df = rolling_backtest_dataFrame[['trade_date']].copy()
        rolling_predictions_df['predicted_close'] = last_ewma_value
        #print(rolling_predictions_df)
        self.rolling_predictions_df = rolling_predictions_df

        return rolling_predictions_df


    def join_data(self):
        all_trade_date_df = pd.merge(self.calendar_df, self.predict_dataFrame, on='trade_date', how='left')
        all_trade_date_df = pd.merge(all_trade_date_df, self.backtest_dataFrame, on='trade_date', how='left')
        all_trade_date_df = pd.merge(all_trade_date_df, self.ewma_df, on='trade_date', how='left')
        all_trade_date_df = pd.merge(all_trade_date_df, self.predictions_df, on='trade_date', how='left')
        if self.params["is_rolling_prediction"] == True:
            all_trade_date_df = pd.merge(all_trade_date_df, self.rolling_predictions_df, on='trade_date', how='left')

        self.all_trade_date_df = all_trade_date_df
        return all_trade_date_df

    def plot_data(self):
        all_trade_date_df = self.all_trade_date_df
        all_trade_date_df = all_trade_date_df.dropna(subset=['close_x', 'close_y', 'predicted_close'], how='all')

        plt.figure(figsize=(10, 6))

        plt.plot(all_trade_date_df['trade_date'], all_trade_date_df['close_x'], label='Actual Data', )
        plt.plot(all_trade_date_df['trade_date'], all_trade_date_df['close_y'], label='Backtest Data')
        plt.plot(all_trade_date_df['trade_date'], all_trade_date_df['ewma_close'], label='EWMA')
        plt.plot(all_trade_date_df['trade_date'], all_trade_date_df['predicted_close'], label='Predictions', color='r')
        if self.params["is_rolling_prediction"] == True:
            plt.plot(all_trade_date_df['trade_date'], all_trade_date_df['rolling_predicted_close'], label='Rolling Predictions', color='r')

        plt.title('Time Series with EWMA and Predictions')

        market = self.params['market']
        stock = self.params['stock']
        start_date = self.params['start_date']
        end_date = self.params['end_date']
        plt.title(f'Time Series with EWMA and Predictions_{market}.{stock}.{start_date}-{end_date}')
        plt.xticks(all_trade_date_df['trade_date'], rotation=90, fontsize=8)
        plt.xlabel('Date')
        plt.ylabel('Value')
        plt.legend()

        plt.show()

    def write_data(self):
        params = self.params

        file_full_name = FileUtility.get_full_filename_by_timestamp(
            rf"EWMA Prediction_{params['market']}.{params['stock']}.{params['start_date']}-{params['end_date']}",
            "xlsx")
        self.all_trade_date_df.to_excel(file_full_name)

    def ewma_stock_analysis(self):
        params = self.params

        # Step 1： Load Calendar
        calendarService = CalendarService()
        self.calendar_df = calendarService.load_calendar(self.params['start_date'], self.params['backtest_end_date'])

        # Step 2.1： Load predict data
        params['predict_or_backtest'] = 'predict'
        self.load_data()

        # Step 2.2： Load backtest data
        params['start_date'] = params['backtest_start_date']
        params['end_date'] = params['backtest_end_date']
        params['predict_or_backtest'] = 'backtest'
        self.load_data()

        # Step 3: Calculate the EWMA series
        ewma_series, ewma_df = self.calculate_ewma()

        # Step 4: Generate predictions for back_test start/end date
        predictions_series, predictions_df = self.predict()

        # Step 5: Rolling pridiction
        if self.params["is_rolling_prediction"] == True:
            self.ewma_stock_analysis_with_rolling_prediction()

        # Step 6: join the data
        self.join_data()

        # Step 7: Plot the actual data and predictions
        self.plot_data()

        # Step 8: Save the data to excel
        self.write_data()

    def ewma_stock_analysis_with_rolling_prediction(self):
        params = self.original_params

        # Step 1： Load Calendar
        filtered_calendar_df = self.calendar_df[
            (self.calendar_df['trade_date'] >= pd.to_datetime(params['start_date'])) &
            (self.calendar_df['trade_date'] <= pd.to_datetime(params['end_date']))
            ].copy()
        filtered_calendar_df.sort_values(by='trade_date', ascending=True, inplace=True)
        min_trade_date = filtered_calendar_df['trade_date'].min()

        # Step 2.1： Load predict data
        original_predict_dataFrame = self.predict_dataFrame

        # Step 3： Load rolling prediction data
        rolling_predictions_df_list =  []
        rolling_predictions_list = []
        for index, row in filtered_calendar_df.iterrows():

            trade_date = row['trade_date']
            previous_trade_date = trade_date + pd.Timedelta(days=-5)
            latest_trade_date = max(previous_trade_date, min_trade_date)

            rolling_backtest_start_date = trade_date
            rolling_backtest_end_date = trade_date + pd.Timedelta(days=5)

            # Step 3.1： Load predict data
            rolling_predict_dataFrame = original_predict_dataFrame[
            (original_predict_dataFrame['trade_date'] >= latest_trade_date) &
            (original_predict_dataFrame['trade_date'] <= trade_date)
            ]
            if rolling_predict_dataFrame.shape[0] == 0: # 当天没有数据， 跳过
                continue

            # Step 3.2： Load backtest data
            self.params['start_date'] = str(rolling_backtest_start_date).replace("-","")
            self.params['end_date'] = str(rolling_backtest_end_date).replace("-","")
            self.params['predict_or_backtest'] = 'rolling_backtest'
            rolling_backtest_dataFrame = self.load_data()

            # Step 3.3: Calculate the rolling_EWMA series
            ewma_series, rolling_ewma_df = self.calculate_ewma_with_rolling(rolling_predict_dataFrame)
            ewma_value = ewma_series.iloc[-1]
            rolling_predictions_list.append((trade_date, ewma_value))

            # Step 4: Generate predictions for back_test start/end date
            rolling_predictions_df = self.predict_with_rolling(ewma_series, rolling_ewma_df, rolling_backtest_dataFrame)
            rolling_predictions_df = pd.merge(self.calendar_df, rolling_predictions_df, on='trade_date', how='left')
            rolling_predictions_df_list.append(rolling_predictions_df)

        rolling_predictions_df = pd.DataFrame(rolling_predictions_list)
        rolling_predictions_df.columns = ['trade_date','rolling_predicted_close']
        self.rolling_predictions_df_list = rolling_predictions_df_list
        self.rolling_predictions_df = rolling_predictions_df

        return rolling_predictions_df_list, rolling_predictions_df

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
            'start_date': '20241001',
            'end_date': '20241223',
            'predict_or_backtest': 'predict',
            'span': 30,
            'analysis_column': 'pct_chg',
            'backtest_start_date': '20241224',
            'backtest_end_date': '20241230',
            'is_rolling_prediction': True,
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
        ewmaManager = EWMAManager(params)
        ewmaManager.ewma_stock_analysis()

    ##################################
    # 采用滚动预测分析
    ##################################
    # for params in params_list:
    #     ewmaManager = EWMAManager(params)
    #     ewmaManager.ewma_stock_analysis_with_rolling_prediction()
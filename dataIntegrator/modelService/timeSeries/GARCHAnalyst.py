import math

import matplotlib.pyplot as plt
import scipy.stats as stats
import pandas as pd
from arch import arch_model
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
import numpy as np

from dataIntegrator.utility.FileUtility import FileUtility


class GARCHManager:
    def __init__(self, params):
        self.params = params
        self.dataFrame = None
        self.garch_model = None
        self.garch_fit = None
        self.results_df = None
        self.forecast_df = None
        self.data_conditional_volatility_df = None
        self.all_trade_date_df = None
        self.backtest_dataFrame = None

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

        if predict_or_backtest == "predict":
            self.predict_dataFrame = self.dataFrame
        else:
            self.backtest_dataFrame = self.dataFrame

        return self.dataFrame

    def find_best_garch_model(self, data, p, q):
        """
        Find the best fitting GARCH model given data and ranges for p and q.

        :param data: pandas Series containing the data to fit the GARCH model on
        :param p_range: range of p values to test
        :param q_range: range of q values to test
        :return: instance of arch_model with best fitting parameters
        """

        best_aic = np.inf
        best_model = None
        best_p = None
        best_q = None
        p_range = range(1, p)  # Example: p can be 0 to 4
        q_range = range(1, q)  # Example: q can be 0 to 4

        # Iterate over the possible combinations of p and q
        for p in p_range:
            for q in q_range:
                try:
                    # Fit a GARCH(3,3) model
                    model = arch_model(data, vol='Garch', p=p, q=q, dist='Normal')
                    garch_fit = model.fit(disp="off")

                    # Update the model with the best AIC
                    if garch_fit.aic < best_aic:
                        best_aic = garch_fit.aic
                        best_p = p
                        best_q = q
                        best_model = garch_fit
                except Exception as e:
                    # Print an error message if the model couldn't be fit
                    print(f"Error fitting GARCH({p}, {q}): {e}")

        print(f"Best p: {best_p}, Best q: {best_q}, AIC: {best_aic}")
        return best_model

    def fit_garch_model(self):
        """Fit a GARCH model to the selected data column."""
        analysis_column = self.params["analysis_column"]
        data = self.dataFrame[analysis_column]
        data = data.fillna(0)

        # Fit GARCH(1, 1) model
        model = self.find_best_garch_model(data, p=3, q=3)
        self.garch_fit = model

        data_conditional_volatility_df = self.dataFrame['trade_date']
        data_conditional_volatility_df = pd.concat([data_conditional_volatility_df, self.garch_fit.conditional_volatility], axis=1)
        data_conditional_volatility_df.colums = ['trade_date','conditional_volatility']
        self.data_conditional_volatility_df = data_conditional_volatility_df

        print(self.garch_fit.summary())


    def forecast_garch(self):
        """Forecast future volatility using the GARCH model."""
        if self.garch_fit is not None:
            # Forecast future volatility (steps=10 as example)
            predict_days = 10
            forecast = self.garch_fit.forecast(horizon=predict_days)
            forecast_volatility = forecast.variance[-1:]
            print(forecast_volatility)
            forecast_volatility_T = forecast_volatility.T
            forecast_volatility_T.columns = ['forecast_volatility']
            historical_mean_return = self.dataFrame['pct_chg'].mean()

            # 整理数据，获得初始值
            last_value = self.dataFrame.sort_values('trade_date', ascending=False).iloc[0]["close"]
            alpha = 0.05
            z_score = stats.norm.ppf(1 - alpha / 2)
            predicted_upper_volatility_list =  []
            predicted_lower_volatility_list = []
            predicted_upper_value_list =  []
            predicted_lower_value_list = []

            predicted_upper_value = last_value
            predicted_lower_value = last_value

            # 转置矩阵，并通过参数估计计算上下边界
            for row_number, (index, row) in enumerate(forecast_volatility_T.iterrows()):
                forecast_volatility_value = row['forecast_volatility']

                row_number_sqrt = np.sqrt(row_number + 1)
                forecast_std_value_std = np.sqrt(forecast_volatility_value)

                # predicted_upper = (historical_mean_return/100 + z_score * ((forecast_volatility_value **0.5)/100)/row_number_sqrt)  # 参数估计
                # predicted_lower = (historical_mean_return/100 - z_score * ((forecast_volatility_value **0.5)/100)/row_number_sqrt)  # 参数估计
                predicted_upper = (historical_mean_return/100 + z_score * ((forecast_std_value_std/100)/row_number_sqrt))  # 参数估计
                predicted_lower = (historical_mean_return/100 - z_score * ((forecast_std_value_std/100)/row_number_sqrt))  # 参数估计

                # predicted_upper_value = predicted_upper_value * (1 + predicted_upper)
                # predicted_lower_value = predicted_lower_value * (1 + predicted_lower)
                predicted_upper_value = last_value * (1 + predicted_upper)
                predicted_lower_value = last_value * (1 + predicted_lower)

                print(predicted_upper, ", ", predicted_lower)
                predicted_upper_volatility_list = predicted_upper_volatility_list + [predicted_upper]
                predicted_lower_volatility_list = predicted_lower_volatility_list + [predicted_lower]
                predicted_upper_value_list = predicted_upper_value_list + [predicted_upper_value]
                predicted_lower_value_list = predicted_lower_value_list + [predicted_lower_value]

            # 存入data frame
            forecast_dates = pd.date_range(start=self.dataFrame["trade_date"].iloc[-1], periods=predict_days + 1, freq='D')[1:]
            self.forecast_df = pd.DataFrame({
                'trade_date': forecast_dates,
                'forecast_volatility': np.sqrt(forecast_volatility_T['forecast_volatility']),
                'predicted_upper_volatility_list': np.array(predicted_upper_volatility_list),
                'predicted_lower_volatility_list': np.array(predicted_lower_volatility_list),
                'predicted_upper_value_list': np.array(predicted_upper_value_list),
                'predicted_lower_value_list': np.array(predicted_lower_value_list)
            })

            print("Future Volatility Forecast:\n", self.forecast_df)
            return self.forecast_df

    def plot_garch_volatility(self):
        """Plot the fitted GARCH volatility."""
        analysis_column = self.params["analysis_column"]
        plot_dataFrame = self.dataFrame
        forecast_df = self.forecast_df
        
        # standard deviation
        standard_deviation = plot_dataFrame[analysis_column].std()
        mean = plot_dataFrame[analysis_column].mean()
        standard_deviation_df = pd.DataFrame({
            'trade_date': plot_dataFrame['trade_date'],
            'mean': [mean] * len(plot_dataFrame),
            'standard_deviation': [standard_deviation] * len(plot_dataFrame)
        })
        
        # conditional volatility
        data_conditional_volatility_df = self.data_conditional_volatility_df
        backtest_dataFrame_df = self.backtest_dataFrame[['trade_date','close']]
        backtest_dataFrame_df.columns = ['trade_date','back_test_close']

        data_conditional_volatility_df['trade_date'] = pd.to_datetime(data_conditional_volatility_df['trade_date']).dt.tz_localize(None)
        plot_dataFrame['trade_date'] = pd.to_datetime(plot_dataFrame['trade_date']).dt.tz_localize(None)
        backtest_dataFrame_df['trade_date'] = pd.to_datetime(backtest_dataFrame_df['trade_date']).dt.tz_localize(None)
        standard_deviation_df['trade_date'] = pd.to_datetime(standard_deviation_df['trade_date']).dt.tz_localize(None)

        all_trade_date_df = pd.concat([plot_dataFrame["trade_date"], self.forecast_df["trade_date"]], ignore_index=True)
        all_trade_date_df = pd.merge(all_trade_date_df, plot_dataFrame, on='trade_date', how='left')
        all_trade_date_df = pd.merge(all_trade_date_df, forecast_df, on='trade_date', how='left')
        all_trade_date_df = pd.merge(all_trade_date_df, data_conditional_volatility_df, on='trade_date', how='left')
        all_trade_date_df = pd.merge(all_trade_date_df, backtest_dataFrame_df, on='trade_date', how='left')
        all_trade_date_df = pd.merge(all_trade_date_df, standard_deviation_df, on='trade_date', how='left')

        if self.garch_fit is not None:
            # Create the first axis for 'chg_pct' and volatility
            fig, ax1 = plt.subplots()

            ax1.plot(all_trade_date_df["trade_date"], all_trade_date_df["pct_chg"], label='pct_chg', color='blue')
            ax1.plot(all_trade_date_df["trade_date"], all_trade_date_df["mean"], label='mean', color='pink')
            ax1.plot(all_trade_date_df["trade_date"], all_trade_date_df["cond_vol"], label='Conditional Volatility', color='orange')
            ax1.plot(all_trade_date_df["trade_date"], all_trade_date_df["standard_deviation"], label='standard deviation',color='gray')
            ax1.set_xlabel('Date')
            ax1.set_ylabel('chg_pct / cond_vol / standard_deviation', color='black')
            ax1.tick_params(axis='y', labelcolor='black')
            ax1.legend(loc='upper left')  # Add legend for ax1

            # Create the second axis for 'close', 'upper_value', and 'lower_value'
            ax2 = ax1.twinx()

            ax2.plot(all_trade_date_df["trade_date"], all_trade_date_df["predicted_upper_value_list"],
                     label='predicted_upper_value_list', color='red', marker='o', markersize=2)
            ax2.plot(all_trade_date_df["trade_date"], all_trade_date_df["predicted_lower_value_list"],
                     label='predicted_lower_value_list', color='green', marker='o', markersize=2)
            ax2.plot(all_trade_date_df["trade_date"], all_trade_date_df["back_test_close"],
                     label='back_test_close', color='purple', marker='o', markersize=2)
            ax2.plot(all_trade_date_df["trade_date"], all_trade_date_df["close"],
                     label='close', color='purple', marker='o', markersize=2)

            ax2.set_ylabel('close / upper_value / lower_value / back_test_close', color='black', labelpad=20)
            ax2.tick_params(axis='y', labelcolor='black')
            ax2.legend(loc='lower right')  # Add legend for ax2

            # Title and display
            market = self.params['market']
            stock = self.params['stock']
            start_date = self.params['start_date']
            end_date = self.params['end_date']

            plt.title(f'GARCH Prediction_{market}.{stock}.{start_date}-{end_date}')
            plt.xticks(rotation=90)
            fig.tight_layout()
            plt.show()

            self.all_trade_date_df = all_trade_date_df

    def write_data(self):
        market = self.params['market']
        stock = self.params['stock']
        start_date = self.params['start_date']
        end_date = self.params['end_date']

        file_full_name = FileUtility.get_full_filename_by_timestamp(
            rf"GARCH Prediction_{market}.{stock}.{start_date}-{end_date}", "xlsx")
        self.all_trade_date_df.to_excel(file_full_name)

    def garch_stock_analysis(self):
        # Load the data
        self.load_data()
        # Fit GARCH model
        self.fit_garch_model()
        # Forecast future volatility
        self.forecast_garch()

        # Get back test data
        params["start_date"] = params["backtest_start_date"]
        params["end_date"] = params["backtest_end_date"]
        params["predict_or_backtest"] = "backtest"
        self.load_data()

        # Plot GARCH volatility
        self.plot_garch_volatility()
        # Write tested data
        self.write_data()


# Example usage
if __name__ == "__main__":
    params_list = [
        {
            'market': "CN",
            'stock': '000001.SH',
            'start_date': '20241001',
            'end_date': '20241218',
            'predict_or_backtest': 'predict',
            'analysis_column': 'pct_chg',
            'backtest_start_date': '20241001',
            'backtest_end_date': '20241220',
        },
        {
            'market': "CN",
            'stock': '601368.SH',
            'start_date': '20241001',
            'end_date': '20241207',
            'predict_or_backtest': 'predict',
            'analysis_column': 'pct_chg',
            'backtest_start_date': '20241001',
            'backtest_end_date': '20241218',
        },
        {
            'market': "CN",
            'stock': '603839.SH',
            'start_date': '20241001',
            'end_date': '20241207',
            'predict_or_backtest': 'predict',
            'analysis_column': 'pct_chg',
            'backtest_start_date': '20241001',
            'backtest_end_date': '20241218',
        },
        {
            'market': "US",
            'stock': 'SNPMF',
            'start_date': '20241001',
            'end_date': '20241207',
            'predict_or_backtest': 'predict',
            'analysis_column': 'pct_chg',
            'backtest_start_date': '20241001',
            'backtest_end_date': '20241218',
        },
        {
            'market': "US",
            'stock': 'C',
            'start_date': '20241001',
            'end_date': '20241207',
            'predict_or_backtest': 'predict',
            'analysis_column': 'pct_chg',
            'backtest_start_date': '20241001',
            'backtest_end_date': '20241218',
        },
    ]

    for params in params_list:
        garchManager = GARCHManager(params)
        garchManager.garch_stock_analysis()
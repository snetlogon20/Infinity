import matplotlib.pyplot as plt
import pandas
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
import numpy as np

class ARMAManager:
    def __init__(self, params):
        self.params = params

        self.dataFrame = None
        self.predict_dataFrame = None
        self.backtest_dataFrame = None
        self.best_model = None
        self.arma_df = None
        self.model_fit = None
        self.result_df = None
        self.forecast_df = None

        self.best_p = None
        self.best_q = None
        self.best_aic = None

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
                        amount,
                        vwap,
                        turnover_ratio,
                        total_mv,
                        pe,
                        pb
                from indexsysdb.df_tushare_us_stock_daily
                where ts_code = '{stock}' AND 
                trade_date>= '{start_date}' and 
                trade_date <='{end_date} 
                order by trade_date'
                    """
            columns = [
                'ts_code',
                'trade_date',
                'close_point',
                'open_point',
                'high_point',
                'low_point',
                'pre_close',
                'change_point',
                'pct_change',
                'vol',
                'amount',
                'vwap',
                'turnover_ratio',
                'total_mv',
                'pe',
                'pb'
            ]
        if market == "CN":
            sql = rf"""
                select 	
                    ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount
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
            columns = [
                'ts_code',
                'trade_date',
                'open',
                'high',
                'low',
                'close',
                'pre_close',
                'change',
                'pct_chg',
                'vol',
                'amount'
            ]

        clickhouseService = ClickhouseService()
        dataFrame = clickhouseService.getDataFrame(sql, columns)

        if predict_or_backtest == "predict":
            self.dataFrame = dataFrame
            self.predict_dataFrame = dataFrame
        else:
            self.backtest_dataFrame = dataFrame

        return dataFrame

    def plot_series(self):
        market = self.params["market"]
        stock = self.params['stock']
        start_date = self.params['start_date']
        end_date = self.params['end_date']

        """Plot the time series data."""
        if self.dataFrame is not None:
            if market == "US":
                ax_line = self.dataFrame.plot.line(x='trade_date', y='close_point')
                ax_scatter = self.dataFrame.plot.scatter(x='trade_date', y='pct_change')

            elif market == "CN":
                ax_line = self.dataFrame.plot.line(x='trade_date', y='close')
                ax_scatter = self.dataFrame.plot.scatter(x='trade_date', y='pct_chg')

            ax_line.set_title(rf'Stock Close Point: {market}-{stock} Between:{start_date} ~ {end_date}')
            ax_scatter.set_title(rf'Stock Change Volatility: {market}-{stock} Between:{start_date} ~ {end_date}')

    def key_indicators(self):
        analysis_column = self.params["analysis_column"]
        x = self.dataFrame["trade_date"].values
        y = self.dataFrame[analysis_column].values

        key_indicators_df = pandas.DataFrame(y, columns=[analysis_column])
        stats = pandas.DataFrame()
        stats["Mean"] = key_indicators_df.mean()
        stats["Std_Dev"] = key_indicators_df.std()
        stats["Variance"] = key_indicators_df.var()
        stats["kurt"] = key_indicators_df.kurt()
        stats["skew"] = key_indicators_df.skew()
        stats["median"] = key_indicators_df.median()
        stats["sem"] = key_indicators_df.sem()
        stats["skew"] = key_indicators_df.skew()
        print(stats)
        return stats

    def plot_acf_pacf(self):
        """Plot ACF and PACF for determining p and q."""
        if self.dataFrame is not None:
            plot_acf(self.dataFrame[self.params["analysis_column"]])
            plot_pacf(self.dataFrame[self.params["analysis_column"]])
            plt.show()

    def find_best_arima_model(self):
        best_aic = np.inf
        best_p = None
        best_q = None
        best_model = None
        #data = self.dataFrame
        arma_df = self.dataFrame[self.params["analysis_column"]]

        p = self.params["p"]
        q = self.params["q"]
        p_range = range(0, p)  # Example: p can be 0 to 4
        q_range = range(0, q)  # Example: q can be 0 to 4

        # Iterate through possible values of p and q
        for p in p_range:
            for q in q_range:
                try:
                    model = ARIMA(arma_df, order=(p, 0, q))
                    model_fit = model.fit()
                    # Compare models based on AIC
                    if model_fit.aic < best_aic:
                        best_aic = model_fit.aic
                        best_p = p
                        best_q = q
                        best_model = model_fit
                except Exception as e:
                    print(f"Error fitting ARIMA({p}, 0, {q}): {e}")
                    continue

        print(f"Best p: {best_p}, Best q: {best_q}, AIC: {best_aic}")
        self.best_p = best_p
        self.best_q = best_q
        self.best_aic = best_aic
        self.best_model = best_model
        return best_model

    def fit_arma_model(self):
        """Fit the ARMA model and forecast future points."""
        arma_df = self.dataFrame[self.params["analysis_column"]]
        p = self.params["p"]
        q = self.params["q"]
        arma_steps = self.params["arma_steps"]

        if self.dataFrame is not None:
            #  Step 1， AIRMA 计算拟合summary
            model_fit = self.best_model
            print(model_fit.summary())

            # Step 2. 计算拟合值，查看拟合程度
            length = len(model_fit.fittedvalues)
            last_trade_dates = self.dataFrame["trade_date"].iloc[-length:]
            print(last_trade_dates)

            result_df = pandas.DataFrame({
                'trade_date': last_trade_dates,
                'fitted_values': model_fit.fittedvalues
            })

            # Step 3. 计算未来 n 天的预测值， Forecast the next 10 data points
            forecast_dates = pandas.date_range(start=self.dataFrame["trade_date"].iloc[-1], periods=arma_steps + 1, freq='D')[1:]
            forecast = model_fit.forecast(steps=arma_steps)
            print("Next 10 predictions:\n", forecast)
            forecast_df = pandas.DataFrame({
                'trade_date': forecast_dates,
                'fitted_values': forecast
            })
            forecast_df.columns = ["trade_date", "values"]
            forecast_df["trade_date"] = pandas.to_datetime(forecast_df["trade_date"], errors='coerce')
            forecast_df["trade_date"] = forecast_df["trade_date"].dt.strftime('%Y-%m-%d')

            self.arma_df = arma_df
            self.model_fit = model_fit
            self.result_df = result_df
            self.forecast_df = forecast_df

            return
        else:
            print("Data is not loaded.")
            return None

    def draw_line_chart(self):
        market = self.params['market']
        stock = self.params['stock']
        start_date = self.params['start_date']
        end_date = self.params['end_date']

        # Step 1. 初始化变量
        arma_df = self.arma_df
        model_fit = self.model_fit
        result_df = self.result_df
        forecast_df = self.forecast_df
        backtest_df = self.backtest_dataFrame
        best_p = self.best_p
        best_q = self.best_q
        best_aic = self.best_aic

        # Step 2. 整理数据
        backtest_df["trade_date"] = backtest_df["trade_date"].astype(str)
        backtest_df["trade_date"] = pandas.to_datetime(backtest_df["trade_date"], format='%Y%m%d').dt.strftime('%Y-%m-%d')
        backtest_df = backtest_df[backtest_df["trade_date"].isin(forecast_df["trade_date"])]
        backtest_df = backtest_df.sort_values(by="trade_date").reset_index(drop=True)

        # Step 3. 作图， 看 拟合值 和 原始数据
        plt.plot(result_df["trade_date"], model_fit.fittedvalues, color='red', label='Fitted')
        plt.plot(forecast_df["trade_date"], forecast_df["values"], color='green', label='Forecasted')
        plt.plot(backtest_df["trade_date"], backtest_df[self.params["analysis_column"]], color='yellow', label='backtest')
        plt.plot(result_df["trade_date"], arma_df, color='blue', label='Original')

        plt.xticks(rotation=90)
        plt.legend()
        plt.xlabel('Trade Date')
        plt.ylabel('Values')

        plt.title(
        plt.title(rf'Stock: {market}-{stock} Between: {start_date} ~ {end_date} best_p: {best_p}, best_q: {best_q}, AIC: {best_aic:.2f}'))
        plt.legend()
        plt.show()


def arma_stock(params):
    # Initialize with path to your dataset
    arma_analysis = ARMAManager(params)

    # Load the data
    arma_analysis.load_data()

    # Plot the time series data
    arma_analysis.plot_series()

    # Plot the time series data
    arma_analysis.key_indicators()

    # Plot ACF and PACF to determine p and q
    arma_analysis.plot_acf_pacf()

    # find out the fittest model
    arma_analysis.find_best_arima_model()

    # Fit ARMA model (example: p=2, q=2)
    arma_analysis.fit_arma_model()

    # load the data for back test
    params['start_date'] = params['backtest_start_date']
    params['end_date'] = params['backtest_end_date']
    params['predict_or_backtest'] = 'backtest'
    # Load the data
    arma_analysis.load_data()

    # plot the line chart
    arma_analysis.draw_line_chart()


# Example usage
if __name__ == "__main__":
    params_list =[
        # {
        # 'market': "CN",
        # 'stock': '000001.SH',
        # 'start_date': '20241001',
        # 'end_date': '20241218',
        # 'predict_or_backtest': 'predict',
        # 'analysis_column': 'close',
        # 'backtest_start_date': '20241001',
        # 'backtest_end_date': '20241218',
        # 'predict_or_backtest': 'predict',
        # 'p': 2,
        # 'q': 2,
        # 'arma_steps': 10
        # },
        {
        'market': "CN",
        'stock': '603839.SH',
        'start_date': '20241001',
        'end_date': '20241207',
        'predict_or_backtest': 'predict',
        'analysis_column': 'close',
        'backtest_start_date': '20241001',
        'backtest_end_date': '20241218',
        'predict_or_backtest': 'predict',
        'p': 2,
        'q': 2,
        'arma_steps': 10
        },
        # {
        # 'market': "CN",
        # 'stock': '601368.SH',
        # 'start_date': '20241001',
        # 'end_date': '20241207',
        # 'predict_or_backtest': 'predict',
        # 'analysis_column': 'close',
        # 'backtest_start_date': '20241001',
        # 'backtest_end_date': '20241218',
        # 'predict_or_backtest': 'predict',
        # 'p': 2,
        # 'q': 2,
        # 'arma_steps': 10
        # },
        # {
        # 'market': "US",
        # 'stock': 'SNPMF',
        # 'start_date': '20241001',
        # 'end_date': '20241207',
        # 'predict_or_backtest': 'predict',
        # 'analysis_column': 'close_point',
        # 'backtest_start_date': '20241001',
        # 'backtest_end_date': '20241215',
        # 'predict_or_backtest': 'predict',
        # 'p': 2,
        # 'q': 2,
        # 'arma_steps': 10
        #  },
        # {
        #     'market': "US",
        #     'stock': 'C',
        #     'start_date': '20241001',
        #     'end_date': '20241207',
        #     'predict_or_backtest': 'predict',
        #     'analysis_column': 'close_point',
        #     'backtest_start_date': '20241001',
        #     'backtest_end_date': '20241219',
        #     'predict_or_backtest': 'predict',
        #     'p': 2,
        #     'q': 2,
        #     'arma_steps': 10
        # },
    ]

    for params in params_list:
        arma_stock(params)
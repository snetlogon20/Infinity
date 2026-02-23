import pandas as pd
import matplotlib.pyplot as plt
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.modelService.commonService.CalendarService import CalendarService
import numpy as np

logger = CommonLib.logger
commonLib = CommonLib()

class EWMAAnalyst:
    def __init__(self):
        """
        Initializes the EWMA_Prediction class.
        """
        pass

    # def load_data(self, params):
    #
    #     market = params["market"]
    #     stock = params['stock']
    #     start_date = params['start_date']
    #     end_date = params['end_date']
    #
    #     filter_key_column = params['filter_key_column']
    #
    #     if market == "US":
    #         sql = rf"""
    #             select ts_code,
    #                     trade_date,
    #                     close_point,
    #                     open_point,
    #                     high_point,
    #                     low_point,
    #                     pre_close,
    #                     change_point,
    #                     pct_change,
    #                     vol,
    #                     amount
    #             from indexsysdb.df_tushare_us_stock_daily
    #             where ts_code = '{stock}' AND
    #             trade_date>= '{start_date}' and
    #             trade_date <='{end_date}'
    #             order by trade_date
    #         """
    #         #columns = ['ts_code', 'trade_date', 'close_point', 'pct_change', 'vol', 'amount']
    #         columns = ['ts_code', 'trade_date', 'close', 'open_point', 'high_point', 'low_point', 'pre_close', 'change_point', 'pct_chg', 'vol', 'amount']
    #     elif market == "CN":
    #         sql = rf"""
    #             select
    #                 ts_code, trade_date, close, pct_chg, vol, amount
    #             from
    #             (
    #                 select
    #                     ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount
    #                 from indexsysdb.df_tushare_stock_daily
    #                 where ts_code = '{stock}' AND
    #                     trade_date >= '{start_date}' AND
    #                     trade_date <= '{end_date}'
    #                 union all
    #                 select
    #                     ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount
    #                 from indexsysdb.df_tushare_cn_index_daily
    #                 where ts_code = '{stock}' AND
    #                     trade_date >= '{start_date}' AND
    #                     trade_date <= '{end_date}'
    #             )
    #             order by trade_date
    #         """
    #         columns = ['ts_code', 'trade_date', 'close', 'pct_chg', 'vol', 'amount']
    #
    #     clickhouseService = ClickhouseService()
    #     dataFrame = clickhouseService.getDataFrame(sql, columns)
    #
    #     # 统一 trade_date 列为 Timestamp 类型
    #     dataFrame['trade_date'] = pd.to_datetime(dataFrame['trade_date'])
    #
    #     return dataFrame

    # EWMA 计算和预测函数
    def ewma_prediction(self, dataFrame, next_n_working_days_df, filter_key_column, analysis_column, prediction_n_steps, span=30):
        # 计算 EWMA
        dataFrame_dwma = dataFrame.copy()
        dataFrame_dwma['ewma'] = dataFrame_dwma[analysis_column].ewm(span=span, adjust=False).mean()

        # 预测：使用最后一个 EWMA 值作为未来预测值, 并不是真正的预测
        last_ewma_value = dataFrame_dwma['ewma'].iloc[-1]
        future_dates = next_n_working_days_df[CommonParameters.CALENDAR_PRIMARY_KEY_FILED].tail(prediction_n_steps - 1).reset_index(drop=True)

        ewma_prediction_df = pd.DataFrame({
            filter_key_column: future_dates,
            'ewma_prediction': [last_ewma_value] * (prediction_n_steps -1)
        })
        ewma_prediction_df[filter_key_column] = pd.to_datetime(ewma_prediction_df[filter_key_column])

        # 返回 EWMA 结果和预测结果
        ewma_df = dataFrame_dwma[[filter_key_column, 'ewma']].copy()
        ewma_df[filter_key_column] = pd.to_datetime(ewma_df[filter_key_column])
        return ewma_df, ewma_prediction_df

    def backtest_prediction(self, dataFrame, filter_key_column, analysis_column, prediction_n_steps, span=30):
        # 分割数据：训练集和测试集
        train_size = len(dataFrame) - prediction_n_steps
        train_data = dataFrame.iloc[:train_size].copy()
        test_data = dataFrame.iloc[train_size:].copy()

        # 在训练集上计算 EWMA
        train_data['ewma'] = train_data[analysis_column].ewm(span=span, adjust=False).mean()

        # 用最后一个 EWMA 值作为初始预测值
        last_ewma_value = train_data['ewma'].iloc[-1]
        predictions = [last_ewma_value]

        # 滚动预测：逐步更新 EWMA 值
        for i in range(1, prediction_n_steps):
            # 动态计算新的 EWMA 值
            temp_df = train_data.tail(span + i)
            ewma_value = temp_df[analysis_column].ewm(span=span, adjust=False).mean().iloc[-1]
            predictions.append(ewma_value)

        # 构造回测结果 DataFrame
        min_length = min(len(test_data), len(predictions))
        backtest_df = pd.DataFrame({
            filter_key_column: test_data[filter_key_column].values[:min_length],
            'actual_value': test_data[analysis_column].values[:min_length],
            'backtest_prediction': predictions[:min_length]
        })

        # 计算误差指标
        actual_values = backtest_df['actual_value'].values
        predicted_values = backtest_df['backtest_prediction'].values

        mse = np.mean((actual_values - predicted_values) ** 2)
        mae = np.mean(np.abs(actual_values - predicted_values))
        rmse = np.sqrt(mse)

        backtest_error_metrics = {
            'backtest-MSE': mse,
            'backtest-MAE': mae,
            'backtest-RMSE': rmse
        }
        logger.info(rf"backtest_error_metrics: %s ", backtest_error_metrics)

        return backtest_df, backtest_error_metrics

    # 滚动预测函数
    def rolling_prediction(self, dataFrame, next_n_working_days_df, filter_key_column, analysis_column, prediction_n_steps, span=30):
        # 滚动预测：每次使用最新的 EWMA 值进行预测
        rolling_predictions = []
        actual_values = []  # 存储实际值用于计算误差

        for i in range(prediction_n_steps - 1) :
            # 动态计算 EWMA
            temp_df = dataFrame.tail(span + i)
            ewma_value = temp_df[analysis_column].ewm(span=span, adjust=False).mean().iloc[-1]
            rolling_predictions.append(ewma_value)

        future_dates = next_n_working_days_df[CommonParameters.CALENDAR_PRIMARY_KEY_FILED].tail(prediction_n_steps - 1).reset_index(drop=True)
        rolling_prediction_df = pd.DataFrame({
            filter_key_column: future_dates,
            'rolling_prediction': rolling_predictions
        })
        rolling_prediction_df[filter_key_column] = pd.to_datetime(rolling_prediction_df[filter_key_column])

        return rolling_prediction_df

    # 主分析流程
    def analyze_workflow(self, params):

        start_date = params["start_date"]
        end_date = params["end_date"]
        next_n_days = params["next_n_days"]
        analysis_column = params["analysis_column"]
        prediction_n_steps  = next_n_days
        span = params["span"]
        filter_key_column = params["filter_key_column"]

        # 步骤 1: 加载原始数据
        dataFrame = params["dataFrame"]

        # 步骤 2: 加载工作日数据
        calendar_service = CalendarService()
        start_to_end_days_df = calendar_service.load_calendar(start_date, end_date)
        next_n_working_days_df = calendar_service.load_next_n_working_days_calendar(start_date, end_date, next_n_days)
        working_days_df = pd.concat([start_to_end_days_df, next_n_working_days_df], ignore_index=True)
        working_days_df = working_days_df.drop_duplicates(subset=[CommonParameters.CALENDAR_PRIMARY_KEY_FILED]).sort_values(
            by=CommonParameters.CALENDAR_PRIMARY_KEY_FILED).reset_index(drop=True)  #trade_date 在此hard code, 是因为calendar中的日期索引必然为trade_date

        # 步骤 3: EWMA 计算和预测
        ewma_df, ewma_prediction_df = self.ewma_prediction(dataFrame, next_n_working_days_df,filter_key_column, analysis_column, prediction_n_steps, span)

        # 步骤 4: 回测
        backtest_df, backtest_error_metrics = self.backtest_prediction(dataFrame, filter_key_column, analysis_column, prediction_n_steps, span)

        # 步骤 5: 滚动预测
        rolling_prediction_df = self.rolling_prediction(dataFrame,next_n_working_days_df, filter_key_column, analysis_column, prediction_n_steps, span)

        # 步骤 6: 合并所有数据
        # 确保 working_days_df 的 trade_date 列为 datetime64[ns] 类型
        working_days_df[filter_key_column] = pd.to_datetime(working_days_df[CommonParameters.CALENDAR_PRIMARY_KEY_FILED])

        # 合并数据
        all_dataframe = working_days_df.merge(dataFrame, on=filter_key_column, how='left') \
            .merge(ewma_df, on=filter_key_column, how='left') \
            .merge(ewma_prediction_df, on=filter_key_column, how='left') \
            .merge(backtest_df, on=filter_key_column, how='left') \
            .merge(rolling_prediction_df, on=filter_key_column, how='left')

        self.draw_plot(all_dataframe, analysis_column, backtest_error_metrics, filter_key_column)

        return all_dataframe

    def draw_plot(self, all_dataframe, analysis_column, backtest_error_metrics, filter_key_column):
        # 步骤 7: 绘图
        plt.figure(figsize=(12, 6))
        plt.plot(all_dataframe[filter_key_column], all_dataframe[analysis_column], label='Actual Data', color='blue')
        plt.plot(all_dataframe[filter_key_column], all_dataframe['ewma'], label='EWMA', color='orange')
        plt.plot(all_dataframe[filter_key_column], all_dataframe['ewma_prediction'], label='EWMA Prediction',
                 color='green', )
        plt.plot(all_dataframe[filter_key_column], all_dataframe['backtest_prediction'], label='Backtest Prediction',
                 color='red', )
        plt.plot(all_dataframe[filter_key_column], all_dataframe['rolling_prediction'], label='Rolling Prediction',
                 color='purple', linestyle='--')
        plt.title('Time Series Analysis and Predictions')
        plt.xlabel('Date')
        plt.ylabel('Value')
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        # 在图表上添加误差指标
        all_error_metrics = {**backtest_error_metrics}
        textstr = '\n'.join([f'{key}: {value:.4f}' for key, value in all_error_metrics.items()])
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        plt.gca().text(0.05, 0.95, textstr, transform=plt.gca().transAxes, fontsize=10,
                       verticalalignment='top', bbox=props)
        plt.show()

        return all_dataframe


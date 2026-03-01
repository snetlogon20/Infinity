import json

from dataIntegrator import CommonLib
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from sklearn.metrics import r2_score
from scipy import stats
import numpy as np
import pandas as pd

from dataIntegrator.plotService.HeatMapPlotManager import HeatMapPlotManager
from dataIntegrator.plotService.LinePlotManager import LinePlotManager
from dataIntegrator.plotService.ScatterPlotManager import ScatterPlotManager
from dataIntegrator.utility.FileUtility import FileUtility
import matplotlib.pyplot as plt
import seaborn as sns


logger = CommonLib.logger
commonLib = CommonLib()

class GeneralLinearRegression:

    def __init__(self):
        pass

    @classmethod
    def perform_linear_regression(self, param_dict):
        response_dict = {}

        try:
            # 将字串转为列表
            xColumns_str = param_dict.get("xColumns")
            clean_str = xColumns_str.strip().replace('\n', '').replace(' ', '')
            parts = [p.strip().strip("'") for p in clean_str.split(',')]
            xColumns = [f"{col}" for col in parts if col]

            yColumn  = param_dict.get("yColumn")
            dataframe = param_dict.get("result")
            X = dataframe[xColumns]
            y = dataframe[yColumn]
            if_run_test = param_dict.get("if_run_test")
            X_given_test_source_path = param_dict.get("X_given_test_source_path")

            logger.info(rf"start the regression: yColumn: {yColumn}, xColumns = {xColumns}")
        except Exception as e:
            raise commonLib.raise_custom_error(error_code="000103",custom_error_message=rf"获取param_dict 失败: {param_dict}", e=e)
            return

        try:
            logger.info(rf"start the LinearRegression")

            ############################
            # Step 1 Test the model
            ############################
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            model = LinearRegression()
            model.fit(X_train, y_train)

            y_pred = model.predict(X_test)

            ############################
            # Step 2 Evaluate the model
            ############################
            logger.info(rf"start the Evaluate the model")

            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            rss = np.sum((y_test - y_pred) ** 2)
            tss = np.sum((y_test - np.mean(y_test)) ** 2)
            f_statistic = (tss - rss) / model.coef_.shape[0] / (rss / (len(y_test) - X_test.shape[1] - 1))
            p_value = 1 - stats.f.cdf(f_statistic, X_test.shape[1], len(y_test) - X_test.shape[1] - 1)

            coefficients = pd.DataFrame(model.coef_, X.columns, columns=["Coefficient"])

            logger.info(f"r2:{r2},mse:{mse}")
            logger.info(f"rss:{rss},tss:{tss},f_statistic(越大越好):{f_statistic},p_value(越小越好):{p_value}")
            logger.info(coefficients)

            ##################################################
            # Step 3 Predict the values per full X value
            ##################################################
            logger.info(rf"start the prediction")

            X_full_test = X
            y_full_pred = model.predict(X_full_test)

            full_test_df = pd.DataFrame(X_full_test)
            full_test_df[yColumn] = y
            full_test_df['y_full_pred'] = y_full_pred
            full_test_df['gap'] = y - y_full_pred
            full_test_df['gap_percent'] = (y - y_full_pred)/y

            # 获取 full_test_df 中与 dataframe 列名重复的列
            common_columns = dataframe.columns.intersection(full_test_df.columns)
            # 删除这些列
            full_test_filtered = full_test_df.drop(columns=common_columns)
            # 进行 join 操作
            combined_df_wit_X_and_full_test_df = dataframe.join(full_test_filtered)

            ##################################################
            # Step 4 Predict the values per the given input
            ##################################################
            logger.info(rf"start the prediction by give X")

            if if_run_test == "true":
                X_given_test = pd.read_excel(X_given_test_source_path,usecols=xColumns)
                # Make predictions
                y_given_pred = model.predict(X_given_test)

                X_given_test_df = pd.DataFrame(X_given_test)
                X_given_test_df['y_given_pred'] = y_given_pred

            ##################################################
            # Step 5 Corr
            ##################################################
            logger.info(rf"start the corr")
            numeric_cols = dataframe.select_dtypes(include=['number']).columns
            df_numeric = dataframe[numeric_cols]
            df_numeric = df_numeric.fillna(0)
            dataframe_corr_df = df_numeric.corr()

            ##################################################
            # Step 5 return
            ##################################################
            logger.info(rf"start the return")
            response_dict["mse"] = mse
            response_dict["r2"] = r2
            response_dict["rss"] = rss
            response_dict["tss"] = tss
            response_dict["f_statistic"] = f_statistic
            response_dict["p_value"] = p_value
            response_dict["coefficients"] = coefficients

            response_dict["model"] = model
            response_dict["full_test_df"] = full_test_df
            response_dict["dataframe"] = combined_df_wit_X_and_full_test_df
            #response_dict["X_given_test_df"] = X_given_test_df
            response_dict["dataframe_corr_df"] =  dataframe_corr_df

            return response_dict

        except Exception as e:
            raise commonLib.raise_custom_error(error_code="000103",custom_error_message=rf"执行回归过程失败", e=e)
        return



    def run_linear_regression_by_AI(self, param_dict_in):

        param_dict = {}

        param_dict["isLinearRegressionRequired"] = param_dict_in.get("isLinearRegressionRequired", "no")
        if param_dict["isLinearRegressionRequired"] == "no":
            return

        param_dict["result"] = param_dict_in.get("results", "None")

        param_dict["plotType"] = param_dict_in.get("plotType", "lineChart")
        param_dict["xColumns"] = param_dict_in.get("xColumns", "None")
        param_dict["yColumn"] = param_dict_in.get("yColumn", "None")

        param_dict["PlotXColumn"] = param_dict_in.get("PlotXColumn", "None")
        param_dict["PlotTitle"] = param_dict_in.get('linearRequirement', {}).get("PlotTitle", "None")
        param_dict["xlabel"] = param_dict_in.get('linearRequirement', {}).get("xlabel", "None")
        param_dict["ylabel"] = param_dict_in.get('linearRequirement', {}).get("ylabel", "None")
        param_dict["if_run_test"] = param_dict_in.get('linearRequirement', {}).get("if_run_test", "false")
        param_dict["X_given_test_source_path"] = param_dict_in.get('linearRequirement', {}).get("if_run_test", "None")

        #####################################
        # 1. run regression test
        #####################################
        response_dict = self.perform_linear_regression(param_dict)

        #####################################
        # 2. run heatmap
        #####################################
        param_dict["isPlotRequired"] = "yes"
        dataframe_heatmap = response_dict["full_test_df"]
        param_dict["results"] = dataframe_heatmap.corr()
        param_dict["plotRequirement"] = {}
        param_dict["plotRequirement"]["PlotTitle"] = param_dict["PlotTitle"]
        param_dict["plotRequirement"]["xlabel"] = param_dict["xlabel"]
        param_dict["plotRequirement"]["ylabel"] = param_dict["ylabel"]
        heatMapPlotManager = HeatMapPlotManager()
        heatMapPlotManager.draw_plot(param_dict)

        #####################################
        # 2. run plot chart
        #####################################
        param_dict["isPlotRequired"] = "yes"
        param_dict["results"] = response_dict.get("dataframe")

        #param_dict["plotRequirement"]["PlotX"] = "df_sys_calendar__trade_date"
        param_dict["plotRequirement"]["PlotX"] = param_dict["PlotXColumn"]
        param_dict["plotRequirement"]["PlotY"] = param_dict["yColumn"] + ",y_full_pred"
        param_dict["plotRequirement"]["PlotTitle"] = param_dict["PlotTitle"]
        param_dict["plotRequirement"]["xlabel"] = param_dict["xlabel"]
        param_dict["plotRequirement"]["ylabel"] = param_dict["ylabel"]
        linePlotManager = LinePlotManager()
        linePlotManager.draw_plot(param_dict)

        return response_dict


def test_perform_linear_regression_single_feature():
    """
    测试单个特征的线性回归
    """
    # 创建测试数据
    X_data = np.random.rand(50, 1)
    y_data = 2 * X_data.ravel() + np.random.normal(0, 0.1, 50)

    df = pd.DataFrame(X_data, columns=['feature1'])
    df['target'] = y_data

    param_dict = {
        'xColumns': "'feature1'",
        'yColumn': 'target',
        'result': df,
        'if_run_test': 'false',
        'X_given_test_source_path': None
    }

    response_dict = GeneralLinearRegression.perform_linear_regression(param_dict)

    assert 'r2' in response_dict
    assert 'coefficients' in response_dict
    assert len(response_dict['coefficients']) == 1

    print("单特征测试通过！")

# 运行测试
if __name__ == "__main__":
    test_perform_linear_regression_single_feature()
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

    def __init__(self, model=None, alpha=None, beta_dict=None, x_columns=None):
        self.model = model
        self.alpha = alpha
        self.beta_dict = beta_dict
        self.x_columns = x_columns
        self.last_regression_result = None

    @classmethod
    def perform_linear_regression(self, param_dict):
        response_dict = {}

        try:
            # 将字串转为列表
            xColumns_str = param_dict.get("xColumns")
            clean_str = xColumns_str.strip().replace('\n', '').replace(' ', '')
            parts = [p.strip().strip("'") for p in clean_str.split(',')]
            xColumns = [f"{col}" for col in parts if col]

            yColumn = param_dict.get("yColumn")
            dataframe = param_dict.get("result")
            X = dataframe[xColumns]
            y = dataframe[yColumn]
            if_run_test = param_dict.get("if_run_test")
            X_given_test_source_path = param_dict.get("X_given_test_source_path")

            logger.info(rf"start the regression: yColumn: {yColumn}, xColumns = {xColumns}")
        except Exception as e:
            raise commonLib.raise_custom_error(error_code="000103",
                                               custom_error_message=rf"获取param_dict 失败: {param_dict}", e=e)
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

            # 获取 alpha (截距) 和 beta (系数)
            alpha = model.intercept_  # 截距
            beta_dict = {}  # 存储每个 x 变量的 beta 值
            for i, col in enumerate(X.columns):
                beta_dict[col] = model.coef_[i]
                logger.info(f"{col} 的 beta 值 (系数): {model.coef_[i]:.6f}")

            logger.info(f"alpha 值 (截距): {alpha:.6f}")

            logger.info(f"r2:{r2},mse:{mse}")
            logger.info(f"rss: {rss}")
            logger.info(f"tss: {tss}")
            logger.info(f"f_statistic (越大越好): {f_statistic}")
            logger.info(f"p_value (越小越好): {p_value}")
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
            full_test_df['gap_percent'] = (y - y_full_pred) / y

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
                X_given_test = pd.read_excel(X_given_test_source_path, usecols=xColumns)
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
            response_dict["alpha"] = alpha
            response_dict["beta_dict"] = beta_dict
            response_dict["x_columns"] = xColumns

            response_dict["model"] = model
            response_dict["full_test_df"] = full_test_df
            response_dict["dataframe"] = combined_df_wit_X_and_full_test_df
            response_dict["dataframe_corr_df"] = dataframe_corr_df

            return response_dict

        except Exception as e:
            raise commonLib.raise_custom_error(error_code="000103", custom_error_message=rf"执行回归过程失败", e=e)
        return

    def predict_with_beta_alpha(self, x_values):
        """
        使用保存的alpha和beta值进行预测
        """
        if self.alpha is None or self.beta_dict is None or self.x_columns is None:
            raise ValueError("请先运行回归分析，获取alpha和beta值")

        if len(x_values) != len(self.x_columns):
            raise ValueError(f"输入的X值数量({len(x_values)})与特征数量({len(self.x_columns)})不匹配")

        # 计算预测值: y = alpha + sum(beta_i * x_i)
        y_pred = self.alpha

        for i, (col, x_val) in enumerate(zip(self.x_columns, x_values)):
            y_pred += self.beta_dict[col] * float(x_val)

        return y_pred

    def predict_with_input(self):
        """
        交互式预测：提示用户输入X值，然后计算Y
        """
        if not self.x_columns or not self.beta_dict or self.alpha is None:
            print("没有找到回归结果，请先运行回归分析。")
            return None

        print(f"\n回归模型信息：")
        print(f"alpha (截距): {self.alpha:.6f}")
        print(f"特征变量: {self.x_columns}")
        print(f"beta系数: {self.beta_dict}")
        print(f"回归方程: y = {self.alpha:.6f} ", end="")
        for i, col in enumerate(self.x_columns):
            sign = "+" if self.beta_dict[col] >= 0 else "-"
            print(f"{sign} {abs(self.beta_dict[col]):.6f}*{col}", end=" ")
        print("\n")

        print("请输入各个X变量的值：")
        x_values = []

        for i, col in enumerate(self.x_columns):
            while True:
                try:
                    x_val = float(input(f"{col}: "))
                    x_values.append(x_val)
                    break
                except ValueError:
                    print("请输入有效的数字！")

        # 使用模型进行预测
        y_pred = self.predict_with_beta_alpha(x_values)

        print(f"\n预测结果：")
        for i, col in enumerate(self.x_columns):
            print(f"  {col} = {x_values[i]}")
        print(f"预测的 Y 值 = {y_pred:.6f}")

        return y_pred, x_values

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

        # 保存回归结果到实例变量
        self.model = response_dict.get("model")
        self.alpha = response_dict.get("alpha")
        self.beta_dict = response_dict.get("beta_dict")
        self.x_columns = response_dict.get("x_columns")
        self.last_regression_result = response_dict

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

        # param_dict["plotRequirement"]["PlotX"] = "df_sys_calendar__trade_date"
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

    # 创建实例并运行回归
    regressor = GeneralLinearRegression()
    response_dict = regressor.perform_linear_regression(param_dict)

    # 保存回归结果
    regressor.model = response_dict.get("model")
    regressor.alpha = response_dict.get("alpha")
    regressor.beta_dict = response_dict.get("beta_dict")
    regressor.x_columns = response_dict.get("x_columns")

    # 测试预测功能
    print("\n=== 手动输入预测测试 ===")

    # 方法1：使用predict_with_input进行交互式预测
    print("请为feature1输入一个值（例如0.5）：")

    # 由于测试环境无法使用input，我们直接测试predict_with_beta_alpha
    test_x_values = [0.5]
    predicted_y = regressor.predict_with_beta_alpha(test_x_values)
    print(f"\n使用X值{test_x_values}进行预测：")
    print(f"预测的Y值: {predicted_y:.6f}")

    # 验证预测是否正确
    expected_y = regressor.alpha + regressor.beta_dict['feature1'] * 0.5
    print(f"验证计算: {regressor.alpha:.6f} + {regressor.beta_dict['feature1']:.6f} * 0.5 = {expected_y:.6f}")

    assert 'r2' in response_dict
    assert 'coefficients' in response_dict
    assert len(response_dict['coefficients']) == 1
    assert abs(predicted_y - expected_y) < 0.000001  # 验证预测计算正确

    print("单特征测试通过！")


# 运行测试
if __name__ == "__main__":
    test_perform_linear_regression_single_feature()

    # 测试交互式预测功能
    print("\n=== 运行回归并测试交互式预测 ===")

    # 创建示例数据
    np.random.seed(42)
    n_samples = 100

    # 创建3个特征
    X_multi = np.random.randn(n_samples, 3)
    # 生成目标变量：y = 2*x1 + 0.5*x2 - 1.5*x3 + 3 + noise
    y_multi = 2 * X_multi[:, 0] + 0.5 * X_multi[:, 1] - 1.5 * X_multi[:, 2] + 3 + np.random.randn(n_samples) * 0.1

    df_multi = pd.DataFrame(X_multi, columns=['feature1', 'feature2', 'feature3'])
    df_multi['target'] = y_multi

    param_dict_multi = {
        'xColumns': "'feature1','feature2','feature3'",
        'yColumn': 'target',
        'result': df_multi,
        'if_run_test': 'false',
        'X_given_test_source_path': None
    }

    # 创建实例并运行回归
    multi_regressor = GeneralLinearRegression()
    response_dict_multi = multi_regressor.perform_linear_regression(param_dict_multi)

    # 保存回归结果
    multi_regressor.model = response_dict_multi.get("model")
    multi_regressor.alpha = response_dict_multi.get("alpha")
    multi_regressor.beta_dict = response_dict_multi.get("beta_dict")
    multi_regressor.x_columns = response_dict_multi.get("x_columns")

    print("\n=== 多元回归模型已训练完成 ===")
    print("模型信息：")
    print(f"alpha: {multi_regressor.alpha:.6f}")
    print(f"beta系数: {multi_regressor.beta_dict}")
    print(f"回归方程: y = {multi_regressor.alpha:.6f} + {multi_regressor.beta_dict['feature1']:.6f}*feature1 + " +
          f"{multi_regressor.beta_dict['feature2']:.6f}*feature2 + {multi_regressor.beta_dict['feature3']:.6f}*feature3")

    # 测试预测
    test_x_values_multi = [1.0, 0.5, -0.5]
    predicted_y_multi = multi_regressor.predict_with_beta_alpha(test_x_values_multi)
    print(f"\n使用X值{test_x_values_multi}进行预测：")
    print(f"预测的Y值: {predicted_y_multi:.6f}")

    # 验证
    expected_y_multi = (multi_regressor.alpha +
                        multi_regressor.beta_dict['feature1'] * 1.0 +
                        multi_regressor.beta_dict['feature2'] * 0.5 +
                        multi_regressor.beta_dict['feature3'] * (-0.5))
    print(f"验证计算: {expected_y_multi:.6f}")

    print("\n如果想进行交互式预测，可以调用：")
    print("regressor = GeneralLinearRegression()")
    print("regressor.model = [回归模型]")
    print("regressor.alpha = [alpha值]")
    print("regressor.beta_dict = [beta字典]")
    print("regressor.x_columns = [特征列表]")
    print("regressor.predict_with_input()  # 这会提示您输入各个X值")
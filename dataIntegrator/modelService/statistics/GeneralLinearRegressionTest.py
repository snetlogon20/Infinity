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

from dataIntegrator.modelService.statistics.GeneralLinearRegression import GeneralLinearRegression
from dataIntegrator.plotService.HeatMapPlotManager import HeatMapPlotManager
from dataIntegrator.plotService.LinePlotManager import LinePlotManager
from dataIntegrator.plotService.ScatterPlotManager import ScatterPlotManager
from dataIntegrator.utility.FileUtility import FileUtility
import matplotlib.pyplot as plt
import seaborn as sns


logger = CommonLib.logger
commonLib = CommonLib()

class GeneralLinearRegressionTest:

    def __init__(self):
        pass


'''
花旗股票分析
'''
def load_param_dict_stock_analysis_001():

    response_dict = {}

    sql = """
    SELECT 
        df_sys_calendar.trade_date AS df_sys_calendar__trade_date,
        df_tushare_us_stock_daily.pct_change AS df_tushare_us_stock_daily__pct_change,
        df_tushare_shibor_daily.tenor_on AS df_tushare_shibor_daily__tenor_on,
        df_tushare_stock_daily.pct_chg AS df_tushare_stock_daily__pct_chg
    FROM
        df_sys_calendar
    LEFT JOIN df_tushare_us_stock_daily 
        ON df_sys_calendar.trade_date = df_tushare_us_stock_daily.trade_date 
        AND df_tushare_us_stock_daily.ts_code = 'C'
    LEFT JOIN df_tushare_shibor_daily 
        ON df_sys_calendar.trade_date = df_tushare_shibor_daily.trade_date
    LEFT JOIN df_tushare_stock_daily 
        ON df_sys_calendar.trade_date = df_tushare_stock_daily.trade_date 
        AND df_tushare_stock_daily.ts_code = '002093.SZ'
    WHERE 
        df_sys_calendar.trade_date BETWEEN '20241202' AND '20241231'
    """

    clickhouseService = ClickhouseService()
    result = clickhouseService.getDataFrameWithoutColumnsName(sql)

    '''此处放置你需要回归使用时的X轴'''
    xColumns = "df_tushare_shibor_daily__tenor_on, df_tushare_stock_daily__pct_chg"
    yColumn = "df_tushare_us_stock_daily__pct_change"

    response_dict["sql"] = sql
    response_dict["results"] = result
    response_dict["xColumns"] = xColumns
    response_dict["yColumn"] = yColumn

    response_dict["isLinearRegressionRequired"]="yes"

    '''此处放置你需要画图的X轴'''
    response_dict["PlotXColumn"] = "df_sys_calendar__trade_date"
    response_dict["PlotTitle"] = "df_tushare_shibor_daily__tenor_on"
    response_dict["xlabel"] = "df_sys_calendar__trade_date"
    response_dict["ylabel"] = "df_tushare_shibor_daily__tenor_on"
    response_dict["if_run_test"] = "no"
    response_dict["X_given_test_source_path"] = ""

    return response_dict

def load_param_dict_stock_analysis_002():

    response_dict = {}

    sql = """
    select
        df_sys_calendar.trade_date AS df_sys_calendar__trade_date,
        df_tushare_us_stock_daily.pct_change AS df_tushare_us_stock_daily__pct_change,
        df_tushare_shibor_daily.tenor_on AS df_tushare_shibor_daily__tenor_on,
        df_tushare_stock_daily.pct_chg AS df_tushare_stock_daily__pct_chg,
        df_akshare_spot_hist_sge.close AS df_akshare_spot_hist_sge__pct_chg
    FROM
        df_sys_calendar
    LEFT JOIN df_tushare_us_stock_daily 
        ON df_sys_calendar.trade_date = df_tushare_us_stock_daily.trade_date 
        AND df_tushare_us_stock_daily.ts_code = 'C'
    LEFT JOIN df_tushare_shibor_daily 
        ON df_sys_calendar.trade_date = df_tushare_shibor_daily.trade_date
    LEFT JOIN df_tushare_stock_daily 
        ON df_sys_calendar.trade_date = df_tushare_stock_daily.trade_date 
        AND df_tushare_stock_daily.ts_code = '002093.SZ'
    LEFT JOIN df_akshare_spot_hist_sge 
        ON df_sys_calendar.trade_date = formatDateTime(toDate(df_akshare_spot_hist_sge.date), '%Y%m%d')
    WHERE 
        df_sys_calendar.trade_date BETWEEN '20241202' AND '20241231'
order by df_sys_calendar__trade_date
    """

    clickhouseService = ClickhouseService()
    result = clickhouseService.getDataFrameWithoutColumnsName(sql)

    '''此处放置你需要回归使用时的X轴'''
    xColumns = "df_tushare_shibor_daily__tenor_on, df_tushare_stock_daily__pct_chg, df_akshare_spot_hist_sge__pct_chg"
    yColumn = "df_tushare_us_stock_daily__pct_change"

    response_dict["sql"] = sql
    response_dict["results"] = result
    response_dict["xColumns"] = xColumns
    response_dict["yColumn"] = yColumn

    response_dict["isLinearRegressionRequired"]="yes"

    '''此处放置你需要画图的X轴'''
    response_dict["PlotXColumn"] = "df_sys_calendar__trade_date"
    response_dict["PlotTitle"] = "df_tushare_shibor_daily__tenor_on"
    response_dict["xlabel"] = "df_sys_calendar__trade_date"
    response_dict["ylabel"] = "df_tushare_shibor_daily__tenor_on"
    response_dict["if_run_test"] = "no"
    response_dict["X_given_test_source_path"] = ""

    return response_dict

def init():
    pd.set_option('display.max_rows', None)  # 设置打印所有行
    pd.set_option('display.max_columns', None)  # 设置打印所有列
    pd.set_option('display.width', None)  # 自动检测控制台的宽度
    pd.set_option('display.max_colwidth', None)  # 设置列的最大宽度


if __name__ == "__main__":
    # 根据输入的 股票代码逐个计算线性回归
    init()

    # response_dict = load_param_dict_stock_analysis_001()
    # generalLinearRegression = GeneralLinearRegression()
    # generalLinearRegression.run_linear_regression_by_AI(response_dict)

    # scatterPlotManager = ScatterPlotManager()
    # scatterPlotManager.draw_plot(param_dict)

    response_dict = load_param_dict_stock_analysis_002()
    generalLinearRegression = GeneralLinearRegression()
    generalLinearRegression.run_linear_regression_by_AI(response_dict)
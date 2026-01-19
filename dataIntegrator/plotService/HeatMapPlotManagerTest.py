import matplotlib
matplotlib.use('TkAgg')

import pandas as pd

from dataIntegrator.plotService.HeatMapPlotManager import HeatMapPlotManager
from dataIntegrator.plotService.LinePlotManager import LinePlotManager
from dataIntegrator.dataService.ClickhouseService import ClickhouseService


def test_simple_heatmap():
    global test_data
    # 创建测试数据 - 相关性矩阵
    test_data = pd.DataFrame({
        'feature1': [1.0, 0.5, -0.3, 0.8],
        'feature2': [0.5, 1.0, 0.2, -0.1],
        'feature3': [-0.3, 0.2, 1.0, 0.4],
        'feature4': [0.8, -0.1, 0.4, 1.0]
    })
    # 设置索引，通常热力图会使用特征名称作为行列标签
    test_data.index = ['Feature A', 'Feature B', 'Feature C', 'Feature D']
    # 创建测试参数字典
    param_dict = {
        "isPlotRequired": "yes",
        "results": test_data,
        "plotRequirement": {
            "PlotTitle": "Correlation Heatmap Test",
            "xlabel": "Features",
            "ylabel": "Features"
        }
    }
    print("正在生成热力图...")
    plotManager = HeatMapPlotManager()
    plotManager.draw_plot(param_dict)

def test_draw_plot_with_SQL_data():
    response_dict = {}

    sql = """
        select
            df_sys_calendar.trade_date AS df_sys_calendar__trade_date,
            df_tushare_us_stock_daily.pct_change AS df_tushare_us_stock_daily__pct_change,
            df_tushare_shibor_daily.tenor_on AS df_tushare_shibor_daily__tenor_on,
            df_tushare_stock_daily.pct_chg AS df_tushare_stock_daily__pct_chg,
            df_akshare_spot_hist_sge.pct_change AS df_akshare_spot_hist_sge__pct_chg
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

    #处理 df_sys_calendar__trade_date 列，将其转换为行号
    if 'df_sys_calendar__trade_date' in result.columns:
        # 对数据按日期排序并添加行号
        result = result.sort_values(by='df_sys_calendar__trade_date').reset_index(drop=True)
        # 将日期列替换为行号
        result['df_sys_calendar__trade_date'] = range(len(result))
    result = result.corr()


    # 创建测试参数字典
    param_dict = {
        "isPlotRequired": "yes",
        "results": result,
        "plotRequirement": {
            "PlotTitle": "Correlation Heatmap Test",
            "xlabel": "Features",
            "ylabel": "Features"
        }
    }
    print("正在生成热力图...")
    plotManager = HeatMapPlotManager()
    plotManager.draw_plot(param_dict)


if __name__ == '__main__':
    #test_simple_heatmap()
    test_draw_plot_with_SQL_data()
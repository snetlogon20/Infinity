import pandas as pd

from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.plotService.ScatterPlotManager import ScatterPlotManager


def test_simple_draw_plot():
    test_data = pd.DataFrame({
        'date': ['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04'],
        'value1': [10, 20, 15, 25],
        'value2': [5, 15, 10, 30]
    })
    # 创建测试参数字典
    param_dict = {
        "isPlotRequired": "yes",
        "results": test_data,
        "plotRequirement": {
            "PlotX": "date",
            "PlotY": "value1",
            "PlotTitle": "Test Line Plot",
            "xlabel": "Date",
            "ylabel": "Value"
        }
    }
    plotManager = ScatterPlotManager()
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

    # 创建测试参数字典
    param_dict = {
        "isPlotRequired": "yes",
        "results": result,
        "plotRequirement": {
            "PlotX": "df_sys_calendar__trade_date",
            "PlotY": "df_tushare_us_stock_daily__pct_change, df_tushare_stock_daily__pct_chg, df_akshare_spot_hist_sge__pct_chg, df_tushare_shibor_daily__tenor_on",
            "PlotTitle": "Test Line Plot",
            "xlabel": "Date",
            "ylabel": "Value"
        }
    }
    plotManager = ScatterPlotManager()
    plotManager.draw_plot(param_dict)

if __name__ == '__main__':
    # test_simple_draw_plot()
    test_draw_plot_with_SQL_data()
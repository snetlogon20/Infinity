import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from dataIntegrator.analysisService.InquiryManager import InquiryManager
from dataIntegrator.modelService.statistics.StaticAnalyisManager import StaticAnalysisManager


class StaticAnalysisManagerTest:
    def __init__(self):
       pass


def test1_analyz_stock_gold_with_sql():
    sql = """
        SELECT 
            --df_sys_calendar.trade_date AS df_sys_calendar__trade_date,
            df_tushare_us_stock_daily.pct_change AS df_tushare_us_stock_daily__pct_change,
            df_tushare_shibor_daily.tenor_on AS df_tushare_shibor_daily__tenor_on,
            df_tushare_stock_daily.pct_chg AS df_tushare_stock_daily__pct_chg,
            df_akshare_spot_hist_sge.close AS df_akshare_spot_hist_sge__close,
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
        --order by df_sys_calendar__trade_date  
    """
    analyzer = StaticAnalysisManager()
    statistics = analyzer.analyze_with_sql(sql)


def test1_analyz_stock_gold_with_dataframe():
    sql = """
        SELECT 
            --df_sys_calendar.trade_date AS df_sys_calendar__trade_date,
            df_tushare_us_stock_daily.pct_change AS df_tushare_us_stock_daily__pct_change,
            df_tushare_shibor_daily.tenor_on AS df_tushare_shibor_daily__tenor_on,
            df_tushare_stock_daily.pct_chg AS df_tushare_stock_daily__pct_chg,
            df_akshare_spot_hist_sge.close AS df_akshare_spot_hist_sge__close,
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
        --order by df_sys_calendar__trade_date  
    """

    dataFrame = InquiryManager().get_sql_dataset(sql)
    analyzer = StaticAnalysisManager()
    statistics = analyzer.analyze_with_dataframe(dataFrame)

# 使用示例
if __name__ == "__main__":
    test1_analyz_stock_gold_with_sql()
    test1_analyz_stock_gold_with_dataframe()
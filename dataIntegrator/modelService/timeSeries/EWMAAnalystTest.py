import pandas as pd

from dataIntegrator.analysisService.InquiryManager import InquiryManager
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.modelService.timeSeries.EWMAAnalyst import EWMAAnalyst


class EWMAAnalystTest:
    def __init__(self):
        pass

    def load_data(self, params):

        market = params["market"]
        stock = params['stock']
        start_date = params['start_date']
        end_date = params['end_date']

        filter_key_column = params['filter_key_column']

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
        dataFrame = clickhouseService.getDataFrame(sql, columns)

        # 统一 trade_date 列为 Timestamp 类型
        dataFrame['trade_date'] = pd.to_datetime(dataFrame['trade_date'])

        return dataFrame


    def analyz_stock_only(self):
        params_list = [
            # {
            #     'market': "CN",
            #     'stock': '000001.SH',
            #     'filter_key_column':'trade_date',
            #     'start_date': '20240901',
            #     'end_date': '20241231',
            #     'next_n_days':10,
            #     'span': 30,
            #     'analysis_column': 'close',
            #     'remark': '分析上证综指的收盘价'
            # },
            # {
            #     'market': "CN",
            #     'stock': '603839.SH',
            #     'filter_key_column':'trade_date',
            #     'start_date': '20240901',
            #     'end_date': '20241231',
            #     'next_n_days':10,
            #     'span': 30,
            #     'analysis_column': 'close',
            #     'remark': '分析安正时尚(603839.SH)的收盘价'
            # },
            # {
            #     'market': "CN",
            #     'stock': '603839.SH',
            #     'filter_key_column': 'trade_date',
            #     'start_date': '20240901',
            #     'end_date': '20241231',
            #     'next_n_days': 10,
            #     'span': 30,
            #     'analysis_column': 'pct_chg',
            #     'remark': '分析安正时尚(603839.SH)的波动率'
            # },
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
            {
                'market': "US",
                'stock': 'C',
                'filter_key_column': 'trade_date',
                'start_date': '20250101',
                'end_date': '20260205',
                'next_n_days': 10,
                'span': 30,
                'analysis_column': 'close',
                'remark': '分析花旗的收盘价'
            }
        ]
        # ##################################
        # # 直接单条分析
        # ##################################
        for params in params_list:
            ewmaAnalystTest = EWMAAnalystTest()
            dataFrame = ewmaAnalystTest.load_data(params)
            params["dataFrame"] = dataFrame

            ewmaAnalyst = EWMAAnalyst()
            ewmaAnalyst.analyze_workflow(params)

    def analyz_with_sql_sge(self):

        sql = """select date, close, pct_change 
                from indexsysdb.df_akshare_spot_hist_sge
                WHERE df_akshare_spot_hist_sge.date > '2024-12-02'"""
        dataFrame = InquiryManager().get_sql_dataset(sql)
        dataFrame['date'] = pd.to_datetime(dataFrame['date'])

        params = {'market': "SGE", 'stock': 'gold', 'filter_key_column': 'date', 'start_date': '20250101',
                  'end_date': '20260208', 'next_n_days': 10, 'span': 30, 'analysis_column': 'close',
                  'remark': '分析黄金走势', "dataFrame": dataFrame}

        ewmaAnalyst = EWMAAnalyst()
        ewmaAnalyst.analyze_workflow(params)

    def analyz_with_sql_shibor(self):

        sql = """
                select * from 
                df_tushare_shibor_daily
                where trade_date >= '20250101'
        """
        dataFrame = InquiryManager().get_sql_dataset(sql)
        dataFrame['trade_date'] = pd.to_datetime(dataFrame['trade_date'])

        params = {'market': "CN", 'stock': 'shibor',
                  'filter_key_column': 'trade_date',
                  'start_date': '20250101',
                  'end_date': '20260208',
                  'next_n_days': 10, 'span': 30,
                  'analysis_column': 'tenor_on',
                  'remark': '分析shibor走势',
                  "dataFrame": dataFrame}

        ewmaAnalyst = EWMAAnalyst()
        ewmaAnalyst.analyze_workflow(params)

if __name__ == "__main__":
    ewmaAnalystTest = EWMAAnalystTest()
    #ewmaAnalystTest.analyz_stock_only()

    #ewmaAnalystTest.analyz_with_sql_sge()
    ewmaAnalystTest.analyz_with_sql_shibor()

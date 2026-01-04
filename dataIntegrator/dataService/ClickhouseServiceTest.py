from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.TuShareService.TuShareService import TuShareService
from clickhouse_driver import Client as ClickhouseClient
import sys
import pandas as pd

from dataIntegrator.dataService.ClickhouseService import ClickhouseService

logger = CommonLib.logger
commonLib = CommonLib()


class ClickhouseServiceTest:
    def init(cls):
        pass

    def test_join_query(self):
        """测试复杂的多表连接查询"""
        queryStatement = """select cn_money_supply.m1  as ml
                                from indexsysdb.df_sys_calendar calendar
                                left join df_tushare_shibor_daily shibor_daily
                                on calendar.trade_date  = shibor_daily.trade_date
                                left join indexsysdb.cn_money_supply cn_money_supply
                                on SUBSTRING(calendar.trade_date,1,6) = cn_money_supply.trade_date
                                left join indexsysdb.df_tushare_cn_gdp cn_gdp
                                on calendar.trade_year || 'Q' || calendar.quarter    = cn_gdp.quarter
                                where CAST(calendar.trade_year AS BIGINT)  >= '2018'
                                order by calendar.trade_date"""
        columns = ['ml']
        clickhouseService = ClickhouseService()
        result = clickhouseService.getDataFrame(queryStatement, columns)
        print(result)
        return result

    def test_average_return_query(self):
        """测试平均收益率查询"""
        queryStatement = """SELECT AVG(pct_change) AS average_return
        FROM indexsysdb.df_tushare_us_stock_daily
        WHERE ts_code = 'C' AND
        trade_date >= '20241215' AND
        trade_date <= '20241216'"""
        clickhouseService = ClickhouseService()
        result = clickhouseService.getDataFrameWithoutColumnsName(queryStatement)
        print(result)
        return result

    def test_create_table(self):
        """测试创建表功能"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS test_table (
            id UInt32,
            name String
        ) ENGINE = Memory
        """
        clickhouseService = ClickhouseService()
        clickhouseService.execute_sql(create_table_sql)
        return "Table creation completed"

    def test_drop_table(self):
        """测试删除表功能"""
        clickhouseService = ClickhouseService()
        drop_table_sql = "DROP TABLE IF EXISTS test_table"
        clickhouseService.execute_sql(drop_table_sql)
        return "Table deletion completed"

    def test_save_a_dataframe_to_clickhouse(self):
        """测试保存 DataFrame 到 ClickHouse 功能"""
        df = pd.DataFrame({
            'date': ['2024-01-01', '2024-01-02'],
            'value': [100, 200],
            'name': ['A', 'B']
        })

        # 保存到 ClickHouse
        clickhouse_service = ClickhouseService()
        result = clickhouse_service.save_dataframe_to_clickhouse(df, 'test_my_table')
        print(f"DataFrame saved successfully: {result}")
        return result

    '''
    保存任意的dataframe进 clickhouse 供快速分析
    '''
    def test_save_akshare_forex_spot_em_to_clickhouse(self):
        import akshare as ak

        df = ak.forex_spot_em()
        print(df)
        df.columns = ['sequence', 'code', 'name', 'price', 'increase_value', 'increase_percent', 'today_open', 'today_high', 'today_low', 'last_close']

        # 保存到 ClickHouse
        clickhouse_service = ClickhouseService()
        result = clickhouse_service.save_dataframe_to_clickhouse(df, 'test_akshare_forex_spot_em')
        print(f"DataFrame saved successfully: {result}")
        return result

if __name__ == "__main__":
    clickhouseServiceTest = ClickhouseServiceTest()

    #执行各个测试
    clickhouseServiceTest.test_join_query()
    clickhouseServiceTest.test_average_return_query()
    clickhouseServiceTest.test_create_table()
    clickhouseServiceTest.test_drop_table()

    clickhouseServiceTest.test_save_dataframe_to_clickhouse()
    clickhouseServiceTest.test_save_akshare_forex_spot_em_to_clickhouse()
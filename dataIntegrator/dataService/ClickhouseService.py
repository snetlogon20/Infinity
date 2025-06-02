from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.TuShareService.TuShareService import TuShareService
from clickhouse_driver import Client as ClickhouseClient
import sys
import pandas as pd

logger = CommonLib.logger
commonLib = CommonLib()

#class ClickhouseService(TuShareService):
class ClickhouseService:

    clickhouseClient = ClickhouseClient(
        host=CommonParameters.clickhouseHostName,
        database=CommonParameters.clickhouseHostDatabase)
    @classmethod
    def getDataFrame(self, sql, columns):
        logger.info("prepareData started")
        try:
            result = self.clickhouseClient.execute(sql)
            dataframe = pd.DataFrame(result)
            dataframe.columns  = columns

        except Exception as e:
            raise commonLib.raise_custom_error(error_code="000101", custom_error_message=rf"getDataFrame execute sql error, sql: {sql}", e=e)

        logger.info("execute_query completed")

        return dataframe

    @classmethod
    def getDataFrameWithoutColumnsName(self, sql):
        logger.info(rf"prepareData started - sql: {sql}")
        try:
            #self.clickhouseClient.execute('USE indexsysdb')
            cursor = self.clickhouseClient.execute_iter(sql, with_column_types=True)
            columns = [col[0] for col in next(cursor)]
            result = list(cursor)
            # 创建 DataFrame 并指定列名
            dataframe = pd.DataFrame(result, columns=columns)

        except Exception as e:
            raise commonLib.raise_custom_error(error_code="000101",custom_error_message=rf"getDataFrameWithoutColumnsName execute sql error, sql: {sql}", e=e)

        logger.info("execute_query completed")

        return dataframe


    @classmethod
    def execute_sql(self, sql):
        logger.info(rf"Executing SQL statement: {sql}")
        try:
            self.clickhouseClient.execute(sql)
        except Exception as e:
            raise commonLib.raise_custom_error(
                error_code="000102",
                custom_error_message=rf"execute_sql failed, SQL: {sql}",
                e=e
            )
        logger.info("SQL execution completed")

if __name__ == "__main__":
    # Example DataFrames
    # queryStatement = """select cn_money_supply.m1  as ml
    #                         from indexsysdb.df_sys_calendar calendar
    #                         left join df_tushare_shibor_daily shibor_daily
    #                         on calendar.trade_date  = shibor_daily.trade_date
    #                         left join indexsysdb.cn_money_supply cn_money_supply
    #                         on SUBSTRING(calendar.trade_date,1,6) = cn_money_supply.trade_date
    #                         left join indexsysdb.df_tushare_cn_gdp cn_gdp
    #                         on calendar.trade_year || 'Q' || calendar.quarter    = cn_gdp.quarter
    #                         where CAST(calendar.trade_year AS BIGINT)  >= '2018'
    #                         order by calendar.trade_date"""
    # columns = ['ml']
    # clickhouseService = ClickhouseService()
    # result = clickhouseService.getDataFrame(queryStatement, columns)
    # print(result)


    queryStatement = """SELECT AVG(pct_change) AS average_return
    FROM indexsysdb.df_tushare_us_stock_daily
    WHERE ts_code = 'C' AND
    trade_date >= '20241215' AND
    trade_date <= '20241216'"""
    clickhouseService = ClickhouseService()
    result = clickhouseService.getDataFrameWithoutColumnsName(queryStatement)
    print(result)

    # create_table_sql = """
    # CREATE TABLE IF NOT EXISTS test_table (
    #     id UInt32,
    #     name String
    # ) ENGINE = Memory
    # """
    # clickhouseService = ClickhouseService()
    # clickhouseService.execute_sql(create_table_sql)

    # # 示例：删除表
    # clickhouseService = ClickhouseService()
    # drop_table_sql = "DROP TABLE IF EXISTS test_table"
    # clickhouseService.execute_sql(drop_table_sql)
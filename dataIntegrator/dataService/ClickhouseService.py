from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
import pandas as pd


class ClickhouseService(TuShareService):
    @classmethod
    def getDataFrame(self, sql, columns):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="prepareData started")
        try:
            result = self.clickhouseClient.execute(sql)
            dataframe = pd.DataFrame(result)
            dataframe.columns  = columns

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="execute_query completed")

        return dataframe

    @classmethod
    def getDataFrameWithoutColumnsName(self, sql):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="prepareData started")
        try:
            cursor = self.clickhouseClient.execute_iter(sql, with_column_types=True)
            columns = [col[0] for col in next(cursor)]
            result = list(cursor)
            # 创建 DataFrame 并指定列名
            dataframe = pd.DataFrame(result, columns=columns)

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="execute_query completed")

        return dataframe

if __name__ == "__main__":
    # Example DataFrames
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



    queryStatement = """SELECT AVG(pct_change) AS average_return 
    FROM indexsysdb.df_tushare_us_stock_daily 
    WHERE ts_code = 'C' AND 
    trade_date >= '20241215' AND 
    trade_date <= '20241216'"""
    clickhouseService = ClickhouseService()
    result = clickhouseService.getDataFrameWithoutColumnsName(queryStatement)
    print(result)

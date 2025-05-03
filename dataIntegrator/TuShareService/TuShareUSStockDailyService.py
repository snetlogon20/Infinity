from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib

logger = CommonLib.logger

class TuShareUSStockDailyService(TuShareService):
    @classmethod
    def prepareDataFrame(self, ts_code, start_date, end_date):
        logger.info("prepareData started")

        try:
            self.dataFrame = self.pro.us_daily(ts_code, start_date=start_date, end_date=end_date) #to check whether ts_code work here
            self.dataFrame.columns = ['ts_code',
                             'trade_date',
                             'close_point',
                             'open_point',
                             'high_point',
                             'low_point',
                             'pre_close',
                             'pct_change',
                             'vol',
                             'amount',
                             'vwap']

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")

        return self.dataFrame

    @classmethod
    def saveDateToClickHouse(self):
        logger.info("saveDateToClickHouse started")

        try:
            insert_df_tushare_stock_daily = 'insert into indexsysdb.df_tushare_us_stock_daily (ts_code,trade_date,close_point,open_point,high_point,low_point,pre_close,pct_change,vol,amount,vwap) VALUES'
            dataValues = self.dataFrame.to_dict('records')
            self.clickhouseClient.execute(insert_df_tushare_stock_daily, dataValues)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed")

    @classmethod
    def deleteDateFromClickHouse(self, ts_code="", start_date="00000000", end_date="00000000"):
        logger.info("deleteDataFromClickHouse started")

        try:
            #del_df_tushare_sql = "ALTER TABLE indexsysdb.df_tushare_us_stock_daily DELETE where ts_code = '%s' and trade_date>= '%s' and trade_date<='%s'" % (ts_code, start_date, end_date)
            del_df_tushare_sql = "ALTER TABLE indexsysdb.df_tushare_us_stock_daily DELETE where trade_date>= '%s' and trade_date<='%s'" % (start_date, end_date)
            self.clickhouseClient.execute(del_df_tushare_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        def deleteDateFromClickHouse(self):
            logger.info("deleteDateFromClickHouse completed")

    # @classmethod
    # def convertDataFrame2JSON(self):
    #     print("prepareData started")
    #
    #     try:
    #         self.jsonString = self.dataFrame.to_json(orient='table')
    #     except Exception as e:
    #         print('Exception', e)
    #         raise e
    #
    #     print("prepareData ended")
    #
    #     return self.jsonString

    # @classmethod
    # def saveDateFrameToDisk(self, fileName, sep='\u0001',mode="w", header="true"):
    #     print("saveDateToDisk started")
    #
    #     try:
    #         self.dataFrame.to_csv(
    #             fileName,
    #             sep=sep,
    #             mode=mode,
    #             header=header)
    #     except Exception as e:
    #         print(e.message)
    #         raise e
    #
    #     print("saveDateToDisk completed")
    #
    #     return
from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib

logger = CommonLib.logger

class TuShareFutureDailyService(TuShareService):
    @classmethod
    def prepareDataFrame(self, ts_code, start_date, end_date):
        logger.info("prepareData started")

        try:
            self.dataFrame = self.pro.fut_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            logger.info("self.dataFrame.shape:" + str(self.dataFrame.shape))
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")

        return self.dataFrame

    @classmethod
    def saveDateToClickHouse(self):
        logger.info("saveDateToClickHouse started")

        try:
            insert_df_sql = 'insert into indexsysdb.df_tushare_future_daily (ts_code,trade_date,pre_close,pre_settle,open,high,low,close,settle,change1,change2,vol,amount,oi,oi_chg) VALUES'
            dataValues = self.dataFrame.to_dict('records')
            self.clickhouseClient.execute(insert_df_sql, dataValues)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed")

    @classmethod
    def deleteDateFromClickHouse(self, ts_code="", start_date="00000000", end_date="00000000"):
        logger.info("deleteDataFromClickHouse started")

        try:
            del_df_tushare_sql = "ALTER TABLE indexsysdb.df_tushare_future_daily DELETE where ts_code = '%s' and trade_date>= '%s' and trade_date<='%s'" % (ts_code, start_date, end_date)
            self.clickhouseClient.execute(del_df_tushare_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

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
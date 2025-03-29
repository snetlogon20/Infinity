from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys


class TushareShiborLPRDailyService(TuShareService):
    @classmethod
    def prepareDataFrame(self, start_date, end_date):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name, event="prepareData started")

        try:
            self.dataFrame = self.pro.shibor_lpr(start_date=start_date, end_date=end_date)
            self.dataFrame.columns = ["trade_date","tenor_1y","tenor_5y"]

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name, event="prepareData started")

        return self.dataFrame

    @classmethod
    def saveDateToClickHouse(self):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="saveDateToClickHouse started")

        try:
            insert_sql_statement = 'insert into indexsysdb.df_tushare_shibor_lpr_daily (trade_date,tenor_1y, tenor_5y) VALUES'
            data = self.dataFrame.to_dict('records')
            self.clickhouseClient.execute(insert_sql_statement, data)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="saveDateToClickHouse completed")

    @classmethod
    def deleteDateFromClickHouse(self, start_date, end_date):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="deleteDataFromClickHouse started")

        try:
            del_df_tushare_sql = "ALTER TABLE indexsysdb.df_tushare_shibor_lpr_daily DELETE where trade_date>= '%s' and trade_date<='%s'" % (start_date, end_date)

            self.clickhouseClient.execute(del_df_tushare_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="deleteDateFromClickHouse completed")

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
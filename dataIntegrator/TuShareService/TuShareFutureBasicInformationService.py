from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys


class TuShareFutureBasicInformationService(TuShareService):
    @classmethod
    def prepareDataFrame(self, exchange, fut_type, fields):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="prepareData started")

        try:
            self.dataFrame = self.pro.fut_basic(exchange=exchange, fut_type=fut_type, fields=fields)

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="prepareData completed")

        return self.dataFrame

    @classmethod
    def saveDateToClickHouse(self):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="saveDateToClickHouse started")

        try:
            insert_df_tushare_stock_daily = 'insert into indexsysdb.df_tushare_future_basic_information (ts_code,symbol,name,quote_unit,list_date,delist_date) VALUES'
            dataValues = self.dataFrame.to_dict('records')
            self.clickhouseClient.execute(insert_df_tushare_stock_daily, dataValues)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="saveDateToClickHouse completed")

    @classmethod
    def deleteDateFromClickHouse(self):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="deleteDataFromClickHouse started")

        try:
            del_df_tushare_sql = "truncate table indexsysdb.df_tushare_future_basic_information"
            self.clickhouseClient.execute(del_df_tushare_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        def deleteDateFromClickHouse(self):
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
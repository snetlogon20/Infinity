import pandas
from clickhouse_driver import Client as ClickhouseClient
import tushare as ts
from pandas import DataFrame
from dataIntegrator.common.CommonParameters import CommonParameters
from dataIntegrator import CommonLib

logger = CommonLib.logger

#class TuShareService(CommonLib.CommonLib):
class TuShareService(CommonLib):


    dataFrame = pandas.core.frame.DataFrame
    jsonString = ""
    token = CommonParameters.tuShareToken
    clickhouseClient = ClickhouseClient(host=CommonParameters.clickhouseHostName,database=CommonParameters.clickhouseHostDatabase)
    ts.set_token(token)
    pro = ts.pro_api()


    # def __init__(self, CommonLib):
    #     logger.info("__init__ started")
    #
    #     self.token = self.getToken()
    #     ts.set_token(self.token)
    #     self.pro = ts.pro_api()
    #
    #     print("__init__ completed")

    def __init__(self):
        logger.info("__init__ started")

        self.token = self.getToken()
        ts.set_token(self.token)
        self.pro = ts.pro_api()

        #print("__init__ completed")

    @classmethod
    def getToken(self):
        # print("getToken started")
        #
        # print("getToken completed")

        return self.token

    @classmethod
    def prepareDataFrame(self, ts_code, start_date, end_date):
        logger.info("prepareData started")

    @classmethod
    def convertDataFrame2JSON(self, orient='table'):
        logger.info("prepareData started")

        try:
            self.jsonString = self.dataFrame.to_json(orient)
        except Exception as e:
            print('Exception', e)
            raise e

        logger.info("prepareData ended")

        return self.jsonString


    @classmethod
    def saveDateFrameToDisk(self, fileName, sep='\u0001',mode="w", header="true"):
        logger.info("saveDateToDisk started")

        try:
            self.dataFrame.to_csv(
                fileName,
                sep=sep,
                mode=mode,
                header=header)

            DataFrame(self.dataFrame.to_dict("records")).to_excel(fileName+'.xlsx', sheet_name='Sheet1')

        except Exception as e:
            print(e.message)
            raise e

        logger.info("saveDateToDisk completed")

        return

    @classmethod
    def deleteDateFromClickHouse(self, start_date="0000000", end_date="0000000"):
        logger.info("saveDateToDisk started")

    @classmethod
    def saveDateToClickHouse(self):
        logger.info("saveDateToClickHouse started...")
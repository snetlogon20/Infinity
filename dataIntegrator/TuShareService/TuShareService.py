import pandas
from clickhouse_driver import Client as ClickhouseClient
import tushare as ts
from pandas import DataFrame
from dataIntegrator.common import CommonLib
from dataIntegrator.common.CommonParameters import CommonParameters
import sys

class TuShareService(CommonLib.CommonLib):
    dataFrame = pandas.core.frame.DataFrame
    jsonString = ""
    token = CommonParameters.tuShareToken
    clickhouseClient = ClickhouseClient(host=CommonParameters.clickhouseHostName,
                                        database=CommonParameters.clickhouseHostDatabase)
    #ts.set_token(token)
    pro = ts.pro_api()
    #pro._DataApi__http_url = 'http://tsapi.majors.ltd:7000'  #From Xianyu


    def __init__(self, CommonLib):
        self.writeLogInfo("__init__ started")

        self.token = self.getToken()
        ts.set_token(self.token)
        self.pro = ts.pro_api()

        print("__init__ completed")

    def __init__(self):
        print("__init__ started")

        self.token = self.getToken()
        ts.set_token(self.token)
        self.pro = ts.pro_api()

        print("__init__ completed")

    @classmethod
    def getToken(self):
        print("getToken started")

        print("getToken completed")

        return self.token

    @classmethod
    def prepareDataFrame(self, ts_code, start_date, end_date):
        print("prepareData started")

        print("prepareData completed")

    @classmethod
    def convertDataFrame2JSON(self, orient='table'):
        print("prepareData started")

        try:
            self.jsonString = self.dataFrame.to_json(orient)
        except Exception as e:
            print('Exception', e)
            raise e

        print("prepareData ended")

        return self.jsonString


    @classmethod
    def saveDateFrameToDisk(self, fileName, sep='\u0001',mode="w", header="true"):
        print("saveDateToDisk started")

        try:
            self.dataFrame.to_csv(
                fileName,
                sep=sep,
                mode=mode,
                header=header)

            DataFrame(self.dataFrame.to_dict("records")).\
                to_excel(fileName+'.xlsx', sheet_name='Sheet1')

        except Exception as e:
            print(e.message)
            raise e

        print("saveDateToDisk completed")

        return

    @classmethod
    def deleteDateFromClickHouse(self, start_date="0000000", end_date="0000000"):
        print("saveDateToDisk started")

        print("prepareData completed")

    @classmethod
    def saveDateToClickHouse(self):
        print("saveDateToClickHouse started...")

        print("saveDateToClickHouse completed")

    # @classmethod
    # def writeLogInfo(self, className ="unknown", functionName="unknown", event="unknown"):
    #     print("%s.%s: %s" % (className, functionName, event))
    #
    # @classmethod
    # def writeLogError(self, e, className ="unknown", functionName="unknown"):
    #     print('==============================================')
    #     print("%s.%s:" % (className, functionName))
    #     print('Exception: ', e)
    #     info = traceback.format_exc()
    #     print(info)
    #     print('==============================================')
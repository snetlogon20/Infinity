import pandas
from clickhouse_driver import Client as ClickhouseClient
import akshare as ak
import sys
from dataIntegrator.common.CommonParameters import CommonParameters
from dataIntegrator import CommonLib
from dataIntegrator.common.FileType import FileType

logger = CommonLib.logger

class AkShareService(CommonLib):
    jsonString = ""
    clickhouseClient = ClickhouseClient(host=CommonParameters.clickhouseHostName,database=CommonParameters.clickhouseHostDatabase)


    def __init__(self):
        logger.info("__init__ started")

        self.ak = ak


    @classmethod
    def prepareDataFrame(self, ts_code, start_date, end_date):
        logger.info("prepareData started")

    @classmethod
    def convertDataFrame2JSON(self, dataFrame: pandas.core.frame.DataFrame, orient='table'):
        logger.info("prepareData started")

        try:
            self.jsonString = dataFrame.to_json(orient)
        except Exception as e:
            print('Exception', e.message)
            raise e

        logger.info("prepareData ended")

        return self.jsonString


    @classmethod
    def saveDateFrameToDisk(cls, dataFrame: pandas.core.frame.DataFrame, fileName, fileType: FileType, sep='\u0001',mode="w", header="true"):
        logger.info("saveDateToDisk started")

        try:
            if fileType == FileType.CSV:
                dataFrame.to_csv(
                    fileName,
                    sep=sep,
                    mode=mode,
                    header=header,
                    index=False
                )
            elif fileType == FileType.EXCEL:
                dataFrame.to_excel(fileName, sheet_name='Sheet1', index=False)
            else:
                raise ValueError(f"Unsupported file type: {fileType}")

        except AttributeError as ae:
            # 处理 e.message 不存在的情况
            print(f'AttributeError: {ae}')
            logger.error(f'AttributeError in saveDateFrameToDisk: {ae}')
            raise
        except Exception as e:
            # 使用 str(e) 获取完整的错误信息
            error_msg = str(e)
            logger.error(f'Exception: {error_msg}')
            raise

        logger.info("saveDateToDisk completed")
        return

    @classmethod
    def readDataFrameFromDisk(self,  fileName, fileType: FileType, sep='\u0001'):
        logger.info("readDataFrameFromDisk started")

        try:
            if fileType == FileType.CSV:
                dataFrame = pandas.read_csv(fileName, sep=sep)
            elif fileType == FileType.EXCEL:
                dataFrame = pandas.read_excel(fileName)
            else:
                raise ValueError(f"Unsupported file type: {fileType}")

        except Exception as e:
            print(e.message)
            raise e

        logger.info("readDataFrameFromDisk completed")

        return dataFrame

    @classmethod
    def deleteAkDateFromClickHouse(self, del_sql: str):
        logger.info("deleteAkDateFromClickHouse started")

        try:
            self.clickhouseClient.execute(del_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e
        logger.info("deleteAkDateFromClickHouse completed")

        return

    @classmethod
    def saveAkDateToClickHouse(self,insert_sql_statement, dataframe: pandas.core.frame.DataFrame):
        logger.info("saveDataToClickHouse started")

        try:
            data = dataframe.to_dict('records')
            self.clickhouseClient.execute(insert_sql_statement, data)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e
        logger.info("saveDataToClickHouse completed")

        return
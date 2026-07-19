import pandas

from dataIntegrator import CommonLib
from dataIntegrator.AKShareService.AkShareService import AkShareService
import sys

logger = CommonLib.logger

class AkShareMacroUsaUnemploymentRateService(AkShareService):

    #@classmethod
    def prepareDataFrame(self, start_date=None, end_date=None):
        logger.info("prepareData started")

        try:
            # 调用 AKShare API 获取美国失业率月度数据
            # 源自金十数据等，返回 1970 年至今的历史数据
            dataFrame = self.ak.macro_usa_unemployment_rate()

            # 重命名列以匹配数据库字段
            dataFrame = dataFrame.rename(columns={'日期': 'date', '今值': 'value'})
            dataFrame = dataFrame[['date', 'value']]

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")
        return dataFrame

    @classmethod
    def transformDataFrame(self, dataFrame: pandas.core.frame.DataFrame):
        logger.info("transformData started")

        try:
            # 数据预处理：转换日期列为字符串
            if 'date' in dataFrame.columns:
                dataFrame['date'] = dataFrame['date'].astype(str)

            # 按日期排序确保数据有序
            dataFrame = dataFrame.sort_values('date').reset_index(drop=True)

            # 确保 value 列为数值类型
            if 'value' in dataFrame.columns:
                dataFrame['value'] = pandas.to_numeric(dataFrame['value'], errors='coerce')

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("transformData completed")
        return dataFrame

    @classmethod
    def saveDateToClickHouse(self, dataFrame):
        logger.info("saveDateToClickHouse started")

        try:
            insert_sql = "INSERT INTO indexsysdb.df_macro_usa_unemployment_rate VALUES"
            self.saveAkDateToClickHouse(insert_sql, dataFrame)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed: %s", insert_sql)

        return

    @classmethod
    def deleteDateFromClickHouse(self, start_date="0000000", end_date="0000000"):
        logger.info("deleteDataFromClickHouse started")

        try:
            del_sql = "ALTER TABLE indexsysdb.df_macro_usa_unemployment_rate DELETE where date>= '%s' and date<='%s'" % (start_date, end_date)
            self.deleteAkDateFromClickHouse(del_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDataFromClickHouse completed: %s", del_sql)

        return

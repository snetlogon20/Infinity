# D:\workspace_python\infinity\dataIntegrator\AKShareService\AkShareMacroChinaExportsYoyService.py
import pandas

from dataIntegrator import CommonLib
from dataIntegrator.AKShareService.AkShareService import AkShareService
import sys

logger = CommonLib.logger

class AkShareMacroChinaExportsYoyService(AkShareService):

    #@classmethod
    def prepareDataFrame(self, start_date=None, end_date=None):  # 移除 @classmethod 装饰器
        logger.info("prepareData started")

        try:
            # 调用 AKShare API 获取中国以美元计算出口年率报告
            dataFrame = self.ak.macro_china_exports_yoy()

            # 重命名列以匹配数据库字段
            dataFrame.columns = [
                'item',
                'date',
                'current_value',
                'forecast_value',
                'previous_value'
            ]

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

            # 填充 NaN 值为 0（预测值可能为空）
            numeric_columns = [
                'current_value',
                'forecast_value',
                'previous_value'
            ]

            for col in numeric_columns:
                if col in dataFrame.columns:
                    dataFrame[col] = dataFrame[col].fillna(0)

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("transformData completed")
        return dataFrame

    @classmethod
    def saveDateToClickHouse(self, dataFrame):
        logger.info("saveDateToClickHouse started")

        try:
            insert_sql = "INSERT INTO indexsysdb.df_macro_china_exports_yoy VALUES"
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
            del_sql = "ALTER TABLE indexsysdb.df_macro_china_exports_yoy DELETE where date>= '%s' and date<='%s'" % (start_date, end_date)
            self.deleteAkDateFromClickHouse(del_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDataFromClickHouse completed: %s", del_sql)

        return

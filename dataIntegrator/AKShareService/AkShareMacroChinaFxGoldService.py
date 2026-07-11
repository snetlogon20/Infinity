# D:\workspace_python\infinity\dataIntegrator\AKShareService\AkShareMacroChinaFxGoldService.py
import pandas

from dataIntegrator import CommonLib
from dataIntegrator.AKShareService.AkShareService import AkShareService
import sys

logger = CommonLib.logger

class AkShareMacroChinaFxGoldService(AkShareService):

    #@classmethod
    def prepareDataFrame(self, start_date=None, end_date=None):  # 移除 @classmethod 装饰器
        logger.info("prepareData started")

        try:
            # 调用 AKShare API 获取外汇和黄金储备数据
            dataFrame = self.ak.macro_china_fx_gold()

            # 重命名列以匹配数据库字段
            dataFrame.columns = [
                'month',
                'gold_reserves_value',
                'gold_reserves_yoy',
                'gold_reserves_mom',
                'forex_reserves_value',
                'forex_reserves_yoy',
                'forex_reserves_mom'
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
            # 数据预处理：转换月份列格式 "2008年01月份" → "200801"
            if 'month' in dataFrame.columns:
                dataFrame['month'] = dataFrame['month'].astype(str)
                dataFrame['month'] = dataFrame['month'].str.replace('年', '', regex=False).str.replace('月份', '', regex=False)
                # 确保月份为两位数（兼容 "2008年1月份" → "20081" → "200801"）
                dataFrame['month'] = dataFrame['month'].apply(
                    lambda x: x[:4] + x[4:].zfill(2) if len(x) == 5 else x
                )

            # 按月份排序确保数据有序
            dataFrame = dataFrame.sort_values('month').reset_index(drop=True)

            # 填充 NaN 值为 0（外汇和黄金储备某些月份可能为空）
            numeric_columns = [
                'gold_reserves_value',
                'gold_reserves_yoy',
                'gold_reserves_mom',
                'forex_reserves_value',
                'forex_reserves_yoy',
                'forex_reserves_mom'
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
            insert_sql = "INSERT INTO indexsysdb.df_macro_china_fx_gold VALUES"
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
            del_sql = "ALTER TABLE indexsysdb.df_macro_china_fx_gold DELETE where month>= '%s' and month<='%s'" % (start_date, end_date)
            self.deleteAkDateFromClickHouse(del_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDataFromClickHouse completed: %s", del_sql)

        return

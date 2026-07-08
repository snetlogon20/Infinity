# D:\workspace_python\infinity\dataIntegrator\AKShareService\AkShareMacroChinaShrzgmService.py
import pandas

from dataIntegrator import CommonLib
from dataIntegrator.AKShareService.AkShareService import AkShareService
import sys

logger = CommonLib.logger

class AkShareMacroChinaShrzgmService(AkShareService):

    #@classmethod
    def prepareDataFrame(self, start_date=None, end_date=None):  # 移除 @classmethod 装饰器
        logger.info("prepareData started")

        try:
            # 调用 AKShare API 获取社会融资规模增量数据
            dataFrame = self.ak.macro_china_shrzgm()

            # 重命名列以匹配数据库字段
            dataFrame.columns = [
                'month',
                'total_shrzgm',
                'rmb_loan',
                'entrusted_loan_foreign_currency_loan',
                'entrusted_loan',
                'trust_loan',
                'undiscounted_bank_acceptance_bills',
                'corporate_bonds',
                'non_financial_enterprise_domestic_equity_financing'
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
            # 数据预处理：转换月份列为字符串
            if 'month' in dataFrame.columns:
                dataFrame['month'] = dataFrame['month'].astype(str)

            # 按月份排序确保数据有序
            dataFrame = dataFrame.sort_values('month').reset_index(drop=True)

            # 填充 NaN 值为 0（社会融资规模某些月份可能为空）
            numeric_columns = [
                'total_shrzgm',
                'rmb_loan',
                'entrusted_loan_foreign_currency_loan',
                'entrusted_loan',
                'trust_loan',
                'undiscounted_bank_acceptance_bills',
                'corporate_bonds',
                'non_financial_enterprise_domestic_equity_financing'
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
            insert_sql = "INSERT INTO indexsysdb.df_macro_china_shrzgm VALUES"
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
            del_sql = "ALTER TABLE indexsysdb.df_macro_china_shrzgm DELETE where month>= '%s' and month<='%s'" % (start_date, end_date)
            self.deleteAkDateFromClickHouse(del_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDataFromClickHouse completed: %s", del_sql)

        return

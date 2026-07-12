# D:\workspace_python\infinity\dataIntegrator\AKShareService\AkShareBondZhUsRateService.py
import pandas

from dataIntegrator import CommonLib
from dataIntegrator.AKShareService.AkShareService import AkShareService
import sys

logger = CommonLib.logger

class AkShareBondZhUsRateService(AkShareService):

    def prepareDataFrame(self, start_date="19901219"):
        logger.info("prepareData started")

        try:
            # 调用 AKShare API 获取中美国债收益率历史数据
            dataFrame = self.ak.bond_zh_us_rate(start_date=start_date)

            # 重命名列以匹配数据库字段
            dataFrame.columns = [
                'trade_date',
                'cn_yield_2y',
                'cn_yield_5y',
                'cn_yield_10y',
                'cn_yield_30y',
                'cn_yield_spread_10y2y',
                'cn_gdp_yoy',
                'us_yield_2y',
                'us_yield_5y',
                'us_yield_10y',
                'us_yield_30y',
                'us_yield_spread_10y2y',
                'us_gdp_yoy'
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
            # 数据预处理：转换日期列为 YYYYMMDD 字符串格式
            if 'trade_date' in dataFrame.columns:
                dataFrame['trade_date'] = pandas.to_datetime(dataFrame['trade_date']).dt.strftime('%Y%m%d')

            # 按日期排序确保数据有序
            dataFrame = dataFrame.sort_values('trade_date').reset_index(drop=True)

            # 填充 NaN 值（收益率数据某些早期日期可能为空）
            numeric_columns = [
                'cn_yield_2y', 'cn_yield_5y', 'cn_yield_10y', 'cn_yield_30y',
                'cn_yield_spread_10y2y', 'cn_gdp_yoy',
                'us_yield_2y', 'us_yield_5y', 'us_yield_10y', 'us_yield_30y',
                'us_yield_spread_10y2y', 'us_gdp_yoy'
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
            insert_sql = "INSERT INTO indexsysdb.df_akshare_bond_zh_us_rate VALUES"
            self.saveAkDateToClickHouse(insert_sql, dataFrame)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed: %s", insert_sql)

        return

    @classmethod
    def deleteDateFromClickHouse(self, start_date="00000000", end_date="99999999"):
        logger.info("deleteDataFromClickHouse started")

        try:
            del_sql = "ALTER TABLE indexsysdb.df_akshare_bond_zh_us_rate DELETE where trade_date >= '%s' and trade_date <= '%s'" % (start_date, end_date)
            self.deleteAkDateFromClickHouse(del_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDataFromClickHouse completed: %s", del_sql)

        return

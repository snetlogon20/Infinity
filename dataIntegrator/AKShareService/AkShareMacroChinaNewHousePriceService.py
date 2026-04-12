import pandas

from dataIntegrator import CommonLib
from dataIntegrator.AKShareService.AkShareService import AkShareService
import sys

logger = CommonLib.logger

class AkShareMacroChinaNewHousePriceService(AkShareService):

    #@classmethod
    def prepareDataFrame(self, city_first="北京", city_second="上海"):
        logger.info("prepareData started")

        try:
            # 调用 AKShare API 获取中国新建商品住宅价格指数数据
            dataFrame = self.ak.macro_china_new_house_price(city_first=city_first, city_second=city_second)

            # 重命名列以匹配数据库字段
            dataFrame.columns = [
                'date',
                'city',
                'new_home_price_index_yoy',
                'new_home_price_index_mom',
                'new_home_price_index_fixed_base',
                'second_hand_home_price_index_yoy',
                'second_hand_home_price_index_mom',
                'second_hand_home_price_index_fixed_base'
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

            # 按日期和城市排序确保数据有序
            dataFrame = dataFrame.sort_values(['date', 'city']).reset_index(drop=True)

            # 填充 NaN 值为 0（价格指数某些月份可能为空）
            numeric_columns = [
                'new_home_price_index_yoy',
                'new_home_price_index_mom',
                'new_home_price_index_fixed_base',
                'second_hand_home_price_index_yoy',
                'second_hand_home_price_index_mom',
                'second_hand_home_price_index_fixed_base'
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
            insert_sql = "INSERT INTO indexsysdb.df_macro_china_new_house_price VALUES"
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
            #del_sql = "ALTER TABLE indexsysdb.df_macro_china_new_house_price DELETE where date>= '%s' and date<='%s'" % (start_date, end_date)
            del_sql = "ALTER TABLE indexsysdb.df_macro_china_new_house_price DELETE where 1=1"
            self.deleteAkDateFromClickHouse(del_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDataFromClickHouse completed: %s", del_sql)

        return

import pandas

from dataIntegrator import CommonLib
from dataIntegrator.AKShareService.AkShareService import AkShareService
import sys
logger = CommonLib.logger

class AkShareFuturesForeignHistService(AkShareService):

    def prepareDataFrame(self, symbol):  # 实例方法
        logger.info("prepareData started")

        try:
            dataFrame = self.ak.futures_foreign_hist(symbol=symbol)

            # 检测并删除字段名为 's' 的列
            if 's' in dataFrame.columns:
                logger.info("检测到字段 's'，正在删除...")
                dataFrame = dataFrame.drop('s', axis=1)
                logger.info(f"删除 's' 字段后，剩余列: {list(dataFrame.columns)}")
            if 'settlement' in dataFrame.columns:
                logger.info("检测到字段 'settlement'，正在删除...")
                dataFrame = dataFrame.drop('settlement', axis=1)
                logger.info(f"删除 's' 字段后，剩余列: {list(dataFrame.columns)}")

            dataFrame['symbol'] = symbol

            #dataFrame.columns = ['date', 'open', 'high', 'low', 'close', ' volume', 'position', 'settlement', 'symbol']
            dataFrame.columns = ['date', 'open', 'high', 'low', 'close', ' volume', 'position', 'symbol']

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")
        return dataFrame

    def transformDataFrame(self, dataFrame: pandas.core.frame.DataFrame):  # 实例方法
        logger.info("transformData started")

        try:
            # 数据预处理：转换日期列
            if 'date' in dataFrame.columns:
                dataFrame['date'] = dataFrame['date'].astype(str)

            # 按日期排序确保计算正确
            dataFrame = dataFrame.sort_values('date').reset_index(drop=True)

            # 计算涨跌幅：(当前收盘价 - 前一日收盘价) / 前一日收盘价
            dataFrame['pct_change'] = dataFrame['close'].pct_change() * 100

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("transformData completed")
        return dataFrame

    def saveDateToClickHouse(self, dataFrame):  # 实例方法
        logger.info("saveDateToClickHouse started")

        try:
            # 显示数据信息用于调试
            logger.info(f"准备保存的数据列: {list(dataFrame.columns)}")
            logger.info(f"数据类型: {dataFrame.dtypes}")
            logger.info(f"数据形状: {dataFrame.shape}")
            logger.info(f"前几行数据:\n{dataFrame.head()}")

            # 确保只保存数据库表中存在的列，并且数据类型正确
            #db_columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'position', 'settlement', 'symbol','pct_change']
            db_columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'position', 'symbol', 'pct_change']
            columns_to_save = [col for col in db_columns if col in dataFrame.columns]

            # 创建要保存的数据副本
            dataFrame_to_save = dataFrame[columns_to_save].copy()

            # 确保数据类型正确
            if 'date' in dataFrame_to_save.columns:
                dataFrame_to_save['date'] = dataFrame_to_save['date'].astype(str)
            if 'volume' in dataFrame_to_save.columns:
                dataFrame_to_save['volume'] = dataFrame_to_save['volume'].fillna(0).astype('int64')
            if 'position' in dataFrame_to_save.columns:
                dataFrame_to_save['position'] = dataFrame_to_save['position'].fillna(0).astype('int64')

            logger.info(f"实际保存的列: {list(dataFrame_to_save.columns)}")
            logger.info(f"保存前数据类型: {dataFrame_to_save.dtypes}")

            # 使用明确的列名插入语句
            columns_str = ', '.join(columns_to_save)
            insert_sql = f"INSERT INTO indexsysdb.df_akshare_futures_foreign_hist ({columns_str}) VALUES"

            logger.info(f"执行的SQL: {insert_sql}")

            self.saveAkDateToClickHouse(insert_sql, dataFrame_to_save)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed: %s", insert_sql)

        return

    def deleteDateFromClickHouse(self, start_date="0000000", end_date="0000000", symbol=""):  # 实例方法
        logger.info("deleteDataFromClickHouse started")

        try:
            del_sql = "ALTER TABLE indexsysdb.df_akshare_futures_foreign_hist DELETE where date>= '%s' and date<='%s' and symbol='%s' " % (start_date, end_date, symbol)
            self.deleteAkDateFromClickHouse(del_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDataFromClickHouse completed: %s", del_sql)

        return

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
            dataFrame['symbol'] = symbol
            dataFrame.columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'position', 'settlement', 'symbol']

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
            # 注意：数据库表结构中没有 pct_change 字段，需要在插入前处理
            # 如果要保存涨跌幅，需要修改表结构或只保存基础字段
            #columns_to_save = ['date', 'open', 'high', 'low', 'close', 'volume', 'position', 'settlement']
            #dataFrame_to_save = dataFrame[columns_to_save].copy()

            dataFrame_to_save = dataFrame.copy()

            insert_sql = "INSERT INTO indexsysdb.df_akshare_futures_foreign_hist VALUES"
            self.saveAkDateToClickHouse(insert_sql, dataFrame_to_save)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed: %s", insert_sql)

        return

    def deleteDateFromClickHouse(self, start_date="0000000", end_date="0000000"):  # 实例方法
        logger.info("deleteDataFromClickHouse started")

        try:
            del_sql = "ALTER TABLE indexsysdb.df_akshare_futures_foreign_hist DELETE where date>= '%s' and date<='%s'" % (start_date, end_date)
            self.deleteAkDateFromClickHouse(del_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDataFromClickHouse completed: %s", del_sql)

        return

from dataIntegrator import CommonLib
from dataIntegrator.AKShareService.AkShareService import AkShareService
import sys
logger = CommonLib.logger

class AkShareSpotHistSGEService(AkShareService):


    #@classmethod
    def prepareDataFrame(self, start_date, end_date):  # 移除 @classmethod 装饰器
        logger.info("prepareData started")

        try:
            dataFrame = self.ak.spot_hist_sge(symbol='Au99.99')
            dataFrame.columns = [
                'date',
                'open',
                'close',
                'low',
                'high']

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")
        return dataFrame

    @classmethod
    def saveDateToClickHouse(self, dataFrame):
        logger.info("saveDateToClickHouse started")

        try:
            # 数据预处理：转换日期列
            if 'date' in dataFrame.columns:
                dataFrame['date'] = dataFrame['date'].astype(str)

            # 按日期排序确保计算正确
            dataFrame = dataFrame.sort_values('date').reset_index(drop=True)

            # 计算涨跌幅：(当前收盘价 - 前一日收盘价) / 前一日收盘价
            dataFrame['pct_change'] = dataFrame['close'].pct_change() * 100

            insert_sql = "INSERT INTO indexsysdb.df_akshare_spot_hist_sge VALUES"
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
            del_sql = "ALTER TABLE indexsysdb.df_akshare_spot_hist_sge DELETE where date>= '%s' and date<='%s'" % (start_date, end_date)
            self.deleteAkDateFromClickHouse(del_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDataFromClickHouse completed: %s", del_sql)

        return

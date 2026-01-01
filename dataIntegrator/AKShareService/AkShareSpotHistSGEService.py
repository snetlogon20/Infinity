from dataIntegrator import CommonLib
from dataIntegrator.AKShareService.AkShareService import AkShareService
import sys
logger = CommonLib.logger

class AkShareSpotHistSGEService(AkShareService):


    #@classmethod
    def prepareDataFrame(self, start_date, end_date):  # 移除 @classmethod 装饰器
        logger.info("prepareData started")

        try:
            self.dataFrame = self.ak.spot_hist_sge(symbol='Au99.99')
            self.dataFrame.columns = [
                'date',
                'open',
                'close',
                'low',
                'high']

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")
        return self.dataFrame

    @classmethod
    def saveDateToClickHouse(self, dataFrame):
        logger.info("saveDateToClickHouse started")

        try:
            # 数据预处理：转换日期列
            if 'date' in dataFrame.columns:
                dataFrame['date'] = dataFrame['date'].astype(str)

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

from dataIntegrator import CommonLib
from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys

logger = CommonLib.logger

class TuShareCNIndexDailyService(TuShareService):
    @classmethod
    def prepareDataFrame(self, ts_code, start_date, end_date):
        logger.info("prepareData started")
        try:
            self.dataFrame = self.pro.index_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")

        return self.dataFrame

    @classmethod
    def saveDateToClickHouse(self):
        logger.info("saveDateToClickHouse started")

        try:
            insert_df_tushare_cn_index_daily = 'insert into indexsysdb.df_tushare_cn_index_daily (ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount) VALUES'
            dataValues = self.dataFrame.to_dict('records')
            self.clickhouseClient.execute(insert_df_tushare_cn_index_daily, dataValues)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed")

    @classmethod
    def deleteDateFromClickHouse(self, ts_code="", start_date="00000000", end_date="00000000"):
        logger.info("deleteDataFromClickHouse started")

        try:
            del_df_tushare_sql = "ALTER TABLE indexsysdb.df_tushare_cn_index_daily DELETE where ts_code = '%s' and trade_date>= '%s' and trade_date<='%s'" % (ts_code, start_date, end_date)
            self.clickhouseClient.execute(del_df_tushare_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name, event="ALTER TABLE indexsysdb.df_tushare_stock_daily Error")
            raise e

        logger.info("deleteDateFromClickHouse completed")

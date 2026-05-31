from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib

logger = CommonLib.logger

class TushareShiborLPRDailyService(TuShareService):
    @classmethod
    def prepareDataFrame(self, start_date, end_date):
        logger.info("prepareData started")

        try:
            self.dataFrame = self.pro.shibor_lpr(start_date=start_date, end_date=end_date)
            self.dataFrame.columns = ["trade_date","tenor_1y","tenor_5y"]

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData started")

        return self.dataFrame

    @classmethod
    def saveDateToClickHouse(self):
        logger.info("saveDateToClickHouse started")

        try:
            insert_sql_statement = 'insert into indexsysdb.df_tushare_shibor_lpr_daily (trade_date,tenor_1y, tenor_5y) VALUES'
            data = self.dataFrame.to_dict('records')
            self.clickhouseClient.execute(insert_sql_statement, data)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e
        logger.info("saveDateToClickHouse completed")

    @classmethod
    def deleteDateFromClickHouse(self, start_date, end_date):
        logger.info("deleteDataFromClickHouse started")

        try:
            del_df_tushare_sql = "ALTER TABLE indexsysdb.df_tushare_shibor_lpr_daily DELETE where trade_date>= '%s' and trade_date<='%s'" % (start_date, end_date)

            self.clickhouseClient.execute(del_df_tushare_sql, settings={'mutations_sync': 1})
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDateFromClickHouse completed")

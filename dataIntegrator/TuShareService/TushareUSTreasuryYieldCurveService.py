from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib

logger = CommonLib.logger

class TushareUSTreasuryYieldCurveService(TuShareService):
    @classmethod
    def prepareDataFrame(self, start_date, end_date):
        logger.info("prepareData started")

        try:
            self.dataFrame = self.pro.us_tycr(start_date=start_date, end_date=end_date, fields = 'date, m1,m2,m3,m6,y1,y2,y3,y5,y7,y10,y20,y30')
            self.dataFrame.columns = ['trade_date',
                'm1',
                'm2',
                'm3',
                'm6',
                'y1',
                'y2',
                'y3',
                'y5',
                'y7',
                'y10',
                'y20',
                'y30']

            logger.info("self.dataFrame.shape:" + str(self.dataFrame.shape))

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData started")

        return self.dataFrame

    @classmethod
    def saveDateToClickHouse(self):
        logger.info("saveDateToClickHouse started")

        try:
            self.dataFrame = self.dataFrame.replace({None: "Nan"})
            self.dataFrame["delist_date"] = "Nan"

            insert_sql_statement = 'insert into indexsysdb.df_tushare_us_treasury_yield_cruve (trade_date, m1,m2,m3,m6,y1,y2,y3,y5,y7,y10,y20,y30) VALUES'
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
            del_df_tushare_sql = "ALTER TABLE indexsysdb.df_tushare_us_treasury_yield_cruve DELETE where trade_date>= '%s' and trade_date<='%s'" % (start_date, end_date)

            self.clickhouseClient.execute(del_df_tushare_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDateFromClickHouse completed")
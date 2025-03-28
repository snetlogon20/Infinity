from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys

class TushareUSTreasuryYieldCurveService(TuShareService):
    @classmethod
    def prepareDataFrame(self, start_date, end_date):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name, event="prepareData started")

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

            self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                              event="self.dataFrame.shape:" + str(self.dataFrame.shape))

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name, event="prepareData started")

        return self.dataFrame

    @classmethod
    def saveDateToClickHouse(self):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="saveDateToClickHouse started")

        try:
            self.dataFrame = self.dataFrame.replace({None: "Nan"})
            self.dataFrame["delist_date"] = "Nan"

            insert_sql_statement = 'insert into indexsysdb.df_tushare_us_treasury_yield_cruve (trade_date, m1,m2,m3,m6,y1,y2,y3,y5,y7,y10,y20,y30) VALUES'
            data = self.dataFrame.to_dict('records')
            self.clickhouseClient.execute(insert_sql_statement, data)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="saveDateToClickHouse completed")

    @classmethod
    def deleteDateFromClickHouse(self, start_date, end_date):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="deleteDataFromClickHouse started")

        try:
            del_df_tushare_sql = "ALTER TABLE indexsysdb.df_tushare_us_treasury_yield_cruve DELETE where trade_date>= '%s' and trade_date<='%s'" % (start_date, end_date)

            self.clickhouseClient.execute(del_df_tushare_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="deleteDateFromClickHouse completed")
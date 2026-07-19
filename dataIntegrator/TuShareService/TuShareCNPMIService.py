import pandas as pd
from dataIntegrator import CommonLib
from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
logger = CommonLib.logger

class TuShareCNPMIService(TuShareService):

    @classmethod
    def prepareDataFrame(self, start_date, end_date):
        logger.info("prepareData started")

        try:
            self.dataFrame = self.pro.cn_pmi(start_m=start_date, end_m=end_date)
            # 动态处理列名：将所有列名转为小写，并将MONTH重命名为trade_date
            cols = [col.lower() for col in self.dataFrame.columns.tolist()]
            for i, col in enumerate(cols):
                if col == 'month':
                    cols[i] = 'trade_date'
                    break
            self.dataFrame.columns = cols

            # 将所有数值列转为float，None/NaN填充为0.0，避免ClickHouse Float64类型不匹配
            for col in self.dataFrame.columns:
                if col != 'trade_date':
                    self.dataFrame[col] = pd.to_numeric(self.dataFrame[col], errors='coerce').fillna(0.0)

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")

        return self.dataFrame

    @classmethod
    def saveDateToClickHouse(self):
        logger.info("saveDateToClickHouse started")

        try:
            insert_sql_statement = ('insert into indexsysdb.df_tushare_cn_pmi '
                '(trade_date,'
                'pmi010000,pmi010100,pmi010200,pmi010300,'
                'pmi010400,pmi010401,pmi010402,pmi010403,'
                'pmi010500,pmi010501,pmi010502,pmi010503,'
                'pmi010600,pmi010601,pmi010602,pmi010603,'
                'pmi010700,pmi010701,pmi010702,pmi010703,'
                'pmi010800,pmi010801,pmi010802,pmi010803,'
                'pmi010900,pmi011000,pmi011100,pmi011200,'
                'pmi011300,pmi011400,pmi011500,pmi011600,'
                'pmi011700,pmi011800,pmi011900,pmi012000,'
                'pmi020100,pmi020101,pmi020102,'
                'pmi020200,pmi020201,pmi020202,'
                'pmi020300,pmi020301,pmi020302,'
                'pmi020400,pmi020401,pmi020402,'
                'pmi020500,pmi020501,pmi020502,'
                'pmi020600,pmi020601,pmi020602,'
                'pmi020700,pmi020800,pmi020900,pmi021000,'
                'pmi030000) VALUES'
            )
            data = self.dataFrame.to_dict('records')
            self.clickhouseClient.execute(insert_sql_statement, data)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e
        logger.info("saveDateToClickHouse completed")

    @classmethod
    def deleteDateFromClickHouse(self, start_date, end_date):
        logger.info("deleteDateFromClickHouse started")

        try:
            del_df_tushare_sql = "ALTER TABLE indexsysdb.df_tushare_cn_pmi DELETE where trade_date>= '%s' and trade_date<='%s'" % (start_date, end_date)
            self.clickhouseClient.execute(del_df_tushare_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDateFromClickHouse completed")

from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib

logger = CommonLib.logger

class TuShareYcCbService(TuShareService):

    @classmethod
    def prepareDataFrame(self, ts_code, start_date, end_date):
        logger.info("prepareData started")

        try:
            # 调用 TuShare yc_cb 接口
            # 根据接口定义，输入参数为 ts_code, start_date, end_date 等
            self.dataFrame = self.pro.yc_cb(ts_code=ts_code, start_date=start_date, end_date=end_date)

            # 重命名列以匹配数据库定义
            self.dataFrame.columns = [
                'trade_date',
                'ts_code',
                'curve_name',
                'curve_type',
                'curve_term',
                'yield'
            ]

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")
        return self.dataFrame

    @classmethod
    def saveDateToClickHouse(self):
        logger.info("saveDateToClickHouse started")

        try:
            insert_sql_statement = 'INSERT INTO indexsysdb.df_tushare_yc_cb (trade_date, ts_code, curve_name, curve_type, curve_term, yield) VALUES'
            data = self.dataFrame.to_dict('records')
            self.clickhouseClient.execute(insert_sql_statement, data)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed")

    @classmethod
    def deleteDateFromClickHouse(self, ts_code, start_date, end_date):
        logger.info("deleteDateFromClickHouse started")

        try:
            del_sql = "ALTER TABLE indexsysdb.df_tushare_yc_cb DELETE WHERE ts_code = '%s' AND trade_date >= '%s' AND trade_date <= '%s'" % (ts_code, start_date, end_date)
            self.clickhouseClient.execute(del_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDateFromClickHouse completed")

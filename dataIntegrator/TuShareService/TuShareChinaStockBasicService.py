from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib

logger = CommonLib.logger

class TuShareStockBasicService(TuShareService):
    @classmethod
    def prepareDataFrame(self, exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date'):
        logger.info("prepareData started")

        try:
            self.dataFrame = self.pro.stock_basic(exchange=exchange, list_status=list_status, fields=fields)
            logger.info(f"成功获取股票列表数据，共 {len(self.dataFrame)} 行")
            logger.info(f"self.dataFrame.shape: {str(self.dataFrame.shape)}")

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")

        return self.dataFrame

    @classmethod
    def saveDateToClickHouse(self):
        logger.info("saveDateToClickHouse started")

        try:
            self.dataFrame = self.dataFrame.replace({None: "Nan"})

            columns = self.dataFrame.columns.tolist()
            columns_str = ','.join(columns)

            insert_sql_statement = f'insert into indexsysdb.df_tushare_stock_basic ({columns_str}) VALUES'
            data = self.dataFrame.to_dict('records')
            self.clickhouseClient.execute(insert_sql_statement, data)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed")

    @classmethod
    def deleteDateFromClickHouse(self):
        logger.info("deleteDataFromClickHouse started")

        try:
            del_df_tushare_sql = "ALTER TABLE indexsysdb.df_tushare_stock_basic DELETE where ts_code is not Null"
            self.clickhouseClient.execute(del_df_tushare_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name, event="ALTER TABLE indexsysdb.df_tushare_stock_basic Error")
            raise e

        logger.info("deleteDateFromClickHouse completed")

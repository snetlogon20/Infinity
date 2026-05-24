from dataIntegrator import CommonLib
from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
import pandas as pd

logger = CommonLib.logger

class TuShareIndexGlobalService(TuShareService):
    @classmethod
    def prepareDataFrame(self, ts_code, start_date, end_date):
        logger.info("prepareData started")
        try:
            self.dataFrame = self.pro.index_global(ts_code=ts_code, start_date=start_date, end_date=end_date)

            row_count = len(self.dataFrame)
            logger.info(f"成功获取全球指数 {ts_code} 的数据，共 {row_count} 行")
            
            # 数据清洗：确保 amount 字段存在（接口返回可能缺少该字段）
            if 'amount' not in self.dataFrame.columns:
                logger.warning(f"全球指数 {ts_code} 数据中缺少 amount 字段，将填充为 0")
                self.dataFrame['amount'] = 0.0
            
            # 处理 NaN 值，将 None/NaN 转换为 0
            numeric_columns = ['open', 'close', 'high', 'low', 'pre_close', 'change', 'pct_chg', 'swing', 'vol', 'amount']
            for col in numeric_columns:
                if col in self.dataFrame.columns:
                    self.dataFrame[col] = pd.to_numeric(self.dataFrame[col], errors='coerce').fillna(0)
                    
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")

        return self.dataFrame

    @classmethod
    def saveDateToClickHouse(self):
        logger.info("saveDateToClickHouse started")

        try:
            insert_df_tushare_index_global = 'insert into indexsysdb.df_tushare_index_global (ts_code,trade_date,open,close,high,low,pre_close,change,pct_chg,swing,vol,amount) VALUES'
            dataValues = self.dataFrame.to_dict('records')
            # self.clickhouseClient.executed(insert_df_tushare_index_global, dataValues)
            self.clickhouseClient.execute(insert_df_tushare_index_global, dataValues)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed")

    @classmethod
    def deleteDateFromClickHouse(self, ts_code="", start_date="00000000", end_date="00000000"):
        logger.info("deleteDateFromClickHouse started")

        try:
            del_df_tushare_sql = "ALTER TABLE indexsysdb.df_tushare_index_global DELETE where ts_code = '%s' and trade_date>= '%s' and trade_date<='%s'" % (ts_code, start_date, end_date)
            self.clickhouseClient.execute(del_df_tushare_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name, event="ALTER TABLE indexsysdb.df_tushare_index_global Error")
            raise e

        logger.info("deleteDateFromClickHouse completed")


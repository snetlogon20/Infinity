from dataIntegrator import CommonLib
from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
logger = CommonLib.logger

class TuShareCNPPIService(TuShareService):

    @classmethod
    def prepareDataFrame(self, start_date, end_date):
        logger.info("prepareData started")

        try:
            self.dataFrame = self.pro.cn_ppi(start_m=start_date, end_m=end_date)
            # 动态处理列名：将所有列名转为小写，并将MONTH重命名为trade_date
            cols = [col.lower() for col in self.dataFrame.columns.tolist()]
            for i, col in enumerate(cols):
                if col == 'month':
                    cols[i] = 'trade_date'
                    break
            self.dataFrame.columns = cols

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")

        return self.dataFrame

    @classmethod
    def saveDateToClickHouse(self):
        logger.info("saveDateToClickHouse started")

        try:
            insert_sql_statement = ('insert into indexsysdb.df_tushare_cn_ppi '
                '(trade_date,ppi_yoy,ppi_mp_yoy,ppi_mp_qm_yoy,ppi_mp_rm_yoy,ppi_mp_p_yoy,'
                'ppi_cg_yoy,ppi_cg_f_yoy,ppi_cg_c_yoy,ppi_cg_adu_yoy,ppi_cg_dcg_yoy,'
                'ppi_mom,ppi_mp_mom,ppi_mp_qm_mom,ppi_mp_rm_mom,ppi_mp_p_mom,'
                'ppi_cg_mom,ppi_cg_f_mom,ppi_cg_c_mom,ppi_cg_adu_mom,ppi_cg_dcg_mom,'
                'ppi_accu,ppi_mp_accu,ppi_mp_qm_accu,ppi_mp_rm_accu,ppi_mp_p_accu,'
                'ppi_cg_accu,ppi_cg_f_accu,ppi_cg_c_accu,ppi_cg_adu_accu,ppi_cg_dcg_accu) VALUES'
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
            del_df_tushare_sql = "ALTER TABLE indexsysdb.df_tushare_cn_ppi DELETE where trade_date>= '%s' and trade_date<='%s'" % (start_date, end_date)
            self.clickhouseClient.execute(del_df_tushare_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDateFromClickHouse completed")

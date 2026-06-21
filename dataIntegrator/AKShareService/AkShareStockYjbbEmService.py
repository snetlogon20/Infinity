import pandas
from datetime import datetime

from dataIntegrator import CommonLib
from dataIntegrator.AKShareService.AkShareService import AkShareService
import sys
logger = CommonLib.logger

"""
股票财报 年报季报 - 业绩报表（含 ROE、毛利率、每股收益、每股经营现金流）
"""
class AkShareStockYjbbEmService(AkShareService):

    @classmethod
    def _normalizeToLatestReportDate(cls, date_str):
        """将任意日期转换为最近的不超过该日期的一个季报日期（0331/0630/0930/1231）"""
        d = datetime.strptime(date_str, '%Y%m%d')
        year = d.year
        candidates = [
            datetime(year, 3, 31),
            datetime(year, 6, 30),
            datetime(year, 9, 30),
            datetime(year, 12, 31),
        ]
        latest = None
        for rd in candidates:
            if rd <= d:
                latest = rd
        if latest is None:
            # 早于当年Q1，回退到去年Q4
            latest = datetime(year - 1, 12, 31)
        return latest.strftime('%Y%m%d')

    def prepareDataFrame(self, date):  # 实例方法
        logger.info("prepareData started")

        try:
            # 将任意日期归一化到最近的季报日期，防止非季报日期传给API导致返回None
            report_date = self._normalizeToLatestReportDate(date)
            if report_date != date:
                logger.info(f"将日期 {date} 归一化为最近季报日期: {report_date}")

            dataFrame = self.ak.stock_yjbb_em(date=report_date)
            dataFrame.columns = [
                'seq',
                'stock_code',
                'stock_name',
                'eps',
                'total_revenue',
                'total_revenue_yoy',
                'total_revenue_qoq',
                'net_profit',
                'net_profit_yoy',
                'net_profit_qoq',
                'bvps',
                'roe',
                'cfps',
                'gross_profit_margin',
                'industry',
                'latest_announce_date'
            ]
            # 去掉无用的序号列（API行号，不需要入库）
            if 'seq' in dataFrame.columns:
                dataFrame = dataFrame.drop('seq', axis=1)

            dataFrame['date'] = report_date

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")
        return dataFrame

    @classmethod
    def transformDataFrame(self, dataFrame: pandas.core.frame.DataFrame):
        logger.info("transformData started")

        try:
            # 强制转换所有 String 列，处理 Excel 读写后可能产生的 NaN / int 等类型变异
            string_columns = ['date', 'stock_code', 'stock_name', 'industry', 'latest_announce_date']
            for col in string_columns:
                if col in dataFrame.columns:
                    dataFrame[col] = dataFrame[col].fillna('').astype(str)

            # 记录转换后的列类型
            logger.info(f"transformData dtypes:\n{dataFrame.dtypes}")

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("transformData completed")
        return dataFrame

    @classmethod
    def saveDateToClickHouse(self, dataFrame):
        logger.info("saveDateToClickHouse started")

        try:
            # 确保只保存数据库表中存在的列
            db_columns = [
                'date', 'stock_code', 'stock_name',
                'eps', 'total_revenue', 'total_revenue_yoy', 'total_revenue_qoq',
                'net_profit', 'net_profit_yoy', 'net_profit_qoq',
                'bvps', 'roe', 'cfps', 'gross_profit_margin',
                'industry', 'latest_announce_date'
            ]
            columns_to_save = [col for col in db_columns if col in dataFrame.columns]
            dataFrame_to_save = dataFrame[columns_to_save].copy()

            # 安全转换 String 列，防止 Excel 读写后类型变异（Nan→float, 数字→int 等）
            string_columns = ['date', 'stock_code', 'stock_name', 'industry', 'latest_announce_date']
            for col in string_columns:
                if col in dataFrame_to_save.columns:
                    dataFrame_to_save[col] = dataFrame_to_save[col].fillna('').astype(str)

            logger.info(f"准备保存的数据类型:\n{dataFrame_to_save.dtypes}")
            logger.info(f"准备保存的数据形状: {dataFrame_to_save.shape}")

            columns_str = ', '.join(columns_to_save)
            insert_sql = f"INSERT INTO indexsysdb.df_akshare_stock_yjbb_em ({columns_str}) VALUES"
            self.saveAkDateToClickHouse(insert_sql, dataFrame_to_save)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed: %s", insert_sql)

        return

    @classmethod
    def deleteDateFromClickHouse(self, date="0000000"):
        logger.info("deleteDataFromClickHouse started")

        try:
            # 归一化日期，与 prepareDataFrame 保持一致
            report_date = self._normalizeToLatestReportDate(date)
            del_sql = "ALTER TABLE indexsysdb.df_akshare_stock_yjbb_em DELETE where date = '%s'" % (report_date)
            self.deleteAkDateFromClickHouse(del_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDataFromClickHouse completed (report_date=%s): %s", report_date, del_sql)

        return

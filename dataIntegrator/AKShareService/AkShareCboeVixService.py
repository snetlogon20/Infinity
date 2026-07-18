# D:\workspace_python\infinity\dataIntegrator\AKShareService\AkShareCboeVixService.py
import pandas
from dataIntegrator import CommonLib
from dataIntegrator.AKShareService.AkShareService import AkShareService
import sys

logger = CommonLib.logger

class AkShareCboeVixService(AkShareService):

    def prepareDataFrame(self, start_date=None, end_date=None):
        logger.info("prepareData started")

        try:
            # VIX数据通过HTTPS从CBOE官网拉取CSV
            url = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"

            dataFrame = pandas.read_csv(
                url,
                parse_dates=["DATE"],
                dayfirst=False,
                infer_datetime_format=True
            )

            # 重命名列以匹配数据库字段
            dataFrame = dataFrame.rename(columns={
                'DATE': 'date',
                'OPEN': 'open',
                'HIGH': 'high',
                'LOW': 'low',
                'CLOSE': 'close'
            })
            dataFrame = dataFrame[['date', 'open', 'high', 'low', 'close']]

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")
        return dataFrame

    @classmethod
    def transformDataFrame(self, dataFrame: pandas.core.frame.DataFrame):
        logger.info("transformData started")

        try:
            # 数据预处理：转换日期列为字符串
            if 'date' in dataFrame.columns:
                dataFrame['date'] = dataFrame['date'].astype(str)

            # 按日期排序确保计算正确
            dataFrame = dataFrame.sort_values('date').reset_index(drop=True)

            # 计算涨跌幅：(当前收盘价 - 前一日收盘价) / 前一日收盘价
            dataFrame['pct_change'] = dataFrame['close'].pct_change() * 100

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("transformData completed")
        return dataFrame

    @classmethod
    def saveDateToClickHouse(self, dataFrame):
        logger.info("saveDateToClickHouse started")

        try:
            insert_sql = "INSERT INTO indexsysdb.df_cboe_vix VALUES"
            self.saveAkDateToClickHouse(insert_sql, dataFrame)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed: %s", insert_sql)

        return

    @classmethod
    def deleteDateFromClickHouse(self, start_date="0000000", end_date="0000000"):
        logger.info("deleteDataFromClickHouse started")

        try:
            del_sql = "ALTER TABLE indexsysdb.df_cboe_vix DELETE where date>= '%s' and date<='%s'" % (start_date, end_date)
            self.deleteAkDateFromClickHouse(del_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDataFromClickHouse completed: %s", del_sql)

        return

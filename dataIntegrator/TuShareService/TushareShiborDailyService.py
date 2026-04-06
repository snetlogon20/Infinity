from datetime import datetime

from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

logger = CommonLib.logger

class TushareShiborDailyService(TuShareService):
    @classmethod
    def prepareDataFrame(self, start_date, end_date):
        logger.info("prepareData started")

        try:
            self.dataFrame = self.pro.shibor(start_date=start_date, end_date=end_date)
            self.dataFrame.columns = ['trade_date', 'tenor_on', 'tenor_1w', 'tenor_2w', 'tenor_1m', 'tenor_3m', 'tenor_6m',
                             'tenor_9m', 'tenor_1y']

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData started")

        return self.dataFrame

    @classmethod
    def saveDateToClickHouse(self):
        logger.info("saveDateToClickHouse started")

        try:
            insert_sql_statement = 'insert into indexsysdb.df_tushare_shibor_daily (trade_date,tenor_on,tenor_1w,tenor_2w,tenor_1m,tenor_3m,tenor_6m,tenor_9m,tenor_1y) VALUES'
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
            del_df_tushare_sql = "ALTER TABLE indexsysdb.df_tushare_shibor_daily DELETE where trade_date>= '%s' and trade_date<='%s'" % (start_date, end_date)

            self.clickhouseClient.execute(del_df_tushare_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDateFromClickHouse completed")

    def get_rate_for_term(self, start_date: str, end_date: str) -> tuple:
        """
        根据开始和结束日期，从 ClickHouse 表中筛选数据，
        计算日期范围内的平均利率，并选择合适的期限列返回单个值。

        参数:
            start_date (str): 开始日期，格式 'YYYYMMDD'（如 '20220103'）
            end_date (str): 结束日期，格式 'YYYYMMDD'

        返回:
            tuple: (平均利率, 最早日期利率, 最晚日期利率, 最大利率, 最小利率)
        """
        # 初始化 ClickHouse 服务
        clickhouseService = ClickhouseService()

        # 构建 SQL 查询语句，筛选日期范围内的数据
        sql = f"""
        SELECT * 
        FROM df_tushare_shibor_daily 
        WHERE trade_date >= '{start_date}' AND trade_date <= '{end_date}'
        """

        # 获取数据（不带列名）
        df = clickhouseService.getDataFrameWithoutColumnsName(sql)

        # 检查是否有数据
        if df.empty:
            raise ValueError(f"在日期范围 {start_date} 到 {end_date} 内没有数据")

        # 自动选择最合适的期限列（基于日期跨度天数）
        date_range_days = (datetime.strptime(end_date, '%Y%m%d') - datetime.strptime(start_date, '%Y%m%d')).days

        # 定义期限列与对应天数的映射
        term_columns = {
            'tenor_on': 1,
            'tenor_1w': 7,
            'tenor_2w': 14,
            'tenor_1m': 30,
            'tenor_3m': 90,
            'tenor_6m': 180,
            'tenor_9m': 270,
            'tenor_1y': 365
        }

        # 选择最接近日期跨度的期限列
        best_term = min(term_columns.keys(), key=lambda x: abs(term_columns[x] - date_range_days))

        # 计算该期限列在日期范围内的统计值
        avg_rate = df[best_term].mean()/100
        earliest_rate = df[best_term].iloc[0]/100
        latest_rate = df[best_term].iloc[-1]/100
        max_rate = df[best_term].max()/100
        min_rate = df[best_term].min()/100

        return avg_rate, earliest_rate, latest_rate, max_rate, min_rate
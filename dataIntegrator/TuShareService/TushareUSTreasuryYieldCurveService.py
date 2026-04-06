from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib
from datetime import datetime
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

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

    def get_yield_for_term(cls, start_date: str, end_date: str) -> float:
        """
        根据开始和结束日期，从 ClickHouse 表中筛选数据，
        计算日期范围内的平均收益率，并选择合适的期限列返回单个值。

        参数:
            start_date (str): 开始日期，格式 'YYYYMMDD'（如 '20220103'）
            end_date (str): 结束日期，格式 'YYYYMMDD'

        返回:
            float: 选定期限在日期范围内的平均收益率
        """
        # 初始化 ClickHouse 服务
        clickhouseService = ClickhouseService()

        # 构建 SQL 查询语句，筛选日期范围内的数据
        sql = f"""
        SELECT * 
        FROM df_tushare_us_treasury_yield_cruve 
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
            'm1': 30,
            'm2': 60,
            'm3': 90,
            'm6': 180,
            'y1': 365,
            'y2': 730,
            'y3': 1095,
            'y5': 1825,
            'y7': 2555,
            'y10': 3650,
            'y20': 7300,
            'y30': 10950
        }

        # 选择最接近日期跨度的期限列
        best_term = min(term_columns.keys(), key=lambda x: abs(term_columns[x] - date_range_days))

        # 计算该期限列在日期范围内的平均值
        # 假设列名是 'm1', 'm2', ..., 'y30'，且数据按 trade_date 排序
        avg_yield = df[best_term].mean()/100
        earliest_yield = df[best_term].iloc[0]/100
        latest_yield = df[best_term].iloc[-1]/100
        max_yield = df[best_term].max()/100
        min_yield = df[best_term].min()/100

        return avg_yield, earliest_yield, latest_yield, max_yield, min_yield
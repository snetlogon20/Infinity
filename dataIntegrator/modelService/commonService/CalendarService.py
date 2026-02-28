import pandas
from datetime import datetime

from dataIntegrator.analysisService.InquiryManager import InquiryManager
from dataIntegrator.common import CommonLib, CommonLogLib
from clickhouse_driver import Client as ClickhouseClient
from dataIntegrator.common.CommonParameters import CommonParameters
import pandas as pd
import sys

from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from datetime import timedelta

#from dataIntegrator import CommonLib

#logger = CommonLib.logger

class CalendarService(CommonLib.CommonLib):
    dataFrame = pandas.core.frame.DataFrame
    clickhouseClient = ClickhouseClient(host=CommonParameters.clickhouseHostName,
                                        database=CommonParameters.clickhouseHostDatabase)

    def __init__(self):
        self.writeLogInfo("Calendar.__init__ started")

        self.clickhouseService = ClickhouseService()

        self.writeLogInfo("Calendar.__init__ completed")

    @classmethod
    def createCalendar(self, start_date = '1900-01-01', end_date = datetime.now().date()):
        # Define the date range
        date_range = pandas.date_range(start=start_date, end=end_date)

        # Create the DataFrame
        df_calendar = pandas.DataFrame()
        df_calendar_temp = pandas.DataFrame(date_range, columns=['calendar_date'])
        df_calendar['trade_date'] = df_calendar_temp['calendar_date'].dt.strftime('%Y%m%d')
        df_calendar['trade_year'] = df_calendar_temp['calendar_date'].dt.year
        df_calendar['trade_month'] = df_calendar_temp['calendar_date'].dt.month
        df_calendar['trade_day'] = df_calendar_temp['calendar_date'].dt.day
        df_calendar['day_of_week'] = df_calendar_temp['calendar_date'].dt.day_name()
        df_calendar['quarter'] = ((df_calendar['trade_month'].astype(int) - 1) // 3 + 1).astype(str)
        df_calendar['calendar_date'] = df_calendar_temp['calendar_date']
        df_calendar = df_calendar.astype(str)

        self.dataFrame = df_calendar
        print(self.dataFrame)


    @classmethod
    def saveDateToClickHouse(self, start_date = '1900-01-01', end_date = datetime.now().date()):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="saveDateToClickHouse started")

        try:
            insert_df_sys_calendar = 'insert into indexsysdb.df_sys_calendar (trade_date,trade_year,trade_month,trade_day,day_of_week,quarter,calendar_date) VALUES'
            dataValues = self.dataFrame.to_dict('records')
            self.clickhouseClient.execute(insert_df_sys_calendar, dataValues)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="saveDateToClickHouse completed")

    @classmethod
    def deleteDataFromClickHouse(self, start_date="00000000", end_date="00000000"):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="deleteDataFromClickHouse started")

        try:
            del_df_tushare_sql = "ALTER TABLE indexsysdb.df_sys_calendar DELETE where trade_date>= '%s' and trade_date<='%s'" % (start_date, end_date)
            self.clickhouseClient.execute(del_df_tushare_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name, event="ALTER TABLE indexsysdb.df_tushare_stock_daily Error")
            raise e

        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name, event="deleteDateFromClickHouse completed")

    def load_calendar(self, start_date="00000000", end_date="00000000"):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="load Calendar started")

        start_date = start_date.replace('-', '')
        end_date = end_date.replace('-', '')

        try:

            sql = rf"""
                select *
                from indexsysdb.df_sys_calendar
                where trade_date >= '{start_date}' and 
                    trade_date <=  '{end_date}'
                order by trade_date
            """
            columns = ['trade_date', 'trade_year', 'trade_month', 'trade_day', 'day_of_week', 'quarter', 'calendar_date']

            self.calendar_df = self.clickhouseService.getDataFrame(sql, columns)
            self.calendar_df['trade_date'] = pd.to_datetime(self.calendar_df['trade_date']).dt.date

            return self.calendar_df

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="saveDateToClickHouse completed")

        return self.calendar_df

    def load_next_n_days_calendar(self, start_date, end_date, next_n_days):
        """
        加载从 start_date 到 end_date + next_n_days 的日历记录
        :param start_date: 起始日期 (str, 格式: 'YYYY-MM-DD')
        :param end_date: 结束日期 (str, 格式: 'YYYY-MM-DD')
        :param next_n_days: 向后扩展的天数 (int)
        :return: 扩展后的日历 DataFrame
        """
        self.writeLogInfo(
            className=self.__class__.__name__,
            functionName=sys._getframe().f_code.co_name,
            event="load_extended_calendar started"
        )

        try:
            # 将 end_date 转换为 datetime 对象并加上 next_n_days
            extended_end_date = pd.to_datetime(end_date) + timedelta(days=next_n_days)
            extended_end_date_str = extended_end_date.strftime('%Y-%m-%d')

            # 调用 load_calendar 获取扩展范围内的数据
            extended_calendar_df = self.load_calendar(start_date=start_date, end_date=extended_end_date_str)

            self.writeLogInfo(
                className=self.__class__.__name__,
                functionName=sys._getframe().f_code.co_name,
                event="load_extended_calendar completed"
            )

            return extended_calendar_df

        except Exception as e:
            self.writeLogError(
                e,
                className=self.__class__.__name__,
                functionName=sys._getframe().f_code.co_name,
                event="load_extended_calendar failed"
            )
            raise e

    def get_last_date_from_calendar(self, start_date, end_date, n_days):
        """
        根据load_next_n_days_calendar的返回结果，获取最后一个日期值

        Args:
            start_date (str): 开始日期
            end_date (str): 结束日期
            n_days (int): 天数

        Returns:
            str: 最后一个日期，格式为 'yyyy-mm-dd'
        """
        try:
            # 调用现有的load_next_n_days_calendar方法
            calendar_df = self.load_next_n_days_calendar(start_date, end_date, n_days)

            # 检查返回的数据框是否为空
            if calendar_df is not None and not calendar_df.empty:
                # 获取最后一个日期值
                last_date = calendar_df['trade_date'].iloc[-1]

                # 确保返回格式为 yyyy-mm-dd 字符串
                if isinstance(last_date, str):
                    formatted_last_date = last_date
                else:
                    # 如果是日期对象，转换为字符串
                    formatted_last_date = pd.to_datetime(last_date).strftime('%Y-%m-%d')

                self.logger.info(f"获取到最后一个日期: {formatted_last_date}")
                return formatted_last_date
            else:
                self.logger.warning("日历数据为空，无法获取最后日期")
                return None

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__,
                               functionName=sys._getframe().f_code.co_name)
            return None

    def calculate_quarter(cls, date):
        """
        根据 end_date 计算对应的季度，格式为 yyyyQn
        :param date: 字符串格式 'yyyymmdd'
        :return: 季度字符串 'yyyyQn'
        """
        try:
            # 将字符串转换为 datetime 对象
            date_obj = datetime.strptime(date, '%Y%m%d')
            year = date_obj.year
            month = date_obj.month

            # 根据月份确定季度
            if 1 <= month <= 3:
                quarter = 1
            elif 4 <= month <= 6:
                quarter = 2
            elif 7 <= month <= 9:
                quarter = 3
            else:  # 10 <= month <= 12
                quarter = 4

            return f"{year}Q{quarter}"
        except Exception as e:
            # 静态方法中无法访问实例方法，直接打印错误
            cls.writeLogError(e, className=cls.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

    # def get_last_working_date_from_calendar(self, start_date, end_date, n_working_days):
    #     """
    #     根据load_next_n_working_days_calendar的返回结果，获取最后一个工作日日期
    #
    #     Args:
    #         start_date (str): 开始日期，格式为 'YYYY-MM-DD'
    #         end_date (str): 结束日期，格式为 'YYYY-MM-DD'
    #         n_working_days (int): 工作日天数
    #
    #     Returns:
    #         str: 最后一个工作日，格式为 'YYYY-MM-DD'
    #     """
    #     try:
    #         # 调用现有的load_next_n_working_days_calendar方法
    #         working_calendar_df = self.load_next_n_working_days_calendar(start_date, end_date, n_working_days)
    #
    #         # 检查返回的数据框是否为空
    #         if working_calendar_df is not None and not working_calendar_df.empty:
    #             # 获取最后一个工作日日期值
    #             last_working_date = working_calendar_df['trade_date'].iloc[-1]
    #
    #             # 确保返回格式为 YYYY-MM-DD 字符串
    #             if isinstance(last_working_date, str):
    #                 formatted_last_date = last_working_date
    #             else:
    #                 # 如果是日期对象，转换为字符串
    #                 formatted_last_date = pd.to_datetime(last_working_date).strftime('%Y-%m-%d')
    #
    #             self.logger.info(f"获取到最后一个工作日: {formatted_last_date}")
    #             return formatted_last_date
    #         else:
    #             self.logger.warning("工作日历数据为空，无法获取最后工作日")
    #             return None
    #
    #     except Exception as e:
    #         self.logger.error(f"获取最后工作日失败: {e}")
    #         return None

    def find_data_by_given_dataframe_and_date_offset(self, original_dataFrame, formatted_start_date, next_n_working_days):
        """
        根据original_dataFrame中的date字段，找到formatted_start_date之后第next_n_working_days条记录的data字段值

        Args:
            original_dataFrame (pd.DataFrame): 包含date和data字段的原始数据框
            formatted_start_date (str): 起始日期，格式为 'YYYY-MM-DD'
            next_n_working_days (int): 向后偏移的工作日天数

        Returns:
            object: 对应记录的data字段值，如果未找到则返回None
        """
        try:
            # 确保必要的字段存在
            if 'trade_date' not in original_dataFrame.columns:
                self.logger.error("original_dataFrame中缺少'trade_date'字段")
                return None

            # 按日期正向排序
            sorted_df = original_dataFrame.sort_values('trade_date').reset_index(drop=True)

            # 找到起始日期的位置
            start_rows = sorted_df[sorted_df['trade_date'] == formatted_start_date]

            if start_rows.empty:
                self.logger.warning(f"未找到起始日期: {formatted_start_date}")
                # 如果找不到精确匹配，找最接近的日期
                closest_date = sorted_df[sorted_df['trade_date'] >= formatted_start_date]['trade_date'].min()
                if pd.notna(closest_date):
                    start_rows = sorted_df[sorted_df['trade_date'] == closest_date]
                    self.logger.info(f"使用最接近的日期: {closest_date}")
                else:
                    return None

            start_index = start_rows.index[0]

            # 计算目标索引
            target_index = start_index + next_n_working_days

            # 检查索引是否有效
            if target_index < len(sorted_df):
                target_row = sorted_df.iloc[target_index]
                data_value = target_row.get('trade_date', None)  # 使用get方法避免KeyError

                self.logger.info(f"找到日期 {target_row['trade_date']} 的数据: {data_value}")
                return data_value
            else:
                self.logger.warning(f"索引 {target_index} 超出数据范围，最大索引为 {len(sorted_df) - 1}")
                # 没有日历了， 只能到 indexsysdb.df_sys_calendar 去找了
                inquiryManager = InquiryManager()
                sql = f"select * from indexsysdb.df_sys_calendar where calendar_date>='{formatted_start_date}' and day_of_week not in ('Saturday','Sunday')  order by trade_date "
                original_dataFrame = inquiryManager.get_sql_dataset(sql)
                original_dataFrame.rename(columns={'trade_date': 'trade_date'}, inplace=True)

                # 使用普通版本
                calendarService = CalendarService()
                result1 = calendarService.find_data_by_given_dataframe_and_date_offset(original_dataFrame,
                                                                                       formatted_start_date,
                                                                                       next_n_working_days)
                result1 = f"{str(result1)[:4]}-{str(result1)[4:6]}-{str(result1)[6:8]}"
                return result1


        except Exception as e:
            self.logger.error(f"查找数据失败: {e}")
            return None

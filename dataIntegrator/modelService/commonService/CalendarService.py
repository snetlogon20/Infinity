import pandas
from datetime import datetime
from dataIntegrator.common import CommonLib, CommonLogLib
from clickhouse_driver import Client as ClickhouseClient
from dataIntegrator.common.CommonParameters import CommonParameters
import pandas as pd
import sys

from dataIntegrator.dataService.ClickhouseService import ClickhouseService


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

if __name__ == '__main__':
    calendar = CalendarService()

    #################################
    # Inquiry Calendar
    #################################
    calendar_df = calendar.load_calendar(start_date='2024-01-01', end_date='2024-12-31')
    print(calendar_df)
    exit(0)

    #################################
    # Create Calendar
    #################################
    #calendar.createCalendar(start_date = '1900-01-01', end_date = datetime.now().date())
    calendar.createCalendar(start_date='1900-01-01', end_date='2026-12-31')
    calendar.deleteDataFromClickHouse(start_date='19000101', end_date='20241005')
    calendar.saveDateToClickHouse(start_date='19000101', end_date='20241005')

import pandas
from datetime import datetime
from dataIntegrator.common import CommonLib, CommonLogLib
from clickhouse_driver import Client as ClickhouseClient
from dataIntegrator.common.CommonParameters import CommonParameters
import pandas as pd
import sys

from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from datetime import timedelta

from dataIntegrator.modelService.commonService.CalendarService import CalendarService


class CalendarServiceTest(CommonLib.CommonLib):

    def load_calendar(self):
        calendar = CalendarService()
        calendar_df = calendar.load_calendar(start_date='2024-01-01', end_date='2024-12-31')
        print(calendar_df)


    def load_next_n_days_calendar(self):
        start_date = '2024-01-01'
        end_date = '2024-12-31'
        next_n_days = 10

        calendar = CalendarService()
        next_n_days_calendar_df = calendar.load_next_n_days_calendar(start_date, end_date, next_n_days)
        print(next_n_days_calendar_df)


    def load_next_n_working_days_calendar(self):

        # 示例调用
        start_date = '2024-01-01'
        end_date = '2024-12-31'
        next_n_days = 10

        calendar = CalendarService()
        working_days_df = calendar.load_next_n_working_days_calendar(start_date, end_date, next_n_days)
        print(working_days_df)


    def createCalendar(self):

        calendar = CalendarService()
        calendar.createCalendar(start_date='1900-01-01', end_date='2026-12-31')
        calendar.deleteDataFromClickHouse(start_date='19000101', end_date='20241005')
        calendar.saveDateToClickHouse(start_date='19000101', end_date='20241005')


if __name__ == '__main__':
    calendarServiceTest = CalendarServiceTest()

    #################################
    # Inquiry Calendar
    #################################
    calendarServiceTest.load_calendar()
    calendarServiceTest.load_next_n_days_calendar()
    calendarServiceTest.load_next_n_working_days_calendar()

    exit(0)

    #################################
    # Create Calendar
    #################################
    createCalendar()

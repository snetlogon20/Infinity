import pandas
from datetime import datetime

from dataIntegrator.analysisService.InquiryManager import InquiryManager
from dataIntegrator.common import CommonLib, CommonLogLib


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

        # 示例调用, 如果不直到结束日期，就赋值2099-12-31
        start_date = '2024-01-01'
        end_date = '2099-12-31'
        next_n_days = 10

        calendar = CalendarService()
        working_days_df = calendar.load_next_n_working_days_calendar(start_date, end_date, next_n_days)
        print(working_days_df)

    def get_last_date_from_calendar(self):

        # 示例调用
        start_date = '2024-01-01'
        end_date = '2024-12-31'
        next_n_days = 10

        calendar = CalendarService()
        formatted_last_date = calendar.get_last_date_from_calendar(start_date, end_date, next_n_days)
        print(formatted_last_date)

    def test_calculate_quarter(self):
        """快速测试calculate_quarter函数"""
        calendar = CalendarService()

        # 正常测试用例
        test_cases = [
            ("20260101", "2026Q1"),
            ("20260228", "2026Q1"),  # 马年正月十二
            ("20260331", "2026Q1"),
            ("20260401", "2026Q2"),
            ("20260630", "2026Q2"),
            ("20260701", "2026Q3"),
            ("20260930", "2026Q3"),
            ("20261001", "2026Q4"),
            ("20261231", "2026Q4"),
        ]

        print("正常测试用例:")
        for date_str, expected in test_cases:
            result = calendar.calculate_quarter(date_str)
            status = "✓" if result == expected else "✗"
            print(f"  {status} {date_str} -> {result} (期望: {expected})")

        # 异常测试用例
        error_cases = [
            "20261301",  # 无效月份
            "20260132",  # 无效日期
            "",  # 空字符串
            "abc",  # 非数字
        ]

        print("\n异常测试用例:")
        for date_str in error_cases:
            result = calendar.calculate_quarter(date_str)
            print(f"  {date_str} -> {result}")

    def createCalendar(self):

        calendar = CalendarService()
        calendar.createCalendar(start_date='1900-01-01', end_date='2026-12-31')
        calendar.deleteDataFromClickHouse(start_date='19000101', end_date='20241005')
        calendar.saveDateToClickHouse(start_date='19000101', end_date='20241005')


    def find_data_by_given_dataframe_and_date_offset(self):
        # 案例1 - 上来就能找到日期，然后计算偏移
        start_date = datetime.strptime('2025-01-02', '%Y-%m-%d')
        formatted_start_date = start_date.strftime('%Y-%m-%d')
        next_n_working_days = 10

        inquiryManager = InquiryManager()
        sql = f"select * from indexsysdb.df_akshare_spot_hist_sge where date>='{formatted_start_date}' order by date "
        original_dataFrame = inquiryManager.get_sql_dataset(sql)

        # 使用普通版本
        calendarService = CalendarService()
        result1 = calendarService.find_data_by_given_dataframe_and_date_offset(original_dataFrame, formatted_start_date,
                                                                               next_n_working_days)

        print(f"test case1: start date {start_date} + {next_n_working_days}: 普通偏移结果: {result1}")


        # 案例2 - 上来就能找不到到日期，然后计算偏移
        start_date = datetime.strptime('2025-01-01', '%Y-%m-%d')
        formatted_start_date = start_date.strftime('%Y-%m-%d')
        next_n_working_days = 9

        inquiryManager = InquiryManager()
        sql = f"select * from indexsysdb.df_akshare_spot_hist_sge where date>='{formatted_start_date}' order by date "
        original_dataFrame = inquiryManager.get_sql_dataset(sql)

        # 使用普通版本
        calendarService = CalendarService()
        result1 = calendarService.find_data_by_given_dataframe_and_date_offset(original_dataFrame, formatted_start_date,
                                                                               next_n_working_days)
        print(f"test case2: start date {start_date} + {next_n_working_days}: 普通偏移结果: {result1}")

        # 案例3 - 根据calendar table来计算偏移量
        start_date = '20260206'
        next_n_working_days = 9
        formatted_start_date = start_date

        inquiryManager = InquiryManager()
        sql = f"select * from indexsysdb.df_sys_calendar where trade_date>='{formatted_start_date}' and day_of_week not in ('Saturday','Sunday')  order by trade_date "
        original_dataFrame = inquiryManager.get_sql_dataset(sql)
        original_dataFrame.rename(columns={'trade_date': 'date'}, inplace=True)

        # 使用普通版本
        calendarService = CalendarService()
        result1 = calendarService.find_data_by_given_dataframe_and_date_offset(original_dataFrame, formatted_start_date,
                                                                               next_n_working_days)
        result1 = f"{str(result1)[:4]}-{str(result1)[4:6]}-{str(result1)[6:8]}"
        print(f"test case3: start date {start_date} + {next_n_working_days}: 普通偏移结果: {result1}")

if __name__ == '__main__':
    calendarServiceTest = CalendarServiceTest()

    #################################
    # Inquiry Calendar
    #################################
    # calendarServiceTest.load_calendar()
    # calendarServiceTest.load_next_n_days_calendar()
    # calendarServiceTest.load_next_n_working_days_calendar()

    #calendarServiceTest.get_last_date_from_calendar()
    calendarServiceTest.test_calculate_quarter()

    #calendarServiceTest.find_data_by_given_dataframe_and_date_offset()
    # exit(0)

    #################################
    # Create Calendar
    #################################
    # createCalendar()



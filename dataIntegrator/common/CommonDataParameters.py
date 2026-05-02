import os
import datetime

from dataIntegrator import CommonParameters
from dataIntegrator.common.MyTokens import MyTokens
from dataIntegrator.modelService.commonService.CalendarService import CalendarService


class CommonDataParameters():

    @classmethod
    def get_start_date(cls, days=360):
        """
        动态获取起始日期（从今天往前推算指定天数）

        参数:
        - days: 往前推算的天数，默认360天

        返回:
        - start_date: 起始日期字符串，格式 'YYYYMMDD'
        """
        calendarService = CalendarService()
        return calendarService.calculate_T_minus_n_days(CommonParameters.today, days=days)

    STOCK_LIST=[
            {'ts_code': '002093.SZ', 'name': '国脉科技'},
            {'ts_code': '600490.SH', 'name': '鹏欣资源'},
            {'ts_code': '000902.SZ', 'name': '新洋丰'},
            {'ts_code': '601368.SH', 'name': '绿城水务'},
            {'ts_code': '603839.SH', 'name': '安正时尚'},
            {'ts_code': '000546.SZ', 'name': '金圆股份'},
            {'ts_code': '600470.SH', 'name': '六国化工'},
            {'ts_code': '600519.SH', 'name': '贵州茅台'},
            {'ts_code': '688498.SH', 'name': '源杰科技'},
        ]

    #US_STOCK_LIST=["SPY", "C", "JPM", "AAPL","NVDA","GS","MS","GE"]
    #US_STOCK_LIST=["C", "JPM", "AAPL", "NVDA", "MSFT"]
    US_STOCK_LIST = [
        "SPY", "C", "JPM", "AAPL", "NVDA", "GS", "MS", "GE",  # 你原有的代码
        "MSFT", "AVGO", "ADBE", "UNH", "JNJ", "LLY", "PFE", "MRK", "AMZN",
        "TSLA", "MCD", "NFLX", "HD", "GOOGL", "META", "DIS", "CMCSA", "T",
        "CAT", "UPS", "BA", "HON", "PG", "KO", "PEP", "WMT", "COST", "XOM",
        "CVX", "COP", "SLB", "EOG", "AMT", "PLD", "EQIX", "SPG", "O", "NEE",
        "DUK", "SO", "D", "EXC", "LIN", "APD", "FCX", "NEM", "SHW"
    ]

    CN_INDEX_LIST = [
        '000001.SH',  # 上证指数
        '399001.SZ',  # 深证成指
        '000300.SH',  # 沪深300
        '000905.SH',  # 中证500
        '000852.SH',  # 中证1000
        '399006.SZ',  # 创业板指
    ]



"""
收益率比较器：比较 SHIBOR、国债收益率、可转债收益率
支持批量日期分析，输出PDF报告（含专业金融分析）
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime
from calendar import monthrange
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.modelService.bonds.BondYieldComparator import BondYieldComparator
from dataIntegrator.modelService.commonService.CalendarService import CalendarService

logger = CommonLib.logger


class BondYieldComparatorTest:
    def __init__(self):
        pass

if __name__ == '__main__':
    comparator = BondYieldComparator()

    # 批量日期分析：输入日期列表，生成一份 PDF 报告
    calendarService = CalendarService()
    start_date = calendarService.calculate_T_minus_n_days(CommonParameters.today, days=360)
    end_date = CommonParameters.today

    # 生成 start_date ~ end_date 之间各月的月底日期，最后一天为 end_date
    start_dt = datetime.strptime(start_date, '%Y%m%d')
    end_dt = datetime.strptime(end_date, '%Y%m%d')

    trade_dates = []
    year, month = start_dt.year, start_dt.month
    while True:
        last_day = monthrange(year, month)[1]
        month_end = datetime(year, month, last_day)
        month_end_str = month_end.strftime('%Y%m%d')

        if month_end_str >= start_date and month_end_str < end_date:
            trade_dates.append(month_end_str)
        elif month_end_str >= end_date:
            break

        month += 1
        if month > 12:
            month = 1
            year += 1

    trade_dates.append(end_date)
    logger.info(f"生成交易日期列表（月底+end_date）: {trade_dates}")

    all_shibor_treasury, all_convertible = comparator.run(
        trade_dates=trade_dates
    )

    logger.info(f"处理完成，共 {len(all_shibor_treasury)} 个有效日期")



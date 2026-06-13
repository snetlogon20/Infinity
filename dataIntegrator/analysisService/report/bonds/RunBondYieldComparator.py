"""
收益率比较报告生成器 - 批量运行入口

仿照 RunSMLAnalysisReport 的结构，将 BondYieldComparatorTest.py 的业务逻辑
封装为可被 run_reports.bat 调用的独立脚本。
"""

from datetime import datetime
from calendar import monthrange

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.common.ReportJobLogger import ReportJobLogger
from dataIntegrator.modelService.bonds.BondYieldComparator import BondYieldComparator
from dataIntegrator.modelService.commonService.CalendarService import CalendarService

logger = CommonLib.logger


class RunBondYieldComparator:
    """收益率比较报告运行器"""

    def __init__(self):
        self.comparator = BondYieldComparator()
        self.job_logger = ReportJobLogger()

    def generate_report(self, start_date=None, end_date=None):
        """
        生成收益率比较报告（SHIBOR / 国债 / 可转债）

        参数:
        - start_date: 开始日期 (格式: 'YYYYMMDD')，默认 T-360
        - end_date: 结束日期 (格式: 'YYYYMMDD')，默认 today
        """
        if end_date is None:
            end_date = CommonParameters.today

        if start_date is None:
            calendarService = CalendarService()
            start_date = calendarService.calculate_T_minus_n_days(end_date, days=360)

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
        logger.info("=" * 80)
        logger.info("开始生成 收益率比较报告 (SHIBOR / 国债 / 可转债)")
        logger.info(f"   日期范围: {start_date} ~ {end_date}")
        logger.info(f"   交易日期列表（月底+end_date）: {trade_dates}")
        logger.info("=" * 80)

        self.job_logger.start_job('BondYieldComparator', 'BondYield',
                                  params={'start_date': start_date, 'end_date': end_date,
                                          'trade_date_count': len(trade_dates)})
        try:
            all_shibor_treasury, all_convertible = self.comparator.run(
                trade_dates=trade_dates
            )
            records_count = len(all_shibor_treasury) if all_shibor_treasury is not None else 0
            self.job_logger.end_job_success(records_processed=records_count)
            logger.info("收益率比较报告 生成成功")
            logger.info(f"   共 {records_count} 个有效日期")
        except Exception as e:
            logger.error(f"收益率比较报告 生成失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.job_logger.end_job_failed(str(e), traceback.format_exc())
            raise


if __name__ == "__main__":
    runner = RunBondYieldComparator()
    runner.generate_report()

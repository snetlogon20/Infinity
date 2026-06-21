"""
可转债量化管理报告生成器 - 批量运行入口

仿照 RunSMLAnalysisReport 的结构，将 ConvertibleBondManagerReportTest.py 的业务逻辑
封装为可被 run_reports.bat 调用的独立脚本。
"""

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.common.ReportJobLogger import ReportJobLogger
from dataIntegrator.modelService.bonds.ConvertibleBondManager import ConvertibleBondManager
from dataIntegrator.modelService.bonds.ConvertibleBondManagerReport import ConvertibleBondManagerReport
from dataIntegrator.modelService.commonService.CalendarService import CalendarService

logger = CommonLib.logger


class RunConvertibleBondManagerReport:
    """可转债量化管理报告运行器"""

    def __init__(self):
        self.report = ConvertibleBondManagerReport()
        self.job_logger = ReportJobLogger()

    def generate_report(self, start_date=None, end_date=None):
        """
        生成可转债量化管理报告

        参数:
        - start_date: 开始日期 (格式: 'YYYYMMDD')，默认 T-90
        - end_date: 结束日期 (格式: 'YYYYMMDD')，默认 today
        """
        if end_date is None:
            end_date = CommonParameters.today

        if start_date is None:
            calendarService = CalendarService()
            start_date = calendarService.calculate_T_minus_n_days(end_date, days=90)

        logger.info("=" * 80)
        logger.info("开始生成 可转债量化管理报告")
        logger.info(f"   日期范围: {start_date} ~ {end_date}")
        logger.info("=" * 80)

        self.job_logger.start_job('ConvertibleBondManagerReport', 'ConvertibleBond',
                                  params={'start_date': start_date, 'end_date': end_date})
        try:
            # 1. 先刷新可转债指标数据（计算并入库）
            logger.info("=" * 60)
            logger.info(f"步骤1: 刷新可转债指标数据 ({start_date} ~ {end_date})")
            logger.info("=" * 60)
            manager = ConvertibleBondManager()
            manager.save_calculated_bonds(start_date, end_date)

            # 2. 再生成报表
            logger.info("=" * 60)
            logger.info(f"步骤2: 生成可转债量化管理报告 ({start_date} ~ {end_date})")
            logger.info("=" * 60)
            self.report.run(start_date, end_date)

            self.job_logger.end_job_success()
            logger.info("可转债量化管理报告 生成成功")
        except Exception as e:
            logger.error(f"可转债量化管理报告 生成失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.job_logger.end_job_failed(str(e), traceback.format_exc())
            raise


if __name__ == "__main__":
    runner = RunConvertibleBondManagerReport()
    runner.generate_report()

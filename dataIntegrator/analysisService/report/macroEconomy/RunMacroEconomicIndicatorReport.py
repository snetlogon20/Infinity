"""
宏观经济指标报告生成器 - 批量运行入口

仿照 RunConvertibleBondManagerReport 的结构，将 MacroEconomicIndicatorReportTest.py 的业务逻辑
封装为可被 run_reports.bat 调用的独立脚本。
"""

from dataIntegrator import CommonLib
from dataIntegrator.common.ReportJobLogger import ReportJobLogger
from dataIntegrator.modelService.macroEconomy.MacroEconomicIndicatorReport import MacroEconomicIndicatorReport

logger = CommonLib.logger


class RunMacroEconomicIndicatorReport:
    """宏观经济指标报告生成运行器"""

    def __init__(self):
        self.report = MacroEconomicIndicatorReport()
        self.job_logger = ReportJobLogger()

    def generate_report(self, start_date=None, end_date=None):
        """
        生成宏观经济指标环比分析报告（PDF）

        参数:
        - start_date: 保留兼容，暂未使用
        - end_date: 保留兼容，暂未使用
        """
        logger.info("=" * 80)
        logger.info("开始生成 宏观经济指标环比分析报告")
        logger.info("=" * 80)

        self.job_logger.start_job('MacroEconomicIndicatorReport', 'MacroEconomy', params={})
        try:
            pdf_path = self.report.run()
            self.job_logger.end_job_success()
            logger.info("宏观经济指标环比分析报告 生成成功")
            logger.info(f"   报告路径: {pdf_path}")
        except Exception as e:
            logger.error(f"宏观经济指标环比分析报告 生成失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.job_logger.end_job_failed(str(e), traceback.format_exc())
            raise

    def run(self):
        """生成宏观经济指标环比分析报告 - 无参数入口"""
        self.generate_report()


if __name__ == "__main__":
    RunMacroEconomicIndicatorReport().run()

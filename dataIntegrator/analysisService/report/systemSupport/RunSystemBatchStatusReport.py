"""
系统批量任务状态报告运行器
仿照 RunSMLAnalysisReport 结构，调用 SystemBatchStatusReport 生成 PDF 报告。
"""
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.systemSupport.SystemBatchStatusReport import SystemBatchStatusReport

logger = CommonLib.logger


class RunSystemBatchStatusReport:
    """系统批量任务状态报告运行器"""

    def __init__(self):
        self.reporter = SystemBatchStatusReport()

    def generate_report(self):
        """生成系统批量任务状态报告（默认查询当天）"""
        logger.info("=" * 80)
        logger.info("开始生成 系统批量任务状态报告")
        logger.info("=" * 80)

        try:
            pdf_path = self.reporter.generate_report()
            logger.info(f"系统批量任务状态报告 生成成功: {pdf_path}")
        except Exception as e:
            logger.error(f"系统批量任务状态报告 生成失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise


if __name__ == "__main__":
    runner = RunSystemBatchStatusReport()
    runner.generate_report()

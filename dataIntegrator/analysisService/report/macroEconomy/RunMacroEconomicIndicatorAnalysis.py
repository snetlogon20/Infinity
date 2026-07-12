"""
宏观经济指标数据生成器 - 批量运行入口

仿照 RunConvertibleBondManagerReport 的结构，将 MacroEconomicIndicatorAnalysisTest.py 的业务逻辑
封装为可被 run_reports.bat 调用的独立脚本。
"""

from dataIntegrator import CommonLib
from dataIntegrator.common.ReportJobLogger import ReportJobLogger
from dataIntegrator.modelService.macroEconomy.MacroEconomicIndicatorAnalysis import MacroEconomicIndicatorAnalysis

logger = CommonLib.logger


class RunMacroEconomicIndicatorAnalysis:
    """宏观经济指标数据生成运行器"""

    def __init__(self):
        self.analysis = MacroEconomicIndicatorAnalysis()
        self.job_logger = ReportJobLogger()

    def generate_report(self, start_date=None, end_date=None):
        """
        生成宏观经济指标数据（拉取 → 填充 → 计算环比 → 写入ClickHouse）

        参数:
        - start_date: 保留兼容，暂未使用
        - end_date: 保留兼容，暂未使用
        """
        logger.info("=" * 80)
        logger.info("开始生成 宏观经济指标数据")
        logger.info("=" * 80)

        self.job_logger.start_job('MacroEconomicIndicatorAnalysis', 'MacroEconomy', params={})
        try:
            df = self.analysis.generate_macro_indicator_data()
            records_count = len(df) if df is not None else 0
            self.job_logger.end_job_success(records_processed=records_count)
            logger.info("宏观经济指标数据 生成成功")
            logger.info(f"   共 {records_count} 条记录")
        except Exception as e:
            logger.error(f"宏观经济指标数据 生成失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.job_logger.end_job_failed(str(e), traceback.format_exc())
            raise

    def run(self):
        """生成宏观经济指标数据 - 无参数入口"""
        self.generate_report()


if __name__ == "__main__":
    RunMacroEconomicIndicatorAnalysis().run()

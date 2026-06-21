"""
PD (违约概率) 分析报告生成器

本文件用于批量生成 PD (Probability of Default) 分析报告，
支持按板块分组生成独立报告。
"""

from dataIntegrator import CommonLib
from dataIntegrator.common.CommonDataParameters import CommonDataParameters
from dataIntegrator.common.ReportJobLogger import ReportJobLogger
from dataIntegrator.modelService.financialAnalysis.PDAnalysisTest import PDAnalysisTest
from dataIntegrator.modelService.financialAnalysis.PDAnalysisReport import PDAnalysisReport

logger = CommonLib.logger


class RunPDAnalysisReport:
    """PD 违约概率分析报告生成器"""

    def __init__(self):
        self.pdAnalysisTest = PDAnalysisTest()
        self.pdAnalysisReport = PDAnalysisReport()
        self.job_logger = ReportJobLogger()

    def run_all_stocks_report(self, start_year="2020"):
        """
        生成全量股票合并 PD 分析报告（分析 + 统一报告）

        Args:
            start_year (str): 起始年份

        Returns:
            str: PDF 报告路径
        """
        logger.info("=" * 80)
        logger.info("📊 开始生成全量股票 PD 分析综合报告")
        logger.info("=" * 80)

        self.job_logger.start_job('PDAnalysisReport', 'ALL_STOCKS',
                                  params={'start_year': start_year})

        try:
            # 先批量分析入库
            self.pdAnalysisTest.run_all_analysis(start_year=start_year, generate_reports=False)

            # 再生成统一 PDF 报告
            report_path = self.pdAnalysisReport.generate_all_stocks_report()

            logger.info(f"\n✅ 全量股票 PD 分析综合报告生成成功: {report_path}")
            self.job_logger.end_job_success(records_processed=len(CommonDataParameters.STOCK_LIST))

            return report_path

        except Exception as e:
            logger.error(f"❌ 全量股票 PD 分析报告生成失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.job_logger.end_job_failed(str(e), traceback.format_exc())
            return None

    def run_sector_reports(self, start_year="2020"):
        """
        按板块分组，为每个板块生成独立 PD 分析报告

        Args:
            start_year (str): 起始年份

        Returns:
            list: 各板块报告路径列表
        """
        logger.info("=" * 80)
        logger.info("📊 开始按板块生成 PD 分析报告")
        logger.info("=" * 80)

        self.job_logger.start_job('PDAnalysisReport', 'BY_SECTOR',
                                  params={'start_year': start_year})

        try:
            # 按板块分析 + 生成报告（内置在 run_analysis_by_sector 中）
            self.pdAnalysisTest.run_analysis_by_sector(start_year=start_year, generate_reports=True)

            logger.info(f"\n✅ 按板块 PD 分析报告全部生成完成")
            self.job_logger.end_job_success()

            return True

        except Exception as e:
            logger.error(f"❌ 按板块 PD 分析报告生成失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.job_logger.end_job_failed(str(e), traceback.format_exc())
            return None

    def run_batch_reports(self, start_year="2020"):
        """
        批量生成 PD 分析报告（全量 + 按板块）

        Args:
            start_year (str): 起始年份
        """
        logger.info("\n" + "=" * 80)
        logger.info("🎯 PD 违约概率分析 批量报告生成 开始")
        logger.info(f"   起始年份: {start_year}")
        logger.info(f"   股票数量: {len(CommonDataParameters.STOCK_LIST)}")
        logger.info("=" * 80)

        # ---- 模式1: 全量股票综合报告 ----
        logger.info("\n--- [1/2] 全量股票综合报告 ---")
        all_stocks_path = self.run_all_stocks_report(start_year=start_year)
        if all_stocks_path:
            logger.info(f"   全量报告路径: {all_stocks_path}")

        # ---- 模式2: 按板块分组报告 ----
        logger.info("\n--- [2/2] 按板块分组报告 ---")
        self.run_sector_reports(start_year=start_year)

        logger.info("\n" + "=" * 80)
        logger.info("🎉 PD 违约概率分析 批量报告生成 全部完成！")
        logger.info(f"📁 报告输出目录: {self.pdAnalysisReport.output_dir}")
        logger.info("=" * 80)


if __name__ == "__main__":
    """
    批量生成 PD (违约概率) 分析报告

    执行流程:
    1. 全量股票综合报告 — 所有股票合并为一个 PDF
    2. 按板块分组报告 — 每个板块（高科技、银行、化工...）生成独立 PDF
    """
    runReport = RunPDAnalysisReport()

    # 执行批量报告生成
    runReport.run_batch_reports(start_year="2020")

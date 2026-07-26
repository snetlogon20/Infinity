"""
投资组合指标分析报告生成器

本文件用于批量生成投资组合指标分析报告，支持多种股票组合类型
"""

import os

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.common.CommonDataParameters import CommonDataParameters
from dataIntegrator.common.ReportJobLogger import ReportJobLogger
from dataIntegrator.modelService.financialAnalysis.PortfolioMetricsAnalysisTest import PortfolioMetricsAnalysisTest
from dataIntegrator.modelService.financialAnalysis.PortfolioMetricsAnalysisReport import PortfolioMetricsAnalysisReport

logger = CommonLib.logger


class RunPortfolioMetricsAnalysisReport:
    """投资组合指标分析报告生成器"""

    def __init__(self):
        self.job_logger = ReportJobLogger()

    def run(self):
        """批量生成投资组合指标分析报告"""
        portfolioMetricsAnalysisTest = PortfolioMetricsAnalysisTest()
        portfolioMetricsAnalysisReport = PortfolioMetricsAnalysisReport()

        # 定义报告配置（参考 PortfolioMetricsAnalysisTest）
        report_configs = [
            {
                "name": "美国科技股",
                "stock_type": "us_tech",
                "start_date": CommonDataParameters.get_start_date(days=720),
                "end_date": CommonParameters.today,
                "interest_country": "US",
                "market_type": "US"
            },
            {
                "name": "美国科技股",
                "stock_type": "us_tech",
                "start_date": CommonDataParameters.get_start_date(days=360),
                "end_date": CommonParameters.today,
                "interest_country": "US",
                "market_type": "US"
            },
            {
                "name": "美国科技股",
                "stock_type": "us_tech",
                "start_date": CommonDataParameters.get_start_date(days=60),
                "end_date": CommonParameters.today,
                "interest_country": "US",
                "market_type": "US"
            },
            {
                "name": "美国金融股",
                "stock_type": "us_finance",
                "start_date": CommonDataParameters.get_start_date(days=720),
                "end_date": CommonParameters.today,
                "interest_country": "US",
                "market_type": "US"
            },
            {
                "name": "美国混合股票",
                "stock_type": "us_mixed",
                "start_date": CommonDataParameters.get_start_date(days=720),
                "end_date": CommonParameters.today,
                "interest_country": "US",
                "market_type": "US"
            },
            {
                "name": "美国自定义组合",
                "stock_type": "us_custom",
                "start_date": CommonDataParameters.get_start_date(days=360),
                "end_date": CommonParameters.today,
                "interest_country": "US",
                "market_type": "US"
            },
            {
                "name": "中国蓝筹股组合",
                "stock_type": "cn_blue_chip",
                "start_date": CommonDataParameters.get_start_date(days=720),
                "end_date": CommonParameters.today,
                "interest_country": "CN",
                "market_type": "CN"
            },
            {
                "name": "中国科技股组合",
                "stock_type": "cn_tech",
                "start_date": CommonDataParameters.get_start_date(days=720),
                "end_date": CommonParameters.today,
                "interest_country": "CN",
                "market_type": "CN"
            },
            {
                "name": "中国大消费组合",
                "stock_type": "cn_consumer",
                "start_date": CommonDataParameters.get_start_date(days=720),
                "end_date": CommonParameters.today,
                "interest_country": "CN",
                "market_type": "CN"
            },
            {
                "name": "中国金融股组合",
                "stock_type": "cn_financial",
                "start_date": CommonDataParameters.get_start_date(days=720),
                "end_date": CommonParameters.today,
                "interest_country": "CN",
                "market_type": "CN"
            },
            {
                "name": "中国能源与制造业组合",
                "stock_type": "cn_energy",
                "start_date": CommonDataParameters.get_start_date(days=720),
                "end_date": CommonParameters.today,
                "interest_country": "CN",
                "market_type": "CN"
            },
            {
                "name": "中国自定义股票组合",
                "stock_type": "cn_custom",
                "start_date": CommonDataParameters.get_start_date(days=720),
                "end_date": CommonParameters.today,
                "interest_country": "CN",
                "market_type": "CN"
            },
            {
                "name": "中国上证ETF50组合",
                "stock_type": "cn_sse_50",
                "start_date": CommonDataParameters.get_start_date(days=720),
                "end_date": CommonParameters.today,
                "interest_country": "CN",
                "market_type": "CN"
            },
        ]

        all_results = []

        for idx, config in enumerate(report_configs, 1):
            logger.info("\n" + "=" * 80)
            logger.info(f" 开始生成第 {idx}/{len(report_configs)} 个投资组合指标分析报告")
            logger.info(f"   报告名称: {config['name']}")
            logger.info("=" * 80)

            start_date = config.get("start_date")
            end_date = config.get("end_date")
            if end_date is None:
                end_date = CommonParameters.today

            self.job_logger.start_job(
                'PortfolioMetricsAnalysisReport', 'PortfolioMetrics',
                params={
                    'report_name': config['name'],
                    'stock_type': config.get('stock_type'),
                    'start_date': start_date,
                    'end_date': end_date,
                }
            )

            try:
                # 执行滚动回测分析
                results_df = portfolioMetricsAnalysisTest.run_portfolio_metrics_analysis(
                    stock_type=config["stock_type"],
                    start_date_fixed=None,
                    end_date_start=start_date,
                    end_date_end=end_date,
                    window_days=360,
                    risk_free_rate=None
                )

                # 导出到Excel（带资产组合名称）
                excel_path, pdf_path = portfolioMetricsAnalysisTest.export_to_excel(
                    results_df,
                    stock_type=config["stock_type"],
                    case_name=config['name'],
                    output_dir=os.path.join(CommonParameters.outBoundPath, "report", "PortfolioMetricsAnalysis")
                )

                all_results.append({
                    'name': config['name'],
                    'market_type': config['market_type'],
                    'stock_type': config['stock_type'],
                    'excel_path': excel_path,
                    'pdf_path': pdf_path,
                    'start_date': start_date,
                    'end_date': end_date,
                    'total_records': len(results_df)
                })

                self.job_logger.end_job_success(records_processed=len(results_df))

                logger.info(f"✅ 第 {idx} 个案例分析完成")
                logger.info(f"   Excel 路径: {excel_path}")
                if pdf_path:
                    logger.info(f"   PDF 路径: {pdf_path}")
                logger.info(f"   总记录数: {len(results_df)}")

            except Exception as e:
                logger.error(f" 第 {idx} 个分析失败: {config['name']}")
                logger.error(f"   错误信息: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                self.job_logger.end_job_failed(str(e), traceback.format_exc())
                continue

        if all_results:
            logger.info("\n" + "=" * 80)
            logger.info("✅ 投资组合指标分析完成")
            logger.info(f"📊 包含 {len(all_results)} 个测试案例")
        else:
            logger.warning("⚠️ 没有成功的测试案例")

        logger.info("\n" + "=" * 80)
        logger.info(" 所有投资组合指标分析任务完成！")
        logger.info(f"📁 报告输出目录: {portfolioMetricsAnalysisReport.output_dir}")
        logger.info("=" * 80)

        return all_results


if __name__ == "__main__":
    RunPortfolioMetricsAnalysisReport().run()

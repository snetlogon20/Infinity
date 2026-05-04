"""
投资组合指标分析报告生成器

本文件用于批量生成投资组合指标分析报告,支持多种股票组合类型
"""

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.common.CommonDataParameters import CommonDataParameters
from dataIntegrator.modelService.financialAnalysis.PortfolioMetricsAnalysisTest import PortfolioMetricsAnalysisTest
from dataIntegrator.modelService.financialAnalysis.PortfolioMetricsAnalysisReport import PortfolioMetricsAnalysisReport

logger = CommonLib.logger


class RunPortfolioMetricsAnalysisReport:
    """投资组合指标分析报告生成器"""

    def __init__(self):
        self.portfolioMetricsAnalysisTest = PortfolioMetricsAnalysisTest()
        self.portfolioMetricsAnalysisReport = PortfolioMetricsAnalysisReport()

    def generate_report(self, stock_type="cn_blue_chip", start_date=None, end_date=None,
                       case_name=None):
        """
        生成单个投资组合指标分析报告

        参数:
        - stock_type: 股票类型
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')
        - case_name: 案例名称

        返回:
        - results: 分析结果字典
        """
        if end_date is None:
            end_date = CommonParameters.today

        # 执行滚动回测分析
        results_df = self.portfolioMetricsAnalysisTest.run_portfolio_metrics_analysis(
            stock_type=stock_type,
            start_date_fixed=None,
            end_date_start=start_date,
            end_date_end=end_date,
            window_days=360,
            risk_free_rate=None
        )

        return {
            'name': case_name,
            'market_type': 'CN',
            'stock_type': stock_type,
            'results_df': results_df,
            'start_date': start_date,
            'end_date': end_date,
            'total_records': len(results_df)
        }

    def run_batch_reports(self, report_configs):
        """
        批量生成投资组合指标分析报告

        参数:
        - report_configs: 报告配置列表

        返回:
        - all_results: 所有分析结果列表
        """
        all_results = []

        for idx, config in enumerate(report_configs, 1):
            logger.info("\n" + "=" * 80)
            logger.info(f" 开始生成第 {idx}/{len(report_configs)} 个投资组合指标分析报告")
            logger.info(f"   报告名称: {config['name']}")
            logger.info("=" * 80)

            try:
                start_date = config.get("start_date")
                end_date = config.get("end_date")

                if end_date is None:
                    end_date = CommonParameters.today

                result = self.generate_report(
                    stock_type=config["stock_type"],
                    start_date=start_date,
                    end_date=end_date,
                    case_name=config["name"]
                )

                all_results.append(result)

                logger.info(f"✅ 第 {idx} 个案例分析完成")
                logger.info(f"   总记录数: {result['total_records']}")

            except Exception as e:
                logger.error(f" 第 {idx} 个分析失败: {config['name']}")
                logger.error(f"   错误信息: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                continue

        # 生成综合报告
        if all_results:
            logger.info("\n" + "=" * 80)
            logger.info(" 开始生成投资组合指标综合分析研究报告")
            logger.info("=" * 80)

            comprehensive_pdf_path = self.portfolioMetricsAnalysisReport.generate_comprehensive_pdf(
                all_results=all_results,
                report_title="投资组合指标综合分析研究报告"
            )

            logger.info(f"\n✅ 综合分析报告生成成功: {comprehensive_pdf_path}")
            logger.info(f"📊 包含 {len(all_results)} 个测试案例")
        else:
            logger.warning("⚠️ 没有成功的测试案例，无法生成综合报告")

        logger.info("\n" + "=" * 80)
        logger.info("🎉 所有投资组合指标分析任务完成！")
        logger.info(f" 报告输出目录: {self.portfolioMetricsAnalysisReport.output_dir}")
        logger.info("=" * 80)

        return all_results


if __name__ == "__main__":
    """
    使用示例 - 批量生成投资组合指标分析报告
    """
    runReport = RunPortfolioMetricsAnalysisReport()

    # ========================================
    # 配置测试案例
    # ========================================
    report_configs = [
        {
            "name": "美国科技股",
            "stock_type": "us_tech",
            "start_date": "20250101",
            "end_date": None,
            "interest_country": "US"
        },
        {
            "name": "美国金融股",
            "stock_type": "us_finance",
            "start_date": "20250101",
            "end_date": None,
            "interest_country": "US"
        },
        {
            "name": "美国混合股票",
            "stock_type": "us_mixed",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "US"
        },
        {
            "name": "美国自定义组合",
            "stock_type": "us_custom",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "US"
        },
        {
            "name": "中国蓝筹股组合",
            "stock_type": "cn_blue_chip",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN"
        },
        {
            "name": "中国科技股组合",
            "stock_type": "cn_tech",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN"
        },
        {
            "name": "中国大消费组合",
            "stock_type": "cn_consumer",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN"
        },
        {
            "name": "中国金融股组合",
            "stock_type": "cn_financial",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN"
        },
        {
            "name": "中国能源与制造业组合",
            "stock_type": "cn_energy",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN"
        },
        {
            "name": "中国自定义股票组合",
            "stock_type": "cn_custom",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN"
        }
    ]

    # 执行批量报告生成
    all_results = runReport.run_batch_reports(report_configs)

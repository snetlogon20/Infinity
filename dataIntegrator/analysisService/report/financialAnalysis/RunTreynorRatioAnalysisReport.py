"""
特雷诺比率 (Treynor Ratio) 分析报告生成器

本文件用于批量生成特雷诺比率分析报告，支持多种股票组合类型
"""

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.common.CommonDataParameters import CommonDataParameters
from dataIntegrator.modelService.financialAnalysis.TreynorRatioAnalysisTest import TreynorRatioAnalysisTest
from dataIntegrator.modelService.financialAnalysis.TreynorRatioAnalysisReport import TreynorRatioAnalysisReport

logger = CommonLib.logger


class RunTreynorRatioAnalysisReport:
    """特雷诺比率分析报告生成器"""

    def __init__(self):
        self.treynorAnalysisTest = TreynorRatioAnalysisTest()
        self.treynorAnalysisReport = TreynorRatioAnalysisReport()

    def generate_report(self, asset_type="cn_blue_chip", start_date=None, end_date=None,
                       interest_country=None, case_name=None):
        """
        生成单个特雷诺比率分析报告

        参数:
        - asset_type: 资产类型
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')
        - interest_country: 利率国家 ('US' 或 'CN')
        - case_name: 案例名称

        返回:
        - results: 分析结果字典
        """
        if end_date is None:
            end_date = CommonParameters.today

        results = self.treynorAnalysisTest.run_treynor_analysis(
            asset_type=asset_type,
            start_date=start_date,
            end_date=end_date,
            risk_free_rate=None,
            interest_country=interest_country,
            case_name=case_name
        )

        return {
            'name': case_name,
            'market_type': results['market_type'],
            'chart_path': results['plot_path'],
            'betas': results['betas'],
            'expected_returns': results['expected_returns'],
            'treynor_ratios': results['treynor_ratios'],
            'risk_free_rate': results['risk_free_rate'],
            'market_return': results['market_return'],
            'market_risk_premium': results['market_risk_premium'],
            'market_symbol': results['market_symbol'],
            'start_date': start_date,
            'end_date': end_date
        }

    def run_batch_reports(self, report_configs):
        """
        批量生成特雷诺比率分析报告

        参数:
        - report_configs: 报告配置列表

        返回:
        - all_results: 所有分析结果列表
        """
        all_results = []

        for idx, config in enumerate(report_configs, 1):
            logger.info("\n" + "=" * 80)
            logger.info(f" 开始生成第 {idx}/{len(report_configs)} 个特雷诺比率分析报告")
            logger.info(f"   报告名称: {config['name']}")
            logger.info("=" * 80)

            try:
                start_date = config.get("start_date")
                end_date = config.get("end_date")

                if end_date is None:
                    end_date = CommonParameters.today

                result = self.generate_report(
                    asset_type=config["asset_type"],
                    start_date=start_date,
                    end_date=end_date,
                    interest_country=config["interest_country"],
                    case_name=config["name"]
                )

                all_results.append(result)

                logger.info(f"✅ 第 {idx} 个案例分析完成")
                logger.info(f"   图表路径: {result['chart_path']}")

            except Exception as e:
                logger.error(f" 第 {idx} 个分析失败: {config['name']}")
                logger.error(f"   错误信息: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                continue

        # 生成综合报告
        if all_results:
            logger.info("\n" + "=" * 80)
            logger.info(" 开始生成特雷诺比率综合分析研究报告")
            logger.info("=" * 80)

            comprehensive_pdf_path = self.treynorAnalysisReport.generate_comprehensive_pdf(
                all_results=all_results,
                report_title="特雷诺比率 (Treynor Ratio) 综合分析研究报告"
            )

            logger.info(f"\n✅ 综合分析报告生成成功: {comprehensive_pdf_path}")
            logger.info(f" 包含 {len(all_results)} 个测试案例")
        else:
            logger.warning("️ 没有成功的测试案例，无法生成综合报告")

        logger.info("\n" + "=" * 80)
        logger.info(" 所有特雷诺比率分析任务完成！")
        logger.info(f" 报告输出目录: {self.treynorAnalysisReport.output_dir}")
        logger.info("=" * 80)

        return all_results


if __name__ == "__main__":
    """
    使用示例 - 批量生成特雷诺比率分析报告
    """
    runReport = RunTreynorRatioAnalysisReport()

    # ========================================
    # 配置测试案例
    # ========================================
    report_configs = [
        {
            "name": "美国科技股",
            "asset_type": "us_tech",
            "start_date": "20250101",
            "end_date": None,
            "interest_country": "US"
        },
        {
            "name": "美国金融股",
            "asset_type": "us_finance",
            "start_date": "20250101",
            "end_date": None,
            "interest_country": "US"
        },
        {
            "name": "美国混合股票",
            "asset_type": "us_mixed",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "US"
        },
        {
            "name": "美国自定义组合",
            "asset_type": "us_custom",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "US"
        },
        {
            "name": "中国蓝筹股组合",
            "asset_type": "cn_blue_chip",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN"
        },
        {
            "name": "中国科技股组合",
            "asset_type": "cn_tech",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN"
        },
        {
            "name": "中国大消费组合",
            "asset_type": "cn_consumer",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN"
        },
        {
            "name": "中国金融股组合",
            "asset_type": "cn_financial",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN"
        },
        {
            "name": "中国能源与制造业组合",
            "asset_type": "cn_energy",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN"
        },
        {
            "name": "中国自定义股票组合",
            "asset_type": "cn_custom",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN"
        }
    ]

    # 执行批量报告生成
    all_results = runReport.run_batch_reports(report_configs)

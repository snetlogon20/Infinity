"""
CML 分析报告生成器 - 股票 + 商品混合分析

本文件用于批量生成 CML（资本市场线）分析报告，支持股票与商品的混合投资组合
"""

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.common.CommonDataParameters import CommonDataParameters
from dataIntegrator.common.ReportJobLogger import ReportJobLogger
from dataIntegrator.modelService.financialAnalysis.CMLAnalysisWithCommoditiesTest import CMLAnalysisWithCommoditiesTest
from dataIntegrator.modelService.financialAnalysis.CMLAnalysisReport import CMLAnalysisReport

logger = CommonLib.logger


class RunCMLAnalysisWithCommoditiesReport:
    """CML 分析报告生成器 - 支持商品"""

    def __init__(self):
        self.cmlTest = CMLAnalysisWithCommoditiesTest()
        self.cmlAnalysisReport = CMLAnalysisReport()
        self.job_logger = ReportJobLogger()

    def generate_report(self, stock_type="us_tech", start_date=None, end_date=None,
                       interest_country=None, case_name=None, include_commodities=None):
        """
        生成单个 CML 分析报告（含商品）

        参数:
        - stock_type: 股票类型
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')
        - interest_country: 利率国家 ('US' 或 'CN')
        - case_name: 案例名称
        - include_commodities: 商品配置字典，例如 {'GC': 'COMEX黄金'}

        返回:
        - results: 分析结果字典
        """
        if end_date is None:
            end_date = CommonParameters.today

        results = self.cmlTest.run_cml_with_commodities(
            stock_type=stock_type,
            start_date=start_date,
            end_date=end_date,
            risk_free_rate=None,
            interest_country=interest_country,
            case_name=case_name,
            include_commodities=include_commodities
        )

        return {
            'name': case_name,
            'market_type': results['market_type'],
            'chart_path': results['plot_path'],
            'expected_returns': results['expected_returns'],
            'volatilities': results['volatilities'],
            'max_sharpe_return': results['max_sharpe_return'],
            'max_sharpe_volatility': results['max_sharpe_volatility'],
            'max_sharpe_ratio': results['max_sharpe_ratio'],
            'max_sharpe_weights': results['max_sharpe_weights'],
            'min_vol_return': results['min_vol_return'],
            'min_vol_volatility': results['min_vol_volatility'],
            'min_vol_weights': results['min_vol_weights'],
            'market_symbol': results['market_symbol'],
            'start_date': start_date,
            'end_date': end_date
        }

    def run_batch_reports(self, report_configs):
        """
        批量生成 CML 分析报告（含商品）

        参数:
        - report_configs: 报告配置列表

        返回:
        - all_results: 所有分析结果列表
        """
        all_results = []

        for idx, config in enumerate(report_configs, 1):
            logger.info("\n" + "=" * 80)
            logger.info(f"📊 开始生成第 {idx}/{len(report_configs)} 个 CML 分析报告（含商品）")
            logger.info(f"   报告名称: {config['name']}")
            logger.info("=" * 80)

            start_date = config.get("start_date")
            end_date = config.get("end_date")
            if end_date is None:
                end_date = CommonParameters.today

            self.job_logger.start_job('CMLAnalysisReport', 'CMLAnalysis',
                                      params={'report_name': config['name'],
                                              'stock_type': config.get('stock_type'),
                                              'start_date': start_date, 'end_date': end_date,
                                              'interest_country': config.get('interest_country'),
                                              'commodities': str(config.get('commodities'))})
            try:
                result = self.generate_report(
                    stock_type=config["stock_type"],
                    start_date=start_date,
                    end_date=end_date,
                    interest_country=config["interest_country"],
                    case_name=config["name"],
                    include_commodities=config.get("commodities")
                )

                all_results.append(result)
                self.job_logger.end_job_success(records_processed=len(result.get('expected_returns', [])))

                logger.info(f"✅ 第 {idx} 个案例分析完成")
                logger.info(f"   图表路径: {result['chart_path']}")
                logger.info(f"   最大夏普比率: {result['max_sharpe_ratio']:.4f}")

            except Exception as e:
                logger.error(f"❌ 第 {idx} 个分析失败: {config['name']}")
                logger.error(f"   错误信息: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                self.job_logger.end_job_failed(str(e), traceback.format_exc())
                continue

        # 生成综合报告
        if all_results:
            logger.info("\n" + "=" * 80)
            logger.info("📝 开始生成 CML 综合分析研究报告（含商品资产）")
            logger.info("=" * 80)

            comprehensive_pdf_path = self.cmlAnalysisReport.generate_comprehensive_pdf(
                all_results=all_results,
                report_title="CML 综合分析研究报告（含商品资产）"
            )

            logger.info(f"\n✅ 综合分析报告生成成功: {comprehensive_pdf_path}")
            logger.info(f"📊 包含 {len(all_results)} 个测试案例")
        else:
            logger.warning("⚠️ 没有成功的测试案例，无法生成综合报告")

        logger.info("\n" + "=" * 80)
        logger.info("🎉 所有 CML 分析任务完成！")
        logger.info(f"📁 报告输出目录: {self.cmlAnalysisReport.output_dir}")
        logger.info("=" * 80)

        return all_results


if __name__ == "__main__":
    """
    使用示例 - 批量生成带商品的 CML 分析报告
    """
    runReport = RunCMLAnalysisWithCommoditiesReport()

    # ========================================
    # 配置测试案例（股票 + 商品组合）
    # ========================================
    report_configs = [
        {
            "name": "美国科技股 + COMEX黄金",
            "stock_type": "us_tech",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "US",
            "commodities": {'GC': 'COMEX黄金'}
        },
        {
            "name": "美国金融股 + 多种国际商品",
            "stock_type": "us_finance",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "US",
            "commodities": {'GC': 'COMEX黄金', 'CL': 'WTI原油', 'XAU': '伦敦金'}
        },
        {
            "name": "美国混合股票 + COMEX黄金",
            "stock_type": "us_mixed",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "US",
            "commodities": {'GC': 'COMEX黄金'}
        },
        {
            "name": "美国自定义组合 + COMEX黄金",
            "stock_type": "us_custom",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "US",
            "commodities": {'GC': 'COMEX黄金'}
        },
        {
            "name": "中国蓝筹股组合 + 上海黄金",
            "stock_type": "cn_blue_chip",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN",
            "commodities": {'Au99.99': '上海黄金'}
        },
        {
            "name": "中国科技股组合 + 上海黄金",
            "stock_type": "cn_tech",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN",
            "commodities": {'Au99.99': '上海黄金'}
        },
        {
            "name": "中国大消费组合 + 上海黄金",
            "stock_type": "cn_consumer",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN",
            "commodities": {'Au99.99': '上海黄金'}
        },
        {
            "name": "中国金融股组合 + 上海黄金",
            "stock_type": "cn_financial",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN",
            "commodities": {'Au99.99': '上海黄金'}
        },
        {
            "name": "中国能源与制造业组合 + 上海黄金",
            "stock_type": "cn_energy",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN",
            "commodities": {'Au99.99': '上海黄金'}
        },
        {
            "name": "中国自定义股票组合 + 上海黄金",
            "stock_type": "cn_custom",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN",
            "commodities": {'Au99.99': '上海黄金'}
        }
    ]

    # 执行批量报告生成
    all_results = runReport.run_batch_reports(report_configs)

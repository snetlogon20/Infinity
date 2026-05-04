import os

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.common.CommonDataParameters import CommonDataParameters
from dataIntegrator.modelService.financialAnalysis.RiskFreeRateManager import RiskFreeRateManager
from dataIntegrator.modelService.financialAnalysis.PortfolioMetricsAnalysis import PortfolioMetricsAnalysis
from dataIntegrator.modelService.financialAnalysis.PortfolioMetricsAnalysisReport import PortfolioMetricsAnalysisReport

logger = CommonLib.logger
commonLib = CommonLib()


class PortfolioMetricsAnalysisTest:

    def get_stock_list(self, stock_type="cn_blue_chip"):
        """
        根据类型获取股票列表

        参数:
        - stock_type: 股票类型
                      美股: ['us_tech', 'us_finance', 'us_mixed', 'custom']
                      A股: ['cn_blue_chip', 'cn_tech', 'cn_consumer', 'cn_financial', 'cn_energy', 'cn_custom']

        返回:
        - stocks: 股票代码列表
        - market_type: 市场类型 ('US' 或 'CN')
        - market_symbol: 市场指数符号
        """
        # 美国股票组合
        if stock_type == "us_tech":
            stocks = ["SPY", "AAPL", "MSFT", "NVDA", "GOOGL", "META", "TSLA", "AVGO", "ADBE"]
            market_type = "US"
            market_symbol = "SPY"

        elif stock_type == "us_finance":
            stocks = ["SPY", "C", "JPM", "GS", "MS", "BAC", "WFC", "BLK", "AXP"]
            market_type = "US"
            market_symbol = "SPY"

        elif stock_type == "us_mixed":
            stocks = [
                "SPY", "C", "JPM", "AAPL", "NVDA", "GS", "MS", "GE",
                "MSFT", "AVGO", "ADBE", "UNH", "JNJ", "LLY", "PFE", "MRK", "AMZN",
                "TSLA", "MCD", "NFLX", "HD", "GOOGL", "META", "DIS", "CMCSA", "T",
                "CAT", "UPS", "BA", "HON", "PG", "KO", "PEP", "WMT", "COST", "XOM",
                "CVX", "COP", "SLB", "EOG", "AMT", "PLD", "EQIX", "SPG", "O", "NEE",
                "DUK", "SO", "D", "EXC", "LIN", "APD", "FCX", "NEM", "SHW"
            ]
            market_type = "US"
            market_symbol = "SPY"

        elif stock_type == "us_custom":
            stocks = ["SPY", "C", "JPM", "AAPL", "NVDA", "MSFT"]
            market_type = "US"
            market_symbol = "SPY"

        # 中国A股组合
        elif stock_type == "cn_blue_chip":
            stocks = [
                '000001.SH',
                '600519.SH',
                '601318.SH',
                '600036.SH',
                '601012.SH',
                '000858.SZ',
                '000333.SZ',
                '600276.SH',
                '601888.SH',
            ]
            market_type = "CN"
            market_symbol = "000001.SH"

        elif stock_type == "cn_tech":
            stocks = [
                '399001.SZ',
                '002093.SZ',
                '000902.SZ',
                '688498.SH',
                '002475.SZ',
                '002594.SZ',
                '300750.SZ',
                '000063.SZ',
                '600745.SH',
            ]
            market_type = "CN"
            market_symbol = "399001.SZ"

        elif stock_type == "cn_consumer":
            stocks = [
                '000001.SH',
                '600519.SH',
                '000858.SZ',
                '000333.SZ',
                '600887.SH',
                '603288.SH',
                '002714.SZ',
                '600104.SH',
                '601888.SH',
            ]
            market_type = "CN"
            market_symbol = "000001.SH"

        elif stock_type == "cn_financial":
            stocks = [
                '000300.SH',
                '601318.SH',
                '600036.SH',
                '601398.SH',
                '601288.SH',
                '601166.SH',
                '600030.SH',
                '601688.SH',
                '000776.SZ',
            ]
            market_type = "CN"
            market_symbol = "000300.SH"

        elif stock_type == "cn_energy":
            stocks = [
                '000001.SH',
                '601012.SH',
                '600438.SH',
                '601899.SH',
                '600028.SH',
                '601857.SH',
                '601368.SH',
                '600490.SH',
                '600470.SH',
            ]
            market_type = "CN"
            market_symbol = "000001.SH"

        elif stock_type == "cn_custom":
            stocks = CommonDataParameters.STOCK_LIST.copy()
            stocks.insert(0, {'ts_code': '000001.SH', 'name': '上证指数'})
            stocks = [stock['ts_code'] if isinstance(stock, dict) else stock for stock in stocks]
            market_type = "CN"
            market_symbol = "000001.SH"

        else:
            raise ValueError(
                f"不支持的股票类型: {stock_type}。"
                f"支持的类型: ['us_tech', 'us_finance', 'us_mixed', 'us_custom', "
                f"'cn_blue_chip', 'cn_tech', 'cn_consumer', 'cn_financial', 'cn_energy', 'cn_custom']")

        return stocks, market_type, market_symbol

    def run_portfolio_metrics_analysis(self, stock_type="cn_blue_chip", start_date_fixed=None,
                                      end_date_start=None, end_date_end=None, window_days=360,
                                      risk_free_rate=None):
        """
        执行投资组合指标滚动回测分析（参考 stock_metrics_analysis.py）

        参数:
        - stock_type: 股票类型
        - start_date_fixed: 固定的开始日期 (格式: 'YYYYMMDD')，窗口起始点
        - end_date_start: 滚动结束日期的起点 (格式: 'YYYYMMDD')
        - end_date_end: 滚动结束日期的终点 (格式: 'YYYYMMDD')，默认为今天
        - window_days: 回看窗口天数（默认360天）
        - risk_free_rate: 年化无风险利率（如果为None，则自动获取）

        返回:
        - results_df: 包含所有滚动窗口的结果 DataFrame
        """
        if end_date_end is None:
            end_date_end = CommonParameters.today

        stocks, market_type, market_symbol = self.get_stock_list(stock_type)

        logger.info("=" * 80)
        logger.info("🎯 开始投资组合指标滚动回测分析")
        logger.info(f"   股票类型: {stock_type}")
        logger.info(f"   市场类型: {market_type}")
        logger.info(f"   市场指数: {market_symbol}")
        logger.info(f"   滚动日期范围: {end_date_start} 至 {end_date_end}")
        logger.info(f"   回看窗口: {window_days} 天")
        logger.info("=" * 80)

        portfolioMetricsAnalysis = PortfolioMetricsAnalysis()

        results_df = portfolioMetricsAnalysis.analyze_stocks_rolling(
            stock_type=stock_type,
            start_date_fixed=start_date_fixed,
            end_date_start=end_date_start,
            end_date_end=end_date_end,
            window_days=window_days,
            risk_free_rate=risk_free_rate
        )

        return results_df

    def export_to_excel(self, results_df, stock_type="cn_blue_chip", case_name=None, output_dir="dataIntegrator/modelService/financialAnalysis/output/portfolio_metrics"):
        """
        导出结果到 Excel 文件（参考 stock_metrics_analysis.py）
        
        参数:
        - results_df: 分析结果 DataFrame
        - stock_type: 股票类型（用于文件名）
        - case_name: 案例名称（用于文件名，优先使用）
        - output_dir: 输出目录
        """
        portfolioMetricsAnalysis = PortfolioMetricsAnalysis()
        return portfolioMetricsAnalysis.export_to_excel(
            results_df, 
            stock_type=stock_type,
            case_name=case_name,
            output_dir=output_dir
        )

if __name__ == "__main__":
    from dataIntegrator.common.CommonDataParameters import CommonDataParameters
    from dataIntegrator.modelService.financialAnalysis.PortfolioMetricsAnalysisTest import PortfolioMetricsAnalysisTest

    portfolioMetricsAnalysisTest = PortfolioMetricsAnalysisTest()
    portfolioMetricsAnalysisReport = PortfolioMetricsAnalysisReport()

    # 定义报告配置（参考 CMLAnalysisTest）
    report_configs = [
        # {
        #     "name": "美国科技股",
        #     "stock_type": "us_tech",
        #     "start_date": "20250101",
        #     "end_date": None,
        #     "interest_country": "US",
        #     "market_type": "US"
        # },
        # {
        #     "name": "美国金融股",
        #     "stock_type": "us_finance",
        #     "start_date": "20250101",
        #     "end_date": None,
        #     "interest_country": "US",
        #     "market_type": "US"
        # },
        # {
        #     "name": "美国混合股票",
        #     "stock_type": "us_mixed",
        #     "start_date": CommonDataParameters.get_start_date(days=360),
        #     "end_date": CommonParameters.today,
        #     "interest_country": "US",
        #     "market_type": "US"
        # },
        # {
        #     "name": "美国自定义组合",
        #     "stock_type": "us_custom",
        #     "start_date": CommonDataParameters.get_start_date(days=360),
        #     "end_date": CommonParameters.today,
        #     "interest_country": "US",
        #     "market_type": "US"
        # },
        # {
        #     "name": "中国蓝筹股组合",
        #     "stock_type": "cn_blue_chip",
        #     "start_date": CommonDataParameters.get_start_date(days=360),
        #     "end_date": CommonParameters.today,
        #     "interest_country": "CN",
        #     "market_type": "CN"
        # },
        # {
        #     "name": "中国科技股组合",
        #     "stock_type": "cn_tech",
        #     "start_date": CommonDataParameters.get_start_date(days=360),
        #     "end_date": CommonParameters.today,
        #     "interest_country": "CN",
        #     "market_type": "CN"
        # },
        # {
        #     "name": "中国大消费组合",
        #     "stock_type": "cn_consumer",
        #     "start_date": CommonDataParameters.get_start_date(days=360),
        #     "end_date": CommonParameters.today,
        #     "interest_country": "CN",
        #     "market_type": "CN"
        # },
        # {
        #     "name": "中国金融股组合",
        #     "stock_type": "cn_financial",
        #     "start_date": CommonDataParameters.get_start_date(days=360),
        #     "end_date": CommonParameters.today,
        #     "interest_country": "CN",
        #     "market_type": "CN"
        # },
        {
            "name": "中国能源与制造业组合",
            "stock_type": "cn_energy",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN",
            "market_type": "CN"
        },
        {
            "name": "中国自定义股票组合",
            "stock_type": "cn_custom",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN",
            "market_type": "CN"
        }
    ]

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

            logger.info(f"✅ 第 {idx} 个案例分析完成")
            logger.info(f"   Excel 路径: {excel_path}")
            if pdf_path:
                logger.info(f"   PDF 路径: {pdf_path}")
            logger.info(f"   总记录数: {len(results_df)}")

        except Exception as e:
            logger.error(f"❌ 第 {idx} 个分析失败: {config['name']}")
            logger.error(f"   错误信息: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            continue

    if all_results:
        logger.info("\n" + "=" * 80)
        logger.info(" 开始生成投资组合指标综合分析研究报告")
        logger.info("=" * 80)

        comprehensive_pdf_path = portfolioMetricsAnalysisReport.generate_comprehensive_pdf(
            all_results=all_results,
            report_title="投资组合指标综合分析研究报告"
        )

        logger.info(f"\n✅ 综合分析报告生成成功: {comprehensive_pdf_path}")
        logger.info(f" 包含 {len(all_results)} 个测试案例")
    else:
        logger.warning("️ 没有成功的测试案例，无法生成综合报告")

    logger.info("\n" + "=" * 80)
    logger.info(" 所有投资组合指标分析任务完成！")
    logger.info(f"📁 报告输出目录: {portfolioMetricsAnalysisReport.output_dir}")
    logger.info("=" * 80)
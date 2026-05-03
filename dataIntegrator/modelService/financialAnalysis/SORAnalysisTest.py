"""
SR (索提诺比率) 分析测试 - 纯股票分析

本文件演示如何使用 SRAnalysis 进行纯股票投资组合的索提诺比率分析
"""

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.common.CommonDataParameters import CommonDataParameters
from dataIntegrator.modelService.financialAnalysis.RiskFreeRateManager import RiskFreeRateManager
from dataIntegrator.modelService.financialAnalysis.SORAnalysis import SORAnalysis
from dataIntegrator.modelService.financialAnalysis.SORAnalysisReport import SORAnalysisReport

logger = CommonLib.logger


class SORAnalysisTest:
    """SOR (索提诺比率) 分析测试类 - 纯股票"""

    def get_stock_list(self, stock_type="cn_blue_chip"):
        """
        根据类型获取股票列表

        参数:
        - stock_type: 股票类型
                      美股: ['us_tech', 'us_finance', 'us_mixed', 'us_custom']
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

    def run_sor_analysis(self, stock_type="cn_blue_chip", start_date="20250101",
                         end_date=None, risk_free_rate=None, interest_country=None, case_name=None):
        """
        执行 SOR (索提诺比率) 分析（纯股票）

        参数:
        - stock_type: 股票类型
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')，默认为今天
        - risk_free_rate: 年化无风险利率（如果为None，则自动获取）
        - interest_country: 利率国家（'US' 或 'CN'）
        - case_name: 测试案例名称（用于文件名区分）

        返回:
        - results: 分析结果字典
        """
        if end_date is None:
            end_date = CommonParameters.today

        # 根据股票类型获取股票列表
        stocks, market_type, market_symbol = self.get_stock_list(stock_type)

        # 自动获取无风险利率
        if risk_free_rate is None:
            if interest_country is None:
                interest_country = market_type

            riskFreeRateManager = RiskFreeRateManager()
            risk_free_rate = riskFreeRateManager.get_risk_free_rate(
                start_date, end_date, interest_country=interest_country
            )
            logger.info(f"💰 动态获取无风险利率 ({interest_country}): {risk_free_rate * 100:.2f}%")

        logger.info("=" * 80)
        logger.info(" 开始 SOR (索提诺比率) 分析（纯股票）")
        logger.info(f"   股票类型: {stock_type}")
        logger.info(f"   市场类型: {market_type}")
        logger.info(f"   市场指数: {market_symbol}")
        logger.info(f"   日期范围: {start_date} 至 {end_date}")
        logger.info(f"   无风险利率: {risk_free_rate * 100:.2f}%")
        logger.info("=" * 80)

        # 执行 SOR 分析
        sorAnalysis = SORAnalysis()
        results = sorAnalysis.generate_sor_report(
            stocks=stocks,
            start_date=start_date,
            end_date=end_date,
            risk_free_rate_annual=risk_free_rate,
            market_type=market_type,
            market_symbol=market_symbol,
            case_name=case_name
        )

        return results


if __name__ == "__main__":
    """
    使用示例 - 批量生成纯股票的 SR 分析报告
    """
    sorTest = SORAnalysisTest()
    sorAnalysisReport = SORAnalysisReport()

    # ========================================
    # 配置测试案例（纯股票组合）
    # ========================================
    report_configs = [
        {
            "name": "美国科技股",
            "stock_type": "us_tech",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "US",
            "market_type": "US"
        },
        {
            "name": "美国金融股",
            "stock_type": "us_finance",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "US",
            "market_type": "US"
        },
        {
            "name": "美国混合股票",
            "stock_type": "us_mixed",
            "start_date": CommonDataParameters.get_start_date(days=360),
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
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN",
            "market_type": "CN"
        },
        {
            "name": "中国科技股组合",
            "stock_type": "cn_tech",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN",
            "market_type": "CN"
        },
        {
            "name": "中国大消费组合",
            "stock_type": "cn_consumer",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN",
            "market_type": "CN"
        },
        {
            "name": "中国金融股组合",
            "stock_type": "cn_financial",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN",
            "market_type": "CN"
        },
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
        logger.info(f" 开始生成第 {idx}/{len(report_configs)} 个 SR 分析报告（纯股票）")
        logger.info(f"   报告名称: {config['name']}")
        logger.info("=" * 80)

        try:
            start_date = config.get("start_date")
            end_date = config.get("end_date")

            if end_date is None:
                end_date = CommonParameters.today

            results = sorTest.run_sor_analysis(
                stock_type=config["stock_type"],
                start_date=start_date,
                end_date=end_date,
                risk_free_rate=None,
                interest_country=config["interest_country"],
                case_name=config["name"]
            )

            all_results.append({
                'name': config['name'],
                'market_type': config['market_type'],
                'chart_path': results['plot_path'],
                'expected_returns': results['expected_returns'],
                'downside_deviations': results['downside_deviations'],
                'sor_ratios': results['sor_ratios'],
                'market_symbol': results['market_symbol'],
                'start_date': start_date,
                'end_date': end_date
            })

            logger.info(f"✅ 第 {idx} 个案例分析完成")
            logger.info(f"   图表路径: {results['plot_path']}")

        except Exception as e:
            logger.error(f"❌ 第 {idx} 个分析失败: {config['name']}")
            logger.error(f"   错误信息: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            continue

    if all_results:
        logger.info("\n" + "=" * 80)
        logger.info(" 开始生成 SOR 综合分析研究报告（纯股票）")
        logger.info("=" * 80)

        comprehensive_pdf_path = sorAnalysisReport.generate_comprehensive_pdf(
            all_results=all_results,
            report_title="SOR 综合分析研究报告（纯股票）"
        )

        logger.info(f"\n✅ 综合分析报告生成成功: {comprehensive_pdf_path}")
        logger.info(f" 包含 {len(all_results)} 个测试案例")
    else:
        logger.warning("️ 没有成功的测试案例，无法生成综合报告")

    logger.info("\n" + "=" * 80)
    logger.info(" 所有 SOR 分析任务完成！")
    logger.info(f" 报告输出目录: {sorAnalysisReport.output_dir}")
    logger.info("=" * 80)

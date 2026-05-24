"""
Treynor Ratio 分析测试 - 纯股票分析

本文件演示如何使用 TreynorRatioAnalysis 进行特雷诺比率分析
"""

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.common.CommonDataParameters import CommonDataParameters
from dataIntegrator.modelService.financialAnalysis.RiskFreeRateManager import RiskFreeRateManager
from dataIntegrator.modelService.financialAnalysis.TreynorRatioAnalysis import TreynorRatioAnalysis
from dataIntegrator.modelService.financialAnalysis.TreynorRatioAnalysisReport import TreynorRatioAnalysisReport

logger = CommonLib.logger


class TreynorRatioAnalysisTest:
    """特雷诺比率分析测试类"""

    def get_asset_list(self, asset_type="cn_blue_chip"):
        """
        根据类型获取资产列表

        参数:
        - asset_type: 资产类型
                      美股: ['us_tech', 'us_finance', 'us_mixed', 'us_custom']
                      A股: ['cn_blue_chip', 'cn_tech', 'cn_consumer', 'cn_financial', 'cn_energy', 'cn_custom']

        返回:
        - assets: 资产代码列表
        - market_type: 市场类型 ('US' 或 'CN')
        - market_symbol: 市场指数符号
        """
        # 美国股票组合
        if asset_type == "us_tech":
            assets = ["SPY", "AAPL", "MSFT", "NVDA", "GOOGL", "META", "TSLA", "AVGO", "ADBE"]
            market_type = "US"
            market_symbol = "SPY"

        elif asset_type == "us_finance":
            assets = ["SPY", "C", "JPM", "GS", "MS", "BAC", "WFC", "BLK", "AXP"]
            market_type = "US"
            market_symbol = "SPY"

        elif asset_type == "us_mixed":
            assets = [
                "SPY", "C", "JPM", "AAPL", "NVDA", "GS", "MS", "GE",
                "MSFT", "AVGO", "ADBE", "UNH", "JNJ", "LLY", "PFE", "MRK", "AMZN",
                "TSLA", "MCD", "NFLX", "HD", "GOOGL", "META", "DIS", "CMCSA", "T",
                "CAT", "UPS", "BA", "HON", "PG", "KO", "PEP", "WMT", "COST", "XOM",
                "CVX", "COP", "SLB", "EOG", "AMT", "PLD", "EQIX", "SPG", "O", "NEE",
                "DUK", "SO", "D", "EXC", "LIN", "APD", "FCX", "NEM", "SHW"
            ]
            market_type = "US"
            market_symbol = "SPY"

        elif asset_type == "us_custom":
            assets = ["SPY", "C", "JPM", "AAPL", "NVDA", "MSFT"]
            market_type = "US"
            market_symbol = "SPY"

        # 中国A股组合
        elif asset_type == "cn_blue_chip":
            assets = [
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

        elif asset_type == "cn_tech":
            assets = [
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

        elif asset_type == "cn_consumer":
            assets = [
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

        elif asset_type == "cn_financial":
            assets = [
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

        elif asset_type == "cn_energy":
            assets = [
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

        elif asset_type == "cn_custom":
            assets = CommonDataParameters.STOCK_LIST.copy()
            assets.insert(0, {'ts_code': '000001.SH', 'name': '上证指数'})
            assets = [asset['ts_code'] if isinstance(asset, dict) else asset for asset in assets]
            market_type = "CN"
            market_symbol = "000001.SH"

        # 全球指数组合
        elif asset_type == "global_major":
            assets = [
                'HSI', 'N225', 'KS11', 'STI', 'AS51',
                'SENSEX', 'FTSE', 'GDAXI', 'FCHI', 'SPX',
            ]
            market_type = "GLOBAL"
            market_symbol = "HSI"

        elif asset_type == "global_asia":
            assets = [
                'HSI', 'N225', 'KS11', 'STI', 'AS51',
                'SENSEX', 'TWII', 'XIN9',
            ]
            market_type = "GLOBAL"
            market_symbol = "HSI"

        elif asset_type == "global_europe":
            assets = ['FTSE', 'GDAXI', 'FCHI', 'HKAH', 'CKLSE']
            market_type = "GLOBAL"
            market_symbol = "FTSE"

        elif asset_type == "global_custom":
            assets = ['HSI', 'SPX', 'GDAXI', 'N225']
            market_type = "GLOBAL"
            market_symbol = "HSI"

        else:
            raise ValueError(
                f"不支持的资产类型: {asset_type}。"
                f"支持的类型: ['us_tech', 'us_finance', 'us_mixed', 'us_custom', "
                f"'cn_blue_chip', 'cn_tech', 'cn_consumer', 'cn_financial', 'cn_energy', 'cn_custom', "
                f"'global_major', 'global_asia', 'global_europe', 'global_custom']")

        return assets, market_type, market_symbol

    def run_treynor_analysis(self, asset_type="cn_blue_chip", start_date="20250301",
                             end_date=None, risk_free_rate=None, interest_country=None, case_name=None):
        """
        执行特雷诺比率分析

        参数:
        - asset_type: 资产类型
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')，默认为今天
        - risk_free_rate: 年化无风险利率（如果为None，则自动从RiskFreeRateManager获取）
        - interest_country: 利率国家（如果risk_free_rate为None时使用，'US' 或 'CN'）
        - case_name: 测试案例名称（用于文件名区分）

        返回:
        - results: 分析结果字典
        """
        if end_date is None:
            end_date = CommonParameters.today

        assets, market_type, market_symbol = self.get_asset_list(asset_type)

        if risk_free_rate is None:
            if interest_country is None:
                interest_country = market_type

            riskFreeRateManager = RiskFreeRateManager()
            risk_free_rate = riskFreeRateManager.get_risk_free_rate(start_date, end_date,
                                                                    interest_country=interest_country)
            logger.info(f"💰 动态获取无风险利率 ({interest_country}): {risk_free_rate * 100:.2f}%")

        logger.info("=" * 80)
        logger.info("🎯 开始特雷诺比率 (Treynor Ratio) 分析测试")
        logger.info(f"   资产类型: {asset_type}")
        logger.info(f"   市场类型: {market_type}")
        logger.info(f"   市场指数: {market_symbol}")
        logger.info(f"   日期范围: {start_date} 至 {end_date}")
        logger.info(f"   无风险利率: {risk_free_rate * 100:.2f}%")
        logger.info("=" * 80)

        treynorAnalysis = TreynorRatioAnalysis()

        results = treynorAnalysis.generate_treynor_report(
            assets=assets,
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
    使用示例 - 批量生成特雷诺比率分析报告
    """
    treynorAnalysisTest = TreynorRatioAnalysisTest()
    treynorAnalysisReport = TreynorRatioAnalysisReport()

    report_configs = [
        {
            "name": "美国科技股",
            "asset_type": "us_tech",
            "start_date": "20250101",
            "end_date": None,
            "interest_country": "US",
            "market_type": "US"
        },
        {
            "name": "美国金融股",
            "asset_type": "us_finance",
            "start_date": "20250101",
            "end_date": None,
            "interest_country": "US",
            "market_type": "US"
        },
        {
            "name": "美国混合股票",
            "asset_type": "us_mixed",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "US",
            "market_type": "US"
        },
        {
            "name": "美国自定义组合",
            "asset_type": "us_custom",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "US",
            "market_type": "US"
        },
        {
            "name": "中国蓝筹股组合",
            "asset_type": "cn_blue_chip",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN",
            "market_type": "CN"
        },
        {
            "name": "中国科技股组合",
            "asset_type": "cn_tech",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN",
            "market_type": "CN"
        },
        {
            "name": "中国大消费组合",
            "asset_type": "cn_consumer",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN",
            "market_type": "CN"
        },
        {
            "name": "中国金融股组合",
            "asset_type": "cn_financial",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN",
            "market_type": "CN"
        },
        {
            "name": "中国能源与制造业组合",
            "asset_type": "cn_energy",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN",
            "market_type": "CN"
        },
        {
            "name": "中国自定义股票组合",
            "asset_type": "cn_custom",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN",
            "market_type": "CN"
        },
        {
            "name": "全球主要指数组合",
            "asset_type": "global_major",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "US",
            "market_type": "GLOBAL"
        },
        {
            "name": "全球亚洲指数组合",
            "asset_type": "global_asia",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "US",
            "market_type": "GLOBAL"
        },
        {
            "name": "全球欧洲指数组合",
            "asset_type": "global_europe",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "US",
            "market_type": "GLOBAL"
        },
        {
            "name": "全球自定义指数组合",
            "asset_type": "global_custom",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "US",
            "market_type": "GLOBAL"
        }
    ]

    all_results = []

    for idx, config in enumerate(report_configs, 1):
        logger.info("\n" + "=" * 80)
        logger.info(f"📊 开始生成第 {idx}/{len(report_configs)} 个特雷诺比率分析报告")
        logger.info(f"   报告名称: {config['name']}")
        logger.info("=" * 80)

        try:
            start_date = config.get("start_date")
            end_date = config.get("end_date")

            if end_date is None:
                end_date = CommonParameters.today

            results = treynorAnalysisTest.run_treynor_analysis(
                asset_type=config["asset_type"],
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
                'betas': results['betas'],
                'expected_returns': results['expected_returns'],
                'treynor_ratios': results['treynor_ratios'],
                'risk_free_rate': results['risk_free_rate'],
                'market_return': results['market_return'],
                'market_risk_premium': results['market_risk_premium'],
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
        logger.info("📝 开始生成特雷诺比率综合分析研究报告")
        logger.info("=" * 80)

        comprehensive_pdf_path = treynorAnalysisReport.generate_comprehensive_pdf(
            all_results=all_results,
            report_title="特雷诺比率 (Treynor Ratio) 综合分析研究报告"
        )

        logger.info(f"\n✅ 综合分析报告生成成功: {comprehensive_pdf_path}")
        logger.info(f" 包含 {len(all_results)} 个测试案例")
    else:
        logger.warning("️ 没有成功的测试案例，无法生成综合报告")

    logger.info("\n" + "=" * 80)
    logger.info("🎉 所有特雷诺比率分析任务完成！")
    logger.info(f"📁 报告输出目录: {treynorAnalysisReport.output_dir}")
    logger.info("=" * 80)

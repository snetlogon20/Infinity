from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.common.CommonDataParameters import CommonDataParameters
from dataIntegrator.modelService.financialAnalysis.RiskFreeRateManager import RiskFreeRateManager
from dataIntegrator.modelService.financialAnalysis.SMLAnalysis import SMLAnalysis
from dataIntegrator.modelService.financialAnalysis.SMLAnalysisReport import SMLAnalysisReport

logger = CommonLib.logger
commonLib = CommonLib()


class SMLAnalysisTest:

    def get_stock_list(self, stock_type="us_tech"):
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
            # 组合1：蓝筹股组合（以上证指数为基准）
            stocks = [
                '000001.SH',  # 上证指数（市场基准）
                '600519.SH',  # 贵州茅台
                '601318.SH',  # 中国平安
                '600036.SH',  # 招商银行
                '601012.SH',  # 隆基绿能
                '000858.SZ',  # 五粮液
                '000333.SZ',  # 美的集团
                '600276.SH',  # 恒瑞医药
                '601888.SH',  # 中国中免
            ]
            market_type = "CN"
            market_symbol = "000001.SH"

        elif stock_type == "cn_tech":
            # 组合2：科技股组合（以深证成指为基准）
            stocks = [
                '399001.SZ',  # 深证成指（市场基准）
                '002093.SZ',  # 国脉科技
                '000902.SZ',  # 新洋丰
                '688498.SH',  # 源杰科技
                '002475.SZ',  # 立讯精密
                '002594.SZ',  # 比亚迪
                '300750.SZ',  # 宁德时代
                '000063.SZ',  # 中兴通讯
                '600745.SH',  # 闻泰科技
            ]
            market_type = "CN"
            market_symbol = "399001.SZ"

        elif stock_type == "cn_consumer":
            # 组合3：大消费组合（以上证指数为基准）
            stocks = [
                '000001.SH',  # 上证指数（市场基准）
                '600519.SH',  # 贵州茅台
                '000858.SZ',  # 五粮液
                '000333.SZ',  # 美的集团
                '600887.SH',  # 伊利股份
                '603288.SH',  # 海天味业
                '002714.SZ',  # 牧原股份
                '600104.SH',  # 上汽集团
                '601888.SH',  # 中国中免
            ]
            market_type = "CN"
            market_symbol = "000001.SH"

        elif stock_type == "cn_financial":
            # 组合4：金融股组合（以沪深300为基准）
            stocks = [
                '000300.SH',  # 沪深300（市场基准）
                '601318.SH',  # 中国平安
                '600036.SH',  # 招商银行
                '601398.SH',  # 工商银行
                '601288.SH',  # 农业银行
                '601166.SH',  # 兴业银行
                '600030.SH',  # 中信证券
                '601688.SH',  # 华泰证券
                '000776.SZ',  # 广发证券
            ]
            market_type = "CN"
            market_symbol = "000300.SH"

        elif stock_type == "cn_energy":
            # 组合5：能源与制造业组合（以上证指数为基准）
            stocks = [
                '000001.SH',  # 上证指数（市场基准）
                '601012.SH',  # 隆基绿能
                '600438.SH',  # 通威股份
                '601899.SH',  # 紫金矿业
                '600028.SH',  # 中国石化
                '601857.SH',  # 中国石油
                '601368.SH',  # 绿城水务
                '600490.SH',  # 鹏欣资源
                '600470.SH',  # 六国化工
            ]
            market_type = "CN"
            market_symbol = "000001.SH"

        elif stock_type == "cn_custom":
            # 自定义组合
            stocks = CommonDataParameters.STOCK_LIST.copy()
            # 添加市场指数
            stocks.insert(0, {'ts_code': '000001.SH', 'name': '上证指数'})
            # 提取 ts_code
            stocks = [stock['ts_code'] if isinstance(stock, dict) else stock for stock in stocks]
            market_type = "CN"
            market_symbol = "000001.SH"

        # 全球指数组合
        elif stock_type == "global_major":
            stocks = [
                'HSI',      # 恒生指数
                'N225',     # 日经225
                'KS11',     # 韩国综合指数
                'STI',      # 新加坡海峡时报
                'AS51',     # 澳大利亚标普200
                'SENSEX',   # 印度孟买敏感30
                'FTSE',     # 英国富时100
                'GDAXI',    # 德国DAX
                'FCHI',     # 法国CAC40
                'SPX',      # 标普500
            ]
            market_type = "GLOBAL"
            market_symbol = "HSI"

        elif stock_type == "global_asia":
            stocks = [
                'HSI',      # 恒生指数
                'N225',     # 日经225
                'KS11',     # 韩国综合指数
                'STI',      # 新加坡海峡时报
                'AS51',     # 澳大利亚标普200
                'SENSEX',   # 印度孟买敏感30
                'TWII',     # 台湾加权指数
                'XIN9',     # 新华富时A50
            ]
            market_type = "GLOBAL"
            market_symbol = "HSI"

        elif stock_type == "global_europe":
            stocks = [
                'FTSE',     # 英国富时100
                'GDAXI',    # 德国DAX
                'FCHI',     # 法国CAC40
                'HKAH',     # 恒生AH股指数
                'CKLSE',    # 伦敦富时100
            ]
            market_type = "GLOBAL"
            market_symbol = "FTSE"

        elif stock_type == "global_custom":
            stocks = [
                'HSI',      # 恒生指数
                'SPX',      # 标普500
                'GDAXI',    # 德国DAX
                'N225',     # 日经225
            ]
            market_type = "GLOBAL"
            market_symbol = "HSI"

        else:
            raise ValueError(
                f"不支持的股票类型: {stock_type}。"
                f"支持的类型: ['us_tech', 'us_finance', 'us_mixed', 'us_custom', "
                f"'cn_blue_chip', 'cn_tech', 'cn_consumer', 'cn_financial', 'cn_energy', 'cn_custom', "
                f"'global_major', 'global_asia', 'global_europe', 'global_custom']")

        return stocks, market_type, market_symbol

    def run_sml_analysis(self, stock_type="us_mixed", start_date="20250301",
                         end_date=None, risk_free_rate=None, display_stocks=None, interest_country=None, case_name=None):
        """
        执行 SML 分析

        参数:
        - stock_type: 股票类型
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')，默认为今天
        - risk_free_rate: 年化无风险利率（如果为None，则自动从RiskFreeRateManager获取）
        - display_stocks: 要在图表中显示的股票列表（可选）
        - interest_country: 利率国家（如果risk_free_rate为None时使用，'US' 或 'CN'）
        - case_name: 测试案例名称（用于文件名区分）

        返回:
        - results: 分析结果字典
        """
        if end_date is None:
            end_date = CommonParameters.today

        stocks, market_type, market_symbol = self.get_stock_list(stock_type)

        if risk_free_rate is None:
            if interest_country is None:
                interest_country = market_type

            riskFreeRateManager = RiskFreeRateManager()
            risk_free_rate = riskFreeRateManager.get_risk_free_rate(start_date, end_date,
                                                                    interest_country=interest_country)
            logger.info(f"💰 动态获取无风险利率 ({interest_country}): {risk_free_rate * 100:.2f}%")

        logger.info("=" * 80)
        logger.info("🎯 开始 SML 分析测试")
        logger.info(f"   股票类型: {stock_type}")
        logger.info(f"   市场类型: {market_type}")
        logger.info(f"   市场指数: {market_symbol}")
        logger.info(f"   日期范围: {start_date} 至 {end_date}")
        logger.info(f"   无风险利率: {risk_free_rate * 100:.2f}%")
        logger.info("=" * 80)

        smlAnalysis = SMLAnalysis()

        results = smlAnalysis.generate_sml_report(
            stocks=stocks,
            start_date=start_date,
            end_date=end_date,
            risk_free_rate_annual=risk_free_rate,
            display_stocks=display_stocks,
            market_type=market_type,
            market_symbol=market_symbol,
            case_name=case_name
        )

        return results

if __name__ == "__main__":
    from dataIntegrator.common.CommonDataParameters import CommonDataParameters
    from dataIntegrator.modelService.financialAnalysis.SMLAnalysisTest import SMLAnalysisTest

    smlAnalysisTest = SMLAnalysisTest()
    smlAnalysisReport = SMLAnalysisReport()

    report_configs = [
        {
            "name": "美国科技股",
            "stock_type": "us_tech",
            "start_date": "20250101",
            "end_date": None,
            "interest_country": "US",
            "market_type": "US"
        },
        {
            "name": "美国金融股",
            "stock_type": "us_finance",
            "start_date": "20250101",
            "end_date": None,
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
        },
        {
            "name": "全球主要指数组合",
            "stock_type": "global_major",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "US",
            "market_type": "GLOBAL"
        },
        {
            "name": "全球亚洲指数组合",
            "stock_type": "global_asia",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "US",
            "market_type": "GLOBAL"
        },
        {
            "name": "全球欧洲指数组合",
            "stock_type": "global_europe",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "US",
            "market_type": "GLOBAL"
        },
        {
            "name": "全球自定义指数组合",
            "stock_type": "global_custom",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "US",
            "market_type": "GLOBAL"
        }
    ]

    all_results = []

    for idx, config in enumerate(report_configs, 1):
        logger.info("\n" + "=" * 80)
        logger.info(f" 开始生成第 {idx}/{len(report_configs)} 个 SML 分析报告")
        logger.info(f"   报告名称: {config['name']}")
        logger.info("=" * 80)

        try:
            start_date = config.get("start_date")
            end_date = config.get("end_date")

            if end_date is None:
                end_date = CommonParameters.today

            results = smlAnalysisTest.run_sml_analysis(
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
                'betas': results['betas'],
                'expected_returns': results['expected_returns'],
                'market_symbol': results['market_symbol'],
                'start_date': start_date,
                'end_date': end_date
            })

            logger.info(f"✅ 第 {idx} 个案例分析完成")
            logger.info(f"   图表路径: {results['plot_path']}")
            logger.info(f"   β值数量: {len(results['betas'])}")

        except Exception as e:
            logger.error(f"❌ 第 {idx} 个分析失败: {config['name']}")
            logger.error(f"   错误信息: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            continue

    if all_results:
        logger.info("\n" + "=" * 80)
        logger.info(" 开始生成 SML 综合分析研究报告")
        logger.info("=" * 80)

        comprehensive_pdf_path = smlAnalysisReport.generate_comprehensive_pdf(
            all_results=all_results,
            report_title="SML 综合分析研究报告"
        )

        logger.info(f"\n✅ 综合分析报告生成成功: {comprehensive_pdf_path}")
        logger.info(f" 包含 {len(all_results)} 个测试案例")
    else:
        logger.warning("️ 没有成功的测试案例，无法生成综合报告")

    logger.info("\n" + "=" * 80)
    logger.info(" 所有 SML 分析任务完成！")
    logger.info(f"📁 报告输出目录: {smlAnalysisReport.output_dir}")
    logger.info("=" * 80)
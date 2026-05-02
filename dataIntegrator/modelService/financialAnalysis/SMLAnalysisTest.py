from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.common.CommonDataParameters import CommonDataParameters
from dataIntegrator.modelService.financialAnalysis.RiskFreeRateManager import RiskFreeRateManager
from dataIntegrator.modelService.financialAnalysis.SMLAnalysis import SMLAnalysis

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

        else:
            raise ValueError(
                f"不支持的股票类型: {stock_type}。"
                f"支持的类型: ['us_tech', 'us_finance', 'us_mixed', 'us_custom', "
                f"'cn_blue_chip', 'cn_tech', 'cn_consumer', 'cn_financial', 'cn_energy', 'cn_custom']")

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

    smlAnalysisTest = SMLAnalysisTest()

    test_cases = {
        "美国科技股": {
            "stock_type": "us_tech",
            "start_date": "20250101",
            "end_date": None,
            "interest_country": "US"
        },
        "美国金融股": {
            "stock_type": "us_finance",
            "start_date": "20250101",
            "end_date": None,
            "interest_country": "US"
        },
        "美国混合股票": {
            "stock_type": "us_mixed",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "US"
        },
        "中国蓝筹股组合": {
            "stock_type": "cn_blue_chip",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN"
        },
        "中国科技股组合": {
            "stock_type": "cn_tech",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN"
        },
        "中国大消费组合": {
            "stock_type": "cn_consumer",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN"
        },
        "中国金融股组合": {
            "stock_type": "cn_financial",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN"
        },
        "中国能源与制造业组合": {
            "stock_type": "cn_energy",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN"
        },
        "中国自定义股票组合": {
            "stock_type": "cn_custom",
            "start_date": CommonDataParameters.get_start_date(days=360),
            "end_date": CommonParameters.today,
            "interest_country": "CN"
        }
    }

    for case_name, case_params in test_cases.items():
        logger.info(f"\n{'=' * 80}")
        logger.info(f"🧪 开始测试: {case_name}")
        logger.info(f"{'=' * 80}")

        try:
            results = smlAnalysisTest.run_sml_analysis(
                stock_type=case_params["stock_type"],
                start_date=case_params["start_date"],
                end_date=case_params["end_date"],
                risk_free_rate=None,
                interest_country=case_params["interest_country"],
                case_name=case_name
            )

            logger.info(f"\n✅ {case_name} 测试完成！")
            logger.info(f"   市场类型: {results['market_type']}")
            logger.info(f"   市场指数: {results['market_symbol']}")
            logger.info(f"   β值数量: {len(results['betas'])}")
            logger.info(f"   图表路径: {results['plot_path']}")

        except Exception as e:
            logger.error(f"\n❌ {case_name} 测试失败: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
            continue
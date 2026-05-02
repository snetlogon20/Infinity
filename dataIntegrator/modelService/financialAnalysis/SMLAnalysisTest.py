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
        - stock_type: 股票类型 ['us_tech', 'us_finance', 'us_mixed', 'custom']

        返回:
        - stocks: 股票代码列表
        """
        if stock_type == "us_tech":
            stocks = ["SPY", "AAPL", "MSFT", "NVDA", "GOOGL", "META", "TSLA", "AVGO", "ADBE"]

        elif stock_type == "us_finance":
            stocks = ["SPY", "C", "JPM", "GS", "MS", "BAC", "WFC", "BLK", "AXP"]

        elif stock_type == "us_mixed":
            stocks = [
                "SPY", "C", "JPM", "AAPL", "NVDA", "GS", "MS", "GE",
                "MSFT", "AVGO", "ADBE", "UNH", "JNJ", "LLY", "PFE", "MRK", "AMZN",
                "TSLA", "MCD", "NFLX", "HD", "GOOGL", "META", "DIS", "CMCSA", "T",
                "CAT", "UPS", "BA", "HON", "PG", "KO", "PEP", "WMT", "COST", "XOM",
                "CVX", "COP", "SLB", "EOG", "AMT", "PLD", "EQIX", "SPG", "O", "NEE",
                "DUK", "SO", "D", "EXC", "LIN", "APD", "FCX", "NEM", "SHW"
            ]

        elif stock_type == "custom":
            stocks = ["SPY", "C", "JPM", "AAPL", "NVDA", "MSFT"]

        else:
            raise ValueError(
                f"不支持的股票类型: {stock_type}。支持的类型: ['us_tech', 'us_finance', 'us_mixed', 'custom']")

        return stocks

    def run_sml_analysis(self, stock_type="us_mixed", start_date="20250301",
                        end_date=None, risk_free_rate=0.04, display_stocks=None):
        """
        执行 SML 分析

        参数:
        - stock_type: 股票类型
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')，默认为今天
        - risk_free_rate: 年化无风险利率
        - display_stocks: 要在图表中显示的股票列表（可选）

        返回:
        - results: 分析结果字典
        """
        if end_date is None:
            end_date = CommonParameters.today

        logger.info("=" * 80)
        logger.info("🎯 开始 SML 分析测试")
        logger.info(f"   股票类型: {stock_type}")
        logger.info(f"   日期范围: {start_date} 至 {end_date}")
        logger.info(f"   无风险利率: {risk_free_rate*100:.2f}%")
        logger.info("=" * 80)

        stocks = self.get_stock_list(stock_type)

        smlAnalysis = SMLAnalysis()

        results = smlAnalysis.generate_sml_report(
            stocks=stocks,
            start_date=start_date,
            end_date=end_date,
            risk_free_rate_annual=risk_free_rate,
            display_stocks=display_stocks
        )

        return results


if __name__ == "__main__":

    smlAnalysisTest = SMLAnalysisTest()
    riskFreeRateManager = RiskFreeRateManager()

    """
        测试案例1：美国科技股
    """
    # stock_type = "us_tech"
    # start_date = "20250101"
    # end_date = None  # 使用今天
    # risk_free_rate = riskFreeRateManager.get_risk_free_rate(start_date, end_date, interest_country="US")

    """
        测试案例2：美国金融股
    """
    # stock_type = "us_finance"
    # start_date = "20250101"
    # end_date = None
    # risk_free_rate = riskFreeRateManager.get_risk_free_rate(start_date, end_date, interest_country="US")

    """
        测试案例3：美国混合股票（推荐）
    """
    stock_type = "us_mixed"
    start_date = CommonDataParameters.get_start_date(days=360)
    end_date = CommonParameters.today
    risk_free_rate = riskFreeRateManager.get_risk_free_rate(start_date, end_date, interest_country="US")

    """
        测试案例4：自定义股票列表
    """
    # stock_type = "custom"
    # start_date = CommonDataParameters.get_start_date(days=360)
    # end_date = CommonParameters.today
    # risk_free_rate = riskFreeRateManager.get_risk_free_rate(start_date, end_date, interest_country="US")

    # 执行分析
    results = smlAnalysisTest.run_sml_analysis(
        stock_type=stock_type,
        start_date=start_date,
        end_date=end_date,
        risk_free_rate=risk_free_rate
    )

    logger.info("\n✅ 测试完成！")
    logger.info(f"β值数量: {len(results['betas'])}")
    logger.info(f"图表路径: {results['plot_path']}")

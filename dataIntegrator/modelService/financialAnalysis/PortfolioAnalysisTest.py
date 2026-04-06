from dataIntegrator import CommonLib
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.modelService.financialAnalysis.PortfolioAnalysis import PortfolioAnalysis
import numpy as np
from scipy.optimize import minimize

logger = CommonLib.logger
commonLib = CommonLib()

class PortfolioAnalysisTest():

    def test_simple_portfolio_p41(cls):
        portfolioAnalysis = PortfolioAnalysis()

        # 示例值 P41, Example of Computing the risk of a portfolio
        print("given 2 products")
        w = np.array([0.6, 0.4])  # 权重
        u = np.array([0.00, 1])  # 预期收益率
        sigma = np.array([5, 9.95])  # 标准差
        rho = np.array([[1, 0.3], [0.3, 1]])  # 相关系数矩阵
        portfolio_return, portfolio_volatility = portfolioAnalysis.calculate_portfolio_return_and_volatility(w, u, sigma,
                                                                                                             rho)
        print(f"投资组合的波动率为: {portfolio_return}")
        print(f"投资组合的波动率为: {portfolio_volatility}")


    def test_parameter_portfolio(cls):
        portfolioAnalysis = PortfolioAnalysis()

        # 示例值
        print("given 5 products")
        w = np.array([0.1, 0.2, 0.3, 0.25, 0.15])  # 权重
        u = np.array([0.05, 0.1, 0.15, 0.2, 0.25])  # 预期收益率
        sigma = np.array([0.1, 0.2, 0.15, 0.25, 0.18])  # 标准差
        rho = np.array([[1, 0.3, 0.2, 0.1, 0.2],
                        [0.3, 1, 0.4, 0.3, 0.25],
                        [0.2, 0.4, 1, 0.2, 0.15],
                        [0.1, 0.3, 0.2, 1, 0.2],
                        [0.2, 0.25, 0.15, 0.2, 1]])  # 相关系数矩阵
        portfolio_return, portfolio_volatility = portfolioAnalysis.calculate_portfolio_return_and_volatility(w, u, sigma,
                                                                                                             rho)
        print(f"投资组合的波动率为: {portfolio_return}")
        print(f"投资组合的波动率为: {portfolio_volatility}")

    def prepare_data_from_clickhouse(self, stock_codes, start_date, end_date):
        """
        从 ClickHouse 获取数据并计算 u, sigma, rho
        """
        stock_codes_str = ','.join([f"'{code}'" for code in stock_codes])
        # 转换日期格式：从 'YYYYMMDD' 转为 'YYYY-MM-DD' 用于伦敦金查询
        start_date_formatted = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
        end_date_formatted = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"

        # 纯美国股票
        # sql = f"""
        #     select ts_code, trade_date, close_point
        #     from df_tushare_us_stock_daily
        #     where ts_code in ({stock_codes_str})
        #     AND trade_date >= '{start_date}' and trade_date <='{end_date}'
        #     order by trade_date asc
        # """

        # 纯美国股票 + 黄金
        # sql = f"""
        #     SELECT
        #         ts_code,
        #         trade_date,
        #         close_point
        #     FROM
        #     (
        #         SELECT
        #             ts_code,
        #             trade_date,
        #             close_point
        #         FROM df_tushare_us_stock_daily
        #         WHERE ts_code IN ({stock_codes_str})
        #             AND trade_date >= '{start_date}'
        #             AND trade_date <= '{end_date}'
        #         UNION DISTINCT
        #         SELECT
        #             'GC' AS ts_code,
        #             replaceAll(toString(date), '-', '') AS trade_date,
        #             close AS close_point
        #         FROM indexsysdb.df_akshare_futures_foreign_hist
        #         WHERE symbol = 'GC'
        #             AND date >= '{start_date_formatted}'
        #             AND date <= '{end_date_formatted}'
        #             AND close > 0
        #     )
        #     ORDER BY trade_date, ts_code
        # """

        # 国内自选股票
        # sql = f"""
        #     select
        #         ts_code as ts_code,
        #         trade_date as trade_date,
        #         close as close_point
        #     from indexsysdb.df_tushare_stock_daily
        #     where ts_code in
        #     (
        #                 '002093.SZ',
        #                 '600490.SH',
        #                 '000902.SZ',
        #                 '601368.SH',
        #                 '603839.SH'
        #     )
        #     AND
        #             trade_date >= '20241001' AND
        #             trade_date <= '20261231'
        #     order by trade_date desc
        #  """

        # AI选股票
        # sql = f"""
        #     select
        #         ts_code as ts_code,
        #         trade_date as trade_date,
        #         close as close_point
        #     from indexsysdb.df_tushare_stock_daily
        #     where ts_code in
        #     (
        #                 '688585.SH',
        #                 '605255.SH',
        #                 '300476.SZ',
        #                 '301232.SZ',
        #                 '603226.SH'
        #     )
        #     AND
        #             trade_date >= '20241001' AND
        #             trade_date <= '20261231'
        #     order by trade_date desc
        #  """

        # 大宗商品
        sql="""
            SELECT
                symbol as ts_code,
                replaceAll(toString(date), '-', '') as trade_date,
                close AS close_point
            FROM indexsysdb.df_akshare_futures_foreign_hist
            WHERE symbol in ('GC','CL','OIL','NG')
                AND close > 0
                AND date >= '2022-01-01'  -- 注意：这里的 date 列是原始列名
                AND date <= '2026-03-31'  -- 注意：原表中的日期格式是 yyyy-mm-dd
            order by date desc
        """

        logger.info(f"执行 SQL 查询: {sql}")
        clickhouseService = ClickhouseService()
        df = clickhouseService.getDataFrameWithoutColumnsName(sql)

        logger.info(f"获取到原始数据形状: {df.shape}")
        logger.info(f"数据列: {list(df.columns)}")
        logger.info(f"包含股票: {df['ts_code'].unique()}")

        # 数据透视：行=日期，列=股票，值=收盘价
        pivot_df = df.pivot(index='trade_date', columns='ts_code', values='close_point')
        pivot_df = pivot_df.dropna()

        logger.info(f"透视后数据形状: {pivot_df.shape}")
        logger.info(f"列名顺序: {list(pivot_df.columns)}")

        # 计算日收益率
        returns_df = pivot_df.pct_change().dropna()

        # 计算 u (预期收益率 - 日均值)
        u = returns_df.mean().values
        # 计算 sigma (标准差 - 日标准差)
        sigma = returns_df.std().values
        # 计算 rho (相关系数矩阵)
        rho = returns_df.corr().values

        logger.info(f"预期收益率 (u): {u}")
        logger.info(f"标准差 (sigma): {sigma}")
        logger.info(f"相关系数矩阵 (rho):\n{rho}")

        return u, sigma, rho, pivot_df.columns.tolist()

    def calculate_sharpe_ratio(self, weights, u, sigma, rho, risk_free_rate=0.015, trading_days=252):
        """
        计算给定权重的夏普比率（返回负值用于最小化）
        """
        portfolioAnalysis = PortfolioAnalysis()
        portfolio_return, portfolio_volatility = portfolioAnalysis.calculate_portfolio_return_and_volatility(
            weights, u, sigma, rho)

        annual_return = portfolio_return * trading_days
        annual_volatility = portfolio_volatility * np.sqrt(trading_days)

        sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility
        return -sharpe_ratio

    def calculate_negative_return(self, weights, u, sigma, rho, trading_days=252):
        """
        计算负的投资组合收益率（用于最小化，即最大化收益）
        """
        portfolioAnalysis = PortfolioAnalysis()
        portfolio_return, _ = portfolioAnalysis.calculate_portfolio_return_and_volatility(
            weights, u, sigma, rho)

        annual_return = portfolio_return * trading_days
        return -annual_return

    def calculate_volatility(self, weights, u, sigma, rho, trading_days=252):
        """
        计算投资组合波动率
        """
        portfolioAnalysis = PortfolioAnalysis()
        _, portfolio_volatility = portfolioAnalysis.calculate_portfolio_return_and_volatility(
            weights, u, sigma, rho)

        annual_volatility = portfolio_volatility * np.sqrt(trading_days)
        return annual_volatility

    def optimize_portfolio_weights(self, u, sigma, rho, option="best_sharpe_ratio", risk_free_rate=0.015):
        """
        优化投资组合权重

        参数:
        - u: 预期收益率数组
        - sigma: 标准差数组
        - rho: 相关系数矩阵
        - option: 优化目标 ['best_sharpe_ratio', 'best_return', 'lowest_volatility']
        - risk_free_rate: 无风险利率（仅在 best_sharpe_ratio 时使用）

        返回:
        - optimal_weights: 最优权重
        - optimization_result: 优化结果字典
        """
        n_assets = len(u)

        # 初始权重（等权重）
        initial_weights = np.array([1.0 / n_assets] * n_assets)

        # 约束条件：权重之和等于1
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1.0})

        # 边界条件：每个权重在0到1之间（不允许做空）
        bounds = tuple((0.0, 1.0) for _ in range(n_assets))

        # 根据选项选择目标函数
        if option == "best_sharpe_ratio":
            objective_func = self.calculate_sharpe_ratio
            objective_args = (u, sigma, rho, risk_free_rate)
            optimization_name = "最大化夏普比率"
        elif option == "best_return":
            objective_func = self.calculate_negative_return
            objective_args = (u, sigma, rho)
            optimization_name = "最大化收益率"
        elif option == "lowest_volatility":
            objective_func = self.calculate_volatility
            objective_args = (u, sigma, rho)
            optimization_name = "最小化波动率"
        else:
            raise ValueError(f"不支持的优化选项: {option}。支持的选项: ['best_sharpe_ratio', 'best_return', 'lowest_volatility']")

        # 使用SLSQP算法进行优化
        result = minimize(
            objective_func,
            initial_weights,
            args=objective_args,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000, 'ftol': 1e-10}
        )

        if result.success:
            optimal_weights = result.x

            # 计算各项指标
            portfolioAnalysis = PortfolioAnalysis()
            portfolio_return, portfolio_volatility = portfolioAnalysis.calculate_portfolio_return_and_volatility(
                optimal_weights, u, sigma, rho)

            trading_days = 252
            annual_return = portfolio_return * trading_days
            annual_volatility = portfolio_volatility * np.sqrt(trading_days)
            sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility if annual_volatility > 0 else 0

            optimization_result = {
                'optimal_weights': optimal_weights,
                'annual_return': annual_return,
                'annual_volatility': annual_volatility,
                'sharpe_ratio': sharpe_ratio,
                'optimization_name': optimization_name,
                'success': True
            }

            return optimal_weights, optimization_result
        else:
            logger.error(f"优化失败: {result.message}")
            return None, None

    def test_optimal_portfolio_weights(self, option="best_sharpe_ratio"):
        """
        测试计算最优投资组合权重

        参数:
        - option: 优化目标 ['best_sharpe_ratio', 'best_return', 'lowest_volatility']
        """

        portfolioAnalysis = PortfolioAnalysis()

        # 定义股票池和日期范围
        stock_codes = ['C', 'JPM', 'NVDA', 'MSFT', 'AAPL']
        start_date = '20220101'
        end_date = '20260331'
        option = "best_sharpe_ratio"

        valid_options = ['best_sharpe_ratio', 'best_return', 'lowest_volatility']
        if option not in valid_options:
            logger.error(f"无效的优化选项: {option}。请使用: {valid_options}")
            return


        # 1. 从数据库获取数据并计算参数
        u, sigma, rho, actual_codes = self.prepare_data_from_clickhouse(stock_codes, start_date, end_date)

        # 2. 优化权重
        logger.info("=" * 80)
        logger.info(f"🔍 开始优化投资组合权重（{option}）")
        logger.info("=" * 80)

        optimal_weights, result = self.optimize_portfolio_weights(u, sigma, rho, option=option)

        if optimal_weights is not None and result is not None:
            logger.info("✅ 优化成功！")
            logger.info("-" * 80)
            logger.info(f"📊 最优权重配置 ({result['optimization_name']}):")
            for i, (code, weight) in enumerate(zip(actual_codes, optimal_weights)):
                logger.info(f"  {code}: {weight:.4f} ({weight * 100:.2f}%)")
            logger.info("-" * 80)

            logger.info("📈 最优投资组合计算结果")
            logger.info("-" * 80)
            logger.info(f"投资组合年化收益率: {result['annual_return']:.4f} ({result['annual_return'] * 100:.2f}%)")
            logger.info(f"投资组合年化波动率: {result['annual_volatility']:.4f} ({result['annual_volatility'] * 100:.2f}%)")
            logger.info(f"夏普比率: {result['sharpe_ratio']:.4f}")
            logger.info("=" * 80)
        else:
            logger.error("❌ 权重优化失败")

    def test_all_optimization_options(self):
        """
        测试所有优化选项并对比结果
        """
        logger.info("\n")
        logger.info("╔" + "═" * 78 + "╗")
        logger.info("║" + " " * 20 + "投资组合优化方案对比" + " " * 36 + "║")
        logger.info("╚" + "═" * 78 + "╝")
        logger.info("\n")

        # 定义股票池和日期范围
        stock_codes = ['C', 'JPM', 'NVDA', 'MSFT', 'AAPL']
        start_date = '20220101'
        end_date = '20260331'

        # 从数据库获取数据并计算参数
        u, sigma, rho, actual_codes = self.prepare_data_from_clickhouse(stock_codes, start_date, end_date)

        # 测试三种优化方案
        options = ['best_sharpe_ratio', 'best_return', 'lowest_volatility']
        results = {}

        for option in options:
            logger.info(f"\n{'=' * 80}")
            logger.info(f"正在优化: {option}")
            logger.info(f"{'=' * 80}")

            optimal_weights, result = self.optimize_portfolio_weights(u, sigma, rho, option=option)

            if optimal_weights is not None and result is not None:
                results[option] = {
                    'weights': optimal_weights,
                    'result': result
                }

                logger.info(f"✅ {result['optimization_name']} 完成")
                logger.info("-" * 80)
                for code, weight in zip(actual_codes, optimal_weights):
                    logger.info(f"  {code}: {weight:.4f} ({weight * 100:.2f}%)")
                logger.info("-" * 80)
                logger.info(f"  年化收益率: {result['annual_return'] * 100:.2f}%")
                logger.info(f"  年化波动率: {result['annual_volatility'] * 100:.2f}%")
                logger.info(f"  夏普比率: {result['sharpe_ratio']:.4f}")
            else:
                logger.error(f"❌ {option} 优化失败")

        # 对比总结
        if results:
            logger.info("\n")
            logger.info("╔" + "═" * 78 + "╗")
            logger.info("║" + " " * 30 + "优化结果对比总结" + " " * 32 + "║")
            logger.info("╚" + "═" * 78 + "╝")
            logger.info("")

            # 表头
            header = f"{'优化目标':<25} {'年化收益率':>12} {'年化波动率':>12} {'夏普比率':>10}"
            logger.info(header)
            logger.info("-" * 80)

            # 数据行
            for option, data in results.items():
                result = data['result']
                row = f"{result['optimization_name']:<20} {result['annual_return'] * 100:>11.2f}% {result['annual_volatility'] * 100:>11.2f}% {result['sharpe_ratio']:>10.4f}"
                logger.info(row)

            logger.info("=" * 80)
            logger.info("")

            # 详细权重配置
            logger.info("╔" + "═" * 78 + "╗")
            logger.info("║" + " " * 28 + "各策略最优权重配置" + " " * 30 + "║")
            logger.info("╚" + "═" * 78 + "╝")
            logger.info("")

            for option, data in results.items():
                result = data['result']
                weights = data['weights']

                logger.info(f"📊 {result['optimization_name']}")
                logger.info("-" * 80)
                for code, weight in zip(actual_codes, weights):
                    logger.info(f"  {code}: {weight:.4f} ({weight * 100:.2f}%)")
                logger.info("-" * 80)
                logger.info(f"  年化收益率: {result['annual_return'] * 100:.2f}%")
                logger.info(f"  年化波动率: {result['annual_volatility'] * 100:.2f}%")
                logger.info(f"  夏普比率: {result['sharpe_ratio']:.4f}")
                logger.info("")

            logger.info("=" * 80)

    def test_portfolio_with_data(cls):
        portfolioAnalysis = PortfolioAnalysis()

        # 定义股票池和日期范围
        stock_codes = ['C', 'JPM', 'NVDA', 'MSFT', 'AAPL']
        start_date = '20220101'
        end_date = '20260331'

        # 1. 从数据库获取数据并计算参数
        u, sigma, rho, actual_codes = cls.prepare_data_from_clickhouse(stock_codes, start_date, end_date)

        # 2. 设置权重 (示例：等权重)
        w = np.array([0.2, 0.2, 0.2, 0.2, 0.2])  # 等权重配置
        # w = np.array([0.1, 0.2, 0.2, 0.2, 0.3])
        # w = np.array([0.0, 0.2, 0.2, 0.2, 0.4])

        logger.info("=" * 80)
        logger.info("📊 投资组合分析参数")
        logger.info("=" * 80)
        logger.info(f"股票列表: {actual_codes}")
        logger.info(f"权重配置: {w}")
        logger.info(f"预期收益率 (u): {u}")
        logger.info(f"标准差 (sigma): {sigma}")
        logger.info(f"相关系数矩阵 (rho) 维度: {rho.shape}")
        logger.info("-" * 80)

        # 3. 调用原有算法计算投资组合收益和波动率
        portfolio_return, portfolio_volatility = (
            portfolioAnalysis.calculate_portfolio_return_and_volatility(w, u, sigma, rho))

        logger.info("📈 投资组合计算结果")
        logger.info("-" * 80)
        logger.info(f"投资组合日收益率: {portfolio_return:.6f} ({portfolio_return * 100:.4f}%)")
        logger.info(f"投资组合日波动率: {portfolio_volatility:.6f} ({portfolio_volatility * 100:.4f}%)")

        # 年化计算 (假设 252 个交易日)
        trading_days = 252
        annual_return = portfolio_return * trading_days
        annual_volatility = portfolio_volatility * np.sqrt(trading_days)

        logger.info(f"投资组合年化收益率: {annual_return:.4f} ({annual_return * 100:.2f}%)")
        logger.info(f"投资组合年化波动率: {annual_volatility:.4f} ({annual_volatility * 100:.2f}%)")

        # 计算夏普比率 (假设无风险利率 1.5%)
        risk_free_rate = 0.015
        sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility
        logger.info(f"夏普比率: {sharpe_ratio:.4f}")
        logger.info("=" * 80)



if __name__ == "__main__":
    portfolioAnalysisTest = PortfolioAnalysisTest()

    # portfolioAnalysisTest.test_simple_portfolio_p41()
    #
    # portfolioAnalysisTest.test_parameter_portfolio()

    # portfolioAnalysisTest.test_portfolio_with_data()

    # 测试单个优化选项
    # portfolioAnalysisTest.test_optimal_portfolio_weights(option="best_sharpe_ratio")
    # portfolioAnalysisTest.test_optimal_portfolio_weights(option="best_return")
    # portfolioAnalysisTest.test_optimal_portfolio_weights(option="lowest_volatility")

    # 测试所有优化选项并对比
    portfolioAnalysisTest.test_all_optimization_options()

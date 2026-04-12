from dataIntegrator import CommonLib
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.modelService.financialAnalysis.PortfolioAnalysis import PortfolioAnalysis
import numpy as np
from scipy.optimize import minimize

logger = CommonLib.logger
commonLib = CommonLib()

class PortfolioAnalysisTest():

    def test_simple_portfolio_p41(self):
        portfolioAnalysis = PortfolioAnalysis()

        # 示例值 P41, Example of Computing the risk of a portfolio
        logger.info("given 2 products")
        w = np.array([0.6, 0.4])  # 权重
        u = np.array([0.00, 1])  # 预期收益率
        sigma = np.array([5, 9.95])  # 标准差
        rho = np.array([[1, 0.3], [0.3, 1]])  # 相关系数矩阵
        portfolio_return, portfolio_volatility = portfolioAnalysis.calculate_portfolio_return_and_volatility(w, u, sigma, rho)
        logger.info(f"投资组合的收益率: {portfolio_return}")
        logger.info(f"投资组合的波动率: {portfolio_volatility}")

    def test_parameter_portfolio(self):
        portfolioAnalysis = PortfolioAnalysis()

        # 示例值
        logger.info("given 5 products")
        w = np.array([0.1, 0.2, 0.3, 0.25, 0.15])  # 权重
        u = np.array([0.05, 0.1, 0.15, 0.2, 0.25])  # 预期收益率
        sigma = np.array([0.1, 0.2, 0.15, 0.25, 0.18])  # 标准差
        rho = np.array([[1, 0.3, 0.2, 0.1, 0.2],
                        [0.3, 1, 0.4, 0.3, 0.25],
                        [0.2, 0.4, 1, 0.2, 0.15],
                        [0.1, 0.3, 0.2, 1, 0.2],
                        [0.2, 0.25, 0.15, 0.2, 1]])  # 相关系数矩阵
        portfolio_return, portfolio_volatility = portfolioAnalysis.calculate_portfolio_return_and_volatility(w, u, sigma, rho)
        logger.info(f"投资组合的收益率: {portfolio_return}")
        logger.info(f"投资组合的波动率: {portfolio_volatility}")

    def prepare_sql_from_clickhouse(self, stock_codes, start_date, end_date):
        """
        生成 SQL 查询语句
        """
        stock_codes_str = ','.join([f"'{code}'" for code in stock_codes])
        start_date_formatted = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
        end_date_formatted = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"

        # 大宗商品
        sql = """
            SELECT
                symbol as ts_code,
                replaceAll(toString(date), '-', '') as trade_date,
                close AS close_point
            FROM indexsysdb.df_akshare_futures_foreign_hist
            WHERE symbol in ('GC','CL','OIL','NG')
                AND close > 0
                AND date >= '2022-01-01'
                AND date <= '2026-03-31'
            order by date desc
        """
        return sql

    def prepare_data_from_clickhouse(self, sql):
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

        valid_options = ['best_sharpe_ratio', 'best_return', 'lowest_volatility']
        if option not in valid_options:
            logger.error(f"无效的优化选项: {option}。请使用: {valid_options}")
            return

        # 1. 生成 SQL 查询语句
        sql = self.prepare_sql_from_clickhouse(stock_codes, start_date, end_date)

        # 2. 从数据库获取数据并计算参数
        u, sigma, rho, actual_codes = self.prepare_data_from_clickhouse(sql)

        # 3. 优化权重
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

    def test_portfolio_with_data(self):
        portfolioAnalysis = PortfolioAnalysis()

        # 定义股票池和日期范围
        stock_codes = ['C', 'JPM', 'NVDA', 'MSFT', 'AAPL']
        start_date = '20220101'
        end_date = '20260331'

        # 生成 SQL 查询语句
        sql = self.prepare_sql_from_clickhouse(stock_codes, start_date, end_date)

        # 1. 从数据库获取数据并计算参数
        u, sigma, rho, actual_codes = self.prepare_data_from_clickhouse(sql)

        # 2. 设置权重 (示例：等权重)
        # w = np.array([0.2, 0.2, 0.2, 0.2, 0.2])  # 等权重配置
        # 2. 设置权重 (根据实际股票数量动态生成等权重)
        n_assets = len(actual_codes)
        w = np.array([1.0 / n_assets] * n_assets)

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

    portfolioAnalysisTest.test_simple_portfolio_p41()

    portfolioAnalysisTest.test_parameter_portfolio()

    portfolioAnalysisTest.test_portfolio_with_data()

    # 测试单个优化选项
    portfolioAnalysisTest.test_optimal_portfolio_weights(option="best_sharpe_ratio")
    portfolioAnalysisTest.test_optimal_portfolio_weights(option="best_return")
    portfolioAnalysisTest.test_optimal_portfolio_weights(option="lowest_volatility")

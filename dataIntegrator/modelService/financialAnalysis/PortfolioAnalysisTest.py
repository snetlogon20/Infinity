from dataIntegrator import CommonLib
from dataIntegrator.TuShareService.TushareShiborDailyService import TushareShiborDailyService
from dataIntegrator.TuShareService.TushareUSTreasuryYieldCurveService import TushareUSTreasuryYieldCurveService
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.modelService.financialAnalysis.PortfolioAnalysis import PortfolioAnalysis
import numpy as np
from scipy.optimize import minimize
import pandas as pd
import os
from dataIntegrator import CommonParameters
from dataIntegrator.utility.FileUtility import FileUtility

logger = CommonLib.logger
commonLib = CommonLib()

class PortfolioAnalysisTest():

    #def prepare_sql(self, stock_codes=None, start_date=None, end_date=None, sql_type="commodities"):
    def prepare_sql(self, start_date=None, end_date=None, sql_type="us_stocks"):
        """
        根据类型生成 SQL 查询语句

        参数:
        - stock_codes: 股票代码列表
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')
        - sql_type: SQL 类型 ['us_stocks', 'us_stocks_gold', 'china_self_selected', 'ai_selected', 'commodities']

        返回:
        - sql: SQL 查询语句
        """
        if sql_type == "us_stocks":
            # stock_codes_str = ','.join([f"'{code}'" for code in stock_codes])
            sql = f"""
                select ts_code, trade_date, close_point
                from df_tushare_us_stock_daily
                where ts_code in ('C', 'JPM', 'NVDA', 'MSFT', 'AAPL')
                AND trade_date >= '{start_date}' and trade_date <='{end_date}'
                order by trade_date asc
            """

        elif sql_type == "us_stocks_gold":
            #stock_codes_str = ','.join([f"'{code}'" for code in stock_codes])
            start_date_formatted = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
            end_date_formatted = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"
            sql = f"""
                SELECT
                    ts_code,
                    trade_date,
                    close_point
                FROM
                (
                    SELECT
                        ts_code,
                        trade_date,
                        close_point
                    FROM df_tushare_us_stock_daily
                    WHERE ts_code IN ('C', 'JPM', 'NVDA', 'MSFT', 'AAPL')
                        AND trade_date >= '{start_date}'
                        AND trade_date <= '{end_date}'
                    UNION DISTINCT
                    SELECT
                        'GC' AS ts_code,
                        replaceAll(toString(date), '-', '') AS trade_date,
                        close AS close_point
                    FROM indexsysdb.df_akshare_futures_foreign_hist
                    WHERE symbol = 'GC'
                        AND date >= '{start_date_formatted}'
                        AND date <= '{end_date_formatted}'
                        AND close > 0
                )
                ORDER BY trade_date, ts_code
            """

        elif sql_type == "china_self_selected":
            sql = f"""
                select
                    ts_code as ts_code,
                    trade_date as trade_date,
                    close as close_point
                from indexsysdb.df_tushare_stock_daily
                where ts_code in
                (
                            '002093.SZ',
                            '600490.SH',
                            '000902.SZ',
                            '601368.SH',
                            '603839.SH'
                )
                AND
                        trade_date >= '20241001' AND
                        trade_date <= '20261231'
                order by trade_date desc
             """

        elif sql_type == "ai_selected":
            sql = f"""
                select
                    ts_code as ts_code,
                    trade_date as trade_date,
                    close as close_point
                from indexsysdb.df_tushare_stock_daily
                where ts_code in
                (
                            '688585.SH',
                            '605255.SH',
                            '300476.SZ',
                            '301232.SZ',
                            '603226.SH'
                )
                AND
                        trade_date >= '20241001' AND
                        trade_date <= '20261231'
                order by trade_date desc
             """

        elif sql_type == "commodities":
            sql = """
                SELECT
                    symbol as ts_code,
                    replaceAll(toString(date), '-', '') as trade_date,
                    close AS close_point
                FROM indexsysdb.df_akshare_futures_foreign_hist
                WHERE symbol in ('GC','CL','OIL','NG','XAG','XAU')
                    AND close > 0
                    AND date >= '2022-01-01'
                    AND date <= '2026-03-31'
                order by date desc
            """

        else:
            raise ValueError(
                f"不支持的 SQL 类型: {sql_type}。支持的类型: ['us_stocks', 'us_stocks_gold', 'china_self_selected', 'ai_selected', 'commodities']")

        return sql

    def prepare_data_from_clickhouse(self, sql):
        """
        从 ClickHouse 获取数据并计算 u, sigma, rho

        参数:
        - sql: SQL 查询语句
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
            raise ValueError(
                f"不支持的优化选项: {option}。支持的选项: ['best_sharpe_ratio', 'best_return', 'lowest_volatility']")

        # 使用SLSQP算法进行优化，添加更严格的参数
        try:
            result = minimize(
                objective_func,
                initial_weights,
                args=objective_args,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={
                    'maxiter': 1000,
                    'ftol': 1e-12,
                    'disp': False
                }
            )
        except Exception as e:
            logger.error(f"优化过程发生异常: {str(e)}")

            # 如果SLSQP失败，尝试使用等权重作为备选方案
            logger.warning("SLSQP优化失败，使用等权重作为备选方案")
            optimal_weights = initial_weights
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
                'optimization_name': optimization_name + " (备选: 等权重)",
                'success': False
            }

            return optimal_weights, optimization_result

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

            # 尝试使用等权重作为备选方案
            logger.warning("优化未收敛，使用等权重作为备选方案")
            optimal_weights = initial_weights
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
                'optimization_name': optimization_name + " (备选: 等权重)",
                'success': False
            }

            return optimal_weights, optimization_result

    def test_all_optimization_options(self, start_date, end_date, interest_country, sql_type):
        """
        测试所有优化选项并对比结果
        """
        logger.info("\n")
        logger.info("╔" + "═" * 78 + "╗")
        logger.info("║" + " " * 20 + "投资组合优化方案对比" + " " * 36 + "║")
        logger.info("╚" + "═" * 78 + "╝")
        logger.info("\n")

        sql = self.prepare_sql(start_date, end_date, sql_type)
        u, sigma, rho, actual_codes = self.prepare_data_from_clickhouse(sql)

        # 测试三种优化方案
        options = ['best_sharpe_ratio', 'best_return', 'lowest_volatility']
        results = {}

        # 用于存储最终的 DataFrame 数据
        result_data = []
        # 用于存储指标级别的 DataFrame 数据
        metrics_data = []

        for option in options:
            logger.info(f"\n{'=' * 80}")
            logger.info(f"正在优化: {option}")
            logger.info(f"{'=' * 80}")

            if interest_country == "US":
                # 根据输入的起止日期计算使用的年化收益率
                tushareUSTreasuryYieldCurveService = TushareUSTreasuryYieldCurveService()
                avg_yield, earliest_yield, latest_yield, max_yield, min_yield = tushareUSTreasuryYieldCurveService.get_yield_for_term(
                    start_date, end_date)

                logger.info(f"平均收益率: {avg_yield:.4f}")
                logger.info(f"最早日期收益率: {earliest_yield:.4f}")
                logger.info(f"最晚日期收益率: {latest_yield:.4f}")
                logger.info(f"最大收益率: {max_yield:.4f}")
                logger.info(f"最小收益率: {min_yield:.4f}")

            else:
                tushareShiborDailyService = TushareShiborDailyService()
                avg_rate, earliest_rate, latest_rate, max_rate, min_rate = tushareShiborDailyService.get_rate_for_term(
                    start_date, end_date)

                logger.info(f"平均收益率: {avg_rate:.4f}")
                logger.info(f"最早日期收益率: {earliest_rate:.4f}")
                logger.info(f"最晚日期收益率: {latest_rate:.4f}")
                logger.info(f"最大收益率: {max_rate:.4f}")
                logger.info(f"最小收益率: {min_rate:.4f}")

                latest_yield = latest_rate

            logger.info(f"最终选取收益率: {latest_yield:.4f}")
            optimal_weights, result = self.optimize_portfolio_weights(u, sigma, rho, option=option,
                                                                      risk_free_rate=latest_yield)

            if optimal_weights is not None and result is not None:
                results[option] = {
                    'weights': optimal_weights,
                    'result': result
                }

                logger.info(f"✅ {result['optimization_name']} 完成")
                logger.info("-" * 80)
                for code, weight in zip(actual_codes, optimal_weights):
                    logger.info(f"  {code}: {weight:.4f} ({weight * 100:.2f}%)")

                    # 将数据添加到结果列表中
                    result_data.append({
                        'date': end_date,
                        'strategy': result['optimization_name'],
                        'products': code,
                        'rate': weight
                    })

                logger.info("-" * 80)
                logger.info(f"  年化收益率: {result['annual_return'] * 100:.2f}%")
                logger.info(f"  年化波动率: {result['annual_volatility'] * 100:.2f}%")
                logger.info(f"  夏普比率: {result['sharpe_ratio']:.4f}")

                # 记录指标级别的数据
                metrics_data.append({
                    'date': end_date,
                    '优化目标': result['optimization_name'],
                    '年化收益率': result['annual_return'] * 100,
                    '年化波动率': result['annual_volatility'] * 100,
                    '夏普比率': result['sharpe_ratio']
                })
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

        # 创建 DataFrame 并保存到磁盘
        result_dfs = {}

        if result_data:
            result_df = pd.DataFrame(result_data)
            result_dfs['products'] = result_df
        else:
            result_df = None

        # 创建指标 DataFrame
        if metrics_data:
            metrics_df = pd.DataFrame(metrics_data)
            result_dfs['metrics'] = metrics_df

            logger.info("\n优化指标 DataFrame 预览:")
            logger.info(metrics_df.to_string(index=False))

        return result_dfs if result_dfs else None


if __name__ == "__main__":
    portfolioAnalysisTest = PortfolioAnalysisTest()

    # 测试所有优化选项并对比
    # start_date = '20260101'
    # end_date = '20260331'
    # interest_country = "US" # US, CN
    # sql_type = "us_stocks"  # us_stocks, us_stocks_gold, china_self_selected, ai_selected, commodities

    # start_date = '20240101'
    # end_date = '20260331'
    # interest_country = "US" # US, CN
    # sql_type = "us_stocks"  # us_stocks, us_stocks_gold, china_self_selected, ai_selected, commodities
    # result_df = portfolioAnalysisTest.test_all_optimization_options(start_date, end_date, interest_country, sql_type)

    from datetime import datetime, timedelta

    # 循环参数设置
    # end_date_start = '20260301'  # end_date 起始日期
    # end_date_end = '20260331'  # end_date 结束日期（可根据需要调整）
    # interest_country = "US"  # US, CN
    # sql_type = "us_stocks"  # us_stocks, us_stocks_gold, china_self_selected, ai_selected, commodities

    # end_date_start = '20251001'  # end_date 起始日期
    # end_date_end = '20260331'  # end_date 结束日期（可根据需要调整）
    # interest_country = "CN"  # US, CN
    # sql_type = "ai_selected"  # us_stocks, us_stocks_gold, china_self_selected, ai_selected, commodities

    # end_date_start = '20230301'  # end_date 起始日期
    # end_date_end = '20260411'  # end_date 结束日期（可根据需要调整）
    # interest_country = "US"  # US, CN
    # sql_type = "us_stocks_gold"  # us_stocks, us_stocks_gold, china_self_selected, ai_selected, commodities

    # end_date_start = '20230301'  # end_date 起始日期
    # end_date_end = '20260411'  # end_date 结束日期（可根据需要调整）
    # interest_country = "CN"  # US, CN
    # sql_type = "china_self_selected"  # us_stocks, us_stocks_gold, china_self_selected, ai_selected, commodities

    # end_date_start = '20260301'  # end_date 起始日期
    # end_date_end = '20260411'  # end_date 结束日期（可根据需要调整）
    # interest_country = "CN"  # US, CN
    # sql_type = "ai_selected"  # us_stocks, us_stocks_gold, china_self_selected, ai_selected, commodities

    end_date_start = '20240301'  # end_date 起始日期
    end_date_end = '20260411'  # end_date 结束日期（可根据需要调整）
    interest_country = "US"  # US, CN
    sql_type = "commodities"  # us_stocks, us_stocks_gold, china_self_selected, ai_selected, commodities

    # 初始化日期
    current_end_date = datetime.strptime(end_date_start, '%Y%m%d')
    final_end_date = datetime.strptime(end_date_end, '%Y%m%d')

    # 存储所有结果的 DataFrame 列表
    all_products_results = []
    all_metrics_results = []

    logger.info("=" * 80)
    logger.info(f"开始循环优化测试")
    logger.info(f"end_date 范围: {end_date_start} 到 {end_date_end}")
    logger.info(f"interest_country: {interest_country}")
    logger.info(f"sql_type: {sql_type}")
    logger.info("=" * 80)

    # 循环遍历每个日历日
    while current_end_date <= final_end_date:
        # 格式化当前日期
        current_end_date_str = current_end_date.strftime('%Y%m%d')
        # start_date 是 end_date 往前推2年
        current_start_date = current_end_date - timedelta(days=730)  # 2年 = 730天
        current_start_date_str = current_start_date.strftime('%Y%m%d')

        logger.info("\n" + "=" * 80)
        logger.info(f"处理日期: end_date={current_end_date_str}, start_date={current_start_date_str}")
        logger.info("=" * 80 + "\n")

        try:
            # 执行优化测试
            result_dfs = portfolioAnalysisTest.test_all_optimization_options(
                current_start_date_str,
                current_end_date_str,
                interest_country,
                sql_type
            )

            # 如果返回了 DataFrame，保存并添加到结果列表
            if result_dfs is not None:
                # 在循环中立即保存到磁盘
                single_file_name = f"portfolio_optimization_{current_end_date_str}"

                # 保存 products DataFrame
                if 'products' in result_dfs:
                    products_df = result_dfs['products']

                    all_products_results.append(products_df)

                # 保存 metrics DataFrame
                if 'metrics' in result_dfs:
                    metrics_df = result_dfs['metrics']

                    all_metrics_results.append(metrics_df)

                logger.info(f"✅ {current_end_date_str} 处理完成")
            else:
                logger.warning(f"⚠️ {current_end_date_str} 未返回结果")

        except Exception as e:
            logger.error(f"❌ {current_end_date_str} 处理失败: {str(e)}")

        # end_date + 1 天
        current_end_date += timedelta(days=1)

    # 合并所有 products 结果
    if all_products_results:
        final_products_df = pd.concat(all_products_results, ignore_index=True)

        # 保存到磁盘
        output_file_name = FileUtility.generate_filename_by_timestamp(
            f"portfolio_optimization_all_products_{end_date_start}_to_{end_date_end}",
            "csv"
        )

        csv_file_path = os.path.join(CommonParameters.outBoundPath, f"{output_file_name}.csv")
        final_products_df.to_csv(csv_file_path, index=False, encoding='utf-8-sig')
        logger.info(f"\n✅ 所有 products 结果已合并并保存到 CSV: {csv_file_path}")

        excel_file_path = os.path.join(CommonParameters.outBoundPath, f"{output_file_name}.xlsx")
        final_products_df.to_excel(excel_file_path, index=False)
        logger.info(f"✅ 所有 products 结果已保存到 Excel: {excel_file_path}")

        # 打印统计信息
        logger.info("\n" + "=" * 80)
        logger.info("最终 Products 结果统计:")
        logger.info(f"总记录数: {len(final_products_df)}")
        logger.info(f"日期范围: {final_products_df['date'].min()} 到 {final_products_df['date'].max()}")
        logger.info(f"策略类型: {final_products_df['strategy'].unique()}")
        logger.info(f"产品列表: {final_products_df['products'].unique()}")
        logger.info("=" * 80)

    # 合并所有 metrics 结果
    if all_metrics_results:
        final_metrics_df = pd.concat(all_metrics_results, ignore_index=True)

        # 保存到磁盘
        metrics_file_name = FileUtility.generate_filename_by_timestamp(
            f"portfolio_optimization_all_metrics_{end_date_start}_to_{end_date_end}",
            "xlsx"
        )
        metrics_excel_path = os.path.join(CommonParameters.outBoundPath, f"{metrics_file_name}.xlsx")
        final_metrics_df.to_excel(metrics_excel_path, index=False)
        logger.info(f"✅ 所有 metrics 结果已保存到 Excel: {metrics_excel_path}")

        # 打印统计信息
        logger.info("\n" + "=" * 80)
        logger.info("最终 Metrics 结果统计:")
        logger.info(f"总记录数: {len(final_metrics_df)}")
        logger.info(f"日期范围: {final_metrics_df['date'].min()} 到 {final_metrics_df['date'].max()}")
        logger.info(f"优化目标: {final_metrics_df['优化目标'].unique()}")
        logger.info("=" * 80)

        # 打印前20条记录预览
        logger.info("\nMetrics DataFrame 预览（前20条）:")
        logger.info(final_metrics_df.head(20).to_string(index=False))


    # ==================== 开始绘图 ====================
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib import rcParams

    # 设置中文字体
    rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
    rcParams['axes.unicode_minus'] = False

    # 图1: 三种优化策略的指标对比（按日期）
    if all_metrics_results:
        final_metrics_df_plot = pd.concat(all_metrics_results, ignore_index=True)
        final_metrics_df_plot['date'] = pd.to_datetime(final_metrics_df_plot['date'], format='%Y%m%d')
        final_metrics_df_plot = final_metrics_df_plot.sort_values('date')

        fig, axes = plt.subplots(3, 1, figsize=(14, 12))
        fig.suptitle('投资组合优化策略对比分析', fontsize=16, fontweight='bold')

        strategies = ['最大化夏普比率', '最大化收益率', '最小化波动率']
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
        markers = ['o', 's', '^']

        for idx, (metric, title, ylabel) in enumerate([
            ('年化收益率', '年化收益率对比 (%)', '收益率 (%)'),
            ('年化波动率', '年化波动率对比 (%)', '波动率 (%)'),
            ('夏普比率', '夏普比率对比', '夏普比率')
        ]):
            ax = axes[idx]
            for strategy, color, marker in zip(strategies, colors, markers):
                strategy_data = final_metrics_df_plot[final_metrics_df_plot['优化目标'] == strategy]
                if not strategy_data.empty:
                    ax.plot(strategy_data['date'], strategy_data[metric],
                           label=strategy, color=color, marker=marker,
                           linewidth=2, markersize=4, alpha=0.8)

            ax.set_title(title, fontsize=12, fontweight='bold')
            ax.set_xlabel('日期', fontsize=10)
            ax.set_ylabel(ylabel, fontsize=10)
            ax.legend(loc='best', fontsize=9)
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()
        metrics_plot_path = os.path.join(CommonParameters.outBoundPath, 'portfolio_optimization_strategies_comparison.png')
        plt.savefig(metrics_plot_path, dpi=300, bbox_inches='tight')
        logger.info(f"✅ 策略对比图已保存: {metrics_plot_path}")
        plt.close()

    # 图2: 按策略分组的综合对比图
    if all_products_results:
        final_products_df_plot = pd.concat(all_products_results, ignore_index=True)
        final_products_df_plot['date'] = pd.to_datetime(final_products_df_plot['date'], format='%Y%m%d')
        final_products_df_plot = final_products_df_plot.sort_values('date')

        fig, axes = plt.subplots(3, 1, figsize=(16, 12))
        fig.suptitle('各策略下产品权重配置对比', fontsize=16, fontweight='bold')

        strategies = ['最大化夏普比率', '最大化收益率', '最小化波动率']

        # 为每个产品分配不同的颜色
        products = final_products_df_plot['products'].unique()
        product_colors = plt.cm.tab10(np.linspace(0, 1, len(products)))
        product_markers = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h']

        for idx, strategy in enumerate(strategies):
            ax = axes[idx]
            strategy_data = final_products_df_plot[final_products_df_plot['strategy'] == strategy]

            if not strategy_data.empty:
                for prod_idx, product in enumerate(products):
                    product_data = strategy_data[strategy_data['products'] == product]
                    if not product_data.empty:
                        color = product_colors[prod_idx % len(product_colors)]
                        marker = product_markers[prod_idx % len(product_markers)]

                        ax.plot(product_data['date'], product_data['rate'] * 100,
                               label=product, color=color, marker=marker,
                               linewidth=2, markersize=4, alpha=0.85)

                ax.set_title(f'📊 {strategy}', fontsize=13, fontweight='bold',
                           loc='left', pad=10)
                ax.set_xlabel('日期', fontsize=11)
                ax.set_ylabel('权重 (%)', fontsize=11)
                ax.legend(loc='upper right', fontsize=9, ncol=2, framealpha=0.95, shadow=True)
                ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.8)
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

                # 设置Y轴范围动态调整
                if not product_data.empty:
                    y_min = strategy_data['rate'].min() * 100
                    y_max = strategy_data['rate'].max() * 100
                    y_padding = (y_max - y_min) * 0.1 if y_max > y_min else 10
                    ax.set_ylim(max(0, y_min - y_padding), y_max + y_padding)

        plt.tight_layout()
        combined_plot_path = os.path.join(CommonParameters.outBoundPath, 'portfolio_strategies_products_weights.png')
        plt.savefig(combined_plot_path, dpi=300, bbox_inches='tight')
        logger.info(f"✅ 策略产品权重分组图已保存: {combined_plot_path}")
        plt.close()

    logger.info("\n" + "=" * 80)
    logger.info("📊 所有图表生成完成！")
    logger.info("=" * 80)


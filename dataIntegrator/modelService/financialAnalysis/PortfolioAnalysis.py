import os
from datetime import datetime

import pandas as pd

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.TuShareService.TushareShiborDailyService import TushareShiborDailyService
from dataIntegrator.TuShareService.TushareUSTreasuryYieldCurveService import TushareUSTreasuryYieldCurveService
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
import numpy as np
from scipy.optimize import minimize
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams
from dataIntegrator.utility.FileUtility import FileUtility

logger = CommonLib.logger
commonLib = CommonLib()

class PortfolioAnalysis(TuShareService):

    def __init__(self):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="PortfolioVolatilityCalculator started")

    def calculate_portfolio_return_and_volatility(self, weight, mean, sigma, rho):
        n = len(weight)

        # 生成协方差矩阵
        cov_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i == j:
                    cov_matrix[i][j] = sigma[i] ** 2
                else:
                    cov_matrix[i][j] = rho[i][j] * sigma[i] * sigma[j]

        # 确保协方差矩阵是对称的
        cov_matrix = (cov_matrix + cov_matrix.T) / 2

        # 检查并修正协方差矩阵的正定性
        eigenvalues = np.linalg.eigvalsh(cov_matrix)
        if np.any(eigenvalues < 0):
            # 添加一个小的正则化项使矩阵正定
            min_eigenvalue = np.min(eigenvalues)
            if min_eigenvalue < 0:
                cov_matrix += (-min_eigenvalue + 1e-8) * np.eye(n)
                logger.warning(f"协方差矩阵不是正定的，已添加正则化项: {-min_eigenvalue + 1e-8}")

        # 计算投资组合收益
        portfolio_return = np.dot(weight, mean)
        # 计算投资组合方差
        portfolio_variance = np.dot(weight, np.dot(cov_matrix, weight))

        # 数值保护：确保方差非负
        if portfolio_variance < 0:
            portfolio_variance = abs(portfolio_variance)
            logger.warning(f"投资组合方差为负数，已取绝对值: {portfolio_variance}")

        # 计算投资组合波动率
        portfolio_volatility = np.sqrt(portfolio_variance)

        return portfolio_return, portfolio_volatility

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

    def execute_full_analysis_workflow(self, end_date_start, end_date_end, interest_country, sql_type,
                                       prepare_sql_func):
        """
        执行完整的投资组合分析工作流

        包括：
        1. 滚动窗口优化
        2. 合并保存结果
        3. 生成 PDF 报告
        4. 生成 PNG 图表

        参数:
        - end_date_start: 结束日期起始值 (格式: 'YYYYMMDD')
        - end_date_end: 结束日期终止值 (格式: 'YYYYMMDD')
        - interest_country: 利率国家 ('US' 或 'CN')
        - sql_type: SQL 类型
        - prepare_sql_func: SQL 生成函数（由外部传入）

        返回:
        - all_products_results: 产品权重结果列表
        - all_metrics_results: 指标结果列表
        - pdf_path: PDF 报告路径
        """
        logger.info("=" * 80)
        logger.info("🚀 开始执行完整分析工作流")
        logger.info(f"   日期范围: {end_date_start} 至 {end_date_end}")
        logger.info(f"   利率国家: {interest_country}")
        logger.info(f"   数据类型: {sql_type}")
        logger.info("=" * 80)

        # 步骤1: 滚动优化
        logger.info("\n📊 步骤 1/4: 执行滚动窗口优化...")
        all_products_results, all_metrics_results = self.run_rolling_optimization(
            end_date_start,
            end_date_end,
            interest_country,
            sql_type,
            prepare_sql_func
        )

        # 步骤2: 合并保存结果
        logger.info("\n💾 步骤 2/4: 合并并保存结果...")
        self.merge_and_save_results(all_products_results, all_metrics_results, end_date_start, end_date_end)

        # 步骤3: 生成 PDF 报告
        logger.info("\n📄 步骤 3/4: 生成 PDF 报告...")
        pdf_path = self.generate_pdf_report(
            all_products_results,
            all_metrics_results,
            end_date_start,
            end_date_end,
            sql_type
        )

        # 步骤4: 生成 PNG 图表
        logger.info("\n📈 步骤 4/4: 生成 PNG 图表...")
        self.plot_optimization_results(all_products_results, all_metrics_results)

        logger.info("\n" + "=" * 80)
        logger.info("✅ 完整分析工作流执行完毕！")
        logger.info(f"   PDF 报告: {pdf_path}")
        logger.info("=" * 80)

        return all_products_results, all_metrics_results, pdf_path

    #外围处理的主程序
    def run_rolling_optimization(self, end_date_start, end_date_end, interest_country, sql_type, prepare_sql_func):
        """
        执行滚动窗口投资组合优化

        参数:
        - end_date_start: 结束日期起始值 (格式: 'YYYYMMDD')
        - end_date_end: 结束日期终止值 (格式: 'YYYYMMDD')
        - interest_country: 利率国家 ('US' 或 'CN')
        - sql_type: SQL 类型
        - prepare_sql_func: SQL 生成函数（由外部传入）

        返回:
        - all_products_results: 产品权重结果列表
        - all_metrics_results: 指标结果列表
        """
        from datetime import datetime, timedelta

        # 初始化结果列表
        all_products_results = []
        all_metrics_results = []

        # 转换日期
        current_end_date = datetime.strptime(end_date_start, '%Y%m%d')
        final_end_date = datetime.strptime(end_date_end, '%Y%m%d')

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
                sql = prepare_sql_func(current_start_date_str, current_end_date_str, sql_type)

                result_dfs, latest_yield = self.test_all_optimization_options(
                    current_start_date_str,
                    current_end_date_str,
                    interest_country,
                    sql
                )

                # 如果返回了 DataFrame，保存并添加到结果列表
                if result_dfs is not None:
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

        return all_products_results, all_metrics_results

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

    def test_all_optimization_options(self, start_date, end_date, interest_country, sql):
        """
        测试所有优化选项并对比结果
        """
        logger.info("\n")
        logger.info("╔" + "═" * 78 + "╗")
        logger.info("║" + " " * 20 + "投资组合优化方案对比" + " " * 36 + "║")
        logger.info("╚" + "═" * 78 + "╝")
        logger.info("\n")

        #sql = self.prepare_sql(start_date, end_date, sql_type)
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
                        'rate': weight,
                        'risk_free_rate': latest_yield
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
                    '夏普比率': result['sharpe_ratio'],
                    '无风险利率': latest_yield
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

        return (result_dfs, latest_yield) if result_dfs else (None, None)

    def merge_and_save_results(self, all_products_results, all_metrics_results, end_date_start, end_date_end):
        """
        合并并保存投资组合优化结果

        参数:
        - all_products_results: 产品权重结果列表
        - all_metrics_results: 指标结果列表
        - end_date_start: 开始日期
        - end_date_end: 结束日期
        """
        # 合并所有 products 结果
        if all_products_results:
            final_products_df = pd.concat(all_products_results, ignore_index=True)

            # 保存到磁盘
            output_file_name = FileUtility.generate_filename_by_timestamp(
                f"portfolio_optimization_all_products_{end_date_start}_to_{end_date_end}", "xlsx"
            )

            excel_file_path = os.path.join(CommonParameters.outBoundPath, output_file_name)
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
            metrics_excel_path = os.path.join(CommonParameters.outBoundPath, metrics_file_name)
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


    def plot_optimization_results(self, all_products_results, all_metrics_results):
        """
        绘制投资组合优化结果图表

        参数:
        - all_products_results: 产品权重结果列表
        - all_metrics_results: 指标结果列表
        """

        # 设置中文字体
        rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
        rcParams['axes.unicode_minus'] = False

        # 图1: 三种优化策略的指标对比（按日期）
        if all_metrics_results:
            final_metrics_df_plot = pd.concat(all_metrics_results, ignore_index=True)
            final_metrics_df_plot['date'] = pd.to_datetime(final_metrics_df_plot['date'], format='%Y%m%d')
            final_metrics_df_plot = final_metrics_df_plot.sort_values('date')

            fig, axes = plt.subplots(3, 1, figsize=(14, 14))
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

                # 绘制三种策略的指标
                for strategy, color, marker in zip(strategies, colors, markers):
                    strategy_data = final_metrics_df_plot[final_metrics_df_plot['优化目标'] == strategy]
                    if not strategy_data.empty:
                        ax.plot(strategy_data['date'], strategy_data[metric],
                                label=strategy, color=color, marker=marker,
                                linewidth=2, markersize=4, alpha=0.8)

                # 添加无风险利率（仅在年化收益率图中显示）
                if metric == '年化收益率' and '无风险利率' in final_metrics_df_plot.columns:
                    ax2 = ax.twinx()

                    # 获取无风险利率数据（去重）
                    risk_free_data = final_metrics_df_plot[['date', '无风险利率']].drop_duplicates(subset=['date'])
                    risk_free_data = risk_free_data.sort_values('date')

                    # 转换为百分比并绘制
                    ax2.plot(risk_free_data['date'], risk_free_data['无风险利率'] * 100,
                             color='red', linestyle='--', linewidth=2.5, alpha=0.7,
                             label='无风险利率', marker='s', markersize=5)

                    # 设置右侧 Y 轴
                    ax2.set_ylabel('无风险利率 (%)', fontsize=10, color='red')
                    ax2.tick_params(axis='y', labelcolor='red')
                    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.2f}'))

                    # 动态调整右侧 Y 轴范围
                    rf_min = risk_free_data['无风险利率'].min() * 100
                    rf_max = risk_free_data['无风险利率'].max() * 100
                    rf_padding = (rf_max - rf_min) * 0.2 if rf_max > rf_min else 0.5
                    ax2.set_ylim(max(0, rf_min - rf_padding), rf_max + rf_padding)

                    # 合并图例
                    lines1, labels1 = ax.get_legend_handles_labels()
                    lines2, labels2 = ax2.get_legend_handles_labels()
                    ax.legend(lines1 + lines2, labels1 + labels2,
                              loc='best', fontsize=9, framealpha=0.95, shadow=True)
                else:
                    ax.legend(loc='best', fontsize=9)

                ax.set_title(title, fontsize=12, fontweight='bold')
                ax.set_xlabel('日期', fontsize=10)
                ax.set_ylabel(ylabel, fontsize=10)
                ax.grid(True, alpha=0.3, linestyle='--')
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

            plt.tight_layout()
            metrics_plot_path = os.path.join(CommonParameters.outBoundPath,
                                             FileUtility.generate_filename_by_timestamp(
                                                 'portfolio_optimization_strategies_comparison', 'png'))
            plt.savefig(metrics_plot_path, dpi=300, bbox_inches='tight')
            logger.info(f"策略对比图已保存: {metrics_plot_path}")
            plt.close()

    # 图2: 按策略分组的综合对比图
        if all_products_results:
            final_products_df_plot = pd.concat(all_products_results, ignore_index=True)
            final_products_df_plot['date'] = pd.to_datetime(final_products_df_plot['date'], format='%Y%m%d')
            final_products_df_plot = final_products_df_plot.sort_values('date')

            fig, axes = plt.subplots(3, 1, figsize=(16, 14))
            fig.suptitle('各策略下产品权重配置与无风险利率对比', fontsize=16, fontweight='bold')

            strategies = ['最大化夏普比率', '最大化收益率', '最小化波动率']

            # 为每个产品分配不同的颜色
            products = final_products_df_plot['products'].unique()
            product_colors = plt.cm.tab10(np.linspace(0, 1, len(products)))
            product_markers = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h']

            for idx, strategy in enumerate(strategies):
                ax = axes[idx]
                strategy_data = final_products_df_plot[final_products_df_plot['strategy'] == strategy]

                if not strategy_data.empty:
                    # 创建右侧 Y 轴用于显示无风险利率
                    ax2 = ax.twinx()

                    # 绘制产品权重（左侧 Y 轴）
                    for prod_idx, product in enumerate(products):
                        product_data = strategy_data[strategy_data['products'] == product]
                        if not product_data.empty:
                            color = product_colors[prod_idx % len(product_colors)]
                            marker = product_markers[prod_idx % len(product_markers)]

                            ax.plot(product_data['date'], product_data['rate'] * 100,
                                    label=product, color=color, marker=marker,
                                    linewidth=2, markersize=4, alpha=0.85)

                    # 绘制无风险利率（右侧 Y 轴）- 转换为百分比
                    if 'risk_free_rate' in strategy_data.columns:
                        risk_free_data = strategy_data[['date', 'risk_free_rate']].drop_duplicates(subset=['date'])
                        risk_free_data = risk_free_data.sort_values('date')

                        ax2.plot(risk_free_data['date'], risk_free_data['risk_free_rate'] * 100,
                                 color='red', linestyle='--', linewidth=2.5, alpha=0.7,
                                 label='无风险利率', marker='s', markersize=5)

                        # 设置右侧 Y 轴
                        ax2.set_ylabel('无风险利率 (%)', fontsize=11, color='red')
                        ax2.tick_params(axis='y', labelcolor='red')
                        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.2f}%'))

                        # 动态调整右侧 Y 轴范围
                        rf_min = risk_free_data['risk_free_rate'].min() * 100
                        rf_max = risk_free_data['risk_free_rate'].max() * 100
                        rf_padding = (rf_max - rf_min) * 0.2 if rf_max > rf_min else 0.5
                        ax2.set_ylim(max(0, rf_min - rf_padding), rf_max + rf_padding)

                    ax.set_title(f'{strategy}', fontsize=13, fontweight='bold',
                                 loc='left', pad=10)
                    ax.set_xlabel('日期', fontsize=11)
                    ax.set_ylabel('权重 (%)', fontsize=11)

                    # 合并两个轴的图例
                    lines1, labels1 = ax.get_legend_handles_labels()
                    lines2, labels2 = ax2.get_legend_handles_labels()
                    ax.legend(lines1 + lines2, labels1 + labels2,
                              loc='upper right', fontsize=9, ncol=2,
                              framealpha=0.95, shadow=True)

                    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.8)
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
                    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

                    # 设置左侧 Y 轴范围动态调整
                    y_min = strategy_data['rate'].min() * 100
                    y_max = strategy_data['rate'].max() * 100
                    y_padding = (y_max - y_min) * 0.1 if y_max > y_min else 10
                    ax.set_ylim(max(0, y_min - y_padding), y_max + y_padding)

            plt.tight_layout()
            combined_plot_path = os.path.join(CommonParameters.outBoundPath,
                                              FileUtility.generate_filename_by_timestamp(
                                                  'portfolio_strategies_products_weights', 'png'))
            plt.savefig(combined_plot_path, dpi=300, bbox_inches='tight')
            logger.info(f"策略产品权重分组图已保存: {combined_plot_path}")
            plt.close()

        logger.info("\n" + "=" * 80)
        logger.info("所有图表生成完成！")
        logger.info("=" * 80)

    def generate_pdf_report(self, all_products_results, all_metrics_results, end_date_start, end_date_end,
                            sql_type="unknown"):
        """
        生成专业的金融报告 PDF

        参数:
        - all_products_results: 产品权重结果列表
        - all_metrics_results: 指标结果列表
        - end_date_start: 开始日期
        - end_date_end: 结束日期
        - sql_type: SQL 类型（用于区分不同报告）
        """
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch, cm
        from reportlab.lib import colors
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import tempfile

        # 注册中文字体 - 尝试多个可能的路径
        chinese_font = 'Helvetica'
        font_paths = [
            'C:/Windows/Fonts/simhei.ttf',  # 黑体
            'C:/Windows/Fonts/msyh.ttc',  # 微软雅黑
            'C:/Windows/Fonts/msyh.ttf',  # 微软雅黑 (旧版)
            'C:/Windows/Fonts/simsun.ttc',  # 宋体
        ]

        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    font_name = os.path.basename(font_path).split('.')[0]
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    chinese_font = font_name
                    logger.info(f"成功加载中文字体: {font_path}")
                    break
            except Exception as e:
                logger.warning(f"字体加载失败 {font_path}: {e}")
                continue

        if chinese_font == 'Helvetica':
            logger.warning("未找到中文字体，PDF 中的中文可能无法正常显示")

        # 生成临时图表文件
        temp_files = []

        # 生成图表1：策略对比
        chart1_path = None
        if all_metrics_results:
            final_metrics_df_plot = pd.concat(all_metrics_results, ignore_index=True)
            final_metrics_df_plot['date'] = pd.to_datetime(final_metrics_df_plot['date'], format='%Y%m%d')
            final_metrics_df_plot = final_metrics_df_plot.sort_values('date')

            fig, axes = plt.subplots(3, 1, figsize=(14, 12))
            fig.suptitle('投资组合优化策略对比分析', fontsize=16, fontweight='bold', fontname=chinese_font)

            strategies = ['最大化夏普比率', '最大化收益率', '最小化波动率']
            colors_list = ['#FF6B6B', '#4ECDC4', '#45B7D1']
            markers = ['o', 's', '^']

            for idx, (metric, title, ylabel) in enumerate([
                ('年化收益率', '年化收益率对比 (%)', '收益率 (%)'),
                ('年化波动率', '年化波动率对比 (%)', '波动率 (%)'),
                ('夏普比率', '夏普比率对比', '夏普比率')
            ]):
                ax = axes[idx]
                for strategy, color, marker in zip(strategies, colors_list, markers):
                    strategy_data = final_metrics_df_plot[final_metrics_df_plot['优化目标'] == strategy]
                    if not strategy_data.empty:
                        ax.plot(strategy_data['date'], strategy_data[metric],
                                label=strategy, color=color, marker=marker,
                                linewidth=2, markersize=4, alpha=0.8)

                ax.set_title(title, fontsize=12, fontweight='bold', fontname=chinese_font)
                ax.set_xlabel('日期', fontsize=10, fontname=chinese_font)
                ax.set_ylabel(ylabel, fontsize=10, fontname=chinese_font)
                ax.legend(loc='best', fontsize=9, prop={'family': chinese_font})
                ax.grid(True, alpha=0.3, linestyle='--')
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

            plt.tight_layout()
            chart1_path = os.path.join(tempfile.gettempdir(), 'chart1.png')
            plt.savefig(chart1_path, dpi=150, bbox_inches='tight')
            temp_files.append(chart1_path)
            plt.close()

        # 生成图表2：产品权重
        chart2_path = None
        if all_products_results:
            final_products_df_plot = pd.concat(all_products_results, ignore_index=True)
            final_products_df_plot['date'] = pd.to_datetime(final_products_df_plot['date'], format='%Y%m%d')
            final_products_df_plot = final_products_df_plot.sort_values('date')

            fig, axes = plt.subplots(3, 1, figsize=(16, 12))
            fig.suptitle('各策略下产品权重配置对比', fontsize=16, fontweight='bold', fontname=chinese_font)

            strategies = ['最大化夏普比率', '最大化收益率', '最小化波动率']
            products = final_products_df_plot['products'].unique()
            product_colors = plt.cm.tab10(np.linspace(0, 1, len(products)))

            for idx, strategy in enumerate(strategies):
                ax = axes[idx]
                strategy_data = final_products_df_plot[final_products_df_plot['strategy'] == strategy]

                if not strategy_data.empty:
                    for prod_idx, product in enumerate(products):
                        product_data = strategy_data[strategy_data['products'] == product]
                        if not product_data.empty:
                            color = product_colors[prod_idx % len(product_colors)]
                            ax.plot(product_data['date'], product_data['rate'] * 100,
                                    label=product, color=color, linewidth=2, alpha=0.85)

                    ax.set_title(strategy, fontsize=13, fontweight='bold', fontname=chinese_font, loc='left')
                    ax.set_xlabel('日期', fontsize=11, fontname=chinese_font)
                    ax.set_ylabel('权重 (%)', fontsize=11, fontname=chinese_font)
                    ax.legend(loc='upper right', fontsize=9, prop={'family': chinese_font}, ncol=2)
                    ax.grid(True, alpha=0.3, linestyle='--')
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
                    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

            plt.tight_layout()
            chart2_path = os.path.join(tempfile.gettempdir(), 'chart2.png')
            plt.savefig(chart2_path, dpi=150, bbox_inches='tight')
            temp_files.append(chart2_path)
            plt.close()

        # 创建 PDF - 文件名中包含 sql_type
        pdf_filename = FileUtility.generate_filename_by_timestamp(
            f"portfolio_report_{sql_type}_{end_date_start}_to_{end_date_end}", "pdf"
        )
        pdf_path = os.path.join(CommonParameters.outBoundPath, pdf_filename)

        doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4),
                                rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=18)

        # 获取页面可用宽度
        page_width = landscape(A4)[0] - 144  # 减去左右边距
        page_height = landscape(A4)[1] - 90  # 减去上下边距

        # 样式
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            leading=32,
            alignment=1,
            fontName=chinese_font,
            spaceAfter=30
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            leading=24,
            fontName=chinese_font,
            spaceAfter=12,
            spaceBefore=12
        )
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            fontName=chinese_font
        )

        story = []

        # 标题页 - 添加 sql_type 信息
        story.append(Paragraph('投资组合优化分析报告', title_style))
        story.append(Spacer(1, 0.3 * inch))
        story.append(Paragraph(f'数据类型: {sql_type}', normal_style))
        story.append(Paragraph(f'报告期间: {end_date_start} 至 {end_date_end}', normal_style))
        story.append(Paragraph(f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', normal_style))
        story.append(PageBreak())

        # 执行摘要
        story.append(Paragraph('一、执行摘要', heading_style))
        if all_metrics_results:
            final_metrics_df = pd.concat(all_metrics_results, ignore_index=True)
            summary_text = f"""
            本报告分析了从 {end_date_start} 到 {end_date_end} 期间的投资组合优化结果。
            数据类型: {sql_type}。
            共进行了 {len(final_metrics_df)} 次优化计算，涵盖三种策略：最大化夏普比率、最大化收益率、最小化波动率。
            """
            story.append(Paragraph(summary_text, normal_style))
        story.append(Spacer(1, 0.3 * inch))

        # 策略对比图表
        if chart1_path:
            story.append(Paragraph('二、策略性能对比', heading_style))
            img = Image(chart1_path, width=page_width, height=page_width * 0.7)
            story.append(img)
            story.append(Spacer(1, 0.3 * inch))
            story.append(Paragraph('上图展示了三种优化策略在年化收益率、波动率和夏普比率方面的表现对比。', normal_style))
            story.append(PageBreak())

        # 产品权重图表
        if chart2_path:
            story.append(Paragraph('三、产品权重配置', heading_style))
            img = Image(chart2_path, width=page_width, height=page_width * 0.7)
            story.append(img)
            story.append(Spacer(1, 0.3 * inch))
            story.append(Paragraph('上图展示了不同策略下各产品的权重配置变化。', normal_style))
            story.append(PageBreak())

        # 详细数据表格
        if all_metrics_results:
            story.append(Paragraph('四、关键指标统计', heading_style))
            final_metrics_df = pd.concat(all_metrics_results, ignore_index=True)

            # 汇总统计
            summary_stats = final_metrics_df.groupby('优化目标')[['年化收益率', '年化波动率', '夏普比率']].agg(
                ['mean', 'std', 'min', 'max'])

            # 创建表格数据
            table_data = [['策略', '指标', '均值', '标准差', '最小值', '最大值']]
            for strategy in summary_stats.index:
                for metric in ['年化收益率', '年化波动率', '夏普比率']:
                    row = [
                        strategy,
                        metric,
                        f"{summary_stats.loc[strategy, (metric, 'mean')]:.2f}",
                        f"{summary_stats.loc[strategy, (metric, 'std')]:.2f}",
                        f"{summary_stats.loc[strategy, (metric, 'min')]:.2f}",
                        f"{summary_stats.loc[strategy, (metric, 'max')]:.2f}"
                    ]
                    table_data.append(row)

            table = Table(table_data, colWidths=[2 * inch, 1.5 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), chinese_font),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTNAME', (0, 1), (-1, -1), chinese_font),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(table)
            story.append(PageBreak())

        # 最新权重配置
        if all_products_results:
            story.append(Paragraph('五、最新权重配置', heading_style))
            final_products_df = pd.concat(all_products_results, ignore_index=True)
            latest_date = final_products_df['date'].max()
            latest_data = final_products_df[final_products_df['date'] == latest_date]

            table_data = [['策略', '产品', '权重(%)', '无风险利率(%)']]
            for _, row in latest_data.iterrows():
                table_data.append([
                    row['strategy'],
                    row['products'],
                    f"{row['rate'] * 100:.2f}",
                    f"{row.get('risk_free_rate', 0) * 100:.2f}" if 'risk_free_rate' in row else 'N/A'
                ])

            table = Table(table_data, colWidths=[2 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), chinese_font),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTNAME', (0, 1), (-1, -1), chinese_font),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(table)

        # 生成 PDF
        doc.build(story)

        # 清理临时文件
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except:
                pass

        logger.info(f"✅ PDF 报告已生成: {pdf_path}")
        return pdf_path

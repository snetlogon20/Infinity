import os
import sys
from datetime import datetime
import matplotlib.font_manager as fm
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from matplotlib import rcParams
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator import CommonLib, CommonParameters

logger = CommonLib.logger
commonLib = CommonLib()

# 配置中文字体
def setup_chinese_font():
    """配置中文字体"""
    font_paths = [
        r'C:\Windows\Fonts\msyh.ttc',
        r'C:\Windows\Fonts\msyhbd.ttc',
        r'C:\Windows\Fonts\simhei.ttf',
        r'C:\Windows\Fonts\simsun.ttc',
        r'C:\Windows\Fonts\simfang.ttf',
    ]

    chinese_font = 'SimHei'

    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                font_name = fm.FontProperties(fname=font_path).get_name()
                fm.fontManager.addfont(font_path)
                chinese_font = font_name
                logger.info(f"✅ 成功加载中文字体: {font_path} -> {font_name}")
                break
            except Exception as e:
                logger.warning(f"⚠️ 字体加载失败 {font_path}: {e}")
                continue

    if chinese_font == 'SimHei':
        logger.warning("⚠️ 未找到中文字体，图表中的中文可能无法正常显示")

    rcParams['font.sans-serif'] = [chinese_font, 'Arial Unicode MS', 'Microsoft YaHei', 'SimHei']
    rcParams['axes.unicode_minus'] = False

    return chinese_font

chinese_font = setup_chinese_font()


class CMLAnalysis:
    """资本市场线(CML)分析类"""

    def __init__(self):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="CMLAnalysis started")

    def writeLogInfo(self, className="unknown", functionName="unknown", event="unknown"):
        """记录日志信息"""
        print("%s.%s: %s" % (className, functionName, event))
        logger.info("%s.%s: %s" % (className, functionName, event))

    def fetch_stock_data(self, stocks, start_date, end_date, market_type="CN", market_symbol=None, include_commodities=None):
        """
        从 ClickHouse 获取股票数据（支持多数据源：股票 + 商品）

        参数:
        - stocks: 股票代码列表
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')
        - market_type: 市场类型 ['US', 'CN']
        - market_symbol: 市场指数符号（用于区分指数和股票）
        - include_commodities: 商品配置字典，例如 {'GC': '黄金', 'CL': '原油'}

        返回:
        - dfs: 字典，key为资产代码（A股格式为 ts_code-name，美股格式为 ts_code-enname），value为DataFrame
        - stock_names: 字典，key为ts_code，value为资产名称
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event=f"Fetching data for {len(stocks)} stocks from {start_date} to {end_date}, market={market_type}")

        if include_commodities:
            logger.info(f" 同时获取 {len(include_commodities)} 种商品数据: {list(include_commodities.keys())}")

        dfs = {}
        stock_names = {}

        # Step 1: 获取股票名称
        if market_type == "CN":
            cn_stocks = [s for s in stocks if s != market_symbol]
            if cn_stocks:
                clickhouseService = ClickhouseService()
                stock_codes = "','".join(cn_stocks)
                name_sql = f"""
                SELECT ts_code, name
                FROM indexsysdb.df_tushare_stock_basic
                WHERE ts_code IN ('{stock_codes}')
                """
                name_df = clickhouseService.getDataFrameWithoutColumnsName(name_sql)
                if not name_df.empty:
                    for _, row in name_df.iterrows():
                        stock_names[row['ts_code']] = row['name']

        elif market_type == "US":
            us_stocks = [s for s in stocks if s != market_symbol]
            if us_stocks:
                clickhouseService = ClickhouseService()
                stock_codes = "','".join(us_stocks)
                name_sql = f"""
                SELECT ts_code, enname
                FROM indexsysdb.df_tushare_us_stock_basic
                WHERE ts_code IN ('{stock_codes}')
                """
                name_df = clickhouseService.getDataFrameWithoutColumnsName(name_sql)
                if not name_df.empty:
                    for _, row in name_df.iterrows():
                        stock_names[row['ts_code']] = row['enname']

        # Step 2: 获取股票数据
        for stock in stocks:
            is_market_index = (stock == market_symbol)

            if market_type == "US":
                sql = self._build_us_stock_sql(stock, start_date, end_date)
                display_name = stock

            elif market_type == "CN":
                if is_market_index:
                    sql = self._build_cn_index_sql(stock, start_date, end_date)
                    display_name = stock
                else:
                    sql = self._build_cn_stock_sql(stock, start_date, end_date)
                    display_name = stock

            else:
                raise ValueError(f"不支持的市场类型: {market_type}。支持的类型: ['US', 'CN']")

            clickhouseService = ClickhouseService()
            df = clickhouseService.getDataFrameWithoutColumnsName(sql)
            if df.empty:
                logger.warning(f"警告: {stock} 在 {start_date} 到 {end_date} 期间没有数据")
                continue

            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df.set_index('trade_date', inplace=True)

            if market_type == "CN" and not is_market_index:
                if stock in stock_names and stock_names[stock]:
                    display_name = f"{stock}-{stock_names[stock]}"

            if market_type == "US" and not is_market_index:
                if stock in stock_names and stock_names[stock]:
                    display_name = f"{stock}-{stock_names[stock]}"

            dfs[display_name] = df

        # Step 3: 获取商品数据（如果有配置）
        if include_commodities:
            commodity_dfs = self._fetch_commodities_data(include_commodities, start_date, end_date, market_type)
            dfs.update(commodity_dfs)

        logger.info(f"成功获取 {len(dfs)} 个资产的数据")
        return dfs

    def _build_us_stock_sql(self, stock, start_date, end_date):
        """构建美股查询SQL"""
        return f"""
        SELECT
            date as trade_date,
            close as close_point
        FROM df_akshare_stock_us_daily
        WHERE symbol = '{stock}'
          AND date >= '{start_date}'
          AND date <= '{end_date}'
        ORDER BY date ASC
        """

    def _build_cn_stock_sql(self, stock, start_date, end_date):
        """构建A股查询SQL"""
        return f"""
        SELECT
            trade_date as trade_date,
            close as close_point
        FROM df_tushare_stock_daily
        WHERE ts_code = '{stock}'
          AND trade_date >= '{start_date}'
          AND trade_date <= '{end_date}'
        ORDER BY trade_date ASC
        """

    def _build_cn_index_sql(self, stock, start_date, end_date):
        """构建中国指数查询SQL"""
        return f"""
        SELECT
            trade_date as trade_date,
            close as close_point
        FROM df_tushare_cn_index_daily
        WHERE ts_code = '{stock}'
          AND trade_date >= '{start_date}'
          AND trade_date <= '{end_date}'
        ORDER BY trade_date ASC
        """

    def _fetch_commodities_data(self, commodities, start_date, end_date, market_type="US"):
        """
        获取商品数据（支持 UNION 多商品一次性查询）
        
        参数:
        - commodities: 商品配置字典，例如 {'GC': '黄金', 'CL': '原油'} 或 {'Au99.99': '上海黄金'}
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')
        - market_type: 市场类型 ('US' 使用国外期货表, 'CN' 使用国内SGE表)
        
        返回:
        - dfs: 商品数据字典
        """
        if not commodities:
            return {}

        logger.info(f"🔍 开始获取商品数据，市场类型: {market_type}, 商品列表: {list(commodities.keys())}")

        # 格式化日期（YYYYMMDD -> YYYY-MM-DD）
        start_date_formatted = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
        end_date_formatted = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"

        # 根据市场类型选择数据表
        if market_type == "CN":
            # 中国资产：使用上海黄金交易所数据
            # 注意：df_akshare_spot_hist_sge 表只包含上海黄金(Au99.99)数据，没有 symbol 字段
            table_name = "indexsysdb.df_akshare_spot_hist_sge"
            has_symbol_field = False  # 该表没有 symbol 字段
            logger.info(f"🇨🇳 使用国内黄金数据表: {table_name}")
            logger.info(f"   日期范围: {start_date_formatted} 至 {end_date_formatted}")
            logger.info(f"   ⚠️ 注意: 该表只包含上海黄金(Au99.99)数据，不支持多商品查询")
        else:
            # 美国/国际资产：使用外盘期货数据
            table_name = "indexsysdb.df_akshare_futures_foreign_hist"
            has_symbol_field = True  # 该表有 symbol 字段
            logger.info(f"🇺🇸 使用国外期货数据表: {table_name}")
            logger.info(f"   日期范围: {start_date_formatted} 至 {end_date_formatted}")

        # 构建 UNION ALL 查询
        union_queries = []
        for symbol, name in commodities.items():
            if market_type == "CN":
                # 中国资产：不使用 symbol 过滤（表中只有上海黄金数据）
                union_queries.append(f"""
                    SELECT
                        '{symbol}' AS ts_code,
                        replaceAll(toString(date), '-', '') AS trade_date,
                        close AS close_point
                    FROM {table_name}
                    WHERE date >= '{start_date_formatted}'
                      AND date <= '{end_date_formatted}'
                      AND close > 0
                """)
            else:
                # 美国/国际资产：使用 symbol 过滤
                union_queries.append(f"""
                    SELECT
                        '{symbol}' AS ts_code,
                        replaceAll(toString(date), '-', '') AS trade_date,
                        close AS close_point
                    FROM {table_name}
                    WHERE symbol = '{symbol}'
                      AND date >= '{start_date_formatted}'
                      AND date <= '{end_date_formatted}'
                      AND close > 0
                """)

        # 合并为完整 SQL
        combined_sql = " UNION ALL ".join(union_queries) + " ORDER BY trade_date, ts_code"
        logger.info(f"📝 执行商品数据查询 SQL:\n{combined_sql}")

        clickhouseService = ClickhouseService()
        df = clickhouseService.getDataFrameWithoutColumnsName(combined_sql)

        if df.empty:
            logger.warning(f"⚠️ 警告: 未获取到任何商品数据 (市场类型: {market_type}, 商品: {list(commodities.keys())})")
            logger.warning(f"   请检查:")
            logger.warning(f"   1. 表 {table_name} 中是否有数据")
            logger.warning(f"   2. 日期范围 {start_date_formatted} 至 {end_date_formatted} 是否正确")
            if has_symbol_field:
                logger.warning(f"   3. 商品代码 {list(commodities.keys())} 是否存在于表中")
            return {}

        logger.info(f"✅ 成功获取商品原始数据: {len(df)} 条记录")
        logger.info(f"   包含商品: {df['ts_code'].unique().tolist()}")

        # 按商品分组
        dfs = {}
        for symbol in df['ts_code'].unique():
            commodity_df = df[df['ts_code'] == symbol][['trade_date', 'close_point']].copy()
            commodity_df['trade_date'] = pd.to_datetime(commodity_df['trade_date'])
            commodity_df.set_index('trade_date', inplace=True)
            
            display_name = f"{symbol}-{commodities.get(symbol, '')}"
            dfs[display_name] = commodity_df
            logger.info(f"   {display_name}: {len(commodity_df)} 条数据, 日期范围: {commodity_df.index.min()} 至 {commodity_df.index.max()}")

        return dfs

    def filter_common_dates(self, dfs):
        """
        过滤出所有股票共同的交易日期

        参数:
        - dfs: 股票数据字典

        返回:
        - filtered_dfs: 过滤后的数据字典
        - common_dates: 共同日期列表
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="Filtering common dates")

        stock_keys = list(dfs.keys())
        if not stock_keys:
            raise ValueError("没有可用的股票数据")

        common_dates = set(dfs[stock_keys[0]].index)
        for key in stock_keys[1:]:
            if key in dfs:
                common_dates = common_dates.intersection(set(dfs[key].index))

        common_dates = sorted(list(common_dates))

        logger.info(f"共同日期数量: {len(common_dates)}")
        if len(common_dates) > 0:
            logger.info(f"共同日期范围: {common_dates[0]} 至 {common_dates[-1]}")
        else:
            raise ValueError("错误：所有股票没有共同的交易日！")

        filtered_dfs = {}
        for key in stock_keys:
            if key in dfs:
                filtered_dfs[key] = dfs[key].loc[common_dates]
                logger.info(f"{key}: {len(filtered_dfs[key])} 条数据")

        return filtered_dfs, common_dates

    def calculate_daily_return(self, dfs):
        """
        计算各股票日收益率（对数收益率）

        参数:
        - dfs: 股票数据字典

        返回:
        - returns_df: 收益率DataFrame
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="Calculating daily returns")

        returns_df = pd.DataFrame()

        for stock, df in dfs.items():
            close_prices = df['close_point']
            daily_return = np.log(close_prices / close_prices.shift(1))
            returns_df[stock] = daily_return

        returns_df = returns_df.dropna()
        logger.info(f"收益率数据形状: {returns_df.shape}")

        return returns_df

    def calculate_statistics(self, returns_df, trading_days=252):
        """
        计算收益率统计量

        参数:
        - returns_df: 收益率DataFrame
        - trading_days: 年交易日数

        返回:
        - expected_returns: 年化预期收益率
        - cov_matrix: 年化协方差矩阵
        - volatilities: 年化波动率
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="Calculating statistics")

        expected_returns = returns_df.mean() * trading_days
        cov_matrix = returns_df.cov() * trading_days
        volatilities = returns_df.std() * np.sqrt(trading_days)

        logger.info(f"计算完成 {len(expected_returns)} 只股票的统计量")

        return expected_returns, cov_matrix, volatilities

    def portfolio_performance(self, weights, expected_returns, cov_matrix):
        """计算投资组合的预期收益率和波动率"""
        portfolio_return = np.dot(weights, expected_returns)
        portfolio_volatility = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
        return portfolio_return, portfolio_volatility

    def negative_sharpe_ratio(self, weights, expected_returns, cov_matrix, risk_free_rate):
        """负夏普比率（用于最小化）"""
        p_return, p_volatility = self.portfolio_performance(weights, expected_returns, cov_matrix)
        return -(p_return - risk_free_rate) / p_volatility

    def optimize_max_sharpe(self, expected_returns, cov_matrix, risk_free_rate):
        """
        优化最大夏普比率组合

        参数:
        - expected_returns: 年化预期收益率
        - cov_matrix: 年化协方差矩阵
        - risk_free_rate: 年化无风险利率

        返回:
        - result: 优化结果
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="Optimizing maximum Sharpe ratio")

        n_assets = len(expected_returns)
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1.0})
        bounds = tuple((0.0, 1.0) for _ in range(n_assets))
        initial_weights = np.array([1.0 / n_assets] * n_assets)

        result = minimize(
            self.negative_sharpe_ratio,
            initial_weights,
            args=(expected_returns.values, cov_matrix.values, risk_free_rate),
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        if not result.success:
            logger.warning(f"优化失败: {result.message}")

        return result

    def optimize_min_variance(self, expected_returns, cov_matrix):
        """
        优化最小方差组合

        参数:
        - expected_returns: 年化预期收益率
        - cov_matrix: 年化协方差矩阵

        返回:
        - result: 优化结果
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="Optimizing minimum variance portfolio")

        n_assets = len(expected_returns)
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1.0})
        bounds = tuple((0.0, 1.0) for _ in range(n_assets))
        initial_weights = np.array([1.0 / n_assets] * n_assets)

        result = minimize(
            lambda w: self.portfolio_performance(w, expected_returns.values, cov_matrix.values)[1],
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        if not result.success:
            logger.warning(f"优化失败: {result.message}")

        return result

    def generate_efficient_frontier(self, expected_returns, cov_matrix, min_return, max_return, n_points=50):
        """
        生成有效前沿

        参数:
        - expected_returns: 年化预期收益率
        - cov_matrix: 年化协方差矩阵
        - min_return: 最小目标收益率
        - max_return: 最大目标收益率
        - n_points: 点数

        返回:
        - frontier_returns: 有效前沿收益率列表
        - frontier_volatilities: 有效前沿波动率列表
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="Generating efficient frontier")

        target_returns = np.linspace(min_return, max_return, n_points)
        frontier_returns = []
        frontier_volatilities = []

        n_assets = len(expected_returns)
        bounds = tuple((0.0, 1.0) for _ in range(n_assets))
        initial_weights = np.array([1.0 / n_assets] * n_assets)

        for target_return in target_returns:
            constraints = (
                {'type': 'eq', 'fun': lambda x: np.sum(x) - 1.0},
                {'type': 'eq', 'fun': lambda x: np.dot(x, expected_returns.values) - target_return}
            )

            result = minimize(
                lambda w: self.portfolio_performance(w, expected_returns.values, cov_matrix.values)[1],
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints
            )

            if result.success:
                p_return, p_volatility = self.portfolio_performance(
                    result.x, expected_returns.values, cov_matrix.values
                )
                frontier_returns.append(p_return)
                frontier_volatilities.append(p_volatility)

        return frontier_returns, frontier_volatilities

    def monte_carlo_simulation(self, expected_returns, cov_matrix, risk_free_rate, n_portfolios=10000):
        """
        蒙特卡洛模拟

        参数:
        - expected_returns: 年化预期收益率
        - cov_matrix: 年化协方差矩阵
        - risk_free_rate: 年化无风险利率
        - n_portfolios: 模拟组合数量

        返回:
        - results: 模拟结果数组
        - weights_record: 权重记录
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event=f"Running Monte Carlo simulation with {n_portfolios} portfolios")

        n_assets = len(expected_returns)
        results = np.zeros((n_portfolios, 3))
        weights_record = np.zeros((n_portfolios, n_assets))

        for i in range(n_portfolios):
            weights = np.random.random(n_assets)
            weights = weights / np.sum(weights)

            p_return, p_volatility = self.portfolio_performance(weights, expected_returns.values, cov_matrix.values)
            sharpe = (p_return - risk_free_rate) / p_volatility

            results[i, 0] = p_return
            results[i, 1] = p_volatility
            results[i, 2] = sharpe
            weights_record[i, :] = weights

        return results, weights_record

    def plot_cml(self, stocks, expected_returns, volatilities, mc_results, max_sharpe_idx,
                 max_sharpe_return, max_sharpe_volatility, max_sharpe_weights,
                 min_vol_return, min_vol_volatility, min_vol_weights,
                 frontier_returns, frontier_volatilities,
                 risk_free_rate, save_path=None, case_name=None):
        """
        绘制 CML 和有效前沿图

        参数:
        - stocks: 股票代码列表
        - expected_returns: 预期收益率字典
        - volatilities: 波动率字典
        - mc_results: 蒙特卡洛模拟结果
        - max_sharpe_idx: 最大夏普比率索引
        - max_sharpe_return: 最大夏普比率组合收益率
        - max_sharpe_volatility: 最大夏普比率组合波动率
        - max_sharpe_weights: 最大夏普比率组合权重
        - min_vol_return: 最小方差组合收益率
        - min_vol_volatility: 最小方差组合波动率
        - min_vol_weights: 最小方差组合权重
        - frontier_returns: 有效前沿收益率列表
        - frontier_volatilities: 有效前沿波动率列表
        - risk_free_rate: 无风险利率
        - save_path: 保存路径（可选）
        - case_name: 测试案例名称（用于文件名区分）

        返回:
        - plot_path: 图表保存路径
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="Plotting CML")

        # 直接使用 expected_returns 的 index 获取所有股票名称
        all_stock_names = list(expected_returns.index)
        num_stocks = len(all_stock_names)
        
        # 根据股票数量动态调整图表高度，为底部表格预留空间
        if num_stocks <= 5:
            fig_height = 12
        elif num_stocks <= 10:
            fig_height = 14
        elif num_stocks <= 20:
            fig_height = 16
        else:
            fig_height = 18
        
        plt.figure(figsize=(16, fig_height))

        scatter = plt.scatter(
            mc_results[:, 1],
            mc_results[:, 0],
            c=mc_results[:, 2],
            cmap='viridis',
            marker='o',
            s=10,
            alpha=0.3,
            label='随机组合'
        )

        if frontier_volatilities and frontier_returns:
            plt.plot(
                frontier_volatilities,
                frontier_returns,
                'r-',
                linewidth=2,
                label='有效前沿'
            )

        cml_volatility = np.linspace(0, max_sharpe_volatility * 1.5, 100)
        cml_return = risk_free_rate + (max_sharpe_return - risk_free_rate) / max_sharpe_volatility * cml_volatility

        plt.plot(
            cml_volatility,
            cml_return,
            'g--',
            linewidth=2.5,
            label='CML (资本市场线)'
        )

        plt.scatter(0, risk_free_rate, color='black', s=150, zorder=5, marker='D')
        plt.text(0.005, risk_free_rate + 0.005, f'无风险资产\n(Rf={risk_free_rate*100:.1f}%)',
                 fontsize=10, color='black', fontweight='bold')

        # 构建切点组合的配置比例文本
        max_sharpe_weights_text = '切点组合\n'
        max_sharpe_weights_text += f'(夏普比率={mc_results[max_sharpe_idx, 2]:.3f})\n'
        for idx, stock in enumerate(all_stock_names):
            weight_pct = max_sharpe_weights[idx] * 100
            if weight_pct > 0.5:  # 只显示占比超过0.5%的股票
                max_sharpe_weights_text += f'{stock}: {weight_pct:.1f}%\n'
        
        plt.scatter(max_sharpe_volatility, max_sharpe_return,
                    color='red', s=200, zorder=5, marker='*', label='切点组合 (最大夏普比率)')
        plt.text(max_sharpe_volatility + 0.005, max_sharpe_return + 0.005,
                 max_sharpe_weights_text.strip(),
                 fontsize=8, color='red', fontweight='bold')

        # 构建最小方差组合的配置比例文本
        min_vol_weights_text = '最小方差组合\n'
        min_vol_weights_text += f'({min_vol_return*100:.2f}%, {min_vol_volatility*100:.2f}%)\n'
        for idx, stock in enumerate(all_stock_names):
            weight_pct = min_vol_weights[idx] * 100
            if weight_pct > 0.5:  # 只显示占比超过0.5%的股票
                min_vol_weights_text += f'{stock}: {weight_pct:.1f}%\n'
        
        plt.scatter(min_vol_volatility, min_vol_return,
                    color='blue', s=150, zorder=5, marker='s', label='最小方差组合')
        plt.text(min_vol_volatility + 0.005, min_vol_return,
                 min_vol_weights_text.strip(),
                 fontsize=8, color='blue', fontweight='bold')

        # 直接使用 expected_returns 的 index 获取所有股票名称
        all_stock_names = list(expected_returns.index)
        
        for idx, stock in enumerate(all_stock_names):
            plt.scatter(volatilities[stock], expected_returns[stock],
                        color='purple', s=120, zorder=5, marker='^', label=stock)
            plt.text(volatilities[stock] + 0.003, expected_returns[stock] + 0.003,
                     f'{stock}\n({expected_returns[stock]*100:.1f}%, {volatilities[stock]*100:.1f}%)',
                     fontsize=9, color='purple')

        plt.xlabel('年化波动率 (%)', fontsize=12, fontname=chinese_font, fontweight='bold')
        plt.ylabel('年化预期收益率 (%)', fontsize=12, fontname=chinese_font, fontweight='bold')
        plt.title('资本市场线 (CML) 与有效前沿分析', fontsize=14, fontweight='bold', fontname=chinese_font)
        
        # 调整图例布局：增加列数，减小字体，增加间距
        num_columns = min(len(all_stock_names), 30)
        
        plt.legend(loc='upper center',
                   bbox_to_anchor=(0.5, -0.12),
                   ncol=num_columns,
                   fontsize=7,
                   markerscale=0.6,
                   columnspacing=0.8,
                   handlelength=1.0,
                   handletextpad=0.4,
                   framealpha=0.95,
                   borderaxespad=1.0)
        
        plt.grid(True, alpha=0.3, linestyle='--')

        plt.gca().xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x*100:.1f}%'))
        plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x*100:.1f}%'))

        cbar = plt.colorbar(scatter)
        cbar.set_label('夏普比率', fontsize=10, fontweight='bold')

        plt.tight_layout()
        plt.subplots_adjust(left=0.06, right=0.97, top=0.92, bottom=0.15)

        if save_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if case_name:
                save_path = os.path.join(CommonParameters.outBoundPath,
                                         f"cml_analysis_{case_name}_{timestamp}.png")
            else:
                save_path = os.path.join(CommonParameters.outBoundPath,
                                         f"cml_analysis_{timestamp}.png")

        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"CML 图表已保存: {save_path}")
        plt.close()

        return save_path

    def generate_cml_report(self, stocks, start_date, end_date, risk_free_rate_annual=0.04,
                           market_type="CN", trading_days=252, market_symbol=None, case_name=None,
                           include_commodities=None):
        """
        生成完整的 CML 分析报告（支持股票 + 商品混合分析）

        参数:
        - stocks: 股票代码列表
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')
        - risk_free_rate_annual: 年化无风险利率
        - market_type: 市场类型 ['US', 'CN']
        - trading_days: 年交易日数
        - market_symbol: 市场指数符号（预留参数，保持与SML一致）
        - case_name: 测试案例名称（用于文件名区分）
        - include_commodities: 商品配置字典，例如 {'GC': '黄金', 'CL': '原油'}

        返回:
        - results: 包含所有分析结果的字典
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="Starting complete CML analysis")

        if market_symbol is None:
            if market_type == "US":
                market_symbol = "SPY"
            elif market_type == "CN":
                market_symbol = "000001.SH"
            else:
                raise ValueError(f"不支持的市场类型: {market_type}")

        logger.info("=" * 80)
        logger.info("🚀 开始 CML 分析")
        logger.info(f"   市场类型: {market_type}")
        logger.info(f"   市场指数: {market_symbol}")
        logger.info(f"   股票数量: {len(stocks)}")
        if include_commodities:
            logger.info(f"   商品数量: {len(include_commodities)} - {list(include_commodities.keys())}")
        logger.info(f"   日期范围: {start_date} 至 {end_date}")
        logger.info(f"   无风险利率: {risk_free_rate_annual*100:.2f}%")
        logger.info("=" * 80)

        logger.info("\n📊 步骤 1/6: 获取资产数据（股票 + 商品）...")
        dfs = self.fetch_stock_data(stocks, start_date, end_date, 
                                   market_type=market_type, 
                                   market_symbol=market_symbol,
                                   include_commodities=include_commodities)

        if not dfs:
            raise ValueError("未能获取任何资产数据")

        logger.info("\n📅 步骤 2/6: 过滤共同日期...")
        filtered_dfs, common_dates = self.filter_common_dates(dfs)

        logger.info("\n📈 步骤 3/6: 计算日收益率和统计量...")
        returns_df = self.calculate_daily_return(filtered_dfs)
        expected_returns, cov_matrix, volatilities = self.calculate_statistics(returns_df, trading_days)

        # 排除市场指数（如SPY、000001.SH等），避免干扰组合优化
        # 市场指数作为基准参考，不应参与投资组合优化
        optimization_stocks = [stock for stock in expected_returns.index if stock != market_symbol]
        if market_symbol in expected_returns.index:
            logger.info(f"\n⚠️  从投资组合优化中排除市场指数: {market_symbol}")
            logger.info(f"   优化资产数量: {len(optimization_stocks)} (原始: {len(expected_returns)})")
            
            # 为优化创建不含市场指数的数据
            expected_returns_opt = expected_returns.drop(market_symbol)
            cov_matrix_opt = cov_matrix.drop(market_symbol).drop(market_symbol, axis=1)
            volatilities_opt = volatilities.drop(market_symbol)
        else:
            logger.info(f"\n✅ 所有资产均参与优化 (数量: {len(optimization_stocks)})")
            expected_returns_opt = expected_returns
            cov_matrix_opt = cov_matrix
            volatilities_opt = volatilities

        logger.info("\n⚡ 步骤 4/6: 投资组合优化...")
        max_sharpe_result = self.optimize_max_sharpe(expected_returns_opt, cov_matrix_opt, risk_free_rate_annual)
        min_vol_result = self.optimize_min_variance(expected_returns_opt, cov_matrix_opt)

        # 使用优化后的数据计算组合表现
        max_sharpe_return, max_sharpe_volatility = self.portfolio_performance(
            max_sharpe_result.x, expected_returns_opt.values, cov_matrix_opt.values
        )
        
        # 创建完整的权重数组（与原始expected_returns顺序一致，市场指数权重为0）
        max_sharpe_weights = np.zeros(len(expected_returns))
        for idx, stock in enumerate(expected_returns.index):
            if stock != market_symbol and stock in expected_returns_opt.index:
                opt_idx = list(expected_returns_opt.index).index(stock)
                max_sharpe_weights[idx] = max_sharpe_result.x[opt_idx]

        min_vol_return, min_vol_volatility = self.portfolio_performance(
            min_vol_result.x, expected_returns_opt.values, cov_matrix_opt.values
        )
        
        # 创建完整的权重数组（与原始expected_returns顺序一致，市场指数权重为0）
        min_vol_weights = np.zeros(len(expected_returns))
        for idx, stock in enumerate(expected_returns.index):
            if stock != market_symbol and stock in expected_returns_opt.index:
                opt_idx = list(expected_returns_opt.index).index(stock)
                min_vol_weights[idx] = min_vol_result.x[opt_idx]

        logger.info("\n 步骤 5/6: 生成有效前沿...")
        frontier_returns, frontier_volatilities = self.generate_efficient_frontier(
            expected_returns_opt, cov_matrix_opt, min_vol_return, max_sharpe_return
        )

        logger.info("\n🎲 步骤 6/6: 蒙特卡洛模拟和绘图...")
        n_portfolios = 10000
        mc_results, weights_record = self.monte_carlo_simulation(
            expected_returns_opt, cov_matrix_opt, risk_free_rate_annual, n_portfolios
        )

        max_sharpe_idx = np.argmax(mc_results[:, 2])

        plot_path = self.plot_cml(
            stocks, expected_returns, volatilities, mc_results, max_sharpe_idx,
            max_sharpe_return, max_sharpe_volatility, max_sharpe_weights,
            min_vol_return, min_vol_volatility, min_vol_weights,
            frontier_returns, frontier_volatilities,
            risk_free_rate_annual, case_name=case_name
        )

        results = {
            'expected_returns': expected_returns.to_dict(),
            'volatilities': volatilities.to_dict(),
            'cov_matrix': cov_matrix,
            'max_sharpe_return': max_sharpe_return,
            'max_sharpe_volatility': max_sharpe_volatility,
            'max_sharpe_weights': max_sharpe_weights,
            'max_sharpe_ratio': mc_results[max_sharpe_idx, 2],
            'min_vol_return': min_vol_return,
            'min_vol_volatility': min_vol_volatility,
            'min_vol_weights': min_vol_weights,
            'frontier_returns': frontier_returns,
            'frontier_volatilities': frontier_volatilities,
            'plot_path': plot_path,
            'start_date': start_date,
            'end_date': end_date,
            'stocks': stocks,
            'market_type': market_type,
            'market_symbol': market_symbol,
            'mc_results': mc_results,
            'weights_record': weights_record
        }

        logger.info("\n" + "=" * 80)
        logger.info("✅ CML 分析完成！")
        logger.info(f"   市场类型: {market_type}")
        logger.info(f"   市场指数: {market_symbol}")
        logger.info(f"   分析股票数: {len(expected_returns)}")
        logger.info(f"   图表路径: {plot_path}")
        logger.info(f"   最大夏普比率: {mc_results[max_sharpe_idx, 2]:.4f}")
        logger.info("=" * 80)

        logger.info("\n 收益率和波动率汇总:")
        logger.info("-" * 80)
        for stock in sorted(expected_returns.keys()):
            logger.info(f"{stock:20s}: E(R)={expected_returns[stock]*100:7.2f}%, "
                      f"σ={volatilities[stock]*100:7.2f}%")
        logger.info("-" * 80)

        return results

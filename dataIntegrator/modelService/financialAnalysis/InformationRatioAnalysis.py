"""
Information Ratio (信息比率) 分析

信息比率衡量的是单位主动风险所获得的超额收益（相对于基准）
公式: IR = (E(Rp) - E(Rb)) / σ(Rp - Rb)

其中：
- Rp: 投资组合收益率
- Rb: 基准收益率
- σ(Rp - Rb): 跟踪误差（主动风险）
"""

import os
import sys
from datetime import datetime
import matplotlib.font_manager as fm
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
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


class InformationRatioAnalysis:
    """信息比率分析类"""

    def __init__(self):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="InformationRatioAnalysis started")

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
            logger.info(f"📦 同时获取 {len(include_commodities)} 种商品数据: {list(include_commodities.keys())}")

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

        logger.info(f"✅ 成功获取 {len(dfs)} 个资产的数据")
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
            table_name = "indexsysdb.df_akshare_spot_hist_sge"
            has_symbol_field = False
            logger.info(f"🇨🇳 使用国内黄金数据表: {table_name}")
            logger.info(f"   日期范围: {start_date_formatted} 至 {end_date_formatted}")
        else:
            # 美国/国际资产：使用外盘期货数据
            table_name = "indexsysdb.df_akshare_futures_foreign_hist"
            has_symbol_field = True
            logger.info(f"🇺🇸 使用国外期货数据表: {table_name}")
            logger.info(f"   日期范围: {start_date_formatted} 至 {end_date_formatted}")

        # 构建 UNION ALL 查询
        union_queries = []
        for symbol, name in commodities.items():
            if market_type == "CN":
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

        combined_sql = " UNION ALL ".join(union_queries) + " ORDER BY trade_date, ts_code"
        logger.info(f"📝 执行商品数据查询 SQL")

        clickhouseService = ClickhouseService()
        df = clickhouseService.getDataFrameWithoutColumnsName(combined_sql)

        if df.empty:
            logger.warning(f"⚠️ 警告: 未获取到任何商品数据 (市场类型: {market_type})")
            return {}

        logger.info(f"✅ 成功获取商品原始数据: {len(df)} 条记录")

        # 按商品分组
        dfs = {}
        for symbol in df['ts_code'].unique():
            commodity_df = df[df['ts_code'] == symbol][['trade_date', 'close_point']].copy()
            commodity_df['trade_date'] = pd.to_datetime(commodity_df['trade_date'])
            commodity_df.set_index('trade_date', inplace=True)
            
            display_name = f"{symbol}-{commodities.get(symbol, '')}"
            dfs[display_name] = commodity_df
            logger.info(f"   {display_name}: {len(commodity_df)} 条数据")

        return dfs

    def filter_common_dates(self, dfs):
        """
        过滤出所有资产共同的交易日期

        参数:
        - dfs: 资产数据字典

        返回:
        - filtered_dfs: 过滤后的数据字典
        - common_dates: 共同日期列表
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="Filtering common dates")

        asset_keys = list(dfs.keys())
        if not asset_keys:
            raise ValueError("没有可用的资产数据")

        common_dates = set(dfs[asset_keys[0]].index)
        for key in asset_keys[1:]:
            if key in dfs:
                common_dates = common_dates.intersection(set(dfs[key].index))

        common_dates = sorted(list(common_dates))

        logger.info(f"共同日期数量: {len(common_dates)}")
        if len(common_dates) > 0:
            logger.info(f"共同日期范围: {common_dates[0]} 至 {common_dates[-1]}")
        else:
            raise ValueError("错误：所有资产没有共同的交易日！")

        filtered_dfs = {}
        for key in asset_keys:
            if key in dfs:
                filtered_dfs[key] = dfs[key].loc[common_dates]
                logger.info(f"{key}: {len(filtered_dfs[key])} 条数据")

        return filtered_dfs, common_dates

    def calculate_daily_return(self, dfs):
        """
        计算各资产日收益率（对数收益率）

        参数:
        - dfs: 资产数据字典

        返回:
        - returns_df: 收益率DataFrame
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="Calculating daily returns")

        returns_df = pd.DataFrame()

        for asset, df in dfs.items():
            close_prices = df['close_point']
            daily_return = np.log(close_prices / close_prices.shift(1))
            returns_df[asset] = daily_return

        returns_df = returns_df.dropna()
        logger.info(f"收益率数据形状: {returns_df.shape}")

        return returns_df

    def calculate_information_ratio(self, returns_df, benchmark_symbol, trading_days=252):
        """
        计算信息比率
        IR = (E(Rp) - E(Rb)) / σ(Rp - Rb)
        
        参数:
        - returns_df: 收益率DataFrame
        - benchmark_symbol: 基准资产代码
        - trading_days: 年化交易日数
        
        返回:
        - information_ratios: 信息比率字典
        - active_returns: 主动收益率字典
        - tracking_errors: 跟踪误差字典
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="Calculating Information Ratios")

        benchmark_returns = returns_df[benchmark_symbol]
        
        information_ratios = {}
        active_returns_dict = {}
        tracking_errors_dict = {}
        
        for asset in returns_df.columns:
            if asset == benchmark_symbol:
                # 基准自身的信息比率为0
                information_ratios[asset] = 0.0
                active_returns_dict[asset] = 0.0
                tracking_errors_dict[asset] = 0.0
                continue
            
            # 计算主动收益（超额收益）
            active_return = returns_df[asset] - benchmark_returns
            
            # 年化主动收益
            annualized_active_return = active_return.mean() * trading_days
            
            # 计算跟踪误差（主动收益的标准差）
            tracking_error = active_return.std() * np.sqrt(trading_days)
            
            # 计算信息比率
            if tracking_error != 0:
                ir = annualized_active_return / tracking_error
            else:
                ir = np.nan
            
            information_ratios[asset] = ir
            active_returns_dict[asset] = annualized_active_return
            tracking_errors_dict[asset] = tracking_error
        
        logger.info(f"计算完成 {len(information_ratios)} 个资产的信息比率")
        
        return information_ratios, active_returns_dict, tracking_errors_dict

    def plot_information_ratio(self, information_ratios, active_returns, tracking_errors, 
                               benchmark_symbol, save_path=None, case_name=None):
        """
        绘制信息比率分析图
        
        X轴: 跟踪误差（主动风险）
        Y轴: 主动收益（超额收益）
        每条射线的斜率代表信息比率
        
        参数:
        - information_ratios: 信息比率字典
        - active_returns: 主动收益字典
        - tracking_errors: 跟踪误差字典
        - benchmark_symbol: 基准资产代码
        - save_path: 保存路径（可选）
        - case_name: 测试案例名称（用于文件名区分）
        
        返回:
        - plot_path: 图表保存路径
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="Plotting Information Ratio Analysis")

        plt.figure(figsize=(12, 8))
        
        # 准备数据
        assets_to_plot = [a for a in information_ratios.keys() if a != benchmark_symbol]
        colors = plt.cm.viridis(np.linspace(0, 1, len(assets_to_plot)))
        
        # 绘制各资产的点
        for idx, asset in enumerate(assets_to_plot):
            ir = information_ratios[asset]
            te = tracking_errors[asset]
            ar = active_returns[asset]
            
            if not np.isnan(ir):
                color = colors[idx % len(colors)]
                plt.scatter(
                    te * 100, 
                    ar * 100,
                    color=color, s=80, zorder=4, alpha=0.7,
                    edgecolors='black', linewidths=0.5
                )
                
                # 标注资产代码和IR值
                if idx % 2 == 0:
                    xytext = (30, 5)
                else:
                    xytext = (-30, 5)
                
                plt.annotate(
                    f'{asset}\nIR={ir:.2f}',
                    xy=(te * 100, ar * 100),
                    xytext=xytext,
                    textcoords='offset points',
                    fontsize=7,
                    color=color,
                    fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7)
                )
        
        # 标记基准（原点）
        plt.scatter(0, 0, color='blue', s=150, zorder=5, marker='*', 
                   label=f'基准 ({benchmark_symbol})', edgecolors='darkblue', linewidths=2)
        
        # 绘制从原点到各点的射线（表示信息比率）
        for asset in assets_to_plot[:10]:  # 只显示前10个资产，避免过于拥挤
            ir = information_ratios[asset]
            te = tracking_errors[asset]
            
            if not np.isnan(ir) and te > 0:
                te_max = max([tracking_errors[a] for a in assets_to_plot 
                             if not np.isnan(information_ratios[a])])
                te_line = np.linspace(0, min(te * 1.5, te_max), 50)
                ar_line = ir * te_line
                plt.plot(te_line * 100, ar_line * 100, '--', alpha=0.3, linewidth=1)
        
        # 添加零线
        plt.axhline(y=0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
        plt.axvline(x=0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
        
        # 图表美化
        plt.xlabel('跟踪误差 - 主动风险 (%)', fontsize=12, fontname=chinese_font, fontweight='bold')
        plt.ylabel('主动收益 - 超额收益 (%)', fontsize=12, fontname=chinese_font, fontweight='bold')
        plt.title(f'信息比率 (Information Ratio) 分析\n基准: {benchmark_symbol}', 
                 fontsize=14, fontweight='bold', fontname=chinese_font)
        
        plt.legend(loc='upper left', fontsize=9, framealpha=0.9)
        plt.grid(True, alpha=0.3, linestyle='--')
        
        plt.tight_layout()

        if save_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if case_name:
                save_path = os.path.join(CommonParameters.outBoundPath,
                                         f"information_ratio_{case_name}_{timestamp}.png")
            else:
                save_path = os.path.join(CommonParameters.outBoundPath,
                                         f"information_ratio_{timestamp}.png")

        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"📊 信息比率图表已保存: {save_path}")
        plt.close()

        return save_path

    def generate_ir_report(self, stocks, start_date, end_date, 
                          market_type="CN", trading_days=252, market_symbol=None, 
                          case_name=None, include_commodities=None):
        """
        生成完整的信息比率分析报告（支持股票 + 商品混合分析）

        参数:
        - stocks: 资产代码列表
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')
        - market_type: 市场类型 ['US', 'CN']
        - trading_days: 年交易日数
        - market_symbol: 基准指数符号
        - case_name: 测试案例名称（用于文件名区分）
        - include_commodities: 商品配置字典，例如 {'GC': '黄金', 'CL': '原油'}

        返回:
        - results: 包含所有分析结果的字典
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="Starting complete Information Ratio analysis")

        if market_symbol is None:
            if market_type == "US":
                market_symbol = "SPY"
            elif market_type == "CN":
                market_symbol = "000001.SH"
            else:
                raise ValueError(f"不支持的市场类型: {market_type}")

        logger.info("=" * 80)
        logger.info("🚀 开始信息比率 (Information Ratio) 分析")
        logger.info(f"   市场类型: {market_type}")
        logger.info(f"   基准指数: {market_symbol}")
        logger.info(f"   资产数量: {len(stocks)}")
        if include_commodities:
            logger.info(f"   商品数量: {len(include_commodities)} - {list(include_commodities.keys())}")
        logger.info(f"   日期范围: {start_date} 至 {end_date}")
        logger.info("=" * 80)

        logger.info("\n📊 步骤 1/4: 获取资产数据（股票 + 商品）...")
        dfs = self.fetch_stock_data(stocks, start_date, end_date, 
                                   market_type=market_type, 
                                   market_symbol=market_symbol,
                                   include_commodities=include_commodities)

        if not dfs:
            raise ValueError("未能获取任何资产数据")

        logger.info("\n📅 步骤 2/4: 过滤共同日期...")
        filtered_dfs, common_dates = self.filter_common_dates(dfs)

        logger.info("\n📈 步骤 3/4: 计算日收益率...")
        returns_df = self.calculate_daily_return(filtered_dfs)

        logger.info("\n⚡ 步骤 4/4: 计算信息比率...")
        information_ratios, active_returns, tracking_errors = \
            self.calculate_information_ratio(returns_df, market_symbol, trading_days)

        logger.info("\n🎨 绘制信息比率分析图...")
        plot_path = self.plot_information_ratio(
            information_ratios, active_returns, tracking_errors,
            market_symbol, case_name=case_name
        )

        results = {
            'information_ratios': information_ratios,
            'active_returns': active_returns,
            'tracking_errors': tracking_errors,
            'plot_path': plot_path,
            'start_date': start_date,
            'end_date': end_date,
            'stocks': stocks,
            'market_type': market_type,
            'market_symbol': market_symbol,
            'benchmark': market_symbol
        }

        logger.info("\n" + "=" * 80)
        logger.info("✅ 信息比率分析完成！")
        logger.info(f"   市场类型: {market_type}")
        logger.info(f"   基准指数: {market_symbol}")
        logger.info(f"   分析资产数: {len(information_ratios)}")
        logger.info(f"   图表路径: {plot_path}")
        logger.info("=" * 80)

        logger.info("\n📋 信息比率汇总:")
        logger.info("-" * 80)
        logger.info(f"{'资产代码':<25} {'主动收益':>10} {'跟踪误差':>10} {'IR':>10}")
        logger.info("-" * 80)
        
        # 按信息比率排序
        sorted_assets = sorted(
            information_ratios.items(), 
            key=lambda x: x[1] if not np.isnan(x[1]) else -np.inf, 
            reverse=True
        )
        
        for asset, ir in sorted_assets:
            if asset != market_symbol and not np.isnan(ir):
                logger.info(
                    f"{asset:<25} "
                    f"{active_returns[asset]*100:>9.2f}% "
                    f"{tracking_errors[asset]*100:>9.2f}% "
                    f"{ir:>9.4f}"
                )
        logger.info("-" * 80)

        return results

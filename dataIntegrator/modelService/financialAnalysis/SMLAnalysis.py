import os
import sys
from datetime import datetime
import matplotlib.font_manager as fm
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from statsmodels import regression
import statsmodels.api as sm
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


class SMLAnalysis:
    """证券市场线(SML)分析类"""

    def __init__(self):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="SMLAnalysis started")

    def writeLogInfo(self, className="unknown", functionName="unknown", event="unknown"):
        """记录日志信息"""
        print("%s.%s: %s" % (className, functionName, event))
        logger.info("%s.%s: %s" % (className, functionName, event))

# ... existing code ...

    def fetch_stock_data(self, stocks, start_date, end_date, market_type="US", market_symbol=None, include_commodities=None):
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
        logger.info(f"📝 执行商品数据查询 SQL")

        clickhouseService = ClickhouseService()
        df = clickhouseService.getDataFrameWithoutColumnsName(combined_sql)

        if df.empty:
            logger.warning(f"⚠️ 警告: 未获取到任何商品数据 (市场类型: {market_type}, 商品: {list(commodities.keys())})")
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
            logger.info(f"   {display_name}: {len(commodity_df)} 条数据")

        return dfs


    def calculate_daily_return(self, df):
        """
        计算日收益率（对数收益率）

        参数:
        - df: 包含close_point列的DataFrame

        返回:
        - df_clean: 包含daily_return列的DataFrame
        """
        df['daily_return'] = np.log(df['close_point'] / df['close_point'].shift(1))
        df_clean = df.dropna()
        return df_clean

    def calculate_beta(self, stock_return, market_return):
        """
        用线性回归计算 β：stock_return = α + β * market_return + ε

        参数:
        - stock_return: 股票收益率序列
        - market_return: 市场收益率序列

        返回:
        - beta: β值
        """
        aligned_data = pd.DataFrame({
            'stock': stock_return,
            'market': market_return
        }).dropna()

        if len(aligned_data) == 0:
            raise ValueError("没有可用的收益率数据用于计算 β")

        x = aligned_data['market'].values
        y = aligned_data['stock'].values

        x = sm.add_constant(x)
        model = regression.linear_model.OLS(y, x).fit()
        return model.params[1]

    def calculate_all_betas(self, dfs, stocks, market_symbol='SPY', market_type="US"):
        """
        计算所有资产的β值（股票 + 商品）

        参数:
        - dfs: 资产数据字典（包含股票和商品）
        - stocks: 股票代码列表
        - market_symbol: 市场指数符号（美股用 SPY，A股用 000001.SH 或 399001.SZ）
        - market_type: 市场类型

        返回:
        - betas: 字典，key为资产代码，value为β值
        - market_return: 市场收益率序列
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="Calculating betas for all assets")

        if market_symbol not in dfs:
            raise ValueError(f"市场指数 {market_symbol} 数据不存在，无法计算 β 值")

        market_return = dfs[market_symbol]['daily_return']
        betas = {}

        # Step 1: 处理市场指数本身
        betas[market_symbol] = 1.0
        logger.info(f"{market_symbol}: β = 1.0 (市场基准)")

        # Step 2: 处理股票资产
        for stock in stocks:
            if stock == market_symbol:
                continue  # 市场指数已在Step 1处理
            
            display_stock = stock

            if market_type == "CN":
                for key in dfs.keys():
                    if key.startswith(stock + "-"):
                        display_stock = key
                        break

            elif market_type == "US":
                for key in dfs.keys():
                    if key.startswith(stock + "-"):
                        display_stock = key
                        break

            if display_stock not in dfs:
                logger.warning(f"跳过 {display_stock}：没有数据")
                continue
            stock_return = dfs[display_stock]['daily_return']
            beta = self.calculate_beta(stock_return, market_return)
            betas[display_stock] = beta
            logger.info(f"{display_stock}: β = {beta:.4f}")

        # Step 3: 处理商品资产（关键修复！）
        commodity_count = 0
        for asset_key in dfs.keys():
            # 跳过股票和市场指数
            is_stock = any(asset_key == stock or asset_key.startswith(stock + "-") for stock in stocks)
            is_market = asset_key == market_symbol
            
            if not is_stock and not is_market:
                # 这是商品资产
                commodity_return = dfs[asset_key]['daily_return']
                beta = self.calculate_beta(commodity_return, market_return)
                betas[asset_key] = beta
                commodity_count += 1
                logger.info(f"📦 {asset_key}: β = {beta:.4f} (商品)")
        
        if commodity_count > 0:
            logger.info(f"✅ 成功计算 {commodity_count} 个商品的β值")

        return betas, market_return

    def calculate_expected_returns(self, betas, market_return, risk_free_rate_annual=0.04):
        """
        计算各股票的预期收益率（年化）

        参数:
        - betas: β值字典
        - market_return: 市场日收益率序列
        - risk_free_rate_annual: 年化无风险利率

        返回:
        - expected_returns: 字典，key为股票代码，value为预期年化收益率
        - market_risk_premium: 市场风险溢价
        - E_Rm: 市场预期年化收益率
        """
        Rf = risk_free_rate_annual / 252
        E_Rm = market_return.mean() * 252
        market_risk_premium = E_Rm - (Rf * 252)

        expected_returns = {}
        for stock, beta in betas.items():
            expected_returns[stock] = Rf * 252 + beta * market_risk_premium

        logger.info(f"无风险利率(年化): {risk_free_rate_annual*100:.2f}%")
        logger.info(f"市场预期收益率(年化): {E_Rm*100:.2f}%")
        logger.info(f"市场风险溢价: {market_risk_premium*100:.2f}%")

        return expected_returns, market_risk_premium, E_Rm

    def plot_sml(self, betas, expected_returns, E_Rm, risk_free_rate_annual=0.04,
                 stocks=None, save_path=None, case_name=None):
        """
        绘制证券市场线(SML)图

        参数:
        - betas: β值字典
        - expected_returns: 预期收益率字典
        - E_Rm: 市场预期年化收益率
        - risk_free_rate_annual: 年化无风险利率
        - stocks: 股票代码列表（用于控制显示的股票）
        - save_path: 保存路径（可选）
        - case_name: 测试案例名称（用于文件名区分）

        返回:
        - plot_path: 图表保存路径
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="Plotting SML")

        Rf_annual = risk_free_rate_annual

        display_stocks = stocks if stocks else list(betas.keys())
        num_stocks = len([s for s in display_stocks if s != 'SPY' and s in betas])

        # 根据股票数量动态调整图表宽度和标注偏移
        if num_stocks <= 5:
            fig_width = 16
            offset_x = 40
        elif num_stocks <= 10:
            fig_width = 20
            offset_x = 50
        elif num_stocks <= 20:
            fig_width = 24
            offset_x = 60
        elif num_stocks <= 30:
            fig_width = 28
            offset_x = 70
        else:
            fig_width = 32
            offset_x = 80

        # 创建动态宽度的图表
        plt.figure(figsize=(fig_width, 14))

        beta_range = np.linspace(0, 2, 100)
        sml_returns = Rf_annual + beta_range * (E_Rm - Rf_annual)

        plt.plot(beta_range, sml_returns, 'r-', linewidth=2, label='SML (CAPM)')

        for idx, stock in enumerate(display_stocks):
            if stock not in betas:
                continue
            if stock == 'SPY':
                continue
            plt.scatter(betas[stock], expected_returns[stock], s=80, alpha=0.7, label=stock)

            # 根据索引交替设置标注位置，避免重叠
            if idx % 2 == 0:
                xytext = (offset_x, 8)
            else:
                xytext = (-offset_x, -12)

            plt.annotate(stock,
                         xy=(betas[stock], expected_returns[stock]),
                         xytext=xytext,
                         textcoords='offset points',
                         fontsize=8,
                         fontweight='normal',
                         alpha=0.85,
                         bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.6, edgecolor='none'))

        plt.scatter(0, Rf_annual, color='black', label=f'无风险资产 (Rf={Rf_annual * 100:.2f}%)', s=120, zorder=5)
        plt.scatter(1, E_Rm, color='blue', label=f'市场组合 (SPY, E(Rm)={E_Rm * 100:.2f}%)', s=120, zorder=5)

        plt.xlabel('系统性风险 (β)', fontsize=13, fontname=chinese_font, labelpad=10)
        plt.ylabel('预期收益率 (年化)', fontsize=13, fontname=chinese_font, labelpad=10)
        plt.title('证券市场线 (SML) 分析', fontsize=18, fontweight='bold', fontname=chinese_font, pad=15)

        # 调整图例布局：增加列数，减小字体，增加间距
        num_columns = min(len(display_stocks), 30)

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

        plt.grid(True, alpha=0.3)

        # 使用 tight_layout 并增加边距，确保标注不被裁剪
        plt.tight_layout()
        plt.subplots_adjust(left=0.06, right=0.97, top=0.92, bottom=0.15)

        if save_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if case_name:
                save_path = os.path.join(CommonParameters.outBoundPath,
                                         f"sml_analysis_{case_name}_{timestamp}.png")
            else:
                save_path = os.path.join(CommonParameters.outBoundPath,
                                         f"sml_analysis_{timestamp}.png")

        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"SML 图表已保存: {save_path}")
        plt.close()

        return save_path



    def generate_sml_report(self, stocks, start_date, end_date, risk_free_rate_annual=0.04,
                           display_stocks=None, market_type="US", market_symbol=None, case_name=None,
                           include_commodities=None):
        """
        生成完整的 SML 分析报告（支持股票 + 商品混合分析）

        参数:
        - stocks: 股票代码列表
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')
        - risk_free_rate_annual: 年化无风险利率
        - display_stocks: 要在图表中显示的股票列表（可选）
        - market_type: 市场类型 ['US', 'CN']
        - market_symbol: 市场指数符号（美股默认 SPY，A股默认 000001.SH）
        - case_name: 测试案例名称（用于文件名区分）
        - include_commodities: 商品配置字典，例如 {'GC': '黄金', 'CL': '原油'}

        返回:
        - results: 包含所有分析结果的字典
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="Starting complete SML analysis")

        if market_symbol is None:
            if market_type == "US":
                market_symbol = "SPY"
            elif market_type == "CN":
                market_symbol = "000001.SH"
            else:
                raise ValueError(f"不支持的市场类型: {market_type}")

        logger.info("=" * 80)
        logger.info("🚀 开始 SML 分析（支持商品）")
        logger.info(f"   市场类型: {market_type}")
        logger.info(f"   市场指数: {market_symbol}")
        logger.info(f"   股票数量: {len(stocks)}")
        if include_commodities:
            logger.info(f"   商品数量: {len(include_commodities)} - {list(include_commodities.keys())}")
        logger.info(f"   日期范围: {start_date} 至 {end_date}")
        logger.info(f"   无风险利率: {risk_free_rate_annual*100:.2f}%")
        logger.info("=" * 80)

        logger.info("\n📊 步骤 1/4: 获取资产数据（股票 + 商品）...")
        dfs = self.fetch_stock_data(stocks, start_date, end_date, 
                                   market_type=market_type, 
                                   market_symbol=market_symbol,
                                   include_commodities=include_commodities)

        if not dfs:
            raise ValueError("未能获取任何股票数据")

        logger.info("\n📈 步骤 2/4: 计算日收益率...")
        for display_stock in list(dfs.keys()):
            dfs[display_stock] = self.calculate_daily_return(dfs[display_stock])

        logger.info("\n🔢 步骤 3/4: 计算β值和预期收益率...")
        betas, market_return = self.calculate_all_betas(dfs, stocks, market_symbol=market_symbol, market_type=market_type)
        expected_returns, market_risk_premium, E_Rm = self.calculate_expected_returns(
            betas, market_return, risk_free_rate_annual)

        logger.info("\n 步骤 4/4: 绘制SML图表...")
        display_stocks_list = list(betas.keys()) if display_stocks is None else display_stocks
        plot_path = self.plot_sml(betas, expected_returns, E_Rm, risk_free_rate_annual,
                                  display_stocks_list, case_name=case_name)

        results = {
            'betas': betas,
            'expected_returns': expected_returns,
            'market_return': market_return,
            'market_risk_premium': market_risk_premium,
            'E_Rm': E_Rm,
            'risk_free_rate': risk_free_rate_annual,
            'plot_path': plot_path,
            'start_date': start_date,
            'end_date': end_date,
            'stocks': stocks,
            'market_type': market_type,
            'market_symbol': market_symbol
        }

        logger.info("\n" + "=" * 80)
        logger.info("✅ SML 分析完成！")
        logger.info(f"   市场类型: {market_type}")
        logger.info(f"   市场指数: {market_symbol}")
        logger.info(f"   分析股票数: {len(betas)}")
        logger.info(f"   图表路径: {plot_path}")
        logger.info("=" * 80)

        logger.info("\n β值和预期收益率汇总:")
        logger.info("-" * 80)
        for stock in sorted(betas.keys()):
            if stock != market_symbol:
                logger.info(f"{stock:20s}: β={betas[stock]:7.4f}, "
                          f"E(R)={expected_returns[stock]*100:7.2f}%")
        logger.info("-" * 80)

        return results
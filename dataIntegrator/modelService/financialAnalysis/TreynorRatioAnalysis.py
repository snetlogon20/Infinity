"""
Treynor Ratio (特雷诺比率) 分析引擎

特雷诺比率衡量的是单位系统性风险(β)所获得的超额收益
公式: TR = (E(Rp) - Rf) / βp

与夏普比率不同，特雷诺比率只考虑系统性风险(β)，而非总风险(σ)
适用于充分分散的投资组合评估
"""

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
                logger.warning(f"️ 字体加载失败 {font_path}: {e}")
                continue

    if chinese_font == 'SimHei':
        logger.warning("️ 未找到中文字体，图表中的中文可能无法正常显示")

    rcParams['font.sans-serif'] = [chinese_font, 'Arial Unicode MS', 'Microsoft YaHei', 'SimHei']
    rcParams['axes.unicode_minus'] = False

    return chinese_font

chinese_font = setup_chinese_font()


class TreynorRatioAnalysis:
    """特雷诺比率分析类"""

    def __init__(self):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="TreynorRatioAnalysis started")

    def writeLogInfo(self, className="unknown", functionName="unknown", event="unknown"):
        """记录日志信息"""
        print("%s.%s: %s" % (className, functionName, event))
        logger.info("%s.%s: %s" % (className, functionName, event))

    def fetch_asset_data(self, assets, start_date, end_date, market_type="CN", market_symbol=None, include_commodities=None):
        """
        从 ClickHouse 获取资产数据（支持多数据源：股票 + 商品）

        参数:
        - assets: 资产代码列表
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')
        - market_type: 市场类型 ['US', 'CN']
        - market_symbol: 市场指数符号（用于区分指数和股票）
        - include_commodities: 商品配置字典，例如 {'GC': '黄金', 'CL': '原油'}

        返回:
        - dfs: 字典，key为资产代码（A股格式为 ts_code-name，美股格式为 ts_code-enname），value为DataFrame
        - asset_names: 字典，key为ts_code，value为资产名称
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event=f"Fetching data for {len(assets)} assets from {start_date} to {end_date}, market={market_type}")

        if include_commodities:
            logger.info(f" 同时获取 {len(include_commodities)} 种商品数据: {list(include_commodities.keys())}")

        dfs = {}
        asset_names = {}

        # Step 1: 获取资产名称
        if market_type == "CN":
            cn_assets = [a for a in assets if a != market_symbol]
            if cn_assets:
                clickhouseService = ClickhouseService()
                asset_codes = "','".join(cn_assets)
                name_sql = f"""
                SELECT ts_code, name
                FROM indexsysdb.df_tushare_stock_basic
                WHERE ts_code IN ('{asset_codes}')
                """
                logger.info(f"🔍 查询A股名称: {len(cn_assets)} 只股票")
                name_df = clickhouseService.getDataFrameWithoutColumnsName(name_sql)
                if not name_df.empty:
                    for _, row in name_df.iterrows():
                        asset_names[row['ts_code']] = row['name']
                    logger.info(f"✅ 成功获取 {len(asset_names)} 只A股名称")
                else:
                    logger.warning(f"⚠️ 未获取到A股名称数据")

        elif market_type == "US":
            us_assets = [a for a in assets if a != market_symbol]
            if us_assets:
                clickhouseService = ClickhouseService()
                asset_codes = "','".join(us_assets)
                name_sql = f"""
                SELECT ts_code, enname
                FROM indexsysdb.df_tushare_us_stock_basic
                WHERE ts_code IN ('{asset_codes}')
                """
                logger.info(f"🔍 查询美股名称: {len(us_assets)} 只股票")
                name_df = clickhouseService.getDataFrameWithoutColumnsName(name_sql)
                if not name_df.empty:
                    for _, row in name_df.iterrows():
                        asset_names[row['ts_code']] = row['enname']
                    logger.info(f"✅ 成功获取 {len(asset_names)} 只美股名称")
                else:
                    logger.warning(f"⚠️ 未获取到美股名称数据")

        # Step 2: 获取股票/指数数据
        for asset in assets:
            is_market_index = (asset == market_symbol)

            if market_type == "US":
                sql = self._build_us_stock_sql(asset, start_date, end_date)
                display_name = asset

            elif market_type == "CN":
                if is_market_index:
                    sql = self._build_cn_index_sql(asset, start_date, end_date)
                    display_name = asset
                else:
                    sql = self._build_cn_stock_sql(asset, start_date, end_date)
                    display_name = asset

            else:
                raise ValueError(f"不支持的市场类型: {market_type}。支持的类型: ['US', 'CN']")

            clickhouseService = ClickhouseService()
            df = clickhouseService.getDataFrameWithoutColumnsName(sql)
            if df.empty:
                logger.warning(f"警告: {asset} 在 {start_date} 到 {end_date} 期间没有数据")
                continue

            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df.set_index('trade_date', inplace=True)

            # 拼接显示名称（与 CMLAnalysis 对齐）
            if market_type == "CN" and not is_market_index:
                if asset in asset_names and asset_names[asset]:
                    display_name = f"{asset}-{asset_names[asset]}"
                    logger.debug(f"   {asset} -> {display_name}")
                else:
                    logger.debug(f"   {asset}: 未找到名称，使用原始代码")

            if market_type == "US" and not is_market_index:
                if asset in asset_names and asset_names[asset]:
                    display_name = f"{asset}-{asset_names[asset]}"
                    logger.debug(f"   {asset} -> {display_name}")
                else:
                    logger.debug(f"   {asset}: 未找到名称，使用原始代码")

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

        logger.info(f" 开始获取商品数据，市场类型: {market_type}, 商品列表: {list(commodities.keys())}")

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

    def calculate_beta(self, asset_return, market_return):
        """
        用线性回归计算 β：asset_return = α + β * market_return + ε
        
        参数:
        - asset_return: 资产收益率序列
        - market_return: 市场收益率序列
        
        返回:
        - beta: β 值（系统性风险）
        """
        # 确保两个 Series 对齐且非空
        aligned_data = pd.DataFrame({
            'asset': asset_return,
            'market': market_return
        }).dropna()

        if len(aligned_data) == 0:
            raise ValueError("没有可用的收益率数据用于计算 β")

        x = aligned_data['market'].values
        y = aligned_data['asset'].values

        x = sm.add_constant(x)  # 添加截距项（α）
        model = regression.linear_model.OLS(y, x).fit()
        return model.params[1]  # 返回 β（斜率）

    def calculate_treynor_ratio(self, expected_returns_annual, betas, risk_free_rate_annual):
        """
        计算特雷诺比率
        TR = (E(Rp) - Rf) / βp
        
        参数:
        - expected_returns_annual: 年化预期收益率字典
        - betas: β 字典
        - risk_free_rate_annual: 年化无风险利率
        
        返回:
        - treynor_ratios: 特雷诺比率字典
        """
        logger.info("计算特雷诺比率...")

        treynor_ratios = {}
        for asset in expected_returns_annual.keys():
            beta = betas[asset]
            if beta != 0:  # 避免除以零
                excess_return = expected_returns_annual[asset] - risk_free_rate_annual
                treynor_ratios[asset] = excess_return / beta
            else:
                treynor_ratios[asset] = np.nan

        return treynor_ratios

    def plot_treynor_analysis(self, assets, betas, expected_returns, treynor_ratios,
                             risk_free_rate, market_return, market_risk_premium,
                             market_symbol, save_path=None, case_name=None):
        """
        绘制特雷诺比率分析图
        
        X轴: β (系统性风险)
        Y轴: 预期收益率
        每条线的斜率代表特雷诺比率
        
        参数:
        - assets: 资产代码列表
        - betas: β 字典
        - expected_returns: 预期收益率字典
        - treynor_ratios: 特雷诺比率字典
        - risk_free_rate: 无风险利率
        - market_return: 市场收益率
        - market_risk_premium: 市场风险溢价
        - market_symbol: 市场指数符号
        - save_path: 保存路径（可选）
        - case_name: 测试案例名称（用于文件名区分）
        
        返回:
        - plot_path: 图表保存路径
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="Plotting Treynor Ratio analysis")

        plt.figure(figsize=(14, 10))

        # 绘制 SML (证券市场线) - 作为参考线
        beta_range = np.linspace(0, 2.5, 100)
        sml_returns = risk_free_rate + beta_range * market_risk_premium
        plt.plot(beta_range, sml_returns * 100, 'r-', linewidth=2,
                label='市场风险溢价线 (参考)', alpha=0.5, linestyle='--')

        # 绘制各资产的点
        colors = plt.cm.viridis(np.linspace(0, 1, len(assets)))

        for idx, asset in enumerate(assets):
            if asset == market_symbol:
                # 市场组合特殊标记
                plt.scatter(
                    betas[asset],
                    expected_returns[asset] * 100,
                    color='blue', s=200, zorder=5, marker='*',
                    label=f'市场组合 ({market_symbol})',
                    edgecolors='darkblue', linewidths=2
                )
            else:
                tr = treynor_ratios[asset]
                if not np.isnan(tr):
                    color = colors[idx % len(colors)]
                    plt.scatter(
                        betas[asset],
                        expected_returns[asset] * 100,
                        color=color, s=100, zorder=4, alpha=0.8,
                        edgecolors='black', linewidths=0.8
                    )

                    # 标注资产代码和TR值
                    if idx % 2 == 0:
                        xytext = (35, 8)
                    else:
                        xytext = (-35, 8)

                    plt.annotate(
                        f'{asset}\nTR={tr*100:.2f}%',
                        xy=(betas[asset], expected_returns[asset] * 100),
                        xytext=xytext,
                        textcoords='offset points',
                        fontsize=8,
                        color=color,
                        fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.8, edgecolor='gray')
                    )

        # 标记无风险资产
        plt.scatter(0, risk_free_rate * 100, color='green', s=150, zorder=5,
                   marker='D', label=f'无风险资产 (Rf={risk_free_rate*100:.2f}%)',
                   edgecolors='darkgreen', linewidths=2)

        # 绘制从原点到各点的射线（表示特雷诺比率）
        for asset in assets[:15]:  # 只显示前15只资产，避免过于拥挤
            tr = treynor_ratios[asset]
            if not np.isnan(tr) and betas[asset] > 0:
                beta_max = max(betas.values())
                beta_line = np.linspace(0, min(betas[asset] * 1.3, beta_max), 50)
                tr_line = risk_free_rate + tr * beta_line
                plt.plot(beta_line, tr_line * 100, '--', alpha=0.25, linewidth=1.2)

        # 图表美化
        plt.xlabel('系统性风险 (β)', fontsize=13, fontweight='bold')
        plt.ylabel('年化预期收益率 (%)', fontsize=13, fontweight='bold')
        plt.title('特雷诺比率 (Treynor Ratio) 分析\n单位系统性风险的超额收益',
                 fontsize=15, fontweight='bold')

        plt.legend(loc='upper left', fontsize=9, framealpha=0.9)
        plt.grid(True, alpha=0.3, linestyle='--')

        plt.tight_layout()

        # 保存图表
        if save_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if case_name:
                save_path = os.path.join(CommonParameters.outBoundPath,
                                         f"treynor_ratio_{case_name}_{timestamp}.png")
            else:
                save_path = os.path.join(CommonParameters.outBoundPath,
                                         f"treynor_ratio_{timestamp}.png")

        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"📊 特雷诺比率图表已保存: {save_path}")
        plt.close()

        return save_path

    def generate_treynor_report(self, assets, start_date, end_date, risk_free_rate_annual=0.04,
                               market_type="CN", trading_days=252, market_symbol=None, case_name=None,
                               include_commodities=None):
        """
        生成完整的特雷诺比率分析报告（支持股票 + 商品混合分析）

        参数:
        - assets: 资产代码列表
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')
        - risk_free_rate_annual: 年化无风险利率
        - market_type: 市场类型 ['US', 'CN']
        - trading_days: 年交易日数
        - market_symbol: 市场指数符号
        - case_name: 测试案例名称（用于文件名区分）
        - include_commodities: 商品配置字典，例如 {'GC': '黄金', 'CL': '原油'}

        返回:
        - results: 包含所有分析结果的字典
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="Starting complete Treynor Ratio analysis")

        if market_symbol is None:
            if market_type == "US":
                market_symbol = "SPY"
            elif market_type == "CN":
                market_symbol = "000001.SH"
            else:
                raise ValueError(f"不支持的市场类型: {market_type}")

        logger.info("=" * 80)
        logger.info("🎯 开始特雷诺比率 (Treynor Ratio) 分析")
        logger.info(f"   市场类型: {market_type}")
        logger.info(f"   市场指数: {market_symbol}")
        logger.info(f"   资产数量: {len(assets)}")
        if include_commodities:
            logger.info(f"   商品数量: {len(include_commodities)} - {list(include_commodities.keys())}")
        logger.info(f"   日期范围: {start_date} 至 {end_date}")
        logger.info(f"   无风险利率: {risk_free_rate_annual*100:.2f}%")
        logger.info("=" * 80)

        # Step 1: 获取资产数据
        logger.info("\n📊 步骤 1/5: 获取资产数据（股票 + 商品）...")
        dfs = self.fetch_asset_data(assets, start_date, end_date,
                                   market_type=market_type,
                                   market_symbol=market_symbol,
                                   include_commodities=include_commodities)

        if not dfs:
            raise ValueError("未能获取任何资产数据")

        # Step 2: 过滤共同日期
        logger.info("\n 步骤 2/5: 过滤共同日期...")
        filtered_dfs, common_dates = self.filter_common_dates(dfs)

        # Step 3: 计算收益率
        logger.info("\n 步骤 3/5: 计算日收益率...")
        returns_df = self.calculate_daily_return(filtered_dfs)

        # Step 4: 计算 β 和预期收益率
        logger.info("\n⚡ 步骤 4/5: 计算 β 和预期收益率...")
        market_return = returns_df[market_symbol]
        betas = {}
        expected_returns = {}

        for asset in returns_df.columns:
            if asset == market_symbol:
                betas[asset] = 1.0  # 市场组合的 β 恒为 1
            else:
                asset_return = returns_df[asset]
                beta = self.calculate_beta(asset_return, market_return)
                betas[asset] = beta

            # 使用历史平均收益率作为预期收益率
            expected_returns[asset] = returns_df[asset].mean() * trading_days

        # 计算市场风险溢价
        E_Rm = returns_df[market_symbol].mean() * trading_days
        market_risk_premium = E_Rm - risk_free_rate_annual

        # 计算特雷诺比率
        treynor_ratios = self.calculate_treynor_ratio(expected_returns, betas, risk_free_rate_annual)

        # Step 5: 绘制图表
        logger.info("\n🎨 步骤 5/5: 绘制特雷诺比率分析图...")
        plot_path = self.plot_treynor_analysis(
            assets=list(expected_returns.keys()),
            betas=betas,
            expected_returns=expected_returns,
            treynor_ratios=treynor_ratios,
            risk_free_rate=risk_free_rate_annual,
            market_return=E_Rm,
            market_risk_premium=market_risk_premium,
            market_symbol=market_symbol,
            case_name=case_name
        )

        results = {
            'betas': betas,
            'expected_returns': expected_returns,
            'treynor_ratios': treynor_ratios,
            'risk_free_rate': risk_free_rate_annual,
            'market_return': E_Rm,
            'market_risk_premium': market_risk_premium,
            'plot_path': plot_path,
            'start_date': start_date,
            'end_date': end_date,
            'assets': assets,
            'market_type': market_type,
            'market_symbol': market_symbol
        }

        logger.info("\n" + "=" * 80)
        logger.info("✅ 特雷诺比率分析完成！")
        logger.info(f"   市场类型: {market_type}")
        logger.info(f"   市场指数: {market_symbol}")
        logger.info(f"   分析资产数: {len(expected_returns)}")
        logger.info(f"   图表路径: {plot_path}")
        logger.info("=" * 80)

        logger.info("\n📊 特雷诺比率汇总 (按TR降序排列):")
        logger.info("-" * 80)
        logger.info(f"{'资产代码':<20} {'β':>8} {'E(R)':>10} {'TR':>10}")
        logger.info("-" * 80)

        # 按特雷诺比率排序
        sorted_assets = sorted(
            treynor_ratios.items(),
            key=lambda x: x[1] if not np.isnan(x[1]) else -np.inf,
            reverse=True
        )

        for asset, tr in sorted_assets:
            if not np.isnan(tr):
                logger.info(
                    f"{asset:<20} {betas[asset]:>8.4f} "
                    f"{expected_returns[asset]*100:>9.2f}% "
                    f"{tr*100:>9.2f}%"
                )

        logger.info("-" * 80)

        return results

"""
Sortino Ratio (索提诺比率/SOR) 分析

索提诺比率衡量的是单位下行风险所获得的超额收益
公式: SOR = (E(Rp) - Rf) / σd

其中：
- E(Rp): 投资组合预期收益率
- Rf: 无风险利率
- σd: 下行偏差（Downside Deviation），只考虑负收益的波动

与夏普比率不同，索提诺比率只惩罚下行风险，不惩罚上行波动
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
from dataIntegrator.modelService.financialAnalysis.MarketDataService import MarketDataService

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


class SORAnalysis:
    """索提诺比率(Sortino Ratio/SOR)分析类"""

    def __init__(self):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="SORAnalysis started")
        self.market_data_service = MarketDataService()

    def writeLogInfo(self, className="unknown", functionName="unknown", event="unknown"):
        """记录日志信息"""
        print("%s.%s: %s" % (className, functionName, event))
        logger.info("%s.%s: %s" % (className, functionName, event))

    def fetch_stock_data(self, stocks, start_date, end_date, market_type="CN", market_symbol=None, include_commodities=None):
        """从 ClickHouse 获取股票数据（支持多数据源：股票 + 商品）"""
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

        elif market_type == "GLOBAL":
            # 全球指数表(df_tushare_index_global)没有name字段，直接使用ts_code
            logger.info(f"🌍 全球指数数据源不包含名称信息，将使用指数代码作为显示名称")
            pass

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

            elif market_type == "GLOBAL":
                sql = self._build_global_index_sql(stock, start_date, end_date)
                display_name = stock

            else:
                raise ValueError(f"不支持的市场类型: {market_type}。支持的类型: ['US', 'CN', 'GLOBAL']")

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

    def _build_global_index_sql(self, stock, start_date, end_date):
        """构建全球指数查询SQL"""
        return f"""
        SELECT
            trade_date as trade_date,
            close as close_point
        FROM df_tushare_index_global
        WHERE ts_code = '{stock}'
          AND trade_date >= '{start_date}'
          AND trade_date <= '{end_date}'
        ORDER BY trade_date ASC
        """

    def _fetch_commodities_data(self, commodities, start_date, end_date, market_type="US"):
        """获取商品数据"""
        if not commodities:
            return {}

        logger.info(f"🔍 开始获取商品数据，市场类型: {market_type}, 商品列表: {list(commodities.keys())}")

        start_date_formatted = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
        end_date_formatted = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"

        if market_type == "CN":
            table_name = "indexsysdb.df_akshare_spot_hist_sge"
            has_symbol_field = False
            logger.info(f"🇨🇳 使用国内黄金数据表: {table_name}")
        else:
            table_name = "indexsysdb.df_akshare_futures_foreign_hist"
            has_symbol_field = True
            logger.info(f"🇺🇸 使用国外期货数据表: {table_name}")

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

        clickhouseService = ClickhouseService()
        df = clickhouseService.getDataFrameWithoutColumnsName(combined_sql)

        if df.empty:
            logger.warning(f"⚠️ 警告: 未获取到任何商品数据")
            return {}

        logger.info(f"✅ 成功获取商品原始数据: {len(df)} 条记录")

        dfs = {}
        for symbol in df['ts_code'].unique():
            commodity_df = df[df['ts_code'] == symbol][['trade_date', 'close_point']].copy()
            commodity_df['trade_date'] = pd.to_datetime(commodity_df['trade_date'])
            commodity_df.set_index('trade_date', inplace=True)
            
            display_name = f"{symbol}-{commodities.get(symbol, '')}"
            dfs[display_name] = commodity_df

        return dfs

    def filter_common_dates(self, dfs):
        """过滤出所有股票共同的交易日期"""
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

        return filtered_dfs

    def calculate_daily_return(self, dfs):
        """计算各股票日收益率（对数收益率）"""
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

    def calculate_downside_deviation(self, returns, trading_days=252, target_return=0):
        """计算下行偏差（Downside Deviation）"""
        downside_returns = returns[returns < target_return]
        
        if len(downside_returns) == 0:
            return 0.0
        
        downside_variance = np.mean((downside_returns - target_return) ** 2)
        downside_deviation = np.sqrt(downside_variance) * np.sqrt(trading_days)
        
        return downside_deviation

    def calculate_sor_ratio(self, expected_returns_annual, downside_deviations, risk_free_rate_annual):
        """
        计算索提诺比率
        SOR = (E(Rp) - Rf) / σd
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="Calculating Sortino Ratio")

        sor_ratios = {}
        for stock in expected_returns_annual.keys():
            dd = downside_deviations[stock]
            if dd != 0:
                excess_return = expected_returns_annual[stock] - risk_free_rate_annual
                sor_ratios[stock] = excess_return / dd
            else:
                sor_ratios[stock] = np.nan

        return sor_ratios

    def plot_sor_analysis(self, stocks, expected_returns, downside_deviations, sor_ratios,
                         risk_free_rate, save_path=None, case_name=None):
        """绘制索提诺比率分析图"""
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="Plotting SOR Analysis")

        plt.figure(figsize=(12, 8))

        stocks_to_plot = [s for s in stocks if s in sor_ratios and not np.isnan(sor_ratios[s])]
        colors = plt.cm.viridis(np.linspace(0, 1, len(stocks_to_plot)))

        for idx, stock in enumerate(stocks_to_plot):
            sr = sor_ratios[stock]
            dd = downside_deviations[stock]
            er = expected_returns[stock]

            color = colors[idx % len(colors)]
            plt.scatter(
                dd * 100,
                er * 100,
                color=color, s=80, zorder=4, alpha=0.7,
                edgecolors='black', linewidths=0.5
            )

            if idx % 2 == 0:
                xytext = (30, 5)
            else:
                xytext = (-30, 5)

            plt.annotate(
                f'{stock}\nSOR={sr:.2f}',
                xy=(dd * 100, er * 100),
                xytext=xytext,
                textcoords='offset points',
                fontsize=7,
                color=color,
                fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7)
            )

        plt.scatter(0, risk_free_rate * 100, color='green', s=120, zorder=5,
                   marker='D', label=f'无风险资产 (Rf={risk_free_rate*100:.2f}%)')

        for stock in stocks_to_plot[:10]:
            sr = sor_ratios[stock]
            dd = downside_deviations[stock]

            if not np.isnan(sr) and dd > 0:
                dd_max = max([downside_deviations[s] for s in stocks_to_plot
                             if not np.isnan(sor_ratios[s])])
                dd_line = np.linspace(0, min(dd * 1.5, dd_max), 50)
                er_line = risk_free_rate + sr * dd_line
                plt.plot(dd_line * 100, er_line * 100, '--', alpha=0.3, linewidth=1)

        plt.axhline(y=risk_free_rate * 100, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)

        plt.xlabel('下行偏差 - 下行风险 (%)', fontsize=12, fontweight='bold')
        plt.ylabel('预期收益率 (%)', fontsize=12, fontweight='bold')
        plt.title('索提诺比率 (Sortino Ratio/SOR) 分析',
                 fontsize=14, fontweight='bold')

        plt.legend(loc='upper left', fontsize=9, framealpha=0.9)
        plt.grid(True, alpha=0.3, linestyle='--')

        plt.tight_layout()

        if save_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if case_name:
                save_path = os.path.join(CommonParameters.outBoundPath,
                                         f"sor_analysis_{case_name}_{timestamp}.png")
            else:
                save_path = os.path.join(CommonParameters.outBoundPath,
                                         f"sor_analysis_{timestamp}.png")

        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"SOR 图表已保存: {save_path}")
        plt.close()

        return save_path

    def generate_sor_report(self, stocks, start_date, end_date, risk_free_rate_annual=0.04,
                           market_type="CN", trading_days=252, market_symbol=None, case_name=None,
                           include_commodities=None):
        """生成完整的索提诺比率分析报告（支持股票 + 商品混合分析）"""
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="Starting complete SOR analysis")

        if market_symbol is None:
            if market_type == "US":
                market_symbol = "SPY"
            elif market_type == "CN":
                market_symbol = "000001.SH"
            else:
                raise ValueError(f"不支持的市场类型: {market_type}")

        logger.info("=" * 80)
        logger.info("🚀 开始 SOR (索提诺比率) 分析")
        logger.info(f"   市场类型: {market_type}")
        logger.info(f"   市场指数: {market_symbol}")
        logger.info(f"   股票数量: {len(stocks)}")
        if include_commodities:
            logger.info(f"   商品数量: {len(include_commodities)} - {list(include_commodities.keys())}")
        logger.info(f"   日期范围: {start_date} 至 {end_date}")
        logger.info(f"   无风险利率: {risk_free_rate_annual*100:.2f}%")
        logger.info("=" * 80)

        logger.info("\n📊 步骤 1/5: 获取资产数据（股票 + 商品）...")
        dfs = self.fetch_stock_data(stocks, start_date, end_date,
                                   market_type=market_type,
                                   market_symbol=market_symbol,
                                   include_commodities=include_commodities)

        if not dfs:
            raise ValueError("未能获取任何资产数据")

        logger.info("\n📅 步骤 2/5: 过滤共同日期...")
        filtered_dfs = self.filter_common_dates(dfs)

        logger.info("\n📈 步骤 3/5: 计算日收益率...")
        returns_df = self.calculate_daily_return(filtered_dfs)

        logger.info("\n⚡ 步骤 4/5: 计算预期收益率和下行偏差...")
        expected_returns = {}
        downside_deviations = {}

        for stock in returns_df.columns:
            expected_returns[stock] = returns_df[stock].mean() * trading_days
            downside_deviations[stock] = self.calculate_downside_deviation(
                returns_df[stock], trading_days, target_return=0
            )

        expected_returns_series = pd.Series(expected_returns)
        downside_deviations_series = pd.Series(downside_deviations)

        logger.info("\n🎯 步骤 5/5: 计算索提诺比率和绘图...")
        sor_ratios = self.calculate_sor_ratio(
            expected_returns, downside_deviations, risk_free_rate_annual
        )

        plot_path = self.plot_sor_analysis(
            list(expected_returns.keys()),
            expected_returns_series,
            downside_deviations_series,
            sor_ratios,
            risk_free_rate_annual,
            case_name=case_name
        )

        results = {
            'expected_returns': expected_returns,
            'downside_deviations': downside_deviations,
            'sor_ratios': sor_ratios,
            'plot_path': plot_path,
            'start_date': start_date,
            'end_date': end_date,
            'stocks': stocks,
            'market_type': market_type,
            'market_symbol': market_symbol
        }

        logger.info("\n" + "=" * 80)
        logger.info("✅ SOR 分析完成！")
        logger.info(f"   市场类型: {market_type}")
        logger.info(f"   市场指数: {market_symbol}")
        logger.info(f"   分析资产数: {len(expected_returns)}")
        logger.info(f"   图表路径: {plot_path}")
        logger.info("=" * 80)

        logger.info("\n 收益率、下行偏差和索提诺比率汇总:")
        logger.info("-" * 80)
        for stock in sorted(expected_returns.keys()):
            sr = sor_ratios.get(stock, np.nan)
            if not np.isnan(sr):
                logger.info(f"{stock:30s}: E(R)={expected_returns[stock]*100:7.2f}%, "
                          f"σd={downside_deviations[stock]*100:7.2f}%, "
                          f"SOR={sr:.4f}")
        logger.info("-" * 80)

        return results

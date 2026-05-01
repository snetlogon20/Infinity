import os
import sys
import tempfile
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
from dataIntegrator.utility.FileUtility import FileUtility

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

    def fetch_stock_data(self, stocks, start_date, end_date):
        """
        从 ClickHouse 获取股票数据

        参数:
        - stocks: 股票代码列表
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')

        返回:
        - dfs: 字典，key为股票代码，value为DataFrame
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event=f"Fetching data for {len(stocks)} stocks from {start_date} to {end_date}")

        dfs = {}
        for stock in stocks:
            sql = f"""
            SELECT
                date as trade_date,
                close as close_point
            FROM df_akshare_stock_us_daily
            WHERE symbol = '{stock}'
              AND date >= '{start_date}'
              AND date <= '{end_date}'
            ORDER BY date ASC
            """

            clickhouseService = ClickhouseService()
            df = clickhouseService.getDataFrameWithoutColumnsName(sql)
            if df.empty:
                logger.warning(f"警告: {stock} 在 {start_date} 到 {end_date} 期间没有数据")
                continue
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df.set_index('trade_date', inplace=True)
            dfs[stock] = df

        logger.info(f"成功获取 {len(dfs)} 只股票的数据")
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

    def calculate_all_betas(self, dfs, stocks):
        """
        计算所有股票的β值

        参数:
        - dfs: 股票数据字典
        - stocks: 股票代码列表

        返回:
        - betas: 字典，key为股票代码，value为β值
        - market_return: 市场收益率序列
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="Calculating betas for all stocks")

        market_return = dfs['SPY']['daily_return']
        betas = {}

        for stock in stocks:
            if stock == 'SPY':
                betas[stock] = 1.0
            else:
                if stock not in dfs:
                    logger.warning(f"跳过 {stock}：没有数据")
                    continue
                stock_return = dfs[stock]['daily_return']
                beta = self.calculate_beta(stock_return, market_return)
                betas[stock] = beta
                logger.info(f"{stock}: β = {beta:.4f}")

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
                 stocks=None, save_path=None):
        """
        绘制证券市场线(SML)图

        参数:
        - betas: β值字典
        - expected_returns: 预期收益率字典
        - E_Rm: 市场预期年化收益率
        - risk_free_rate_annual: 年化无风险利率
        - stocks: 股票代码列表（用于控制显示的股票）
        - save_path: 保存路径（可选）

        返回:
        - plot_path: 图表保存路径
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="Plotting SML")

        Rf_annual = risk_free_rate_annual

        plt.figure(figsize=(14, 9))

        beta_range = np.linspace(0, 2, 100)
        sml_returns = Rf_annual + beta_range * (E_Rm - Rf_annual)

        plt.plot(beta_range, sml_returns, 'r-', linewidth=2, label='SML (CAPM)')

        display_stocks = stocks if stocks else list(betas.keys())

        for idx, stock in enumerate(display_stocks):
            if stock not in betas:
                continue
            if stock == 'SPY':
                continue
            plt.scatter(betas[stock], expected_returns[stock], s=80, alpha=0.7, label=stock)

            if idx % 2 == 0:
                xytext = (40, -4)
            else:
                xytext = (-40, -4)

            plt.annotate(stock,
                         xy=(betas[stock], expected_returns[stock]),
                         xytext=xytext,
                         textcoords='offset points',
                         fontsize=7,
                         fontweight='normal',
                         alpha=0.8)

        plt.scatter(0, Rf_annual, color='black', label=f'无风险资产 (Rf={Rf_annual*100:.2f}%)', s=120, zorder=5)
        plt.scatter(1, E_Rm, color='blue', label=f'市场组合 (SPY, E(Rm)={E_Rm*100:.2f}%)', s=120, zorder=5)

        plt.xlabel('系统性风险 (β)', fontsize=12, fontname=chinese_font)
        plt.ylabel('预期收益率 (年化)', fontsize=12, fontname=chinese_font)
        plt.title('证券市场线 (SML) 分析', fontsize=16, fontweight='bold', fontname=chinese_font)

        num_columns = min(len(display_stocks), 20)

        plt.legend(loc='upper center',
                   bbox_to_anchor=(0.5, -0.18),
                   ncol=num_columns,
                   fontsize=6.5,
                   markerscale=0.5,
                   columnspacing=0.6,
                   handlelength=0.8,
                   handletextpad=0.3,
                   framealpha=0.9,
                   borderaxespad=0.8)

        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        if save_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            save_path = os.path.join(CommonParameters.outBoundPath,
                                     f"sml_analysis_{timestamp}.png")

        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"SML 图表已保存: {save_path}")
        plt.close()

        return save_path



    def generate_sml_report(self, stocks, start_date, end_date, risk_free_rate_annual=0.04,
                           display_stocks=None):
        """
        生成完整的 SML 分析报告

        参数:
        - stocks: 股票代码列表
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')
        - risk_free_rate_annual: 年化无风险利率
        - display_stocks: 要在图表中显示的股票列表（可选）

        返回:
        - results: 包含所有分析结果的字典
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="Starting complete SML analysis")

        logger.info("=" * 80)
        logger.info("🚀 开始 SML 分析")
        logger.info(f"   股票数量: {len(stocks)}")
        logger.info(f"   日期范围: {start_date} 至 {end_date}")
        logger.info(f"   无风险利率: {risk_free_rate_annual*100:.2f}%")
        logger.info("=" * 80)

        # 步骤1: 获取数据
        logger.info("\n📊 步骤 1/4: 获取股票数据...")
        dfs = self.fetch_stock_data(stocks, start_date, end_date)

        if not dfs:
            raise ValueError("未能获取任何股票数据")

        # 步骤2: 计算收益率
        logger.info("\n📈 步骤 2/4: 计算日收益率...")
        for stock in stocks:
            if stock in dfs:
                dfs[stock] = self.calculate_daily_return(dfs[stock])

        # 步骤3: 计算β和预期收益率
        logger.info("\n🔢 步骤 3/4: 计算β值和预期收益率...")
        betas, market_return = self.calculate_all_betas(dfs, stocks)
        expected_returns, market_risk_premium, E_Rm = self.calculate_expected_returns(
            betas, market_return, risk_free_rate_annual)

        # 步骤4: 绘制SML图
        logger.info("\n📉 步骤 4/4: 绘制SML图表...")
        plot_path = self.plot_sml(betas, expected_returns, E_Rm, risk_free_rate_annual,
                                  display_stocks if display_stocks else stocks)

        # 整理结果
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
            'stocks': stocks
        }

        # 打印总结
        logger.info("\n" + "=" * 80)
        logger.info("✅ SML 分析完成！")
        logger.info(f"   分析股票数: {len(betas)}")
        logger.info(f"   图表路径: {plot_path}")
        logger.info("=" * 80)

        logger.info("\n📋 β值和预期收益率汇总:")
        logger.info("-" * 80)
        for stock in sorted(betas.keys()):
            if stock != 'SPY':
                logger.info(f"{stock:8s}: β={betas[stock]:7.4f}, "
                          f"E(R)={expected_returns[stock]*100:7.2f}%")
        logger.info("-" * 80)

        return results

from dataIntegrator.TuShareService.TuShareService import TuShareService
import numpy as np
from dataIntegrator import CommonLib
import matplotlib.pyplot as plt
import pandas as pd

logger = CommonLib.logger
commonLib = CommonLib()

class SharpRatio(TuShareService):
    def __init__(self):
        logger.info("SharpRatio started")

    def calculate_sharpe_ratio_from_data(self, riskfree_data, portfolio_data, riskfree_column, portfolio_price_column):
        price_col = portfolio_price_column

        # Calculate mean and segma for risk-free asset
        riskfree_mean = riskfree_data[riskfree_column].mean()
        riskfree_sigma = riskfree_data[riskfree_column].std()
        logger.info(f'riskfree_mean={riskfree_mean:.6f}，riskfree_sigma={riskfree_sigma:.6f}')

        # Create a copy to avoid SettingWithCopyWarning
        portfolio_data = portfolio_data.copy().reset_index(drop=True)

        # Calculate mean and segma for portfilio asset
        # 2. 检查数据
        print("\n" + "=" * 80)
        print("📊 投资组合数据详情")
        print("=" * 80)
        print(f"数据列：{list(portfolio_data.columns)}")
        print(f"最新收盘价：{portfolio_data[portfolio_price_column].iloc[-1]:.2f} 元")
        print(f"数据行数：{len(portfolio_data)}")
        print(
            f"价格范围：{portfolio_data[portfolio_price_column].min():.2f} - {portfolio_data[portfolio_price_column].max():.2f} 元")

        # 3. 计算日收益率
        portfolio_data.loc[:, 'daily_return'] = portfolio_data[portfolio_price_column].pct_change()
        portfolio_data = portfolio_data.dropna().reset_index(drop=True)

        if len(portfolio_data) < 20:
            print("❌ 数据量不足，无法计算")
            return

        # 4. 设置参数
        trading_days = 242  # A 股年交易日数 (约 242 天)
        risk_free_rate = 0.015  # 年化无风险利率 1.5%(中国 10 年期国债)

        # 5. 计算统计量
        daily_mean = portfolio_data['daily_return'].mean()
        daily_std = portfolio_data['daily_return'].std()

        annual_return, annual_volatility, sharpe_ratio = (
            self.calculate_sharpe_ratio_from_stats(daily_mean, daily_std, risk_free_rate, trading_days))

        # 6. 计算累计收益率
        portfolio_data.loc[:, 'cumulative_return'] = (1 + portfolio_data['daily_return']).cumprod() - 1

        # 7. 打印详细结果 - 突出显示关键指标
        print("\n" + "=" * 80)
        print("💹 夏普比率计算结果摘要")
        print("=" * 80)
        print(f"{'总交易日数:':<30} {len(portfolio_data):>10,} 天")
        print(f"{'年化交易日数:':<30} {trading_days:>10} 天")
        print(f"{'年化无风险利率:':<30} {risk_free_rate:>10.2%}")
        print("-" * 80)
        print(f"{'平均日收益率:':<30} {daily_mean:>10.4%}")
        print(f"{'日收益率标准差:':<30} {daily_std:>10.4%}")
        print(f"{'年化收益率:':<30} {annual_return:>10.2%}")
        print(f"{'年化波动率:':<30} {annual_volatility:>10.2%}")
        print(f"\n{'⭐ 夏普比率:':<30} {sharpe_ratio:>10.4f}")
        print("-" * 80)
        print(f"{'期间累计收益率:':<30} {portfolio_data['cumulative_return'].iloc[-1]:>10.2%}")
        print(f"{'期间最大单日涨幅:':<30} {portfolio_data['daily_return'].max():>10.4%}")
        print(f"{'期间最大单日跌幅:':<30} {portfolio_data['daily_return'].min():>10.4%}")
        print("=" * 80)

        # 8. 结果解读 - 使用醒目的图标
        print("\n" + "=" * 80)
        print("📊 夏普比率结果解读")
        print("=" * 80)
        if sharpe_ratio > 2:
            print("✅ 夏普比率 > 2: 风险调整后回报非常优秀 ⭐⭐⭐")
        elif sharpe_ratio > 1:
            print("✅ 夏普比率 > 1: 风险调整后回报良好 ⭐⭐")
        elif sharpe_ratio > 0:
            print("⚠️  夏普比率 > 0: 获得正风险调整后收益 ⭐")
        else:
            print("❌ 夏普比率 ≤ 0: 风险调整后收益为负 ⚠️")
        print("=" * 80)

        # 9. 分年度计算 - 详细展示
        print("\n" + "=" * 80)
        print("📅 分年度夏普比率分析")
        print("=" * 80)
        print(f"{'年份':<10} {'夏普比率':>12} {'年化收益率':>15} {'年化波动率':>15} {'评价':>20}")
        print("-" * 80)

        # 添加年份列 - 使用.loc 避免警告
        portfolio_data.loc[:, 'year'] = pd.to_datetime(portfolio_data['trade_date']).dt.year

        yearly_results = []
        for year in sorted(portfolio_data['year'].unique()):
            year_data = portfolio_data[portfolio_data['year'] == year]
            if len(year_data) > 20:
                year_return = year_data['daily_return'].mean()
                year_vol = year_data['daily_return'].std()
                year_annual_return = (1 + year_return) ** trading_days - 1
                year_annual_vol = year_vol * np.sqrt(trading_days)

                if year_annual_vol > 0:
                    year_sharpe = (year_annual_return - risk_free_rate) / year_annual_vol

                    # 添加评价
                    if year_sharpe > 2:
                        rating = "优秀 ⭐⭐⭐"
                    elif year_sharpe > 1:
                        rating = "良好 ⭐⭐"
                    elif year_sharpe > 0:
                        rating = "一般 ⭐"
                    else:
                        rating = "较差 ⚠️"

                    print(
                        f"{year:<10} {year_sharpe:>12.4f} {year_annual_return:>15.2%} {year_annual_vol:>15.2%} {rating:>20}")
                    yearly_results.append({
                        'year': year,
                        'sharpe_ratio': year_sharpe,
                        'annual_return': year_annual_return,
                        'annual_volatility': year_annual_vol,
                        'rating': rating
                    })
                else:
                    print(f"{year:<10} {'N/A':>12} {'N/A':>15} {'N/A':>15} {'波动率为 0':>20}")

        print("=" * 80)

        # 10. 绘制图表 - 简化版本，避免中文字体问题
        print("\n📈 正在生成分析图表...")
        try:
            plt.figure(figsize=(15, 10))

            # 子图 1: 股价走势
            plt.subplot(3, 2, 1)
            plt.plot(portfolio_data.index, portfolio_data[price_col], label='Close Price', color='red', linewidth=2)
            plt.title('Price Trend', fontsize=12, fontweight='bold')
            plt.ylabel('Price', fontsize=10)
            plt.grid(True, alpha=0.3)
            plt.legend()

            # 子图 2: 日收益率分布
            plt.subplot(3, 2, 2)
            plt.hist(portfolio_data['daily_return'] * 100, bins=50, alpha=0.7, color='blue', edgecolor='black')
            plt.axvline(x=daily_mean * 100, color='red', linestyle='--', label=f'Mean: {daily_mean:.2%}')
            plt.title('Daily Return Distribution', fontsize=12, fontweight='bold')
            plt.xlabel('Daily Return (%)', fontsize=10)
            plt.ylabel('Frequency', fontsize=10)
            plt.grid(True, alpha=0.3)
            plt.legend()

            # 子图 3: 日收益率时间序列
            plt.subplot(3, 2, 3)
            plt.plot(portfolio_data.index, portfolio_data['daily_return'] * 100, color='green', alpha=0.7, linewidth=1)
            plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            plt.title('Daily Return Time Series', fontsize=12, fontweight='bold')
            plt.ylabel('Daily Return (%)', fontsize=10)
            plt.grid(True, alpha=0.3)

            # 子图 4: 累积收益率
            plt.subplot(3, 2, 4)
            plt.plot(portfolio_data.index, portfolio_data['cumulative_return'] * 100, color='purple', linewidth=2)
            plt.title('Cumulative Return', fontsize=12, fontweight='bold')
            plt.ylabel('Cumulative Return (%)', fontsize=10)
            plt.grid(True, alpha=0.3)

            # 子图 5: 滚动夏普比率
            plt.subplot(3, 2, 5)
            window = 60
            if len(portfolio_data) > window:
                rolling_sharpe = []
                for i in range(window, len(portfolio_data)):
                    window_returns = portfolio_data['daily_return'].iloc[i - window:i]
                    window_mean = window_returns.mean()
                    window_std = window_returns.std()
                    window_annual_return = (1 + window_mean) ** trading_days - 1
                    window_annual_vol = window_std * np.sqrt(trading_days)
                    if window_annual_vol > 0:
                        window_sharpe = (window_annual_return - risk_free_rate) / window_annual_vol
                        rolling_sharpe.append(window_sharpe)
                    else:
                        rolling_sharpe.append(0)

                plt.plot(portfolio_data.index[window:], rolling_sharpe, color='orange', linewidth=2)
                plt.axhline(y=sharpe_ratio, color='red', linestyle='--', label=f'Overall: {sharpe_ratio:.3f}')
                plt.title(f'{window}-Day Rolling Sharpe Ratio', fontsize=12, fontweight='bold')
                plt.ylabel('Rolling Sharpe', fontsize=10)
                plt.grid(True, alpha=0.3)
                plt.legend()

            plt.tight_layout()
            plt.show()
            print("✅ 图表生成成功")

        except Exception as e:
            print(f"⚠️  图表生成失败：{e}")

        # 11. 保存结果
        print("\n" + "=" * 80)
        print("💾 数据保存")
        print("=" * 80)
        try:
            file_name = f"e:\tmp\Sharpe_Analysis_{portfolio_data['trade_date'].iloc[0]}_{portfolio_data['trade_date'].iloc[-1]}.csv"
            portfolio_data.to_csv(file_name, encoding='utf-8-sig', index=False)
            print(f"✅ 数据已保存到：{file_name}")
            print(f"   文件包含 {len(portfolio_data)} 行数据")
            print(f"   包含列：{', '.join(portfolio_data.columns)}")

        except Exception as e:
            print(f"⚠️  保存文件时出错：{e}")

        print("\n" + "=" * 80)
        print("✨ 分析完成！")
        print("=" * 80)

        return sharpe_ratio, annual_return, annual_volatility

    def calculate_sharpe_ratio_from_stats(self, daily_mean, daily_std, risk_free_rate, trading_days):
        
        # 年化收益率和波动率
        annual_return = (1 + daily_mean) ** trading_days - 1
        annual_volatility = daily_std * np.sqrt(trading_days)
        # 夏普比率
        sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility

        logger.info(f'sharpe_ratio={sharpe_ratio:.6f}')
        
        return annual_return, annual_volatility, sharpe_ratio

    # def calculate_sharpe_ratio_from_stats(self, portfolio_mean, portfolio_sigma, riskfree_mean):
    #     # Calculate Sharpe Ratio
    # 
    #     # 年化收益率
    #     annualized_return = (1 + portfolio_mean) ** 252 - 1  # 252个交易日
    #     # 年化波动率
    #     annualized_volatility = portfolio_sigma * np.sqrt(252)
    # 
    #     #sharpe_ratio = (portfolio_mean - riskfree_mean) / portfolio_sigma
    #     sharpe_ratio = (annualized_return - riskfree_mean) / annualized_volatility
    # 
    #     logger.info(f'sharpe_ratio={sharpe_ratio:.6f}')
    #     return  sharpe_ratio


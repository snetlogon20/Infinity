import math
import random

import pandas
import scipy.stats as stats
from matplotlib import pyplot as plt

from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.utility.FileUtility import FileUtility


class MonteCarlo:
    def __init__(self):
        pass

    @classmethod
    def caculate_monte_carlo_single_line_normal_distribute(self, S, mu, sigma, t, times):
        x = []
        y = []
        x.append(0)
        y.append(S)

        for time in range(1, times):
            random_num = random.random()
            normsvin = stats.norm.ppf(random_num, 0, 1)

            sample = S * math.exp((mu - 0.5 * sigma * sigma) * t + sigma * math.sqrt(t) * normsvin)
            S = sample

            x.append(time)
            y.append(S)
        return x, y

    @classmethod
    def caculate_monte_carlo_single_line_lognormal_distribute(self, S, mu, sigma, t, times):
        x = []
        y = []
        x.append(0)
        y.append(S)

        for time in range(1, times):
            random_num = random.random()
            lognormsvin = stats.lognorm.ppf(random_num, 1)

            sample = S * math.exp((mu - 0.5 * sigma * sigma) * t + sigma * math.sqrt(t) * lognormsvin)
            S = sample

            x.append(time)
            y.append(S)
        return x, y

    @classmethod
    def caculate_monte_carlo_single_line_historical(cls, S, historical_returns, times):
        """历史收益率重采样模拟"""
        x, y = [0], [S]
        for _ in range(1, times):
            ret = random.choice(historical_returns)  # 随机选择历史收益率
            S *= (1 + ret)  # 应用收益率
            x.append(_)
            y.append(S)
        return x, y

    @classmethod
    def simulation_multi_series(cls, dataFrame, simulat_params):
        # 参数解析
        analysis_column = simulat_params["analysis_column"]
        init_value_col = simulat_params["init_value"]

        # 获取历史收益率（转换为小数）
        historical_returns = dataFrame[analysis_column].dropna().values / 100

        # 统计指标计算
        stats = pandas.DataFrame({
            "Mean": [historical_returns.mean()],
            "Std_Dev": [historical_returns.std()],
            "Init_Value": [dataFrame[init_value_col].iloc[-1]]  # 使用最后一天的收盘价
        })

        # 模拟参数
        S = stats["Init_Value"][0]
        times = simulat_params["times"]
        series = simulat_params["series"]
        alpha = simulat_params["alpha"]
        dist_type = simulat_params["distribution_type"]

        # 结果存储
        all_lines = []
        final_values = []
        plt.figure(figsize=(20, 8))

        # 模拟主循环
        for line in range(series):
            if line % 100 == 0:
                print(f"Processing {line + 1}/{series}...")

            # 选择分布类型
            if dist_type == "historical":
                x, y = cls.caculate_monte_carlo_single_line_historical(S, historical_returns, times)
            elif dist_type == "normal":
                mu = historical_returns.mean()
                sigma = historical_returns.std()
                t = 1 / 252  # 假设日数据
                x, y = cls.caculate_monte_carlo_single_line_normal_distribute(S, mu, sigma, t, times)
            elif dist_type == "lognormal":
                mu = historical_returns.mean()
                sigma = historical_returns.std()
                t = 1 / 252
                x, y = cls.caculate_monte_carlo_single_line_lognormal_distribute(S, mu, sigma, t, times)

            # 存储结果
            all_lines.extend(zip([line] * len(x), x, y))
            final_values.append(y[-1])
            plt.plot(x, y, alpha=0.5)

        # 风险值计算
        final_values = sorted(final_values)
        var_index = int(alpha * series)
        var = final_values[var_index]

        #股票信息
        market = simulat_params.get("market","Unknown")
        stock = simulat_params.get("stock","Unknown")
        start_date = simulat_params.get("start_date","Unknown")
        end_date = simulat_params.get("end_date", "Unknown")

        # 图表标注
        plt.axhline(var, color='red', linestyle='--',
                    label=f'VaR ({alpha * 100}%): {var:.2f}')
        plt.title(f"Monte Carlo Simulation ({dist_type})\n"
                  f'Stock: {market}-{stock} Between:{start_date} ~ {end_date}\n'
                  f"Paths: {series}, Steps: {times}, Initial Value: {S:.2f}, Mean: {stats['Mean'][0]:.6f}, SDV: {stats['Std_Dev'][0]:.6f}"
                  )
        plt.legend()
        plt.show()

        # 转换为DataFrame
        df = pandas.DataFrame(all_lines, columns=['Path', 'Step', 'Value'])
        return df


def get_dataset(market, stock, start_date, end_date):
    if market == "US":
        sql = rf"""
                select ts_code,
                        trade_date,
                        close_point,
                        open_point,
                        high_point,
                        low_point,
                        pre_close,
                        change_point,
                        pct_change,
                        vol,
                        amount,
                        vwap,
                        turnover_ratio,
                        total_mv,
                        pe,
                        pb
                from indexsysdb.df_tushare_us_stock_daily
                where ts_code = '{stock}' AND 
                trade_date>= '{start_date}' and 
                trade_date <='{end_date}'
                    """

    if market == "CN":
        sql = rf"""
                select 
                    ts_code,
                    trade_date,
                    open,
                    high,
                    low,
                    close,
                    pre_close,
                    change,
                    pct_chg,
                    vol,
                    amount
                from indexsysdb.df_tushare_stock_daily
                where ts_code = '{stock}' AND
                        trade_date >= '{start_date}' AND 
                        trade_date <= '{end_date}'
                order by trade_date
                    """

    clickhouseService = ClickhouseService()
    dataFrame = clickhouseService.getDataFrameWithoutColumnsName(sql)

    if market == "US":
        ax_line = dataFrame.plot.line(x='trade_date', y='close_point')
        ax_scatter = dataFrame.plot.scatter(x='trade_date', y='pct_change')

    elif market == "CN":
        ax_line = dataFrame.plot.line(x='trade_date', y='close')
        ax_scatter = dataFrame.plot.scatter(x='trade_date', y='pct_chg')

    ax_line.set_title(rf'Stock Close Point: {market}-{stock} Between:{start_date} ~ {end_date}')
    ax_scatter.set_title(rf'Stock Change Volatility: {market}-{stock} Between:{start_date} ~ {end_date}')

    return dataFrame


def init():
    pandas.set_option('display.max_rows', None)  # 设置打印所有行
    pandas.set_option('display.max_columns', None)  # 设置打印所有列
    pandas.set_option('display.width', None)  # 自动检测控制台的宽度
    pandas.set_option('display.max_colwidth', None)  # 设置列的最大宽度

if __name__ == "__main__":
    init()

    ###############################
    # 1. 基本模拟
    ###############################
    # monteCarlo = MonteCarlo()
    # # 1. 单线模拟 - normal_distribute
    # S, u, segma, t, times = 100, 0.1, 0.2, 0.01, 10
    # x, y = monteCarlo.caculate_monte_carlo_single_line_normal_distribute(S, u, segma, t, times)
    #
    # # 2. 单线模拟 - lognormal_distribute
    # S, u, segma, t, times = 100, 0.1, 0.2, 0.01, 10
    # x, y = monteCarlo.caculate_monte_carlo_single_line_lognormal_distribute(S, u, segma, t, times)
    #
    # #################################################
    # # 2. 多线模拟 - Normal Distribution - 花旗股票
    # #################################################
    # dataFrame = get_dataset("US","C","20240101","20241207")
    # monteCarlo = MonteCarlo()
    # simulat_params = {
    #             'init_value': 'close_point',
    #             'analysis_column': 'pct_change',
    #             't':0.01,
    #             'times':10,
    #             'series' : 1000,
    #             'alpha': 0.05,
    #             'distribution_type':'normal' # normal/lognormal/historical
    # }
    # all_line_df = monteCarlo.simulation_multi_series(dataFrame, simulat_params)
    #
    # # 写入excel
    # file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_normal", "xlsx")
    # all_line_df.to_excel(file_full_name)
    #
    # #################################################
    # # 3. 多线模拟 - LogNormal Distribution - 花旗股票
    # #################################################
    # dataFrame = get_dataset("US","C","20240101","20241207")
    # monteCarlo = MonteCarlo()
    # simulat_params = {
    #             'init_value': 'close_point',
    #             'analysis_column': 'pct_change',
    #             't':0.01,
    #             'times':10,
    #             'series' : 1000,
    #             'alpha': 0.05,
    #             'distribution_type':'lognormal' # normal/lognormal/historical
    # }
    # all_line_df = monteCarlo.simulation_multi_series(dataFrame, simulat_params)
    # # 写入excel
    # file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_lognormal", "xlsx")
    # all_line_df.to_excel(file_full_name)
    #
    #
    # #################################################
    # # 4. 多线模拟 - LogNormal Distribution - 摩根股票
    # #################################################
    # dataFrame = get_dataset("US","JPM","20240101","20241207")
    # monteCarlo = MonteCarlo()
    # simulat_params = {
    #             'init_value': 'close_point',
    #             'analysis_column': 'pct_change',
    #             't':0.01,
    #             'times':10,
    #             'series' : 1000,
    #             'alpha': 0.05,
    #             'distribution_type':'lognormal' # normal/lognormal/historical
    # }
    # all_line_df = monteCarlo.simulation_multi_series(dataFrame, simulat_params)
    # # 写入excel
    # file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_lognormal", "xlsx")
    # all_line_df.to_excel(file_full_name)
    #
    # #################################################
    # # 5. 多线模拟 - LogNormal Distribution - 浦发 - 20220101 ~ 20221207
    # #################################################
    # dataFrame = get_dataset("CN","600000.SH","20220101","20221207")
    # monteCarlo = MonteCarlo()
    # simulat_params = {
    #             'init_value': 'close',
    #             'analysis_column': 'pct_chg',
    #             't':0.01,
    #             'times':10,
    #             'series' : 1000,
    #             'alpha': 0.05,
    #             'distribution_type':'lognormal' # normal/lognormal/historical
    # }
    # all_line_df = monteCarlo.simulation_multi_series(dataFrame, simulat_params)
    # # 写入excel
    # file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_lognormal", "xlsx")
    # all_line_df.to_excel(file_full_name)
    #
    # #################################################
    # # 6. 多线模拟 - LogNormal Distribution - 浦发 - 20240101 ~ 20241207
    # #################################################
    # dataFrame = get_dataset("CN","600000.SH","20241001","20241207")
    # monteCarlo = MonteCarlo()
    # simulat_params = {
    #             'init_value': 'close',
    #             'analysis_column': 'pct_chg',
    #             't':0.01,
    #             'times':10,
    #            'series' : 1000,
    #             'alpha': 0.05,
    #             'distribution_type':'lognormal' # normal/lognormal/historical
    # }
    # all_line_df = monteCarlo.simulation_multi_series(dataFrame, simulat_params)
    # # 写入excel
    # file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_lognormal", "xlsx")
    # all_line_df.to_excel(file_full_name)
    #
    # #################################################
    # # 7. 多线模拟 - LogNormal Distribution - 绿城水务 - 20240101 ~ 20241207
    # #################################################
    # simulat_params = {
    #             'market': 'CN','stock': '601368.SH',
    #             'start_date': '20241001', 'end_date': '20241207',
    #             'init_value': 'close',
    #             'analysis_column': 'pct_chg',
    #             't':0.01,
    #             'times':10,
    #            'series' : 1000,
    #             'alpha': 0.05,
    #             'distribution_type':'lognormal' # normal/lognormal/historical
    # }
    # dataFrame = get_dataset(simulat_params['market'],simulat_params['stock'],simulat_params['start_date'],simulat_params['end_date'])
    #
    #
    # monteCarlo = MonteCarlo()
    # all_line_df = monteCarlo.simulation_multi_series(dataFrame, simulat_params)
    # # 写入excel
    # file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_lognormal", "xlsx")
    # all_line_df.to_excel(file_full_name)

    #################################################
    # 8. 多股票，多线模拟 - LogNormal Distribution - 绿城水务 - 20240101 ~ 20241207
    #################################################
    simulat_params_list = [
                # {
                #     'market': 'CN', 'stock': '603839.SH',
                #     'start_date': '20241001', 'end_date': '20241213',
                #     'init_value': 'close',
                #     'analysis_column': 'pct_chg',
                #     't': 0.01,
                #     'times': 10,
                #     'series': 1000,
                #     'alpha': 0.05,
                #     'distribution_type': 'historical'  # normal/lognormal/historical
                # },
                # {
                # 'market': 'CN','stock': '000902.SZ',
                # 'start_date': '20241001', 'end_date': '20241207',
                # 'init_value': 'close',
                # 'analysis_column': 'pct_chg',
                # 't':0.01,
                # 'times':10,
                # 'series' : 1000,
                # 'alpha': 0.05,
                # 'distribution_type':'lognormal' # normal/lognormal/historical
                # },
                # {
                # 'market': 'CN','stock': '002093.SZ',
                # 'start_date': '20241001', 'end_date': '20241207',
                # 'init_value': 'close',
                # 'analysis_column': 'pct_chg',
                # 't':0.01,
                # 'times':10,
                # 'series' : 1000,
                # 'alpha': 0.05,
                # 'distribution_type':'lognormal' # normal/lognormal/historical
                # },
                # {
                # 'market': 'CN','stock': '600490.SH',
                # 'start_date': '20241001', 'end_date': '20241207',
                # 'init_value': 'close',
                # 'analysis_column': 'pct_chg',
                # 't':0.01,
                # 'times':10,
                # 'series' : 1000,
                # 'alpha': 0.05,
                # 'distribution_type':'lognormal' # normal/lognormal/historical
                # },
                # {
                # 'market': 'CN','stock': '601368.SH',
                # 'start_date': '20241001', 'end_date': '20241207',
                # 'init_value': 'close',
                # 'analysis_column': 'pct_chg',
                # 't':0.01,
                # 'times':10,
                # 'series' : 1000,
                # 'alpha': 0.05,
                # 'distribution_type':'lognormal' # normal/lognormal/historical
                # },
                {
                'market': 'US','stock': 'C',
                'start_date': '20221001', 'end_date': '20241119',
                'init_value': 'close_point',
                'analysis_column': 'pct_change',
                't':0.01,
                'times':2,
                'series' : 10000,
                'alpha': 0.05,
                'distribution_type':'historical' # normal/lognormal/historical
                },
                # {
                #     'market': 'US','stock': 'JPM',
                #     'start_date': '20241001', 'end_date': '20241207',
                #     'init_value': 'close_point',
                #     'analysis_column': 'pct_change',
                #     't': 0.01,
                #     'times': 10,
                #    'series' : 1000,
                #     'alpha': 0.05,
                #     'distribution_type': 'lognormal'  # normal/lognormal/historical
                # },
                # {
                #     'market': 'CN','stock': '600000.SH',
                #     'start_date': '20241001', 'end_date': '20241207',
                #     'init_value': 'close',
                #     'analysis_column': 'pct_chg',
                #     't': 0.01,
                #     'times': 10,
                #    'series' : 1000,
                #     'alpha': 0.05,
                #     'distribution_type': 'lognormal'  # normal/lognormal/historical
                # },
    ]

    for simulat_params in simulat_params_list:
        dataFrame = get_dataset(simulat_params['market'], simulat_params['stock'], simulat_params['start_date'],
                                simulat_params['end_date'])
        monteCarlo = MonteCarlo()
        all_line_df = monteCarlo.simulation_multi_series(dataFrame, simulat_params)
        # 写入excel
        file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_lognormal", "xlsx")
        all_line_df.to_excel(file_full_name)

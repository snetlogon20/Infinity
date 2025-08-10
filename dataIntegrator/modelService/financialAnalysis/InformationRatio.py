from operator import itemgetter

import pandas as pd
from parso.python.tree import Class

from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.modelService.financialAnalysis.TrackingError import TrackingError

class InformationRatio:
    def caculate_information_ratio_with_dataframe(self,tev_data,tev_portfolio_column, tev_benchmark_column):

        # Calculate mean of portfolio asset
        portfolio_mean = tev_data[tev_portfolio_column].mean()
        print("portfolio_column_mean: {:.6f}".format(portfolio_mean))

        # Calculate mean for benchmark asset
        benchmark_mean = tev_data[tev_benchmark_column].mean()
        print("benchmark_mean: {:.6f}".format(benchmark_mean))

        # Calculate tev_data
        trackingError = TrackingError()
        tev = trackingError.caculate_TEV_with_dataframe(tev_data, tev_portfolio_column, tev_benchmark_column)
        print("tev: {:.6f}".format(tev))

        information_ratio = self.caculate_information_ratio_with_number(benchmark_mean, portfolio_mean, tev)

        return information_ratio

    def caculate_information_ratio_with_number(self, benchmark_mean, portfolio_mean, tev):
        # Calculate information Ratio
        information_ratio = (portfolio_mean - benchmark_mean) / tev
        print("information_ratio: {:.6f}".format(information_ratio))
        return information_ratio

    def get_information_ratio_dataframe(self, ts_code_portfolio, ts_code_benchmark, start_date, end_date, information_ratio_data_portfolio_columns):
        information_ratio = f"""select calendar.trade_date, 
                              us_stock_daily_portfolio.pct_change as portfolio_pct_change,
                              us_stock_daily_benchmark.pct_change as benchmark_pct_change
                      from indexsysdb.df_sys_calendar calendar
                      left join (
                          select trade_date, pct_change from indexsysdb.df_tushare_us_stock_daily
                          where ts_code = '{ts_code_portfolio}' AND trade_date >= '{start_date}' and trade_date <= '{end_date}'
                          ) us_stock_daily_portfolio
                      on calendar.trade_date = us_stock_daily_portfolio.trade_date 
                      left join (
                          select trade_date, pct_change from indexsysdb.df_tushare_us_stock_daily
                          where ts_code = '{ts_code_benchmark}' AND trade_date >= '{start_date}' and trade_date <= '{end_date}'
                          ) us_stock_daily_benchmark
                      on calendar.trade_date = us_stock_daily_benchmark.trade_date 
                      where calendar.trade_date >= '{start_date}' and calendar.trade_date <= '{end_date}'"""

        clickhouClickhouseService = ClickhouseService()
        information_ratio_data = clickhouClickhouseService.getDataFrame(information_ratio, information_ratio_data_portfolio_columns)

        return information_ratio_data

def create_combinations():
    """
    在此处增加你需要分析的所有股票，将会为你做cross join
    """

    #from itertools import combinations
    from itertools import permutations

    # 产品列表
    products = ['C', 'BAC', 'JPM', 'INTC', 'AAPL', 'NVDA','MSFT','BX','GS','MS']

    # 创建字典，存储组合
    portfolio_param_list = []

    # 生成所有两两组合
    #for combo in combinations(products, 2):
    for combo in permutations(products, 2):
        key = f"{combo[0]}/{combo[1]}"
        print(key)

        params = {
            'trade_start_date': '20220101',
            'trade_end_date': '20241027',
            'portfolio': f"{combo[0]}",
            'benchmark': f"{combo[1]}",
            'portfolio_columns': ["trade_date", "portfolio_pct_change", "benchmark_pct_change"]
        }
        portfolio_param_list.append(params)

    print(portfolio_param_list)
    return portfolio_param_list

if __name__ == "__main__":


    #############################
    # Option 1 Simple method
    #############################
    trackingError = TrackingError()
    tev = trackingError.caculate_TEV_with_number(0.14,0.2,0.98)

    informationRatio = InformationRatio()
    information_ratio = informationRatio.caculate_information_ratio_with_number(0.08, 0.1, tev)

    print(f'information_ratio: {information_ratio:.6f}')

    #############################
    # Option 2 iterate by List of Dictionary
    #############################
    information_ratio_dict = {}
    portfolio_param_list = []

    portfolio_param_list = create_combinations()
    for params in portfolio_param_list:
        informationRatio = InformationRatio()
        tev_data = informationRatio.get_information_ratio_dataframe(
                                     params['portfolio'],
                                     params['benchmark'],
                                     params['trade_start_date'],
                                     params['trade_end_date'],
                                     params['portfolio_columns'])
        tev_portfolio_column = "portfolio_pct_change"
        tev_benchmark_column = "benchmark_pct_change"
        information_ratio = informationRatio.caculate_information_ratio_with_dataframe(tev_data, tev_portfolio_column, tev_benchmark_column)
        #information_ratio_dict["name"] = params['portfolio']+"/"+params['benchmark']
        information_ratio_dict[params['portfolio']+"/"+params['benchmark']] = information_ratio


    print(information_ratio_dict)



    information_ratio_df = pd.DataFrame.from_dict(information_ratio_dict, orient='index')
    #information_ratio_df = information_ratio_df.sort_values(by='Information Ratio', ascending=False)
    # for index, row in information_ratio_df.iterrows():
    #     print(f"Index: {index}, Information Ratio: {row['Information Ratio']:.6f}")

    print(information_ratio_df)

    import matplotlib.pyplot as plt

    sorted_dict = dict(sorted(information_ratio_dict.items(), key=itemgetter(1)))
    keys = list(sorted_dict.keys())
    values = list(sorted_dict.values())
    # 创建散点图
    plt.scatter(keys, values)

    # 设置图表标题和轴标签
    plt.title('Scatter Chart from Dictionary')
    plt.xlabel('Keys')
    plt.ylabel('Values')
    plt.xticks(rotation=45)

    # 显示图表
    plt.show()
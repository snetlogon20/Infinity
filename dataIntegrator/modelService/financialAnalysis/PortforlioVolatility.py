import pandas as pd

from dataIntegrator.LLMSuport.RAGFactory.RAGFactory import RAGFactory
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.TuShareService.TuShareService import TuShareService
import matplotlib.pyplot as plt
import itertools
import sys

class PortfolioVolatilityCalculator(TuShareService):

    def __init__(self, weight_a: float, weight_b: float, portfolio_data: pd.DataFrame):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="PortfolioVolatilityCalculator started")
        self.weight_a = weight_a
        self.weight_b = weight_b
        self.portfolio_data = portfolio_data
        self.results_df = pd.DataFrame()

    def calculate_static_mean_and_volatility(self):
        mean_a = self.portfolio_data['portfolio_a'].mean()
        mean_b = self.portfolio_data['portfolio_b'].mean()
        sigma_a = self.portfolio_data['portfolio_a'].std()
        sigma_b = self.portfolio_data['portfolio_b'].std()
        rho_ab = self.portfolio_data[['portfolio_a', 'portfolio_b']].corr().iloc[0, 1]

        print("mean_a:",mean_a)
        print("mean_b:",mean_b)
        print("sigma_a:",sigma_a)
        print("sigma_b:",sigma_b)
        print("rho_ab:",rho_ab)
        return mean_a, mean_b, sigma_a,sigma_b, rho_ab

    def calculate_portfolio_volatility(self,  weight_a, sigma_a, weight_b, sigma_b, rho_ab):
        portfolio_sigma = (weight_a**2 * sigma_a**2 +
                           weight_b**2 * sigma_b**2 +
                           2 * weight_a * weight_b * sigma_a * sigma_b * rho_ab) ** 0.5
        print("portfolio_sigma:", portfolio_sigma)
        return portfolio_sigma

    def calculate_portfolio_mean(self,  weight_a, mean_a, weight_b, mean_b):
        portfolio_mean = (weight_a * mean_a +
                           weight_b* mean_b )
        print("portfolio_mean:", portfolio_mean)
        return portfolio_mean

    def caculate_segma_with_dataframe(self, portfolio_data: pd.DataFrame):
        # 用于存储结果
        results = []
        calculator = PortfolioVolatilityCalculator(weight_a=0, weight_b=0, portfolio_data=portfolio_data)
        mean_a, mean_b, sigma_a,sigma_b, rho_ab = calculator.calculate_static_mean_and_volatility()
        print(f"mean_a:{mean_a}, mean_a:{mean_b}")
        print(f"sigma_a:{sigma_a}, sigma_b:{sigma_b}, rho_ab:{rho_ab}")

        # weight_a 从 0.01 到 0.99 增加
        for idx, weight_a in enumerate([i / 100 for i in range(1, 100)]):
            weight_b = 1 - weight_a

            portfolio_mean = calculator.calculate_portfolio_mean(weight_a, mean_a, weight_b, mean_b)
            portfolio_volatility = calculator.calculate_portfolio_volatility(weight_a, sigma_a, weight_b, sigma_b, rho_ab)

            results.append({'weight_a': weight_a, 'weight_b': weight_b,
                            'portfolio_mean': portfolio_mean,'portfolio_volatility': portfolio_volatility})
        # 转换为 DataFrame
        self.results_df = pd.DataFrame(results)
        print(self.results_df)
        return self.results_df

    def save_resultset(self, results_df, path):
        results_df.to_excel(r'D:\workspace_python\dataIntegrator\dataIntegrator\data\outbound\PortfolioVolatitity.results.xlsx', index=False, encoding='utf-8')

    def display_scatter_chart(self, results_df):
        plt.scatter(results_df['portfolio_volatility'], results_df['portfolio_mean'], alpha=0.7)
        plt.xlabel('portfolio_mean A')
        plt.ylabel('Portfolio Volatility')
        plt.title('Weight A vs Portfolio Volatility')
        plt.show()

    def display_scatter_chart_with_color_dict(self, results_df):
        plt.scatter(results_df['portfolio_volatility'], results_df['portfolio_mean'], alpha=0.7)
        plt.xlabel('portfolio_mean A')
        plt.ylabel('Portfolio Volatility')
        plt.title('Weight A vs Portfolio Volatility')
        plt.show()

    def generate_sql_query(self, params):
        """
        生成SQL查询语句，用于获取特定时间段和股票代码的百分比变化数据。

        参数:
        trade_start_date (str): 交易开始日期。
        trade_end_date (str): 交易结束日期。
        portfolio_a (str): 股票代码A。
        portfolio_b (str): 股票代码B。

        返回:
        str: 生成的SQL查询语句。
        """
        trade_start_date = params.get('trade_start_date')
        trade_end_date = params.get('trade_end_date')
        portfolio_a = params.get('portfolio_a')
        portfolio_b = params.get('portfolio_b')

        portfolio_sql = f"""
        select calendar.trade_date,
               us_stock_daily_portfolio.pct_change as portfolio_pct_change,
               us_stock_daily_benchmark.pct_change  as benchmark_pct_change
        from indexsysdb.df_sys_calendar calendar
        left join (
            select trade_date, pct_change
            from indexsysdb.df_tushare_us_stock_daily
            where ts_code = '{portfolio_a}'
              and trade_date >= '{trade_start_date}'
              and trade_date <= '{trade_end_date}'
        ) us_stock_daily_portfolio
        on calendar.trade_date = us_stock_daily_portfolio.trade_date
        left join (
            select trade_date, pct_change
            from indexsysdb.df_tushare_us_stock_daily
            where ts_code = '{portfolio_b}'
              and trade_date >= '{trade_start_date}'
              and trade_date <= '{trade_end_date}'
        ) us_stock_daily_benchmark
        on calendar.trade_date = us_stock_daily_benchmark.trade_date
        where calendar.trade_date >= '{trade_start_date}'
            and calendar.trade_date <= '{trade_end_date}'
        """

        print(portfolio_sql)
        return portfolio_sql

    def get_color_dict(self, num_colors):
        color_dict = {}
        cmap = plt.cm.get_cmap('tab20', num_colors)  # 从'matplotlib'选择一个色彩映射，生成指定数量的不同颜色
        for i in range(num_colors):
            color_dict[i] = cmap(i)  # 按顺序获取颜色
        return color_dict


    def draw_scatter_chart(self, result_df_list, color_dict):
        global index, key
        for index, (key, df) in enumerate(result_df_list.items()):
            plt.scatter(df['portfolio_volatility'], df['portfolio_mean'], color=color_dict[index], label=key, s=5)
        # 设置图表标题和标签
        plt.xlabel('Portfolio Volatility')
        plt.ylabel('Portfolio Mean')
        plt.title('Scatter Chart of Three Series Data')
        plt.legend()
        plt.show()

    def test_portfolio_volatility(self, portfolio_sql,params):

        portfolio_columns = params.get('portfolio_columns')
        clickhouseService = ClickhouseService()
        portfolio_data = clickhouseService.getDataFrame(portfolio_sql, portfolio_columns)

        portfolioVolatilityCalculator = PortfolioVolatilityCalculator(weight_a=0, weight_b=0, portfolio_data=portfolio_data)
        results_df = portfolioVolatilityCalculator.caculate_segma_with_dataframe(portfolio_data)
        portfolioVolatilityCalculator.save_resultset(results_df,r'D:\workspace_python\dataIntegrator\dataIntegrator\data\outbound\PortfolioVolatitity.results.xlsx')
        #portfolioVolatilityCalculator.display_scatter_chart(results_df)
        return results_df

    def test_portfolio_volatility_with_any_pair(self, response_dict):

        elements = response_dict["results"]["ts_code"]  # .tolist()
        unique_elements = list(set(elements))

        result_pairs = self.generate_pairs(unique_elements)

        param_list = []
        start_date = response_dict["start_date"]
        end_date = response_dict["end_date"]
        columns = ['trade_date', 'portfolio_a', 'portfolio_b']

        for pair in result_pairs:
            param_dict = {
                'trade_start_date': start_date,
                'trade_end_date': end_date,
                'portfolio_a': pair[0],
                'portfolio_b': pair[1],
                'portfolio_columns': columns
            }
            param_list.append(param_dict)

        result_df_list = {}
        for params in param_list:
            portfolio_sql = self.generate_sql_query(params)
            results_df = self.test_portfolio_volatility(portfolio_sql, params)
            result_df_list[f"{params['portfolio_a']}/{params['portfolio_b']}"] = results_df

        color_dict = self.get_color_dict(num_colors=len(result_df_list))
        #self.draw_scatter_chart(result_df_list, color_dict)

        return result_df_list

    def generate_pairs(self, elements):
        pairs = list(itertools.combinations(elements, 2))
        return pairs


def test_portfolio_pair_by_pair():
    """
    在此处增加你需要分析的 一对股票
    """
    result_df_list = {}
    portfolio_param_list = []

    params = {
        'trade_start_date': '20220101',
        'trade_end_date': '20241027',
        'portfolio_a': 'C',
        'portfolio_b': 'BAC',
        'portfolio_columns': ["trade_date", "portfolio_a", "portfolio_b"]
    }
    portfolio_param_list.append(params)
    params = {
        'trade_start_date': '20220101',
        'trade_end_date': '20241027',
        'portfolio_a': 'C',
        'portfolio_b': 'JPM',
        'portfolio_columns': ["trade_date", "portfolio_a", "portfolio_b"]
    }
    portfolio_param_list.append(params)
    params = {
        'trade_start_date': '20220101',
        'trade_end_date': '20241027',
        'portfolio_a': 'C',
        'portfolio_b': 'AAPL',
        'portfolio_columns': ["trade_date", "portfolio_a", "portfolio_b"]
    }
    portfolio_param_list.append(params)
    params = {
        'trade_start_date': '20220101',
        'trade_end_date': '20241027',
        'portfolio_a': 'JPM',
        'portfolio_b': 'AAPL',
        'portfolio_columns': ["trade_date", "portfolio_a", "portfolio_b"]
    }
    portfolio_param_list.append(params)
    params = {
        'trade_start_date': '20220101',
        'trade_end_date': '20241027',
        'portfolio_a': 'NVDA',
        'portfolio_b': 'INTC',
        'portfolio_columns': ["trade_date", "portfolio_a", "portfolio_b"]
    }
    portfolio_param_list.append(params)
    params = {
        'trade_start_date': '20220101',
        'trade_end_date': '20241027',
        'portfolio_a': 'NVDA',
        'portfolio_b': 'AAPL',
        'portfolio_columns': ["trade_date", "portfolio_a", "portfolio_b"]
    }
    portfolio_param_list.append(params)
    for params in portfolio_param_list:
        portfolioVolatilityCalculator = PortfolioVolatilityCalculator(weight_a=0, weight_b=0,
                                                                      portfolio_data=pd.DataFrame())
        portfolio_sql = portfolioVolatilityCalculator.generate_sql_query(params)
        results_df = portfolioVolatilityCalculator.test_portfolio_volatility(portfolio_sql, params)
        result_df_list[f"{params['portfolio_a']}/{params['portfolio_b']}"] = results_df
    portfolioVolatilityCalculator = PortfolioVolatilityCalculator(weight_a=0, weight_b=0, portfolio_data=pd.DataFrame())
    color_dict = portfolioVolatilityCalculator.get_color_dict(num_colors=len(result_df_list))
    portfolioVolatilityCalculator.draw_scatter_chart(result_df_list, color_dict)


def test_portfolio_by_AIAgent():
    knowledge_base_file_path = rf"D:\workspace_python\dataIntegrator\dataIntegrator\LLMSuport\RAGFactory\configurations\RAG_SQL_inquiry_stocks_code_knowledge_base.json"
    prompt_file_path = rf"D:\workspace_python\dataIntegrator\dataIntegrator\LLMSuport\RAGFactory\configurations\RAG_SQL_inquiry_stocks_code_prompts.txt"

    question = """帮我找出花旗， 美国银行，JP 摩根， 苹果，英伟达， 因特尔的股票代码。股票数据需要2023-01-01到2023-12-31之间的数据。不需要冗余数据，返回单一股票代码即可。"""

    response_dict = RAGFactory.run_rag_inquiry(
        "RAG_SQL_inquiry_stocks_code", "spark",
        question, knowledge_base_file_path, prompt_file_path)
    # response_dict = {
    #     "start_date": "20220101",
    #     "end_date": "20241027",
    #     "results": {
    #         "ts_code": ["C", "BAC", "JPM", "AAPL", "NVDA", "INTC"]
    #     }
    # }

    portfolioVolatilityCalculator = PortfolioVolatilityCalculator(weight_a=0, weight_b=0, portfolio_data=pd.DataFrame())
    portfolioVolatilityCalculator.test_portfolio_volatility_with_any_pair(response_dict)


if __name__ == "__main__":


    # test_pair_by_pair
    #test_portfolio_pair_by_pair()

    test_portfolio_by_AIAgent()
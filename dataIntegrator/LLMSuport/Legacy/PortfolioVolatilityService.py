import itertools
import pandas as pd
from dataIntegrator.LLMSuport.Legacy.FinancialAnalysisRAG import FinancialAnalysisRAG
from dataIntegrator.modelService.financialAnalysis.PortforlioVolatility import PortfolioVolatilityCalculator

class PortfolioVolatilityService:
    def generate_pairs(self, elements):
        pairs = list(itertools.combinations(elements, 2))
        return pairs

    def draw_scatter_chart(self, result_df_list):
        portfolioVolatilityCalculator = PortfolioVolatilityCalculator(weight_a=0, weight_b=0,
                                                                      portfolio_data=pd.DataFrame())
        color_dict = portfolioVolatilityCalculator.get_color_dict(num_colors=len(result_df_list))
        portfolioVolatilityCalculator.draw_scatter_chart(result_df_list, color_dict)

    def test_portfolio_volatility(self, question):
        # question = """
        # 帮我找出花旗， 美国银行，JP 摩根， 苹果，英伟达， 因特尔的股票代码。股票数据需要2023-01-01到2023-12-31之间的数据。
        # """

        question_with_hint =  f"从下面这个问题中先设法找出股票代码，还有数据的开始日期和结束日期。 问题：{question}"
        financialAnalysisRAG = FinancialAnalysisRAG()
        response = financialAnalysisRAG.process_query(question)
        if "error" in response:
            print(f"错误：{response['error']}")
            if "sql_attempt" in response:
                print(f"尝试执行的SQL：{response['sql_attempt']}")
        else:
            print("生成的SQL/SQL generated：", response["sql"])
            print("解释说明：", response["explanation_in_Mandarin"])
            print("Explain：", response["explanation_in_English"])
            print("查询结果/Result：")
            print(response["results"])
            print(response["start_date"])
            print(response["end_date"])

        elements = response["results"]["ts_code"].tolist()
        unique_elements = list(set(elements))
        result_pairs = self.generate_pairs(unique_elements)

        param_list = []
        start_date = response["start_date"]
        end_date = response["end_date"]
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

        print(param_list)

        result_df_list = {}
        for params in param_list:
            portfolioVolatilityCalculator = PortfolioVolatilityCalculator(weight_a=0, weight_b=0, portfolio_data=pd.DataFrame())
            portfolio_sql = portfolioVolatilityCalculator.generate_sql_query(params)
            results_df = portfolioVolatilityCalculator.test_portfolio_volatility(portfolio_sql, params)
            result_df_list[f"{params['portfolio_a']}/{params['portfolio_b']}"] = results_df


        return result_df_list

if __name__ == "__main__":
    portfolioVolatilityService = PortfolioVolatilityService()
    question = """
    帮我找出花旗， 美国银行，JP 摩根， 苹果，英伟达， 因特尔的股票代码。股票数据需要2023-01-01到2023-12-31之间的数据。
    """

    result_df_list = portfolioVolatilityService.test_portfolio_volatility(question)
    portfolioVolatilityService.draw_scatter_chart(result_df_list)
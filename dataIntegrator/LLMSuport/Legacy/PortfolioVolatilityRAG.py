import itertools
import pandas as pd
from dataIntegrator.LLMSuport.RAGFactory.RAGFactory import RAGFactory
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
        knowledge_base_file_path = rf"/dataIntegrator/LLMSuport/RAGFactory/configurations/RAG_SQL_inquiry_stocks_code_knowledge_base.json"
        prompt_file_path = rf"/dataIntegrator/LLMSuport/RAGFactory/configurations/RAG_SQL_inquiry_stocks_code_prompts.txt"

        question = """帮我找出花旗， 美国银行，JP 摩根， 苹果，英伟达， 因特尔的股票代码。股票数据需要2023-01-01到2023-12-31之间的数据。不需要冗余数据，返回单一股票代码即可。"""
        response_dict = RAGFactory.run_rag_inquiry(
            "RAG_SQL_inquiry_stocks_code", "spark",
            question, knowledge_base_file_path, prompt_file_path)


        elements = response_dict["results"]["ts_code"].tolist()
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
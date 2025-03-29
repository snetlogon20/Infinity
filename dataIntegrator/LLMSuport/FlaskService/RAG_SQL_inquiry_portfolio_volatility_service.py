from dataIntegrator.LLMSuport.RAGFactory.RAGFactory import RAGFactory
from dataIntegrator.modelService.financialAnalysis.PortforlioVolatility import PortfolioVolatilityCalculator
import json
import pandas as pd

class RAG_SQL_inquiry_portfolio_volatility_service:

    @classmethod
    def RAG_SQL_inquiry_portfolio_volatility_fetch(self, agent_type, question, response_dict):
        knowledge_base_file_path = rf"D:\workspace_python\dataIntegrator\dataIntegrator\LLMSuport\RAGFactory\configurations\RAG_SQL_inquiry_stocks_code_knowledge_base.json"
        prompt_file_path = rf"D:\workspace_python\dataIntegrator\dataIntegrator\LLMSuport\RAGFactory\configurations\RAG_SQL_inquiry_stocks_code_prompts.txt"

        response_dict = RAGFactory.run_rag_inquiry(
            "RAG_SQL_inquiry_stocks_code", agent_type,
            question, knowledge_base_file_path, prompt_file_path)
        portfolioVolatilityCalculator = PortfolioVolatilityCalculator(weight_a=0, weight_b=0,
                                                                      portfolio_data=pd.DataFrame())
        result_df_list = portfolioVolatilityCalculator.test_portfolio_volatility_with_any_pair(response_dict)
        results_json_dict = {}

        for key, df in result_df_list.items():
            results_json_dict[key] = df.to_json()
        results_json_dict_json = json.dumps(results_json_dict)
        return response_dict, results_json_dict_json
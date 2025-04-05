from dataIntegrator.LLMSuport.RAGFactory.RAGFactory import RAGFactory
from dataIntegrator.LLMSuport.StreamLit.RAG_SQL_inquiry.RAG_SQL_inquiry import BaseRAGSQLInquiry
from dataIntegrator.modelService.financialAnalysis.PortforlioVolatility import PortfolioVolatilityCalculator
import json
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

class RAG_SQL_inquiry_portfolio_volatility_service(BaseRAGSQLInquiry):

    @classmethod
    def inquiry(self, agent_type, question):
        knowledge_base_file_path = rf"D:\workspace_python\dataIntegrator\dataIntegrator\LLMSuport\RAGFactory\configurations\RAG_SQL_inquiry_stocks_code_knowledge_base.json"
        prompt_file_path = rf"D:\workspace_python\dataIntegrator\dataIntegrator\LLMSuport\RAGFactory\configurations\RAG_SQL_inquiry_stocks_code_prompts.txt"

        agent_type = "spark"
        response_dict = RAGFactory.run_rag_inquiry(
            "RAG_SQL_inquiry_stocks_code", agent_type,
            question, knowledge_base_file_path, prompt_file_path)
        portfolioVolatilityCalculator = PortfolioVolatilityCalculator(weight_a=0, weight_b=0,
                                                                      portfolio_data=pd.DataFrame())
        result_df_list = portfolioVolatilityCalculator.test_portfolio_volatility_with_any_pair(response_dict)

        sql = response_dict["sql"]
        explanation_in_Mandarin = response_dict["explanation_in_Mandarin"]
        explanation_in_English = response_dict["explanation_in_English"]

        self.write_form(explanation_in_English, explanation_in_Mandarin, sql)
        self.draw_plot(result_df_list)

        return response_dict

    @classmethod
    def draw_plot(cls, result_df_list):
        try:
            fig1, ax1 = plt.subplots(figsize=(10, 6))
            for key, df in result_df_list.items():
                ax1.scatter(df['portfolio_volatility'], df['portfolio_mean'], label=key, s=5)

            ax1.set_xlabel('Portfolio Volatility')
            ax1.set_ylabel('Portfolio Mean')
            ax1.set_title('Scatter Chart of Three Series Data')
            ax1.legend()

            st.pyplot(fig1)
        except Exception as e:
            print(f"An error occurred: {e}")

    @classmethod
    def write_form(cls, explanation_in_English, explanation_in_Mandarin, sql):
        st.write(rf"**Explanation：**")
        st.write(rf"{explanation_in_English}/{explanation_in_Mandarin}")
        st.write(rf"**SQL Statement：**")
        st.write(rf"{sql}")
        st.write(rf"**Results：**")

    @classmethod
    def write_excel(cls, edited_data_frame):
        pass
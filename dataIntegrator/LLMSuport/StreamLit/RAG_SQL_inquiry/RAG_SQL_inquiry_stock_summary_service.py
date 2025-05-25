import os

from dataIntegrator import CommonParameters, CommonLib
from dataIntegrator.LLMSuport.StreamLit.RAG_SQL_inquiry.RAG_SQL_inquiry import BaseRAGSQLInquiry
from dataIntegrator.LLMSuport.RAGFactory.RAGFactory import RAGFactory
import streamlit as st
import pandas as pd
from io import BytesIO
import base64

from dataIntegrator.common.CustomError import CustomError
from dataIntegrator.modelService.MonteCarlo.MonteCarlo import MonteCarlo
from dataIntegrator.modelService.statistics.GeneralLinearRegression import GeneralLinearRegression
from dataIntegrator.plotService.PlotManager import PlotManager
from dataIntegrator.utility.SQLUtility import SQLUtility

logger = CommonLib.logger
commonLib = CommonLib()

class RAG_SQL_inquiry_stock_summary_service(BaseRAGSQLInquiry):

    @classmethod
    def inquiry(self, agent_type, question):

        try:
            knowledge_base_file_path = os.path.join(CommonParameters.rag_configuration_path,"RAG_SQL_inquiry_stock_summary_knowledge_base.json")
            prompt_file_path = os.path.join(CommonParameters.rag_configuration_path,"RAG_SQL_inquiry_stock_summary_prompts.txt")

            response_dict = (
                RAGFactory.run_rag_inquiry(
                    "RAG_SQL_inquiry_stock_summary",
                    agent_type, question,
                    knowledge_base_file_path, prompt_file_path))

            sql = response_dict["sql"]
            explanation_in_Mandarin = response_dict["explanation_in_Mandarin"]
            explanation_in_English = response_dict["explanation_in_English"]
            data_frame = response_dict["results"]

            param_dict = response_dict

            edited_data_frame = self.write_form(data_frame, explanation_in_English, explanation_in_Mandarin, sql)
            self.write_excel(edited_data_frame)

            plotManager = PlotManager()
            plotManager.draw_plot(param_dict)

            #param_dict = response_dict
            generalLinearRegression = GeneralLinearRegression()
            generalLinearRegression.run_linear_regression_by_AI(param_dict)

            if response_dict["isMonteCarloRequired"] == "yes":
                dataFrame = response_dict["results"]
                simulat_params = response_dict["MonteCarloRequirement"]
                monteCarlo = MonteCarlo()
                all_line_df = monteCarlo.simulation_multi_series(dataFrame, simulat_params)

            return response_dict
        except CustomError as e:
            st.write(e.error_code, e.error_message)
            raise e
        except Exception as e:
            st.write(e.error_code, e.error_message)
            raise commonLib.raise_custom_error(error_code="000104", custom_error_message=rf"Error when executing RAG service", e=e)

    @classmethod
    def write_form(cls, data_frame, explanation_in_English, explanation_in_Mandarin, sql):
        # 使用st.dataframe显示DataFrame
        st.write(rf"**Explanation：**")
        st.write(rf"{explanation_in_English}/{explanation_in_Mandarin}")
        st.write(rf"**SQL Statement：**")
        #st.write(rf"{sql}")
        st.code(SQLUtility().beautify_sql(sql))
        st.write(rf"**Results：**")
        edited_data_frame = st.data_editor(data_frame)
        return edited_data_frame

    @classmethod
    def write_excel(cls, edited_data_frame):
        # 提供 Excel 下载功能
        if not edited_data_frame.empty:
            try:
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    edited_data_frame.to_excel(writer, sheet_name='Sheet1', index=False)
                output.seek(0)
                b64 = base64.b64encode(output.getvalue()).decode('utf-8')  # 修改此处
                href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="query_results.xlsx" style="font-size: 12px;">Download As Excel</a>'
                st.markdown(href, unsafe_allow_html=True)
            except ImportError:
                st.error(
                    "The 'xlsxwriter' module is required for Excel export. Please install it using 'pip install xlsxwriter'.")


import os

from plantuml import PlantUML

from dataIntegrator import CommonParameters, CommonLib
from dataIntegrator.LLMSuport.StreamLit.RAG_SQL_inquiry.RAG_SQL_inquiry import BaseRAGSQLInquiry
from dataIntegrator.LLMSuport.RAGFactory.RAGFactory import RAGFactory
import streamlit as st
import pandas as pd
from io import BytesIO
import base64

from dataIntegrator.common.CustomError import CustomError
from dataIntegrator.modelService.MonteCarlo.MonteCarloRandom import MonteCarlo
from dataIntegrator.modelService.statistics.GeneralLinearRegression import GeneralLinearRegression
from dataIntegrator.plotService.PlotManager import PlotManager
from dataIntegrator.utility.SQLUtility import SQLUtility

logger = CommonLib.logger
commonLib = CommonLib()

class RAG_UML_txt2uml_service(BaseRAGSQLInquiry):

    @classmethod
    def inquiry(self, agent_type, question):

        try:
            knowledge_base_file_path = rf"D:\workspace_python\infinity\dataIntegrator\test\RegulatoryRAG2UML\Letter of Credit Requirement_RAG.txt"
            prompt_file_path = os.path.join(CommonParameters.rag_configuration_path, "RAG_UML_req2uml_prompts.txt")

            response_dict = RAGFactory.run_rag_inquiry("RAG_UML_txt2uml", CommonParameters.Default_AI_Engine, question,
                                                       knowledge_base_file_path, prompt_file_path)

            st.write(response_dict["explanation_in_Mandarin"])
            st.write(response_dict["explanation_in_English"])

            # PlantUML 服务器（可以使用公共服务器或本地部署）
            plantuml_server = "http://www.plantuml.com/plantuml/png/"
            # UML 代码（示例类图）
            uml_code = response_dict["create_table_uml_statement"]
            # 生成图表 URL
            plantuml = PlantUML(plantuml_server)
            image_url = plantuml.get_url(uml_code)
            # 在 Streamlit 中显示
            st.image(image_url)

            create_table_sql_statement_list = response_dict["create_table_sql_statement"]
            for create_table_sql_statement_dict in create_table_sql_statement_list:

                table_name = create_table_sql_statement_dict["table_name"]
                sql = create_table_sql_statement_dict["create_table_sql"]

                st.markdown(rf"**Table Name: {table_name}**")
                st.code(SQLUtility().beautify_sql(sql))

                # st.write(create_table_sql_statement_dict["table_name"])
                # st.write(create_table_sql_statement_dict["create_table_sql"])

            st.markdown(rf"**UML statement**")
            st.write(response_dict["create_table_uml_statement"])

            st.success("生成成功！")

            return response_dict
        except CustomError as e:
            st.write(e.error_code, e.error_message)
            raise e
        except Exception as e:
            st.write(e.error_code, e.error_message)
            raise commonLib.raise_custom_error(error_code="000104", custom_error_message=rf"Error when executing RAG service", e=e)
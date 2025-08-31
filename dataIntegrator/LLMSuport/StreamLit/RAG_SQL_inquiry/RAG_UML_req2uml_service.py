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

class RAG_UML_req2uml_service(BaseRAGSQLInquiry):

    @classmethod
    def inquiry(self, agent_type, question):

        try:
            question = "请按照要求生成 Database UML和建表语句,并按照JSON格式返回"

            # knowledge_base_file_path = os.path.join(CommonParameters.rag_configuration_path,"RAG_UML_req2uml.json")
            knowledge_base_file_path = os.path.join(CommonParameters.rag_configuration_path, "RAG_UML_req2uml.md")
            prompt_file_path = os.path.join(CommonParameters.rag_configuration_path, "RAG_UML_req2uml_prompts.txt")

            response_dict = RAGFactory.run_rag_inquiry("RAG_UML_txt2uml", CommonParameters.Default_AI_Engine, question,
                                                       knowledge_base_file_path, prompt_file_path)
            print(response_dict)

            st.success("生成成功！")

            return response_dict
        except CustomError as e:
            st.write(e.error_code, e.error_message)
            raise e
        except Exception as e:
            st.write(e.error_code, e.error_message)
            raise commonLib.raise_custom_error(error_code="000104", custom_error_message=rf"Error when executing RAG service", e=e)
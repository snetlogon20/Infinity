from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.LLMSuport.StreamLit.RAG_SQL_inquiry.RAG_SQL_inquiry_stock_summary_service import \
    RAG_SQL_inquiry_stock_summary_service
import sys

from dataIntegrator.LLMSuport.StreamLit.SteamLitManager.SuperInquiry import SuperInquiry
from dataIntegrator.common.CustomError import CustomError

logger = CommonLib.logger
commonLib = CommonLib()

class AnySQLInquiry(SuperInquiry):


    def __init__(self):
        self.writeLogInfo("__init__ started")

    @classmethod
    def request_for_rag_inquiry(self, question):
        if question is None or len(question) == 0:
            logger.info("question is null")
            return

        logger.info("request_for_rag_inquiry started")

        try:
            agent_type = CommonParameters.Default_AI_Engine
            service = RAG_SQL_inquiry_stock_summary_service()
            response_dict = service.inquiry(agent_type, question)
            return response_dict
        except CustomError as e:
            raise e
        except Exception as e:
            raise commonLib.raise_custom_error(error_code="000104", custom_error_message=rf"Error when executing RAG service", e=e)

        logger.info("request_for_rag_inquiry finished")
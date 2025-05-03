from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.LLMSuport.StreamLit.RAG_SQL_inquiry.RAG_SQL_inquiry_stock_summary_service import \
    RAG_SQL_inquiry_stock_summary_service
import sys

from dataIntegrator.LLMSuport.StreamLit.SteamLitManager.SuperInquiry import SuperInquiry

logger = CommonLib.logger

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
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("request_for_rag_inquiry finished")
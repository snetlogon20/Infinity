from dataIntegrator.LLMSuport.StreamLit.RAG_SQL_inquiry.RAG_SQL_inquiry_portfolio_volatility_service import \
    RAG_SQL_inquiry_portfolio_volatility_service
import sys

from dataIntegrator.LLMSuport.StreamLit.SteamLitManager.SuperInquiry import SuperInquiry


class AnyFinancialInquiry(SuperInquiry):
    def __init__(self):
        self.writeLogInfo("__init__ started")

    @classmethod
    def request_for_rag_inquiry(self, question):
        if question is None or len(question) == 0:
            print("question is null")
            return

        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="request_for_rag_inquiry started")
        try:
            agent_type = "spark"
            service = RAG_SQL_inquiry_portfolio_volatility_service
            response_dict = service.inquiry(agent_type, question)
            return response_dict
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="prepareData completed")


        return sql, explanation_in_Mandarin, explanation_in_English
from dataIntegrator.LLMSuport.ChromaService.ChromaDialogAgent import ChromaDialogAgent
from dataIntegrator.LLMSuport.StreamLit.RAG_SQL_inquiry.RAG_SQL_inquiry_stock_summary_service import \
    RAG_SQL_inquiry_stock_summary_service
import sys

from dataIntegrator.LLMSuport.StreamLit.SteamLitManager.SuperInquiry import SuperInquiry
from dataIntegrator.utility.FileUtility import FileUtility
import streamlit as st

class RAGChatBot(SuperInquiry):
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
            model_path = FileUtility.get_full_outbound_path("model", "all-MiniLM-L6-v2")
            db_persistent_path = FileUtility.get_full_outbound_path("chormadb", "persistent.db")
            meta_excel_path = FileUtility.get_full_outbound_path("inbound", "chromadb_meta_collections.xlsx")
            user_id = "snetlogon20"
            # current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            current_time = "20250406"
            session_id = f"snetlogon20_{current_time}"  # 每次启动使用新的collection，避免以前消息的干扰

            agent = ChromaDialogAgent(model_path)  # 使用继承后的对话代理类
            agent.set_persistent_folder(db_persistent_path)

            collection = agent.create_collection(model_path=model_path,
                                                 collection_name=f"{user_id}_{session_id}_ChromaDB")
            print("集合中的文档数量：", collection.count())

            query, chromadb_results, ai_response_dict = agent.process_query(user_id, question, collection,
                                                                            n_results=3)
            print(f"系统回答：{ai_response_dict['response']}")
            print("-" * 60)

            # 模拟系统响应
            system_response = f"---你好--- {ai_response_dict['response']}"
            # 更新会话历史
            st.session_state.chat_history.append((query, system_response))
            # 刷新页面以显示新对话
            st.rerun()
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="request_for_rag_inquiry finished")
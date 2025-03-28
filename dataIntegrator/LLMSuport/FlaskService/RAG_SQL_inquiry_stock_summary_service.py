from dataIntegrator.LLMSuport.RAGFactory.RAGFactory import RAGFactory

class RAG_SQL_inquiry_stock_summary_service:

    @classmethod
    def RAG_SQL_inquiry_stock_summary_service_fetch(self, agent_type, question):

        knowledge_base_file_path = rf"D:\workspace_python\dataIntegrator\dataIntegrator\LLMSuport\RAGFactory\configurations\RAG_SQL_inquiry_stock_summary_knowledge_base.json"
        prompt_file_path = rf"D:\workspace_python\dataIntegrator\dataIntegrator\LLMSuport\RAGFactory\configurations\RAG_SQL_inquiry_stock_summary_prompts.txt"
        response_dict = RAGFactory.run_rag_inquiry("RAG_SQL_inquiry_stock_summary", agent_type, question,
                                                   knowledge_base_file_path, prompt_file_path)

        return response_dict
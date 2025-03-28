from dataIntegrator.LLMSuport.RAGFactory.RAGAgent import RAGAgent  # 确保 RAGAgent 类被正确导入
from typing import Dict, Type

from dataIntegrator.LLMSuport.RAGFactory.RAG_SQL_inquiry_stock_summary import RAG_SQL_inquiry_stock_summary
from dataIntegrator.LLMSuport.RAGFactory.RAG_SQL_inquiry_stocks_code import RAG_SQL_inquiry_stocks_code


class RAGFactory:
    _registry: Dict[str, Type[RAGAgent]] = {
        "RAG_SQL_inquiry_stock_summary": RAG_SQL_inquiry_stock_summary,
        "RAG_SQL_inquiry_stocks_code": RAG_SQL_inquiry_stocks_code
    }

    @classmethod
    def new_agent(cls, agent_type: str, knowledge_base_file_path: str, prompt_file_path: str) -> RAGAgent:
        """创建代理实例"""
        agent_class = cls._registry.get(agent_type)
        if not agent_class:
            raise ValueError(f"Unregistered agent type: {agent_type}")
        return agent_class(knowledge_base_file_path, prompt_file_path)

    @classmethod
    def run_rag_inquiry(cls,  rag_model: str, agent_type: str,question: str, knowledge_base_file_path: str, prompt_file_path: str):
        """直接调用代理功能"""
        agent = cls.new_agent(rag_model, knowledge_base_file_path, prompt_file_path)
        return agent.run_single_question(agent_type, question)

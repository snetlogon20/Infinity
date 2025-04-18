from dataIntegrator.LLMSuport.RAGFactory.RAGFactory import RAGFactory
from dataIntegrator.common.CommonParameters import CommonParameters
import os

if __name__ == "__main__":


    ##############################
    # RAG_SQL_inquiry_stock_summary
    ##############################
    # knowledge_base_file_path = rf"D:\workspace_python\dataIntegrator\dataIntegrator\LLMSuport\RAGFactory\configurations\RAG_SQL_inquiry_stock_summary_knowledge_base.json"
    # prompt_file_path = rf"D:\workspace_python\dataIntegrator\dataIntegrator\LLMSuport\RAGFactory\configurations\RAG_SQL_inquiry_stock_summary_prompts.txt"
    #
    # question = "花旗银行 2024年12月26日的收盘价"
    # response_dict = RAGFactory.run_rag_inquiry(
    #     "RAG_SQL_inquiry_stock_summary", "spark",
    #     question, knowledge_base_file_path, prompt_file_path)
    # print(response_dict)

    ##############################
    # RAG_SQL_inquiry_stocks_code
    ##############################
    # knowledge_base_file_path = os.path.join(CommonParameters.basePath, "LLMSuport", "RAGFactory", "configurations", "RAG_SQL_inquiry_stocks_code_knowledge_base.json")
    # prompt_file_path = os.path.join(CommonParameters.basePath, "LLMSuport", "RAGFactory", "configurations", "RAG_SQL_inquiry_stocks_code_prompts.txt")
    #
    # question = """帮我找出花旗， 美国银行，JP 摩根， 苹果，英伟达， 因特尔的股票代码。股票数据需要2023-01-01到2023-12-31之间的数据。不需要冗余数据，返回单一股票代码即可。"""
    # response_dict = RAGFactory.run_rag_inquiry(
    #     "RAG_SQL_inquiry_stocks_code", "spark",
    #     question, knowledge_base_file_path, prompt_file_path)
    # print(response_dict)

    ##############################
    # RAG_SQL_inquiry_stock_summary
    ##############################
    # params = {
    #     "agent_type": "spark",
    #     "rag_model": "RAG_general_inquiry",
    #     "question": "what's the capital of France",
    #     "knowledge_base_file_path": os.path.join(CommonParameters.rag_configuration_path, "RAG_general_inquiry.json"),
    #     "prompt_file_path": os.path.join(CommonParameters.rag_configuration_path, "RAG_general_inquiry.txt"),
    # }
    #
    # response_dict = RAGFactory.run_rag_inquiry_with_params(params)
    # print(response_dict)

    ##############################
    # RAG_workflow_100000_inquiry
    ##############################
    params = {
        "agent_type": "spark",
        "rag_model": "RAG_general_inquiry",
        "question": "下载, 保存、然后分析数据",
        "knowledge_base_file_path": os.path.join(CommonParameters.rag_configuration_path, "RAG_workflow_100000_inquiry.json"),
        "prompt_file_path": os.path.join(CommonParameters.rag_configuration_path, "RAG_workflow_100000_inquiry.txt"),
    }

    response_dict = RAGFactory.run_rag_inquiry_with_params(params)
    print(response_dict)
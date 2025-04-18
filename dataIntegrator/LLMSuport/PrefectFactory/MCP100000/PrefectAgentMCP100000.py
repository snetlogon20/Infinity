import os

from dataIntegrator.LLMSuport.RAGFactory.RAGFactory import RAGFactory
from dataIntegrator.common.CommonLib import CommonLib
from dataIntegrator.common.CommonParameters import CommonParameters
from dataIntegrator.LLMSuport.PrefectFactory.PrefectManager import PrefectManager


class PrefectAgentMCP100000(CommonLib):
    def __init__(self):
        pass

    def call_rag_inquiry(self, query: str) -> dict:

        rag_json_file = "RAG_workflow_100000_inquiry.json"
        rag_prompt_file = "RAG_workflow_100000_inquiry.txt"
        params = {
            "agent_type": "spark",
            "rag_model": "RAG_general_inquiry",
            "question": "下载, 保存、然后分析数据",
            "knowledge_base_file_path": os.path.join(CommonParameters.rag_configuration_path, rag_json_file),
            "prompt_file_path": os.path.join(CommonParameters.rag_configuration_path, rag_prompt_file),
        }

        response_dict = RAGFactory.run_rag_inquiry_with_params(params)
        print(rf"response_dict: \n" + response_dict)

        return {"query": query, "response": response_dict}


    def run_user_input(self, user_input):
        prefectManager = PrefectManager()

        try:
            # Generate the flow firstly
            steps = prefectAgent.call_rag_inquiry(user_input)

            # Execute the flow
            prefectManager.build_flow(steps["response"])
        except Exception as e:
            print(f"发生错误: {e}")


if __name__ == "__main__":
    # 保存、下载，分析数据
    # 分析、保存、最后下载数据
    # 下载, 保存、然后分析数据

    while True:
        user_input = input("请输入工作需求（如'下载，分析并保存数据'），输入 ':exit' 退出: ")
        if user_input.lower() == ":exit":
            break

        prefectAgent = PrefectAgentMCP100000()
        prefectAgent.run_user_input(user_input)
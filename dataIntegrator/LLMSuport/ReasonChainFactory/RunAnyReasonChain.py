from dataIntegrator.LLMSuport.RAGFactory.RAGFactory import RAGFactory
from dataIntegrator.common.CommonParameters import CommonParameters
import os

from dataIntegrator.utility.FileUtility import FileUtility
from dataIntegrator.utility.TimeUtility import TimeUtility


def reason_chain_10000_inquiry():
    params = {
        "agent_type": "spark",
        "rag_model": "RAG_general_inquiry",
        "question": """

        """,
        "knowledge_base_file_path": os.path.join(CommonParameters.reason_chain_configuration_path,"RAG_reasoning_chain.json"),
        "prompt_file_path": os.path.join(CommonParameters.reason_chain_configuration_path, "RAG_reasoning_chain.txt"),
    }

    question = ""
    while True:
        # 提示用户输入
        user_input = input("\n是否继续？输入 [:run] 运行，输入 [:exit] 退出: ").strip().lower()

        # 根据输入决定是否退出循环
        if user_input == ":exit":
            print("程序已停止。")
            break
        elif user_input == ":run":
            if question.strip() == "":
                print("你还没有输入任何问题。请先输入问题。")
                continue
            print(rf"正在运行你的问题：{question}")
            params["question"] = question
            response_dict = RAGFactory.run_rag_inquiry_with_params(params)
            print(response_dict)
            question = ""  # 重置 question 为空字符串以便重新输入
        else:
            question = question + "\n" + user_input
            print(rf"你已输入：{question}")


if __name__ == "__main__":


    ##############################
    # reason_chain_10000_inquiry
    ##############################
    reason_chain_10000_inquiry()
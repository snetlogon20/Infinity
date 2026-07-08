from dataIntegrator.LLMSuport.RAGFactory.RAGFactory import RAGFactory
from dataIntegrator.common.CommonParameters import CommonParameters
import os

from dataIntegrator.utility.FileUtility import FileUtility
from dataIntegrator.utility.TimeUtility import TimeUtility
import re
import json

def reason_chain_10000_inquiry():
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

            response_dict = run_reason_chain(question)
            response_dict = run_mcp_with_question(response_dict["sorted_question"])

            question = ""  # 重置 question 为空字符串以便重新输入
        else:
            question = question + "\n" + user_input
            print(rf"你已输入：{question}")


def run_reason_chain(question):
    reason_chain_configuration_json = os.path.join(CommonParameters.reason_chain_configuration_path,
                 "RAG_reasoning_chain.json")
    reason_chain_configuration_txt = os.path.join(CommonParameters.reason_chain_configuration_path,
                 "RAG_reasoning_chain.txt")
    params = {
        "agent_type": "spark",
        "rag_model": "RAG_general_inquiry",
        "question": question,
        "knowledge_base_file_path": reason_chain_configuration_json,
        "prompt_file_path": reason_chain_configuration_txt,
    }

    params["question"] = question
    response_dict = RAGFactory.run_rag_inquiry_with_params(params)

    response_dict["response_json"] = re.sub(r'[^\x20-\x7E]', '', response_dict["response_json"])
    print(response_dict["response_json"])

    response_dict = json.loads(response_dict['response_json'])

    return response_dict


def run_mcp_with_question(question):

    ##############################
    # RAG_general_inquiry
    ##############################
    params = {
        "agent_type": "spark",
        "rag_model": "RAG_general_inquiry",
        "question": question,
        "knowledge_base_file_path": rf"D:\workspace_python\infinity\dataIntegrator\LLMSuport\MCPFactory\RunFlaskClientTemplate.py",
        "prompt_file_path": os.path.join(CommonParameters.mcp_configuration_path, "RAG_python_code_gen.txt"),
    }
    response_dict = RAGFactory.run_rag_inquiry_with_params(params)
    print(response_dict)
    content = response_dict["response_json"]
    content = content.replace("python", rf"'''AI generated at: {TimeUtility.get_formatted_time_with_milliseconds()}'''",1)
    program_path = r"D:\workspace_python\infinity\dataIntegrator\LLMSuport\MCPFactory\genearted_code\ai_generated.py"
    FileUtility.write_file(program_path, content)

    response_dict = {"program_path":program_path}
    return response_dict


if __name__ == "__main__":

    ##############################
    # reason_chain_10000_inquiry
    ##############################
    reason_chain_10000_inquiry()
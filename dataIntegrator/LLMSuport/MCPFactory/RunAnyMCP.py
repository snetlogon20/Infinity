from dataIntegrator.LLMSuport.MCPFactory.SubProcessManager import SubProcessManager
from dataIntegrator.LLMSuport.RAGFactory.RAGFactory import RAGFactory
from dataIntegrator.common.CommonParameters import CommonParameters
import os

from dataIntegrator.utility.FileUtility import FileUtility
from dataIntegrator.utility.TimeUtility import TimeUtility


def run_mcp_stock_summary():

    ##############################
    # RAG_general_inquiry
    ##############################
    params = {
        "agent_type": "spark",
        "rag_model": "RAG_general_inquiry",

        "question": """
Now you are going to generate the code for the following steps:
    a) fetch the data of df_tushare_us_stock_daily
        1) the question shall be "show me the trade date, percent, vwap and volume of Citi change between 2022/01/01 to 2024/12/31"
    b) save the data df_tushare_us_stock_daily
    c) open the data of df_tushare_us_stock_daily to excel file in excel
    d) draw the plot
        1) let trade_date be PlotX
        2) let pct_change be PlotY  
        """,

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

def run_mcp_stock_summary_with_mocked_question():

    ##############################
    # RAG_general_inquiry
    ##############################
    mocked_text = '```python\nimport os\n\nfrom dataIntegrator.LLMSuport.MCPFactory.FlaskClientWithAI import FlaskClientWithAI\nfrom dataIntegrator.common.CommonParameters import CommonParameters\n\nif __name__ == \'__main__\':\n\n    # Step 0 - Init the program\n    client = FlaskClientWithAI()\n    response_dict = dict()\n\n    # Step 1 - fetch df_tushare_us_stock_daily\n    param_dict = {\n        "name": "fetch_df_tushare_us_stock_daily",\n        "action": "fetch",\n        "params": {\n            "url": "http://localhost:5000/fetch_data_with_ai",\n            "question": "show me the trade date, percent, vwap and volume of Citi change between 2022/01/01 to 2024/12/31",\n            }\n    }\n\n    response = client.fetchData(param_dict)\n    response_dict["fetch_df_tushare_us_stock_daily"] = response\n    if response.get("return_code") != "000000":\n        exit()\n\n    # Step 2 - save df_tushare_us_stock_daily\n    param_dict = {\n        "name": "save_df_tushare_us_stock_daily",\n        "action": "save",\n        "params": {\n            "path": r"D:\\workspace_python\\infinity\\dataIntegrator\\data\\outbound",\n            "resultset_df": response_dict["fetch_df_tushare_us_stock_daily"]["resultset_df"]\n        }\n    }\n    response = client.saveData(param_dict)\n    response_dict["save_df_tushare_us_stock_daily"] = response\n    if response.get("return_code") != "000000":\n        exit()\n\n    # Step 3 - open save_df_tushare_us_stock_daily excel\n    param_dict = {\n        "name": "open_file",\n        "action": "start",\n        "params": {\n            "action": "start",\n            "command": "excel",\n            "file_path": response_dict["save_df_tushare_us_stock_daily"]["excel_file_path"]\n        }\n    }\n    response = client.open_file(param_dict)\n    response_dict["open_file"] = response\n    if response.get("return_code") != "000000":\n        exit()\n\n    # Step 4 - draw plot\n    param_dict = {\n        "name": "plot_df_tushare_us_stock_daily",\n        "action": "plot",\n        "params": {\n            "resultset_df": response_dict["fetch_df_tushare_us_stock_daily"]["resultset_df"],\n            "PlotX": "trade_date",\n            "PlotY": "pct_change",\n            "plot_file_path": os.path.join(CommonParameters.outBoundPath,"close_point_plot.png")\n        }\n    }\n    response = client.draw_plot(param_dict)\n    response_dict["plot_df_tushare_us_stock_daily"] = response\n    if response.get("return_code") != "000000":\n        exit()\n```'

    params = {
        "agent_type": "mockedai",
        "rag_model": "RAG_general_inquiry",
        "question": mocked_text,
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

def run_mcp_stock_basic():

    ##############################
    # RAG_general_inquiry
    ##############################
    params = {
        "agent_type": "spark",
        "rag_model": "RAG_general_inquiry",

        "question": """
        Now you are going to generate the code for the following steps:
            a) fetch the data of df_tushare_us_stock_basic
                1) the question is "显示股票分类是 EQ 的这些股票的英文名称，股票分类和上市日期，按照上市日期排序，每个股票只显示一次即可。"
            b) save the data df_tushare_us_stock_basic
            c) open the data of df_tushare_us_stock_basic to excel file in excel
                """,

        "knowledge_base_file_path": rf"D:\workspace_python\infinity\dataIntegrator\LLMSuport\MCPFactory\RunFlaskClientTemplate.py",
        "prompt_file_path": os.path.join(CommonParameters.rag_configuration_path, "RAG_python_code_gen.txt"),
    }
    response_dict = RAGFactory.run_rag_inquiry_with_params(params)
    print(response_dict)
    content = response_dict["response_json"]
    content = content.replace("python", rf"'''AI generated at: {TimeUtility.get_formatted_time_with_milliseconds()}'''",1)
    program_path = r"D:\workspace_python\infinity\dataIntegrator\LLMSuport\MCPFactory\generated_code\genearted_code\ai_generated.py"
    FileUtility.write_file(program_path, content)

    response_dict = {"program_path":program_path}
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


def run_mpc_with_prompt_questions():
    global result
    question = ""
    while True:

        # 提示用户输入
        user_input = input("\n是否继续？输入 [:run] 运行，输入 [:exit] 退出: ").strip().lower()

        # 根据输入决定是否退出循环
        if user_input == ":exit":
            print("程序已停止。")
            break
        elif user_input == ":run":
            print(rf"正在运行你的问题：{question}")
            response_dict = run_mcp_with_question(question)
            result = subProcessManger.run_python_script(response_dict["program_path"])
            question = ""
        else:
            question = question + "\n" + user_input
            print(rf"你已输入：{question}")

        '''
        Now you are going to generate the code for the following steps:
            a) fetch the data of df_tushare_us_stock_basic
                1) the question is "显示股票分类是 EQ 的这些股票的英文名称，股票分类和上市日期，按照上市日期排序，每个股票只显示一次即可。"
            b) save the data df_tushare_us_stock_basic
            c) open the data of df_tushare_us_stock_basic to excel file in excel
        '''

        '''
        Now you are going to generate the code for the following steps:
        a) fetch the data of df_tushare_us_stock_daily
            1) the question shall be "show me the trade date, percent, vwap and volume of Citi change between 2022/01/01 to 2024/12/31"
        b) save the data df_tushare_us_stock_daily
        c) open the data of df_tushare_us_stock_daily to excel file in excel
        d) draw the plot
            1) let PlotY be vwap
        e) open the plot file in mspaint 
        '''


if __name__ == "__main__":
    subProcessManger = SubProcessManager()

    response_dict = run_mcp_stock_summary()
    result = subProcessManger.run_python_script(response_dict["program_path"])

    # response_dict =  run_mcp_stock_basic()
    # result = subProcessManger.run_python_script(response_dict["program_path"])

    # run_mpc_with_prompt_questions()

    # response_dict = run_mcp_stock_summary_with_mocked_question()
    # result = subProcessManger.run_python_script(response_dict["program_path"])



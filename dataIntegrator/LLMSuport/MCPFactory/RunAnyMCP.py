from dataIntegrator.LLMSuport.RAGFactory.RAGFactory import RAGFactory
from dataIntegrator.common.CommonParameters import CommonParameters
import os

from dataIntegrator.utility.FileUtility import FileUtility
from dataIntegrator.utility.TimeUtility import TimeUtility

if __name__ == "__main__":

    ##############################
    # RAG_workflow_100000_inquiry
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
        1) let PlotY be vwap
    e) open the plot file in mspaint
        """,

#         "question": """
# Now you are going to generate the code for the following steps:
#     a) fetch the data of df_tushare_us_stock_basic
#         1) the question is "显示股票分类是 EQ 的这些股票的英文名称，股票分类和上市日期，按照上市日期排序，每个股票只显示一次即可。"
#     b) save the data df_tushare_us_stock_basic
#     c) open the data of df_tushare_us_stock_basic to excel file in excel
#         """,

        "knowledge_base_file_path": rf"D:\workspace_python\infinity\dataIntegrator\LLMSuport\MCPFactory\RunFlaskClientTemplate.py",
        "prompt_file_path": os.path.join(CommonParameters.rag_configuration_path, "RAG_python_code_gen.txt"),
    }

    response_dict = RAGFactory.run_rag_inquiry_with_params(params)
    print(response_dict)

    content = response_dict["response_json"]
    content = content.replace("python", rf"'''AI generated at: {TimeUtility.get_formatted_time_with_milliseconds()}'''", 1)

    program_path = r"D:\workspace_python\infinity\dataIntegrator\LLMSuport\MCPFactory\ai_generated.py"
    FileUtility.write_file(program_path, content)

    env = os.environ.copy()
    env["MPLBACKEND"] = "Agg"  # 强制使用非交互式后端

    import subprocess
    result = subprocess.run(
        ["python", program_path],
        capture_output=True,
        text=True,
        env=env  # 传递修改后的环境变量
    )

    print("程序 B 的输出：", result.stdout)
    print("程序 B 的错误（如果有）：", result.stderr)
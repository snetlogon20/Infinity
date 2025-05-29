from dataIntegrator.LLMSuport.RAGFactory.RAGFactory import RAGFactory
from dataIntegrator.common.CommonParameters import CommonParameters
import os

from dataIntegrator.modelService.MonteCarlo.MonteCarlo import MonteCarlo
from dataIntegrator.modelService.statistics.GeneralLinearRegression import GeneralLinearRegression
from dataIntegrator.plotService.PlotManager import PlotManager
from dataIntegrator.utility.FileUtility import FileUtility
from dataIntegrator.utility.TimeUtility import TimeUtility


def RAG_SQL_inquiry_stock_summary():
    # knowledge_base_file_path = rf"D:\workspace_python\dataIntegrator\dataIntegrator\LLMSuport\RAGFactory\configurations\RAG_SQL_inquiry_stock_summary_knowledge_base.json"
    # prompt_file_path = rf"D:\workspace_python\dataIntegrator\dataIntegrator\LLMSuport\RAGFactory\configurations\RAG_SQL_inquiry_stock_summary_prompts.txt"

    knowledge_base_file_path = os.path.join(CommonParameters.rag_configuration_path,"RAG_SQL_inquiry_stock_summary_knowledge_base.json")
    prompt_file_path = os.path.join(CommonParameters.rag_configuration_path,"RAG_SQL_inquiry_stock_summary_prompts.txt")

    # question = "花旗银行 2024年12月26日的收盘价"
    #question = "show me all the stock information of Citi change between 2022/12/22 to 2024/12/31"
    #question = "show me the trade date, percent change and volume of Citi change between 2022/12/25 to 2024/12/31"
    #question = "show me the china CPI data as of 2022 Aug."
    #question = "show me the 期货基本信息 ，期货名称中包含豆的产品."
    #question = "show me the 美国国债收益率曲线 2022年01月10日当日."
    #question = "帮我在df_tushare_us_stock_daily找出花旗2024-12-01到2024-12-27的成交额，然后再比较同期df_tushare_stock_daily 中国脉科技的成交额"
    #question = "帮我在美国股票信息中找出花旗2024-12-02的成交额，然后再比较同期中国股票中 “国脉科技”的成交额"
    #question = "帮我在美国股票信息中找出花旗2024-12-02的pct_change，然后再比较 同期上海银行间同业拆放利率中的所有信息， 和同期上海黄金交易所日行情中的所有信息"
    #question = "帮我在美国股票信息中找出花旗2024-12-02到2024-12-31的pct_change，然后再比较 同期上海银行间同业拆放利率中的所有信息，比较同期中国股票中 “国脉科技”的成交额 和同期上海黄金交易所日行情中的所有信息"
    #question = "帮我在美国股票信息中找出花旗2024-12-02到2024-12-31的pct_change，然后再比较 同期上海银行间同业拆放利率中的所有信息，比较同期中国股票中 “国脉科技”的成交额 和同期上海黄金交易所日行情中的所有信息。 作图"
    #question = "帮我在美国股票信息中找出花旗2024-12-02到2024-12-31的pct_change，然后再比较 同期上海银行间同业拆放利率中的所有信息，比较同期中国股票中 “国脉科技”的收益率 和同期上海黄金交易所日行情中的所有信息。 作图时把美股的当日收益率, 国脉科技的收益率、黄金收益率和同业拆放利率的各类利率当作Y 轴"
    #question = "帮我在美国股票信息中找出花旗2024-12-02到2024-12-31的交易量，交易金额，然后再比较同期中国股票中 “国脉科技”的交易量*500倍，交易金额*500倍。 作图"
    #question = "帮我在美国股票信息中找出花旗2024-12-02到2024-12-31的交易量，交易金额，然后再比较同期中国股票中 “国脉科技”的交易量*500倍，交易金额*500倍。 用散点图"
    #question = "帮我在美国股票信息中找出花旗2024-5-02到2025-5-5的月收益率，然后再比较同期苹果、摩根大通的平均收益率， 然后再比较 同期上海银行间同业拆放利率中的隔夜利息， 和同期上海黄金交易所日行情中的合约代码为Au99.99的收益率。用折线图"
    #question = "帮我在美国股票信息中找出花旗2024-10-02到2024-10-31的交易量，交易金额，然后再比较同期摩根大通的交易量，交易金额。 用折线图"
    #question = "帮我在美国股票信息中找出花旗2024-12-02到2024-12-31的pct_change，然后再比较 同期上海银行间同业拆放利率中的overnight的收益率，比较同期中国股票中 “国脉科技”的收益率。不作图，但是 需要线性回归分析：花旗pct_change是ycolumn, 其余是xColumns"
    #question = "帮我在美国股票信息中找出花旗2024-06-02到2024-12-31的pct_change、收盘价，然后再比较 同期上海银行间同业拆放利率中的overnight的收益率，比较同期中国股票中 “国脉科技”的收益率、价格, 再比较 美国国债收益率曲线 中的 1月期、3月期、 3年期收益率和10年期收益率, 再比较外汇市场日行情行情中人民币对美元的买入收盘价。去除为0的数据。作图，然后需要线性回归分析：花旗pct_change是ycolumn, 其余是xColumns"
    #question = "帮我在美国股票信息中找出花旗2024-06-02到2024-12-31的pct_change、收盘价，然后再比较 同期上海银行间同业拆放利率中的overnight的收益率，比较同期中国股票中 “国脉科技”的收益率、价格, 再比较 美国国债收益率曲线 中的 1月期、3月期、 3年期收益率和10年期收益率, 再比较外汇市场日行情行情中人民币对美元的买入收盘价。去除为0的数据 , 按照交易日期排序。作图，然后需要线性回归分析：花旗pct_change是ycolumn, 其余是xColumns"
    question = "Find all the fields for AAPL in the us stock market between December2024.31.2024 and December 31, 2024. I need this to do a Monte carlo analysis. stock code: AAPL, date taken from October 1, 2022, to November 19, 2024.The initial field is close point, and the analysis field is pct change."

    response_dict = RAGFactory.run_rag_inquiry("RAG_SQL_inquiry_stock_summary", CommonParameters.Default_AI_Engine, question, knowledge_base_file_path, prompt_file_path)
    print(response_dict)

    param_dict = response_dict
    plotManager = PlotManager()
    plotManager.draw_plot(param_dict)

    param_dict = response_dict
    generalLinearRegression = GeneralLinearRegression()
    generalLinearRegression.run_linear_regression_by_AI(param_dict)

    if response_dict["isMonteCarloRequired"]=="yes" :
        dataFrame =response_dict["results"]
        simulat_params =response_dict["MonteCarloRequirement"]
        monteCarlo = MonteCarlo()
        all_line_df = monteCarlo.simulation_multi_series(dataFrame, simulat_params)

def RAG_SQL_inquiry_stocks_code():
    knowledge_base_file_path = os.path.join(CommonParameters.basePath, "LLMSuport", "RAGFactory", "configurations",
                                            "RAG_SQL_inquiry_stocks_code_knowledge_base.json")
    prompt_file_path = os.path.join(CommonParameters.basePath, "LLMSuport", "RAGFactory", "configurations",
                                    "RAG_SQL_inquiry_stocks_code_prompts.txt")
    question = """帮我找出花旗， 美国银行，JP 摩根， 苹果，英伟达， 因特尔的股票代码。股票数据需要2023-01-01到2023-12-31之间的数据。不需要冗余数据，返回单一股票代码即可。"""
    response_dict = RAGFactory.run_rag_inquiry(
        "RAG_SQL_inquiry_stocks_code", "spark",
        question, knowledge_base_file_path, prompt_file_path)
    print(response_dict)


def RAG_general_inquiry():
    params = {
        "agent_type": "spark",
        "rag_model": "RAG_general_inquiry",
        "question": "what's the capital of France",
        "knowledge_base_file_path": os.path.join(CommonParameters.rag_configuration_path, "RAG_general_inquiry.json"),
        "prompt_file_path": os.path.join(CommonParameters.rag_configuration_path, "RAG_general_inquiry.txt"),
    }
    response_dict = RAGFactory.run_rag_inquiry_with_params(params)
    print(response_dict)


def RAG_workflow_100000_inquiry():
    params = {
        "agent_type": "spark",
        "rag_model": "RAG_general_inquiry",
        "question": "下载, 保存、然后分析数据",
        "knowledge_base_file_path": os.path.join(CommonParameters.rag_configuration_path,
                                                 "RAG_workflow_100000_inquiry.json"),
        "prompt_file_path": os.path.join(CommonParameters.rag_configuration_path, "RAG_workflow_100000_inquiry.txt"),
    }
    response_dict = RAGFactory.run_rag_inquiry_with_params(params)
    print(response_dict)


def RAG_workflow_100001_inquiry():
    global result
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

        "knowledge_base_file_path": rf"D:\workspace_python\infinity\dataIntegrator\test\FlaskServer\RunFlaskClientTemplate.py",
        "prompt_file_path": os.path.join(CommonParameters.mcp_configuration_path, "RAG_python_code_gen.txt"),
    }
    response_dict = RAGFactory.run_rag_inquiry_with_params(params)
    print(response_dict)
    content = response_dict["response_json"]
    content = content.replace("python", rf"'''AI generated at: {TimeUtility.get_formatted_time_with_milliseconds()}'''",
                              1)
    program_path = r"D:\workspace_python\infinity\dataIntegrator\test\FlaskServer\ai_generated.py"
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

def reason_chain_10000_inquiry():
    params = {
        "agent_type": "spark",
        "rag_model": "RAG_general_inquiry",
        "question": """

        """,
        "knowledge_base_file_path": os.path.join(CommonParameters.rag_configuration_path,"RAG_reasoning_chain.json"),
        "prompt_file_path": os.path.join(CommonParameters.rag_configuration_path, "RAG_reasoning_chain.txt"),
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

def rag_uml_txt2uml_inquiry():
    question = "请按照要求生成 Database UML和建表语句,并按照JSON格式返回"

    #knowledge_base_file_path = os.path.join(CommonParameters.rag_configuration_path,"RAG_UML_txt2uml.json")
    knowledge_base_file_path = rf"D:\workspace_python\infinity\dataIntegrator\test\RegulatoryRAG2UML\Letter of Credit Requirement_RAG.txt"
    prompt_file_path = os.path.join(CommonParameters.rag_configuration_path,"RAG_UML_txt2uml_prompts.txt")

    response_dict = RAGFactory.run_rag_inquiry("RAG_UML_txt2uml", CommonParameters.Default_AI_Engine, question, knowledge_base_file_path, prompt_file_path)
    print(response_dict)

if __name__ == "__main__":

    ##############################
    # RAG_SQL_inquiry_stock_summary
    ##############################
    # RAG_SQL_inquiry_stock_summary()
    #
    # ##############################
    # # RAG_SQL_inquiry_stocks_code
    # ##############################
    # RAG_SQL_inquiry_stocks_code()
    #
    # #############################
    # # RAG_general_inquiry
    # #############################
    # RAG_general_inquiry()
    #
    # ##############################
    # # RAG_workflow_100000_inquiry
    # ##############################
    # RAG_workflow_100000_inquiry()
    #
    # ##############################
    # # RAG_workflow_100001_inquiry
    # ##############################
    # RAG_workflow_100001_inquiry()

    ##############################
    # reason_chain_10000_inquiry
    ##############################
    # reason_chain_10000_inquiry()

    ##############################
    # rag_uml_txt2uml_inquiry
    ##############################
    rag_uml_txt2uml_inquiry()
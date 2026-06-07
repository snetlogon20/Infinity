import os
import datetime
from dataIntegrator.common.MyTokens import MyTokens

class CommonParameters():

    application_name = "infinity_grid"
    default_time_zone = 'Asia/Shanghai'
    today = datetime.date.today().strftime('%Y%m%d')


    basePath = r"D:\workspace_python\infinity\dataIntegrator"
    rag_configuration_path = os.path.join(basePath, 'LLMSuport', 'RAGFactory', 'configurations')
    mcp_configuration_path = os.path.join(basePath, 'LLMSuport', 'MCPFactory', 'configurations')
    reason_chain_configuration_path = os.path.join(basePath, 'LLMSuport', 'ReasonChainFactory', 'configurations')


    dataPath = r"D:\workspace_python\infinity_data"
    outBoundPath = os.path.join(dataPath,'outbound')
    logPath = os.path.join(dataPath,'log')
    logFilePath = os.path.join(dataPath,'log','dataIntegrater.log')
    reportPath = os.path.join(outBoundPath, 'report')
    portfolioAnalysisReportPath = os.path.join(reportPath, 'PortfolioAnalysis')


    tuShareToken = MyTokens.tuShareToken

    clickhouseHostName='192.168.98.184'
    clickhouseHostDatabase='indexsysdb'

    oracle_config = {
        'host': '192.168.98.129',
        'port': 1521,
        'sid': 'orcl',
        'username': 'citi',
        'password': 'citi@citi',
        'oracle_client': r'C:\app\ASUS\product\11.2.0\client_2'
    }

    Default_AI_Engine = 'spark'

    CALENDAR_PRIMARY_KEY_FILED = 'trade_date'

    # Configuration - 1
    # SPARKAI_URL_REQUEST_TIMEOUT = 120
    # SPARKAI_URL = 'wss://spark-api.xf-yun.com/v3.5/chat'
    # SPARKAI_DOMAIN = 'generalv3.5'
    # SPARK_APPID = "5f5c4f75"
    # SPARK_API_KEY = "7a3136e4cac2160adb122031351fe0a4"
    # SPARK_API_SECRET = "0672724ff7d71dc8fbbdcf98614aedb1"

    # # Configuration - 2
    SPARKAI_URL_REQUEST_TIMEOUT = 120
    #SPARKAI_URL = 'wss://spark-api.xf-yun.com/v3.5/chat'
    #SPARKAI_URL = 'wss://spark-api.xf-yun.com/chat/max-32k'  #超长文本时使用
    SPARKAI_URL = "wss://spark-api.xf-yun.com/v4.0/chat"
    SPARKAI_DOMAIN = 'spark-x'  # 仅支持 spark-x/x1/asean
    SPARK_APPID = "c4c24a9d"
    SPARK_API_SECRET = "YmI5MGEwOWQ5NzMyMWMzYTk0YjE4MDA2"
    SPARK_API_KEY = "7ee29f75c407872e608b2cc7e19115fb"


    # Alibaba Cloud Bailian (DashScope / Tongyi Qianwen)
    BAILIAN_API_KEY = "sk-49cf76b94af74825b15eafd0b5acabcb"
    BAILIAN_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    BAILIAN_MODEL = "qwen-plus"  # qwen-turbo / qwen-plus / qwen-max / qwen-max-longcontext

    #Keep the parameter when you are running PlotManager standalone (not within StreamLit)
    IS_STREAMLIT_ON = False
    # IS_STREAMLIT_ON = True

    # IF_ENABLE_MOCKED_AI = True   # use stored mocked AI answer
    IF_ENABLE_MOCKED_AI = False  # use real AI answer

    STOCK_LIST=[
            {'ts_code': '002093.SZ', 'name': '国脉科技'},
            {'ts_code': '600490.SH', 'name': '鹏欣资源'},
            {'ts_code': '000902.SZ', 'name': '新洋丰'},
            {'ts_code': '601368.SH', 'name': '绿城水务'},
            {'ts_code': '603839.SH', 'name': '安正时尚'},
            {'ts_code': '000546.SZ', 'name': '金圆股份'},
            {'ts_code': '600470.SH', 'name': '六国化工'},
            {'ts_code': '600519.SH', 'name': '贵州茅台'},
            {'ts_code': '688498.SH', 'name': '源杰科技'},
        ]

    #US_STOCK_LIST=["SPY", "C", "JPM", "AAPL","NVDA","GS","MS","GE"]
    #US_STOCK_LIST=["C", "JPM", "AAPL", "NVDA", "MSFT"]
    US_STOCK_LIST = [
        "SPY", "C", "JPM", "AAPL", "NVDA", "GS", "MS", "GE",  # 你原有的代码
        "MSFT", "AVGO", "ADBE", "UNH", "JNJ", "LLY", "PFE", "MRK", "AMZN",
        "TSLA", "MCD", "NFLX", "HD", "GOOGL", "META", "DIS", "CMCSA", "T",
        "CAT", "UPS", "BA", "HON", "PG", "KO", "PEP", "WMT", "COST", "XOM",
        "CVX", "COP", "SLB", "EOG", "AMT", "PLD", "EQIX", "SPG", "O", "NEE",
        "DUK", "SO", "D", "EXC", "LIN", "APD", "FCX", "NEM", "SHW"
    ]

    def __init__(self, LogLib):
        print("CommonParameters init begin ")

        print("CommonParameters init end ")




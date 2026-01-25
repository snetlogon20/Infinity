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

    tuShareToken = MyTokens.tuShareToken

    clickhouseHostName='192.168.98.174'
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
    SPARKAI_URL = 'wss://spark-api.xf-yun.com/chat/max-32k'  #超长文本时使用
    SPARKAI_DOMAIN = 'generalv3.5'
    SPARK_APPID = "c4c24a9d"
    SPARK_API_KEY = "7ee29f75c407872e608b2cc7e19115fb"
    SPARK_API_SECRET = "YmI5MGEwOWQ5NzMyMWMzYTk0YjE4MDA2"


    #Keep the parameter when you are running PlotManager standalone (not within StreamLit)
    IS_STREAMLIT_ON = False
    # IS_STREAMLIT_ON = True

    IF_ENABLE_MOCKED_AI = True   # use stored mocked AI answer
    # IF_ENABLE_MOCKED_AI = False  # use real AI answer

    def __init__(self, LogLib):
        print("CommonParameters init begin ")

        print("CommonParameters init end ")




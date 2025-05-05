import os

class CommonParameters():

    application_name = "infinity_grid"
    default_time_zone = 'Asia/Shanghai'

    basePath = r"D:\workspace_python\infinity\dataIntegrator"
    rag_configuration_path = os.path.join(basePath, 'LLMSuport', 'RAGFactory', 'configurations')
    mcp_configuration_path = os.path.join(basePath, 'LLMSuport', 'MCPFactory', 'configurations')
    reason_chain_configuration_path = os.path.join(basePath, 'LLMSuport', 'ReasonChainFactory', 'configurations')


    dataPath = r"D:\workspace_python\infinity_data"
    outBoundPath = os.path.join(dataPath,'outbound')
    logPath = os.path.join(dataPath,'log')
    logFilePath = os.path.join(dataPath,'log','dataIntegrater.log')

    #tuShareToken = "00fcaf64c13f1a8e58011bb7b07d2016f9c632e7711162c0b95c2003"  #Samuel
    tuShareToken = "2876ea85cb005fb5fa17c809a98174f2d5aae8b1f830110a5ead6211"  # 咸鱼

    clickhouseHostName='192.168.98.152'
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

    SPARKAI_URL = 'wss://spark-api.xf-yun.com/v3.5/chat'
    SPARKAI_DOMAIN = 'generalv3.5'
    SPARK_APPID = "5f5c4f75"
    SPARK_API_KEY = "7a3136e4cac2160adb122031351fe0a4"
    SPARK_API_SECRET = "0672724ff7d71dc8fbbdcf98614aedb1"

    MOCKED_AI_ANSWER = ""

    #Keep the parameter when you are running PlotManager standalone (not within StreamLit)
    IS_STREAMLIT_ON = False

    def __init__(self, LogLib):
        print("CommonParameters init begin ")

        print("CommonParameters init end ")




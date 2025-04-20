import os

class CommonParameters():

    default_time_zone = 'Asia/Shanghai'

    basePath = r"D:\workspace_python\infinity\dataIntegrator"
    rag_configuration_path = os.path.join(basePath, 'LLMSuport', 'RAGFactory', 'configurations')


    dataPath = r"D:\workspace_python\infinity_data"
    outBoundPath = os.path.join(dataPath,'outbound')
    logFilePath = os.path.join(dataPath,'log','dataIntegrater.log')

    tuShareToken = "00fcaf64c13f1a8e58011bb7b07d2016f9c632e7711162c0b95c2003"  #Samuel

    clickhouseHostName='192.168.98.149'
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

    def __init__(self, LogLib):
        print("CommonParameters init begin ")

        print("CommonParameters init end ")




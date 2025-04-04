import os

class CommonParameters():

    basePath = r"D:\workspace_python\infinity\dataIntegrator"

    dataPath = r"D:\workspace_python\infinity_data"
    logFilePath = os.path.join(dataPath,'log','dataIntegrater.log')

    tuShareToken = "00fcaf64c13f1a8e58011bb7b07d2016f9c632e7711162c0b95c2003"  #Samuel
    clickhouseHostName='192.168.98.148'
    clickhouseHostDatabase='indexsysdb'

    SPARKAI_URL = 'wss://spark-api.xf-yun.com/v3.5/chat'
    SPARKAI_DOMAIN = 'generalv3.5'
    SPARK_APPID = "5f5c4f75"
    SPARK_API_KEY = "7a3136e4cac2160adb122031351fe0a4"
    SPARK_API_SECRET = "0672724ff7d71dc8fbbdcf98614aedb1"

    def __init__(self, LogLib):
        print("CommonParameters init begin ")

        print("CommonParameters init end ")




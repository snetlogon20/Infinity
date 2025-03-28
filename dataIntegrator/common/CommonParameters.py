import traceback
from dataIntegrator.common import CommonLogLib

class CommonParameters():

    logFilePath="D:\\workspace_python\\dataIntegrator\\dataIntegrator\\data\\log\\dataIntegrater.log"
    tuShareToken = "00fcaf64c13f1a8e58011bb7b07d2016f9c632e7711162c0b95c2003"  #Samuel
    #tuShareToken = "20241124210121-584f5f8b-ebd1-4508-aeb3-434ef64cf790" #From Xianyu
    clickhouseHostName='192.168.98.147'
    clickhouseHostDatabase='indexsysdb'

    SPARKAI_URL = 'wss://spark-api.xf-yun.com/v3.5/chat'
    SPARKAI_DOMAIN = 'generalv3.5'
    SPARK_APPID = "5f5c4f75"
    SPARK_API_KEY = "7a3136e4cac2160adb122031351fe0a4"
    SPARK_API_SECRET = "0672724ff7d71dc8fbbdcf98614aedb1"

    def __init__(self, LogLib):
        print("CommonParameters init begin ")

        print("CommonParameters init end ")




from dataIntegrator.common.CommonLib import CommonLib
from dataIntegrator.LLMSuport.PrefectFactory.MCP100000.ServiceAnalyze import ServiceAnalyze
from dataIntegrator.LLMSuport.PrefectFactory.MCP100000.ServiceDownload import ServiceDownload
from dataIntegrator.LLMSuport.PrefectFactory.MCP100000.ServiceSavedata import ServiceSavedata

MCP_MAP = {
    "MCP100000": "保存、下载，分析数据",
    "MCP100001": "",
    "MCP100002": "",
}

ACTION_MAP = {
    "download": ServiceDownload.download,
    "analyze": ServiceAnalyze.analyze,
    "save_data": ServiceSavedata.save_data,
}

class PrefectActionMapper(CommonLib):
    def __init__(self):
        pass
    @classmethod
    def getActionMap(self) -> dict:
        return ACTION_MAP
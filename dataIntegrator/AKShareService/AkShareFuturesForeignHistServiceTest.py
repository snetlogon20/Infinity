from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.AKShareService.AkShareFuturesForeignHistService import AkShareFuturesForeignHistService
from dataIntegrator.common.FileType import FileType
import os
import sys
import time

logger = CommonLib.logger

class AkShareFuturesForeignHistServiceTest:

    def callAkShareFuturesForeignHistService(self, symbol, file_suffix):
        """
        统一的期货外盘历史数据测试方法

        Args:
            symbol (str): 期货品种代码，如 'XAU'(黄金), 'XAG'(白银), 'GC'(COMEX黄金)等
            file_suffix (str): 文件名后缀，用于区分不同品种
        """
        logger.info(f"callAkShareFuturesForeignHistService started... Symbol: {symbol}")

        file_path = os.path.join(CommonParameters.outBoundPath, f'akshare_futures_foreign_hist_{file_suffix}.xlsx')

        try:
            akShareService = AkShareFuturesForeignHistService()

            # 获取原始数据
            dataFrame = akShareService.prepareDataFrame(symbol)
            akShareService.saveDateFrameToDisk(dataFrame, file_path, FileType.EXCEL)
            dataFrame = akShareService.readDataFrameFromDisk(file_path, FileType.EXCEL)
            akShareService.deleteDateFromClickHouse(symbol)
            transformed_dataFrame = akShareService.transformDataFrame(dataFrame)
            akShareService.saveDateToClickHouse(transformed_dataFrame)

        except Exception as e:
            logger.info('Exception: %s', e)
            raise e

        logger.info(f"callAkShareFuturesForeignHistService ended... Symbol: {symbol}")

if __name__ == '__main__':
    akShareFuturesForeignHistServiceTest = AkShareFuturesForeignHistServiceTest()

    # ==================== 贵金属 ====================
    akShareFuturesForeignHistServiceTest.callAkShareFuturesForeignHistService(symbol='XAG', file_suffix='XAG')  # 伦敦银
    akShareFuturesForeignHistServiceTest.callAkShareFuturesForeignHistService(symbol='GC', file_suffix='GC')  # COMEX黄金
    akShareFuturesForeignHistServiceTest.callAkShareFuturesForeignHistService(symbol='XAU', file_suffix='XAU')  # 伦敦金
    akShareFuturesForeignHistServiceTest.callAkShareFuturesForeignHistService(symbol='SI', file_suffix='SI')  # COMEX白银
    akShareFuturesForeignHistServiceTest.callAkShareFuturesForeignHistService(symbol='HG', file_suffix='HG')  # COMEX铜

    # ==================== 能源 ====================
    akShareFuturesForeignHistServiceTest.callAkShareFuturesForeignHistService(symbol='CL', file_suffix='CL')  # NYMEX原油 (WTI)
    akShareFuturesForeignHistServiceTest.callAkShareFuturesForeignHistService(symbol='OIL', file_suffix='OIL')  # 布伦特原油
    akShareFuturesForeignHistServiceTest.callAkShareFuturesForeignHistService(symbol='NG', file_suffix='NG')  # NYMEX天然气

    # ==================== 农产品 ====================
    akShareFuturesForeignHistServiceTest.callAkShareFuturesForeignHistService(symbol='S', file_suffix='S')  # CBOT大豆
    akShareFuturesForeignHistServiceTest.callAkShareFuturesForeignHistService(symbol='W', file_suffix='W')  # CBOT小麦
    akShareFuturesForeignHistServiceTest.callAkShareFuturesForeignHistService(symbol='C', file_suffix='C')  # CBOT玉米
    akShareFuturesForeignHistServiceTest.callAkShareFuturesForeignHistService(symbol='FCPO', file_suffix='FCPO')  # 马棕油

    # ==================== LME金属（3个月）====================
    akShareFuturesForeignHistServiceTest.callAkShareFuturesForeignHistService(symbol='CAD', file_suffix='CAD')  # LME铜3个月
    akShareFuturesForeignHistServiceTest.callAkShareFuturesForeignHistService(symbol='AHD', file_suffix='AHD')  # LME铝3个月
    akShareFuturesForeignHistServiceTest.callAkShareFuturesForeignHistService(symbol='ZSD', file_suffix='ZSD')  # LME锌3个月
    akShareFuturesForeignHistServiceTest.callAkShareFuturesForeignHistService(symbol='NID', file_suffix='NID')  # LME镍3个月


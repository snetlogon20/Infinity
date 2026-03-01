from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.AKShareService.AkShareFuturesForeignHistService import AkShareFuturesForeignHistService
from dataIntegrator.common.FileType import FileType
import os
import sys

logger = CommonLib.logger

class AkShareFuturesForeignHistServiceTest:

    def callAkShareFuturesForeignHistService(self, symbol='XAU', file_suffix='xau'):
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

    akShareFuturesForeignHistServiceTest.callAkShareFuturesForeignHistService('GC', 'GC')
    akShareFuturesForeignHistServiceTest.callAkShareFuturesForeignHistService('XAU', 'XAU')
    akShareFuturesForeignHistServiceTest.callAkShareFuturesForeignHistService('XAG', 'XAG')


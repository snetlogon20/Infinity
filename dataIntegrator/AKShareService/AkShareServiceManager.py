import os

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.AKShareService.AkShareSpotHistSGEService import AkShareSpotHistSGEService
from dataIntegrator.AKShareService.AkShareFuturesForeignHistService import AkShareFuturesForeignHistService
from dataIntegrator.common.FileType import FileType

logger = CommonLib.logger

class AkShareServiceManager():

    def __init__(self):
        logger.info("__init__ started")

    @classmethod
    def callAkShareSpotHistSGEService(self, start_date = '20240101', end_date = CommonParameters.today):
        logger.info("callAkShareSpotHistSGEServicee started...")

        file_path = os.path.join(CommonParameters.outBoundPath,'sakshare_spot_hist_sge_dg.xlsx')

        try:
            akShareService = AkShareSpotHistSGEService()

            dataFrame = akShareService.prepareDataFrame(start_date, end_date)

            akShareService.saveDateFrameToDisk(dataFrame,file_path,FileType.EXCEL)
            dataFrame = akShareService.readDataFrameFromDisk(file_path,FileType.EXCEL)

            akShareService.deleteDateFromClickHouse(start_date, end_date)

            dataFrame = akShareService.transformDataFrame(dataFrame)
            akShareService.saveDateToClickHouse(dataFrame)

        except Exception as e:
            logger.info('Exception: %s', e)
            raise e

        logger.info("callTushareSGEDailyService ended...")

    @classmethod
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

    @classmethod
    def callAkShareService(self, start_date = "20260101", end_date = CommonParameters.today):
        try:
            logger.info("callAkShareService started")

            start_date = "20240101"
            end_date = CommonParameters.today

            self.callAkShareSpotHistSGEService(start_date, end_date)
            self.callAkShareFuturesForeignHistService('GC', 'GC')
            self.callAkShareFuturesForeignHistService('XAU', 'XAU')
            self.callAkShareFuturesForeignHistService('XAG', 'XAG')

        except Exception as e:
            logger.error('==============================================')
            logger.error('Exception: %s', e)
            logger.error('==============================================')
            raise e

def main():
    akShareServiceManager = AkShareServiceManager()
    akShareServiceManager.callAkShareService(start_date = "20260101", end_date = CommonParameters.today)

if __name__ == '__main__':
    main()

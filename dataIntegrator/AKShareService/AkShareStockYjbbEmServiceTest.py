from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.AKShareService.AkShareStockYjbbEmService import AkShareStockYjbbEmService
from dataIntegrator.common.FileType import FileType
import os

logger = CommonLib.logger

"""
年报季报
业绩报表
接口: stock_yjbb_em
目标地址: http://data.eastmoney.com/bbsj/202003/yjbb.html
"""
class AkShareStockYjbbEmServiceTest:

    def test1_callAkShareStockYjbbEmService(cls):
        logger.info("callAkShareStockYjbbEmService started...")

        date = '20231231'
        file_path = os.path.join(CommonParameters.outBoundPath, 'akshare_stock_yjbb_em.xlsx')

        try:
            akShareService = AkShareStockYjbbEmService()

            dataFrame = akShareService.prepareDataFrame(date)

            akShareService.saveDateFrameToDisk(dataFrame, file_path, FileType.EXCEL)
            dataFrame = akShareService.readDataFrameFromDisk(file_path, FileType.EXCEL)

            akShareService.deleteDateFromClickHouse(date)

            dataFrame = akShareService.transformDataFrame(dataFrame)
            akShareService.saveDateToClickHouse(dataFrame)

        except Exception as e:
            logger.info('Exception: %s', e)
            raise e

        logger.info("callAkShareStockYjbbEmService ended...")

if __name__ == '__main__':
    akShareStockYjbbEmServiceTest = AkShareStockYjbbEmServiceTest()
    akShareStockYjbbEmServiceTest.test1_callAkShareStockYjbbEmService()

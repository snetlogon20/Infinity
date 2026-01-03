from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.AKShareService.AkShareFDIService import AkShareFDIService
import os
from dataIntegrator.common.FileType import FileType

logger = CommonLib.logger

class AkShareFDIServiceTest:

    def test1_callAkShareFDIServiceTest(self):  # 修正方法签名，移除cls参数
        logger.info("callAkShareFDIService started...")

        start_date = '202401'  # 使用年月格式
        end_date = CommonParameters.today[:6]  # 使用年月格式
        file_path = os.path.join(CommonParameters.outBoundPath,'akshare_fdi.xlsx')

        try:
            akShareService = AkShareFDIService()

            dataFrame = akShareService.prepareDataFrame(start_date, end_date)

            akShareService.saveDateFrameToDisk(dataFrame,file_path,FileType.EXCEL)
            dataFrame = akShareService.readDataFrameFromDisk(file_path,FileType.EXCEL)

            akShareService.deleteDateFromClickHouse(start_date, end_date)

            dataFrame = akShareService.transformDataFrame(dataFrame)
            akShareService.saveDateToClickHouse(dataFrame)

        except Exception as e:
            logger.info('Exception: %s', e)
            raise e

        logger.info("callAkShareFDIService ended...")

if __name__ == '__main__':
    akShareFDIServiceTest = AkShareFDIServiceTest()
    akShareFDIServiceTest.test1_callAkShareFDIServiceTest()

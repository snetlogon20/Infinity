from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.AKShareService.NYFedSofrDailyService import NYFedSofrDailyService
from dataIntegrator.common.FileType import FileType
import os

logger = CommonLib.logger

"""
SOFR（担保隔夜融资利率）
接口: GET https://markets.newyorkfed.org/api/rates/secured/sofr/last/{days}.json
目标地址: https://www.newyorkfed.org/markets/reference-rates/sofr
"""
class NYFedSofrDailyServiceTest:

    def test1_callNYFedSofrDailyService(cls, days=30):
        logger.info("callNYFedSofrDailyService started...")

        file_path = os.path.join(CommonParameters.outBoundPath, 'nyfed_sofr_daily.xlsx')

        try:
            nyFedService = NYFedSofrDailyService()

            dataFrame = nyFedService.prepareDataFrame(days)

            nyFedService.saveDateFrameToDisk(dataFrame, file_path, FileType.EXCEL)
            dataFrame = nyFedService.readDataFrameFromDisk(file_path, FileType.EXCEL)

            nyFedService.deleteDateFromClickHouse()

            dataFrame = nyFedService.transformDataFrame(dataFrame)
            nyFedService.saveDateToClickHouse(dataFrame)

        except Exception as e:
            logger.info('Exception: %s', e)
            raise e

        logger.info("callNYFedSofrDailyService ended...")

if __name__ == '__main__':
    nyFedSofrDailyServiceTest = NYFedSofrDailyServiceTest()
    nyFedSofrDailyServiceTest.test1_callNYFedSofrDailyService()

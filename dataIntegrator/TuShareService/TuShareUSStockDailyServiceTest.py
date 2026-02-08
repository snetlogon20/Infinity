from dataIntegrator.TuShareService.TuShareService import TuShareService
import os
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.TuShareService.TuShareUSStockDailyService import TuShareUSStockDailyService

logger = CommonLib.logger

class TuShareUSStockDailyServiceTest(TuShareService):
    @classmethod
    def refresh_citi(self):
        try:

            ts_code = 'C'
            start_date = '20250101'
            end_date = '20251231'

            csvFilePath = os.path.join(CommonParameters.outBoundPath, "df_tushare_df_tushare_USStockBasic_20220507.csv")

            tuShareService = TuShareUSStockDailyService()
            dataFrame = tuShareService.prepareDataFrame(ts_code, start_date, end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date, end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            logger.info('Exception', e)
            raise e


if __name__ == '__main__':
    tuShareUSStockDailyServiceTest = TuShareUSStockDailyServiceTest()
    tuShareUSStockDailyServiceTest.refresh_citi()
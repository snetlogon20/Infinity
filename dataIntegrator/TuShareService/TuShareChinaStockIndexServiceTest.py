from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib
import os
from dataIntegrator import CommonParameters
from dataIntegrator.TuShareService.TuShareChinaStockIndexService import TuShareChinaStockIndexService

logger = CommonLib.logger

class TuShareChinaStockIndexServiceTest(TuShareService):
    @classmethod
    def refresh_shanghai_index(self):
        try:
            ts_code = '000001.SH'  # 上证指数
            start_date = '20240101'
            end_date = '20261231'

            csvFilePath = os.path.join(CommonParameters.outBoundPath, "df_tushare_china_stock_index_2025.csv")

            tuShareService = TuShareChinaStockIndexService()
            dataFrame = tuShareService.prepareDataFrame(ts_code, start_date, end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(ts_code, start_date, end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            logger.info('Exception', e)
            raise e

    @classmethod
    def refresh_guomaikeji_index(self):
        try:
            ts_code = '002093.SZ'  # 上证指数
            start_date = '20250101'
            end_date = '20261231'

            csvFilePath = os.path.join(CommonParameters.outBoundPath, "df_tushare_china_stock_index_2025.csv")

            tuShareService = TuShareChinaStockIndexService()
            dataFrame = tuShareService.prepareDataFrame(ts_code, start_date, end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(ts_code, start_date, end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            logger.info('Exception', e)
            raise e

if __name__ == '__main__':
    tuShareChinaStockIndexServiceTest = TuShareChinaStockIndexServiceTest()
    tuShareChinaStockIndexServiceTest.refresh_shanghai_index()
    #tuShareChinaStockIndexServiceTest.refresh_guomaikeji_index()

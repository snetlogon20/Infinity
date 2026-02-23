from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib
import os
from dataIntegrator import CommonParameters
from dataIntegrator.TuShareService.TuShareSGEDailyService import TuShareSGEDailyService

logger = CommonLib.logger

class TuShareSGEDailyServiceTest(TuShareService):
    @classmethod
    def refresh_sge_daily_data(self):
        try:
            # 设置日期范围
            start_date = '20240101'
            end_date = '20261231'

            # 设置CSV文件路径
            csvFilePath = os.path.join(CommonParameters.outBoundPath, "df_tushare_sge_daily_2025.csv")

            # 创建服务实例并执行数据处理流程
            tuShareService = TuShareSGEDailyService()
            dataFrame = tuShareService.prepareDataFrame(start_date, end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date, end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            logger.info('Exception', e)
            raise e

    @classmethod
    def refresh_sge_specific_date(self):
        try:
            # 设置特定交易日期
            trade_date = '20241201'

            # 设置CSV文件路径
            csvFilePath = os.path.join(CommonParameters.outBoundPath, "df_tushare_sge_daily_specific.csv")

            # 创建服务实例并执行数据处理流程
            tuShareService = TuShareSGEDailyService()
            dataFrame = tuShareService.prepareDataFrame(trade_date, trade_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            # 删除指定日期范围的数据
            tuShareService.deleteDateFromClickHouse(trade_date, trade_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            logger.info('Exception', e)
            raise e

if __name__ == '__main__':
    tuShareSGEDailyServiceTest = TuShareSGEDailyServiceTest()
    # tuShareSGEDailyServiceTest.refresh_sge_daily_data()
    # 可选：测试特定日期的数据刷新
    tuShareSGEDailyServiceTest.refresh_sge_specific_date()

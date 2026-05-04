import time

from dataIntegrator.TuShareService.TuShareService import TuShareService
import os
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.TuShareService.TushareUSStockBasicService import TushareUSStockBasicService

logger = CommonLib.logger

class TushareUSStockBasicServiceTest(TuShareService):
    @classmethod
    def refresh_us_stocks(self):
        """获取所有美股基本信息"""
        try:
            csvFilePath = os.path.join(CommonParameters.outBoundPath, "df_tushare_us_stock_basic_all.csv")

            logger.info("开始获取所有美股基本信息...")

            tuShareService = TushareUSStockBasicService()
            dataFrame = tuShareService.prepareAllDataFrames()

            if dataFrame.empty:
                logger.warning("没有获取到美股列表数据")
                return

            logger.info(f"获取到 {len(dataFrame)} 只美股")
            logger.info(f"数据列: {dataFrame.columns.tolist()}")
            logger.info(f"前5条数据:\n{dataFrame.head()}")

            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date=None, end_date=None)
            tuShareService.saveDateToClickHouse()

            logger.info(f"✅ 成功刷新 {len(dataFrame)} 只美股基本信息")

        except Exception as e:
            logger.error(f"❌ 刷新美股列表失败：{str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise e

if __name__ == '__main__':
    tushareUSStockBasicServiceTest = TushareUSStockBasicServiceTest()
    tushareUSStockBasicServiceTest.refresh_us_stocks()
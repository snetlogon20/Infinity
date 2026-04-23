from dataIntegrator.TuShareService.TuShareChinaStockBasicService import TuShareStockBasicService
from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib
import os
from dataIntegrator import CommonParameters

logger = CommonLib.logger

class TuShareStockBasicServiceTest(TuShareService):
    @classmethod
    def refresh_all_stocks(self):
        """获取所有上市股票基本信息"""
        try:
            csvFilePath = os.path.join(CommonParameters.outBoundPath, "df_tushare_stock_basic_all.csv")

            logger.info("开始获取所有上市股票基本信息...")

            tuShareService = TuShareStockBasicService()
            dataFrame = tuShareService.prepareDataFrame(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')

            if dataFrame.empty:
                logger.warning("没有获取到股票列表数据")
                return

            logger.info(f"获取到 {len(dataFrame)} 只股票")
            logger.info(f"数据列: {dataFrame.columns.tolist()}")
            logger.info(f"前5条数据:\n{dataFrame.head()}")

            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse()
            tuShareService.saveDateToClickHouse()

            logger.info(f"✅ 成功刷新 {len(dataFrame)} 只上市股票信息")

        except Exception as e:
            logger.error(f"❌ 刷新股票列表失败：{str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise e

if __name__ == '__main__':
    tuShareStockBasicServiceTest = TuShareStockBasicServiceTest()
    tuShareStockBasicServiceTest.refresh_all_stocks()

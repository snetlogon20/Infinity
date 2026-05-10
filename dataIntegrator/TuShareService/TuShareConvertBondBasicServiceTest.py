import time
import os
from dataIntegrator.TuShareService.TuShareService import TuShareService
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.TuShareService.TuShareConvertBondBasicService import TuShareConvertBondBasicService

logger = CommonLib.logger

class TuShareConvertBondBasicServiceTest(TuShareService):

    @classmethod
    def refresh_cb_basic(self):
        """
        刷新可转债基础信息数据
        由于 cb_basic 是全量数据，不需要日期范围
        """
        try:
            csvFilePath = os.path.join(CommonParameters.outBoundPath, "df_tushare_cb_basic.csv")

            tuShareService = TuShareConvertBondBasicService()
            dataFrame = tuShareService.prepareDataFrame()

            logger.info(f"获取到 {len(dataFrame)} 条可转债基础信息记录")

            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)

            # 先删除旧数据，再插入新数据
            tuShareService.deleteDateFromClickHouse()
            tuShareService.saveDateToClickHouse()

            logger.info("可转债基础信息处理完成")

        except Exception as e:
            logger.error(f"可转债基础信息处理失败：{str(e)}")

if __name__ == '__main__':
    tuShareCbBasicServiceTest = TuShareConvertBondBasicServiceTest()
    tuShareCbBasicServiceTest.refresh_cb_basic()

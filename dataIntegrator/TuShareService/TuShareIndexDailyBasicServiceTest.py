from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib
import os
from dataIntegrator import CommonParameters
from dataIntegrator.TuShareService.TuShareIndexDailyBasicService import TuShareIndexDailyBasicService
from dataIntegrator.common.CommonDataParameters import CommonDataParameters

logger = CommonLib.logger

class TuShareIndexDailyBasicServiceTest(TuShareService):

    @classmethod
    def refresh_any_index_dailybasic(self):
        """批量处理多个指数"""
        index_list = CommonDataParameters.CN_INDEX_LIST

        # 设置日期范围
        start_date = '20250101'
        end_date = CommonParameters.today

        logger.info(f"开始批量处理 {len(index_list)} 个指数...")

        for ts_code in index_list:
            try:
                logger.info(f"\n{'=' * 60}")
                logger.info(f"正在处理：{ts_code}")
                logger.info(f"{'=' * 60}")

                csvFilePath = os.path.join(CommonParameters.outBoundPath,
                                           f"df_tushare_index_dailybasic_{ts_code.replace('.', '_')}.csv")

                tuShareService = TuShareIndexDailyBasicService()
                dataFrame = tuShareService.prepareDataFrame(ts_code, start_date=start_date, end_date=end_date)

                if dataFrame.empty:
                    logger.warning(f"{ts_code} 没有获取到数据，跳过...")
                    continue

                logger.info(f"转换数据为 JSON...")
                jsonString = tuShareService.convertDataFrame2JSON()
                logger.info(f"保存到：{csvFilePath}")
                tuShareService.saveDateFrameToDisk(csvFilePath)
                tuShareService.deleteDateFromClickHouse(ts_code, start_date, end_date)
                tuShareService.saveDateToClickHouse()

                logger.info(f" {ts_code} 处理完成！")

            except Exception as e:
                logger.error(f" {ts_code} 处理失败：{str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                continue

        logger.info(f"\n{'=' * 60}")
        logger.info(f"批量处理完成！共处理 {len(index_list)} 个指数")
        logger.info(f"{'=' * 60}")

if __name__ == '__main__':
    tuShareIndexDailyBasicServiceTest = TuShareIndexDailyBasicServiceTest()
    tuShareIndexDailyBasicServiceTest.refresh_any_index_dailybasic()

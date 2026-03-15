from dataIntegrator.TuShareService.TuShareService import TuShareService
from dataIntegrator import CommonLib
import os
from dataIntegrator import CommonParameters
from dataIntegrator.TuShareService.TuShareUSDIndexDailyService import TuShareUSDIndexDailyService
from dataIntegrator.modelService.commonService.CalendarService import CalendarService

logger = CommonLib.logger

class TuShareUSDIndexDailyServiceTest(TuShareService):

    @classmethod
    def callTuShareUSDIndexDailyService(self):
        """刷新美元指数数据"""
        logger.info("="*60)
        logger.info("开始刷新美元指数数据")
        logger.info("="*60)

        start_date = '20260301'
        end_date = CommonParameters.today

        calendar = CalendarService()
        date_range = calendar.generate_date_range(start_date, end_date)

        try:
            csvFilePath = os.path.join(CommonParameters.outBoundPath, "df_tushare_usd_index_%s-%s.csv" % (start_date, end_date))

            tuShareService = TuShareUSDIndexDailyService()
            dataFrame = tuShareService.prepareDataFrame(start_date, end_date)

            if not dataFrame.empty and len(dataFrame) > 0:
                jsonString = tuShareService.convertDataFrame2JSON()
                tuShareService.saveDateFrameToDisk(csvFilePath)
                tuShareService.deleteDateFromClickHouse(start_date, end_date)
                tuShareService.saveDateToClickHouse()

                logger.info(f"✅ {start_date} - {end_date} 刷新成功，共 {len(dataFrame)} 条数据")
            else:
                logger.warning(f"⚠️ {start_date} - {end_date} 没有数据")

        except Exception as e:
            logger.error(f"❌ {start_date} - {end_date} - 刷新失败：{e}")

        logger.info("\n" + "="*60)
        logger.info("美元指数数据刷新完成")
        logger.info("="*60)


if __name__ == '__main__':
    tuShareUSDIndexDailyServiceTest = TuShareUSDIndexDailyServiceTest()
    tuShareUSDIndexDailyServiceTest.callTuShareUSDIndexDailyService()

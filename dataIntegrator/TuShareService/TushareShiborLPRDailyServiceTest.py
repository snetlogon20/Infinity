from dataIntegrator.TuShareService.TuShareService import TuShareService
from dataIntegrator import CommonLib
import os
from dataIntegrator import CommonParameters
from dataIntegrator.TuShareService.TushareShiborLPRDailyService import TushareShiborLPRDailyService
from dataIntegrator.modelService.commonService.CalendarService import CalendarService

logger = CommonLib.logger

class TushareShiborLPRDailyServiceTest(TuShareService):

    @classmethod
    def callTushareShiborLPRDailyService(self):
        """刷新LPR利率数据"""
        logger.info("="*60)
        logger.info("开始刷新LPR利率数据")
        logger.info("="*60)

        start_date = '20200101'
        end_date = CommonParameters.today

        calendar = CalendarService()
        date_range = calendar.generate_date_range(start_date, end_date)

        try:
            csvFilePath = os.path.join(CommonParameters.outBoundPath, "df_tushare_shibor_lpr_%s-%s.csv" % (start_date, end_date))

            tushareService = TushareShiborLPRDailyService()
            dataFrame = tushareService.prepareDataFrame(start_date, end_date)

            if not dataFrame.empty and len(dataFrame) > 0:
                jsonString = tushareService.convertDataFrame2JSON()
                tushareService.saveDateFrameToDisk(csvFilePath)
                tushareService.deleteDateFromClickHouse(start_date, end_date)
                tushareService.saveDateToClickHouse()

                logger.info(f"✅ {start_date} - {end_date} 刷新成功，共 {len(dataFrame)} 条数据")
            else:
                logger.warning(f"⚠️ {start_date} - {end_date} 没有数据")

        except Exception as e:
            logger.error(f"❌ {start_date} - {end_date} - 刷新失败：{e}")

        logger.info("\n" + "="*60)
        logger.info("LPR利率数据刷新完成")
        logger.info("="*60)


if __name__ == '__main__':
    tushareShiborLPRDailyServiceTest = TushareShiborLPRDailyServiceTest()
    tushareShiborLPRDailyServiceTest.callTushareShiborLPRDailyService()

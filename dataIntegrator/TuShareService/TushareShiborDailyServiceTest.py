import os
from dataIntegrator.TuShareService.TuShareService import TuShareService
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.TuShareService.TushareShiborDailyService import TushareShiborDailyService
from dataIntegrator.modelService.commonService.CalendarService import CalendarService

logger = CommonLib.logger

class TushareShiborDailyServiceTest(TuShareService):
    @classmethod
    def refresh_shibor_daily(self):

        calenearService = CalendarService()
        # 获取 31 天前的日期，作为滚动扫描的 start date
        start_date = calenearService.calculate_T_minus_n_days(CommonParameters.today, days=300)
        end_date = CommonParameters.today

        try:
            csvFilePath = os.path.join(CommonParameters.outBoundPath, rf"df_tushare_shibor_daily_{start_date}-{end_date}.csv")

            tushareShiborDailyService = TushareShiborDailyService()
            dataFrame = tushareShiborDailyService.prepareDataFrame(start_date, end_date)
            jsonString = tushareShiborDailyService.convertDataFrame2JSON()
            tushareShiborDailyService.saveDateFrameToDisk(csvFilePath)
            tushareShiborDailyService.deleteDateFromClickHouse(start_date, end_date)
            tushareShiborDailyService.saveDateToClickHouse()

            logger.info(f"SHIBOR日线数据 {start_date}-{end_date} 处理完成")


        except Exception as e:
            logger.error(f"SHIBOR日线数据处理失败：{str(e)}")


    def get_rate_for_term(self):
        start_date = "20250101"
        end_date = "20260401"
        tushareShiborDailyService = TushareShiborDailyService()
        avg_rate, earliest_rate, latest_rate, max_rate, min_rate = tushareShiborDailyService.get_rate_for_term(
            start_date, end_date)

        print(f"在 {start_date} 到 {end_date} 期间：")
        print(f"  平均利率: {avg_rate:.4f}")
        print(f"  最早日期利率: {earliest_rate:.4f}")
        print(f"  最晚日期利率: {latest_rate:.4f}")
        print(f"  最大利率: {max_rate:.4f}")
        print(f"  最小利率: {min_rate:.4f}")

if __name__ == '__main__':
    tushareShiborDailyServiceTest = TushareShiborDailyServiceTest()
    tushareShiborDailyServiceTest.refresh_shibor_daily()

    # tushareShiborDailyServiceTest.get_rate_for_term()

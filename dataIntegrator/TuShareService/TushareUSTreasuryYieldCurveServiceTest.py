


from dataIntegrator.TuShareService.TuShareService import TuShareService
import os
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.TuShareService.TushareUSTreasuryYieldCurveService import TushareUSTreasuryYieldCurveService
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.modelService.commonService.CalendarService import CalendarService

logger = CommonLib.logger

class TushareUSTreasuryYieldCurveServiceTest(TuShareService):
    @classmethod
    def refresh_us_treasury_yield_curve(self):

        calenearService = CalendarService()
        # 获取 31 天前的日期，作为滚动扫描的 start date
        start_date = calenearService.calculate_T_minus_n_days(CommonParameters.today, days=300)
        end_date = CommonParameters.today

        try:
            csvFilePath = os.path.join(CommonParameters.outBoundPath, rf"df_tushare_US_Treasury_Yield_Curve_{start_date}-{end_date}.csv")

            tushareUSTreasuryYieldCurveService = TushareUSTreasuryYieldCurveService()
            dataFrame = tushareUSTreasuryYieldCurveService.prepareDataFrame(start_date, end_date)
            jsonString = tushareUSTreasuryYieldCurveService.convertDataFrame2JSON()
            tushareUSTreasuryYieldCurveService.saveDateFrameToDisk(csvFilePath)
            tushareUSTreasuryYieldCurveService.deleteDateFromClickHouse(start_date, end_date)
            tushareUSTreasuryYieldCurveService.saveDateToClickHouse()

            logger.info(f"美国国债收益率曲线 {start_date}-{end_date} 处理完成")


        except Exception as e:
            logger.error(f"美国国债收益率曲线处理失败：{str(e)}")


    def get_yield_for_term(cls) -> float:
        start_date = "20250101"
        end_date = "20260401"
        tushareUSTreasuryYieldCurveService = TushareUSTreasuryYieldCurveService()
        avg_yield, earliest_yield, latest_yield, max_yield, min_yield = tushareUSTreasuryYieldCurveService.get_yield_for_term(
            start_date, end_date)

        print(f"在 {start_date} 到 {end_date} 期间：")
        print(f"平均收益率: {avg_yield:.4f}")
        print(f"最早日期收益率: {earliest_yield:.4f}")
        print(f"最晚日期收益率: {latest_yield:.4f}")
        print(f"最大收益率: {max_yield:.4f}")
        print(f"最小收益率: {min_yield:.4f}")

if __name__ == '__main__':
    tushareUSTreasuryYieldCurveServiceTest = TushareUSTreasuryYieldCurveServiceTest()
    #tushareUSTreasuryYieldCurveServiceTest.refresh_us_treasury_yield_curve()

    tushareUSTreasuryYieldCurveServiceTest.get_yield_for_term()


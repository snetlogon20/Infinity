import time

from dataIntegrator.TuShareService.TuShareService import TuShareService
import os
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.TuShareService.TuShareUSStockDailyService import TuShareUSStockDailyService
from dataIntegrator.modelService.commonService.CalendarService import CalendarService

logger = CommonLib.logger

class TuShareUSStockDailyServiceTest(TuShareService):
    @classmethod
    def refresh_citi(self):

            # ts_code = 'C'
            # start_date = '20250101'
            # end_date = '20251231'

            calenearService = CalendarService()
            # 获取31天前的日期，作为滚动扫描的start date
            start_date = calenearService.calculate_T_minus_n_days( CommonParameters.today, days=31)
            end_date = CommonParameters.today

            ts_code_list = ["C", "JPM", "AAPL","NVDA", "MSFT"]
            ts_code_dict = {f"stock_{i}": code for i, code in enumerate(ts_code_list, 1)}

            # 循环调用
            for key, ts_code in ts_code_dict.items():
                try:
                    csvFilePath = os.path.join(CommonParameters.outBoundPath, rf"df_tushare_df_tushare_USStockBasic_{ts_code}{start_date}-{end_date}.csv")

                    tuShareService = TuShareUSStockDailyService()
                    dataFrame = tuShareService.prepareDataFrame(ts_code, start_date, end_date)
                    jsonString = tuShareService.convertDataFrame2JSON()
                    tuShareService.saveDateFrameToDisk(csvFilePath)
                    tuShareService.deleteDateFromClickHouse(start_date, end_date)
                    tuShareService.saveDateToClickHouse()

                    logger.info(f"{key}: {ts_code} {start_date}-{end_date} 处理完成")
                    # Tushare 规定 1 分钟只能访问 2 次，这里循环休眠 31 秒
                    for i in range(1, 32):
                        logger.info(f"Tushare 限流控制：第 {i}/31 秒...")
                        time.sleep(1)

                except Exception as e:
                    logger.error(f"{key}: {ts_code} 处理失败：{str(e)}")

if __name__ == '__main__':
    tuShareUSStockDailyServiceTest = TuShareUSStockDailyServiceTest()
    tuShareUSStockDailyServiceTest.refresh_citi()
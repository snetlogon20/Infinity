import time
import os
from dataIntegrator.TuShareService.TuShareService import TuShareService
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.TuShareService.TuShareYcCbService import TuShareYcCbService
from dataIntegrator.modelService.commonService.CalendarService import CalendarService

logger = CommonLib.logger

class TuShareYcCbServiceTest(TuShareService):

    @classmethod
    def refresh_yc_cb(self):
        calendarService = CalendarService()
        # 获取过去600天的数据作为示例
        start_date = calendarService.calculate_T_minus_n_days(CommonParameters.today, days=600)
        end_date = CommonParameters.today

        # 示例曲线编码：1001.CB-中债国债收益率曲线
        ts_code_list = ["1001.CB"]

        ts_code_dict = {f"code_{i}": code for i, code in enumerate(ts_code_list, 1)}

        for key, ts_code in ts_code_dict.items():
            try:
                csvFilePath = os.path.join(CommonParameters.outBoundPath, rf"df_tushare_yc_cb_{ts_code}_{start_date}-{end_date}.csv")

                tuShareService = TuShareYcCbService()
                dataFrame = tuShareService.prepareDataFrame(ts_code, start_date, end_date)
                jsonString = tuShareService.convertDataFrame2JSON()
                tuShareService.saveDateFrameToDisk(csvFilePath)

                # 先删除旧数据，再插入新数据
                tuShareService.deleteDateFromClickHouse(ts_code, start_date, end_date)
                tuShareService.saveDateToClickHouse()

                logger.info(f"{key}: {ts_code} {start_date}-{end_date} 处理完成")

            except Exception as e:
                logger.error(f"{key}: {ts_code} 处理失败：{str(e)}")

if __name__ == '__main__':
    tuShareYcCbServiceTest = TuShareYcCbServiceTest()
    tuShareYcCbServiceTest.refresh_yc_cb()

from dataIntegrator.TuShareService.TuShareService import TuShareService
from dataIntegrator import CommonLib
import os
from dataIntegrator import CommonParameters
from dataIntegrator.TuShareService.TuShareFXDailyService import TuShareFXDailyService
from dataIntegrator.modelService.commonService.CalendarService import CalendarService

logger = CommonLib.logger

class TuShareFXDailyServiceTest(TuShareService):


    @classmethod
    def callTuShareFXDailyService(self):
        """刷新所有主要外汇对数据"""
        logger.info("="*60)
        logger.info("开始刷新所有主要外汇对数据")
        logger.info("="*60)


        logger.info(f"\n正在刷新")
        ts_code = "nothing"
        # start_date = '20231028'
        # end_date = '20231028'

        start_date = '20231028'
        end_date = CommonParameters.today

        calendar = CalendarService()
        #date_range = self.generate_date_range(start_date, end_date)
        date_range = calendar.generate_date_range(start_date, end_date)
        for i, (current_start, current_end) in enumerate(date_range, 1):
            try:
                csvFilePath = os.path.join(CommonParameters.outBoundPath, "df_tushare_fx_%s-%s.csv"% (start_date, start_date))

                tuShareService = TuShareFXDailyService()
                dataFrame = tuShareService.prepareDataFrame(ts_code, current_start, current_start)
                jsonString = tuShareService.convertDataFrame2JSON()
                tuShareService.saveDateFrameToDisk(csvFilePath)
                tuShareService.deleteDateFromClickHouse(ts_code, current_start, current_start)
                tuShareService.saveDateToClickHouse()

                logger.info(f"✅ {current_start} - {current_end} 刷新成功，共 {len(dataFrame)} 条数据")
                # logger.info(f"✅ {current_start} - {current_end} 刷新成功，共  条数据")

            except Exception as e:
                logger.error(f"❌ {current_start} - {current_end} - 刷新失败：{e}")
                continue

        logger.info("\n" + "="*60)
        logger.info("所有外汇对刷新完成")
        logger.info("="*60)

    # @classmethod
    # def generate_date_range(self, start_date, end_date):
    #     """生成日期范围列表，按天循环"""
    #     date_ranges = []
    #
    #     from datetime import datetime, timedelta
    #
    #     start = datetime.strptime(start_date, '%Y%m%d')
    #     end = datetime.strptime(end_date, '%Y%m%d')
    #
    #     current = start
    #     while current <= end:
    #         date_str = current.strftime('%Y%m%d')
    #         date_ranges.append((date_str, date_str))
    #         current += timedelta(days=1)
    #
    #     return date_ranges



if __name__ == '__main__':
    tuShareFXDailyServiceTest = TuShareFXDailyServiceTest()

    # 批量刷新所有外汇对
    tuShareFXDailyServiceTest.callTuShareFXDailyService()

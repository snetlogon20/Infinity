import os
from dataIntegrator.TuShareService.TuShareService import TuShareService
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.TuShareService.TuShareIndexDailyBasicService import TuShareIndexDailyBasicService
from dataIntegrator.modelService.commonService.CalendarService import CalendarService

logger = CommonLib.logger

class TuShareIndexDailyBasicServiceTest(TuShareService):

    @classmethod
    def refresh_index_dailybasic_by_date(self):
        """
        按交易日维度处理 index_dailybasic 数据。
        每个交易日一把拉取全量指数数据，直接入库。
        """
        start_date = '20250101'
        end_date = CommonParameters.today

        calendar_service = CalendarService()
        trade_date_list = calendar_service.calculate_dates_between_start_end_date(start_date, end_date)

        logger.info("=" * 80)
        logger.info(f"开始处理 index_dailybasic 数据（按交易日批量模式）")
        logger.info(f"日期范围: {start_date} ~ {end_date}, 共 {len(trade_date_list)} 个交易日")
        logger.info("=" * 80)

        total_records = 0
        for trade_date_str in trade_date_list:
            try:
                tuShareService = TuShareIndexDailyBasicService()
                dataFrame = tuShareService.prepareDataFrame(ts_code="", trade_date=trade_date_str)

                if dataFrame.empty:
                    logger.info(f"  {trade_date_str}: 无数据，跳过")
                    continue

                hit_count = len(dataFrame)
                logger.info(f"  {trade_date_str}: {hit_count} 条记录")

                csvFilePath = os.path.join(CommonParameters.outBoundPath,
                                           f"df_tushare_index_dailybasic_{trade_date_str}.csv")

                TuShareIndexDailyBasicService.dataFrame = dataFrame
                TuShareIndexDailyBasicService.convertDataFrame2JSON()
                TuShareIndexDailyBasicService.saveDateFrameToDisk(csvFilePath)
                TuShareIndexDailyBasicService.deleteByTradeDate(trade_date_str)
                TuShareIndexDailyBasicService.saveDateToClickHouse()

                total_records += hit_count
                logger.info(f"  {trade_date_str}: 已保存 {hit_count} 条记录")

            except Exception as e:
                logger.error(f"  {trade_date_str} 处理失败：{str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                continue

        logger.info("\n" + "=" * 80)
        logger.info(f"处理完成！共 {total_records} 条记录")
        logger.info("=" * 80)


if __name__ == '__main__':
    tuShareIndexDailyBasicServiceTest = TuShareIndexDailyBasicServiceTest()
    tuShareIndexDailyBasicServiceTest.refresh_index_dailybasic_by_date()

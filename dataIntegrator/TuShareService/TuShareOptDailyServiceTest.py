import os
import time
import pandas as pd
from dataIntegrator.TuShareService.TuShareService import TuShareService
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.TuShareService.TuShareOptDailyService import TuShareOptDailyService
from dataIntegrator.modelService.commonService.CalendarService import CalendarService

logger = CommonLib.logger

class TuShareOptDailyServiceTest(TuShareService):



    @classmethod
    def test_by_trade_date(self, trade_date="20261218", exchange=""):
        """
        按单个交易日测试期权日线数据
        """
        tuShareService = TuShareOptDailyService()

        logger.info(f"按交易日查询: {trade_date}")
        tuShareService.refresh_opt_daily(
            trade_date=trade_date,
            exchange=exchange
        )


    def refresh_opt_daily_by_ts_code(self):

        tuShareService = TuShareOptDailyService()

        ts_code_list = [
            "HO2612-C-2500.CFX", "HO2612-C-2600.CFX", "HO2612-C-2700.CFX",
            "HO2612-C-2800.CFX", "HO2612-C-2900.CFX", "HO2612-C-3000.CFX",
            "HO2612-C-3100.CFX", "HO2612-C-3200.CFX", "HO2612-C-3300.CFX",
            "HO2612-C-3400.CFX", "HO2612-C-3500.CFX",
            "HO2612-P-2500.CFX", "HO2612-P-2600.CFX", "HO2612-P-2700.CFX",
            "HO2612-P-2800.CFX", "HO2612-P-2900.CFX", "HO2612-P-3000.CFX",
            "HO2612-P-3100.CFX", "HO2612-P-3200.CFX", "HO2612-P-3300.CFX",
            "HO2612-P-3400.CFX", "HO2612-P-3500.CFX",
        ]
        calendarService = CalendarService()
        start_date = calendarService.calculate_T_minus_n_days(CommonParameters.today, days=300)
        end_date = CommonParameters.today
        calendar_service = CalendarService()
        trade_date_list = calendar_service.calculate_dates_between_start_end_date(start_date, end_date)
        # 批量模式: 每个交易日只调1次API（vs 原来每个合约1次），效率提升 22 倍
        tuShareService.refresh_opt_daily_by_ts_code_list(
            ts_code_list=ts_code_list,
            trade_date_list=trade_date_list,
            exchange=""
        )
        logger.info("=" * 80)
        logger.info("期权日线数据处理完成")
        logger.info("=" * 80)


if __name__ == '__main__':
    tuShareOptDailyServiceTest = TuShareOptDailyServiceTest()

    try:
        logger.info("=" * 80)
        logger.info("开始处理期权日线数据...")
        logger.info("=" * 80)

        # 使用示例1: 按交易日查询（推荐，单日数据量适中）
        # tuShareOptDailyServiceTest.test_by_trade_date(
        #     trade_date="20260702",
        #     exchange=""
        # )

        # 使用示例2: 批量获取期权日线数据（一次 API 调用获取全天全量，内存过滤，最后一次性存入 ClickHouse）
        tuShareOptDailyServiceTest.refresh_opt_daily_by_ts_code()

    except Exception as e:
        logger.error(f"处理失败: {e}")
        import traceback
        traceback.print_exc()

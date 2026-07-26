import os
from dataIntegrator.TuShareService.TuShareService import TuShareService
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.TuShareService.TuShareOptDailyService import TuShareOptDailyService
from dataIntegrator.modelService.commonService.CalendarService import CalendarService

logger = CommonLib.logger

class TuShareOptDailyServiceTest(TuShareService):

    @classmethod
    def refresh_opt_daily(self, ts_code=None, trade_date=None, start_date=None, end_date=None, exchange=None):
        """
        刷新期权日线行情数据

        Args:
            ts_code: TS合约代码（可选）
            trade_date: 交易日期 (YYYYMMDD)（可选）
            start_date: 开始日期 (YYYYMMDD)（可选）
            end_date: 结束日期 (YYYYMMDD)（可选）
            exchange: 交易所(SSE/SZSE/CFFEX/DCE/SHFE/CZCE)（可选）
        """
        try:
            csvFilePath = os.path.join(CommonParameters.outBoundPath, "df_tushare_opt_daily.csv")

            tuShareService = TuShareOptDailyService()

            logger.info(f"开始获取期权日线数据...")
            logger.info(f"  - ts_code: {ts_code}")
            logger.info(f"  - trade_date: {trade_date}")
            logger.info(f"  - 日期范围: {start_date} ~ {end_date}")
            logger.info(f"  - exchange: {exchange}")

            # 获取数据
            dataFrame = tuShareService.prepareDataFrame(
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date,
                exchange=exchange
            )

            if dataFrame.empty:
                logger.warning("期权日线数据为空，跳过处理")
                return

            logger.info(f"获取到 {len(dataFrame)} 条期权日线记录")

            # 保存到 CSV
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            logger.info(f"数据已保存到: {csvFilePath}")

            # 先删除旧数据，再插入新数据
            logger.info("开始删除 ClickHouse 中的旧数据...")
            tuShareService.deleteDateFromClickHouse(
                ts_code=ts_code if ts_code else "",
                trade_date=trade_date if trade_date else "",
                start_date=start_date if start_date else "",
                end_date=end_date if end_date else ""
            )

            logger.info("开始保存数据到 ClickHouse...")
            tuShareService.saveDateToClickHouse()

            logger.info(f"✅ 期权日线数据处理完成，共 {len(dataFrame)} 条记录")

        except Exception as e:
            logger.error(f"❌ 期权日线数据处理失败：{str(e)}")
            import traceback
            logger.error(traceback.format_exc())

    @classmethod
    def test_by_trade_date(self, trade_date="20261218", exchange=""):
        """
        按单个交易日测试期权日线数据
        """
        logger.info(f"按交易日查询: {trade_date}")
        self.refresh_opt_daily(
            trade_date=trade_date,
            exchange=exchange
        )

    @classmethod
    def test_by_ts_code(self, ts_code="10001313.SH", trade_date="20261201"):
        """
        按合约代码 + 交易日期测试期权日线数据
        """
        logger.info(f"按合约代码 + 交易日期查询: {ts_code}, {trade_date}")
        self.refresh_opt_daily(
            ts_code=ts_code,
            trade_date=trade_date
        )

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

        # 使用示例2: 按合约代码 + 日期范围查询（取消注释使用）
        # tuShareOptDailyServiceTest.test_by_ts_code(
        #     ts_code="HO2612-C-2500.CFX",
        #     trade_date="20260701"
        # )


        # 使用示例3: 使用 calculate_T_minus_n_days_list 循环遍历日期
        # calendarService = CalendarService()
        # start_date = calendarService.calculate_T_minus_n_days(CommonParameters.today, days=30)
        # end_date = CommonParameters.today
        #
        # calendar_service = CalendarService()
        # trade_date_list = calendar_service.calculate_dates_between_start_end_date(start_date, end_date)
        # for trade_date_str in trade_date_list:
        #     tuShareOptDailyServiceTest.test_by_trade_date(
        #         trade_date=trade_date_str,
        #         exchange=""
        #     )

        # 使用示例4: 使用 calculate_T_minus_n_days_list 循环遍历日期, 并循环要求的产品代码
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
        start_date = calendarService.calculate_T_minus_n_days(CommonParameters.today, days=30)
        end_date = CommonParameters.today

        calendar_service = CalendarService()
        trade_date_list = calendar_service.calculate_dates_between_start_end_date(start_date, end_date)
        for trade_date_str in trade_date_list:
            for ts_code in ts_code_list:
                tuShareOptDailyServiceTest.test_by_ts_code(
                    ts_code=ts_code,
                    trade_date=trade_date_str
                )


        logger.info("=" * 80)
        logger.info("期权日线数据处理完成")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"处理失败: {e}")
        import traceback
        traceback.print_exc()

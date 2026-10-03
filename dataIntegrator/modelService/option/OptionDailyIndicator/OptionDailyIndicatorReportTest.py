from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.modelService.option.OptionDailyIndicator.OptionDailyIndicatorReport import \
    OptionDailyIndicatorReport

logger = CommonLib.logger


class OptionDailyIndicatorReportTest:

    def run(self):
        """按产品配置生成期权日线指标 PDF 报告"""
        logger.info("=" * 80)
        logger.info("Starting OptionDailyIndicatorReportTest")
        logger.info("=" * 80)

        # 定义报告配置：华夏上证50ETF期权（小合约），symbol like '510050%'
        # 每个 symbol_filter + call_put 组合为独立产品
        report_configs = [
            {
                "name": "华夏上证50ETF看涨欧式期权",
                "start_date": "20251222",
                #"end_date": "20260717",
                "end_date": CommonParameters.today,
                "call_put": "C",
                "symbol_filter": "510050_2612%", #一个月的期权数据，否则太大，报表没有作用
            },
            {
                "name": "华夏上证50ETF看跌欧式期权",
                "start_date": "20251222",
                #"end_date": "20260717",
                "end_date": CommonParameters.today, #一个月的期权数据，否则太大，报表没有作用
                "call_put": "P",
                "symbol_filter": "510050_2612%",
            },
        ]

        dailyIndicatorReport = OptionDailyIndicatorReport()

        for idx, config in enumerate(report_configs, 1):
            logger.info("\n" + "=" * 60)
            logger.info(f" 生成 PDF 报告 [{idx}/{len(report_configs)}]: {config['name']}")
            logger.info("=" * 60)

            try:
                pdf_path = dailyIndicatorReport.run(
                    start_date=config.get("start_date"),
                    end_date=config.get("end_date"),
                    symbol_filter=config.get("symbol_filter"),
                    call_put=config.get("call_put"),
                )
                if pdf_path:
                    logger.info(f"✅ PDF 报告已生成: {pdf_path}")
                else:
                    logger.warning(f"⚠️ PDF 报告未生成 (可能数据为空)")

            except Exception as e:
                logger.error(f"❌ PDF 生成失败: {config['name']}")
                logger.error(f"   错误信息: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                continue

        logger.info("=" * 80)
        logger.info("Test completed.")
        logger.info("=" * 80)


if __name__ == "__main__":
    test = OptionDailyIndicatorReportTest()
    test.run()

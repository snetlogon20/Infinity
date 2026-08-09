from dataIntegrator import CommonLib
from dataIntegrator.modelService.option.OptDailyIndicatorReport import \
    OptDailyIndicatorReport

logger = CommonLib.logger


class OptDailyIndicatorReportTest:

    def run(self):
        """按产品配置生成期权日线指标 PDF 报告"""
        logger.info("=" * 80)
        logger.info("Starting OptDailyIndicatorReportTest")
        logger.info("=" * 80)

        # 定义报告配置：每个 ts_code_filter + call_put 组合为独立产品
        report_configs = [
            {
                "name": "HO2612看涨欧式期权",
                "start_date": "20251222",
                "end_date": "20260717",
                "call_put": "C",
                "ts_code_filter": "HO2612%",
            },
            {
                "name": "HO2612看跌欧式期权",
                "start_date": "20251222",
                "end_date": "20260717",
                "call_put": "P",
                "ts_code_filter": "HO2612%",
            },
        ]

        opt_report = OptDailyIndicatorReport()

        for idx, config in enumerate(report_configs, 1):
            logger.info("\n" + "=" * 60)
            logger.info(f" 生成 PDF 报告 [{idx}/{len(report_configs)}]: {config['name']}")
            logger.info("=" * 60)

            try:
                pdf_path = opt_report.run(
                    start_date=config.get("start_date"),
                    end_date=config.get("end_date"),
                    ts_code_filter=config.get("ts_code_filter"),
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
    test = OptDailyIndicatorReportTest()
    test.run()

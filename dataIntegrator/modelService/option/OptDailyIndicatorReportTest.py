from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.modelService.option.OptDailyIndicatorReport import \
    OptDailyIndicatorReport

logger = CommonLib.logger


class OptDailyIndicatorReportTest:

    def run(self):
        """运行期权日线指标报告生成测试"""
        logger.info("=" * 80)
        logger.info("Starting OptDailyIndicatorReportTest")
        logger.info("=" * 80)

        report = OptDailyIndicatorReport()
        pdf_path = report.run(
            start_date="20251222",
            end_date="20260717",
            ts_code_filter="HO2612%",
        )

        if pdf_path:
            logger.info(f"\n✅ Report generated successfully: {pdf_path}")
        else:
            logger.warning("\n⚠️ Report generation returned None")

        logger.info("=" * 80)
        logger.info("Test completed.")
        logger.info("=" * 80)

        return pdf_path


if __name__ == "__main__":
    test = OptDailyIndicatorReportTest()
    test.run()

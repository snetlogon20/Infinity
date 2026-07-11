from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.modelService.macroEconomy.MacroEinaEconomicIndicatorReport import \
    MacroEinaEconomicIndicatorReport

logger = CommonLib.logger
commonLib = CommonLib()


class MacroEinaEconomicIndicatorReportTest:

    def run(self):
        """运行宏观EINA经济指标报告生成测试"""
        logger.info("=" * 80)
        logger.info("Starting MacroEinaEconomicIndicatorReportTest")
        logger.info("=" * 80)

        report = MacroEinaEconomicIndicatorReport()
        pdf_path = report.run()

        if pdf_path:
            logger.info(f"\n✅ Report generated successfully: {pdf_path}")
        else:
            logger.warning("\n⚠️ Report generation returned None")

        logger.info("=" * 80)
        logger.info("Test completed.")
        logger.info("=" * 80)

        return pdf_path


if __name__ == "__main__":
    test = MacroEinaEconomicIndicatorReportTest()
    test.run()

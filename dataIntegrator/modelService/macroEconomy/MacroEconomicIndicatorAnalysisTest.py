from dataIntegrator import CommonLib
from dataIntegrator.modelService.macroEconomy.MacroEconomicIndicatorAnalysis import MacroEconomicIndicatorAnalysis

logger = CommonLib.logger
commonLib = CommonLib()


class MacroEconomicIndicatorAnalysisTest:

    def run(self):
        """运行宏观经济指标数据生成测试"""
        logger.info("=" * 80)
        logger.info("🚀 Starting MacroEconomicIndicatorTest")
        logger.info("=" * 80)

        indicator = MacroEconomicIndicatorAnalysis()
        df = indicator.generate_macro_indicator_data()

        # 打印前5行预览
        logger.info("\n📋 数据预览 (前5行):")
        logger.info(df.head(5).to_string())

        logger.info("\n" + "=" * 80)
        logger.info(f"✅ Test completed. Generated {len(df)} rows, {len(df.columns)} columns.")
        logger.info("=" * 80)

        return df


if __name__ == "__main__":
    test = MacroEconomicIndicatorAnalysisTest()
    test.run()

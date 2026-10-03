r"""
Covered Call 策略 PDF 报告 — 测试入口

运行方式：
    python -m dataIntegrator.modelService.option.OptionTradingStrategyManager.CoveredCallStrategyReportTest

前置条件：
    先运行 CoveredCallStrategyAnalysisTest 完成 tb_option_trading_strategy_covered_call 落库

功能：
    调用 CoveredCallStrategyReport 按配置从 tb_option_trading_strategy_covered_call 读取
    strategy_type='COVERED_CALL' 的分析结果，生成 PDF 报告（含指标表格、10张图表、
    数字化交易员点评），输出到 CommonParameters.optionAnalysisReportPath：
    D:\workspace_python\infinity_data\outbound\report\OptionAnalysis

配置说明：
    - name:           报告名称
    - start_date:     数据起始日期 YYYYMMDD（与分析落库区间一致）
    - end_date:       数据截止日期 YYYYMMDD
    - call_put:       'C'（Covered Call 只用认购侧）
    - symbol_filter:  LIKE 模式过滤 symbol，如 '510050C2612%'
"""

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.modelService.option.OptionTradingStrategyManager.CoveredCallStrategyReport import (
    CoveredCallStrategyReport
)

logger = CommonLib.logger


class CoveredCallStrategyReportTest:
    """Covered Call 策略 PDF 报告测试类"""

    def run(self):
        """按配置批量生成 PDF 报告"""
        logger.info("=" * 80)
        logger.info("Starting CoveredCallStrategyReportTest")
        logger.info("=" * 80)

        # ============================================================
        # 报告配置列表 — 与 CoveredCallStrategyAnalysisTest 保持一致
        # ============================================================
        report_configs = [
            {
                "name": "华夏上证50ETF认购期权（Covered Call）",
                "start_date": "20251222",
                # "end_date": "20260717",
                "end_date": CommonParameters.today,
                "call_put": "C",
                "symbol_filter": "510050C2612%",
            },
            # 追加配置示例（换月滚动时改 symbol_filter 即可）:
            # {
            #     "name": "华夏上证50ETF认购期权2603（Covered Call）",
            #     "start_date": "20251222",
            #     "end_date": CommonParameters.today,
            #     "call_put": "C",
            #     "symbol_filter": "510050C2603%",
            # },
        ]

        report = CoveredCallStrategyReport()

        success_count = 0
        fail_count = 0
        skip_count = 0

        for idx, config in enumerate(report_configs, 1):
            name = config.get("name", "Unknown")

            logger.info("\n" + "=" * 60)
            logger.info(f"  报告 [{idx}/{len(report_configs)}]: {name}")
            logger.info("=" * 60)

            try:
                filepath = report.run(config)
                if filepath:
                    logger.info(f"  ✅ PDF 报告已生成: {filepath}")
                    success_count += 1
                else:
                    logger.warning(f"  ⚠️ 数据为空（先运行 CoveredCallStrategyAnalysisTest），报告跳过")
                    skip_count += 1

            except Exception as e:
                logger.error(f"  ❌ 报告生成失败: {name}")
                logger.error(f"     错误信息: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                fail_count += 1

        # 总结
        logger.info("\n" + "=" * 80)
        logger.info("CoveredCallStrategyReportTest 完成")
        logger.info(f"  成功: {success_count}, 跳过(空数据): {skip_count}, 失败: {fail_count}")
        logger.info(f"  输出目录: {report.REPORT_DIR}")
        logger.info("=" * 80)


if __name__ == "__main__":
    test = CoveredCallStrategyReportTest()
    test.run()

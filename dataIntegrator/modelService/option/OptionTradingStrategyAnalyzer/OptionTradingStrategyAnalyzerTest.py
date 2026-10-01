r"""
Long Call 策略分析 — 测试入口

运行方式：
    python -m dataIntegrator.modelService.option.OptionCallStrategyAnalyzerTest

功能：
    调用 OptionCallStrategyAnalyzer 按配置循环生成 Excel 报表
    输出路径: D:\workspace_python\infinity_data\outbound\report\OptionAnalysis

配置说明：
    - name:            报表名称（用于文件名和标题）
    - start_date:      数据起始日期 YYYYMMDD
    - end_date:        数据截止日期 YYYYMMDD
    - call_put:        'C' 看涨 / 'P' 看跌
    - exercise_type:   '欧式' / '美式'，None 不过滤
    - ts_code_filter:  LIKE 模式过滤合约代码，如 'HO2612%', 'IO2606%'
"""

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.modelService.option.OptionTradingStrategyAnalyzer import OptionTradingStrategyAnalyzer

logger = CommonLib.logger


class OptionTradingStrategyAnalyzerTest:
    """Long Call 策略分析测试类"""

    def run(self):
        """按产品配置批量生成策略盈亏 Excel 报表"""
        logger.info("=" * 80)
        logger.info("Starting OptionCallStrategyAnalyzerTest")
        logger.info("=" * 80)

        # ============================================================
        # 报告配置列表 — 按需要修改此配置即可批量出报表
        # ============================================================
        report_configs = [
            {
                "name": "HO2612看涨欧式期权",
                "start_date": "20251222",
                #"end_date": "20260717",
                "end_date": CommonParameters.today,
                "call_put": "C",
                "exercise_type": "欧式",
                "ts_code_filter": "HO2612%",
            },
            {
                "name": "HO2612看跌欧式期权",
                "start_date": "20251222",
                #"end_date": "20260717",
                "end_date": CommonParameters.today,
                "call_put": "P",
                "exercise_type": "欧式",
                "ts_code_filter": "HO2612%",
            },
            # 追加配置示例:
            # {
            #     "name": "IO2606看涨欧式期权",
            #     "start_date": "20251222",
            #     "end_date": "20260717",
            #     "call_put": "C",
            #     "exercise_type": "欧式",
            #     "ts_code_filter": "IO2606%",
            # },
            # {
            #     "name": "MO2606看涨欧式期权",
            #     "start_date": "20251222",
            #     "end_date": "20260717",
            #     "call_put": "C",
            #     "exercise_type": "欧式",
            #     "ts_code_filter": "MO2606%",
            # },
        ]

        analyzer = OptionTradingStrategyAnalyzer()

        success_count = 0
        fail_count = 0
        skip_count = 0

        for idx, config in enumerate(report_configs, 1):
            name = config.get("name", "Unknown")

            logger.info("\n" + "=" * 60)
            logger.info(f"  报表 [{idx}/{len(report_configs)}]: {name}")
            logger.info("=" * 60)

            try:
                filepath = analyzer.run(config)
                if filepath:
                    logger.info(f"  ✅ Excel 报表已生成: {filepath}")
                    success_count += 1
                else:
                    logger.warning(f"  ⚠️ 数据为空，报表跳过")
                    skip_count += 1

            except Exception as e:
                logger.error(f"  ❌ 报表生成失败: {name}")
                logger.error(f"     错误信息: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                fail_count += 1

        # 总结
        logger.info("\n" + "=" * 80)
        logger.info("OptionCallStrategyAnalyzerTest 完成")
        logger.info(f"  成功: {success_count}, 跳过(空数据): {skip_count}, 失败: {fail_count}")
        logger.info(f"  输出目录: {analyzer.REPORT_DIR}")
        logger.info("=" * 80)


if __name__ == "__main__":
    test = OptionTradingStrategyAnalyzerTest()
    test.run()

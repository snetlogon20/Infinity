r"""
OptionTradingStrategyAnalyzerReport — 测试入口

运行方式：
    python -m dataIntegrator.modelService.option.OptionTradingStrategyAnalyzerReportTest

功能：
    读取 indexsysdb.tb_option_trading_strategy_indicator（由 OptionTradingStrategyAnalyzer 写入），
    按 trade_date + ts_code_filter 生成「指标 × 合约」透视矩阵 Excel 报表。
    输出路径: CommonParameters.optionAnalysisReportPath
             (D:\workspace_python\infinity_data\outbound\report\OptionAnalysis\)

配置说明：
    - trade_date:      交易日期 YYYYMMDD（读取该日指标数据）
                       默认取表中最新交易日，可显式指定（如 "20260828"）
    - call_put:        'C' 看涨 / 'P' 看跌 / None 不过滤
    - ts_code_filter:  LIKE 模式过滤合约代码，如 'HO2612%', 'IO2606%'

文件名示例:
    OptionTradingStrategyAnalyzerReport_20260828_20260830_103000_HO2612_C.xlsx
    （文件名含生成时间戳 yyyymmdd_hhmmss，同一交易日重复生成不会被 Excel 占用覆盖）
"""

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.modelService.option.OptionTradingStrategyAnalyzerReport import \
    OptionTradingStrategyAnalyzerReport

logger = CommonLib.logger


class OptionTradingStrategyAnalyzerReportTest:
    """期权策略分析报告测试类"""

    @staticmethod
    def get_latest_trade_date():
        """查询 tb_option_trading_strategy_indicator 中最新交易日（无数据返回 None）"""
        try:
            sql = ("SELECT max(trade_date) AS latest_date "
                   "FROM indexsysdb.tb_option_trading_strategy_indicator")
            df = ClickhouseService.getDataFrameWithoutColumnsName(sql)
            if len(df) == 0 or not df.iloc[0]['latest_date']:
                return None
            return str(df.iloc[0]['latest_date'])
        except Exception as e:
            logger.warning(f"Failed to query latest trade_date: {e}")
            return None

    def run(self):
        """按产品配置批量生成透视矩阵 Excel 报表"""
        logger.info("=" * 80)
        logger.info("Starting OptionTradingStrategyAnalyzerReportTest")
        logger.info("=" * 80)

        # 默认交易日 = 表中最新交易日（可被下方配置覆盖）
        default_trade_date = self.get_latest_trade_date() or CommonParameters.today
        logger.info(f"Default trade_date (latest in table): {default_trade_date}")

        # ============================================================
        # 报告配置列表 — 按需要修改此配置即可批量出报表
        # ============================================================
        report_configs = [
            {
                "name": "HO2612看涨欧式期权",
                "trade_date": default_trade_date,
                "call_put": "C",
                "ts_code_filter": "HO2612%",
            },
            {
                "name": "HO2612看跌欧式期权",
                "trade_date": default_trade_date,
                "call_put": "P",
                "ts_code_filter": "HO2612%",
            },
        ]

        reporter = OptionTradingStrategyAnalyzerReport()

        success_count = 0
        fail_count = 0
        skip_count = 0

        for idx, config in enumerate(report_configs, 1):
            name = config.get("name", "Unknown")

            logger.info("\n" + "=" * 60)
            logger.info(f"  报表 [{idx}/{len(report_configs)}]: {name}")
            logger.info("=" * 60)

            try:
                filepath = reporter.run(
                    trade_date=config.get("trade_date"),
                    ts_code_filter=config.get("ts_code_filter"),
                    call_put=config.get("call_put"),
                )
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
        logger.info("OptionTradingStrategyAnalyzerReportTest 完成")
        logger.info(f"  成功: {success_count}, 跳过(空数据): {skip_count}, 失败: {fail_count}")
        logger.info(f"  输出目录: {reporter.REPORT_DIR}")
        logger.info("=" * 80)


if __name__ == "__main__":
    test = OptionTradingStrategyAnalyzerReportTest()
    test.run()

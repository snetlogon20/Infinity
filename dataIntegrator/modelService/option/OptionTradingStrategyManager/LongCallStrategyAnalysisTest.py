r"""
Long Call（牛市买购）策略分析 — 测试入口

运行方式：
    python -m dataIntegrator.modelService.option.OptionTradingStrategyManager.LongCallStrategyAnalysisTest

前置条件：
    tb_tushare_opt_daily_indicator 已有 510050C2612 认购期权日线指标数据

功能：
    调用 LongCallStrategyAnalysis 按配置计算策略指标，
    结果写入 ClickHouse 表 tb_option_trading_strategy_long_call（含分析时间戳与参数）。
    报表由 LongCallStrategyReportTest 读取该表生成 PDF。

配置说明：
    - name:           批次名称（写入日志）
    - start_date:     数据起始日期 YYYYMMDD
    - end_date:       数据截止日期 YYYYMMDD
    - call_put:       'C'（Long Call 只用认购侧）
    - symbol_filter:  LIKE 模式过滤 basic.symbol，如 '510050C2612%'
                      （华夏上证50ETF 2612 到期认购，8位 ts_code 由 basic 反查）
"""

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.modelService.option.OptionTradingStrategyManager.OptionStrategyFactory import (
    OptionStrategyFactory
)

logger = CommonLib.logger


class LongCallStrategyAnalysisTest:
    """Long Call 策略分析测试类"""

    def run(self):
        """按配置批量执行策略分析并落库"""
        logger.info("=" * 80)
        logger.info("Starting LongCallStrategyAnalysisTest")
        logger.info("=" * 80)

        # ============================================================
        # 分析配置列表 — 按需要修改此配置即可批量执行
        # ============================================================
        report_configs = [
            {
                "name": "华夏上证50ETF认购期权（Long Call 牛市买购）",
                "start_date": "20251222",
                # "end_date": "20260717",
                "end_date": CommonParameters.today,
                "call_put": "C",
                "symbol_filter": "510050C2612%",
            },
            # 追加配置示例（换月滚动时改 symbol_filter 即可）:
            # {
            #     "name": "华夏上证50ETF认购期权2603（Long Call 牛市买购）",
            #     "start_date": "20251222",
            #     "end_date": CommonParameters.today,
            #     "call_put": "C",
            #     "symbol_filter": "510050C2603%",
            # },
        ]

        analyzer = OptionStrategyFactory.create('LONG_CALL')

        success_count = 0
        fail_count = 0
        skip_count = 0

        for idx, config in enumerate(report_configs, 1):
            name = config.get("name", "Unknown")

            logger.info("\n" + "=" * 60)
            logger.info(f"  分析批次 [{idx}/{len(report_configs)}]: {name}")
            logger.info("=" * 60)

            try:
                df = analyzer.run(config)
                if df is not None and len(df) > 0:
                    logger.info(f"  ✅ 分析完成并落库: {len(df)} rows")
                    # 最新交易日信号摘要
                    latest_date = df['trade_date'].max()
                    latest = df[df['trade_date'] == latest_date]
                    signal_counts = latest['trade_signal'].value_counts().to_dict()
                    logger.info(f"  最新交易日 {latest_date} 信号分布: {signal_counts}")
                    # 买方关键指标摘要
                    if 'capital_leverage' in latest.columns:
                        logger.info(f"  资金杠杆: mean={latest['capital_leverage'].mean():.1f}x, "
                                    f"max={latest['capital_leverage'].max():.1f}x")
                    if 'breakeven_required_upside_pct' in latest.columns:
                        logger.info(f"  回本所需涨幅: mean={latest['breakeven_required_upside_pct'].mean():.2f}%")
                    success_count += 1
                else:
                    logger.warning(f"  ⚠️ 数据为空，批次跳过")
                    skip_count += 1

            except Exception as e:
                logger.error(f"  ❌ 分析失败: {name}")
                logger.error(f"     错误信息: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                fail_count += 1

        # 总结
        logger.info("\n" + "=" * 80)
        logger.info("LongCallStrategyAnalysisTest 完成")
        logger.info(f"  成功: {success_count}, 跳过(空数据): {skip_count}, 失败: {fail_count}")
        logger.info(f"  目标表: tb_option_trading_strategy_long_call (strategy_type='LONG_CALL')")
        logger.info("=" * 80)


if __name__ == "__main__":
    test = LongCallStrategyAnalysisTest()
    test.run()

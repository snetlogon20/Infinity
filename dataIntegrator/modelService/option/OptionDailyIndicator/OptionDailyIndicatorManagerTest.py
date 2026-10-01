from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.modelService.option.OptionDailyIndicator.OptionDailyIndicatorManager import OptionDailyIndicatorManager
logger = CommonLib.logger

# ================================================================
# 运行入口
# ================================================================
if __name__ == "__main__":
    print("=" * 80)
    print("OptionDailyIndicatorManagerTest")
    print("=" * 80)

    # 定义测试配置：华夏上证50ETF期权（小合约），symbol like '510050%'
    # 每个 symbol_filter + call_put 组合为独立产品
    report_configs = [
        {
            "name": "华夏上证50ETF看涨欧式期权",
            "start_date": "20251222",
            #"end_date": "20260717",
            "end_date": CommonParameters.today,
            "call_put": "C",
            "exercise_type": "欧式",
            "symbol_filter": "510050%",
        },
        {
            "name": "华夏上证50ETF看跌欧式期权",
            "start_date": "20251222",
            #"end_date": "20260717",
            "end_date": CommonParameters.today,
            "call_put": "P",
            "exercise_type": "欧式",
            "symbol_filter": "510050%",
        },
    ]

    optionDailyIndicatorManager = OptionDailyIndicatorManager()

    # ---- 计算并保存指标数据 ----
    for idx, config in enumerate(report_configs, 1):
        logger.info("\n" + "=" * 80)
        logger.info(f" 开始计算 第 {idx}/{len(report_configs)} 个期权配置")
        logger.info(f"   配置名称: {config['name']}")
        logger.info("=" * 80)

        try:
            df_option_result = optionDailyIndicatorManager.run(
                start_date=config.get("start_date"),
                end_date=config.get("end_date"),
                call_put=config.get("call_put"),
                exercise_type=config.get("exercise_type"),
                symbol_filter=config.get("symbol_filter"),
            )
            logger.info(f"✅ 第 {idx} 个配置计算完成，记录数: {len(df_option_result)}")

        except Exception as e:
            logger.error(f"❌ 第 {idx} 个配置计算失败: {config['name']}")
            logger.error(f"   错误信息: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            continue

    logger.info("\n" + "=" * 80)
    logger.info("所有任务完成！")
    logger.info("=" * 80)

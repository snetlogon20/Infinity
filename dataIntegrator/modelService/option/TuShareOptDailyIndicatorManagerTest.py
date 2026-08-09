from datetime import datetime, timedelta

from dataIntegrator import CommonLib
from dataIntegrator.modelService.option.TuShareOptDailyIndicatorManager import TuShareOptDailyIndicatorManager
logger = CommonLib.logger

# ================================================================
# 运行入口
# ================================================================
if __name__ == "__main__":
    from dataIntegrator import CommonParameters

    print("=" * 80)
    print("TuShareOptDailyIndicatorServiceTest")
    print("=" * 80)

    # 定义测试配置
    report_configs = [
        {
            "name": "HO2612看涨欧式期权",
            "start_date": "20251222",
            "end_date": "20260717",
            "call_put": "C",
            "exercise_type": "欧式",
            "ts_code_filter": "HO2612%",
        },
    ]

    tuShareOptDailyIndicatorManager = TuShareOptDailyIndicatorManager()

    for idx, config in enumerate(report_configs, 1):
        logger.info("\n" + "=" * 80)
        logger.info(f" 开始测试第 {idx}/{len(report_configs)} 个期权配置")
        logger.info(f"   配置名称: {config['name']}")
        logger.info("=" * 80)

        try:
            df_option_result = tuShareOptDailyIndicatorManager.run(
                start_date=config.get("start_date"),
                end_date=config.get("end_date"),
                call_put=config.get("call_put"),
                exercise_type=config.get("exercise_type"),
                ts_code_filter=config.get("ts_code_filter"),
            )
            logger.info(f"✅ 第 {idx} 个配置测试完成，记录数: {len(df_option_result)}")

        except Exception as e:
            logger.error(f"❌ 第 {idx} 个配置测试失败: {config['name']}")
            logger.error(f"   错误信息: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            continue

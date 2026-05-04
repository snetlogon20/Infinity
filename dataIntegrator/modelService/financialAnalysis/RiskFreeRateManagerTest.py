from dataIntegrator.modelService.financialAnalysis.RiskFreeRateManager import RiskFreeRateManager
from dataIntegrator import CommonLib

logger = CommonLib.logger


class RiskFreeRateManagerTest:
    """
    无风险利率管理器测试类
    用于测试 RiskFreeRateManager 的各项功能
    """

    def __init__(self):
        logger.info("RiskFreeRateManagerTest initialized")

    def test_get_risk_free_rate_us(self):
        """
        测试获取美国国债收益率
        """
        logger.info("=" * 80)
        logger.info("测试1: 获取美国国债收益率 (US)")
        logger.info("=" * 80)

        start_date = "20250101"
        end_date = "20260401"

        riskFreeRateManager = RiskFreeRateManager()
        latest_yield = riskFreeRateManager.get_risk_free_rate(start_date, end_date, interest_country="US")

        logger.info(f"测试日期范围: {start_date} 到 {end_date}")
        logger.info(f"最新美国国债收益率: {latest_yield:.4f}")
        logger.info(f"测试结果: {'✅ 通过' if latest_yield > 0 else '❌ 失败'}")
        logger.info("")

        return latest_yield

    def test_get_risk_free_rate_cn(self):
        """
        测试获取中国 SHIBOR 利率
        """
        logger.info("=" * 80)
        logger.info("测试2: 获取中国 SHIBOR 利率 (CN)")
        logger.info("=" * 80)

        start_date = "20250101"
        end_date = "20260401"

        riskFreeRateManager = RiskFreeRateManager()
        latest_rate = riskFreeRateManager.get_risk_free_rate(start_date, end_date, interest_country="CN")

        logger.info(f"测试日期范围: {start_date} 到 {end_date}")
        logger.info(f"最新 SHIBOR 利率: {latest_rate:.4f}")
        logger.info(f"测试结果: {'✅ 通过' if latest_rate > 0 else '❌ 失败'}")
        logger.info("")

        return latest_rate

    def test_get_risk_free_rate_details_us(self):
        """
        测试获取美国国债收益率详细信息
        """
        logger.info("=" * 80)
        logger.info("测试3: 获取美国国债收益率详细信息 (US)")
        logger.info("=" * 80)

        start_date = "20250101"
        end_date = "20260401"

        riskFreeRateManager = RiskFreeRateManager()
        details = riskFreeRateManager.get_risk_free_rate_details(start_date, end_date, interest_country="US")

        logger.info(f"测试日期范围: {start_date} 到 {end_date}")
        logger.info(f"平均收益率: {details['avg_rate']:.4f}")
        logger.info(f"最早日期收益率: {details['earliest_rate']:.4f}")
        logger.info(f"最新日期收益率: {details['latest_rate']:.4f}")
        logger.info(f"最大收益率: {details['max_rate']:.4f}")
        logger.info(f"最小收益率: {details['min_rate']:.4f}")

        # 验证数据合理性
        is_valid = (
            details['avg_rate'] > 0 and
            details['latest_rate'] > 0 and
            details['min_rate'] <= details['avg_rate'] <= details['max_rate']
        )

        logger.info(f"测试结果: {'✅ 通过' if is_valid else '❌ 失败'}")
        logger.info("")

        return details

    def test_get_risk_free_rate_details_cn(self):
        """
        测试获取中国 SHIBOR 利率详细信息
        """
        logger.info("=" * 80)
        logger.info("测试4: 获取中国 SHIBOR 利率详细信息 (CN)")
        logger.info("=" * 80)

        start_date = "20250101"
        end_date = "20260401"

        riskFreeRateManager = RiskFreeRateManager()
        details = riskFreeRateManager.get_risk_free_rate_details(start_date, end_date, interest_country="CN")

        logger.info(f"测试日期范围: {start_date} 到 {end_date}")
        logger.info(f"平均利率: {details['avg_rate']:.4f}")
        logger.info(f"最早日期利率: {details['earliest_rate']:.4f}")
        logger.info(f"最新日期利率: {details['latest_rate']:.4f}")
        logger.info(f"最大利率: {details['max_rate']:.4f}")
        logger.info(f"最小利率: {details['min_rate']:.4f}")

        # 验证数据合理性
        is_valid = (
            details['avg_rate'] > 0 and
            details['latest_rate'] > 0 and
            details['min_rate'] <= details['avg_rate'] <= details['max_rate']
        )

        logger.info(f"测试结果: {'✅ 通过' if is_valid else '❌ 失败'}")
        logger.info("")

        return details

    def test_compare_us_cn_rates(self):
        """
        对比中美无风险利率
        """
        logger.info("=" * 80)
        logger.info("测试5: 对比中美无风险利率")
        logger.info("=" * 80)

        start_date = "20250101"
        end_date = "20260401"

        riskFreeRateManager = RiskFreeRateManager()

        # 获取美国国债收益率
        us_rate = riskFreeRateManager.get_risk_free_rate(start_date, end_date, interest_country="US")

        # 获取中国 SHIBOR 利率
        cn_rate = riskFreeRateManager.get_risk_free_rate(start_date, end_date, interest_country="CN")

        logger.info(f"测试日期范围: {start_date} 到 {end_date}")
        logger.info(f"美国国债收益率: {us_rate:.4f} ({us_rate * 100:.2f}%)")
        logger.info(f"中国 SHIBOR 利率: {cn_rate:.4f} ({cn_rate * 100:.2f}%)")
        logger.info(f"利差 (US - CN): {us_rate - cn_rate:.4f} ({(us_rate - cn_rate) * 100:.2f}%)")

        if us_rate > cn_rate:
            logger.info("结论: 美国国债收益率高于中国 SHIBOR 利率")
        elif us_rate < cn_rate:
            logger.info("结论: 中国 SHIBOR 利率高于美国国债收益率")
        else:
            logger.info("结论: 两者收益率相等")

        logger.info(f"测试结果: {'✅ 通过' if us_rate > 0 and cn_rate > 0 else '❌ 失败'}")
        logger.info("")

        return us_rate, cn_rate

    def test_different_time_periods(self):
        """
        测试不同时间段的无风险利率
        """
        logger.info("=" * 80)
        logger.info("测试6: 测试不同时间段的无风险利率")
        logger.info("=" * 80)

        riskFreeRateManager = RiskFreeRateManager()

        # 定义不同的时间段
        periods = [
            ("20240101", "20240331", "2024年第一季度"),
            ("20240401", "20240630", "2024年第二季度"),
            ("20240701", "20240930", "2024年第三季度"),
            ("20241001", "20241231", "2024年第四季度"),
            ("20250101", "20250331", "2025年第一季度"),
        ]

        results = []

        for start_date, end_date, period_name in periods:
            try:
                us_rate = riskFreeRateManager.get_risk_free_rate(start_date, end_date, interest_country="US")
                cn_rate = riskFreeRateManager.get_risk_free_rate(start_date, end_date, interest_country="CN")

                results.append({
                    'period': period_name,
                    'start_date': start_date,
                    'end_date': end_date,
                    'us_rate': us_rate,
                    'cn_rate': cn_rate,
                    'spread': us_rate - cn_rate
                })

                logger.info(f"{period_name}: US={us_rate:.4f} ({us_rate * 100:.2f}%), "
                          f"CN={cn_rate:.4f} ({cn_rate * 100:.2f}%), "
                          f"利差={us_rate - cn_rate:.4f} ({(us_rate - cn_rate) * 100:.2f}%)")

            except Exception as e:
                logger.error(f"{period_name} 测试失败: {str(e)}")
                results.append({
                    'period': period_name,
                    'start_date': start_date,
                    'end_date': end_date,
                    'us_rate': None,
                    'cn_rate': None,
                    'spread': None,
                    'error': str(e)
                })

        logger.info("")
        logger.info("汇总统计:")
        logger.info("-" * 80)

        valid_results = [r for r in results if r['us_rate'] is not None]
        if valid_results:
            avg_us_rate = sum(r['us_rate'] for r in valid_results) / len(valid_results)
            avg_cn_rate = sum(r['cn_rate'] for r in valid_results) / len(valid_results)
            avg_spread = sum(r['spread'] for r in valid_results) / len(valid_results)

            logger.info(f"平均美国国债收益率: {avg_us_rate:.4f} ({avg_us_rate * 100:.2f}%)")
            logger.info(f"平均中国 SHIBOR 利率: {avg_cn_rate:.4f} ({avg_cn_rate * 100:.2f}%)")
            logger.info(f"平均利差: {avg_spread:.4f} ({avg_spread * 100:.2f}%)")

        logger.info(f"测试结果: {'✅ 通过' if len(valid_results) > 0 else '❌ 失败'}")
        logger.info("")

        return results


if __name__ == '__main__':
    logger.info("\n" + "=" * 80)
    logger.info("开始执行 RiskFreeRateManager 测试套件")
    logger.info("=" * 80 + "\n")

    test_manager = RiskFreeRateManagerTest()

    try:
        # 测试1: 获取美国国债收益率
        us_rate = test_manager.test_get_risk_free_rate_us()

        # 测试2: 获取中国 SHIBOR 利率
        cn_rate = test_manager.test_get_risk_free_rate_cn()

        # 测试3: 获取美国国债收益率详细信息
        us_details = test_manager.test_get_risk_free_rate_details_us()

        # 测试4: 获取中国 SHIBOR 利率详细信息
        cn_details = test_manager.test_get_risk_free_rate_details_cn()

        # 测试5: 对比中美无风险利率
        us_rate_compare, cn_rate_compare = test_manager.test_compare_us_cn_rates()

        # 测试6: 测试不同时间段的无风险利率
        period_results = test_manager.test_different_time_periods()

        logger.info("\n" + "=" * 80)
        logger.info("✅ 所有测试执行完成！")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\n❌ 测试过程中发生异常: {str(e)}")
        import traceback
        traceback.print_exc()

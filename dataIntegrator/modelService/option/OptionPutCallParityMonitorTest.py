"""
Put-Call Parity 实时监控服务 - 测试入口

运行方式：
    python -m dataIntegrator.modelService.option.OptionPutCallParityMonitorTest

测试策略：
    1. 单日监控：指定 trade_date，验证 PCP 偏差计算和告警逻辑
    2. 打印 PCP 偏差统计、告警分布、股息噪声分解
"""

from datetime import datetime, timedelta

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.modelService.option.OptionPutCallParityMonitor import OptionPutCallParityMonitor

logger = CommonLib.logger


class OptionPutCallParityMonitorTest:
    """Put-Call Parity 监控测试类"""

    def __init__(self):
        self.monitor = OptionPutCallParityMonitor(
            lookback_days=20,
            alert_threshold=2.0,
            strong_alert_threshold=3.0,
            noise_ratio=0.70,
            q_min_uncertainty=0.005,
            min_volume=10,
        )
        logger.info("OptionPutCallParityMonitorTest initialized")

    def test_by_trade_date(self, trade_date=None):
        """单日监控测试

        Args:
            trade_date: 交易日 YYYYMMDD，默认 today
        """
        if trade_date is None:
            trade_date = CommonParameters.today

        logger.info("=" * 80)
        logger.info(f"PCP Monitor - Single Day Test: {trade_date}")
        logger.info("=" * 80)

        df_result = self.monitor.run(trade_date=trade_date)

        if len(df_result) == 0:
            logger.warning("No results returned, test completed without data")
            return df_result

        # ---- 验证输出 ----
        self._validate_results(df_result, trade_date)

        return df_result

    def test_by_date_range(self, start_date=None, end_date=None):
        """日期区间监控测试

        Args:
            start_date: 起始日期 YYYYMMDD
            end_date: 截止日期 YYYYMMDD
        """
        if end_date is None:
            end_date = CommonParameters.today
        if start_date is None:
            start_dt = datetime.strptime(end_date, '%Y%m%d') - timedelta(days=5)
            start_date = start_dt.strftime('%Y%m%d')

        logger.info("=" * 80)
        logger.info(f"PCP Monitor - Date Range Test: [{start_date}, {end_date}]")
        logger.info("=" * 80)

        df_result = self.monitor.run(start_date=start_date, end_date=end_date)

        if len(df_result) == 0:
            logger.warning("No results returned, test completed without data")
            return df_result

        self._validate_results(df_result, end_date)

        return df_result

    def _validate_results(self, df_result, ref_date):
        """验证监控结果并打印统计"""
        logger.info("\n" + "=" * 60)
        logger.info("VALIDATION & STATISTICS")
        logger.info("=" * 60)

        # 1. 基本统计
        logger.info(f"\nTotal pairs: {len(df_result)}")
        logger.info(f"Unique trade_dates: {df_result['trade_date'].nunique()}")
        logger.info(f"Unique underlyings: {df_result['underlying_code'].unique().tolist()}")

        # 2. PCP 偏差统计
        logger.info("\n--- PCP Deviation Statistics ---")
        eps = df_result['pcp_deviation'].dropna()
        if len(eps) > 0:
            logger.info(f"  Count: {len(eps)}")
            logger.info(f"  Mean:  {eps.mean():.4f}")
            logger.info(f"  Std:   {eps.std():.4f}")
            logger.info(f"  Min:   {eps.min():.4f}")
            logger.info(f"  Max:   {eps.max():.4f}")
            logger.info(f"  |ε| > 1.0: {(abs(eps) > 1.0).sum()} pairs")
            logger.info(f"  |ε| > 5.0: {(abs(eps) > 5.0).sum()} pairs")

        # 3. 告警统计
        logger.info("\n--- Alert Distribution ---")
        alert_dist = df_result['alert_level'].value_counts()
        for level, count in alert_dist.items():
            logger.info(f"  {level}: {count} pairs")

        # 4. 偏差类型分布
        logger.info("\n--- Deviation Type Distribution ---")
        type_dist = df_result['deviation_type'].value_counts()
        for dtype, count in type_dist.items():
            logger.info(f"  {dtype}: {count} pairs")

        # 5. z-score 统计
        logger.info("\n--- Z-Score Statistics ---")
        z = df_result['z_score'].dropna()
        if len(z) > 0:
            logger.info(f"  Mean:  {z.mean():.4f}")
            logger.info(f"  Std:   {z.std():.4f}")
            logger.info(f"  |z| > 2.0: {(abs(z) > 2.0).sum()} pairs")
            logger.info(f"  |z| > 3.0: {(abs(z) > 3.0).sum()} pairs")

        # 6. 股息噪声分解
        logger.info("\n--- Dividend Noise Decomposition ---")
        div_contrib = df_result['dividend_contribution'].dropna()
        residual = df_result['residual_deviation'].dropna()
        if len(div_contrib) > 0:
            logger.info(f"  dividend_contribution mean: {div_contrib.mean():.4f}")
            logger.info(f"  residual_deviation mean:    {residual.mean():.4f}")

        # 7. 告警详情
        alert_df = df_result[df_result['alert_level'] != 'NORMAL']
        if len(alert_df) > 0:
            logger.warning(f"\n--- ALERT DETAILS ({len(alert_df)} pairs) ---")
            display_cols = ['trade_date', 'underlying_code', 'exercise_price',
                            'maturity_date', 'pcp_deviation', 'z_score',
                            'dividend_contribution', 'residual_deviation',
                            'alert_level', 'deviation_type']
            avail = [c for c in display_cols if c in alert_df.columns]
            logger.warning(f"\n{alert_df[avail].to_string(max_rows=50)}")
        else:
            logger.info("\n✅ No alerts detected - all PCP deviations within normal range")

        # 8. 样本数据
        logger.info("\n--- Sample Data (first 10 rows) ---")
        sample_cols = ['trade_date', 'underlying_code', 'exercise_price',
                        'pcp_deviation', 'pcp_deviation_pct', 'z_score',
                        'dividend_contribution', 'alert_level', 'deviation_type']
        avail_sample = [c for c in sample_cols if c in df_result.columns]
        logger.info(f"\n{df_result[avail_sample].head(10).to_string()}")

        logger.info("\n" + "=" * 60)
        logger.info("VALIDATION COMPLETED")
        logger.info("=" * 60)

    def run(self):
        """主测试入口：先单日监控，再区间验证"""
        logger.info("=" * 80)
        logger.info("OptionPutCallParityMonitorTest.run: Starting PCP monitor tests")
        logger.info("=" * 80)

        # Test 1: 单日监控（最近一个交易日）
        trade_date = CommonParameters.today
        logger.info(f"\n{'='*60}")
        logger.info(f"Test 1: Single Day Monitoring ({trade_date})")
        logger.info(f"{'='*60}")
        df1 = self.test_by_trade_date(trade_date=trade_date)

        logger.info("\n" + "=" * 80)
        logger.info("All tests completed!")
        logger.info("=" * 80)

        return df1


if __name__ == "__main__":
    test = OptionPutCallParityMonitorTest()
    test.run()

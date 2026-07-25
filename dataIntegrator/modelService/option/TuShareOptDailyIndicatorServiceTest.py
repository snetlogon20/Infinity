"""
期权日线指标计算服务 - 测试入口

运行方式：
    python -m dataIntegrator.modelService.option.TuShareOptDailyIndicatorServiceTest

测试策略：
    1. 先拉取少量数据进行验证
    2. 打印各个指标的分位数/分布
    3. 不写入 ClickHouse（dry-run 模式）
"""

import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.modelService.option.TuShareOptDailyIndicatorService import TuShareOptDailyIndicatorService

logger = CommonLib.logger
commonLib = CommonLib()


class TuShareOptDailyIndicatorServiceTest:
    """期权日线指标计算服务测试类"""

    def __init__(self):
        self.service = TuShareOptDailyIndicatorService()
        self.writeLogInfo(
            className=self.__class__.__name__,
            functionName=sys._getframe().f_code.co_name,
            event="Test initialized"
        )

    def writeLogInfo(self, className="unknown", functionName="unknown", event="unknown"):
        print("%s.%s: %s" % (className, functionName, event))
        logger.info("%s.%s: %s" % (className, functionName, event))

    def test_run(self, start_date=None, end_date=None, dry_run=True):
        """运行测试

        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            dry_run: 是否只计算不写入（默认 True）
        """
        self.writeLogInfo(
            className=self.__class__.__name__,
            functionName=sys._getframe().f_code.co_name,
            event="=" * 80
        )
        self.writeLogInfo(
            className=self.__class__.__name__,
            functionName=sys._getframe().f_code.co_name,
            event="🧪 Starting TuShareOptDailyIndicatorServiceTest"
        )
        self.writeLogInfo(
            className=self.__class__.__name__,
            functionName=sys._getframe().f_code.co_name,
            event="=" * 80
        )

        if end_date is None:
            end_date = CommonParameters.today  # e.g., 20260719
        if start_date is None:
            # 默认取近 30 天（确保覆盖样本数据 20260717）
            start_dt = datetime.strptime(end_date, '%Y%m%d') - timedelta(days=30)
            start_date = start_dt.strftime('%Y%m%d')

        logger.info(f"Test date range: {start_date} ~ {end_date}")
        logger.info(f"Dry-run mode: {dry_run}")

        # ---- Step 1: 拉取数据 ----
        logger.info("\n📥 Step 1: Fetching data...")
        df = self.service.fetch_data(start_date=start_date, end_date=end_date)
        logger.info(f"Fetched {len(df)} rows, {len(df.columns)} columns")

        if len(df) == 0:
            logger.warning("No data fetched, test aborted")
            return df

        # 打印原始数据概览
        logger.info("\n原始数据前 5 行（关键列）:")
        key_cols = ['ts_code', 'trade_date', 'call_put', 'exercise_price',
                    'opt_multiplier', 'close', 'spot_price', 'maturity_date']
        available_key_cols = [c for c in key_cols if c in df.columns]
        logger.info(f"\n{df[available_key_cols].head().to_string()}")

        # ---- Step 2: 分步计算并验证 ----
        logger.info("\n🧮 Step 2: Calculating indicators step by step...")

        # 2a: 盘面硬指标
        logger.info("\n--- Level 1: Trading P&L ---")
        df = self.service._calc_trading_metrics(df)
        trading_cols = ['mtm_pnl_close', 'mtm_pnl_settle', 'point_change',
                        'pct_change', 'turnover_ratio', 'avg_unit_price']
        logger.info(f"Sample:\n{df[trading_cols].head(10).to_string()}")
        logger.info(f"NaN counts:\n{df[trading_cols].isna().sum()}")

        # 2b: 时间指标
        logger.info("\n--- Level 2: Time Metrics ---")
        df = self.service._calc_time_metrics(df)
        time_cols = ['days_to_maturity', 'years_to_maturity_calendar', 'years_to_maturity_trading']
        logger.info(f"Sample:\n{df[time_cols].head(10).to_string()}")
        logger.info(f"Stats:\n{df[time_cols].describe()}")

        # 2c: 价态
        logger.info("\n--- Level 3: Moneyness ---")
        df = self.service._calc_moneyness(df)
        money_cols = ['moneyness_status', 'moneyness_log']
        logger.info(f"Sample:\n{df[money_cols].head(10).to_string()}")
        logger.info(f"Status distribution:\n{df['moneyness_status'].value_counts()}")

        # 2d: 隐含波动率 & Greeks
        logger.info("\n--- Level 4 & 5: Implied Vol & Greeks ---")
        df = self.service._calc_implied_vol_and_greeks(df)
        greek_cols = ['implied_vol', 'bs_theoretical_price',
                       'delta', 'gamma', 'vega', 'theta', 'rho']
        logger.info(f"Sample:\n{df[['ts_code', 'trade_date', 'call_put', 'spot_price', 'close'] + greek_cols].head(10).to_string()}")
        logger.info(f"IV stats:\n{df['implied_vol'].describe()}")
        iv_count = df['implied_vol'].notna().sum()
        logger.info(f"IV computed for {iv_count}/{len(df)} rows")

        # ---- 验证示例数据（与用户提供的样例对照） ----
        logger.info("\n--- Sample Validation ---")
        sample = df[df['ts_code'].str.contains('HO2612', na=False)]
        if len(sample) > 0:
            row = sample.iloc[0]
            logger.info(f"Contract: {row['ts_code']}, Trade Date: {row['trade_date']}")
            logger.info(f"  Expected mtm_pnl_close (311.4-370)*100 = -5860, Got: {row['mtm_pnl_close']:.1f}")
            logger.info(f"  Expected mtm_pnl_settle (314-372)*100 = -5800, Got: {row['mtm_pnl_settle']:.1f}")
            logger.info(f"  Expected point_change 311.4-370 = -58.6, Got: {row['point_change']:.1f}")
            logger.info(f"  Expected pct_change (311.4/370-1)*100 = -15.84%, Got: {row['pct_change']:.2f}%")
            logger.info(f"  Days to maturity (20261218-20260717) = 154, Got: {row['days_to_maturity']}")

        # ---- Step 3: 保存（仅非 dry-run） ----
        if not dry_run:
            logger.info("\n💾 Step 3: Saving to ClickHouse...")
            self.service.save_to_clickhouse(df)
        else:
            logger.info("\n💾 Step 3: Skipped (dry-run mode)")

        logger.info("\n" + "=" * 80)
        logger.info("✅ Test completed!")
        if dry_run:
            logger.info("   Dry-run: data was NOT written to ClickHouse")
        logger.info("=" * 80)

        return df

    def test_single_contract(self, ts_code="HO2612-C-2500.CFX", trade_date="20260717"):
        """测试单个合约的指标计算（精确验证）"""
        logger.info(f"\n--- Single Contract Test: {ts_code} @ {trade_date} ---")

        df = self.service.fetch_data(start_date=trade_date, end_date=trade_date)
        if len(df) == 0:
            logger.warning(f"No data for {ts_code} @ {trade_date}")
            return None

        df = df[df['ts_code'] == ts_code]
        if len(df) == 0:
            logger.warning(f"Contract {ts_code} not found in fetched data")
            return None

        logger.info(f"Raw data:\n{df.to_string()}")

        # 全量计算
        df = self.service.calculate_indicators(df)

        logger.info(f"\nCalculated indicators:")
        for col in df.columns:
            val = df.iloc[0][col]
            logger.info(f"  {col}: {val}")

        return df


# ================================================================
# 运行入口
# ================================================================
if __name__ == "__main__":
    print("=" * 80)
    print("TuShareOptDailyIndicatorServiceTest")
    print("=" * 80)

    tester = TuShareOptDailyIndicatorServiceTest()

    # 默认：写入 ClickHouse
    df = tester.test_run(dry_run=False)

    # 如需精确验证某个合约，取消注释以下行：
    # tester.test_single_contract(ts_code="HO2612-C-2500.CFX", trade_date="20260717")

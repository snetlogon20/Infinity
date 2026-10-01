"""
期权日线指标计算服务 - 测试入口

运行方式：
    python -m dataIntegrator.modelService.option.OptionDailyIndicatorManagerTest

测试策略：
    1. 先拉取少量数据进行验证
    2. 打印各个指标的分位数/分布
"""

from datetime import datetime, timedelta

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.modelService.option.OptionDailyIndicator.OptionDailyIndicatorAnalyst import OptionDailyIndicatorAnalyst

logger = CommonLib.logger


class OptionDailyIndicatorManager:
    """期权日线指标计算服务测试类
    TuShareOptDailyIndicatorServiceTest  计算Option  各项数据及Greeks指标
    输入：df_tushare_opt_daily
    逻辑：OptDailyIndicatorReport - 根据 TuShareOptDailyIndicatorServiceTest 的数据出具最基础的Option分析报表
    输出：indexsysdb.tb_tushare_opt_daily_indicator
    """

    def __init__(self):
        self.service = OptionDailyIndicatorAnalyst()
        logger.info("OptionDailyIndicatorManager.__init__: initialized")

    def run(self, start_date=None, end_date=None,
                 call_put=None, exercise_type=None, ts_code_filter=None):
        """运行测试

        Args:
            start_date: 期权日线 & 指数行情起始日期 YYYYMMDD
            end_date: 期权日线 & 指数行情截止日期 YYYYMMDD
            call_put: 行权方向 'C'/'P'，None 不过滤
            exercise_type: 行权方式 '欧式'/'美式'，None 不过滤
            ts_code_filter: 合约代码过滤（LIKE），如 'HO2612%'
        """
        logger.info("=" * 80)
        logger.info("OptionDailyIndicatorManager.run: Starting")
        logger.info("=" * 80)

        if end_date is None:
            end_date = CommonParameters.today  # e.g., 20260719
        if start_date is None:
            # 默认取近 30 天
            start_dt = datetime.strptime(end_date, '%Y%m%d') - timedelta(days=30)
            start_date = start_dt.strftime('%Y%m%d')

        logger.info(f"Test date range: {start_date} ~ {end_date}")

        # ---- Step 1: 拉取数据 ----
        logger.info("\n📥 Step 1: Fetching data...")
        df_option_data = self.service.fetch_data(
            start_date=start_date, end_date=end_date,
            call_put=call_put, exercise_type=exercise_type, ts_code_filter=ts_code_filter
        )
        logger.info(f"Fetched {len(df_option_data)} rows, {len(df_option_data.columns)} columns")

        if len(df_option_data) == 0:
            logger.warning("No data fetched, test aborted")
            return df_option_data

        # 打印原始数据概览
        logger.info("\n原始数据前 5 行（关键列）:")
        key_cols = ['ts_code', 'trade_date', 'call_put', 'exercise_price',
                    'opt_multiplier', 'close', 'spot_price', 'maturity_date']
        available_key_cols = [c for c in key_cols if c in df_option_data.columns]
        logger.info(f"\n{df_option_data[available_key_cols].head().to_string()}")

        # ---- Step 2: 分步计算并验证 ----
        logger.info("\n🧮 Step 2: Calculating indicators step by step...")

        # 2a: 盘面硬指标
        logger.info("\n--- Level 1: Trading P&L ---")
        df_option_data = self.service._calc_trading_metrics(df_option_data)
        trading_cols = ['mtm_pnl_close', 'mtm_pnl_settle', 'point_change',
                        'pct_change', 'turnover_ratio', 'avg_unit_price']
        logger.info(f"Sample:\n{df_option_data[trading_cols].head(10).to_string()}")
        logger.info(f"NaN counts:\n{df_option_data[trading_cols].isna().sum()}")

        # 2b: 时间指标
        logger.info("\n--- Level 2: Time Metrics ---")
        df_option_data = self.service._calc_time_metrics(df_option_data)
        time_cols = ['days_to_maturity', 'years_to_maturity_calendar', 'years_to_maturity_trading']
        logger.info(f"Sample:\n{df_option_data[time_cols].head(10).to_string()}")
        logger.info(f"Stats:\n{df_option_data[time_cols].describe()}")

        # 2c: 价态
        logger.info("\n--- Level 3: Moneyness ---")
        df_option_data = self.service._calc_moneyness(df_option_data)
        money_cols = ['moneyness_status', 'moneyness_log']
        logger.info(f"Sample:\n{df_option_data[money_cols].head(10).to_string()}")
        logger.info(f"Status distribution:\n{df_option_data['moneyness_status'].value_counts()}")

        # 2d: 隐含波动率 & Greeks（先拉取 SHIBOR 作为无风险利率，再拉取股息率 q）
        logger.info("\n--- Fetching SHIBOR data for risk-free rate ---")
        shibor_dict = self.service._fetch_shibor_data(start_date, end_date)

        logger.info("\n--- Fetching index daily basic data for dividend yield q ---")
        dividend_yield_dict = self.service._fetch_dividend_yield_data(start_date, end_date)

        logger.info("\n--- Level 4 & 5: Implied Vol & Greeks ---")
        df_option_data = self.service._calc_implied_vol_and_greeks(
            df_option_data, shibor_dict=shibor_dict, dividend_yield_dict=dividend_yield_dict
        )
        greek_cols = ['implied_vol', 'bs_theoretical_price',
                       'd1', 'd2', 'nd1', 'nd2',
                       'delta', 'gamma', 'vega', 'theta', 'rho']
        logger.info(f"Sample:\n{df_option_data[['ts_code', 'trade_date', 'call_put', 'spot_price', 'close'] + greek_cols].head(10).to_string()}")
        logger.info(f"IV stats:\n{df_option_data['implied_vol'].describe()}")
        iv_count = df_option_data['implied_vol'].notna().sum()
        logger.info(f"IV computed for {iv_count}/{len(df_option_data)} rows")

        # ---- 验证示例数据（用实际数据做自洽性检查） ----
        logger.info("\n--- Sample Validation ---")
        # 选一个有 IV 的行做完整自洽验证
        valid_iv = df_option_data[df_option_data['implied_vol'].notna()]
        if len(valid_iv) > 0:
            sample_row = valid_iv.iloc[0]
            c = sample_row['close']
            pc = sample_row['pre_close']
            s = sample_row['settle']
            ps = sample_row['pre_settle']
            mul = sample_row['opt_multiplier']
            logger.info(f"Contract: {sample_row['ts_code']}, Trade Date: {sample_row['trade_date']}")
            logger.info(f"  close={c:.1f}, pre_close={pc:.1f}, settle={s:.1f}, pre_settle={ps:.1f}, multiplier={mul}")
            logger.info(f"  mtm_pnl_close = ({c:.1f} - {pc:.1f}) * {mul} = {(c - pc) * mul:.1f}, Computed: {sample_row['mtm_pnl_close']:.1f}")
            logger.info(f"  mtm_pnl_settle = ({s:.1f} - {ps:.1f}) * {mul} = {(s - ps) * mul:.1f}, Computed: {sample_row['mtm_pnl_settle']:.1f}")
            logger.info(f"  point_change = {c:.1f} - {pc:.1f} = {c - pc:.1f}, Computed: {sample_row['point_change']:.1f}")
            logger.info(f"  pct_change = ({c:.1f}/{pc:.1f} - 1) * 100 = {(c/pc - 1)*100:.2f}%, Computed: {sample_row['pct_change']:.2f}%")
            logger.info(f"  days_to_maturity = maturity_date - trade_date, Computed: {sample_row['days_to_maturity']}")
            logger.info(f"  implied_vol: {sample_row['implied_vol']:.6f}, delta: {sample_row['delta']:.4f}, gamma: {sample_row['gamma']:.6f}")
            logger.info(f"  d1: {sample_row['d1']:.6f}, d2: {sample_row['d2']:.6f}, N(d1): {sample_row['nd1']:.6f}, N(d2): {sample_row['nd2']:.6f}")

        # ---- 保存前检查：打印最后几条记录的关键字段 ----
        logger.info("\n🔍 保存前最后 5 条记录 (risk_free_rate / dividend_yield / spot_price 相关字段):")
        debug_cols = ['trade_date', 'ts_code', 'days_to_maturity',
                       'risk_free_rate', 'dividend_yield', 'spot_price', 'rho']
        avail_debug_cols = [c for c in debug_cols if c in df_option_data.columns]
        logger.info(f"\n{df_option_data[avail_debug_cols].tail(5).to_string()}")

        rf_unique = df_option_data['risk_free_rate'].dropna().unique()
        logger.info(f"risk_free_rate 唯一值: {sorted(rf_unique)}")
        logger.info(f"risk_free_rate 分布: {df_option_data['risk_free_rate'].value_counts().head(10).to_string()}")

        if 'dividend_yield' in df_option_data.columns:
            dy_unique = df_option_data['dividend_yield'].dropna().unique()
            logger.info(f"dividend_yield 唯一值: {sorted(dy_unique)}")
            logger.info(f"dividend_yield 分布: {df_option_data['dividend_yield'].value_counts().head(10).to_string()}")
            dy_nonzero = (df_option_data['dividend_yield'] > 0).sum()
            dy_zero = (df_option_data['dividend_yield'] == 0).sum()
            dy_nan = df_option_data['dividend_yield'].isna().sum()
            logger.info(f"dividend_yield 统计: 非零={dy_nonzero}, 零={dy_zero}, NaN={dy_nan}, 总计={len(df_option_data)}")
        else:
            logger.warning("dividend_yield 列不存在！")

        # ---- Step 3: 保存 ----
        logger.info("\n💾 Step 3: Saving to ClickHouse...")
        self.service.save_to_clickhouse(df_option_data, call_put=call_put, ts_code_filter=ts_code_filter)

        logger.info("\n" + "=" * 80)
        logger.info("✅ Test completed!")
        logger.info("=" * 80)

        return df_option_data
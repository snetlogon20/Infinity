r"""
Long Call 策略分析器 — 专业交易员视角

策略定义：买现货 + 买 Call（Spot + Long Call）
核心假设：到期标的价格 S_T = K（行权价）
核心问题：到期时，现货收益能否覆盖 Call 的权利金成本？

交易员核心关注：
  1. cost_efficiency（收益成本比）= (K - S₀) / C  —  >1 才赚钱
  2. delta_weighted_pnl（概率加权盈亏）         —  期望收益
  3. theta_cost_total（时间衰减总成本）          —  持有成本
  4. close_vs_theoretical（贵还是便宜）          —  定价偏差
  5. multi_scenario_pnl（多情景盈亏）            —  不止看 K，还看超越 K 的情景

数据源：
  - tb_tushare_opt_daily_indicator (含 BSM IV、Greeks)
  - vw_tushare_opt_daily (补充 name/exchange 等字段)

输出：Excel 报表 → D:\workspace_python\infinity_data\outbound\report\OptDailyIndicator\
"""

import os
import math
import numpy as np
import pandas as pd
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side, numbers
)
from openpyxl.utils import get_column_letter

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

logger = CommonLib.logger


class OptionCallStrategyAnalyzer:
    """Long Call 策略分析器

    分析：买入标的现货 + 买入看涨期权，到期时标的价格达到行权价 K 时的盈亏情况。
    """

    # === 表名常量 ===
    TABLE_INDICATOR = 'tb_tushare_opt_daily_indicator'
    TABLE_DAILY_VIEW = 'vw_tushare_opt_daily'

    # === 合约前缀 → 标的指数代码映射 ===
    CONTRACT_INDEX_MAP = {
        'HO': '000016.SH',
        'IO': '000300.SH',
        'MO': '000852.SH',
    }

    # === 输出路径 ===
    REPORT_DIR = os.path.join(CommonParameters.reportPath, 'OptDailyIndicator')

    # === 多情景系数 ===
    DEFAULT_SCENARIOS = [1.00, 1.03, 1.05, 1.08, 1.10, 1.15, 1.20]

    # === Excel 样式常量 ===
    HEADER_FILL = PatternFill(start_color='1F4E79', end_color='1F4E79', fill_type='solid')
    HEADER_FONT = Font(name='Microsoft YaHei', size=10, bold=True, color='FFFFFF')
    BODY_FONT = Font(name='Microsoft YaHei', size=9)
    TITLE_FONT = Font(name='Microsoft YaHei', size=14, bold=True, color='1F4E79')
    SUBTITLE_FONT = Font(name='Microsoft YaHei', size=11, bold=True, color='2E75B6')
    GREEN_FILL = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
    RED_FILL = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
    YELLOW_FILL = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')
    LIGHT_BLUE_FILL = PatternFill(start_color='BDD7EE', end_color='BDD7EE', fill_type='solid')
    THIN_BORDER = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9'),
    )
    CENTER_ALIGN = Alignment(horizontal='center', vertical='center', wrap_text=True)
    LEFT_ALIGN = Alignment(horizontal='left', vertical='center', wrap_text=True)

    # === 信号定义 ===
    SIGNAL_MAP = {
        'STRONG_BUY':  ('强烈买入', 'FF0000'),   # cost_efficiency > 1 且 市价 < 理论价
        'BUY':          ('买入', 'FF6600'),       # cost_efficiency > 1 但 市价 > 理论价
        'CONSIDER':     ('关注', 'FF9900'),       # cost_efficiency 0.95 ~ 1.0
        'NEUTRAL':      ('中性', '808080'),       # cost_efficiency 0.85 ~ 0.95
        'AVOID':        ('回避', '3399FF'),       # cost_efficiency < 0.85
    }

    def __init__(self):
        os.makedirs(self.REPORT_DIR, exist_ok=True)
        logger.info(f"OptionCallStrategyAnalyzer initialized. Report dir: {self.REPORT_DIR}")

    # ================================================================
    # Step 1: 数据拉取
    # ================================================================
    def fetch_data(self, start_date, end_date, call_put='C',
                   ts_code_filter=None, exercise_type=None):
        """从 indicator 表拉取数据，join vw_tushare_opt_daily 补充信息

        Args:
            start_date: 起始日期 YYYYMMDD
            end_date: 截止日期 YYYYMMDD
            call_put: 'C' 看涨 / 'P' 看跌
            ts_code_filter: LIKE 过滤，如 'HO2612%'
            exercise_type: 行权方式 '欧式'/'美式'，None 不过滤

        Returns:
            pd.DataFrame: 合并后的原始数据
        """
        logger.info("=" * 80)
        logger.info(f"Fetching option data: [{start_date}, {end_date}], "
                    f"call_put={call_put}, filter={ts_code_filter}, exercise_type={exercise_type}")

        where_clauses = [
            f"ind.trade_date >= '{start_date}'",
            f"ind.trade_date <= '{end_date}'",
        ]
        if call_put:
            where_clauses.append(f"ind.call_put = '{call_put}'")
        if ts_code_filter:
            where_clauses.append(f"ind.ts_code LIKE '{ts_code_filter}'")
        if exercise_type:
            where_clauses.append(f"v.exercise_type = '{exercise_type}'")

        where_str = "\n              AND ".join(where_clauses)

        # 从 indicator 表获取全量计算字段
        # join vw_tushare_opt_daily 获取 name, exchange, exercise_type 等补充字段
        sql = f"""
        SELECT
            ind.trade_date,
            ind.ts_code,
            ind.call_put,
            ind.exercise_price,
            ind.opt_multiplier,
            ind.s_month,
            ind.maturity_date,
            ind.pre_close,
            ind.close,
            ind.pre_settle,
            ind.settle,
            ind.open,
            ind.high,
            ind.low,
            ind.vol,
            ind.amount,
            ind.oi,
            ind.mtm_pnl_close,
            ind.mtm_pnl_settle,
            ind.point_change,
            ind.pct_change,
            ind.turnover_ratio,
            ind.avg_unit_price,
            ind.days_to_maturity,
            ind.years_to_maturity_calendar,
            ind.years_to_maturity_trading,
            ind.moneyness_status,
            ind.moneyness_log,
            ind.spot_price,
            ind.risk_free_rate,
            ind.dividend_yield,
            ind.implied_vol,
            ind.bs_theoretical_price,
            ind.delta,
            ind.gamma,
            ind.vega,
            ind.theta,
            ind.rho,
            ind.d1,
            ind.d2,
            ind.nd1,
            ind.nd2,
            v.name          AS opt_name,
            v.exchange      AS opt_exchange,
            v.exercise_type,
            v.list_date,
            v.delist_date
        FROM indexsysdb.{self.TABLE_INDICATOR} ind
        LEFT JOIN indexsysdb.{self.TABLE_DAILY_VIEW} v
            ON ind.ts_code = v.opt_daily_ts_code
           AND ind.trade_date = v.trade_date
        WHERE {where_str}
        ORDER BY ind.trade_date, ind.exercise_price
        """

        logger.info(f"SQL:\n{sql}")
        df_raw = ClickhouseService.getDataFrameWithoutColumnsName(sql)

        if len(df_raw) == 0:
            logger.warning("No data fetched, returning empty DataFrame")
            return pd.DataFrame()

        logger.info(f"Fetched {len(df_raw)} rows, {len(df_raw.columns)} columns")

        # 类型转换
        numeric_cols = [
            'exercise_price', 'opt_multiplier',
            'pre_close', 'close', 'pre_settle', 'settle', 'open', 'high', 'low',
            'vol', 'amount', 'oi',
            'mtm_pnl_close', 'mtm_pnl_settle', 'point_change', 'pct_change',
            'turnover_ratio', 'avg_unit_price',
            'days_to_maturity', 'years_to_maturity_calendar', 'years_to_maturity_trading',
            'moneyness_log', 'spot_price', 'risk_free_rate', 'dividend_yield',
            'implied_vol', 'bs_theoretical_price',
            'delta', 'gamma', 'vega', 'theta', 'rho',
            'd1', 'd2', 'nd1', 'nd2',
        ]
        for col in numeric_cols:
            if col in df_raw.columns:
                df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce')

        str_cols = ['trade_date', 'ts_code', 'call_put', 's_month', 'maturity_date',
                     'moneyness_status', 'opt_name', 'opt_exchange', 'exercise_type',
                     'list_date', 'delist_date']
        for col in str_cols:
            if col in df_raw.columns:
                df_raw[col] = df_raw[col].fillna('').astype(str)

        return df_raw

    # ================================================================
    # Step 2: 数据清洗与过滤
    # ================================================================
    def _clean_and_filter(self, df):
        """数据清洗：过滤无效行

        条件：
        - spot_price > 0 (有标的价格)
        - close > 0 (期权有成交价)
        - exercise_price > 0
        - exercise_price > spot_price (只看 OTM/ATM call，ITM 不做此假设)
        """
        before = len(df)

        # 移除无效行
        mask = (
            df['spot_price'].notna() & (df['spot_price'] > 0) &
            df['close'].notna() & (df['close'] > 0) &
            df['exercise_price'].notna() & (df['exercise_price'] > 0)
        )
        df = df[mask].copy()

        after = len(df)
        logger.info(f"Data cleaning: {before} -> {after} rows "
                    f"(removed {before - after} rows with missing S/K/close)")

        # 推导标的指数代码
        df['underlying_code'] = df['ts_code'].apply(self._get_underlying_code)

        return df

    @classmethod
    def _get_underlying_code(cls, ts_code):
        """从合约代码推导标的指数代码"""
        ts_str = str(ts_code).strip()
        for prefix, index_code in cls.CONTRACT_INDEX_MAP.items():
            if ts_str.startswith(prefix):
                return index_code
        return ''

    # ================================================================
    # Step 3: 核心盈亏计算
    # ================================================================
    def calc_strategy_pnl(self, df):
        """核心：Spot + Long Call 策略到期盈亏计算

        策略：买入现货 (S₀) + 买入看涨期权 (C, K)
        假设：到期 S_T = K
        到期价值 = S_T + max(0, S_T - K) = K + 0 = K
        策略成本 = S₀ + C
        策略盈亏 = K - S₀ - C

        cost_efficiency = (K - S₀) / C  — 核心指标，>1 才赚钱
        """
        logger.info("Calculating Long Call strategy P&L metrics...")

        S = df['spot_price'].values
        K = df['exercise_price'].values
        C = df['close'].values
        mult = df['opt_multiplier'].values
        days = df['days_to_maturity'].values.astype(float)
        years = df['years_to_maturity_calendar'].values.astype(float)
        delta = df['delta'].values.astype(float)
        theta = df['theta'].values.astype(float)
        iv = df['implied_vol'].values.astype(float)
        bs = df['bs_theoretical_price'].values.astype(float)

        # ---------- 1. 标的需要涨多少到 K ----------
        df['spot_to_strike'] = np.where(S > 0, K - S, np.nan)
        df['spot_to_strike_pct'] = np.where(S > 0, (K / S - 1) * 100, np.nan)
        df['K_S_ratio'] = np.where(S > 0, K / S, np.nan)

        # ---------- 2. 策略到期盈亏 (S_T = K) ----------
        # 标的价值 = K，期权价值 = max(0, K-K) = 0
        # 策略成本 = S₀ + C，策略盈亏 = K - S₀ - C
        df['spot_gain_at_K'] = np.where(S > 0, K - S, np.nan)     # 现货盈利
        df['call_payoff_at_K'] = 0.0                                # 期权到期价值 (ATM = 0)
        df['total_pnl_at_K'] = np.where(S > 0, K - S - C, np.nan)  # 组合净盈亏
        df['total_pnl_at_K_cny'] = df['total_pnl_at_K'] * mult

        # ---------- 3. 收益成本比 (核心!) ----------
        # 现货上涨空间 / 期权权利金
        df['cost_efficiency'] = np.where(
            (S > 0) & (C > 0),
            (K - S) / C,
            np.nan
        )
        # > 1: 现货涨幅覆盖了期权成本 → 赚钱
        # = 1: 刚好覆盖 → 保本
        # < 1: 覆盖不了 → 亏钱

        # ---------- 4. 盈亏平衡分析 ----------
        # 策略盈亏平衡条件: S_T + max(0, S_T-K) - S₀ - C = 0
        # 当 cost_efficiency < 1 时需要 S_T > K 才能盈利
        # 当 cost_efficiency >= 1 时 S_T = K 已盈利

        # 情况 A: S_T >= K (期权有内在价值)
        #   2·S_T - K - S₀ - C = 0  →  S_T_breakeven = (S₀ + K + C) / 2
        #   需要 S_T_breakeven >= K  →  S₀ + C >= K  (即 cost_efficiency <= 1)

        # 情况 B: S_T < K (期权到期作废)
        #   S_T - S₀ - C = 0  →  S_T_breakeven = S₀ + C
        #   需要 S_T_breakeven < K  →  S₀ + C < K  (即 cost_efficiency > 1)

        be_high = np.where(
            (S > 0) & (K > 0),
            (S + K + C) / 2.0,
            np.nan
        )
        be_low = np.where(S > 0, S + C, np.nan)
        # 根据 cost_efficiency 选择适用的盈亏平衡点
        df['breakeven_S_T'] = np.where(
            df['cost_efficiency'] <= 1.0,
            be_high,  # 需要 S_T > K
            be_low    # S_T < K 即可盈利
        )
        df['breakeven_S_T_pct'] = np.where(
            S > 0,
            (df['breakeven_S_T'] / S - 1) * 100,
            np.nan
        )
        df['breakeven_type'] = np.where(
            df['cost_efficiency'] <= 1.0,
            'S_T > K (期权有价值)',
            'S_T < K (期权作废亦可)'
        )

        # ---------- 5. 纯看涨期权盈亏 (不买现货) ----------
        df['pure_call_breakeven'] = np.where(K > 0, K + C, np.nan)
        df['pure_call_breakeven_pct'] = np.where(
            S > 0,
            (df['pure_call_breakeven'] / S - 1) * 100,
            np.nan
        )
        df['pure_call_max_loss'] = -C
        df['pure_call_max_loss_cny'] = -C * mult
        df['pure_call_max_loss_pct'] = -100.0

        # ---------- 6. 概率加权盈亏 (Delta 加权) ----------
        df['delta_weighted_pnl'] = np.where(
            pd.notna(delta),
            delta * df['total_pnl_at_K'],
            np.nan
        )
        df['delta_pct'] = delta * 100  # delta 转百分比展示

        # ---------- 7. 时间衰减成本 ----------
        df['theta_cost_daily'] = np.abs(theta)
        df['theta_cost_total'] = np.where(
            pd.notna(theta) & pd.notna(days),
            np.abs(theta) * days,
            np.nan
        )
        df['pnl_after_theta'] = np.where(
            pd.notna(df['theta_cost_total']),
            df['total_pnl_at_K'] - df['theta_cost_total'],
            np.nan
        )
        # Theta 成本占期权权利金比例
        df['theta_cost_pct_of_premium'] = np.where(
            (C > 0) & pd.notna(df['theta_cost_total']),
            df['theta_cost_total'] / C * 100,
            np.nan
        )

        # ---------- 8. 市场价 vs BS 理论价 ----------
        df['close_vs_theoretical'] = np.where(
            pd.notna(bs) & pd.notna(C),
            C - bs,
            np.nan
        )
        df['close_vs_theoretical_pct'] = np.where(
            (pd.notna(bs)) & (bs > 0),
            (C - bs) / bs * 100,
            np.nan
        )
        # 市价偏离信号
        df['price_bias'] = np.select(
            [
                df['close_vs_theoretical_pct'] < -5,
                (df['close_vs_theoretical_pct'] >= -5) & (df['close_vs_theoretical_pct'] < -1),
                (df['close_vs_theoretical_pct'] >= -1) & (df['close_vs_theoretical_pct'] <= 1),
                (df['close_vs_theoretical_pct'] > 1) & (df['close_vs_theoretical_pct'] <= 5),
                df['close_vs_theoretical_pct'] > 5,
            ],
            ['严重低估', '低估', '公允', '高估', '严重高估'],
            default='N/A'
        )

        # ---------- 9. 年化收益率 ----------
        df['annualized_return_pct'] = np.where(
            (C > 0) & (years > 0) & pd.notna(df['total_pnl_at_K']),
            df['total_pnl_at_K'] / C / years * 100,
            np.nan
        )

        # ---------- 10. 最大风险 ----------
        df['strategy_max_loss'] = -C
        df['strategy_max_loss_cny'] = -C * mult
        df['strategy_max_loss_pct_of_spot'] = np.where(
            S > 0,
            -C / S * 100,
            np.nan
        )

        # ---------- 11. 杠杆倍数 ----------
        # 期权资金撬动的现货名义价值
        df['leverage_notional'] = np.where(C > 0, S / C, np.nan)

        # ---------- 12. 交易信号 ----------
        df = self._assign_trade_signals(df)

        logger.info(f"Strategy P&L calculated for {len(df)} rows")
        valid = df['cost_efficiency'].notna().sum()
        if valid > 0:
            logger.info(f"  cost_efficiency: mean={df['cost_efficiency'].mean():.4f}, "
                        f"median={df['cost_efficiency'].median():.4f}, "
                        f"min={df['cost_efficiency'].min():.4f}, max={df['cost_efficiency'].max():.4f}")
            profitable = (df['cost_efficiency'] > 1.0).sum()
            logger.info(f"  Profitable (cost_efficiency > 1): {profitable}/{valid}")

        return df

    def _assign_trade_signals(self, df):
        """分配交易信号

        综合 cost_efficiency + 定价偏差 + IV 偏离度
        """
        ce = df['cost_efficiency'].values
        price_bias_pct = df['close_vs_theoretical_pct'].values
        iv = df['implied_vol'].values
        delta = df['delta'].values
        days = df['days_to_maturity'].values

        signals = np.full(len(df), 'AVOID', dtype=object)
        signal_reasons = np.full(len(df), '', dtype=object)

        for i in range(len(df)):
            ce_i = ce[i]
            bias_i = price_bias_pct[i]
            delta_i = delta[i]
            days_i = days[i]

            if pd.isna(ce_i):
                signals[i] = 'N/A'
                signal_reasons[i] = '数据不足'
                continue

            reasons = []

            if ce_i > 1.05:
                if pd.notna(bias_i) and bias_i < -1:
                    signals[i] = 'STRONG_BUY'
                    reasons.append(f'收益成本比={ce_i:.2f}>1.05')
                    reasons.append(f'低估{bias_i:.1f}%')
                else:
                    signals[i] = 'BUY'
                    reasons.append(f'收益成本比={ce_i:.2f}>1.05')
            elif ce_i > 1.00:
                signals[i] = 'BUY'
                reasons.append(f'收益成本比={ce_i:.2f}>1')
            elif ce_i > 0.95:
                signals[i] = 'CONSIDER'
                reasons.append(f'收益成本比={ce_i:.2f}>0.95')
            elif ce_i > 0.85:
                signals[i] = 'NEUTRAL'
                reasons.append(f'收益成本比={ce_i:.2f}')
            else:
                signals[i] = 'AVOID'
                reasons.append(f'收益成本比={ce_i:.2f}<0.85')

            # 补充理由
            if pd.notna(bias_i) and abs(bias_i) > 5:
                reasons.append('定价严重偏离BS理论价' if bias_i > 0 else '定价大幅低于理论价')
            if pd.notna(delta_i) and pd.notna(days_i) and days_i < 10:
                if abs(delta_i) < 0.2:
                    reasons.append('临近到期+深度虚值，风险极高')
            if pd.notna(days_i) and days_i < 5:
                reasons.append(f'仅剩{days_i:.0f}天到期')

            signal_reasons[i] = '; '.join(reasons)

        df['trade_signal'] = signals
        df['signal_reason'] = signal_reasons

        signal_counts = pd.Series(signals).value_counts()
        logger.info(f"Trade signals: {signal_counts.to_dict()}")

        return df

    # ================================================================
    # Step 4: 多情景盈亏
    # ================================================================
    def calc_scenario_pnl(self, df, scenarios=None):
        """多情景盈亏：标的价格达到 K 的不同倍数时的策略盈亏

        S_T = K * factor
        策略总价值 = S_T + max(0, S_T - K)
        策略总盈亏 = S_T + max(0, S_T - K) - S₀ - C

        Args:
            df: DataFrame
            scenarios: 情景因子列表，如 [1.0, 1.05, 1.10, 1.15, 1.20]
                       默认 DEFAULT_SCENARIOS

        Returns:
            pd.DataFrame: 在原 df 上追加情景列
        """
        if scenarios is None:
            scenarios = self.DEFAULT_SCENARIOS

        logger.info(f"Calculating multi-scenario P&L for {len(scenarios)} scenarios: {scenarios}")

        S = df['spot_price'].values
        K = df['exercise_price'].values
        C = df['close'].values
        mult = df['opt_multiplier'].values

        for factor in scenarios:
            s_T = K * factor  # 到期标的价格

            # 期权到期价值
            call_payoff = np.maximum(s_T - K, 0)

            # 策略总价值 = 标的价值 + 期权价值
            total_value = s_T + call_payoff

            # 策略总盈亏 = 总价值 - 成本(S₀ + C)
            total_pnl = total_value - S - C
            total_pnl_cny = total_pnl * mult

            label = f'{factor:.2f}'.replace('.', '_')
            col_pnl = f'scenario_pnl_{label}K'
            col_pnl_cny = f'scenario_pnl_{label}K_cny'
            col_pnl_pct = f'scenario_pnl_{label}K_pct'

            df[col_pnl] = total_pnl
            df[col_pnl_cny] = total_pnl_cny
            # 收益率 = 总盈亏 / (S₀ + C) 投入资金回报率
            df[col_pnl_pct] = np.where(
                (S > 0) & (C >= 0),
                total_pnl / (S + C) * 100,
                np.nan
            )

        # 纯期权盈亏 (不买现货，仅 Long Call)
        for factor in scenarios:
            s_T = K * factor
            call_payoff = np.maximum(s_T - K, 0)
            call_pnl = call_payoff - C
            call_pnl_cny = call_pnl * mult

            label = f'{factor:.2f}'.replace('.', '_')
            col_pnl = f'pure_call_pnl_{label}K'
            col_pnl_cny = f'pure_call_pnl_{label}K_cny'
            col_pnl_pct = f'pure_call_pnl_{label}K_pct'

            df[col_pnl] = call_pnl
            df[col_pnl_cny] = call_pnl_cny
            # 收益率 = 纯期权盈亏 / 权利金 C (投入资金仅为权利金)
            df[col_pnl_pct] = np.where(
                C > 0,
                call_pnl / C * 100,
                np.nan
            )

        logger.info("Multi-scenario P&L calculated")

        return df

    # ================================================================
    # Step 5: 导出 Excel
    # ================================================================
    def export_to_excel(self, df, config_name, start_date, end_date):
        """导出多 Sheet Excel 报表

        Sheet 1: "策略盈亏总览" — 核心指标排序表
        Sheet 2: "LongCall详细分析" — 完整字段明细
        Sheet 3: "多情景盈亏" — 不同 S_T 水平下的 P&L
        Sheet 4: "交易信号汇总" — 按信号分组统计
        Sheet 5: "当日数据分析" — 最新交易日快照透视表 (字段 × 合约)
        """
        if len(df) == 0:
            logger.warning("Empty DataFrame, nothing to export")
            return None

        # 文件名
        safe_name = config_name.replace(' ', '_').replace('/', '_')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{safe_name}_{start_date}_{end_date}_{timestamp}.xlsx'
        filepath = os.path.join(self.REPORT_DIR, filename)

        logger.info(f"Exporting Excel to: {filepath}")

        wb = Workbook()

        # ==================== Sheet 1: 策略盈亏总览 ====================
        ws1 = wb.active
        ws1.title = "策略盈亏总览"

        overview_cols = [
            'trade_date', 'ts_code', 'opt_name',
            'exercise_price', 'close', 'opt_multiplier',
            'days_to_maturity', 'maturity_date',
            'spot_price', 'K_S_ratio', 'moneyness_status',
            'implied_vol', 'delta', 'theta',
            'cost_efficiency',
            'total_pnl_at_K', 'total_pnl_at_K_cny',
            'breakeven_S_T', 'breakeven_S_T_pct',
            'delta_weighted_pnl',
            'theta_cost_total', 'pnl_after_theta',
            'close_vs_theoretical', 'close_vs_theoretical_pct', 'price_bias',
            'annualized_return_pct',
            'trade_signal', 'signal_reason',
        ]

        # 按 cost_efficiency 降序排列
        df_overview = df.sort_values('cost_efficiency', ascending=False, na_position='last')

        self._write_sheet_header(ws1, overview_cols,
                                 title=f'期权策略盈亏总览 — {config_name}',
                                 subtitle=f'数据区间: {start_date} ~ {end_date} | '
                                          f'共 {len(df_overview)} 条合约 | '
                                          f'策略: Spot + Long Call (假设到期 S_T = K)')

        self._write_data_rows(ws1, df_overview, overview_cols, start_row=4)

        # 条件格式
        self._apply_conditional_formatting(ws1, df_overview, overview_cols, start_row=4)

        # ==================== Sheet 2: LongCall详细分析 ====================
        ws2 = wb.create_sheet("LongCall详细分析")

        detail_cols = [
            'trade_date', 'ts_code', 'opt_name', 'opt_exchange',
            'call_put', 'exercise_price', 'opt_multiplier',
            's_month', 'maturity_date', 'days_to_maturity',
            'years_to_maturity_calendar',
            'spot_price', 'moneyness_status', 'moneyness_log',
            'risk_free_rate', 'dividend_yield',
            # 价格
            'open', 'high', 'low', 'close', 'settle', 'pre_close',
            'vol', 'amount', 'oi',
            'pct_change', 'turnover_ratio',
            # BS 定价
            'implied_vol', 'bs_theoretical_price',
            'close_vs_theoretical', 'close_vs_theoretical_pct', 'price_bias',
            # Greeks
            'delta', 'gamma', 'theta', 'vega', 'rho',
            'd1', 'd2', 'nd1', 'nd2',
            # 策略盈亏
            'spot_to_strike', 'spot_to_strike_pct', 'K_S_ratio',
            'cost_efficiency',
            'total_pnl_at_K', 'total_pnl_at_K_cny',
            'breakeven_S_T', 'breakeven_S_T_pct', 'breakeven_type',
            'pure_call_breakeven', 'pure_call_breakeven_pct',
            'delta_weighted_pnl',
            'theta_cost_daily', 'theta_cost_total', 'theta_cost_pct_of_premium',
            'pnl_after_theta', 'annualized_return_pct',
            'strategy_max_loss', 'strategy_max_loss_cny', 'strategy_max_loss_pct_of_spot',
            'leverage_notional',
            # 信号
            'trade_signal', 'signal_reason',
        ]

        self._write_sheet_header(ws2, detail_cols,
                                 title=f'Long Call 策略详细分析 — {config_name}',
                                 subtitle=f'数据区间: {start_date} ~ {end_date} | '
                                          f'共 {len(df)} 条合约')

        df_detail = df.sort_values(['trade_date', 'exercise_price'])
        self._write_data_rows(ws2, df_detail, detail_cols, start_row=4)

        # ==================== Sheet 3: 多情景盈亏 ====================
        ws3 = wb.create_sheet("多情景盈亏")

        scenario_cols_base = [
            'trade_date', 'ts_code', 'exercise_price', 'close',
            'spot_price', 'days_to_maturity', 'moneyness_status',
            'cost_efficiency', 'trade_signal',
        ]
        scenario_pnl_cols = []
        scenario_call_cols = []
        for factor in self.DEFAULT_SCENARIOS:
            label = f'{factor:.2f}'.replace('.', '_')
            scenario_pnl_cols.append(f'scenario_pnl_{label}K')
            scenario_pnl_cols.append(f'scenario_pnl_{label}K_cny')
            scenario_pnl_cols.append(f'scenario_pnl_{label}K_pct')
            scenario_call_cols.append(f'pure_call_pnl_{label}K')
            scenario_call_cols.append(f'pure_call_pnl_{label}K_cny')
            scenario_call_cols.append(f'pure_call_pnl_{label}K_pct')

        scenario_cols = scenario_cols_base + scenario_pnl_cols + scenario_call_cols

        self._write_sheet_header(ws3, scenario_cols,
                                 title=f'多情景盈亏分析 — {config_name}',
                                 subtitle=f'情景: S_T = K × {self.DEFAULT_SCENARIOS} | '
                                          f'策略: Spot + Long Call 组合')

        df_scenario = df_overview.copy()
        self._write_data_rows(ws3, df_scenario, scenario_cols, start_row=4)

        # 为情景 P&L 列添加条件格式
        self._apply_scenario_formatting(ws3, df_scenario, scenario_pnl_cols, start_row=4)

        # ==================== Sheet 4: 交易信号汇总 ====================
        ws4 = wb.create_sheet("交易信号汇总")

        signal_cols = [
            'trade_date', 'ts_code', 'opt_name',
            'exercise_price', 'close', 'opt_multiplier',
            'spot_price', 'K_S_ratio', 'moneyness_status',
            'days_to_maturity',
            'cost_efficiency', 'total_pnl_at_K', 'total_pnl_at_K_cny',
            'delta', 'implied_vol',
            'close_vs_theoretical_pct', 'price_bias',
            'annualized_return_pct',
            'trade_signal', 'signal_reason',
        ]

        self._write_sheet_header(ws4, signal_cols,
                                 title=f'交易信号汇总 — {config_name}',
                                 subtitle=f'按信号强度排序 | 数据区间: {start_date} ~ {end_date}')

        # 按信号排序: STRONG_BUY > BUY > CONSIDER > NEUTRAL > AVOID
        signal_order = {'STRONG_BUY': 0, 'BUY': 1, 'CONSIDER': 2,
                         'NEUTRAL': 3, 'AVOID': 4, 'N/A': 5}
        df_signal = df.copy()
        df_signal['_signal_rank'] = df_signal['trade_signal'].map(signal_order).fillna(99)
        df_signal = df_signal.sort_values(['_signal_rank', 'cost_efficiency'],
                                          ascending=[True, False])

        self._write_data_rows(ws4, df_signal, signal_cols, start_row=4)

        # ==================== Sheet 5: 当日数据分析 ====================
        ws5 = wb.create_sheet("当日数据分析")
        self._write_daily_pivot_sheet(ws5, df, config_name)

        # ==================== 保存 ====================
        wb.save(filepath)
        logger.info(f"Excel report saved: {filepath}")

        # 打印摘要
        self._print_summary(df)

        return filepath

    def _write_sheet_header(self, ws, columns, title='', subtitle=''):
        """写入 Sheet 标题和表头"""
        # 标题行
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(columns))
        title_cell = ws.cell(row=1, column=1, value=title)
        title_cell.font = self.TITLE_FONT
        title_cell.alignment = Alignment(horizontal='left', vertical='center')
        ws.row_dimensions[1].height = 30

        # 副标题行
        if subtitle:
            ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(columns))
            sub_cell = ws.cell(row=2, column=1, value=subtitle)
            sub_cell.font = self.SUBTITLE_FONT
            sub_cell.alignment = Alignment(horizontal='left', vertical='center')
            ws.row_dimensions[2].height = 22

        # 表头
        header_row = 3 if subtitle else 2
        for col_idx, col_name in enumerate(columns, 1):
            cell = ws.cell(row=header_row, column=col_idx, value=col_name)
            cell.font = self.HEADER_FONT
            cell.fill = self.HEADER_FILL
            cell.alignment = self.CENTER_ALIGN
            cell.border = self.THIN_BORDER
        ws.row_dimensions[header_row].height = 28

        # 冻结表头
        ws.freeze_panes = ws.cell(row=header_row + 1, column=1)

        # 自动筛选
        ws.auto_filter.ref = f'A{header_row}:{get_column_letter(len(columns))}{header_row}'

    def _write_data_rows(self, ws, df, columns, start_row=4):
        """写入数据行"""
        for row_idx, (_, row) in enumerate(df.iterrows()):
            excel_row = start_row + row_idx + 1
            for col_idx, col_name in enumerate(columns, 1):
                val = row.get(col_name)
                if isinstance(val, float) and (pd.isna(val) or np.isinf(val)):
                    val = None

                cell = ws.cell(row=excel_row, column=col_idx, value=val)
                cell.font = self.BODY_FONT
                cell.border = self.THIN_BORDER
                cell.alignment = self.CENTER_ALIGN

                # 数值格式
                fmt = self._resolve_number_format(col_name)
                if fmt and val is not None:
                    cell.number_format = fmt

    def _resolve_number_format(self, col_name):
        """根据列名解析 Excel 数值格式（多个 Sheet 复用）"""
        if col_name in ('pct_change', 'spot_to_strike_pct', 'breakeven_S_T_pct',
                        'pure_call_breakeven_pct', 'theta_cost_pct_of_premium',
                        'close_vs_theoretical_pct', 'annualized_return_pct',
                        'strategy_max_loss_pct_of_spot'):
            return '0.00"%"'
        if col_name in ('implied_vol', 'risk_free_rate', 'dividend_yield'):
            return '0.00%'
        if col_name in ('delta', 'gamma', 'theta', 'vega', 'rho',
                        'd1', 'd2', 'nd1', 'nd2'):
            return '0.0000'
        if col_name in ('cost_efficiency', 'K_S_ratio'):
            return '0.0000'
        if col_name in ('close', 'settle', 'open', 'high', 'low', 'pre_close',
                        'exercise_price', 'spot_price',
                        'spot_to_strike', 'total_pnl_at_K',
                        'breakeven_S_T', 'pure_call_breakeven',
                        'delta_weighted_pnl', 'theta_cost_daily',
                        'theta_cost_total', 'pnl_after_theta',
                        'bs_theoretical_price', 'close_vs_theoretical',
                        'spot_gain_at_K', 'strategy_max_loss', 'avg_unit_price'):
            return '#,##0.00'
        if col_name in ('mtm_pnl_close', 'mtm_pnl_settle',
                        'total_pnl_at_K_cny', 'strategy_max_loss_cny',
                        'pure_call_max_loss_cny'):
            return '#,##0'
        if 'scenario_pnl' in col_name or 'pure_call_pnl' in col_name:
            if '_pct' in col_name:
                return '0.00"%"'
            if '_cny' in col_name:
                return '#,##0'
            return '#,##0.00'
        if col_name == 'leverage_notional':
            return '0.0"x"'
        return None

    def _apply_conditional_formatting(self, ws, df, columns, start_row=4):
        """对 cost_efficiency、trade_signal 列应用条件格式"""
        n_rows = len(df)
        if n_rows == 0:
            return

        end_row = start_row + n_rows

        # 找到 cost_efficiency 列位置
        ce_col = None
        signal_col = None
        total_pnl_col = None
        for col_idx, col_name in enumerate(columns, 1):
            if col_name == 'cost_efficiency':
                ce_col = col_idx
            elif col_name == 'trade_signal':
                signal_col = col_idx
            elif col_name == 'total_pnl_at_K':
                total_pnl_col = col_idx

        # cost_efficiency 着色: >= 1 绿色, < 1 红色
        if ce_col:
            for row in range(start_row + 1, end_row + 1):
                cell = ws.cell(row=row, column=ce_col)
                val = cell.value
                if val is not None:
                    if val >= 1.0:
                        cell.fill = self.GREEN_FILL
                    elif val >= 0.85:
                        cell.fill = self.YELLOW_FILL
                    else:
                        cell.fill = self.RED_FILL

        # total_pnl_at_K 着色
        if total_pnl_col:
            for row in range(start_row + 1, end_row + 1):
                cell = ws.cell(row=row, column=total_pnl_col)
                val = cell.value
                if val is not None and isinstance(val, (int, float)):
                    if val > 0:
                        cell.fill = self.GREEN_FILL
                    elif val < 0:
                        cell.fill = self.RED_FILL

        # trade_signal 着色
        signal_fills = {
            'STRONG_BUY': PatternFill(start_color='FF0000', end_color='FF0000', fill_type='solid'),
            'BUY': PatternFill(start_color='FF6600', end_color='FF6600', fill_type='solid'),
            'CONSIDER': PatternFill(start_color='FFC000', end_color='FFC000', fill_type='solid'),
            'NEUTRAL': PatternFill(start_color='BDD7EE', end_color='BDD7EE', fill_type='solid'),
            'AVOID': PatternFill(start_color='D9D9D9', end_color='D9D9D9', fill_type='solid'),
        }
        signal_fonts = {
            'STRONG_BUY': Font(name='Microsoft YaHei', size=9, bold=True, color='FFFFFF'),
            'BUY': Font(name='Microsoft YaHei', size=9, bold=True, color='FFFFFF'),
            'CONSIDER': Font(name='Microsoft YaHei', size=9, bold=True),
        }

        if signal_col:
            for row in range(start_row + 1, end_row + 1):
                cell = ws.cell(row=row, column=signal_col)
                val = str(cell.value) if cell.value else ''
                if val in signal_fills:
                    cell.fill = signal_fills[val]
                if val in signal_fonts:
                    cell.font = signal_fonts[val]

    def _apply_scenario_formatting(self, ws, df, scenario_cols, start_row=4):
        """对多情景 P&L 列着色：盈利绿，亏损红"""
        n_rows = len(df)
        if n_rows == 0:
            return
        end_row = start_row + n_rows

        # 找到 scenario 列位置 (需要知道 columns 顺序)
        # 通过 sheet header 反查
        header_row = start_row - 1
        for col_idx in range(1, ws.max_column + 1):
            cell = ws.cell(row=header_row, column=col_idx)
            if cell.value and 'scenario_pnl_' in str(cell.value) and '_K' in str(cell.value):
                # scenario P&L 列, 跳过 _cny 和 _pct 列
                col_name = str(cell.value)
                is_cny = '_cny' in col_name
                is_pct = '_pct' in col_name
                if is_cny or is_pct:
                    continue
                for row in range(start_row + 1, end_row + 1):
                    c = ws.cell(row=row, column=col_idx)
                    val = c.value
                    if val is not None and isinstance(val, (int, float)):
                        if val > 0:
                            c.fill = self.GREEN_FILL
                        elif val < 0:
                            c.fill = self.RED_FILL

    def _build_daily_pivot_fields(self):
        """构建"当日数据分析"透视表的字段行列表（指标 × 合约）

        字段顺序与用户指定的报表一致，重复字段已去重。
        """
        fields = [
            # --- 策略核心指标 (来自 Sheet 1 策略盈亏总览) ---
            'trade_date', 'ts_code', 'exercise_price', 'close', 'opt_multiplier',
            'days_to_maturity', 'maturity_date', 'spot_price', 'K_S_ratio',
            'moneyness_status', 'implied_vol', 'delta', 'gamma', 'vega', 'rho',
            'theta', 'cost_efficiency', 'total_pnl_at_K', 'total_pnl_at_K_cny',
            'breakeven_S_T', 'breakeven_S_T_pct', 'delta_weighted_pnl',
            'theta_cost_total', 'pnl_after_theta',
            'close_vs_theoretical', 'close_vs_theoretical_pct', 'price_bias',
            'annualized_return_pct', 'trade_signal', 'signal_reason',
            # --- 行情与 BS 定价 (来自 Sheet 2 LongCall详细分析) ---
            'risk_free_rate', 'dividend_yield',
            'open', 'high', 'low', 'settle', 'pre_close',
            'vol', 'amount', 'oi', 'pct_change', 'turnover_ratio',
            'bs_theoretical_price', 'd1', 'd2', 'nd1', 'nd2',
            'spot_to_strike', 'spot_to_strike_pct',
        ]
        # --- 多情景组合盈亏 (来自 Sheet 3 多情景盈亏) ---
        for factor in self.DEFAULT_SCENARIOS:
            label = f'{factor:.2f}'.replace('.', '_')
            fields.append(f'scenario_pnl_{label}K')
            fields.append(f'scenario_pnl_{label}K_cny')
            fields.append(f'scenario_pnl_{label}K_pct')
        # --- 多情景纯期权盈亏 (不买现货) ---
        for factor in self.DEFAULT_SCENARIOS:
            label = f'{factor:.2f}'.replace('.', '_')
            fields.append(f'pure_call_pnl_{label}K')
            fields.append(f'pure_call_pnl_{label}K_cny')
            fields.append(f'pure_call_pnl_{label}K_pct')
        return fields

    def _write_daily_pivot_sheet(self, ws, df, config_name):
        """写入"当日数据分析"透视表：行 = 指标/字段，列 = 合约

        取最新交易日快照，合约按行权价升序排列，
        便于横向对比同一日期下不同行权价合约的指标。
        """
        if len(df) == 0:
            logger.warning("Empty DataFrame, skip daily pivot sheet")
            return

        # 最新交易日
        latest_date = str(df['trade_date'].max())
        df_latest = df[df['trade_date'] == latest_date].copy()
        df_latest = df_latest.sort_values('exercise_price', ascending=True)

        n_contracts = len(df_latest)
        if n_contracts == 0:
            logger.warning("No rows for latest trade date, skip daily pivot sheet")
            return
        n_cols = n_contracts + 1  # 第 1 列 = 指标名

        fields = self._build_daily_pivot_fields()

        # --- 标题 ---
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=n_cols)
        title_cell = ws.cell(row=1, column=1, value=f'当日数据分析 — {config_name}')
        title_cell.font = self.TITLE_FONT
        title_cell.alignment = Alignment(horizontal='left', vertical='center')
        ws.row_dimensions[1].height = 30

        # --- 副标题 ---
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=n_cols)
        sub_cell = ws.cell(
            row=2, column=1,
            value=f'最新交易日: {latest_date} | 共 {n_contracts} 个合约 | '
                  f'按行权价升序排列 | 行 = 指标, 列 = 合约'
        )
        sub_cell.font = self.SUBTITLE_FONT
        sub_cell.alignment = Alignment(horizontal='left', vertical='center')
        ws.row_dimensions[2].height = 22

        # --- 表头 (row 3): A3 = 指标, B3.. = ts_code ---
        header_row = 3
        h0 = ws.cell(row=header_row, column=1, value='指标/字段')
        h0.font = self.HEADER_FONT
        h0.fill = self.HEADER_FILL
        h0.alignment = self.CENTER_ALIGN
        h0.border = self.THIN_BORDER
        for col_idx, (_, row) in enumerate(df_latest.iterrows(), 2):
            cell = ws.cell(row=header_row, column=col_idx, value=str(row['ts_code']))
            cell.font = self.HEADER_FONT
            cell.fill = self.HEADER_FILL
            cell.alignment = self.CENTER_ALIGN
            cell.border = self.THIN_BORDER
        ws.row_dimensions[header_row].height = 28
        ws.freeze_panes = ws.cell(row=header_row + 1, column=1)

        # --- 数据行 ---
        start_row = header_row + 1
        for row_idx, field in enumerate(fields, start_row):
            name_cell = ws.cell(row=row_idx, column=1, value=field)
            name_cell.font = Font(name='Microsoft YaHei', size=9, bold=True)
            name_cell.alignment = self.LEFT_ALIGN
            name_cell.border = self.THIN_BORDER

            fmt = self._resolve_number_format(field)
            for col_idx, (_, row) in enumerate(df_latest.iterrows(), 2):
                val = row.get(field)
                if isinstance(val, float) and (pd.isna(val) or np.isinf(val)):
                    val = None
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.font = self.BODY_FONT
                cell.alignment = self.CENTER_ALIGN
                cell.border = self.THIN_BORDER
                if fmt and val is not None:
                    cell.number_format = fmt

            # 关键指标行着色
            self._paint_pivot_row(ws, row_idx, field, df_latest)

        # --- 列宽 ---
        ws.column_dimensions['A'].width = 30
        for col_idx in range(2, n_cols + 1):
            ws.column_dimensions[get_column_letter(col_idx)].width = 18

        # --- 备注 ---
        note_row = start_row + len(fields) + 1
        ws.merge_cells(start_row=note_row, start_column=1,
                       end_row=note_row, end_column=n_cols)
        note_cell = ws.cell(row=note_row, column=1, value=self._build_pivot_note())
        note_cell.font = Font(name='Microsoft YaHei', size=9, color='808080')
        note_cell.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
        ws.row_dimensions[note_row].height = 360

    def _paint_pivot_row(self, ws, row_idx, field, df_latest):
        """对当日透视表的特定指标行着色"""
        if field == 'cost_efficiency':
            for col_idx, (_, row) in enumerate(df_latest.iterrows(), 2):
                val = row.get(field)
                if isinstance(val, (int, float)) and not pd.isna(val):
                    cell = ws.cell(row=row_idx, column=col_idx)
                    if val >= 1.0:
                        cell.fill = self.GREEN_FILL
                    elif val >= 0.85:
                        cell.fill = self.YELLOW_FILL
                    else:
                        cell.fill = self.RED_FILL
        elif field == 'trade_signal':
            for col_idx, (_, row) in enumerate(df_latest.iterrows(), 2):
                val = str(row.get(field) or '')
                if val in self.SIGNAL_MAP:
                    cell = ws.cell(row=row_idx, column=col_idx)
                    if val == 'STRONG_BUY':
                        cell.fill = self.GREEN_FILL
                    elif val == 'BUY':
                        cell.fill = self.YELLOW_FILL
                    elif val == 'AVOID':
                        cell.fill = self.RED_FILL
        elif field.startswith('scenario_pnl_') or field.startswith('pure_call_pnl_'):
            # 只给盈亏金额列着色 (跳过 _cny / _pct)
            if field.endswith('_cny') or field.endswith('_pct'):
                return
            for col_idx, (_, row) in enumerate(df_latest.iterrows(), 2):
                val = row.get(field)
                if isinstance(val, (int, float)) and not pd.isna(val):
                    cell = ws.cell(row=row_idx, column=col_idx)
                    if val > 0:
                        cell.fill = self.GREEN_FILL
                    elif val < 0:
                        cell.fill = self.RED_FILL

    def _build_pivot_note(self):
        """当日数据分析 Sheet 的备注说明（字段作用 + 公式）"""
        lines = [
            '【当日数据分析 说明】',
            '本 Sheet 为最新交易日的快照透视表：行 = 指标/字段, 列 = 合约(按行权价升序)，便于横向对比同一日期不同行权价合约。',
            '',
            '【字段说明与公式】',
            'trade_date: 交易日期（取数据中最新有记录的日期）',
            'ts_code: 合约代码，如 HO2612-C-2500.CFX = 上证50指数(HO) 2612到期月 行权价2500 看涨(C)',
            'exercise_price K: 行权价;   close C: 期权收盘价(权利金);   opt_multiplier: 合约乘数',
            'days_to_maturity: 距到期自然日;   maturity_date: 到期日',
            'spot_price S0: 标的指数收盘价;   K_S_ratio = K / S0;   moneyness_status: 实值/平值/虚值',
            'implied_vol: 隐含波动率;   delta / gamma / vega / theta / rho: 期权希腊字母',
            'cost_efficiency = (K - S0) / C : 收益成本比，> 1 表示到期 S_T=K 时盈利',
            'total_pnl_at_K = K - S0 - C : 到期 S_T=K 时组合净盈亏;   total_pnl_at_K_cny = total_pnl_at_K × 乘数',
            'breakeven_S_T: 策略盈亏平衡标的价 (cost_efficiency<=1 时 = (S0+K+C)/2; >1 时 = S0+C);   '
            'breakeven_S_T_pct = (breakeven_S_T / S0 - 1) × 100%',
            'delta_weighted_pnl = delta × total_pnl_at_K : 概率加权期望盈亏',
            'theta_cost_total = |theta| × days_to_maturity : 持有到期总时间衰减成本;   '
            'pnl_after_theta = total_pnl_at_K - theta_cost_total',
            'close_vs_theoretical = close - bs_theoretical_price : 市价偏离 BS 理论价;   '
            'close_vs_theoretical_pct = (close - BS价) / BS价 × 100%',
            'price_bias: 定价偏离判定 (严重低估/低估/公允/高估/严重高估)',
            'annualized_return_pct = total_pnl_at_K / C / 剩余年限 × 100% : 年化收益率',
            'trade_signal: 交易信号 (STRONG_BUY/BUY/CONSIDER/NEUTRAL/AVOID);   signal_reason: 信号依据',
            'risk_free_rate: 无风险利率;   dividend_yield: 股息率 (BS 输入参数)',
            'open / high / low / close / settle / pre_close: 当日开盘/最高/最低/收盘/结算/前收',
            'vol / amount / oi: 成交量 / 成交额 / 持仓量;   pct_change / turnover_ratio: 涨跌幅 / 换手率',
            'bs_theoretical_price: BS 模型理论价;   d1 / d2 / nd1 / nd2: BS 公式中间量',
            'spot_to_strike = K - S0;   spot_to_strike_pct = (K / S0 - 1) × 100%',
            '',
            '【多情景盈亏公式】(S_T = K × 系数)',
            'scenario_pnl_1_xxK = S_T + max(0, S_T - K) - S0 - C : 组合盈亏 (Spot + Long Call)',
            'scenario_pnl_1_xxK_cny = scenario_pnl × 乘数',
            'scenario_pnl_1_xxK_pct = scenario_pnl / (S0 + C) × 100% : 组合收益率',
            'pure_call_pnl_1_xxK = max(0, S_T - K) - C : 纯期权盈亏 (不买现货)',
            'pure_call_pnl_1_xxK_cny = pure_call_pnl × 乘数',
            'pure_call_pnl_1_xxK_pct = pure_call_pnl / C × 100% : 权利金收益率',
            '',
            '【着色规则】cost_efficiency: 绿(≥1) / 黄(0.85~1) / 红(<0.85);  '
            'trade_signal: 绿=STRONG_BUY / 黄=BUY / 红=AVOID;  盈亏列: 绿=盈利 / 红=亏损',
        ]
        return '\n'.join(lines)

    def _print_summary(self, df):
        """打印分析摘要到日志"""
        total = len(df)
        valid = df['cost_efficiency'].notna().sum()

        logger.info("=" * 60)
        logger.info("  策略分析摘要")
        logger.info("=" * 60)
        logger.info(f"  总合约数: {total}")
        logger.info(f"  有效计算数: {valid}")

        if valid > 0:
            ce = df['cost_efficiency'].dropna()
            logger.info(f"  收益成本比 (cost_efficiency):")
            logger.info(f"    均值: {ce.mean():.4f}")
            logger.info(f"    中位数: {ce.median():.4f}")
            logger.info(f"    最小值: {ce.min():.4f}")
            logger.info(f"    最大值: {ce.max():.4f}")
            profitable = (ce > 1.0).sum()
            logger.info(f"    盈利 (cost_efficiency > 1): {profitable}/{valid} ({profitable/valid*100:.1f}%)")

        # 信号分布
        signal_counts = df['trade_signal'].value_counts()
        logger.info(f"  交易信号分布:")
        for sig, cnt in signal_counts.items():
            info = self.SIGNAL_MAP.get(sig, (sig, ''))
            logger.info(f"    {sig} ({info[0]}): {cnt}")

        # Top 5 最佳
        if valid > 0:
            top5 = df.nlargest(5, 'cost_efficiency')
            logger.info(f"  Top 5 最佳合约 (按 cost_efficiency):")
            for _, row in top5.iterrows():
                logger.info(f"    {row['ts_code']:20s} K={row['exercise_price']:8.1f} "
                            f"close={row['close']:7.2f} CE={row['cost_efficiency']:.4f} "
                            f"P&L={row.get('total_pnl_at_K', 0):.2f} "
                            f"sig={row['trade_signal']}")

        logger.info("=" * 60)

    # ================================================================
    # 主流程
    # ================================================================
    def run(self, config):
        """主流程：拉取 → 清洗 → 计算 → 导出

        Args:
            config: dict with keys:
                - name: str, 报告名称
                - start_date: str YYYYMMDD
                - end_date: str YYYYMMDD
                - call_put: str 'C'/'P'
                - exercise_type: str '欧式'/'美式' (optional)
                - ts_code_filter: str LIKE pattern

        Returns:
            str or None: Excel 文件路径
        """
        name = config.get('name', 'Unknown')
        start_date = config.get('start_date')
        end_date = config.get('end_date')
        call_put = config.get('call_put', 'C')
        exercise_type = config.get('exercise_type')
        ts_code_filter = config.get('ts_code_filter')

        logger.info("\n" + "=" * 80)
        logger.info(f"OptionCallStrategyAnalyzer.run: {name}")
        logger.info(f"  Period: [{start_date}, {end_date}], call_put={call_put}, "
                    f"filter={ts_code_filter}, exercise_type={exercise_type}")
        logger.info("=" * 80)

        # Step 1: 拉取数据
        logger.info("\nStep 1/4: Fetching data...")
        df = self.fetch_data(
            start_date=start_date, end_date=end_date,
            call_put=call_put, ts_code_filter=ts_code_filter,
            exercise_type=exercise_type,
        )

        if len(df) == 0:
            logger.warning(f"[{name}] No data found, skipping")
            return None

        # Step 2: 清洗
        logger.info("\nStep 2/4: Cleaning and filtering...")
        df = self._clean_and_filter(df)

        if len(df) == 0:
            logger.warning(f"[{name}] No valid data after cleaning, skipping")
            return None

        # Step 3: 计算策略盈亏
        logger.info("\nStep 3/4: Calculating strategy P&L...")
        df = self.calc_strategy_pnl(df)
        df = self.calc_scenario_pnl(df)

        # Step 4: 导出 Excel
        logger.info("\nStep 4/4: Exporting Excel report...")
        filepath = self.export_to_excel(df, name, start_date, end_date)

        logger.info(f"\n{'='*80}")
        logger.info(f"[{name}] Report generated: {filepath}")
        logger.info(f"{'='*80}")

        return filepath


# ================================================================
# 独立运行入口
# ================================================================
if __name__ == "__main__":
    report_configs = [
        {
            "name": "HO2612看涨欧式期权",
            "start_date": "20251222",
            "end_date": "20260717",
            "call_put": "C",
            "exercise_type": "欧式",
            "ts_code_filter": "HO2612%",
        },
        {
            "name": "HO2612看跌欧式期权",
            "start_date": "20251222",
            "end_date": "20260717",
            "call_put": "P",
            "exercise_type": "欧式",
            "ts_code_filter": "HO2612%",
        },
    ]

    analyzer = OptionCallStrategyAnalyzer()

    for config in report_configs:
        name = config.get("name")
        logger.info(f"\n{'#'*80}")
        logger.info(f"# Running config: {name}")
        logger.info(f"{'#'*80}")
        try:
            filepath = analyzer.run(config)
            if filepath:
                logger.info(f"✅ [{name}] Excel: {filepath}")
            else:
                logger.warning(f"⚠️ [{name}] No data, report skipped")
        except Exception as e:
            logger.error(f"❌ [{name}] Failed: {e}", exc_info=True)

r"""
期权波动率曲面 偏度/期限结构分析器 (Vol Surface: Skew / Risk Reversal / Butterfly / Term)

专业定位:
    偏度交易(skew trading) + 期限结构交易(term structure)的信号层:
        1. risk_reversal = call_wing_iv - put_wing_iv: 风险逆转(25Δ近似,
           正=Call翼贵=上行需求, 负=左偏=恐慌Put贵)
        2. skew_slope: IV 对 moneyness_log 的回归斜率(每单位log价态的IV变化,
           <0 = 虚值Put贵, 即经典股票左偏)
        3. butterfly: 翼部对平值的凸性溢价(微笑厚度)
        4. term_slope: (远月atm_iv - 近月atm_iv)/年限差(>0 = 正期限结构,
           卖近买远的日历价差占优; <0 = 倒挂, 常见于事件/分红季)

数据流:
    tb_tushare_opt_daily_indicator (moneyness_log + implied_vol)
      + df_tushare_opt_basic (symbol → underlying_key)
    → tb_option_vol_surface (每行 = 交易日 x 标的 x 到期月 的曲面切片)

使用:
    config = {
        "name": "华夏上证50ETF期权（波动率曲面偏度/期限结构）",
        "start_date": "20250901",
        "end_date": CommonParameters.today,
        "symbol_filter": "510050%",
    }
    VolSurfaceSkewTermAnalysis().run(config)

注: 本模块专注把曲面指标结构化落库供跨日回溯与信号研究;
    报告出口有二:
        1. VolSurfaceReport: 时序视角(RR/蝶式/期限斜率走势 + 最新信号一览)
        2. GreeksEfficiencyReport 图2/图4: 最新日截面快照(微笑/期限结构)
"""

import json
from datetime import datetime

import numpy as np
import pandas as pd

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.common.ReportJobLogger import ReportJobLogger
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

logger = CommonLib.logger


class VolSurfaceSkewTermAnalysis:
    """波动率曲面 偏度/期限结构分析器"""

    STRATEGY_TYPE = 'VOL_SURFACE'
    ANALYSIS_VERSION = 'v1'
    TABLE_INDICATOR = 'tb_tushare_opt_daily_indicator'
    TABLE_BASIC = 'df_tushare_opt_basic'
    TABLE_TARGET = 'tb_option_vol_surface'

    # === 曲面分带(moneyness_log = ln(K/S)/sqrt(T年)) ===
    ATM_BAND = 0.05            # |moneyness_log| <= 此值 → 平值
    WING_THRESHOLD = 0.15      # |moneyness_log| >= 此值 → 翼部(25Δ近似)

    # === 信号阈值 ===
    SKEW_SIGNAL_BP = 2.0       # |risk_reversal| 超过此值(百分点)给偏度信号
    TERM_SIGNAL_BP = 2.0       # |term_slope| 超过此值(百分点/年)给日历信号

    # === 目标表字段(与建表 SQL 逐列对齐) ===
    TARGET_COLUMNS = [
        'strategy_type', 'analysis_time', 'analysis_params', 'analysis_version',
        'trade_date', 'underlying_key', 's_month', 'maturity_date',
        'days_to_maturity', 'years_to_maturity_calendar', 'n_contracts',
        'atm_iv', 'put_wing_iv', 'call_wing_iv', 'risk_reversal',
        'skew_slope', 'butterfly', 'iv_dispersion',
        'term_atm_iv_near', 'term_atm_iv_far', 'term_slope', 'n_term_months',
        'trade_signal', 'signal_reason',
    ]

    STR_COLUMNS = {'strategy_type', 'analysis_params', 'analysis_version',
                   'trade_date', 'underlying_key', 's_month', 'maturity_date',
                   'trade_signal', 'signal_reason'}

    # ================================================================
    # 数据获取
    # ================================================================
    @staticmethod
    def _underlying_key(symbol, ts_code):
        s = str(symbol or '')
        if len(s) >= 6 and s[:6].isdigit():
            return s[:6]
        tc = str(ts_code or '')
        if len(tc) >= 2 and tc[:2].isalpha():
            return tc[:2]
        return s or tc

    def fetch_data(self, start_date, end_date, symbol_filter=None):
        """拉取 indicator 表(moneyness_log/implied_vol), join basic 取 symbol"""
        where_clauses = [
            f"ind.trade_date >= '{start_date}'",
            f"ind.trade_date <= '{end_date}'",
            "ind.implied_vol > 0",
            "ind.moneyness_log IS NOT NULL",
        ]
        if symbol_filter:
            where_clauses.append(
                f"(b.symbol LIKE '{symbol_filter}' OR ind.ts_code LIKE '{symbol_filter}')"
            )
        sql = f"""
        SELECT ind.trade_date, ind.ts_code, ind.call_put, ind.exercise_price,
               ind.s_month, ind.maturity_date, ind.days_to_maturity,
               ind.years_to_maturity_calendar, ind.moneyness_log, ind.implied_vol,
               b.symbol AS symbol
        FROM indexsysdb.{self.TABLE_INDICATOR} ind
        INNER JOIN (
            SELECT ts_code, any(symbol) AS symbol
            FROM indexsysdb.{self.TABLE_BASIC}
            GROUP BY ts_code
        ) b ON ind.ts_code = b.ts_code
        WHERE {' AND '.join(where_clauses)}
        ORDER BY ind.trade_date, ind.s_month, ind.exercise_price
        """
        logger.info(f"SQL:\n{sql}")
        df = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        if len(df) == 0:
            logger.warning("No vol surface data fetched")
            return pd.DataFrame()
        for col in ['exercise_price', 'years_to_maturity_calendar', 'moneyness_log',
                    'implied_vol', 'days_to_maturity']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        for col in ['trade_date', 'ts_code', 'call_put', 's_month', 'maturity_date',
                    'symbol']:
            df[col] = df[col].fillna('').astype(str)
        df = df.dropna(subset=['moneyness_log', 'implied_vol'])
        df['underlying_key'] = [
            self._underlying_key(sym, tc)
            for sym, tc in zip(df['symbol'], df['ts_code'])
        ]
        logger.info(f"Fetched {len(df)} rows for vol surface")
        return df

    # ================================================================
    # 曲面切片指标(交易日 x 标的 x 到期月)
    # ================================================================
    def _calc_surface_metrics(self, df):
        """计算每切片: atm_iv / 翼IV / risk_reversal / skew_slope / butterfly"""
        records = []
        for (td, und, sm), g in df.groupby(['trade_date', 'underlying_key', 's_month']):
            years = float(g['years_to_maturity_calendar'].iloc[0]) \
                if len(g) else np.nan
            maturity = str(g['maturity_date'].iloc[0]) if len(g) else ''
            days = int(g['days_to_maturity'].iloc[0]) \
                if pd.notna(g['days_to_maturity'].iloc[0]) else 0

            atm = g[g['moneyness_log'].abs() <= self.ATM_BAND]
            atm_iv = float(atm['implied_vol'].mean()) if len(atm) else np.nan

            put_wing = g[(g['call_put'] == 'P')
                         & (g['moneyness_log'] <= -self.WING_THRESHOLD)]
            call_wing = g[(g['call_put'] == 'C')
                          & (g['moneyness_log'] >= self.WING_THRESHOLD)]
            put_wing_iv = float(put_wing['implied_vol'].mean()) if len(put_wing) else np.nan
            call_wing_iv = float(call_wing['implied_vol'].mean()) if len(call_wing) else np.nan
            rr = (call_wing_iv - put_wing_iv) \
                if pd.notna(put_wing_iv) and pd.notna(call_wing_iv) else np.nan

            # 偏度斜率: IV ~ moneyness_log 线性回归(C+P 合并)
            if len(g) >= 5 and g['moneyness_log'].std() > 1e-9:
                x = g['moneyness_log'].values
                y = g['implied_vol'].values
                slope = float(np.polyfit(x, y, 1)[0])
            else:
                slope = np.nan

            butterfly = np.nan
            if pd.notna(put_wing_iv) and pd.notna(call_wing_iv) and pd.notna(atm_iv):
                butterfly = (put_wing_iv + call_wing_iv) / 2.0 - atm_iv

            records.append({
                'trade_date': td, 'underlying_key': und, 's_month': sm,
                'maturity_date': maturity, 'days_to_maturity': days,
                'years_to_maturity_calendar': years, 'n_contracts': len(g),
                'atm_iv': atm_iv, 'put_wing_iv': put_wing_iv,
                'call_wing_iv': call_wing_iv, 'risk_reversal': rr,
                'skew_slope': slope, 'butterfly': butterfly,
                'iv_dispersion': float(g['implied_vol'].std()) if len(g) > 1 else 0.0,
            })
        return pd.DataFrame(records)

    # ================================================================
    # 期限结构(同标的当日跨月)
    # ================================================================
    def _calc_term_structure(self, df_surf):
        """按 (trade_date, underlying_key) 计算期限斜率并冗余写回各行"""
        df_surf['term_atm_iv_near'] = np.nan
        df_surf['term_atm_iv_far'] = np.nan
        df_surf['term_slope'] = np.nan
        df_surf['n_term_months'] = 0

        for (td, und), g in df_surf.groupby(['trade_date', 'underlying_key']):
            valid = g[g['atm_iv'].notna()].sort_values('years_to_maturity_calendar')
            if len(valid) < 2:
                continue
            near, far = valid.iloc[0], valid.iloc[-1]
            y_diff = float(far['years_to_maturity_calendar']
                           - near['years_to_maturity_calendar'])
            slope = (float(far['atm_iv']) - float(near['atm_iv'])) / y_diff \
                if y_diff > 1e-9 else np.nan
            idx = g.index
            df_surf.loc[idx, 'term_atm_iv_near'] = float(near['atm_iv'])
            df_surf.loc[idx, 'term_atm_iv_far'] = float(far['atm_iv'])
            df_surf.loc[idx, 'term_slope'] = slope
            df_surf.loc[idx, 'n_term_months'] = len(valid)
        return df_surf

    # ================================================================
    # 信号
    # ================================================================
    def _assign_signals(self, df):
        """偏度/期限结构信号(百分点口径阈值)"""
        if df.empty:
            return df
        signals, reasons = [], []
        for _, r in df.iterrows():
            sig, why = 'NEUTRAL', []
            rr_bp = r['risk_reversal'] * 100 if pd.notna(r['risk_reversal']) else np.nan
            ts_bp = r['term_slope'] * 100 if pd.notna(r['term_slope']) else np.nan
            if pd.notna(rr_bp) and abs(rr_bp) >= self.SKEW_SIGNAL_BP:
                if rr_bp < 0:
                    sig = 'SELL_SKEW'   # 左偏深: 卖贵Put翼/买Call翼, 做偏度回归
                    why.append(f'风险逆转={rr_bp:+.1f}pp(Put翼贵于Call翼, 左偏深)')
                else:
                    sig = 'BUY_SKEW'    # 右偏: 买Call翼/卖Put翼
                    why.append(f'风险逆转={rr_bp:+.1f}pp(Call翼贵于Put翼, 右偏)')
            if pd.notna(ts_bp) and abs(ts_bp) >= self.TERM_SIGNAL_BP:
                tag = ('远月贵于近月(正期限结构): 卖近买远日历价差占优'
                       if ts_bp > 0 else '近月贵于远月(倒挂): 事件/分红驱动, 买近卖远谨慎')
                why.append(f'期限斜率={ts_bp:+.1f}pp/年: {tag}')
                if sig == 'NEUTRAL':
                    sig = 'BUY_CALENDAR' if ts_bp > 0 else 'SELL_CALENDAR'
            if not why:
                why.append('偏度/期限结构均在中性区间')
            signals.append(sig)
            reasons.append('; '.join(why))
        df['trade_signal'] = signals
        df['signal_reason'] = reasons
        counts = pd.Series(signals).value_counts()
        logger.info(f"Trade signals: {counts.to_dict()}")
        return df

    # ================================================================
    # 落库
    # ================================================================
    def save_to_clickhouse(self, df, config):
        if len(df) == 0:
            logger.warning("Empty vol surface, nothing to save")
            return
        logger.info(f"Saving {len(df)} rows to {self.TABLE_TARGET}")
        df = df.copy()
        df['strategy_type'] = self.STRATEGY_TYPE
        df['analysis_time'] = datetime.now().replace(microsecond=0)
        df['analysis_params'] = json.dumps(config, ensure_ascii=False, default=str)
        df['analysis_version'] = self.ANALYSIS_VERSION

        available_cols = [c for c in self.TARGET_COLUMNS if c in df.columns]
        df_output = df[available_cols].copy()
        for col in df_output.columns:
            if col == 'analysis_time':
                continue
            if col in self.STR_COLUMNS:
                df_output[col] = df_output[col].fillna('').astype(str)
            elif col in ('days_to_maturity', 'n_contracts', 'n_term_months'):
                df_output[col] = pd.to_numeric(
                    df_output[col], errors='coerce').fillna(0).astype(int)
            else:
                df_output[col] = pd.to_numeric(df_output[col], errors='coerce')
                df_output[col] = df_output[col].where(pd.notna(df_output[col]), None)

        symbol_filter = config.get('symbol_filter')
        trade_dates = df_output['trade_date'].unique().tolist()
        dates_str = "','".join(trade_dates)
        delete_conditions = [
            f"strategy_type = '{self.STRATEGY_TYPE}'",
            f"trade_date IN ('{dates_str}')",
        ]
        if symbol_filter:
            delete_conditions.append(f"underlying_key LIKE "
                                     f"'{symbol_filter.rstrip('%').split('%')[0]}%'")
        del_sql = (f"ALTER TABLE indexsysdb.{self.TABLE_TARGET} DELETE WHERE "
                   f"{' AND '.join(delete_conditions)}")
        logger.info(f"SQL:\n{del_sql}")
        ClickhouseService.execute_sql(del_sql)
        ClickhouseService.save_dataframe_to_clickhouse(
            dataframe=df_output, table_name=self.TABLE_TARGET, database='indexsysdb')
        logger.info(f"Saved {len(df_output)} rows to {self.TABLE_TARGET}")
        return df_output

    # ================================================================
    # 主流程
    # ================================================================
    def run(self, config):
        """主流程: 拉取 → 切片指标 → 期限结构 → 信号 → 落库"""
        name = config.get('name', 'Unknown')
        start_date = config.get('start_date')
        end_date = config.get('end_date') or CommonParameters.today
        symbol_filter = config.get('symbol_filter')

        logger.info("\n" + "=" * 80)
        logger.info(f"{self.__class__.__name__}.run: {name}")
        logger.info(f"  Period: [{start_date}, {end_date}], symbol_filter={symbol_filter}")
        logger.info("=" * 80)

        job_logger = ReportJobLogger()
        job_logger.start_job(self.__class__.__name__, 'OptionStrategyAnalysis',
                             params={'report_name': name, 'start_date': start_date,
                                     'end_date': end_date, 'symbol_filter': symbol_filter})
        try:
            logger.info("\nStep 1/4: Fetching indicator data...")
            df = self.fetch_data(start_date=start_date, end_date=end_date,
                                 symbol_filter=symbol_filter)
            if len(df) == 0:
                logger.warning(f"[{name}] No data, skipping")
                job_logger.end_job_success(records_processed=0)
                return None

            logger.info("\nStep 2/4: Calculating surface slice metrics...")
            df_surf = self._calc_surface_metrics(df)
            logger.info(f"  slices: {len(df_surf)} (date x underlying x month)")

            logger.info("\nStep 3/4: Calculating term structure & signals...")
            df_surf = self._calc_term_structure(df_surf)
            df_surf = self._assign_signals(df_surf)

            logger.info("\nStep 4/4: Saving to ClickHouse...")
            self.save_to_clickhouse(df_surf, config)

            logger.info(f"\n{'='*80}")
            logger.info(f"[{name}] Vol surface done: {len(df_surf)} rows "
                        f"-> {self.TABLE_TARGET}")
            logger.info(f"{'='*80}")
            job_logger.end_job_success(records_processed=len(df_surf))
            return df_surf

        except Exception as e:
            import traceback
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise

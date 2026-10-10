r"""
合成股票(Synthetic Stock)策略 PDF 报告生成器 共享核心 — 资深交易员/风控视角

数据源:
    tb_option_trading_strategy_synthetic_long_stock / ..._short_stock
    (由 SyntheticLongStockStrategyAnalysis / SyntheticShortStockStrategyAnalysis 写入)

报告结构:
    封面 → 数据概览(关键数字) → 最新交易日最优组合明细(按评分降序) → 4张图表
    → 资深交易员综合点评(自动生成, 含数字) → 指标口径 → 风险提示

核心图表:
    图1 合成偏离时序(日均+极值带, 0轴=平价理论)
    图2 隐含融资利率 vs 基准无风险利率(最优组合逐日)
    图3 资金效率时序(资金占用/现货全额, 1.0参考线)
    图4 最新日到期损益结构(组合P&L vs 直接持有/融券现货对照, 含盈亏平衡点)

输出:
    PDF → CommonParameters.optionAnalysisReportPath

前置条件:
    先运行 SyntheticLong/ShortStockStrategyAnalysisTest 落库分析结果。

字体注意(历史教训):
    matplotlib 首选字体必须是 Microsoft YaHei —— SimHei 缺少 U+2212(真减号)字形,
    公式/刻度中的减号会渲染成方框(tofu); 雅黑同时覆盖中文/希腊字母/±/×。
"""

import io
import os
import traceback
from datetime import datetime, timedelta

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
# 横轴按"整齐"步长打刻度(ETF ~3元档 => 0.1), 见 _nice_tick_step
from matplotlib.ticker import MultipleLocator
import numpy as np
import pandas as pd
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
                                 PageBreak, Table, TableStyle)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.common.ReportJobLogger import ReportJobLogger
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

logger = CommonLib.logger

# 中文字体支持（matplotlib）: 雅黑优先——SimHei 缺 U+2212 会渲染成方框
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['mathtext.fontset'] = 'dejavusans'


class SyntheticStockStrategyReportBase:
    """合成股票策略 PDF 报告生成器 共享核心

    子类覆写: STRATEGY_TYPE / TABLE_SOURCE / DIRECTION / REPORT_TITLE /
    REPORT_SUBTITLE / STRATEGY_CN。图表/明细/点评/PDF组装全部共享。
    """

    REPORT_DIR = CommonParameters.optionAnalysisReportPath
    DEFAULT_LOOKBACK_DAYS = 90
    DETAIL_TABLE_ROWS = 15
    # 图4 叠加展示的组合数(1=仅最优, 其余用不同颜色虚线 + 右端标注)
    PAYOFF_PROFILE_ROWS = 6
    # 明细表字号(列宽按内容自适应; 加净Γ/净Vega/净Θ后共23列, 6.5pt才能保证零截断)
    DETAIL_TABLE_FONT_SIZE = 6.5
    # 每列最小宽度(pt): 低于此值中文表头/数值会被截断
    DETAIL_TABLE_MIN_COL_WIDTH = 22.0

    # 子类必须覆写
    STRATEGY_TYPE = None
    TABLE_SOURCE = None
    DIRECTION = None          # +1 合成多头 / -1 合成空头
    STRATEGY_CN = None        # 中文名, 如 '合成多头'
    REPORT_TITLE = None
    REPORT_SUBTITLE = None

    CHART_COLORS = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6', '#f39c12',
                    '#1abc9c', '#e67e22', '#2980b9', '#c0392b', '#27ae60']

    # 信号列配色(明细表)
    SIGNAL_COLORS = {'STRONG_BUY': '#C8E6C9', 'BUY': '#E8F5E9',
                     'CONSIDER': '#FFF9C4', 'NEUTRAL': '#ECEFF1',
                     'AVOID': '#FFCDD2'}

    def __init__(self):
        os.makedirs(self.REPORT_DIR, exist_ok=True)
        self.reportlab_font = self._register_chinese_font()

    def _register_chinese_font(self):
        """注册 reportlab 中文字体"""
        reportlab_font = 'Helvetica'
        font_mapping = [
            (r'C:\Windows\Fonts\msyh.ttc', 'MicrosoftYaHei'),
            (r'C:\Windows\Fonts\simhei.ttf', 'SimHei'),
            (r'C:\Windows\Fonts\simfang.ttf', 'FangSong'),
            (r'C:\Windows\Fonts\simsun.ttc', 'SimSun'),
        ]
        for font_path, font_name in font_mapping:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    reportlab_font = font_name
                    logger.info(f"ReportLab 加载中文字体: {font_name}")
                    break
                except Exception as e:
                    logger.warning(f"字体加载失败 {font_path}: {e}")
        if reportlab_font == 'Helvetica':
            logger.warning("ReportLab 未找到中文字体，PDF中文可能无法正常显示")
        return reportlab_font

    def writeLogInfo(self, className="unknown", functionName="unknown", event="unknown"):
        logger.info("%s.%s: %s" % (className, functionName, event))

    # ===================== 通用工具 =====================

    @staticmethod
    def _fmt(val, fmt='{:.4g}'):
        """数值安全格式化（NaN/None → N/A）"""
        try:
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return 'N/A'
            return fmt.format(val)
        except Exception:
            return 'N/A'

    def _fig_to_bytesio(self, fig, dpi=160):
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        return buf

    # ===================== 数据获取 =====================

    def fetch_data(self, start_date=None, end_date=None, symbol_filter=None):
        """从策略专表拉取合成股票分析结果"""
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName="fetch_data",
                          event=f"Fetching data from {self.TABLE_SOURCE}")

        where_clauses = []
        if start_date:
            where_clauses.append(f"trade_date >= '{start_date}'")
        if end_date:
            where_clauses.append(f"trade_date <= '{end_date}'")
        if symbol_filter:
            where_clauses.append(f"symbol LIKE '{symbol_filter}'")

        where_str = (" AND ".join(where_clauses)) if where_clauses else "1=1"
        sql = f"""
        SELECT *
        FROM indexsysdb.{self.TABLE_SOURCE}
        WHERE {where_str}
        ORDER BY trade_date, exercise_price
        """
        logger.info(f"SQL:\n{sql}")
        df = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        logger.info(f"Fetched {len(df)} rows, {len(df.columns)} columns")
        return df

    def clean_data(self, df):
        """类型转换与派生列"""
        numeric_cols = [
            'exercise_price', 'opt_multiplier', 'days_to_maturity',
            'spot_price', 'risk_free_rate', 'dividend_yield',
            'premium', 'premium_put', 'implied_vol', 'implied_vol_put',
            'iv_rank', 'iv_rank_put',
            'delta', 'gamma', 'theta', 'vega', 'delta_put', 'gamma_put',
            'theta_put', 'vega_put',
            'bs_theoretical_price', 'close_vs_theoretical', 'close_vs_theoretical_pct',
            'bs_theoretical_price_put', 'close_vs_theoretical_put',
            'close_vs_theoretical_pct_put',
            'synthetic_net_cost', 'synthetic_net_cost_cny',
            'synthetic_net_cost_pct_of_spot',
            'synthetic_theoretical', 'synth_deviation', 'synth_deviation_pct',
            'implied_financing_rate', 'financing_spread_bp',
            'net_delta', 'delta_check_passed', 'net_gamma', 'net_theta', 'net_vega',
            'margin_est', 'capital_occupied_cny', 'margin_vs_spot_capital',
            'breakeven', 'breakeven_pct', 'score', 'combo_rank',
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        for col in ['trade_date', 'ts_code', 'symbol', 'opt_name', 'opt_exchange',
                    'call_put', 'ts_code_put', 'symbol_put', 'opt_name_put',
                    's_month', 'maturity_date', 'moneyness_status',
                    'price_bias', 'price_bias_put', 'trade_signal', 'signal_reason']:
            if col in df.columns:
                df[col] = df[col].fillna('').astype(str)

        # 情景列
        for col in df.columns:
            if col.startswith(('scenario_pnl_', 'unhedged_pnl_')):
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # 标的代码(Call腿symbol前6位, 如 510050C2612M02750 → 510050)
        if 'symbol' in df.columns:
            df['underlying'] = df['symbol'].str.extract(r'^(\d{6})', expand=False).fillna('')

        df = df.sort_values(['trade_date', 'score'], ascending=[True, False]).reset_index(drop=True)
        df['trade_date_dt'] = pd.to_datetime(df['trade_date'], format='%Y%m%d', errors='coerce')
        return df

    # ===================== 统计辅助 =====================

    def _latest_snapshot(self, df):
        latest_date = df['trade_date'].max()
        return latest_date, df[df['trade_date'] == latest_date]

    def _best_by_date(self, df):
        """每个交易日的最优组合(评分最高且Delta校验通过)"""
        valid = df[df['delta_check_passed'] == 1] if 'delta_check_passed' in df.columns else df
        if valid.empty:
            valid = df
        return valid.sort_values(['trade_date', 'score'], ascending=[True, False]) \
                    .groupby('trade_date').head(1)

    def _build_overview_numbers(self, df):
        """数据概览统计"""
        latest_date, latest = self._latest_snapshot(df)
        trade_dates = sorted(df['trade_date'].unique())

        # Delta 校验通过的有效组合
        ok_latest = latest[latest['delta_check_passed'] == 1] \
            if 'delta_check_passed' in latest.columns else latest
        dev = ok_latest['synth_deviation_pct'].dropna()
        spread = ok_latest['financing_spread_bp'].dropna()
        r_impl = ok_latest['implied_financing_rate'].dropna()
        margin_ratio = ok_latest['margin_vs_spot_capital'].dropna()

        stats = {
            'date_start': trade_dates[0] if trade_dates else 'N/A',
            'date_end': trade_dates[-1] if trade_dates else 'N/A',
            'n_days': len(trade_dates),
            'n_rows': len(df),
            'n_strikes': df['exercise_price'].nunique(),
            'latest_date': latest_date,
            'n_combos_latest': len(latest),
            'n_pass_latest': len(ok_latest),
            'n_delta_fail_latest': int((latest['delta_check_passed'] == 0).sum())
                if len(latest) else 0,
            'n_expiry_soon': int((latest['days_to_maturity'] < 10).sum())
                if len(latest) else 0,
            'dev_mean': dev.mean() if len(dev) else np.nan,
            'dev_absmax': dev.abs().max() if len(dev) else np.nan,
            'spread_mean': spread.mean() if len(spread) else np.nan,
            'spread_min': spread.min() if len(spread) else np.nan,
            'r_impl_mean': r_impl.mean() if len(r_impl) else np.nan,
            'margin_ratio_mean': margin_ratio.mean() if len(margin_ratio) else np.nan,
            'margin_ratio_best': margin_ratio.min() if len(margin_ratio) else np.nan,
            'signal_counts': latest['trade_signal'].value_counts().to_dict()
                if len(latest) else {},
        }
        return stats

    # ===================== 图表生成 =====================

    def gen_chart1_deviation_timeseries(self, df):
        """图1: 合成偏离时序(日均 + 当日极值带; 0轴=平价理论)"""
        daily = df.groupby('trade_date_dt')['synth_deviation_pct']
        mean_s = daily.mean().dropna().sort_index()
        minmax = df.dropna(subset=['synth_deviation_pct']).groupby('trade_date_dt') \
            ['synth_deviation_pct'].agg(['min', 'max'])
        if mean_s.empty:
            logger.warning("No valid data for chart 1, skipping")
            return None

        fig, ax = plt.subplots(figsize=(20, 8))
        fig.suptitle(f'图1：{self.STRATEGY_CN} 偏离时序'
                     r'（偏离 = (C−P) − [S·e^(−qT) − K·e^(−rT)]，占现价%）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        if not minmax.empty:
            idx = minmax.index.intersection(mean_s.index)
            ax.fill_between(idx, minmax.loc[idx, 'min'], minmax.loc[idx, 'max'],
                            color='#3498db', alpha=0.18, label='当日K档极值带')
        ax.plot(mean_s.index.tolist(), mean_s.values, color='#2980b9',
                linewidth=1.8, marker='o', markersize=3, label='日均偏离')
        ax.axhline(y=0, color='#1a1a2e', linewidth=1.2)
        ax.text(0.005, 0, '平价理论（偏离=0）', transform=ax.get_yaxis_transform(),
                fontsize=7.5, color='#1a1a2e', va='bottom')

        ax.set_ylabel('合成偏离（% 现价）', fontsize=11)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10),
                  fontsize=9, ncol=3, frameon=True)
        fig.autofmt_xdate(rotation=45, ha='right')
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    def gen_chart2_implied_rate(self, df):
        """图2: 隐含融资利率 vs 基准无风险利率(最优组合逐日)"""
        best = self._best_by_date(df)
        if best.empty or best['implied_financing_rate'].dropna().empty:
            logger.warning("No valid data for chart 2, skipping")
            return None

        best = best.sort_values('trade_date_dt')
        fig, ax = plt.subplots(figsize=(20, 8))
        fig.suptitle('图2：隐含融资利率 vs 基准无风险利率（最优组合逐日）'
                     r'（r_impl = −ln((S·e^(−qT)−(C−P))/K)/T）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        ax.plot(best['trade_date_dt'], best['implied_financing_rate'],
                color='#2980b9', linewidth=1.8, marker='o', markersize=3,
                label='隐含融资利率 r_impl')
        ax.plot(best['trade_date_dt'], best['risk_free_rate'],
                color='#e74c3c', linewidth=1.4, linestyle='--',
                label='基准无风险利率 r')

        # 利差零轴参考: r_impl-r=0 → 两线重合即合成与基准资金成本打平
        ax.set_ylabel('年化利率', fontsize=11)
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda v, _: f'{v * 100:.1f}%'))
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10),
                  fontsize=9, ncol=2, frameon=True)
        fig.autofmt_xdate(rotation=45, ha='right')
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    def gen_chart3_capital_efficiency(self, df):
        """图3: 资金效率时序(资金占用/现货全额, 1.0=现货全额资金)"""
        best = self._best_by_date(df)
        if best.empty or best['margin_vs_spot_capital'].dropna().empty:
            logger.warning("No valid data for chart 3, skipping")
            return None

        best = best.sort_values('trade_date_dt')
        fig, ax = plt.subplots(figsize=(20, 8))
        fig.suptitle('图3：资金效率时序（资金占用 / 现货全额资金，最优组合逐日）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        ax.plot(best['trade_date_dt'], best['margin_vs_spot_capital'],
                color='#27ae60', linewidth=1.8, marker='o', markersize=3,
                label='资金占用/现货全额')
        for y_val, clr, txt in [(1.0, '#e74c3c', '1.0 现货全额'),
                                (0.3, '#f39c12', '0.3 高效率参考线')]:
            ax.axhline(y=y_val, color=clr, linewidth=1.2, linestyle='--', alpha=0.8)
            ax.text(0.005, y_val, txt, transform=ax.get_yaxis_transform(),
                    fontsize=7.5, color=clr, va='bottom')

        ax.set_ylabel('资金占用 / 现货全额', fontsize=11)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10),
                  fontsize=9, ncol=2, frameon=True)
        fig.autofmt_xdate(rotation=45, ha='right')
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    @staticmethod
    def _nice_tick_step(raw_step, candidates=(1.0, 2.0, 2.5, 5.0, 10.0)):
        """取不小于 raw_step 的"整齐"步长(1/2/2.5/5 × 10^k)

        横轴刻度用: 标的价 ~3 元档(raw≈0.08)时给出 0.1 的细刻度,
        指数期权 ~3000 点档自动放大到 100, 不会退化成读不出来的密集刻度。
        """
        if raw_step <= 0 or not np.isfinite(raw_step):
            return 1.0
        base = 10.0 ** np.floor(np.log10(raw_step))
        for c in candidates:
            step = c * base
            if step >= raw_step - 1e-12:
                return step
        return 10.0 * base

    @staticmethod
    def _spread_label_positions(values, min_gap):
        """把相互重叠的标注纵坐标按最小间距上下错开(保持原有相对顺序)

        合成组合的到期损益线是一族近似平行的直线, 右端标注会挤成一团;
        自下而上推开后仍保持原顺序, 便于对应到各自的线。
        """
        n = len(values)
        if n == 0:
            return []
        order = sorted(range(n), key=lambda i: values[i])
        pos = [float(values[i]) for i in order]
        for k in range(1, n):
            if pos[k] - pos[k - 1] < min_gap:
                pos[k] = pos[k - 1] + min_gap
        out = [0.0] * n
        for k, i in enumerate(order):
            out[i] = pos[k]
        return out

    def gen_chart4_payoff_profile(self, df):
        """图4: 最新日到期损益结构(最优组合 + Top N 其他组合 vs 现货对照)

        - 横轴刻度按标的价位取"整齐"步长(ETF 3元档 => 0.1), 便于精读;
        - 最优组合实线, 其余 Top N 组合用不同颜色虚线;
        - 每条线右端标注该组合双腿的实际合约名称(重叠时自动上下错开),
          跨标的时(如 ALL)可直接看出每条线属于哪个合约。
        """
        _, latest = self._latest_snapshot(df)
        best = latest[latest['delta_check_passed'] == 1] \
            if 'delta_check_passed' in latest.columns else latest
        if best.empty:
            best = latest
        if best.empty:
            logger.warning("No valid data for chart 4, skipping")
            return None

        best = best.sort_values('score', ascending=False)
        dirn = float(self.DIRECTION)
        try:
            S0 = float(best.iloc[0]['spot_price'])
        except (TypeError, ValueError):
            S0 = float('nan')
        if not (S0 > 0):
            logger.warning("Invalid spot price for chart 4, skipping")
            return None

        combos = []
        for _, r in best.head(self.PAYOFF_PROFILE_ROWS).iterrows():
            K = float(r.get('exercise_price', np.nan))
            net_cost = float(r.get('synthetic_net_cost', np.nan))
            if not (K > 0) or pd.isna(net_cost):
                continue
            combos.append({
                'K': K,
                'net_cost': net_cost,
                'be': K + dirn * net_cost,
                'call_name': str(r.get('opt_name', '') or r.get('ts_code', '')),
                'put_name': str(r.get('opt_name_put', '') or r.get('ts_code_put', '')),
            })
        if not combos:
            logger.warning("No valid combos for chart 4, skipping")
            return None

        head = combos[0]
        if not (head['K'] > 0):
            logger.warning("Invalid best combo for chart 4, skipping")
            return None

        s_T = np.linspace(0.8, 1.2, 81) * S0
        span = float(s_T[-1] - s_T[0])
        spot_pnl = dirn * (s_T - S0)

        fig, ax = plt.subplots(figsize=(20, 8))
        fig.suptitle(f'图4：{self.STRATEGY_CN} 到期损益结构'
                     f'（最新日最优组合 K={head["K"]:.4g}，净成本 C−P={head["net_cost"]:+.4g}；'
                     f'虚线=评分前 {len(combos)} 个组合，右端标注双腿合约名称）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        curves = []
        for idx, c in enumerate(combos):
            pnl = dirn * (s_T - c['K'] - c['net_cost'])
            is_best = (idx == 0)
            color = '#2980b9' if is_best else \
                self.CHART_COLORS[(idx - 1) % len(self.CHART_COLORS)]
            c['color'], c['y_end'] = color, float(pnl[-1])
            curves.append(pnl)
            if is_best:
                legend_label = (f'{self.STRATEGY_CN}最优组合 P&L = '
                                + ('S_T−K−(C−P)' if dirn > 0 else 'K−S_T+(C−P)'))
            elif idx == 1:
                legend_label = f'其他组合（评分次优 Top{len(combos)}，虚线）'
            else:
                legend_label = None
            ax.plot(s_T, pnl, color=color, linewidth=2.0 if is_best else 1.3,
                    linestyle='-' if is_best else '--',
                    alpha=1.0 if is_best else 0.9, label=legend_label)

        ax.plot(s_T, spot_pnl, color='#95a5a6', linewidth=1.4, linestyle='-.',
                label='现货对照' + ('（买现货）' if dirn > 0 else '（融券做空）'))

        # ---- 右端标注: 各组合的双腿合约名称(重叠时自动错开) ----
        x_end = float(s_T[-1])
        x_label = x_end + 0.03 * span
        y_lo = float(min(float(np.min(cv)) for cv in curves))
        y_hi = float(max(float(np.max(cv)) for cv in curves))
        y_labels = self._spread_label_positions(
            [c['y_end'] for c in combos], max((y_hi - y_lo) * 0.055, 1e-9))
        for c, y_lab in zip(combos, y_labels):
            ax.annotate(f'K={c["K"]:.4g}  {c["call_name"]} / {c["put_name"]}',
                        xy=(x_end, c['y_end']), xytext=(x_label, y_lab),
                        fontsize=8, color=c['color'], va='center', ha='left',
                        arrowprops=dict(arrowstyle='-', color=c['color'],
                                        lw=0.7, alpha=0.6, shrinkA=0, shrinkB=2))

        # ---- 参考线(0轴 / 最优组合盈亏平衡 / 当日现货) ----
        ax.axhline(y=0, color='#1a1a2e', linewidth=1.0)
        be = head['be']
        ax.axvline(x=be, color='#e74c3c', linewidth=1.2, linestyle=':')
        # 平衡点标注放在0轴下方、S0标注放在上方, 避免两条竖线文字互相压字
        ax.annotate(f'最优组合盈亏平衡 S_T={be:.4g}', xy=(be, 0), xytext=(6, -16),
                    textcoords='offset points', fontsize=9, color='#e74c3c', va='top')
        ax.axvline(x=S0, color='#7f8c8d', linewidth=0.8, linestyle=':')
        ax.annotate(f'S0={S0:.4g}', xy=(S0, 0), xytext=(6, 12),
                    textcoords='offset points', fontsize=9, color='#7f8c8d')

        # ---- 坐标轴: 横轴细刻度 + 右侧留标注位 + 纵向容纳错开的标注 ----
        ax.xaxis.set_major_locator(MultipleLocator(self._nice_tick_step(span / 15.0)))
        ax.set_xlabel('到期标的价格 S_T', fontsize=11)
        ax.set_ylabel('每单位损益', fontsize=11)
        ax.set_xlim(float(s_T[0]) - 0.01 * span, x_label + 0.19 * span)
        lo = min(y_lo, min(y_labels))
        hi = max(y_hi, max(y_labels))
        pad = (hi - lo) * 0.06 if hi > lo else 1.0
        ax.set_ylim(lo - pad, hi + pad)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10),
                  fontsize=9, ncol=3, frameon=True)
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    # ===================== 明细表与点评 =====================

    def _build_detail_table_data(self, latest):
        """最新交易日最优组合明细(按评分降序 Top N)"""
        cand = latest[latest['delta_check_passed'] == 1] \
            if 'delta_check_passed' in latest.columns else latest
        if cand.empty:
            cand = latest
        cand = cand.sort_values('score', ascending=False).head(self.DETAIL_TABLE_ROWS)

        rows = []
        for _, r in cand.iterrows():
            rows.append([
                str(r.get('trade_date', '')),
                self._fmt(r.get('exercise_price'), '{:.4g}'),
                self._fmt(r.get('spot_price'), '{:.4f}'),
                str(r.get('maturity_date', '')),
                self._fmt(r.get('days_to_maturity'), '{:.0f}'),
                self._fmt(r.get('premium'), '{:.4f}'),
                self._fmt(r.get('premium_put'), '{:.4f}'),
                self._fmt(r.get('synthetic_net_cost'), '{:+.4g}'),
                self._fmt(r.get('synthetic_theoretical'), '{:+.4g}'),
                self._fmt(r.get('synth_deviation_pct'), '{:+.3f}'),
                self._fmt(r.get('implied_financing_rate'), '{:.4f}'),
                self._fmt(r.get('financing_spread_bp'), '{:+.1f}'),
                self._fmt(r.get('net_delta'), '{:+.3f}'),
                '通过' if r.get('delta_check_passed') == 1 else '失败',
                self._fmt(r.get('net_gamma'), '{:+.4g}'),
                self._fmt(r.get('net_vega'), '{:+.4g}'),
                self._fmt(r.get('net_theta'), '{:+.4g}'),
                self._fmt(r.get('margin_vs_spot_capital'), '{:.2f}'),
                self._fmt(r.get('breakeven_pct'), '{:+.2f}'),
                self._fmt(r.get('score'), '{:+.3f}'),
                str(r.get('trade_signal', '')),
                str(r.get('opt_name', '')),
                str(r.get('opt_name_put', '')),
            ])
        header = ['交易日', 'K', 'S现货', '到期日', '剩余天数', 'Call价C', 'Put价P',
                  '净成本C−P', '理论成本', '偏离%S', '隐含利率', '利差bp', '净Δ', 'Δ校验',
                  '净Γ', '净Vega', '净Θ', '资金/现货', '平衡点%', '评分', '信号',
                  'Call合约', 'Put合约']
        return header, rows

    def _latest_spot_desc(self, latest):
        """当日标的现货价描述(供小标题展示)

        单一标的给出具体价格; 多标的(如 ALL)给出区间并提示看表内 S现货 列。
        """
        if 'spot_price' not in latest.columns:
            return ''
        spots = pd.to_numeric(latest['spot_price'], errors='coerce').dropna()
        if spots.empty:
            return ''
        lo, hi = float(spots.min()), float(spots.max())
        if abs(hi - lo) < 1e-9:
            return f'{lo:.4f}'
        return f'{lo:.4f} ~ {hi:.4f}（多标的，见 S现货 列）'

    def _build_trader_commentary(self, df, stats):
        """资深交易员综合点评(方向化叙事)"""
        dirn = float(self.DIRECTION)
        paras = []

        # ---- 1. 合成成本环境 ----
        dev_mean, dev_absmax = stats['dev_mean'], stats['dev_absmax']
        spread_mean = stats['spread_mean']
        if pd.notna(dev_mean) and pd.notna(dev_absmax):
            if dirn > 0:
                verdict = ("利差为负意味着市场'借钱买现货'的隐含利率低于基准——"
                           "合成多头比融资买现货便宜，具备替代持有与收敛套利价值；"
                           "利差为正则合成贵，通常指向资金面紧张或分红预期抬升。")
            else:
                verdict = ("偏离为正意味着卖出合成（做空）收价高于理论——"
                           "合成做空成本低于公允水平，作为融券替代更有利；"
                           "偏离为负则是做空成本偏高，通常与分红季 q 抬升有关。")
            paras.append(('合成成本环境判断',
                          f"最新交易日（{stats['latest_date']}）{stats['n_pass_latest']} 个有效组合中，"
                          f"偏离均值 {dev_mean:+.3f}%S、极值 {dev_absmax:.3f}%S，"
                          f"融资利差均值 {self._fmt(spread_mean, '{:+.1f}')}bp。{verdict}"))

        # ---- 2. 资金效率与杠杆 ----
        mr_mean, mr_best = stats['margin_ratio_mean'], stats['margin_ratio_best']
        if pd.notna(mr_mean) and mr_mean > 0:
            paras.append(('资金效率与杠杆',
                          f"资金占用/现货全额均值 {mr_mean:.2f}"
                          f"（最优 {self._fmt(mr_best, '{:.2f}')}），"
                          f"相当于约 {1 / mr_mean:.1f} 倍资金杠杆。"
                          f"注意：合成头寸的'本金'是卖出腿保证金，"
                          f"标的剧烈波动时保证金会动态上调（追缴风险），"
                          f"实际杠杆低于名义值，请按压力情景预留追加资金。"))

        # ---- 3. 信号结构解读 ----
        sig = stats['signal_counts']
        n_strong = sig.get('STRONG_BUY', 0) + sig.get('BUY', 0)
        n_avoid = sig.get('AVOID', 0)
        if n_strong > 0:
            paras.append(('信号结构解读',
                          f"最新交易日 STRONG_BUY/BUY 合计 {n_strong} 个、AVOID {n_avoid} 个"
                          f"（共 {stats['n_combos_latest']} 个组合）。"
                          f"合成偏离本质是平价关系偏差——落地前务必核对双腿盘口宽度与成交深度，"
                          f"偏离的大部分通常被买卖价差与冲击成本吞噬。"))
        else:
            paras.append(('信号结构解读',
                          f"最新交易日无 STRONG_BUY/BUY 信号——合成成本不具吸引力，"
                          f"维持现货/融券原路径即可，本策略保持观察。"))

        # ---- 4. 风险清单 ----
        risk_items = []
        if stats['n_delta_fail_latest'] > 0:
            risk_items.append(f"Delta校验失败 {stats['n_delta_fail_latest']} 个配对（虚值档报价失真，已剔除信号）")
        if stats['n_expiry_soon'] > 0:
            risk_items.append(f"距到期<10天的组合 {stats['n_expiry_soon']} 个（Pin risk，需强平或展期）")
        if str(stats['latest_date'])[4:6] in ('11', '12'):
            risk_items.append("当前处于 ETF 分红季（11~12月），股息率 q 的估计误差直接进入合成成本，偏离解读需保守")
        if self.DIRECTION < 0:
            risk_items.append("合成空头上行亏损不封顶——务必设定止损与保证金压力预案")
        else:
            risk_items.append("合成多头下行亏损不封顶（近似持有现货）——卖出Put腿需全程盯市")
        paras.append(('风险清单', '；'.join(risk_items) + '。'))

        return paras

    # ===================== PDF 样式与组装 =====================

    def _build_pdf_styles(self):
        styles = getSampleStyleSheet()
        return {
            'title': ParagraphStyle('ReportTitle', parent=styles['Heading1'],
                                    fontSize=22, leading=30, alignment=1,
                                    fontName=self.reportlab_font, spaceAfter=24),
            'h1': ParagraphStyle('H1', parent=styles['Heading1'], fontSize=16, leading=22,
                                 fontName=self.reportlab_font, spaceAfter=10, spaceBefore=10),
            'normal': ParagraphStyle('Normal', parent=styles['Normal'], fontSize=10,
                                     leading=15, fontName=self.reportlab_font),
            'cover_info': ParagraphStyle('CoverInfo', parent=styles['Normal'], fontSize=13,
                                         leading=20, alignment=1, fontName=self.reportlab_font,
                                         textColor=colors.HexColor('#333333')),
            'table_note': ParagraphStyle('TableNote', parent=styles['Normal'], fontSize=8,
                                         leading=11, fontName=self.reportlab_font,
                                         textColor=colors.HexColor('#666666')),
        }

    # ===================== 列宽自适应(替代写死宽度, 防截断) =====================

    @staticmethod
    def _text_width(text, font_size):
        """估算字符串显示宽度(pt)

        CJK/全角字符按 1.05em、半角(数字/字母/符号)按 0.58em 估算,
        微软雅黑下表头中文与数字串的实测宽度均落在此保守估计内。
        """
        width = 0.0
        for ch in str(text):
            width += font_size * (1.05 if ord(ch) > 0x2E7F else 0.58)
        return width

    def _calc_col_widths(self, header, rows, total_width, font_size=None,
                         min_width=None, cell_padding=3.0):
        """按内容自适应计算列宽

        规则:
            1. 每列取「表头 + 全部单元格」中的最宽文本 + 内边距, 作为需求宽度;
            2. 需求合计不足页面宽度时, 按需求比例放大(内容长的列获得更多空间);
            3. 超出页面宽度时按比例压缩, 但每列不低于 min_width;
            4. 触底后仍超宽, 对可压缩列等额收回超出部分。

        Args:
            header: 表头字符串列表
            rows: 数据行(与表头等长的字符串列表)
            total_width: 可用页面宽度(pt)
            font_size: 字号(pt), 默认 DETAIL_TABLE_FONT_SIZE
            min_width: 每列最小宽度, 默认 DETAIL_TABLE_MIN_COL_WIDTH
        """
        font_size = font_size or self.DETAIL_TABLE_FONT_SIZE
        min_width = min_width or self.DETAIL_TABLE_MIN_COL_WIDTH
        n_cols = len(header)
        if n_cols == 0:
            return []

        need = []
        for ci in range(n_cols):
            head_w = self._text_width(header[ci], font_size)
            cell_w = max((self._text_width(row[ci], font_size) for row in rows),
                         default=0.0)
            need.append(max(cell_w, head_w) + cell_padding)
        need = [max(w, min_width) for w in need]

        total_need = sum(need)
        if total_need <= 0:
            return [total_width / n_cols] * n_cols

        scale = total_width / total_need
        if total_need < total_width:
            # 有余量: 按需求比例放大, 提升可读性
            widths = [w * scale for w in need]
        else:
            # 超宽: 压缩后再对触底列等额回收
            widths = [max(w * scale, min_width) for w in need]
            overflow = sum(widths) - total_width
            if overflow > 0:
                flexible = [ci for ci, w in enumerate(widths) if w > min_width]
                if flexible:
                    shrink = overflow / len(flexible)
                    for ci in flexible:
                        widths[ci] = max(widths[ci] - shrink, min_width)
        return widths

    def _make_table(self, header, rows, col_widths=None, font_size=None):
        """统一样式表格（信号列着色; 收紧内边距给内容留足横向空间）"""
        font_size = font_size or self.DETAIL_TABLE_FONT_SIZE
        data = [header] + rows
        table = Table(data, colWidths=col_widths, repeatRows=1)
        style_cmds = [
            ('FONTNAME', (0, 0), (-1, -1), self.reportlab_font),
            ('FONTSIZE', (0, 0), (-1, -1), font_size),
            ('LEFTPADDING', (0, 0), (-1, -1), 1.5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 1.5),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#D9D9D9')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.white, colors.HexColor('#EBF1F8')]),
        ]
        if '信号' in header:
            sig_col = header.index('信号')
            for ri, row in enumerate(rows, start=1):
                cell_bg = self.SIGNAL_COLORS.get(str(row[sig_col]).strip())
                if cell_bg:
                    style_cmds.append(('BACKGROUND', (sig_col, ri), (sig_col, ri),
                                       colors.HexColor(cell_bg)))
        table.setStyle(TableStyle(style_cmds))
        return table

    def _generate_pdf_report(self, df, chart_buffers, config):
        styles = self._build_pdf_styles()
        stats = self._build_overview_numbers(df)
        latest_date, latest = self._latest_snapshot(df)

        report_date = datetime.now().strftime('%Y-%m-%d %H:%M')
        now_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        symbol_filter = config.get('symbol_filter')
        tag = symbol_filter.rstrip('%') if symbol_filter else 'ALL'
        date_tag = f"{stats['date_start']}-{stats['date_end']}"
        pdf_path = os.path.join(
            self.REPORT_DIR,
            f"{self.STRATEGY_TYPE}_{tag}_{date_tag}_{now_ts}.pdf")

        doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4),
                                rightMargin=32, leftMargin=32, topMargin=36, bottomMargin=28)
        # 页宽略放宽(左右各32pt), 给17列明细表留出更多横向空间
        page_width = landscape(A4)[0] - 64
        story = []

        # ===== 封面 =====
        story.append(Spacer(1, 1.4 * inch))
        story.append(Paragraph(self.REPORT_TITLE, styles['title']))
        story.append(Paragraph(self.REPORT_SUBTITLE,
                               ParagraphStyle('Sub', parent=styles['normal'], alignment=1,
                                              fontSize=11, fontName=self.reportlab_font,
                                              textColor=colors.HexColor('#888888'))))
        story.append(Spacer(1, 0.35 * inch))

        dirn = float(self.DIRECTION)
        cover_text = (
            f"策略口径：{self.STRATEGY_CN} = "
            f"{'买 Call(K,T) + 卖 Put(K,T)，净成本 C−P' if dirn > 0 else '卖 Call(K,T) + 买 Put(K,T)，净收入 C−P'}<br/>"
            f"理论定价（平价关系）：C − P = S·e^(−qT) − K·e^(−rT)<br/>"
            f"数据区间：{stats['date_start']} — {stats['date_end']}（{stats['n_days']} 个交易日）<br/>"
            f"报告生成时间：{report_date}<br/>"
            f"数据记录：{stats['n_rows']} 条 | 行权价档：{stats['n_strikes']} 个 | "
            f"最新日组合：{stats['n_combos_latest']} 个（Delta校验通过 {stats['n_pass_latest']}）<br/>"
            f"<br/>INFINITY 量化系统 · 期权策略研究"
        )
        story.append(Paragraph(cover_text, styles['cover_info']))
        story.append(PageBreak())

        # ===== 一、数据概览 =====
        story.append(Paragraph('一、数据概览（关键数字）', styles['h1']))
        overview_text = (
            f"最新交易日 {stats['latest_date']}：{stats['n_pass_latest']} 个 Delta 校验通过的有效组合中，"
            f"合成偏离均值 {self._fmt(stats['dev_mean'], '{:+.3f}')}%S、"
            f"极值 {self._fmt(stats['dev_absmax'], '{:.3f}')}%S；"
            f"隐含融资利率均值 {self._fmt(stats['r_impl_mean'], '{:.4f}')}，"
            f"融资利差均值 {self._fmt(stats['spread_mean'], '{:+.1f}')}bp、"
            f"最优 {self._fmt(stats['spread_min'], '{:+.1f}')}bp；"
            f"资金占用/现货全额均值 {self._fmt(stats['margin_ratio_mean'], '{:.2f}')}。"
            f"信号分布："
            + '、'.join(f"{k} {v} 个" for k, v in sorted(stats['signal_counts'].items()))
            + "。"
        )
        story.append(Paragraph(overview_text, styles['normal']))
        story.append(PageBreak())

        # ===== 二、最新交易日最优组合明细 =====
        header, rows = self._build_detail_table_data(latest)
        # 小标题带上当日标的现货价(表内所有以S为基准的比率都依赖它, 缺了无法解释读数)
        spot_desc = self._latest_spot_desc(latest)
        story.append(Paragraph(
            f'二、最新交易日（{latest_date}）最优组合明细（按评分降序 Top {self.DETAIL_TABLE_ROWS}）'
            + (f'　|　标的现货 S = {spot_desc}' if spot_desc else ''),
            styles['h1']))
        if rows:
            # 列宽按内容自适应(表头+全部单元格取最宽), 不再写死固定宽度——
            # 写死时17列中未固定列仅剩约22pt, 数值/合约名会被截断重叠
            col_widths = self._calc_col_widths(header, rows, page_width,
                                               self.DETAIL_TABLE_FONT_SIZE)
            story.append(self._make_table(header, rows, col_widths,
                                          font_size=self.DETAIL_TABLE_FONT_SIZE))
            story.append(Spacer(1, 0.08 * inch))
            story.append(Paragraph(
                '注1（成本口径，逐项说明）：'
                'a) S现货 = 标的当日收盘价，表内所有以 S 为基准的比率'
                '（理论成本、偏离%S、资金/现货、平衡点%）都以它计算，可与 K 直接比较判断虚实值；<br/>'
                'b) Call价C / Put价P = 双腿每张合约的单位权利金（元/份 或 指数点），'
                '×合约乘数即每张人民币金额；<br/>'
                'c) 净成本C−P = Call价C − Put价P'
                + ('（多头=净支出）' if dirn > 0 else '（空头=净收入）')
                + '；<br/>'
                'd) 理论成本 = S·e^(−qT) − K·e^(−rT)（平价关系给出的公允合成成本）；<br/>'
                'e) 偏离% = (净成本 − 理论成本)/S0（正=合成贵）。',
                styles['table_note']))
            story.append(Paragraph(
                '注2（资金与风险口径，逐项说明）：'
                'a) 隐含利率 r_impl：由 C−P = S·e^(−qT) − K·e^(−r_impl·T) 反推，'
                '是市场自己报出的“合成融资价格”；<br/>'
                '　　r_impl＜0 = 市场隐含的资金成本为负，常见成因：① 标的临近分红（市场定价的 q 高于参数）；'
                '② 融券成本高/卖空受限（用买Put卖Call替代融券，压低C−P）；③ 低流动性档位结算价失真；<br/>'
                '　　方向含义：对合成多头=“倒贴融资”（利多）；对合成空头=收价偏低（利空）；<br/>'
                'b) 利差bp = (r_impl − r)×1e4：越负对合成多头越有利（空头相反）；<br/>'
                'c) 净Δ = 该组合对标的的等效暴露（买C卖P应≈+1、卖C买P应≈−1）；'
                '|净Δ∓1|＞0.15 判为脏配对（虚值档报价失真/数据错位），已从信号中剔除（见Δ校验列）；<br/>'
                'd) 资金/现货 = (卖出腿保证金粗估 + 买入腿全额权利金) ÷ 现货全额：'
                '＜1 表示比全额买现货/融券更省资金，其倒数≈资金杠杆；'
                '保证金会随波动动态上调，需按压力情景预留追加资金；<br/>'
                'e) 净Γ = 组合Gamma：双腿同K同T，理论精确=0；非零是两腿IV失配/报价失真的'
                '量化证据，越接近0配对越干净；<br/>'
                'f) 净Vega = 组合Vega：理论精确=0（平价关系与波动率无关）；|净Vega|越大，'
                '偏离越可能来自波动率面而非资金面，信号可信度越低；<br/>'
                'g) 净Θ = 组合Theta：理论≈(qS·e^(−qT) − rK·e^(−rT))/365，即股息与资金成本'
                '之差的日摊（量级极小）；显著偏离多为单腿数据异常。',
                styles['table_note']))
            story.append(Paragraph(
                '注3：评分 = '
                + ('−偏离%（多头越便宜分越高）' if dirn > 0 else '+偏离%（空头卖出收价越高分越高）')
                + '；Call/Put 合约列显示 opt_basic 实际名称。',
                styles['table_note']))
        else:
            story.append(Paragraph('最新交易日无有效组合数据。', styles['normal']))
        story.append(PageBreak())

        # ===== 三~六、图表（各配数字说明） =====
        chart_sections = []
        if chart_buffers.get('chart1'):
            chart_sections.append(('chart1', '图1：合成偏离时序（0 轴=平价理论）',
                                   f"日均偏离 {self._fmt(stats['dev_mean'], '{:+.3f}')}%S、"
                                   f"极值 {self._fmt(stats['dev_absmax'], '{:.3f}')}%S。"
                                   "持续单向偏离=系统性（资金面/分红预期），"
                                   "围绕0轴震荡=流动性噪声，与IV关系不大——"
                                   "这是合成策略与波动率策略的读图差异。"))
        if chart_buffers.get('chart2'):
            chart_sections.append(('chart2', '图2：隐含融资利率 vs 基准利率',
                                   f"最新隐含利率均值 {self._fmt(stats['r_impl_mean'], '{:.4f}')}、"
                                   f"利差 {self._fmt(stats['spread_mean'], '{:+.1f}')}bp。"
                                   "蓝线持续低于红虚线=合成便宜（多头视角利多）；"
                                   "持续高于=资金面偏紧。此图即市场的'隐含资金价格'温度计。"))
        if chart_buffers.get('chart3'):
            chart_sections.append(('chart3', '图3：资金效率时序',
                                   f"资金占用/现货均值 {self._fmt(stats['margin_ratio_mean'], '{:.2f}')}、"
                                   f"最优 {self._fmt(stats['margin_ratio_best'], '{:.2f}')}。"
                                   "低于0.3说明合成路径用三成资金获得等价敞口——"
                                   "但保证金会随波动上调，勿按名义杠杆满仓。"))
        if chart_buffers.get('chart4'):
            chart_sections.append(('chart4', '图4：到期损益结构（最优组合 + 评分次优组合对照）',
                                   "蓝实线为评分最优组合的到期P&L，其余彩色虚线为评分次优的"
                                   f"前 {self.PAYOFF_PROFILE_ROWS} 个组合（横轴刻度已细化，"
                                   "右端标注每组双腿的实际合约名称），灰点划线为现货对照——"
                                   "所有线几乎平行，直观展示'合成=复制现货'的本质，"
                                   "平行线之间的垂直间距即各组合的净成本C−P差异；"
                                   "红点即最优组合的盈亏平衡，与现货的成本分界。"))

        for i, (key, title, note) in enumerate(chart_sections):
            section_cn = ['三', '四', '五', '六', '七', '八'][i] if i < 6 else str(i + 3)
            story.append(Paragraph(f'{section_cn}、{title}', styles['h1']))
            story.append(Spacer(1, 0.08 * inch))
            buf = chart_buffers.get(key)
            if buf is not None:
                img = RLImage(buf)
                w0, h0 = float(img.imageWidth), float(img.imageHeight)
                scale = min(page_width / w0, 390 / h0)
                img.drawWidth = w0 * scale
                img.drawHeight = h0 * scale
                story.append(img)
            story.append(Spacer(1, 0.08 * inch))
            story.append(Paragraph(note, styles['normal']))
            story.append(PageBreak())

        # ===== 资深交易员综合点评 =====
        next_cn = str(len(chart_sections) + 3)
        story.append(Paragraph(f'{next_cn}、资深交易员综合点评（自动生成）', styles['h1']))
        for title, text in self._build_trader_commentary(df, stats):
            story.append(Paragraph(f'<b>{title}</b>', styles['h1']))
            story.append(Paragraph(text, styles['normal']))
            story.append(Spacer(1, 0.10 * inch))
        story.append(PageBreak())

        # ===== 指标口径 =====
        story.append(Paragraph(f'{int(next_cn) + 1}、指标口径', styles['h1']))
        glossary = (
            f"策略定义：{self.STRATEGY_CN} = "
            + ('买Call(K,T)+卖Put(K,T)' if dirn > 0 else '卖Call(K,T)+买Put(K,T)')
            + "，同月同K、ATM±5档配对，净Delta≈±1。<br/>"
            "净成本 C−P：多头为净支出、空头为净收入（卖出收款）。<br/>"
            "理论成本 = S·e^(−qT) − K·e^(−rT)（平价关系，含股息贴现）。<br/>"
            "合成偏离 = (C−P) − 理论成本：正=合成贵、负=合成便宜，评分的核心输入。<br/>"
            "隐含融资利率 r_impl = −ln((S·e^(−qT)−(C−P))/K)/T年：市场为'借钱买现货'定价的资金利率。<br/>"
            "利差bp = (r_impl−r)×1e4：多头视角越负越便宜；空头视角为卖出收价的含金量。<br/>"
            "保证金粗估（卖出腿）= 权利金 + max(12%×S − 虚值额, 7%×S)，交易所公式近似。<br/>"
            "资金占用 = 卖出腿保证金 + 买入腿全额权利金；资金/现货 = 资金占用÷现货全额。<br/>"
            "净Greeks：净Δ≈±1（校验闸门）；净Γ/净Vega 理论精确=0（平价关系对σ求导为零），"
            "非零=两腿IV失配或报价失真，是偏离可信度的第二道读数；"
            "净Θ≈(qS·e^(−qT) − rK·e^(−rT))/365，持有成本的日摊，量级极小。<br/>"
            "情景收益率以资金占用为本金（非权利金口径）——合成策略的杠杆叙事基础。<br/>"
            "信号：基于偏离/利差阈值 + Delta校验一票否决 + 临近到期/分红季风控标注。"
        )
        story.append(Paragraph(glossary, styles['normal']))
        story.append(Spacer(1, 0.15 * inch))

        # ===== 风险提示 =====
        story.append(Paragraph(f'{int(next_cn) + 2}、风险提示', styles['h1']))
        risk_text = (
            "本报告基于期权日线收盘价与 BS 框架参数计算，仅供策略研究参考，不构成投资建议。<br/>"
            "非有限亏损：合成头寸含卖出腿，保证金随波动动态上调，"
            + ("多头下行" if dirn > 0 else "空头上行")
            + "亏损不封顶，请务必预留追加保证金并设定止损。<br/>"
            "偏离≠可执行：观察到的合成偏离通常被双腿买卖价差、冲击成本与保证金成本吞噬，"
            "落地前必须核对盘口深度。<br/>"
            "股息敏感性：合成成本对 q 的估计误差天然敏感（分红季 11~12 月尤甚），"
            "偏离信号在换季时应重新评估。<br/>"
            "行权方式：ETF期权为欧式；若扩展到 CFFES 股指期权（美式），"
            "提前指派会改变合成头寸现金流时点，本口径需修正。<br/>"
            "保证金模型：卖出腿保证金为交易所公式粗估，与实际逐日盯市存在差异，"
            "实际资金占用请以经纪商结算为准。"
        )
        story.append(Paragraph(risk_text, styles['normal']))

        doc.build(story)
        logger.info(f"PDF 报告已生成: {pdf_path}")
        return pdf_path

    # ===================== 主流程 =====================

    def run(self, config):
        """运行报告生成主流程

        Args:
            config: dict with keys:
                - name / start_date / end_date / symbol_filter (optional)

        Returns:
            pdf_path or None
        """
        name = config.get('name', 'Unknown')
        symbol_filter = config.get('symbol_filter')

        end_date = config.get('end_date') or CommonParameters.today
        start_date = config.get('start_date')
        if not start_date:
            start_dt = datetime.strptime(end_date, '%Y%m%d') \
                - timedelta(days=self.DEFAULT_LOOKBACK_DAYS)
            start_date = start_dt.strftime('%Y%m%d')

        self.writeLogInfo(className=self.__class__.__name__,
                          functionName="run",
                          event=f"Generating {self.__class__.__name__}: {name}")

        job_logger = ReportJobLogger()
        job_logger.start_job(self.__class__.__name__, 'OptionStrategyReport',
                             params={'report_name': config.get('name'),
                                     'start_date': start_date,
                                     'end_date': end_date,
                                     'symbol_filter': symbol_filter})

        try:
            # Step 1: 拉取数据
            logger.info(f"Step 1/3: 拉取 {self.TABLE_SOURCE} 数据 "
                        f"(symbol_filter={symbol_filter}, [{start_date}, {end_date}])")
            df = self.fetch_data(start_date=start_date, end_date=end_date,
                                 symbol_filter=symbol_filter)
            if df.empty:
                logger.warning("数据为空（请先运行 SyntheticStockStrategyAnalysisTest 落库），流程终止")
                job_logger.end_job_success(records_processed=0)
                return None

            # Step 2: 清洗 + 图表
            logger.info("Step 2/3: 数据清洗 & 生成图表")
            df = self.clean_data(df)

            chart_buffers = {}
            chart_buffers['chart1'] = self.gen_chart1_deviation_timeseries(df)
            chart_buffers['chart2'] = self.gen_chart2_implied_rate(df)
            chart_buffers['chart3'] = self.gen_chart3_capital_efficiency(df)
            chart_buffers['chart4'] = self.gen_chart4_payoff_profile(df)

            chart_count = sum(1 for v in chart_buffers.values() if v is not None)
            logger.info(f"图表生成完成: {chart_count} 张")

            # Step 3: 生成 PDF
            logger.info("Step 3/3: 生成 PDF 报告")
            pdf_path = self._generate_pdf_report(df, chart_buffers, config)

            logger.info("\n" + "=" * 80)
            logger.info(f"[{name}] {self.STRATEGY_CN} 报告 生成完成！")
            logger.info(f"   Report: {pdf_path}")
            logger.info(f"   Data rows: {len(df)}")
            logger.info(f"   Charts: {chart_count} 张")
            logger.info("=" * 80)
            job_logger.end_job_success(records_processed=len(df))

            return pdf_path

        except Exception as e:
            logger.error(f"报告生成失败: {e}")
            logger.error(traceback.format_exc())
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise

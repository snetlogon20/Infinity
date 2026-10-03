r"""
Bear Put Spread（熊市看跌价差）策略 PDF 报告生成器 — 资深交易员/风控视角

数据源：
    tb_option_trading_strategy_bear_put_spread (strategy_type='BEAR_PUT_SPREAD',
    由 BearPutSpreadStrategyAnalysis 写入，含 analysis_time/analysis_params 审计字段)

报告结构：
    封面 → 数据概览(数字) → 最新交易日组合总览(表格, 按评分排名) → 10张图表(各配数字说明)
    → 交易信号汇总(表格) → 资深交易员综合点评(自动生成, 含数字) → 指标口径 → 风险提示

核心图表：
    图6 教科书三线到期收益结构图（买入腿/卖出腿/组合）——
    左侧最大盈利平台 P=(K2-K1)-D（S_T<=K1）、右侧最大亏损平台 L=-D（S_T>=K2）、
    盈亏平衡点 B=K2-D（镜像于 Bull Call Spread）

输出：
    PDF → CommonParameters.optionAnalysisReportPath
    (D:\workspace_python\infinity_data\outbound\report\OptionAnalysis)
"""

import io
import os
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
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
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

logger = CommonLib.logger

# 中文字体支持（matplotlib）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class BearPutSpreadStrategyReport:
    """Bear Put Spread 策略 报告生成器"""

    REPORT_DIR = CommonParameters.optionAnalysisReportPath
    TABLE_SOURCE = 'tb_option_trading_strategy_bear_put_spread'
    STRATEGY_TYPE = 'BEAR_PUT_SPREAD'

    # 情景因子（与分析端 DEFAULT_SCENARIOS 一致，S_T = K2 × factor，下行为主）
    SCENARIO_FACTORS = [0.85, 0.90, 0.95, 1.00, 1.03, 1.05, 1.10, 1.15]

    CHART_COLORS = [
        '#e74c3c', '#3498db', '#2ecc71', '#9b59b6', '#f39c12',
        '#1abc9c', '#e67e22', '#2980b9', '#c0392b', '#27ae60',
        '#8e44ad', '#d35400', '#16a085', '#2c3e50', '#7f8c8d',
        '#f1c40f', '#00bcd4', '#ff5722', '#795548', '#607d8b',
    ]

    SPOT_COLOR = '#1a1a2e'
    UNHEDGED_COLOR = '#7f8c8d'

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
                    logger.info(f"✅ ReportLab 加载中文字体: {font_name}")
                    break
                except Exception as e:
                    logger.warning(f"⚠️ 字体加载失败 {font_path}: {e}")
        if reportlab_font == 'Helvetica':
            logger.warning("⚠️ ReportLab 未找到中文字体，PDF中文可能无法正常显示")
        return reportlab_font

    def writeLogInfo(self, className="unknown", functionName="unknown", event="unknown"):
        logger.info("%s.%s: %s" % (className, functionName, event))

    # ===================== 数据获取 =====================

    def fetch_data(self, start_date=None, end_date=None, symbol_filter=None, call_put='P'):
        """从 tb_option_trading_strategy_bear_put_spread 拉取 BEAR_PUT_SPREAD 策略分析结果"""
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName="fetch_data",
                          event=f"Fetching data from {self.TABLE_SOURCE}")

        where_clauses = [f"strategy_type = '{self.STRATEGY_TYPE}'"]
        if start_date:
            where_clauses.append(f"trade_date >= '{start_date}'")
        if end_date:
            where_clauses.append(f"trade_date <= '{end_date}'")
        if symbol_filter:
            where_clauses.append(f"symbol LIKE '{symbol_filter}'")
        if call_put:
            where_clauses.append(f"call_put = '{call_put}'")

        where_str = " AND ".join(where_clauses)
        sql = f"""
        SELECT *
        FROM indexsysdb.{self.TABLE_SOURCE}
        WHERE {where_str}
        ORDER BY trade_date, exercise_price, exercise_price_short
        """
        logger.info(f"SQL:\n{sql}")
        df = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        logger.info(f"Fetched {len(df)} rows, {len(df.columns)} columns")
        return df

    def clean_data(self, df):
        """类型转换与派生列（combo_key = "K2/K1" 作为组合唯一标识）"""
        numeric_cols = [
            'exercise_price', 'exercise_price_short', 'opt_multiplier', 'spot_price',
            'premium', 'premium_short', 'implied_vol', 'implied_vol_short',
            'iv_rank', 'iv_rank_short',
            'delta', 'gamma', 'theta', 'vega',
            'delta_short', 'gamma_short', 'theta_short', 'vega_short',
            'bs_theoretical_price', 'bs_theoretical_price_short',
            'close_vs_theoretical', 'close_vs_theoretical_pct',
            'close_vs_theoretical_short', 'close_vs_theoretical_pct_short',
            'net_delta', 'net_gamma', 'net_theta', 'net_vega',
            'spread_width', 'spread_width_pct',
            'net_debit', 'net_debit_cny', 'net_debit_pct_of_spot', 'net_debit_pct_of_width',
            'max_profit', 'max_profit_cny', 'max_profit_pct_of_spot', 'roi_max_pct',
            'max_loss', 'max_loss_cny', 'max_loss_pct_of_spot', 'reward_risk_ratio',
            'breakeven_S_T', 'breakeven_downside_pct',
            'win_prob', 'expected_value', 'score', 'combo_rank',
            'risk_free_rate', 'dividend_yield',
        ] + [f'scenario_pnl_{f:.2f}'.replace('.', '_') + suf
             for f in self.SCENARIO_FACTORS for suf in ('', '_cny', '_pct')] \
          + [f'unhedged_pnl_{f:.2f}'.replace('.', '_') + suf
             for f in self.SCENARIO_FACTORS for suf in ('', '_pct')]

        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        if 'days_to_maturity' in df.columns:
            df['days_to_maturity'] = pd.to_numeric(df['days_to_maturity'], errors='coerce').astype('Int64')

        # 组合唯一标识："K2/K1"（高行权价/低行权价，如 "3.0/2.95"）
        df['combo_key'] = (df['exercise_price'].map(lambda v: f'{v:.4g}') + '/'
                           + df['exercise_price_short'].map(lambda v: f'{v:.4g}'))

        df = df.sort_values(['combo_key', 'trade_date']).reset_index(drop=True)
        df['trade_date_dt'] = pd.to_datetime(df['trade_date'], format='%Y%m%d', errors='coerce')
        return df

    # ===================== 通用工具 =====================

    def _fig_to_bytesio(self, fig, dpi=160):
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        return buf

    def _prep_series(self, df, value_cols):
        """按 combo_key 构建 {combo_key: DataFrame(index=trade_date_dt)}"""
        combo_keys = sorted(df['combo_key'].dropna().unique())
        series_dict = {}
        valid = set()
        for key in combo_keys:
            sub = df[df['combo_key'] == key]
            for col in value_cols:
                if col in sub.columns and sub[col].notna().sum() > 0:
                    valid.add(key)
                    break
        for key in sorted(valid):
            series_dict[key] = df[df['combo_key'] == key].set_index('trade_date_dt')
        return sorted(valid), series_dict

    def _add_end_labels(self, ax, combo_keys, series_dict, y_col,
                        colors=None, x_pad_frac=0.14, label_fontsize=7):
        """折线右端打组合名称标签"""
        if colors is None:
            colors = self.CHART_COLORS
        xlim = ax.get_xlim()
        if xlim[1] > xlim[0]:
            ax.set_xlim(xlim[0], xlim[1] + (xlim[1] - xlim[0]) * x_pad_frac)
        for idx, key in enumerate(combo_keys):
            if key not in series_dict:
                continue
            sub = series_dict[key]
            if y_col not in sub.columns:
                continue
            s = sub[y_col].dropna()
            if len(s) == 0:
                continue
            color = colors[idx % len(colors)]
            ax.annotate(
                key,
                xy=(s.index[-1], s.iloc[-1]),
                xytext=(6, 0), textcoords='offset points',
                color=color, fontsize=label_fontsize, fontweight='bold',
                va='center', ha='left',
                bbox=dict(boxstyle='round,pad=0.18', facecolor='white',
                          edgecolor=color, linewidth=0.5, alpha=0.85),
                zorder=10,
            )

    def _best_combo_latest(self, df):
        """最新交易日评分最高的组合（combo_rank=1）"""
        latest_date = df['trade_date'].max()
        latest = df[df['trade_date'] == latest_date]
        if latest.empty:
            return latest_date, None
        cand = latest.dropna(subset=['score'])
        if cand.empty:
            return latest_date, None
        best = cand.loc[cand['score'].idxmax()]
        return latest_date, best

    # ===================== 图表生成 =====================

    def _gen_metric_chart(self, df, y_col, y_label, chart_num, title_prefix,
                          y2_col=None, y2_label=None, ref_lines=None, ref_lines2=None):
        """通用时间序列图：X=trade_date，每组合一条线（可选第二指标轴）"""
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName=f"gen_chart{chart_num}",
                          event=f"Generating chart {chart_num}: {y_label}")

        value_cols = [y_col] + ([y2_col] if y2_col else [])
        combo_keys, series_dict = self._prep_series(df, value_cols)
        if not combo_keys:
            logger.warning(f"No valid combo for chart {chart_num}, skipping")
            return None

        fig, ax1 = plt.subplots(figsize=(20, 8))
        fig.suptitle(title_prefix, fontsize=14, fontweight='bold', color='#1a1a2e')

        for idx, key in enumerate(combo_keys):
            sub = series_dict[key]
            if y_col in sub.columns and sub[y_col].notna().sum() > 0:
                s = sub[y_col].dropna()
                color = self.CHART_COLORS[idx % len(self.CHART_COLORS)]
                ax1.plot(s.index.tolist(), s.values, color=color, linewidth=1.0,
                         alpha=0.8, marker='o', markersize=3, label=key)

        ax1.set_ylabel(y_label, fontsize=11)
        ax1.grid(True, alpha=0.3, linestyle='--')
        ax1.axhline(y=0, color='gray', linewidth=0.5, linestyle='-', alpha=0.5)

        if ref_lines:
            for y_val, clr, lst, txt in ref_lines:
                ax1.axhline(y=y_val, color=clr, linewidth=1.0, linestyle=lst, alpha=0.7)
                ax1.text(0.005, y_val, txt, transform=ax1.get_yaxis_transform(),
                         fontsize=7.5, color=clr, va='bottom')

        ax2 = None
        if y2_col:
            ax2 = ax1.twinx()
            for idx, key in enumerate(combo_keys):
                sub = series_dict[key]
                if y2_col in sub.columns and sub[y2_col].notna().sum() > 0:
                    s = sub[y2_col].dropna()
                    color = self.CHART_COLORS[idx % len(self.CHART_COLORS)]
                    ax2.plot(s.index.tolist(), s.values, color=color, linewidth=0.8,
                             alpha=0.55, linestyle='--', marker='s', markersize=2)
            ax2.set_ylabel(y2_label, fontsize=11)
            ax2.axhline(y=0, color='gray', linewidth=0.4, linestyle='-', alpha=0.3)
            if ref_lines2:
                for y_val, clr, lst, txt in ref_lines2:
                    ax2.axhline(y=y_val, color=clr, linewidth=1.0, linestyle=lst, alpha=0.7)

        self._add_end_labels(ax1, combo_keys, series_dict, y_col)

        lines, labels = ax1.get_legend_handles_labels()
        n_items = len(lines)
        if n_items > 0:
            ncol = min(n_items, 8)
            ax1.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12),
                       fontsize=6.5, ncol=ncol, frameon=True, borderaxespad=0.5,
                       handlelength=1.2)

        fig.autofmt_xdate(rotation=45, ha='right')
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    def gen_chart1_spot_net_debit(self, df):
        """图1：现货价(Y1) + 各组合净支出 D=Y2（花了多少）"""
        combo_keys, series_dict = self._prep_series(df, ['spot_price', 'net_debit'])
        if not combo_keys:
            return None

        fig, ax1 = plt.subplots(figsize=(20, 8))
        fig.suptitle('图1：标的现货价格 + 各价差组合净支出 D = P2-P1',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        # Y1: spot
        spot_series = None
        for key in combo_keys:
            sub = series_dict[key]
            if 'spot_price' in sub.columns and sub['spot_price'].notna().sum() > 0:
                spot_series = sub['spot_price']
                break
        if spot_series is not None:
            s = spot_series.dropna()
            ax1.plot(s.index.tolist(), s.values, color=self.SPOT_COLOR, linewidth=2.2,
                     marker='o', markersize=4, alpha=0.95, label='spot_price (现货)')
            ax1.annotate('spot_price', xy=(s.index[-1], s.iloc[-1]), xytext=(6, 0),
                         textcoords='offset points', color=self.SPOT_COLOR, fontsize=8,
                         fontweight='bold', va='center', ha='left',
                         bbox=dict(boxstyle='round,pad=0.18', facecolor='white',
                                   edgecolor=self.SPOT_COLOR, linewidth=0.5, alpha=0.85))
        ax1.set_ylabel('spot_price (现货价)', fontsize=11, color=self.SPOT_COLOR)
        ax1.tick_params(axis='y', labelcolor=self.SPOT_COLOR)
        ax1.grid(True, alpha=0.3, linestyle='--')

        # Y2: net_debit
        ax2 = ax1.twinx()
        for idx, key in enumerate(combo_keys):
            sub = series_dict[key]
            if 'net_debit' in sub.columns and sub['net_debit'].notna().sum() > 0:
                s = sub['net_debit'].dropna()
                color = self.CHART_COLORS[idx % len(self.CHART_COLORS)]
                ax2.plot(s.index.tolist(), s.values, color=color, linewidth=0.9,
                         alpha=0.8, marker='o', markersize=3, label=key)
        ax2.set_ylabel('净支出 D (元/单位)', fontsize=11)

        xlim = ax2.get_xlim()
        if xlim[1] > xlim[0]:
            ax2.set_xlim(xlim[0], xlim[1] + (xlim[1] - xlim[0]) * 0.14)
        for idx, key in enumerate(combo_keys):
            sub = series_dict[key]
            if 'net_debit' not in sub.columns:
                continue
            s = sub['net_debit'].dropna()
            if len(s) == 0:
                continue
            color = self.CHART_COLORS[idx % len(self.CHART_COLORS)]
            ax2.annotate(key, xy=(s.index[-1], s.iloc[-1]), xytext=(6, 0),
                         textcoords='offset points', color=color, fontsize=7,
                         fontweight='bold', va='center', ha='left',
                         bbox=dict(boxstyle='round,pad=0.18', facecolor='white',
                                   edgecolor=color, linewidth=0.5, alpha=0.85), zorder=10)

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        n_items = len(lines1) + len(lines2)
        if n_items > 0:
            ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper center',
                       bbox_to_anchor=(0.5, -0.12), fontsize=6.5,
                       ncol=min(n_items, 8), frameon=True, handlelength=1.2)

        fig.autofmt_xdate(rotation=45, ha='right')
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    def gen_chart2_iv(self, df):
        return self._gen_metric_chart(
            df, 'implied_vol', '买入腿隐含波动率 (implied_vol, 小数)',
            chart_num=2, title_prefix='图2：买入腿 隐含波动率 IV（价差成本的核心输入）')

    def gen_chart3_capital_efficiency(self, df):
        return self._gen_metric_chart(
            df, 'net_debit_pct_of_width', '净支出占宽度 D/(K2-K1) (%)',
            chart_num=3, title_prefix='图3：资本效率 — 净支出占价差宽度比例（越低越优）',
            ref_lines=[
                (50.0, '#27ae60', '--', '优质 (<=50%)'),
                (70.0, '#f39c12', '--', '中性 (=70%)'),
                (90.0, '#c0392b', '--', '低效 (>=90%)'),
            ])

    def gen_chart4_roi_winprob(self, df):
        return self._gen_metric_chart(
            df, 'roi_max_pct', '最大资金收益率 max_profit/D (%)',
            chart_num=4, title_prefix='图4：最大资金收益率(实线) + 胜率(虚线)',
            y2_col='win_prob', y2_label='胜率 P(S_T < K2-D)',
            ref_lines=[
                (15.0, '#27ae60', '--', '优质 (=15%)'),
                (50.0, '#3498db', '--', '高杠杆 (=50%)'),
            ])

    def gen_chart5_reward_risk(self, df):
        return self._gen_metric_chart(
            df, 'reward_risk_ratio', '回报风险比 max_profit/D',
            chart_num=5, title_prefix='图5：回报风险比 — 最大盈利/最大亏损',
            ref_lines=[
                (1.0, '#c0392b', '--', '盈亏平衡 (=1.0)'),
                (1.5, '#f39c12', '--', '可接受 (=1.5)'),
                (2.0, '#27ae60', '--', '优质 (=2.0)'),
            ])

    def gen_chart6_payoff_textbook(self, df):
        """图6：教科书三线到期收益结构（最新交易日评分最优组合）★核心图表

        买入腿: max(K2-S_T,0) - P2 (蓝虚线)
        卖出腿: P1 - max(K1-S_T,0) (橙虚线)
        组合:   max(K2-S_T,0) - max(K1-S_T,0) - D (红实线, 教科书厂字形截头镜像版)
        标注:   左侧最大盈利平台 P=(K2-K1)-D / 右侧最大亏损平台 L=-D / B=K2-D 盈亏平衡点
        """
        latest_date, best = self._best_combo_latest(df)
        if best is None:
            return None

        K2 = float(best['exercise_price'])        # 买入腿（高行权价）
        K1 = float(best['exercise_price_short'])  # 卖出腿（低行权价）
        P2 = float(best['premium'])
        P1 = float(best['premium_short'])
        S0 = float(best['spot_price'])
        D = P2 - P1
        width = K2 - K1
        B = K2 - D
        combo_name = best['combo_key']

        x = np.linspace(min(0.70 * S0, K1 * 0.90), max(1.15 * S0, K2 * 1.15), 400)

        payoff_long = np.maximum(K2 - x, 0) - P2          # 买入腿（高行权价 Put）
        payoff_short = P1 - np.maximum(K1 - x, 0)          # 卖出腿（低行权价 Put）
        payoff_combo = payoff_long + payoff_short          # 组合（红实线）

        fig, ax = plt.subplots(figsize=(20, 10))
        fig.suptitle(f'图6：Bear Put Spread 教科书到期收益结构 — 组合 {combo_name}'
                     f'（评分最优，{latest_date}）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        # ---- 盈亏区间着色 ----
        ax.fill_between(x, payoff_combo, 0, where=(payoff_combo > 0), color='#27ae60',
                        alpha=0.10, label='盈利区间 (S_T < K2-D)')
        ax.fill_between(x, payoff_combo, 0, where=(payoff_combo <= 0), color='#c0392b',
                        alpha=0.10, label='亏损区间 (S_T > K2-D)')

        # ---- 三条线：买入腿/卖出腿（虚线）+ 组合（红实线加粗） ----
        ax.plot(x, payoff_long, color='#3498db', linewidth=1.6, linestyle='--',
                alpha=0.85, label=f'买入腿 Put(K2={K2:.4g})：max(K2-S_T,0)-P2')
        ax.plot(x, payoff_short, color='#f39c12', linewidth=1.6, linestyle='--',
                alpha=0.85, label=f'卖出腿 Put(K1={K1:.4g})：P1-max(K1-S_T,0)')
        ax.plot(x, payoff_combo, color='#c0392b', linewidth=3.2, zorder=9,
                label='组合：max(K2-S_T,0)-max(K1-S_T,0)-D')

        # ---- 关键标注：最大盈利平台 P（左侧）/ 最大亏损平台 L（右侧） ----
        ax.axhline(y=width - D, color='#27ae60', linewidth=1.4, linestyle='--', alpha=0.9, zorder=6)
        ax.text(x[0], width - D, f' 最大盈利 P = (K2-K1)-D = {width - D:.4g}\n'
                                 f' (S_T≤K1, 盈利封顶)',
                fontsize=9.5, color='#27ae60', va='bottom', fontweight='bold')
        ax.axhline(y=-D, color='#c0392b', linewidth=1.4, linestyle='--', alpha=0.9, zorder=6)
        ax.text(x[-1], -D, f' 最大亏损 L = -D = {D:.4g}\n (S_T≥K2, 亏损封底)',
                fontsize=9.5, color='#c0392b', va='top', ha='right', fontweight='bold')

        # ---- 行权价竖线 K1/K2 ----
        ax.axvline(x=K1, color='#f39c12', linewidth=1.4, linestyle=':', alpha=0.9, zorder=6)
        ax.text(K1, 0.02, f' K1={K1:.4g}\n (卖出腿拐点)',
                transform=ax.get_xaxis_transform(), fontsize=9, color='#f39c12',
                va='bottom', fontweight='bold')
        ax.axvline(x=K2, color='#3498db', linewidth=1.4, linestyle=':', alpha=0.9, zorder=6)
        ax.text(K2, 0.02, f' K2={K2:.4g}\n (买入腿拐点)',
                transform=ax.get_xaxis_transform(), fontsize=9, color='#3498db',
                va='bottom', fontweight='bold')

        # ---- 盈亏平衡点 B = K2 - D ----
        ax.plot([B], [0], marker='o', markersize=10, color='#27ae60', zorder=11)
        ax.annotate(f'盈亏平衡点 B = K2-D = {B:.4g}\n（需下跌 {(B - S0) / S0 * 100:+.2f}%）',
                    xy=(B, 0), xytext=(16, -55), textcoords='offset points',
                    fontsize=10, fontweight='bold', color='#27ae60',
                    arrowprops=dict(arrowstyle='->', color='#27ae60', linewidth=1.2),
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                              edgecolor='#27ae60', alpha=0.9), zorder=12)

        # ---- 当前现货位置 ----
        ax.axvline(x=S0, color=self.SPOT_COLOR, linewidth=1.0, linestyle=':', alpha=0.6, zorder=5)
        ax.text(S0, 0.55, f' 当前现货 S0={S0:.4g}',
                transform=ax.get_xaxis_transform(), fontsize=9, color=self.SPOT_COLOR,
                va='center', rotation=90, alpha=0.8)

        # ---- Y 轴留白，防止平台贴边 ----
        ymin, ymax = ax.get_ylim()
        ax.set_ylim(ymin - 0.05 * (ymax - ymin), ymax + 0.05 * (ymax - ymin))

        ax.axhline(y=0, color='gray', linewidth=0.8, linestyle='-', alpha=0.6)
        ax.set_xlabel('到期标的价 S_T', fontsize=12, fontweight='bold')
        ax.set_ylabel('盈亏 (元/单位)', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10), fontsize=9,
                  ncol=3, frameon=True, handlelength=1.8)
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    def gen_chart7_scenario_pnl(self, df):
        """图7：多情景到期盈亏（最优组合 vs 买现货对照）"""
        latest_date, best = self._best_combo_latest(df)
        if best is None:
            return None

        factors = self.SCENARIO_FACTORS
        x = np.arange(len(factors))
        xticklabels = [f'{f:.2f}K2' for f in factors]

        combo_vals = [best.get(f'scenario_pnl_{f:.2f}'.replace(".", "_") + "K", np.nan)
                      for f in factors]
        unhedged_vals = [best.get(f'unhedged_pnl_{f:.2f}'.replace(".", "_") + "K", np.nan)
                         for f in factors]

        fig, ax = plt.subplots(figsize=(20, 10))
        fig.suptitle(f'图7：多情景到期盈亏（{latest_date}）— 最优组合 {best["combo_key"]} '
                     f'vs 买现货对照，X轴=S_T/K2 情景因子',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        ax.plot(x, unhedged_vals, color=self.UNHEDGED_COLOR, linewidth=2.5, linestyle='--',
                marker='D', markersize=6, alpha=0.9, label='买现货 (直接持有)')
        ax.plot(x, combo_vals, color='#c0392b', linewidth=2.8,
                marker='o', markersize=7, label=f'价差组合 {best["combo_key"]}')

        ax.axhline(y=0, color='gray', linewidth=0.8, linestyle='-', alpha=0.6)
        ax.set_xticks(x)
        ax.set_xticklabels(xticklabels, fontsize=10)
        ax.set_xlabel('情景因子 (S_T / K2)', fontsize=12, fontweight='bold')
        ax.set_ylabel('盈亏 (元/单位)', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')

        # 右端标签
        xlim = ax.get_xlim()
        if xlim[1] > xlim[0]:
            ax.set_xlim(xlim[0], xlim[1] + (xlim[1] - xlim[0]) * 0.22)
        for vals, clr, txt in [(unhedged_vals, self.UNHEDGED_COLOR, '买现货(现货)'),
                               (combo_vals, '#c0392b', f'价差{best["combo_key"]}')]:
            valid = [(xi, v) for xi, v in zip(x, vals) if pd.notna(v)]
            if not valid:
                continue
            ax.annotate(txt, xy=valid[-1], xytext=(6, 0),
                        textcoords='offset points', color=clr, fontsize=8,
                        fontweight='bold', va='center', ha='left',
                        bbox=dict(boxstyle='round,pad=0.18', facecolor='white',
                                  edgecolor=clr, linewidth=0.5, alpha=0.85), zorder=10)

        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10), fontsize=9,
                  ncol=2, frameon=True)
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    def gen_chart8_efficiency_frontier(self, df):
        """图8：组合有效前沿散点（最新交易日）：X=胜率，Y=最大资金收益率，颜色=回报风险比"""
        latest_date = df['trade_date'].max()
        latest = df[df['trade_date'] == latest_date].dropna(
            subset=['win_prob', 'roi_max_pct'])
        if latest.empty:
            return None

        fig, ax = plt.subplots(figsize=(20, 10))
        fig.suptitle(f'图8：组合有效前沿（{latest_date}）— X=胜率, Y=最大资金收益率, '
                     f'颜色=回报风险比（窄价差高胜率低赔率 vs 宽价差低胜率高赔率）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        sc = ax.scatter(latest['win_prob'], latest['roi_max_pct'],
                        c=latest['reward_risk_ratio'], cmap='RdYlGn',
                        s=180, alpha=0.85, edgecolors='#1a1a2e', linewidths=0.8,
                        zorder=8)
        cbar = fig.colorbar(sc, ax=ax, pad=0.01)
        cbar.set_label('回报风险比 max_profit/D', fontsize=11)

        # 每点标注组合名
        for _, r in latest.iterrows():
            ax.annotate(r['combo_key'], xy=(r['win_prob'], r['roi_max_pct']),
                        xytext=(7, 7), textcoords='offset points', fontsize=7.5,
                        color='#1a1a2e', fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                                  edgecolor='#95a5a6', linewidth=0.4, alpha=0.8))

        # 评分最优组合高亮
        cand = latest.dropna(subset=['score'])
        if not cand.empty:
            best = cand.loc[cand['score'].idxmax()]
            ax.scatter([best['win_prob']], [best['roi_max_pct']], marker='*',
                       s=600, color='#c0392b', edgecolors='#1a1a2e',
                       linewidths=1.2, zorder=10, label=f'评分最优 {best["combo_key"]}')

        ax.axhline(y=0, color='gray', linewidth=0.8, linestyle='-', alpha=0.6)
        ax.set_xlabel('胜率 P(S_T < K2-D)（两腿|delta|插值）', fontsize=12, fontweight='bold')
        ax.set_ylabel('最大资金收益率 max_profit/D (%)', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper left', fontsize=10, frameon=True)
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    def gen_chart9_score_timeline(self, df):
        """图9：Top5 组合评分时间序列（按最新评分选取）"""
        latest_date = df['trade_date'].max()
        latest = df[df['trade_date'] == latest_date].dropna(subset=['score'])
        if latest.empty:
            return None
        top5 = set(latest.nlargest(5, 'score')['combo_key'])
        df_top = df[df['combo_key'].isin(top5)]
        return self._gen_metric_chart(
            df_top, 'score', '综合评分 = 期望值/净支出',
            chart_num=9, title_prefix='图9：Top5 组合综合评分演变（期望值/净支出，越高越优）',
            ref_lines=[(0.0, '#c0392b', '--', '期望值临界 (=0)')])

    def gen_chart10_net_greeks(self, df):
        """图10：净 Theta/净 Vega（价差的核心优势：时间价值与波动率敞口大幅抵消）"""
        latest_date = df['trade_date'].max()
        latest = df[df['trade_date'] == latest_date]
        if latest.empty:
            return None
        # 仅保留最新评分前8的组合，避免线条过密
        cand = latest.dropna(subset=['score'])
        top_keys = set(cand.nlargest(8, 'score')['combo_key']) if not cand.empty \
            else set(latest['combo_key'])
        df_top = df[df['combo_key'].isin(top_keys)]
        return self._gen_metric_chart(
            df_top, 'net_theta', '净Theta (元/单位/日, 买腿损耗-卖腿收入)',
            chart_num=10, title_prefix='图10：净Theta(实线) + 净Vega(虚线) — '
                                      '价差对时间价值与波动率的敞口抵消',
            y2_col='net_vega', y2_label='净Vega (波动率敞口)')

    # ===================== 统计与点评（数字） =====================

    def _latest_snapshot(self, df):
        """最新交易日快照"""
        latest_date = df['trade_date'].max()
        return latest_date, df[df['trade_date'] == latest_date].copy()

    def _fmt(self, v, fmt='{:.2f}', na='N/A'):
        try:
            if v is None or (isinstance(v, float) and np.isnan(v)):
                return na
            return fmt.format(v)
        except (ValueError, TypeError):
            return na

    def _build_overview_numbers(self, df):
        """数据概览统计（资深交易员关注的关键数字）"""
        latest_date, latest = self._latest_snapshot(df)
        trade_dates = sorted(df['trade_date'].unique())
        _, best = self._best_combo_latest(df)
        stats = {
            'date_start': trade_dates[0] if trade_dates else 'N/A',
            'date_end': trade_dates[-1] if trade_dates else 'N/A',
            'n_days': len(trade_dates),
            'n_rows': len(df),
            'n_combos': df['combo_key'].nunique(),
            'latest_date': latest_date,
            'n_combos_latest': len(latest),
            'spot': float(latest['spot_price'].iloc[0]) if len(latest) else np.nan,
            'iv_mean': latest['implied_vol'].mean() if len(latest) else np.nan,
            'iv_rank_mean': latest['iv_rank'].mean() if len(latest) else np.nan,
            'net_debit_mean': latest['net_debit'].mean() if len(latest) else np.nan,
            'roi_mean': latest['roi_max_pct'].mean() if len(latest) else np.nan,
            'rr_mean': latest['reward_risk_ratio'].mean() if len(latest) else np.nan,
            'wp_mean': latest['win_prob'].mean() if len(latest) else np.nan,
            'be_downside_mean': latest['breakeven_downside_pct'].mean() if len(latest) else np.nan,
            'net_theta_mean': latest['net_theta'].mean() if len(latest) else np.nan,
            'days_min': int(latest['days_to_maturity'].min()) if len(latest) else np.nan,
            'signal_counts': latest['trade_signal'].value_counts().to_dict() if len(latest) else {},
            'best': best,
        }
        return stats

    def _build_latest_table_data(self, latest):
        """最新交易日组合总览表数据（按评分排名）"""
        rows = []
        for _, r in latest.sort_values('combo_rank').iterrows():
            rows.append([
                str(r.get('combo_key', '')),
                self._fmt(r['exercise_price'], '{:.4g}'),
                self._fmt(r['exercise_price_short'], '{:.4g}'),
                self._fmt(r['net_debit'], '{:.4g}'),
                self._fmt(r.get('spread_width_pct'), '{:.2f}'),
                self._fmt(r.get('max_profit'), '{:.4g}'),
                self._fmt(r.get('roi_max_pct'), '{:.1f}'),
                self._fmt(r.get('win_prob'), '{:.2f}'),
                self._fmt(r.get('reward_risk_ratio'), '{:.2f}'),
                self._fmt(r.get('breakeven_downside_pct'), '{:+.2f}'),
                self._fmt(r.get('net_delta'), '{:.3f}'),
                self._fmt(r.get('net_theta'), '{:.5f}'),
                self._fmt(r.get('score'), '{:.3f}'),
                str(int(r.get('combo_rank', 0))) if pd.notna(r.get('combo_rank')) else 'N/A',
                str(r.get('trade_signal', '')),
            ])
        header = ['组合 K2/K1', 'K2', 'K1', '净支出D', '宽度%', '最大盈利',
                  'ROI%', '胜率', '回报风险比', '平衡跌幅%', '净Delta', '净Theta',
                  '评分', '排名', '信号']
        return header, rows

    def _build_trader_commentary(self, df, stats):
        """资深交易员综合点评（基于数据自动生成，含具体数字）"""
        latest_date, latest = self._latest_snapshot(df)
        paras = []

        # ---- 1. 波动率环境（价差视角：vega抵消，影响有限） ----
        iv_r = stats['iv_rank_mean']
        iv_m = stats['iv_mean']
        if pd.notna(iv_r):
            if iv_r >= 0.65:
                env_txt = (f"买入腿 IV 处于近60日 {iv_r*100:.0f}% 的高分位（均值 {iv_m*100:.1f}%）。"
                           f"买方价差对 IV 敞口天然抵消（净Vega≈0），高 IV 环境的定价劣势远小于单腿买沽；"
                           f"此时若看跌，价差比裸买 Put 划算得多。")
            elif iv_r >= 0.35:
                env_txt = (f"买入腿 IV 处于近60日 {iv_r*100:.0f}% 的中性区间（均值 {iv_m*100:.1f}%），"
                           f"权利金定价公允，价差与单腿买沽的成本差距主要由宽度而非 IV 决定。")
            else:
                env_txt = (f"买入腿 IV 低至近60日 {iv_r*100:.0f}% 分位（均值 {iv_m*100:.1f}%），"
                           f"期权便宜——这是买方策略的舒适窗口。低 IV 时单腿买沽已足够便宜，"
                           f"价差的'卖腿贴补'效果相对减弱，但亏损封底的价值仍在。"
                           f"（注意：若预期 IV 将回升，单腿买沽更占优；价差适合方向确定但跌幅有限的判断。）")
            paras.append(('波动率环境判断（价差视角）', env_txt))

        # ---- 2. 最优组合推荐 ----
        best = stats['best']
        if best is not None:
            paras.append(('最优组合推荐（综合评分第一）',
                          f"组合 {best['combo_key']}（买 Put(K2={best['exercise_price']:.4g}) + "
                          f"卖 Put(K1={best['exercise_price_short']:.4g})）："
                          f"净支出 D={best['net_debit']:.4g}（占现价 "
                          f"{self._fmt(best.get('net_debit_pct_of_spot'), '{:.2f}')}%），"
                          f"最大盈利 {best['max_profit']:.4g} 元/单位"
                          f"（资金收益率 {self._fmt(best.get('roi_max_pct'), '{:.1f}')}%），"
                          f"最大亏损即净支出 {best['max_loss']:.4g} 元/单位，"
                          f"胜率≈{self._fmt(best.get('win_prob'), '{:.2f}')}，"
                          f"回报风险比 {self._fmt(best.get('reward_risk_ratio'), '{:.2f}')}，"
                          f"盈亏平衡需下跌至 {best['breakeven_S_T']:.4g}"
                          f"（跌幅 {self._fmt(best.get('breakeven_downside_pct'), '{:+.2f}')}%）。"
                          f"信号：{best.get('trade_signal', 'N/A')}。"))

        # ---- 3. 宽度选择评估（窄vs宽权衡） ----
        if len(latest.dropna(subset=['spread_width_pct', 'roi_max_pct'])) >= 2:
            cand = latest.dropna(subset=['spread_width_pct', 'roi_max_pct', 'win_prob'])
            narrow = cand.loc[cand['spread_width_pct'].idxmin()]
            wide = cand.loc[cand['spread_width_pct'].idxmax()]
            paras.append(('宽度选择评估（胜率-赔率权衡）',
                          f"最窄组合 {narrow['combo_key']}（宽度 {narrow['spread_width_pct']:.2f}%）："
                          f"胜率 {narrow['win_prob']:.2f}、ROI {narrow['roi_max_pct']:.1f}%——"
                          f"高胜率低赔率，适合'小跌'判断；"
                          f"最宽组合 {wide['combo_key']}（宽度 {wide['spread_width_pct']:.2f}%）："
                          f"胜率 {wide['win_prob']:.2f}、ROI {wide['roi_max_pct']:.1f}%——"
                          f"低胜率高赔率，适合'大跌'判断。"
                          f"熊市价差没有单一最优宽度：窄价差赚概率、宽价差赚空间，"
                          f"应结合对跌幅空间的判断自选（见图8有效前沿）。"))

        # ---- 4. Greeks 抵消优势 ----
        nt = stats['net_theta_mean']
        if pd.notna(nt):
            theta_long_mean = latest['theta'].mean()
            if pd.notna(theta_long_mean) and theta_long_mean < 0:
                offset = 1 - abs(nt) / abs(theta_long_mean)
                paras.append(('时间价值与波动率敞口抵消（对比单腿买沽）',
                              f"组合平均净 Theta = {nt:.5f} 元/单位/日，而单买 K2 腿的 Theta "
                              f"= {theta_long_mean:.5f}——卖出腿贴补了 "
                              f"{offset*100:.0f}% 的时间价值损耗；"
                              f"净 Vega 同理接近于 0（见图10）。"
                              f"这就是价差相对单腿买沽的结构性优势："
                              f"持有期间不怕横盘阴耗、不怕 IV 回落，只需方向兑现。"))

        # ---- 5. 盈亏平衡与胜率 ----
        be = stats['be_downside_mean']
        wp = stats['wp_mean']
        if pd.notna(be) and pd.notna(wp):
            paras.append(('盈亏平衡与胜率',
                          f"最新组合平均盈亏平衡跌幅 {be:+.2f}%、平均胜率 {wp:.2f}。"
                          f"解读：只要到期跌幅超过 {abs(be):.2f}%，组合即开始盈利；"
                          f"按当前 delta 结构，市场隐含的达标概率约 {wp*100:.0f}%。"
                          f"注意胜率为两腿 |delta| 插值的近似，"
                          f"隐含的是风险中性概率而非真实概率。"))

        # ---- 6. 到期与展期风险 ----
        d_min = stats['days_min']
        if pd.notna(d_min):
            if d_min <= 10:
                paras.append(('到期与展期风险',
                              f"距到期仅 {d_min:.0f} 天，临近到期 Gamma 风险放大、"
                              f"两腿价格剧烈分化，建议立即展期至次月合约。"))
            elif d_min <= 30:
                paras.append(('到期与展期风险',
                              f"距到期 {d_min:.0f} 天，应开始规划展期，"
                              f"避免到期前流动性萎缩导致双腿平仓成本上升。"))
            else:
                paras.append(('到期与展期风险',
                              f"距到期 {d_min:.0f} 天，期限结构健康，暂无展期压力。"))

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
            'h2': ParagraphStyle('H2', parent=styles['Heading2'], fontSize=13, leading=18,
                                 fontName=self.reportlab_font, spaceAfter=6, spaceBefore=6),
            'normal': ParagraphStyle('Normal', parent=styles['Normal'], fontSize=10,
                                     leading=15, fontName=self.reportlab_font),
            'cover_info': ParagraphStyle('CoverInfo', parent=styles['Normal'], fontSize=13,
                                         leading=20, alignment=1, fontName=self.reportlab_font,
                                         textColor=colors.HexColor('#333333')),
            'table_note': ParagraphStyle('TableNote', parent=styles['Normal'], fontSize=8,
                                         leading=11, fontName=self.reportlab_font,
                                         textColor=colors.HexColor('#666666')),
        }

    def _make_table(self, header, rows, col_widths=None, font_size=6.5):
        """构建统一样式的 reportlab 表格"""
        data = [header] + rows
        table = Table(data, colWidths=col_widths, repeatRows=1)
        style_cmds = [
            ('FONTNAME', (0, 0), (-1, -1), self.reportlab_font),
            ('FONTSIZE', (0, 0), (-1, -1), font_size),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#D9D9D9')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.white, colors.HexColor('#EBF1F8')]),
        ]
        # 信号列着色
        if len(header) > 0 and header[-1] == '信号':
            signal_color = {'STRONG_BUY': '#C6EFCE', 'BUY': '#E2EFDA', 'CONSIDER': '#FFEB9C',
                            'NEUTRAL': '#F2F2F2', 'AVOID': '#FFC7CE'}
            for ri, row in enumerate(rows, start=1):
                cell_bg = signal_color.get(str(row[-1]).strip())
                if cell_bg:
                    style_cmds.append(('BACKGROUND', (-1, ri), (-1, ri),
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
        call_put = config.get('call_put', 'P')

        # 最新一轮分析审计信息
        analysis_time_str, analysis_version = 'N/A', 'N/A'
        if 'analysis_time' in df.columns:
            at = pd.to_datetime(df['analysis_time'], errors='coerce').max()
            if pd.notna(at):
                analysis_time_str = at.strftime('%Y-%m-%d %H:%M:%S')
        if 'analysis_version' in df.columns and len(df) > 0:
            analysis_version = str(df['analysis_version'].dropna().iloc[-1])

        filter_tag = symbol_filter.replace('%', '') if symbol_filter else 'all'
        date_tag = f"{stats['date_start']}-{stats['date_end']}"
        pdf_path = os.path.join(
            self.REPORT_DIR,
            f"BearPutSpreadStrategy_{filter_tag}_{date_tag}_{now_ts}.pdf")

        doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4),
                                rightMargin=40, leftMargin=40, topMargin=36, bottomMargin=28)
        page_width = landscape(A4)[0] - 80
        story = []

        # ===== 封面 =====
        story.append(Spacer(1, 1.4 * inch))
        story.append(Paragraph('熊市看跌价差策略分析报告', styles['title']))
        story.append(Paragraph('Bear Put Spread Strategy Analysis Report',
                               ParagraphStyle('Sub', parent=styles['normal'], alignment=1,
                                              fontSize=11, fontName=self.reportlab_font,
                                              textColor=colors.HexColor('#888888'))))
        story.append(Spacer(1, 0.35 * inch))

        combo_names = sorted(set(df['combo_key'].dropna()))
        names_display = '、'.join(combo_names[:40])
        if len(combo_names) > 40:
            names_display += f" 等 {len(combo_names)} 个组合"

        cover_text = (
            f"策略：Bear Put Spread（买入 Put(K2) + 卖出 Put(K1)，K1<K2）<br/>"
            f"数据区间：{stats['date_start']} — {stats['date_end']}（{stats['n_days']} 个交易日）<br/>"
            f"报告生成时间：{report_date}<br/>"
            f"分析时间戳：{analysis_time_str}（算法版本 {analysis_version}）<br/>"
            f"合约过滤：symbol LIKE '{symbol_filter or '无'}' | 方向：{call_put}<br/>"
            f"数据记录：{stats['n_rows']} 条 | 候选组合：{stats['n_combos']} 个<br/>"
            f"组合列表：{names_display or '无'}<br/>"
            f"<br/>INFINITY 量化系统 · 期权策略研究"
        )
        story.append(Paragraph(cover_text, styles['cover_info']))
        story.append(PageBreak())

        # ===== 一、数据概览 =====
        story.append(Paragraph('一、数据概览（关键数字）', styles['h1']))
        overview_text = (
            f"本报告基于 {self.TABLE_SOURCE} 表（strategy_type='{self.STRATEGY_TYPE}'）"
            f"{stats['n_rows']} 条记录，覆盖 {stats['date_start']} 至 {stats['date_end']} "
            f"共 {stats['n_days']} 个交易日、{stats['n_combos']} 个候选价差组合"
            f"（配对规则：买入腿 K2 限定 ATM±1 档，卖出腿 K1 = K2 下方 1~4 档）。<br/>"
            f"最新交易日 {stats['latest_date']}：现货价 {stats['spot']:.4g}，"
            f"{stats['n_combos_latest']} 个候选组合，买入腿 IV 均值 {stats['iv_mean']*100:.1f}%"
            f"（IV 分位均值 {stats['iv_rank_mean']:.2f}），"
            f"平均净支出 {stats['net_debit_mean']:.4g} 元/单位，"
            f"平均最大资金收益率 {stats['roi_mean']:.1f}%，"
            f"平均回报风险比 {stats['rr_mean']:.2f}，平均胜率 {stats['wp_mean']:.2f}，"
            f"平均盈亏平衡跌幅 {stats['be_downside_mean']:+.2f}%，"
            f"最近到期 {stats['days_min']:.0f} 天。"
        )
        story.append(Paragraph(overview_text, styles['normal']))
        story.append(PageBreak())

        # ===== 二、最新交易日组合总览 =====
        story.append(Paragraph(f'二、最新交易日（{latest_date}）候选组合总览（按评分排名）',
                               styles['h1']))
        header, rows = self._build_latest_table_data(latest)
        n_cols = len(header)
        name_w = 90
        rest_w = (page_width - name_w - 62) / (n_cols - 2)
        col_widths = [name_w] + [rest_w] * (n_cols - 2) + [62]
        story.append(self._make_table(header, rows, col_widths))
        story.append(Spacer(1, 0.08 * inch))
        story.append(Paragraph(
            '注：净支出D = P2−P1（也是最大亏损）；宽度% = (K2−K1)/S0；最大盈利 = (K2−K1)−D（S_T≤K1 取得）；'
            'ROI% = 最大盈利/D（以净支出为本金的最大资金收益率）；胜率≈P(S_T&lt;K2−D)（两腿|delta|插值）；'
            '回报风险比 = 最大盈利/D；平衡跌幅% = (K2−D−S0)/S0（跌过该点开始盈利）；'
            '净Delta = Δlong−Δshort（残余空头方向敞口，负值）；净Theta = θlong−θshort（残余时间损耗，'
            '对比单腿已大幅抵消）；评分 = 期望值/净支出 = [胜率×最大盈利−(1−胜率)×D]/D；'
            '排名按同日评分降序（1=最优）。',
            styles['table_note']))
        story.append(PageBreak())

        # ===== 三~十二、图表（各配数字说明） =====
        chart_sections = []
        if chart_buffers.get('chart1'):
            chart_sections.append(('chart1', '图1：现货价格 + 各组合净支出',
                                   f"最新现货 {stats['spot']:.4g}，平均净支出 "
                                   f"{stats['net_debit_mean']:.4g} 元/单位（最大亏损即此值）。"
                                   f"净支出随宽度增加而上升、随 IV 回落而收窄——"
                                   f"同样宽度的组合，净支出越低代表卖腿贴补越多、性价比越高。"))
        if chart_buffers.get('chart2'):
            iv_min = latest['implied_vol'].min()
            iv_max = latest['implied_vol'].max()
            chart_sections.append(('chart2', '图2：买入腿隐含波动率 IV',
                                   f"最新买入腿 IV 区间 {iv_min*100:.1f}% ~ {iv_max*100:.1f}%。"
                                   f"注意价差净 Vega≈0：IV 涨跌对双腿价值的影响相互抵消，"
                                   f"IV 环境主要影响建仓成本而非持有期损益——这是价差与单腿买沽的关键差异。"))
        if chart_buffers.get('chart3'):
            ce_mean = latest['net_debit_pct_of_width'].mean()
            chart_sections.append(('chart3', '图3：资本效率（净支出占宽度）',
                                   f"最新平均净支出占宽度 {ce_mean:.1f}%。"
                                   f"该值越低，同样的最大盈利空间占用资金越少；"
                                   f">=90%（红线）说明宽度几乎全靠权利金支出撑起，卖腿贴补微薄，"
                                   f"不如直接单腿买沽。"))
        if chart_buffers.get('chart4'):
            chart_sections.append(('chart4', '图4：最大资金收益率 + 胜率',
                                   f"最新平均最大资金收益率 {stats['roi_mean']:.1f}%（以净支出为本金）。"
                                   f"注意 ROI 与胜率（虚线）的反向关系：宽价差 ROI 高但胜率低，"
                                   f"窄价差反之——两者乘积的期望才是真实收益预期（见评分）。"))
        if chart_buffers.get('chart5'):
            chart_sections.append(('chart5', '图5：回报风险比',
                                   f"最新平均回报风险比 {stats['rr_mean']:.2f}。"
                                   f"该值恒等于 (1−D/宽度)/(D/宽度)：净支出占宽度越低，比值越高。"
                                   f"红线 1.0 为盈亏比临界，绿线 2.0 以上为优质建仓窗口。"))
        if chart_buffers.get('chart6'):
            best = stats['best']
            if best is not None:
                note = (f"红色实线为组合到期收益（教科书厂字形截头镜像版）："
                        f"左侧横线为最大盈利平台 P={best['max_profit']:.4g}"
                        f"（S_T≤K1 盈利封顶），"
                        f"右侧横线为最大亏损平台 L=−D={-best['net_debit']:.4g}"
                        f"（S_T≥K2 亏损封底），"
                        f"两平台之间斜率为 −1；绿点为盈亏平衡点 B=K2−D={best['breakeven_S_T']:.4g}"
                        f"（需下跌 {best['breakeven_downside_pct']:+.2f}%）。"
                        f"蓝虚线（买入腿）与橙虚线（卖出腿）相加即为组合——"
                        f"卖出腿削掉了买入腿的无限下行，换来成本从 P2 降到 D。")
            else:
                note = "红实线为组合到期收益：左侧盈利封顶 (K2−K1)−D、右侧亏损封底 −D。"
            chart_sections.append(('chart6', '图6：教科书到期收益结构（三线图，评分最优组合）', note))
        if chart_buffers.get('chart7'):
            chart_sections.append(('chart7', '图7：多情景到期盈亏（最优组合 vs 买现货）',
                                   "横轴为情景因子（0.85×K2~1.15×K2）。价差线（红）盈利封顶、"
                                   "亏损封底；买现货线（灰虚线）下跌时亏损无限放大。"
                                   "小跌情景下价差的资金收益率远超现货对冲效果（本金只有净支出 D）；"
                                   "大跌情景下被 K1 封顶——这是用下行空间换成本与封底的代价。"))
        if chart_buffers.get('chart8'):
            chart_sections.append(('chart8', '图8：组合有效前沿（胜率 vs ROI）',
                                   "每个点为一个候选组合（标注 K2/K1），颜色为回报风险比，"
                                   "红星为评分最优。左上角=低胜率高赔率（宽价差），"
                                   "右下角=高胜率低赔率（窄价差）。没有绝对最优——"
                                   "按你对跌幅空间的判断在前沿上自选：预期小跌选右下，预期大跌选左上。"))
        if chart_buffers.get('chart9'):
            chart_sections.append(('chart9', '图9：Top5 组合评分演变',
                                   "评分 = 期望值/净支出，综合了胜率×赔率的期望与资金效率。"
                                   "评分持续为正且稳定的组合是滚动建仓的候选；"
                                   "评分跳水通常意味着 IV 偏移或现货逼近 K1/K2 导致 delta 结构剧变。"))
        if chart_buffers.get('chart10'):
            chart_sections.append(('chart10', '图10：净 Theta / 净 Vega（敞口抵消）',
                                   f"最新平均净 Theta = {stats['net_theta_mean']:.5f} 元/单位/日"
                                   f"（单腿买沽为纯损耗，价差已大幅抵消）。"
                                   f"净 Vega（虚线）接近 0：持有期间不怕 IV 回落。"
                                   f"这就是价差相对单腿买沽的结构性优势——"
                                   f"把'方向+波动+时间'三维博弈压缩为接近纯方向博弈。"))

        for i, (key, title, note) in enumerate(chart_sections):
            section_cn = ['三', '四', '五', '六', '七', '八', '九', '十',
                          '十一', '十二', '十三', '十四'][i] if i < 14 else str(i + 3)
            story.append(Paragraph(f'{section_cn}、{title}', styles['h1']))
            story.append(Spacer(1, 0.08 * inch))
            buf = chart_buffers.get(key)
            if buf is not None:
                # 按图片真实宽高比等比缩放，避免纵向压扁
                img = RLImage(buf)
                w0, h0 = float(img.imageWidth), float(img.imageHeight)
                max_h = 390
                scale = min(page_width / w0, max_h / h0)
                img.drawWidth = w0 * scale
                img.drawHeight = h0 * scale
                story.append(img)
            story.append(Spacer(1, 0.06 * inch))
            story.append(Paragraph(note, styles['normal']))
            story.append(PageBreak())

        # ===== 交易信号汇总 =====
        section_cn = '十三'
        story.append(Paragraph(f'{section_cn}、交易信号汇总（最新交易日）', styles['h1']))
        signal_counts = stats['signal_counts']
        sig_rows = [[k, str(v), f"{v / max(len(latest), 1) * 100:.1f}%"]
                    for k, v in sorted(signal_counts.items(), key=lambda x: -x[1])]
        if sig_rows:
            story.append(self._make_table(['信号', '组合数', '占比'], sig_rows,
                                          [150, 100, 100], font_size=9))
            story.append(Spacer(1, 0.12 * inch))
        # 信号明细（组合 + 评分 + 理由）
        detail = latest[latest['trade_signal'].isin(
            ['STRONG_BUY', 'BUY', 'CONSIDER', 'AVOID'])]
        if len(detail) > 0:
            detail = detail.sort_values(['trade_signal', 'combo_rank'])
            detail_rows = []
            for _, r in detail.iterrows():
                reason = str(r.get('signal_reason', ''))[:80]
                detail_rows.append([str(r.get('combo_key', '')),
                                    self._fmt(r['exercise_price'], '{:.4g}'),
                                    self._fmt(r['exercise_price_short'], '{:.4g}'),
                                    self._fmt(r.get('score'), '{:.3f}'),
                                    str(r['trade_signal']), reason])
            story.append(Paragraph('重点信号明细（含原因）', styles['h2']))
            story.append(self._make_table(
                ['组合 K2/K1', 'K2', 'K1', '评分', '信号', '信号原因'],
                detail_rows, [90, 55, 55, 55, 70, page_width - 325], font_size=6.5))
        story.append(PageBreak())

        # ===== 资深交易员综合点评 =====
        story.append(Paragraph('十四、资深交易员综合点评（自动生成）', styles['h1']))
        commentary = self._build_trader_commentary(df, stats)
        for title, text in commentary:
            story.append(Paragraph(f'{title}', styles['h2']))
            story.append(Paragraph(text, styles['normal']))
            story.append(Spacer(1, 0.10 * inch))
        story.append(PageBreak())

        # ===== 指标口径说明 =====
        story.append(Paragraph('十五、指标口径说明', styles['h1']))
        glossary = (
            "策略定义：买入认沽 Put(K2) + 卖出认沽 Put(K1)，K1<K2，同到期月；"
            "净支出 D = P2−P1；到期组合收益 = max(0,K2−S_T) − max(0,K1−S_T) − D，"
            "呈教科书厂字形（截头镜像版）。<br/>"
            "最大亏损 max_loss = D（S_T≥K2 时亏损封底）；"
            "最大盈利 max_profit = (K2−K1)−D（S_T≤K1 时盈利封顶）。<br/>"
            "盈亏平衡点 breakeven = K2−D：到期跌幅超过 (K2−D−S0)/S0 后组合开始盈利。<br/>"
            "最大资金收益率 roi_max_pct = max_profit/D×100：以净支出为本金，价差杠杆的来源。<br/>"
            "回报风险比 reward_risk_ratio = max_profit/D：赔率维度，恒等于 (1−D/宽度)/(D/宽度)。<br/>"
            "胜率 win_prob ≈ P(S_T&lt;K2−D)：用两腿 |delta|（≈N(−d)）在盈亏平衡点线性插值，"
            "为风险中性概率近似而非真实概率。<br/>"
            "期望值 expected_value = 胜率×max_profit − (1−胜率)×D；"
            "评分 score = 期望值/D（风险调整后收益，同日排名依据）。<br/>"
            "净 Greeks：net_delta = Δlong−Δshort（残余空头方向敞口，价差通常 −0.4~−0.1）；"
            "net_theta = θlong−θshort（残余时间损耗）；net_vega = vega_long−vega_short（≈0，波动率中性）。<br/>"
            "资本效率 net_debit_pct_of_width = D/(K2−K1)：占宽度比例越低，卖腿贴补越多。<br/>"
            "组合配对：买入腿 K2 ∈ ATM±1 档（|K−S0| 最小的档位上下各1档），"
            "卖出腿 K1 = K2 下方第 1~4 档——约束剪枝控制组合爆炸，每日约 12 个候选全量落库。<br/>"
            "信号规则：STRONG_BUY = 回报风险比≥2 且 胜率≥0.60 且 ROI≥15%；"
            "BUY = 回报风险比≥1.5 且 胜率≥0.50；CONSIDER = 回报风险比≥1.2；"
            "NEUTRAL = 回报风险比≥1.0；其余 AVOID。"
        )
        story.append(Paragraph(glossary, styles['normal']))
        story.append(Spacer(1, 0.15 * inch))

        # ===== 风险提示 =====
        story.append(Paragraph('十六、风险提示', styles['h1']))
        risk_text = (
            "本报告基于历史期权日线数据与 BS 模型理论值进行量化分析，仅供参考，不构成投资建议。<br/>"
            "情景盈亏为到期静态假设（S_T=K2×factor），未考虑路径风险、保证金占用与交易成本。<br/>"
            "胜率为两腿 |delta| 插值的风险中性概率近似，与真实概率存在系统性偏差（风险中性≠真实分布）。<br/>"
            "熊市价差盈利封顶：若标的跌幅深于 K1，超额收益全部放弃——崩盘行情中不如单腿买沽或直接做空。<br/>"
            "最大亏损锁定为净支出 D，但双腿流动性差异可能导致平仓成本高于理论值（尤其临近到期）。<br/>"
            "ETF 期权为欧式，无提前行权风险，但存在行权交割与合约调整（除权除息）风险，展期时需核对合约要素。"
        )
        story.append(Paragraph(risk_text, styles['normal']))

        doc.build(story)
        logger.info(f"✅ PDF 报告已生成: {pdf_path}")
        return pdf_path

    # ===================== 主流程 =====================

    def run(self, config):
        """运行报告生成主流程

        Args:
            config: dict with keys:
                - name / start_date / end_date / call_put / symbol_filter

        Returns:
            pdf_path or None
        """
        name = config.get('name', 'Unknown')
        start_date = config.get('start_date')
        end_date = config.get('end_date')
        call_put = config.get('call_put', 'P')
        symbol_filter = config.get('symbol_filter')

        self.writeLogInfo(className=self.__class__.__name__,
                          functionName="run",
                          event=f"Generating BearPutSpreadStrategyReport: {name}")

        try:
            # Step 1: 拉取数据
            logger.info(f"Step 1/3: 拉取 {self.TABLE_SOURCE} 数据 "
                        f"(symbol_filter={symbol_filter}, call_put={call_put})")
            df = self.fetch_data(start_date=start_date, end_date=end_date,
                                 symbol_filter=symbol_filter, call_put=call_put)
            if df.empty:
                logger.warning("数据为空（请先运行 BearPutSpreadStrategyAnalysis 落库），流程终止")
                return None

            # Step 2: 清洗 + 图表
            logger.info("Step 2/3: 数据清洗 & 生成图表")
            df = self.clean_data(df)

            chart_buffers = {}
            chart_buffers['chart1'] = self.gen_chart1_spot_net_debit(df)
            chart_buffers['chart2'] = self.gen_chart2_iv(df)
            chart_buffers['chart3'] = self.gen_chart3_capital_efficiency(df)
            chart_buffers['chart4'] = self.gen_chart4_roi_winprob(df)
            chart_buffers['chart5'] = self.gen_chart5_reward_risk(df)
            chart_buffers['chart6'] = self.gen_chart6_payoff_textbook(df)
            chart_buffers['chart7'] = self.gen_chart7_scenario_pnl(df)
            chart_buffers['chart8'] = self.gen_chart8_efficiency_frontier(df)
            chart_buffers['chart9'] = self.gen_chart9_score_timeline(df)
            chart_buffers['chart10'] = self.gen_chart10_net_greeks(df)

            chart_count = sum(1 for v in chart_buffers.values() if v is not None)
            logger.info(f"图表生成完成: {chart_count} 张")

            # Step 3: 生成 PDF
            logger.info("Step 3/3: 生成 PDF 报告")
            pdf_path = self._generate_pdf_report(df, chart_buffers, config)

            logger.info("\n" + "=" * 80)
            logger.info("✅ Bear Put Spread 策略分析报告 生成完成！")
            logger.info(f"   Report: {pdf_path}")
            logger.info(f"   Data rows: {len(df)}")
            logger.info(f"   Charts: {chart_count} 张")
            logger.info("=" * 80)
            return pdf_path

        except Exception as e:
            import traceback
            logger.error(f"报告生成失败: {e}")
            logger.error(traceback.format_exc())
            raise


if __name__ == "__main__":
    report = BearPutSpreadStrategyReport()
    report.run({
        "name": "华夏上证50ETF认沽期权（Bear Put Spread）",
        "start_date": "20251222",
        "end_date": CommonParameters.today,
        "call_put": "P",
        "symbol_filter": "510050P2612%",
    })

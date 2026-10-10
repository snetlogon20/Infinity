r"""
期权波动率曲面 偏度/期限结构 PDF 报告生成器 — 偏度/日历交易视角

数据源:
    tb_option_vol_surface(由 VolSurfaceSkewTermAnalysis 写入)

报告结构:
    封面 → 数据概览 → 最新日 曲面切片信号一览表 → 4张图表
    → 交易员综合点评 → 指标口径 → 风险提示

核心图表(与 GreeksEfficiencyReport 图2/图4 的最新日截面快照互补, 本报告为跨日时序视角):
    图1 风险逆转RR时序(按标的日均值, bp) —— 偏度回归温度计
    图2 蝶式翼溢价时序(微笑厚度)
    图3 期限结构斜率时序(±2pp/年阈值) —— 日历价差温度计
    图4 最新日曲面切片快照(按结算月: Put翼/ATM/Call翼 IV)

前置条件: 先运行 VolSurfaceSkewTermAnalysisTest 落库。

字体注意(历史教训): matplotlib 首选 Microsoft YaHei —— SimHei 缺 U+2212 字形。
"""

import io
import os
import traceback
from datetime import datetime, timedelta

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
from dataIntegrator.common.ReportJobLogger import ReportJobLogger
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

logger = CommonLib.logger

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['mathtext.fontset'] = 'dejavusans'


class VolSurfaceReport:
    """波动率曲面 偏度/期限结构 PDF 报告生成器"""

    REPORT_DIR = CommonParameters.optionAnalysisReportPath
    TABLE_SOURCE = 'tb_option_vol_surface'
    DEFAULT_LOOKBACK_DAYS = 180
    DETAIL_TABLE_FONT_SIZE = 6.8
    DETAIL_TABLE_MIN_COL_WIDTH = 22.0

    CHART_COLORS = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6', '#f39c12',
                    '#1abc9c', '#e67e22', '#2980b9', '#c0392b', '#27ae60']
    SIGNAL_COLORS = {'SELL_SKEW': '#C8E6C9', 'BUY_SKEW': '#BBDEFB',
                     'BUY_CALENDAR': '#FFF9C4', 'SELL_CALENDAR': '#FFCDD2',
                     'NEUTRAL': '#ECEFF1'}

    def __init__(self):
        os.makedirs(self.REPORT_DIR, exist_ok=True)
        self.reportlab_font = self._register_chinese_font()

    def _register_chinese_font(self):
        reportlab_font = 'Helvetica'
        for font_path, font_name in [
                (r'C:\Windows\Fonts\msyh.ttc', 'MicrosoftYaHei'),
                (r'C:\Windows\Fonts\simhei.ttf', 'SimHei'),
                (r'C:\Windows\Fonts\simsun.ttc', 'SimSun')]:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    reportlab_font = font_name
                    break
                except Exception as e:
                    logger.warning(f"字体加载失败 {font_path}: {e}")
        return reportlab_font

    def writeLogInfo(self, className="unknown", functionName="unknown", event="unknown"):
        logger.info("%s.%s: %s" % (className, functionName, event))

    # ===================== 工具 =====================

    @staticmethod
    def _fmt(val, fmt='{:.4g}'):
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

    @staticmethod
    def _text_width(text, font_size):
        width = 0.0
        for ch in str(text):
            width += font_size * (1.05 if ord(ch) > 0x2E7F else 0.58)
        return width

    def _calc_col_widths(self, header, rows, total_width, font_size=None,
                         min_width=None, cell_padding=3.0):
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
            widths = [w * scale for w in need]
        else:
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

    # ===================== 数据 =====================

    def fetch_data(self, start_date=None, end_date=None, symbol_filter=None):
        where_clauses = ["strategy_type = 'VOL_SURFACE'"]
        if start_date:
            where_clauses.append(f"trade_date >= '{start_date}'")
        if end_date:
            where_clauses.append(f"trade_date <= '{end_date}'")
        if symbol_filter:
            prefix = symbol_filter.rstrip('%').split('%')[0]
            where_clauses.append(f"underlying_key LIKE '{prefix}%'")
        sql = f"""
        SELECT * FROM indexsysdb.{self.TABLE_SOURCE}
        WHERE {' AND '.join(where_clauses)}
        ORDER BY trade_date, underlying_key, s_month
        """
        logger.info(f"SQL:\n{sql}")
        df = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        logger.info(f"Fetched {len(df)} rows, {len(df.columns)} columns")
        return df

    def clean_data(self, df):
        for col in ['days_to_maturity', 'years_to_maturity_calendar', 'n_contracts',
                    'atm_iv', 'put_wing_iv', 'call_wing_iv', 'risk_reversal',
                    'skew_slope', 'butterfly', 'iv_dispersion',
                    'term_atm_iv_near', 'term_atm_iv_far', 'term_slope', 'n_term_months']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        for col in ['trade_date', 'underlying_key', 's_month', 'maturity_date',
                    'trade_signal', 'signal_reason', 'strategy_type']:
            if col in df.columns:
                df[col] = df[col].fillna('').astype(str)
        df['trade_date_dt'] = pd.to_datetime(df['trade_date'], format='%Y%m%d',
                                             errors='coerce')
        return df

    def _latest_snapshot(self, df):
        latest_date = df['trade_date'].max()
        return latest_date, df[df['trade_date'] == latest_date]

    def _build_overview_numbers(self, df, latest):
        trade_dates = sorted(df['trade_date'].unique())
        rr_bp = latest['risk_reversal'].dropna() * 1e4
        bf_pp = latest['butterfly'].dropna() * 100
        ts_pp = latest['term_slope'].dropna() * 100
        return {
            'date_start': trade_dates[0] if trade_dates else 'N/A',
            'date_end': trade_dates[-1] if trade_dates else 'N/A',
            'n_days': len(trade_dates),
            'n_rows': len(df),
            'latest_date': latest['trade_date'].max() if len(latest) else 'N/A',
            'n_slices_latest': len(latest),
            'n_underlyings': latest['underlying_key'].nunique() if len(latest) else 0,
            'n_months_latest': latest['s_month'].nunique() if len(latest) else 0,
            'rr_mean_bp': rr_bp.mean() if len(rr_bp) else np.nan,
            'rr_min_bp': rr_bp.min() if len(rr_bp) else np.nan,
            'rr_max_bp': rr_bp.max() if len(rr_bp) else np.nan,
            'bf_mean_pp': bf_pp.mean() if len(bf_pp) else np.nan,
            'ts_mean_pp': ts_pp.mean() if len(ts_pp) else np.nan,
            'n_sell_skew': int((latest['trade_signal'] == 'SELL_SKEW').sum()),
            'n_buy_skew': int((latest['trade_signal'] == 'BUY_SKEW').sum()),
            'n_buy_calendar': int((latest['trade_signal'] == 'BUY_CALENDAR').sum()),
            'n_sell_calendar': int((latest['trade_signal'] == 'SELL_CALENDAR').sum()),
            'n_neutral': int((latest['trade_signal'] == 'NEUTRAL').sum()),
        }

    # ===================== 图表(时序视角) =====================

    def gen_chart1_risk_reversal_ts(self, df):
        """图1: 风险逆转 RR 时序(按标的日均值, bp)"""
        daily = (df[df['risk_reversal'].notna()]
                 .groupby(['trade_date_dt', 'underlying_key'])['risk_reversal']
                 .mean().reset_index())
        if daily.empty:
            logger.warning("No valid data for chart 1, skipping")
            return None
        fig, ax = plt.subplots(figsize=(20, 8))
        fig.suptitle('图1：风险逆转 Risk Reversal 时序（Call翼IV − Put翼IV，按标的日均值）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')
        for i, (key, g) in enumerate(daily.groupby('underlying_key')):
            g = g.sort_values('trade_date_dt')
            ax.plot(g['trade_date_dt'], g['risk_reversal'] * 1e4,
                    color=self.CHART_COLORS[i % len(self.CHART_COLORS)],
                    linewidth=1.8, marker='o', markersize=3, label=f'标的 {key}')
        ax.axhline(y=0, color='#e74c3c', linewidth=1.0, alpha=0.7)
        ax.axhline(y=-200, color='#7f8c8d', linewidth=0.9, linestyle='--',
                   alpha=0.6, label='信号阈值 ±200bp')
        ax.axhline(y=200, color='#7f8c8d', linewidth=0.9, linestyle='--', alpha=0.6)
        ax.set_ylabel('Risk Reversal（bp）', fontsize=11)
        ax.set_xlabel('交易日', fontsize=11)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10),
                  fontsize=9, ncol=4, frameon=True)
        fig.autofmt_xdate(rotation=45, ha='right')
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    def gen_chart2_butterfly_ts(self, df):
        """图2: 蝶式翼溢价时序(按标的日均值, pp)"""
        daily = (df[df['butterfly'].notna()]
                 .groupby(['trade_date_dt', 'underlying_key'])['butterfly']
                 .mean().reset_index())
        if daily.empty:
            logger.warning("No valid data for chart 2, skipping")
            return None
        fig, ax = plt.subplots(figsize=(20, 8))
        fig.suptitle('图2：蝶式翼溢价 Butterfly 时序（(Put翼+Call翼)/2 − ATM IV，微笑厚度）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')
        for i, (key, g) in enumerate(daily.groupby('underlying_key')):
            g = g.sort_values('trade_date_dt')
            ax.plot(g['trade_date_dt'], g['butterfly'] * 100,
                    color=self.CHART_COLORS[i % len(self.CHART_COLORS)],
                    linewidth=1.8, marker='o', markersize=3, label=f'标的 {key}')
        ax.axhline(y=0, color='#e74c3c', linewidth=1.0, alpha=0.7)
        ax.set_ylabel('Butterfly（pp）', fontsize=11)
        ax.set_xlabel('交易日', fontsize=11)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10),
                  fontsize=9, ncol=4, frameon=True)
        fig.autofmt_xdate(rotation=45, ha='right')
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    def gen_chart3_term_slope_ts(self, df):
        """图3: 期限斜率时序(按标的, pp/年) + 近/远月 ATM IV"""
        daily = (df[df['term_slope'].notna()]
                 .drop_duplicates(subset=['trade_date_dt', 'underlying_key'])
                 .groupby(['trade_date_dt', 'underlying_key'], as_index=False)
                 .agg(term_slope=('term_slope', 'mean'),
                      near=('term_atm_iv_near', 'mean'),
                      far=('term_atm_iv_far', 'mean')))
        if daily.empty:
            logger.warning("No valid data for chart 3, skipping")
            return None
        fig, ax = plt.subplots(figsize=(20, 8))
        fig.suptitle('图3：期限结构斜率时序（(远月ATM−近月ATM)/年限差，pp/年；虚线=±2pp信号阈值）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')
        for i, (key, g) in enumerate(daily.groupby('underlying_key')):
            g = g.sort_values('trade_date_dt')
            ax.plot(g['trade_date_dt'], g['term_slope'] * 100,
                    color=self.CHART_COLORS[i % len(self.CHART_COLORS)],
                    linewidth=1.8, marker='o', markersize=3, label=f'标的 {key}')
        ax.axhline(y=0, color='#e74c3c', linewidth=1.0, alpha=0.7)
        ax.axhline(y=2, color='#7f8c8d', linewidth=0.9, linestyle='--',
                   alpha=0.6, label='信号阈值 ±2pp/年')
        ax.axhline(y=-2, color='#7f8c8d', linewidth=0.9, linestyle='--', alpha=0.6)
        ax.set_ylabel('期限斜率（pp/年）', fontsize=11)
        ax.set_xlabel('交易日', fontsize=11)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10),
                  fontsize=9, ncol=4, frameon=True)
        fig.autofmt_xdate(rotation=45, ha='right')
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    def gen_chart4_latest_slice_snapshot(self, latest):
        """图4: 最新日曲面切片快照(按结算月: Put翼/ATM/Call翼 IV 分组柱)"""
        sub = latest[latest['atm_iv'].notna()].copy()
        if sub.empty:
            logger.warning("No valid data for chart 4, skipping")
            return None
        months = sorted(sub['s_month'].unique())
        atm = [sub[sub['s_month'] == m]['atm_iv'].mean() * 100 for m in months]
        put_w = [sub[sub['s_month'] == m]['put_wing_iv'].mean() * 100 for m in months]
        call_w = [sub[sub['s_month'] == m]['call_wing_iv'].mean() * 100 for m in months]

        fig, ax = plt.subplots(figsize=(20, 8))
        fig.suptitle('图4：最新交易日曲面切片快照（按结算月：Put翼 / ATM / Call翼 IV 均值）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')
        x = np.arange(len(months))
        w = 0.26
        ax.bar(x - w, put_w, width=w, color='#e74c3c', label='Put翼 IV（25Δ近似）')
        ax.bar(x, atm, width=w, color='#27ae60', label='ATM IV')
        ax.bar(x + w, call_w, width=w, color='#2980b9', label='Call翼 IV（25Δ近似）')
        for xi, v in zip(x, atm):
            if pd.notna(v):
                ax.text(xi, v + 0.05, f'{v:.1f}', ha='center', fontsize=9, color='#1a5276')
        ax.set_xticks(x)
        ax.set_xticklabels(months)
        ax.set_xlabel('结算月', fontsize=11)
        ax.set_ylabel('隐含波动率 IV（%）', fontsize=11)
        ax.grid(True, alpha=0.3, linestyle='--', axis='y')
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10),
                  fontsize=9, ncol=3, frameon=True)
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    # ===================== 明细表 =====================

    def _build_signal_table(self, latest):
        """最新日 曲面切片信号一览"""
        cand = latest.sort_values(['underlying_key', 's_month'])
        rows = []
        for _, r in cand.iterrows():
            rows.append([
                str(r.get('trade_date', '')),
                str(r.get('underlying_key', '')),
                str(r.get('s_month', '')),
                self._fmt(r.get('days_to_maturity'), '{:.0f}'),
                self._fmt(r.get('atm_iv'), '{:.2%}'),
                self._fmt(r.get('put_wing_iv'), '{:.2%}'),
                self._fmt(r.get('call_wing_iv'), '{:.2%}'),
                self._fmt(r.get('risk_reversal') * 1e4
                         if pd.notna(r.get('risk_reversal')) else None, '{:+.0f}'),
                self._fmt(r.get('skew_slope'), '{:+.3f}'),
                self._fmt(r.get('butterfly') * 100
                         if pd.notna(r.get('butterfly')) else None, '{:+.2f}'),
                self._fmt(r.get('term_atm_iv_near'), '{:.2%}'),
                self._fmt(r.get('term_atm_iv_far'), '{:.2%}'),
                self._fmt(r.get('term_slope') * 100
                         if pd.notna(r.get('term_slope')) else None, '{:+.2f}'),
                self._fmt(r.get('n_contracts'), '{:.0f}'),
                str(r.get('trade_signal', '')),
            ])
        header = ['交易日', '标的', '结算月', '剩余天数', 'ATM IV', 'Put翼IV', 'Call翼IV',
                  'RR(bp)', '偏度斜率', '蝶式(pp)', '近月ATM', '远月ATM',
                  '期限斜率(pp/年)', '合约数', '信号']
        return header, rows

    # ===================== 点评 =====================

    def _build_trader_commentary(self, df, latest, stats):
        paras = []

        # 1. 偏度环境
        rr_mean = stats['rr_mean_bp']
        if pd.notna(rr_mean):
            if rr_mean < -200:
                verdict = ("左偏显著（恐慌 Put 翼贵）：偏度回归策略可考虑卖贵 Put 翼 / 买 Call 翼"
                           "（SELL_SKEW），但要警惕事件驱动的尾部风险续涨。")
            elif rr_mean > 200:
                verdict = ("右偏显著（Call 翼贵，上行需求旺）：偏度回归可考虑买 Put 翼 / 卖 Call 翼"
                           "（BUY_SKEW），多见于逼空/抢筹行情。")
            else:
                verdict = "偏度处于中性区间，暂无明显的翼部错价可做。"
            paras.append(('偏度环境判断',
                          f"最新交易日（{stats['latest_date']}）RR 均值 "
                          f"{self._fmt(rr_mean, '{:+.0f}')}bp"
                          f"（区间 {self._fmt(stats['rr_min_bp'], '{:+.0f}')} ~ "
                          f"{self._fmt(stats['rr_max_bp'], '{:+.0f}')}bp）。{verdict}"))

        # 2. 微笑厚度
        bf_mean = stats['bf_mean_pp']
        if pd.notna(bf_mean):
            if bf_mean > 0.5:
                verdict = "翼部相对平值有明显凸性溢价：卖方在翼部收租更厚（wing 卖出性价比高）。"
            else:
                verdict = "微笑较平：翼部无额外溢价，卖方收租主要靠平值 theta。"
            paras.append(('微笑厚度（Butterfly）',
                          f"最新日蝶式翼溢价均值 {self._fmt(bf_mean, '{:+.2f}')}pp。{verdict}"))

        # 3. 期限结构
        ts_mean = stats['ts_mean_pp']
        if pd.notna(ts_mean):
            if ts_mean > 2:
                verdict = ("正期限结构显著（远月贵）：卖近买远的日历价差占优"
                           "（BUY_CALENDAR）—— 近月 theta 衰减快、远月 vega 留敞口。")
            elif ts_mean < -2:
                verdict = ("期限倒挂（近月贵）：常见于事件/分红季，买近卖远需谨慎"
                           "（SELL_CALENDAR），事件落地后近月 IV 崩塌才兑现。")
            else:
                verdict = "期限结构中性，日历价差无显著优势。"
            paras.append(('期限结构判断',
                          f"最新日期限斜率均值 {self._fmt(ts_mean, '{:+.2f}')}pp/年。{verdict}"))

        # 4. 信号分布与数据质量
        paras.append(('信号分布与数据质量',
                      f"最新日 {stats['n_slices_latest']} 个曲面切片"
                      f"（{stats['n_underlyings']} 标的 × {stats['n_months_latest']} 结算月）："
                      f"SELL_SKEW {stats['n_sell_skew']}、BUY_SKEW {stats['n_buy_skew']}、"
                      f"BUY_CALENDAR {stats['n_buy_calendar']}、"
                      f"SELL_CALENDAR {stats['n_sell_calendar']}、"
                      f"NEUTRAL {stats['n_neutral']}。"
                      + (f"翼部样本不足的切片已记 N/A（|moneyness_log|≥0.15 无报价）。"
                         if stats['n_neutral'] > 0 else '')))
        return paras

    # ===================== PDF 组装 =====================

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

    def _generate_pdf_report(self, df, chart_buffers, config, stats):
        styles = self._build_pdf_styles()
        latest_date = stats['latest_date']
        _, latest = self._latest_snapshot(df)

        report_date = datetime.now().strftime('%Y-%m-%d %H:%M')
        now_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        symbol_filter = config.get('symbol_filter')
        tag = symbol_filter.rstrip('%') if symbol_filter else 'ALL'
        pdf_path = os.path.join(
            self.REPORT_DIR,
            f"VOL_SURFACE_{tag}_{stats['date_start']}-{stats['date_end']}_{now_ts}.pdf")

        doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4),
                                rightMargin=32, leftMargin=32, topMargin=36, bottomMargin=28)
        page_width = landscape(A4)[0] - 64
        story = []

        # 封面
        story.append(Spacer(1, 1.4 * inch))
        story.append(Paragraph('期权波动率曲面报告', styles['title']))
        story.append(Paragraph('Skew / Risk Reversal / Butterfly / Term Structure',
                               ParagraphStyle('Sub', parent=styles['normal'], alignment=1,
                                              fontSize=11, fontName=self.reportlab_font,
                                              textColor=colors.HexColor('#888888'))))
        story.append(Spacer(1, 0.35 * inch))
        story.append(Paragraph(
            f"定位：偏度交易与期限结构交易的信号研究（跨日时序 + 最新信号一览）<br/>"
            f"数据区间：{stats['date_start']} — {stats['date_end']}（{stats['n_days']} 个交易日）<br/>"
            f"报告生成时间：{report_date}<br/>"
            f"数据记录：{stats['n_rows']} 条曲面切片 | 最新日：{stats['n_slices_latest']} 个切片"
            f"（{stats['n_underlyings']} 标的 × {stats['n_months_latest']} 结算月）<br/>"
            f"<br/>INFINITY 量化系统 · 期权波动率与 Greeks 研究",
            styles['cover_info']))
        story.append(PageBreak())

        # 一、数据概览
        story.append(Paragraph('一、数据概览（关键数字）', styles['h1']))
        story.append(Paragraph(
            f"最新交易日 {latest_date}：RR 均值 "
            f"{self._fmt(stats['rr_mean_bp'], '{:+.0f}')}bp"
            f"（区间 {self._fmt(stats['rr_min_bp'], '{:+.0f}')} ~ "
            f"{self._fmt(stats['rr_max_bp'], '{:+.0f}')}bp）；"
            f"蝶式翼溢价 {self._fmt(stats['bf_mean_pp'], '{:+.2f}')}pp；"
            f"期限斜率 {self._fmt(stats['ts_mean_pp'], '{:+.2f}')}pp/年；"
            f"信号分布：SELL_SKEW {stats['n_sell_skew']} / BUY_SKEW {stats['n_buy_skew']} / "
            f"BUY_CALENDAR {stats['n_buy_calendar']} / SELL_CALENDAR {stats['n_sell_calendar']} / "
            f"NEUTRAL {stats['n_neutral']}。",
            styles['normal']))
        story.append(PageBreak())

        # 二、最新日信号一览表
        header, rows = self._build_signal_table(latest)
        story.append(Paragraph(
            f'二、最新交易日（{latest_date}）曲面切片信号一览'
            f'（按标的 × 结算月，RR/偏度/蝶式/期限斜率 + 信号）', styles['h1']))
        if rows:
            col_widths = self._calc_col_widths(header, rows, page_width,
                                               self.DETAIL_TABLE_FONT_SIZE)
            story.append(self._make_table(header, rows, col_widths))
            story.append(Spacer(1, 0.08 * inch))
            story.append(Paragraph(
                '注1（口径）：ATM = |ln(K/S)/√T|≤0.05 均值；Put/Call翼 = |ln(K/S)/√T|≥0.15 的'
                '认沽/认购翼均值（25Δ近似）。<br/>'
                '注2（偏度刻度）：RR = Call翼IV − Put翼IV（bp，正=右偏）；'
                '偏度斜率 = IV 对 ln(K/S)/√T 的回归斜率（负=左偏）；'
                '蝶式 = (Put翼+Call翼)/2 − ATM（pp，正=微笑厚）。<br/>'
                '注3（期限刻度）：期限斜率 = (远月ATM−近月ATM)/年限差（pp/年，'
                '正=远月贵=正期限结构）。<br/>'
                '注4（信号阈值）：|RR|≥200bp 给偏度信号；|期限斜率|≥2pp/年 给日历信号；'
                '其余 NEUTRAL。N/A 表示该切片翼部无有效报价。',
                styles['table_note']))
        else:
            story.append(Paragraph('最新交易日无有效曲面切片。', styles['normal']))
        story.append(PageBreak())

        # 三~六、图表
        chart_sections = []
        if chart_buffers.get('chart1'):
            chart_sections.append(('chart1', '图1：风险逆转 RR 时序（偏度回归温度计）',
                                   "RR 持续深负=恐慌左偏（卖Put翼/买Call翼的回归机会）；"
                                   "转正或深正=Call翼抢筹。灰色虚线=±200bp 信号阈值。"))
        if chart_buffers.get('chart2'):
            chart_sections.append(('chart2', '图2：蝶式翼溢价时序（微笑厚度）',
                                   "Butterfly 走高=翼部相对平值变贵（wing 卖方收租变厚）；"
                                   "走低甚至为负=翼部便宜（买 wing 的性价比提升）。"))
        if chart_buffers.get('chart3'):
            chart_sections.append(('chart3', '图3：期限结构斜率时序（日历价差温度计）',
                                   "灰色虚线=±2pp/年 信号阈值。持续为正=卖近买远日历占优；"
                                   "倒挂（负值）常见于事件/分红季，事件落地后近月 IV 崩塌。"))
        if chart_buffers.get('chart4'):
            chart_sections.append(('chart4', '图4：最新日曲面切片快照（按结算月）',
                                   "三色柱对比各结算月的 Put翼/ATM/Call翼 IV。"
                                   "同月内红蓝柱高度差=该月偏度；跨月绿柱走势=期限结构；"
                                   "柱顶数字为 ATM IV。"))

        for i, (key, title, note) in enumerate(chart_sections):
            section_cn = ['三', '四', '五', '六'][i] if i < 4 else str(i + 3)
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

        # 交易员点评
        next_cn = str(len(chart_sections) + 3)
        story.append(Paragraph(f'{next_cn}、交易员综合点评（自动生成）', styles['h1']))
        for title, text in self._build_trader_commentary(df, latest, stats):
            story.append(Paragraph(f'<b>{title}</b>', styles['h1']))
            story.append(Paragraph(text, styles['normal']))
            story.append(Spacer(1, 0.10 * inch))
        story.append(PageBreak())

        # 指标口径
        story.append(Paragraph(f'{int(next_cn) + 1}、指标口径', styles['h1']))
        story.append(Paragraph(
            "Risk Reversal（风险逆转）= Call翼IV − Put翼IV：翼部（|ln(K/S)/√T|≥0.15，25Δ近似）"
            "IV 差，正=右偏（Call贵），负=左偏（恐慌Put贵）。<br/>"
            "偏度斜率 = IV 对标准化对数价态 ln(K/S)/√T 的线性回归斜率："
            "每单位价态的 IV 变化，负=经典股票左偏。<br/>"
            "Butterfly（蝶式翼溢价）= (Put翼+Call翼)/2 − ATM：翼部对平值的凸性溢价，"
            "正=微笑明显。<br/>"
            "期限斜率 = (最远月ATM − 最近月ATM)/年限差：正=远月贵（正期限结构）；"
            "负=倒挂（事件/分红季）。<br/>"
            "iv_dispersion = 切片内 IV 标准差：报价离散度，大=流动性差或报价失真。<br/>"
            "信号阈值：|RR|≥200bp → SELL_SKEW(左偏深)/BUY_SKEW(右偏)；"
            "|期限斜率|≥2pp/年 → BUY_CALENDAR(正结构)/SELL_CALENDAR(倒挂)；"
            "偏度信号优先于日历信号；均未触发 → NEUTRAL。<br/>"
            "翼部 IV 需要 |ln(K/S)/√T|≥0.15 档位有有效报价，深度实值/极远月可能缺失记 N/A。",
            styles['normal']))
        story.append(Spacer(1, 0.15 * inch))

        # 风险提示
        story.append(Paragraph(f'{int(next_cn) + 2}、风险提示', styles['h1']))
        story.append(Paragraph(
            "本报告基于日线收盘价与 BS 框架的标准化价态，仅供策略研究参考，不构成投资建议。<br/>"
            "偏度回归（SELL_SKEW）本质是卖尾部保险：左偏可能继续加深（事件驱动），"
            "务必设止损并控制 wing 卖出的名义敞口。<br/>"
            "日历价差对近月到期时点敏感：事件落地前近月 IV 不崩塌则倒挂交易亏损；"
            "分红季（11~12月）q 估计误差会同时扭曲近月 IV 与期限读数。<br/>"
            "翼部（25Δ近似）档位流动性通常弱于平值，落单前务必核对 OI 与盘口宽度；"
            "iv_dispersion 大的切片报价可信度低。<br/>"
            "RR/期限斜率为跨切片均值口径，单腿极端报价会拉动均值，"
            "执行前请回到明细表核对逐切片数值。",
            styles['normal']))

        doc.build(story)
        logger.info(f"PDF 报告已生成: {pdf_path}")
        return pdf_path

    # ===================== 主流程 =====================

    def run(self, config):
        name = config.get('name', 'Unknown')
        symbol_filter = config.get('symbol_filter')
        end_date = config.get('end_date') or CommonParameters.today
        start_date = config.get('start_date')
        if not start_date:
            start_dt = datetime.strptime(end_date, '%Y%m%d') \
                - timedelta(days=self.DEFAULT_LOOKBACK_DAYS)
            start_date = start_dt.strftime('%Y%m%d')

        self.writeLogInfo(className=self.__class__.__name__, functionName="run",
                          event=f"Generating VolSurfaceReport: {name}")

        job_logger = ReportJobLogger()
        job_logger.start_job(self.__class__.__name__, 'OptionStrategyReport',
                             params={'report_name': name, 'start_date': start_date,
                                     'end_date': end_date, 'symbol_filter': symbol_filter})
        try:
            logger.info(f"Step 1/3: 拉取 {self.TABLE_SOURCE} 数据")
            df = self.fetch_data(start_date=start_date, end_date=end_date,
                                 symbol_filter=symbol_filter)
            if df.empty:
                logger.warning("数据为空（请先运行 VolSurfaceSkewTermAnalysisTest 落库），流程终止")
                job_logger.end_job_success(records_processed=0)
                return None

            logger.info("Step 2/3: 数据清洗 & 生成图表")
            df = self.clean_data(df)
            latest_date, latest = self._latest_snapshot(df)
            stats = self._build_overview_numbers(df, latest)

            chart_buffers = {}
            chart_buffers['chart1'] = self.gen_chart1_risk_reversal_ts(df)
            chart_buffers['chart2'] = self.gen_chart2_butterfly_ts(df)
            chart_buffers['chart3'] = self.gen_chart3_term_slope_ts(df)
            chart_buffers['chart4'] = self.gen_chart4_latest_slice_snapshot(latest)
            chart_count = sum(1 for v in chart_buffers.values() if v is not None)
            logger.info(f"图表生成完成: {chart_count} 张")

            logger.info("Step 3/3: 生成 PDF 报告")
            pdf_path = self._generate_pdf_report(df, chart_buffers, config, stats)

            logger.info("\n" + "=" * 80)
            logger.info(f"[{name}] 波动率曲面报告 生成完成！")
            logger.info(f"   Report: {pdf_path}")
            logger.info(f"   Data rows: {len(df)} | Charts: {chart_count} 张")
            logger.info("=" * 80)
            job_logger.end_job_success(records_processed=len(df))
            return pdf_path

        except Exception as e:
            logger.error(f"报告生成失败: {e}")
            logger.error(traceback.format_exc())
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise

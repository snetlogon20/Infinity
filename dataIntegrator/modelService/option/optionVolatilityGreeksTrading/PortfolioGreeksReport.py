r"""
期权组合 Greeks 聚合与对冲 PDF 报告生成器 — 风控/交易员视角

数据源:
    tb_option_portfolio_greeks(由 PortfolioGreeksAggregator 写入,
    含 TOTAL/UNDERLYING/MATURITY 三视角净 Greeks、对冲建议、P&L 归因)

报告结构:
    封面 → 数据概览 → 分组净Greeks汇总表(按到期月) → 对冲建议表(按标的)
    → P&L Explain 归因表+图 → 交易员点评 → 指标口径 → 风险提示

核心图表:
    图1 到期月 Greeks 分布(净Δ/净V/净Θ 分组柱状)
    图2 P&L Explain 分解(Delta/Gamma/Vega/Theta/残差 柱状)

前置条件: 先运行 PortfolioGreeksAggregatorTest 落库。

字体注意(历史教训): matplotlib 首选 Microsoft YaHei。
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


class PortfolioGreeksReport:
    """组合 Greeks 聚合与对冲 PDF 报告生成器"""

    REPORT_DIR = CommonParameters.optionAnalysisReportPath
    TABLE_SOURCE = 'tb_option_portfolio_greeks'
    DEFAULT_LOOKBACK_DAYS = 90

    CHART_COLORS = ['#2980b9', '#27ae60', '#e74c3c', '#f39c12', '#9b59b6']

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

    def _calc_col_widths(self, header, rows, total_width, font_size=7.0,
                         min_width=22.0, cell_padding=3.0):
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

    def _make_table(self, header, rows, col_widths, font_size=7.0):
        data = [header] + rows
        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
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
        ]))
        return table

    # ===================== 数据 =====================

    def fetch_data(self, start_date=None, end_date=None):
        where_clauses = []
        if start_date:
            where_clauses.append(f"trade_date >= '{start_date}'")
        if end_date:
            where_clauses.append(f"trade_date <= '{end_date}'")
        where_str = (" AND ".join(where_clauses)) if where_clauses else "1=1"
        sql = f"""
        SELECT * FROM indexsysdb.{self.TABLE_SOURCE}
        WHERE {where_str}
        ORDER BY trade_date, group_type, group_key
        """
        logger.info(f"SQL:\n{sql}")
        df = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        logger.info(f"Fetched {len(df)} rows, {len(df.columns)} columns")
        return df

    def clean_data(self, df):
        numeric_cols = ['n_positions', 'sum_long_qty', 'sum_short_qty',
                        'net_delta', 'net_gamma', 'net_vega', 'net_theta', 'net_rho',
                        'delta_hedge_units', 'delta_hedge_notional_cny',
                        'hedge_contracts', 'theta_carry_cny', 'net_delta_notional_cny',
                        'pnl_observed_cny', 'pnl_delta_cny', 'pnl_gamma_cny',
                        'pnl_vega_cny', 'pnl_theta_cny', 'pnl_residual_cny',
                        'pnl_explain_coverage']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        for col in ['trade_date', 'trade_date_prev', 'group_type', 'group_key',
                    'hedge_instrument']:
            if col in df.columns:
                df[col] = df[col].fillna('').astype(str)
        return df

    def _latest_snapshot(self, df):
        latest_date = df['trade_date'].max()
        return latest_date, df[df['trade_date'] == latest_date]

    # ===================== 图表 =====================

    def gen_chart1_greeks_by_maturity(self, latest):
        """图1: 到期月 Greeks 分布(净Δ/净V/净Θ, 归一化并列柱状)"""
        mat = latest[latest['group_type'] == 'MATURITY'].sort_values('group_key')
        if mat.empty:
            logger.warning("No MATURITY rows for chart 1, skipping")
            return None

        x = np.arange(len(mat))
        fig, axes = plt.subplots(3, 1, figsize=(20, 12), sharex=True)
        fig.suptitle('图1：到期月 Greeks 分布（哪个月集中爆发）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')
        panels = [('net_delta', '净Delta（标的单位）', axes[0], '#2980b9'),
                  ('net_vega', '净Vega（元/1%IV）', axes[1], '#27ae60'),
                  ('net_theta', '净Theta（元/天）', axes[2], '#e74c3c')]
        for col, label, ax, clr in panels:
            vals = pd.to_numeric(mat[col], errors='coerce').fillna(0.0)
            ax.bar(x, vals, color=clr, alpha=0.85, label=label)
            ax.axhline(y=0, color='#1a1a2e', linewidth=0.8)
            ax.set_ylabel(label, fontsize=10)
            ax.grid(True, alpha=0.3, linestyle='--', axis='y')
            for xi, v in zip(x, vals):
                if v != 0:
                    ax.annotate(f'{v:+.3g}', xy=(xi, v), fontsize=8,
                                va='bottom' if v > 0 else 'top', ha='center')
        axes[-1].set_xticks(x)
        axes[-1].set_xticklabels(mat['group_key'], fontsize=10)
        axes[-1].set_xlabel('到期月（s_month）', fontsize=11)
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    def gen_chart2_pnl_explain(self, latest):
        """图2: P&L Explain 分解(最近交易日 TOTAL, 元)"""
        total = latest[latest['group_type'] == 'TOTAL']
        if total.empty:
            logger.warning("No TOTAL row for chart 2, skipping")
            return None
        r = total.iloc[0]
        comps = [('Delta', r.get('pnl_delta_cny')), ('Gamma', r.get('pnl_gamma_cny')),
                 ('Vega', r.get('pnl_vega_cny')), ('Theta', r.get('pnl_theta_cny')),
                 ('残差', r.get('pnl_residual_cny')),
                 ('实际盯市', r.get('pnl_observed_cny'))]
        labels = [c[0] for c in comps]
        vals = [float(c[1]) if pd.notna(c[1]) else 0.0 for c in comps]
        if all(v == 0 for v in vals):
            logger.warning("P&L explain all zero, skipping chart 2")
            return None

        fig, ax = plt.subplots(figsize=(20, 8))
        fig.suptitle('图2：P&L Explain 损益归因分解（最近两个交易日，元）'
                     '（Δ·dS + ½Γ·dS² + V·dIV + Θ·dt vs 实际盯市）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')
        clrs = ['#2980b9', '#27ae60', '#9b59b6', '#f39c12', '#e74c3c', '#34495e']
        bars = ax.bar(labels, vals, color=clrs, alpha=0.88)
        ax.axhline(y=0, color='#1a1a2e', linewidth=1.0)
        for b, v in zip(bars, vals):
            if v != 0:
                ax.annotate(f'{v:+,.0f}', xy=(b.get_x() + b.get_width() / 2, v),
                            fontsize=10, ha='center',
                            va='bottom' if v > 0 else 'top')
        ax.set_ylabel('损益（元）', fontsize=11)
        ax.grid(True, alpha=0.3, linestyle='--', axis='y')
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    # ===================== 明细表 =====================

    def _build_maturity_table(self, latest):
        """分组净 Greeks 汇总表(TOTAL + 各到期月)"""
        rows = []
        total = latest[latest['group_type'] == 'TOTAL']
        if len(total):
            r = total.iloc[0]
            rows.append(['TOTAL', self._fmt(r.get('n_positions'), '{:.0f}'),
                        self._fmt(r.get('sum_long_qty'), '{:.0f}'),
                        self._fmt(r.get('sum_short_qty'), '{:.0f}'),
                        self._fmt(r.get('net_delta'), '{:+.3f}'),
                        self._fmt(r.get('net_gamma'), '{:+.4g}'),
                        self._fmt(r.get('net_vega'), '{:+.4g}'),
                        self._fmt(r.get('net_theta'), '{:+.4g}'),
                        self._fmt(r.get('net_rho'), '{:+.4g}'),
                        self._fmt(r.get('theta_carry_cny'), '{:+,.0f}'),
                        self._fmt(r.get('net_delta_notional_cny'), '{:+,.0f}')])
        for _, r in latest[latest['group_type'] == 'MATURITY'] \
                .sort_values('group_key').iterrows():
            rows.append([str(r.get('group_key', '')),
                         self._fmt(r.get('n_positions'), '{:.0f}'),
                         self._fmt(r.get('sum_long_qty'), '{:.0f}'),
                         self._fmt(r.get('sum_short_qty'), '{:.0f}'),
                         self._fmt(r.get('net_delta'), '{:+.3f}'),
                         self._fmt(r.get('net_gamma'), '{:+.4g}'),
                         self._fmt(r.get('net_vega'), '{:+.4g}'),
                         self._fmt(r.get('net_theta'), '{:+.4g}'),
                         self._fmt(r.get('net_rho'), '{:+.4g}'),
                         self._fmt(r.get('theta_carry_cny'), '{:+,.0f}'),
                         self._fmt(r.get('net_delta_notional_cny'), '{:+,.0f}')])
        header = ['分组', '持仓数', '买张数', '卖张数', '净Δ', '净Γ', '净Vega',
                  '净Θ(元/天)', '净Rho', 'Θ日收入(元)', 'Δ名义(元)']
        return header, rows

    def _build_hedge_table(self, latest):
        """对冲建议表(按标的)"""
        und = latest[latest['group_type'] == 'UNDERLYING']
        if und.empty:
            return [], []
        rows = []
        for _, r in und.sort_values('group_key').iterrows():
            instr = str(r.get('hedge_instrument', 'SPOT'))
            unit_cn = {'SPOT': '单位(现货/融券)', 'ETF_LOT': '手(100份/手)',
                       'FUTURE': '手(期货)'}[instr]
            rows.append([str(r.get('group_key', '')),
                        self._fmt(r.get('n_positions'), '{:.0f}'),
                        self._fmt(r.get('net_delta'), '{:+.3f}'),
                        self._fmt(r.get('delta_hedge_units'), '{:+.2f}'),
                        unit_cn,
                        self._fmt(r.get('hedge_contracts'), '{:+.2f}'),
                        self._fmt(r.get('delta_hedge_notional_cny'), '{:,.0f}'),
                        self._fmt(r.get('net_gamma'), '{:+.4g}'),
                        self._fmt(r.get('net_vega'), '{:+.4g}'),
                        self._fmt(r.get('net_theta'), '{:+.4g}')])
        header = ['标的', '持仓数', '净Δ', '对冲单位', '对冲工具', '对冲手数',
                  '对冲名义(元)', '残留净Γ', '残留净Vega', '残留净Θ']
        return header, rows

    def _build_explain_table(self, latest):
        """P&L Explain 归因表(TOTAL + 按标的)"""
        rows = []
        for _, r in latest[latest['group_type'].isin(['TOTAL', 'UNDERLYING'])] \
                .sort_values(['group_type', 'group_key']).iterrows():
            rows.append([f"{r.get('group_type', '')}/{r.get('group_key', '')}",
                        self._fmt(r.get('pnl_observed_cny'), '{:+,.0f}'),
                        self._fmt(r.get('pnl_delta_cny'), '{:+,.0f}'),
                        self._fmt(r.get('pnl_gamma_cny'), '{:+,.0f}'),
                        self._fmt(r.get('pnl_vega_cny'), '{:+,.0f}'),
                        self._fmt(r.get('pnl_theta_cny'), '{:+,.0f}'),
                        self._fmt(r.get('pnl_residual_cny'), '{:+,.0f}'),
                        self._fmt(r.get('pnl_explain_coverage'), '{:.1%}')])
        header = ['分组', '实际盯市(元)', 'Delta归因', 'Gamma归因', 'Vega归因',
                  'Theta归因', '残差', '解释覆盖率']
        return header, rows

    # ===================== 点评 =====================

    def _build_trader_commentary(self, latest):
        paras = []
        total = latest[latest['group_type'] == 'TOTAL']
        if total.empty:
            return paras
        t = total.iloc[0]

        # 1. 方向敞口与对冲
        nd = t.get('net_delta')
        if pd.notna(nd):
            verdict = ('接近中性，方向敞口可控' if abs(nd) < 0.5
                       else f'方向敞口显著（相当于 {abs(nd):.2f} 单位标的'
                            f'{"多头" if nd > 0 else "空头"}），建议按对冲表执行')
            paras.append(('方向敞口与对冲',
                         f"组合净Δ = {nd:+.3f}（标的单位），净Δ名义 "
                         f"{self._fmt(t.get('net_delta_notional_cny'), '{:+,.0f}')} 元。"
                         f"{verdict}。对冲后 gamma/vega 残留敞口见对冲建议表，"
                         f"波动骤升时需按情景追加对冲频率。"))

        # 2. 时间价值现金流
        nt = t.get('net_theta')
        if pd.notna(nt):
            paras.append(('时间价值现金流',
                         f"组合净Θ = {nt:+,.0f} 元/天（"
                         + ('净收入：卖方结构在“收租”' if nt > 0
                            else '净损耗：买方结构在为敞口付费')
                         + f"，月度量级约 {nt * 21:+,.0f} 元/21交易日）。"
                         f"Theta 是卖方组合的“工资”，但须与图1的 gamma 集中期对照。"))

        # 3. 期限集中度
        mat = latest[latest['group_type'] == 'MATURITY']
        if len(mat) > 0:
            top = mat.loc[mat['net_vega'].abs().idxmax()]
            paras.append(('Greeks 期限集中度',
                          f"净Vega 最集中的到期月：{top['group_key']}"
                          f"（净V {self._fmt(top['net_vega'], '{:+.4g}')}"
                          f"，净Γ {self._fmt(top['net_gamma'], '{:+.4g}')}）。"
                          f"该月临近时 gamma 会加速放大（近月 Γ ∝ 1/√T），"
                          f"对冲频率与保证金压力同步上升，提前安排展期。"))

        # 4. 模型解释力
        cov = t.get('pnl_explain_coverage')
        if pd.notna(cov):
            verdict = ('Greeks 线性化解释力好，数据可信'
                      if cov > 0.8 else
                      '残差偏大：可能存在报价失真、IV跳变或高阶项主导，需排查数据')
            paras.append(('P&L Explain 模型校验',
                         f"最近两日实际盯市 {self._fmt(t.get('pnl_observed_cny'), '{:+,.0f}')} 元，"
                         f"四项归因 + 残差解释覆盖率 {cov:.1%}。{verdict}——"
                         f"该指标同时是免费的持仓数据质量监控。"))
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

    def _generate_pdf_report(self, df, chart_buffers, config, latest_date):
        styles = self._build_pdf_styles()
        latest = df[df['trade_date'] == latest_date]
        total = latest[latest['group_type'] == 'TOTAL']
        t = total.iloc[0] if len(total) else {}

        report_date = datetime.now().strftime('%Y-%m-%d %H:%M')
        now_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_path = os.path.join(
            self.REPORT_DIR,
            f"PORTFOLIO_GREEKS_{latest_date}_{now_ts}.pdf")

        doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4),
                                rightMargin=32, leftMargin=32, topMargin=36, bottomMargin=28)
        page_width = landscape(A4)[0] - 64
        story = []

        # 封面
        story.append(Spacer(1, 1.4 * inch))
        story.append(Paragraph('期权组合 Greeks 聚合与对冲报告', styles['title']))
        story.append(Paragraph('Portfolio Greeks Aggregation · Delta Hedging · P&L Explain',
                               ParagraphStyle('Sub', parent=styles['normal'], alignment=1,
                                              fontSize=11, fontName=self.reportlab_font,
                                              textColor=colors.HexColor('#888888'))))
        story.append(Spacer(1, 0.35 * inch))
        story.append(Paragraph(
            f"持仓口径日：{latest_date}　|　P&L Explain 对照日："
            f"{t.get('trade_date_prev', 'N/A') if len(t) else 'N/A'}<br/>"
            f"报告生成时间：{report_date}<br/>"
            f"组合净Δ：{self._fmt(t.get('net_delta'), '{:+.3f}') if len(t) else 'N/A'}　|　"
            f"净Γ：{self._fmt(t.get('net_gamma'), '{:+.4g}') if len(t) else 'N/A'}　|　"
            f"净V：{self._fmt(t.get('net_vega'), '{:+.4g}') if len(t) else 'N/A'}　|　"
            f"净Θ：{self._fmt(t.get('net_theta'), '{:+.4g}') if len(t) else 'N/A'}<br/>"
            f"<br/>INFINITY 量化系统 · 期权波动率与 Greeks 研究",
            styles['cover_info']))
        story.append(PageBreak())

        # 一、分组净 Greeks 汇总
        story.append(Paragraph(f'一、分组净 Greeks 汇总（{latest_date}，TOTAL + 按到期月）',
                               styles['h1']))
        header, rows = self._build_maturity_table(latest)
        if rows:
            story.append(self._make_table(header, rows,
                                          self._calc_col_widths(header, rows, page_width)))
            story.append(Paragraph(
                '注：净Greeks = Σ(方向 × 张数 × 合约乘数 × 单腿Greeks)，买腿为正、卖腿为负；'
                '净Δ为标的单位（对冲核心输入），净Vega为 IV 每变动 1 个百分点的权利金变化（元），'
                '净Θ为每日时间价值净收入（元/天）；Δ名义 = 净Δ×现货价。',
                styles['table_note']))
        story.append(PageBreak())

        # 二、对冲建议
        story.append(Paragraph('二、Delta 对冲建议（按标的）', styles['h1']))
        header, rows = self._build_hedge_table(latest)
        if rows:
            story.append(self._make_table(header, rows,
                                          self._calc_col_widths(header, rows, page_width)))
            story.append(Paragraph(
                '注：对冲单位 = −净Δ（现货/融券单位）；ETF_LOT 按每手 100 份折算手数；'
                'FUTURE 按名义金额÷(期货乘数×现货价) 折算手数（乘数默认300，'
                '请以实际合约为准）。Delta 对冲后残留的净Γ/净V 即二阶风险敞口，'
                '波动骤升时对冲频率需同步上调（gamma 对冲无静态解）。',
                styles['table_note']))
        else:
            story.append(Paragraph('无标的维度数据。', styles['normal']))
        story.append(PageBreak())

        # 三、P&L Explain
        story.append(Paragraph('三、P&L Explain 损益归因（最近两个交易日）', styles['h1']))
        header, rows = self._build_explain_table(latest)
        if rows:
            story.append(self._make_table(header, rows,
                                          self._calc_col_widths(header, rows, page_width)))
            story.append(Paragraph(
                '注：用 T-1 日 Greeks 解释 T 日盯市损益：ΔP&L ≈ Δ·dS + ½Γ·dS² + '
                'V·dIV(百分点) + Θ·dt日历天；残差 = 实际 − 四项之和（高阶项/IV曲线非平行移动/'
                '报价失真）；解释覆盖率接近 100% 表示 Greeks 线性化解释力好——'
                '残差持续偏大说明持仓报价或 IV 数据有问题，本身就是数据质量监控。',
                styles['table_note']))
        if chart_buffers.get('chart2'):
            story.append(Spacer(1, 0.1 * inch))
            img = RLImage(chart_buffers['chart2'])
            w0, h0 = float(img.imageWidth), float(img.imageHeight)
            scale = min(page_width / w0, 360 / h0)
            img.drawWidth = w0 * scale
            img.drawHeight = h0 * scale
            story.append(img)
        story.append(PageBreak())

        # 四、到期月 Greeks 分布
        if chart_buffers.get('chart1'):
            story.append(Paragraph('四、到期月 Greeks 分布', styles['h1']))
            img = RLImage(chart_buffers['chart1'])
            w0, h0 = float(img.imageWidth), float(img.imageHeight)
            scale = min(page_width / w0, 480 / h0)
            img.drawWidth = w0 * scale
            img.drawHeight = h0 * scale
            story.append(img)
            story.append(Paragraph(
                '读图：净Δ/净V/净Θ 按到期月的分布——“哪个月集中爆发”。'
                '近月净Γ大是正常现象（Γ∝1/√T），但若净Θ收入也集中在近月，'
                '意味着收租与 gamma 风险同源，一旦波动跳升将同时冲击两端。',
                styles['normal']))
            story.append(PageBreak())

        # 五、交易员点评
        story.append(Paragraph('五、交易员综合点评（自动生成）', styles['h1']))
        for title, text in self._build_trader_commentary(latest):
            story.append(Paragraph(f'<b>{title}</b>', styles['h1']))
            story.append(Paragraph(text, styles['normal']))
            story.append(Spacer(1, 0.10 * inch))
        story.append(PageBreak())

        # 六、指标口径
        story.append(Paragraph('六、指标口径', styles['h1']))
        story.append(Paragraph(
            "净Greeks（持仓口径）= Σ(方向 × 张数 × 合约乘数 × 单腿Greeks)：买腿为正、卖腿为负；"
            "净Δ 单位为标的份数（对冲输入），净Γ 为 Δ 对 dS 的二阶敏感度，"
            "净V 为 IV 每 1 个百分点的损益（元），净Θ 为每日时间价值净收入（元/天）。<br/>"
            "对冲单位 = −净Δ；ETF_LOT 按 100 份/手折算；FUTURE 手数 = |净Δ|×S ÷ (乘数×S)。<br/>"
            "P&L Explain：用 T-1 日 Greeks 解释 T 日盯市损益（BS 框架一阶+二阶展开），"
            "残差包含高阶交叉项（vanna/volga）、IV 曲线非平行移动与报价噪声。<br/>"
            "解释覆盖率 = 1 − |残差/实际盯市|：既是模型校验，也是持仓数据质量监控。<br/>"
            "三视角分组：TOTAL（全组合风控总览）/ UNDERLYING（对冲执行单元）/"
            "MATURITY（期限分布与展期安排）。",
            styles['normal']))
        story.append(Spacer(1, 0.15 * inch))

        # 七、风险提示
        story.append(Paragraph('七、风险提示', styles['h1']))
        story.append(Paragraph(
            "本报告基于日线收盘价与 BS 框架计算，仅供策略研究参考，不构成投资建议。<br/>"
            "Delta 对冲是动态过程：跳空、波动率骤升时离散对冲会产生明显的对冲误差"
            "（gamma 损失），实际对冲频率取决于风险预算。<br/>"
            "卖出腿保证金随波动动态上调，请按压力情景预留追加资金。<br/>"
            "P&L Explain 的残差包含正常的高阶项，残差偏大也可能源于 IV 曲线整体位移"
            "而非数据错误，请结合当日 IV 变动幅度解读。<br/>"
            "持仓输入为人工/上游给定，请确保 ts_code、方向、数量与实际账户一致。",
            styles['normal']))

        doc.build(story)
        logger.info(f"PDF 报告已生成: {pdf_path}")
        return pdf_path

    # ===================== 主流程 =====================

    def run(self, config):
        name = config.get('name', 'Unknown')
        end_date = config.get('end_date') or CommonParameters.today
        start_date = config.get('start_date')
        if not start_date:
            start_dt = datetime.strptime(end_date, '%Y%m%d') \
                - timedelta(days=self.DEFAULT_LOOKBACK_DAYS)
            start_date = start_dt.strftime('%Y%m%d')

        self.writeLogInfo(className=self.__class__.__name__, functionName="run",
                          event=f"Generating PortfolioGreeksReport: {name}")

        job_logger = ReportJobLogger()
        job_logger.start_job(self.__class__.__name__, 'OptionStrategyReport',
                             params={'report_name': name, 'start_date': start_date,
                                     'end_date': end_date})
        try:
            logger.info(f"Step 1/3: 拉取 {self.TABLE_SOURCE} 数据")
            df = self.fetch_data(start_date=start_date, end_date=end_date)
            if df.empty:
                logger.warning("数据为空（请先运行 PortfolioGreeksAggregatorTest 落库），流程终止")
                job_logger.end_job_success(records_processed=0)
                return None

            logger.info("Step 2/3: 数据清洗 & 生成图表")
            df = self.clean_data(df)
            latest_date, latest = self._latest_snapshot(df)

            chart_buffers = {}
            chart_buffers['chart1'] = self.gen_chart1_greeks_by_maturity(latest)
            chart_buffers['chart2'] = self.gen_chart2_pnl_explain(latest)
            chart_count = sum(1 for v in chart_buffers.values() if v is not None)
            logger.info(f"图表生成完成: {chart_count} 张")

            logger.info("Step 3/3: 生成 PDF 报告")
            pdf_path = self._generate_pdf_report(df, chart_buffers, config, latest_date)

            logger.info("\n" + "=" * 80)
            logger.info(f"[{name}] 组合 Greeks 报告 生成完成！")
            logger.info(f"   Report: {pdf_path}")
            logger.info("=" * 80)
            job_logger.end_job_success(records_processed=len(df))
            return pdf_path

        except Exception as e:
            logger.error(f"报告生成失败: {e}")
            logger.error(traceback.format_exc())
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise

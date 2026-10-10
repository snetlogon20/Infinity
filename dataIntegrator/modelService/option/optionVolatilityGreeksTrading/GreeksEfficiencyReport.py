r"""
期权 Greeks 效率 PDF 报告生成器 — 波动率交易员/风控视角

数据源:
    tb_option_greeks_efficiency(由 GreeksEfficiencyAnalysis 写入)

报告结构:
    封面 → 数据概览 → 最新交易日 卖方Top15 / 买方Top15 明细表 → 4张图表
    → 交易员综合点评 → 指标口径 → 风险提示

核心图表:
    图1 VRP时序(日均IV vs HV20, 副轴VRPbp) —— "今天偏买方还是卖方"的温度计
    图2 最新日 IV微笑(K/S 分档 x s_month) + HV参考线
    图3 卖方效率: 日平衡波幅 vs 价态 + 已实现日波幅参考线(theta安全垫)
    图4 期限结构: ATM IV vs 剩余天数 + HV参考线

前置条件: 先运行 GreeksEfficiencyAnalysisTest 落库。

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


class GreeksEfficiencyReport:
    """Greeks 效率扫描 PDF 报告生成器"""

    REPORT_DIR = CommonParameters.optionAnalysisReportPath
    TABLE_SOURCE = 'tb_option_greeks_efficiency'
    DEFAULT_LOOKBACK_DAYS = 90
    DETAIL_TABLE_ROWS = 15
    DETAIL_TABLE_FONT_SIZE = 6.8
    DETAIL_TABLE_MIN_COL_WIDTH = 22.0

    CHART_COLORS = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6', '#f39c12',
                    '#1abc9c', '#e67e22', '#2980b9', '#c0392b', '#27ae60']
    SIGNAL_COLORS = {'SELL_VOL': '#C8E6C9', 'BUY_VOL': '#BBDEFB',
                      'NEUTRAL': '#ECEFF1', 'AVOID': '#FFCDD2'}

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
        where_clauses = []
        if start_date:
            where_clauses.append(f"trade_date >= '{start_date}'")
        if end_date:
            where_clauses.append(f"trade_date <= '{end_date}'")
        if symbol_filter:
            where_clauses.append(f"symbol LIKE '{symbol_filter}'")
        where_str = (" AND ".join(where_clauses)) if where_clauses else "1=1"
        sql = f"""
        SELECT * FROM indexsysdb.{self.TABLE_SOURCE}
        WHERE {where_str}
        ORDER BY trade_date, call_put, exercise_price
        """
        logger.info(f"SQL:\n{sql}")
        df = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        logger.info(f"Fetched {len(df)} rows, {len(df.columns)} columns")
        return df

    def clean_data(self, df):
        for col in ['exercise_price', 'spot_price', 'close', 'implied_vol', 'iv_rank',
                    'hv20', 'hv60', 'vrp', 'vrp_bp', 'vrp_ratio',
                    'delta', 'gamma', 'theta', 'vega',
                    'gamma_breakeven_move', 'gamma_breakeven_move_pct',
                    'theta_gamma_ratio', 'vega_theta_ratio',
                    'gamma_per_premium', 'vega_per_premium',
                    'close_vs_theoretical_pct', 'pcp_z_score',
                    'oi', 'vol', 'amount', 'turnover_ratio',
                    'seller_score', 'buyer_score', 'seller_rank', 'buyer_rank',
                    'days_to_maturity', 'years_to_maturity_calendar', 'moneyness_log',
                    'bs_theoretical_price']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        for col in ['trade_date', 'ts_code', 'symbol', 'opt_name', 'opt_exchange',
                    'call_put', 'underlying_key', 's_month', 'maturity_date',
                    'moneyness_status', 'price_bias', 'pcp_deviation_type',
                    'liq_flag', 'role_recommend', 'trade_signal', 'signal_reason']:
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
        valid = latest[latest['liq_flag'] == 'PASS']
        vrp = valid['vrp_bp'].dropna()
        return {
            'date_start': trade_dates[0] if trade_dates else 'N/A',
            'date_end': trade_dates[-1] if trade_dates else 'N/A',
            'n_days': len(trade_dates),
            'n_rows': len(df),
            'latest_date': df['trade_date'].max(),
            'n_contracts_latest': len(latest),
            'n_valid_latest': len(valid),
            'n_liq_fail': int((latest['liq_flag'] == 'FAIL').sum()) if len(latest) else 0,
            'vrp_mean_bp': vrp.mean() if len(vrp) else np.nan,
            'vrp_max_bp': vrp.max() if len(vrp) else np.nan,
            'vrp_min_bp': vrp.min() if len(vrp) else np.nan,
            'iv_mean': valid['implied_vol'].dropna().mean() * 100
                if valid['implied_vol'].dropna().size else np.nan,
            'hv_mean': valid['hv20'].dropna().mean() * 100
                if valid['hv20'].dropna().size else np.nan,
            'n_sell_vol': int((latest['trade_signal'] == 'SELL_VOL').sum()),
            'n_buy_vol': int((latest['trade_signal'] == 'BUY_VOL').sum()),
            'n_seller_role': int((latest['role_recommend'] == 'SELLER').sum()),
            'n_buyer_role': int((latest['role_recommend'] == 'BUYER').sum()),
            'n_pcp_alert': int((valid['pcp_z_score'].abs() > 2).sum())
                if valid['pcp_z_score'].size else 0,
        }

    # ===================== 图表 =====================

    def gen_chart1_vrp_timeseries(self, df):
        """图1: VRP 时序(日均 IV vs HV20, 副轴 VRP bp)"""
        daily = df.groupby('trade_date_dt').agg(
            iv=('implied_vol', 'mean'), hv=('hv20', 'mean')).dropna()
        daily = daily[daily['iv'] > 0]
        if len(daily) < 2:
            logger.warning("No valid data for chart 1, skipping")
            return None

        fig, ax = plt.subplots(figsize=(20, 8))
        fig.suptitle('图1：波动率风险溢价 VRP 时序（日均 IV vs HV20，副轴 VRP=IV−HV20）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')
        ax.plot(daily.index.tolist(), daily['iv'] * 100, color='#2980b9',
                linewidth=1.8, marker='o', markersize=3, label='日均隐含波动率 IV')
        ax.plot(daily.index.tolist(), daily['hv'] * 100, color='#27ae60',
                linewidth=1.8, marker='s', markersize=3, label='20日实际波动率 HV20')
        ax.set_ylabel('年化波动率（%）', fontsize=11)
        ax.grid(True, alpha=0.3, linestyle='--')

        ax2 = ax.twinx()
        vrp_bp = (daily['iv'] - daily['hv']) * 1e4
        ax2.bar(daily.index.tolist(), vrp_bp, color='#e74c3c', alpha=0.25,
                width=0.8, label='VRP (bp)')
        ax2.axhline(y=0, color='#e74c3c', linewidth=0.8, alpha=0.6)
        ax2.set_ylabel('VRP（bp）', fontsize=11, color='#e74c3c')
        ax2.tick_params(axis='y', labelcolor='#e74c3c')

        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='upper center',
                  bbox_to_anchor=(0.5, -0.10), fontsize=9, ncol=3, frameon=True)
        fig.autofmt_xdate(rotation=45, ha='right')
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    def gen_chart2_smile(self, latest):
        """图2: 最新日 IV 微笑(K/S 分档, 按 s_month, C/P 分别标记)"""
        sub = latest[latest['implied_vol'].notna() & (latest['implied_vol'] > 0)]
        if sub.empty:
            logger.warning("No valid data for chart 2, skipping")
            return None
        hv_ref = sub['hv20'].dropna().mean()

        fig, ax = plt.subplots(figsize=(20, 8))
        fig.suptitle('图2：最新交易日 IV 微笑曲线（横轴 K/S，按到期月，C●/P×）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')
        months = sorted(sub['s_month'].unique())
        for i, m in enumerate(months):
            g = sub[sub['s_month'] == m].sort_values('exercise_price')
            for cp, marker in [('C', 'o'), ('P', 'X')]:
                gg = g[g['call_put'] == cp]
                if gg.empty:
                    continue
                ax.plot(gg['exercise_price'] / gg['spot_price'],
                        gg['implied_vol'] * 100,
                        color=self.CHART_COLORS[i % len(self.CHART_COLORS)],
                        marker=marker, markersize=5, linewidth=1.4,
                        label=f'{m} {"Call" if cp == "C" else "Put"}')
        if pd.notna(hv_ref) and hv_ref > 0:
            ax.axhline(y=hv_ref * 100, color='#27ae60', linewidth=1.4,
                       linestyle='--', label=f'HV20={hv_ref*100:.1f}%')
        ax.axvline(x=1.0, color='#7f8c8d', linewidth=0.8, linestyle=':')
        ax.set_xlabel('K / S（行权价 / 现价）', fontsize=11)
        ax.set_ylabel('隐含波动率 IV（%）', fontsize=11)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10),
                  fontsize=8, ncol=6, frameon=True)
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    def gen_chart3_seller_efficiency(self, latest):
        """图3: 卖方效率 —— 日平衡波幅 vs 价态, 对照已实现日波幅"""
        sub = latest[latest['gamma_breakeven_move_pct'].notna()]
        if sub.empty:
            logger.warning("No valid data for chart 3, skipping")
            return None
        hv = sub['hv20'].dropna().mean()
        realized_daily = hv / np.sqrt(252.0) * 100 if pd.notna(hv) and hv > 0 else np.nan

        fig, ax = plt.subplots(figsize=(20, 8))
        fig.suptitle('图3：卖方效率 —— 日平衡波幅 vs 价态'
                     '（sqrt(2·|Θ|/Γ)/S，超过此波幅 theta 收入被 gamma 损失吃掉）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')
        for cp, clr, marker in [('C', '#2980b9', 'o'), ('P', '#e74c3c', 'X')]:
            g = sub[sub['call_put'] == cp].sort_values('moneyness_log')
            if g.empty:
                continue
            ax.plot(g['moneyness_log'], g['gamma_breakeven_move_pct'],
                    color=clr, marker=marker, markersize=5, linewidth=1.5,
                    label=f'{"认购C" if cp == "C" else "认沽P"} 日平衡波幅')
        if pd.notna(realized_daily):
            ax.axhline(y=realized_daily, color='#27ae60', linewidth=1.6,
                       linestyle='--', label=f'已实现日波幅(HV20/√252)={realized_daily:.2f}%')
        ax.axvline(x=0, color='#7f8c8d', linewidth=0.8, linestyle=':')
        ax.set_xlabel('对数价态 ln(K/S)/√T（0=平值，负=实值Call）', fontsize=11)
        ax.set_ylabel('日平衡波幅（% 现价）', fontsize=11)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10),
                  fontsize=9, ncol=3, frameon=True)
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    def gen_chart4_term_structure(self, latest):
        """图4: 期限结构(ATM IV vs 剩余天数, 按标的)"""
        atm = latest[(latest['moneyness_log'].abs() <= 0.05)
                     & latest['implied_vol'].notna()]
        if atm.empty:
            logger.warning("No valid data for chart 4, skipping")
            return None
        pts = (atm.groupby(['underlying_key', 's_month', 'days_to_maturity'])
               ['implied_vol'].mean().reset_index()
               .groupby(['underlying_key', 's_month', 'days_to_maturity'])
               ['implied_vol'].mean().reset_index())
        hv_ref = latest['hv20'].dropna().mean()

        fig, ax = plt.subplots(figsize=(20, 8))
        fig.suptitle('图4：期限结构 —— ATM IV（|ln(K/S)/√T|≤0.05）vs 剩余天数',
                     fontsize=14, fontweight='bold', color='#1a1a2e')
        for i, (key, g) in enumerate(pts.groupby('underlying_key')):
            g = g.sort_values('days_to_maturity')
            ax.plot(g['days_to_maturity'], g['implied_vol'] * 100,
                    color=self.CHART_COLORS[i % len(self.CHART_COLORS)],
                    marker='o', markersize=6, linewidth=1.6,
                    label=f'标的 {key}（按月均值）')
        if pd.notna(hv_ref) and hv_ref > 0:
            ax.axhline(y=hv_ref * 100, color='#27ae60', linewidth=1.4,
                       linestyle='--', label=f'HV20={hv_ref*100:.1f}%')
        ax.set_xlabel('剩余天数（日历日）', fontsize=11)
        ax.set_ylabel('ATM IV（%）', fontsize=11)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10),
                  fontsize=9, ncol=4, frameon=True)
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    # ===================== 明细表 =====================

    def _build_role_table(self, latest, role):
        """最新日 卖方/买方 Top N 明细(按对应评分降序)"""
        score_col = 'seller_score' if role == 'SELLER' else 'buyer_score'
        rank_col = 'seller_rank' if role == 'SELLER' else 'buyer_rank'
        cand = latest[(latest['liq_flag'] == 'PASS')
                      & latest[score_col].notna()].copy()
        if cand.empty:
            return [], []
        cand = cand.sort_values(score_col, ascending=False).head(self.DETAIL_TABLE_ROWS)

        rows = []
        for _, r in cand.iterrows():
            rows.append([
                str(r.get('trade_date', '')),
                str(r.get('opt_name', '') or r.get('ts_code', '')),
                str(r.get('call_put', '')),
                self._fmt(r.get('exercise_price'), '{:.4g}'),
                self._fmt(r.get('spot_price'), '{:.4f}'),
                str(r.get('s_month', '')),
                self._fmt(r.get('days_to_maturity'), '{:.0f}'),
                self._fmt(r.get('implied_vol'), '{:.2%}'),
                self._fmt(r.get('iv_rank'), '{:.2f}'),
                self._fmt(r.get('hv20'), '{:.2%}'),
                self._fmt(r.get('vrp_bp'), '{:+.0f}'),
                self._fmt(r.get('gamma_breakeven_move_pct'), '{:.2f}'),
                self._fmt(r.get('theta'), '{:+.4g}'),
                self._fmt(r.get('gamma'), '{:.4g}'),
                self._fmt(r.get('vega'), '{:.4g}'),
                self._fmt(r.get('close_vs_theoretical_pct'), '{:+.1f}'),
                self._fmt(r.get('pcp_z_score'), '{:+.1f}'),
                self._fmt(r.get('oi'), '{:.0f}'),
                self._fmt(r.get(score_col), '{:.0f}'),
                self._fmt(r.get(rank_col), '{:.0f}'),
                str(r.get('trade_signal', '')),
            ])
        header = ['交易日', '合约', 'C/P', 'K', 'S现货', '结算月', '剩余天数', 'IV',
                  'IV分位', 'HV20', 'VRPbp', '日平衡%', 'Θ', 'Γ', 'Vega',
                  '定价偏差%', 'PCPz', 'OI', '评分', '排名', '信号']
        return header, rows

    # ===================== 点评 =====================

    def _build_trader_commentary(self, df, latest, stats):
        paras = []

        # 1. VRP 环境
        vrp_mean = stats['vrp_mean_bp']
        if pd.notna(vrp_mean):
            if vrp_mean > 150:
                verdict = ("隐含显著贵于实际（卖方收租环境）：优先考虑卖波动率结构"
                           "（short straddle/strangle），但要核对日平衡波幅是否覆盖已实现日波幅。")
            elif vrp_mean < -50:
                verdict = ("隐含便宜于实际（买方占优环境）：优先考虑买波动率结构"
                           "（long straddle/strangle、日历多头远月），用 gamma/权利金比选腿。")
            else:
                verdict = ("VRP 处于中性区间：方向不明，以价差结构（spread/calendar）"
                           "降低单边 Greeks 敞口为主。")
            paras.append(('VRP 环境判断',
                          f"最新交易日（{stats['latest_date']}）{stats['n_valid_latest']} 个"
                          f"有效合约：日均 IV {self._fmt(stats['iv_mean'], '{:.1f}')}% vs "
                          f"HV20 {self._fmt(stats['hv_mean'], '{:.1f}')}%，"
                          f"VRP 均值 {self._fmt(vrp_mean, '{:+.0f}')}bp"
                          f"（区间 {self._fmt(stats['vrp_min_bp'], '{:+.0f}')}"
                          f"~{self._fmt(stats['vrp_max_bp'], '{:+.0f}')}bp）。{verdict}"))

        # 2. 最优卖方/买方标的
        for role, cn in [('SELLER', '卖方'), ('BUYER', '买方')]:
            score_col = 'seller_score' if role == 'SELLER' else 'buyer_score'
            top = latest[(latest['liq_flag'] == 'PASS')
                         & latest[score_col].notna()].sort_values(
                score_col, ascending=False)
            if len(top):
                r = top.iloc[0]
                paras.append((f'最优{cn}候选',
                              f"{cn}评分第一：{r.get('opt_name') or r.get('ts_code')}"
                              f"（K={self._fmt(r.get('exercise_price'), '{:.4g}')}"
                              f"，剩余 {self._fmt(r.get('days_to_maturity'), '{:.0f}')} 天，"
                              f"IV {self._fmt(r.get('implied_vol'), '{:.2%}')}"
                              f"，VRP {self._fmt(r.get('vrp_bp'), '{:+.0f}')}bp，"
                              f"日平衡波幅 {self._fmt(r.get('gamma_breakeven_move_pct'), '{:.2f}')}%。"
                              f"最新日 SELL_VOL/BUY_VOL 信号 "
                              f"{stats['n_sell_vol']}/{stats['n_buy_vol']} 个。"))

        # 3. 流动性与数据质量
        risk_items = []
        if stats['n_liq_fail'] > 0:
            risk_items.append(f"流动性闸门 FAIL {stats['n_liq_fail']} 个合约"
                              f"（OI/成交额不足或到期窗口外，已排除信号）")
        if stats['n_pcp_alert'] > 0:
            risk_items.append(f"PCP |z|>2 的档位 {stats['n_pcp_alert']} 个"
                              f"（同K档 C/P 结构性错价，报价可信度低）")
        paras.append(('流动性与数据质量',
                      '；'.join(risk_items) + '。' if risk_items
                      else '未发现流动性/PCP 异常。'))
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
            f"GREEKS_EFFICIENCY_{tag}_{stats['date_start']}-{stats['date_end']}_{now_ts}.pdf")

        doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4),
                                rightMargin=32, leftMargin=32, topMargin=36, bottomMargin=28)
        page_width = landscape(A4)[0] - 64
        story = []

        # 封面
        story.append(Spacer(1, 1.4 * inch))
        story.append(Paragraph('期权 Greeks 效率扫描报告', styles['title']))
        story.append(Paragraph('Volatility Risk Premium · Greeks Efficiency Ratios',
                               ParagraphStyle('Sub', parent=styles['normal'], alignment=1,
                                              fontSize=11, fontName=self.reportlab_font,
                                              textColor=colors.HexColor('#888888'))))
        story.append(Spacer(1, 0.35 * inch))
        story.append(Paragraph(
            f"定位：回答“今天该做买方还是卖方、哪几个合约性价比最高”<br/>"
            f"数据区间：{stats['date_start']} — {stats['date_end']}（{stats['n_days']} 个交易日）<br/>"
            f"报告生成时间：{report_date}<br/>"
            f"数据记录：{stats['n_rows']} 条 | 最新日合约：{stats['n_contracts_latest']} 个"
            f"（流动性通过 {stats['n_valid_latest']}）<br/>"
            f"<br/>INFINITY 量化系统 · 期权波动率与 Greeks 研究",
            styles['cover_info']))
        story.append(PageBreak())

        # 一、数据概览
        story.append(Paragraph('一、数据概览（关键数字）', styles['h1']))
        story.append(Paragraph(
            f"最新交易日 {latest_date}：{stats['n_valid_latest']} 个有效合约，"
            f"日均 IV {self._fmt(stats['iv_mean'], '{:.1f}')}% vs "
            f"HV20 {self._fmt(stats['hv_mean'], '{:.1f}')}%，"
            f"VRP 均值 {self._fmt(stats['vrp_mean_bp'], '{:+.0f}')}bp"
            f"（区间 {self._fmt(stats['vrp_min_bp'], '{:+.0f}')} ~ "
            f"{self._fmt(stats['vrp_max_bp'], '{:+.0f}')}bp）；"
            f"角色推荐：卖方 {stats['n_seller_role']} 个 / 买方 {stats['n_buyer_role']} 个；"
            f"信号：SELL_VOL {stats['n_sell_vol']} 个、BUY_VOL {stats['n_buy_vol']} 个。",
            styles['normal']))
        story.append(PageBreak())

        # 二、卖方 Top15
        header, rows = self._build_role_table(latest, 'SELLER')
        story.append(Paragraph(
            f'二、最新交易日（{latest_date}）卖方 Top {self.DETAIL_TABLE_ROWS}'
            f'（按卖方分降序：高 IV / 高 VRP / 高日平衡波幅优先）', styles['h1']))
        if rows:
            col_widths = self._calc_col_widths(header, rows, page_width,
                                               self.DETAIL_TABLE_FONT_SIZE)
            story.append(self._make_table(header, rows, col_widths))
        else:
            story.append(Paragraph('最新交易日无有效卖方候选。', styles['normal']))
        story.append(PageBreak())

        # 三、买方 Top15
        header, rows = self._build_role_table(latest, 'BUYER')
        story.append(Paragraph(
            f'三、最新交易日（{latest_date}）买方 Top {self.DETAIL_TABLE_ROWS}'
            f'（按买方分降序：低 IV / 负 VRP / 高 gamma 每权利金优先）', styles['h1']))
        if rows:
            col_widths = self._calc_col_widths(header, rows, page_width,
                                               self.DETAIL_TABLE_FONT_SIZE)
            story.append(self._make_table(header, rows, col_widths))
            story.append(Spacer(1, 0.08 * inch))
            story.append(Paragraph(
                '注1（口径）：IV/IV分位/HV20 中 IV 分位为该合约近 60 日 IV 经验分位（0~1），'
                'HV20 由标的现货收盘序列现算（年化，√252）；VRPbp = (IV−HV20)×1e4，'
                '正=隐含贵于实际（偏卖方），负=倒挂（偏买方）。<br/>'
                '注2（卖方刻度）：日平衡波幅% = sqrt(2·|Θ|/Γ)/S —— delta 对冲持仓下，'
                '当日标的真实波幅超过此值，gamma 损失吃掉 theta 收入；'
                '与图3绿色虚线（已实现日波幅 HV20/√252）对照，绿线低于曲线的档位才是“收租安全区”。<br/>'
                '注3（买方刻度）：评分含 gamma/权利金与市价−理论价（买便宜）；'
                'PCPz 为同 K 档 C/P 配对的平价 z-score，|z|>2 的报价可信度低。<br/>'
                '注4：流动性闸门 = OI≥500 手 且 当日成交额≥20 万元 且 距到期 5~270 天；'
                '评分为同日百分位加权合成（VRP 40% + IV分位/平衡波幅/定价偏差 各 20%），仅相对排序有意义。',
                styles['table_note']))
        else:
            story.append(Paragraph('最新交易日无有效买方候选。', styles['normal']))
        story.append(PageBreak())

        # 四~七、图表
        chart_sections = []
        if chart_buffers.get('chart1'):
            chart_sections.append(('chart1', '图1：VRP 时序（买方/卖方温度计）',
                                   f"VRP 均值 {self._fmt(stats['vrp_mean_bp'], '{:+.0f}')}bp。"
                                   "红线柱体持续为正=隐含系统性贵于实际（卖方环境）；"
                                   "持续为负=倒挂（买方环境）。这是本报告的总纲："
                                   "先定买/卖方向，再在明细表里选腿。"))
        if chart_buffers.get('chart2'):
            chart_sections.append(('chart2', '图2：最新日 IV 微笑曲线',
                                   "各色线为不同到期月，●=Call ×=Put，绿色虚线=HV20。"
                                   "翼部高于平值=微笑明显（卖方在翼部收租更厚）；"
                                   "C/P 同档 IV 明显分叉=报价失真（结合 PCPz 列判断）。"))
        if chart_buffers.get('chart3'):
            chart_sections.append(('chart3', '图3：卖方效率（日平衡波幅 vs 价态）',
                                   "曲线=theta 安全垫能承受的日波幅；绿虚线=市场真实日波幅。"
                                   "曲线在绿线之上的档位：theta 收入覆盖 gamma 风险，是卖方安全区；"
                                   "反之卖方在为波动率倒贴。"))
        if chart_buffers.get('chart4'):
            chart_sections.append(('chart4', '图4：期限结构（ATM IV vs 剩余天数）',
                                   "远月高于近月=正期限结构（卖近买远的日历价差占优）；"
                                   "近月高于远月=倒挂（事件驱动/分红季，买近卖远谨慎）。"))

        for i, (key, title, note) in enumerate(chart_sections):
            section_cn = ['四', '五', '六', '七'][i] if i < 4 else str(i + 4)
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
        next_cn = str(len(chart_sections) + 4)
        story.append(Paragraph(f'{next_cn}、交易员综合点评（自动生成）', styles['h1']))
        for title, text in self._build_trader_commentary(df, latest, stats):
            story.append(Paragraph(f'<b>{title}</b>', styles['h1']))
            story.append(Paragraph(text, styles['normal']))
            story.append(Spacer(1, 0.10 * inch))
        story.append(PageBreak())

        # 指标口径
        story.append(Paragraph(f'{int(next_cn) + 1}、指标口径', styles['h1']))
        story.append(Paragraph(
            "VRP（波动率风险溢价）= IV − HV20：隐含贵于实际的幅度，正=卖方收租的“溢价”，"
            "负=倒挂（买方占优）。<br/>"
            "HV20/HV60 = 标的现货对数收益 20/60 日滚动标准差 × √252（年化）。<br/>"
            "IV 分位 = 该合约近 60 日 IV 的经验分位（0~1）。<br/>"
            "日平衡波幅 = sqrt(2·|Θ|/Γ)：delta 对冲下 gamma 损失（0.5·Γ·dS²）等于 theta 收入"
            "（|Θ|）的日波幅 dS；占现价% 后与“已实现日波幅（HV20/√252）”直接对照。<br/>"
            "Θ/Γ、Vega/|Θ|、Γ/权利金、Vega/权利金 = Greeks 效率比：分别衡量卖方效率、"
            "买方时间成本、买方单位资金敞口。<br/>"
            "定价偏差% = (收盘 − BS理论价)/理论价：单腿错价。<br/>"
            "PCPz / PCP分类 = 平价监控联查值：同 K 档 C/P 配对的结构性错价信号，"
            "|z|>2 或 REAL/STRONG_ARBITRAGE 的档位报价可信度低。<br/>"
            "流动性闸门 = OI≥500 且 成交额≥20万 且 距到期 5~270 天；FAIL 不参与评分与信号。<br/>"
            "卖方分/买方分 = 同日百分位加权（VRP 40%，其余各 20%），仅相对排序有意义；"
            "角色推荐 = |卖方分−买方分|≥10 判定，否则 NEUTRAL。<br/>"
            "信号：SELL_VOL/BUY_VOL 需角色明确且评分≥65；NEUTRAL=方向不明；AVOID=数据/闸门失败。",
            styles['normal']))
        story.append(Spacer(1, 0.15 * inch))

        # 风险提示
        story.append(Paragraph(f'{int(next_cn) + 2}、风险提示', styles['h1']))
        story.append(Paragraph(
            "本报告基于日线收盘价与 BS 框架计算，仅供策略研究参考，不构成投资建议。<br/>"
            "卖方结构（SELL_VOL）非有限亏损：保证金随波动动态上调，务必预留追加资金并设止损；"
            "日平衡波幅只覆盖一阶 theta/gamma 平衡，跳空与波动率骤升仍可造成超预期亏损。<br/>"
            "VRP 均值会平滑个别档位异常，选腿时务必回到明细表核对 OI、盘口宽度与 PCPz。<br/>"
            "HV 为历史统计，不含未来事件（分红/政策/宏观数据）冲击；分红季（11~12月）"
            "q 估计误差会同时扭曲 IV 与 PCP 读数。<br/>"
            "评分为同日相对排序，跨日不可直接比较分数绝对值。",
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
                          event=f"Generating GreeksEfficiencyReport: {name}")

        job_logger = ReportJobLogger()
        job_logger.start_job(self.__class__.__name__, 'OptionStrategyReport',
                             params={'report_name': name, 'start_date': start_date,
                                     'end_date': end_date, 'symbol_filter': symbol_filter})
        try:
            logger.info(f"Step 1/3: 拉取 {self.TABLE_SOURCE} 数据")
            df = self.fetch_data(start_date=start_date, end_date=end_date,
                                 symbol_filter=symbol_filter)
            if df.empty:
                logger.warning("数据为空（请先运行 GreeksEfficiencyAnalysisTest 落库），流程终止")
                job_logger.end_job_success(records_processed=0)
                return None

            logger.info("Step 2/3: 数据清洗 & 生成图表")
            df = self.clean_data(df)
            latest_date, latest = self._latest_snapshot(df)
            stats = self._build_overview_numbers(df, latest)

            chart_buffers = {}
            chart_buffers['chart1'] = self.gen_chart1_vrp_timeseries(df)
            chart_buffers['chart2'] = self.gen_chart2_smile(latest)
            chart_buffers['chart3'] = self.gen_chart3_seller_efficiency(latest)
            chart_buffers['chart4'] = self.gen_chart4_term_structure(latest)
            chart_count = sum(1 for v in chart_buffers.values() if v is not None)
            logger.info(f"图表生成完成: {chart_count} 张")

            logger.info("Step 3/3: 生成 PDF 报告")
            pdf_path = self._generate_pdf_report(df, chart_buffers, config, stats)

            logger.info("\n" + "=" * 80)
            logger.info(f"[{name}] Greeks 效率报告 生成完成！")
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

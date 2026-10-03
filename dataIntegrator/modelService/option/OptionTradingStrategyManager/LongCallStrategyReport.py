r"""
Long Call（牛市买购）策略 PDF 报告生成器 — 资深交易员/风控视角

数据源：
    tb_option_trading_strategy_long_call (strategy_type='LONG_CALL'，
    由 LongCallStrategyAnalysis 写入，含 analysis_time/analysis_params 审计字段)

报告结构：
    封面 → 数据概览(数字) → 最新交易日核心指标总览(表格) → 10张图表(各配数字说明)
    → 交易信号汇总(表格) → 资深交易员综合点评(自动生成, 含数字) → 指标口径 → 风险提示

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


class LongCallStrategyReport:
    """Long Call（牛市买购）策略 报告生成器"""

    REPORT_DIR = CommonParameters.optionAnalysisReportPath
    TABLE_SOURCE = 'tb_option_trading_strategy_long_call'
    STRATEGY_TYPE = 'LONG_CALL'

    # 情景因子（与分析端 DEFAULT_SCENARIOS 一致，上行为主）
    SCENARIO_FACTORS = [0.90, 0.95, 1.00, 1.03, 1.05, 1.10, 1.15, 1.20]

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

    def fetch_data(self, start_date=None, end_date=None, symbol_filter=None, call_put='C'):
        """从 tb_option_trading_strategy_long_call 拉取 LONG_CALL 策略分析结果"""
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
        ORDER BY trade_date, exercise_price
        """
        logger.info(f"SQL:\n{sql}")
        df = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        logger.info(f"Fetched {len(df)} rows, {len(df.columns)} columns")
        return df

    def clean_data(self, df):
        """类型转换与派生列"""
        numeric_cols = [
            'exercise_price', 'opt_multiplier', 'spot_price', 'premium',
            'implied_vol', 'iv_rank', 'delta', 'gamma', 'theta', 'vega',
            'bs_theoretical_price', 'close_vs_theoretical', 'close_vs_theoretical_pct',
            'premium_ratio_pct', 'annualized_premium_cost_pct',
            'theta_cost_daily', 'theta_cost_total', 'theta_cost_pct_of_premium',
            'breakeven_S_T', 'breakeven_required_upside_pct',
            'max_loss', 'max_loss_cny', 'max_loss_pct_of_spot', 'itm_prob',
            'capital_leverage', 'delta_leverage', 'effective_delta_exposure',
            'upside_capture',
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

        df = df.sort_values(['ts_code', 'trade_date']).reset_index(drop=True)
        df['trade_date_dt'] = pd.to_datetime(df['trade_date'], format='%Y%m%d', errors='coerce')
        return df

    # ===================== 通用工具 =====================

    def _build_label_map(self, df):
        """ts_code → 显示名（优先 opt_name，回退 symbol，再回退 ts_code）"""
        label_map = {}
        if 'ts_code' not in df.columns:
            return label_map
        cols = [c for c in ('ts_code', 'opt_name', 'symbol') if c in df.columns]
        subset = df[cols].astype(str).drop_duplicates(subset='ts_code')
        for _, row in subset.iterrows():
            label = str(row.get('opt_name', '')).strip()
            if label in ('', 'nan', 'None', 'NaT'):
                label = str(row.get('symbol', '')).strip()
            if label in ('', 'nan', 'None', 'NaT'):
                label = str(row['ts_code'])
            label_map[str(row['ts_code'])] = label
        return label_map

    def _fig_to_bytesio(self, fig, dpi=160):
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        return buf

    def _prep_series(self, df, value_cols):
        """按 ts_code 构建 {ts_code: DataFrame(index=trade_date_dt)}"""
        ts_codes = sorted(df['ts_code'].dropna().unique())
        series_dict = {}
        valid_ts = set()
        for ts_code in ts_codes:
            sub = df[df['ts_code'] == ts_code].set_index('trade_date_dt')
            for col in value_cols:
                if col in sub.columns and sub[col].notna().sum() > 0:
                    valid_ts.add(ts_code)
                    break
        for ts_code in sorted(valid_ts):
            series_dict[ts_code] = df[df['ts_code'] == ts_code].set_index('trade_date_dt')
        return sorted(valid_ts), series_dict

    def _add_end_labels(self, ax, ts_codes, series_dict, y_col, label_map,
                        colors=None, x_pad_frac=0.14, label_fontsize=7):
        """折线右端打合约名称标签"""
        if colors is None:
            colors = self.CHART_COLORS
        xlim = ax.get_xlim()
        if xlim[1] > xlim[0]:
            ax.set_xlim(xlim[0], xlim[1] + (xlim[1] - xlim[0]) * x_pad_frac)
        for idx, ts_code in enumerate(ts_codes):
            if ts_code not in series_dict:
                continue
            sub = series_dict[ts_code]
            if y_col not in sub.columns:
                continue
            s = sub[y_col].dropna()
            if len(s) == 0:
                continue
            color = colors[idx % len(colors)]
            ax.annotate(
                label_map.get(ts_code, ts_code),
                xy=(s.index[-1], s.iloc[-1]),
                xytext=(6, 0), textcoords='offset points',
                color=color, fontsize=label_fontsize, fontweight='bold',
                va='center', ha='left',
                bbox=dict(boxstyle='round,pad=0.18', facecolor='white',
                          edgecolor=color, linewidth=0.5, alpha=0.85),
                zorder=10,
            )

    # ===================== 图表生成 =====================

    def _gen_metric_chart(self, df, y_col, y_label, chart_num, title_prefix,
                          y2_col=None, y2_label=None, ref_lines=None, ref_lines2=None):
        """通用时间序列图：X=trade_date，每合约一条线（可选第二指标轴）"""
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName=f"gen_chart{chart_num}",
                          event=f"Generating chart {chart_num}: {y_label}")

        value_cols = [y_col] + ([y2_col] if y2_col else [])
        ts_codes, series_dict = self._prep_series(df, value_cols)
        if not ts_codes:
            logger.warning(f"No valid ts_code for chart {chart_num}, skipping")
            return None

        label_map = self._build_label_map(df)
        fig, ax1 = plt.subplots(figsize=(20, 8))
        fig.suptitle(title_prefix, fontsize=14, fontweight='bold', color='#1a1a2e')

        for idx, ts_code in enumerate(ts_codes):
            sub = series_dict[ts_code]
            if y_col in sub.columns and sub[y_col].notna().sum() > 0:
                s = sub[y_col].dropna()
                color = self.CHART_COLORS[idx % len(self.CHART_COLORS)]
                ax1.plot(s.index.tolist(), s.values, color=color, linewidth=1.0,
                         alpha=0.8, marker='o', markersize=3,
                         label=label_map.get(ts_code, ts_code))

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
            for idx, ts_code in enumerate(ts_codes):
                sub = series_dict[ts_code]
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

        self._add_end_labels(ax1, ts_codes, series_dict, y_col, label_map)

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

    def gen_chart1_spot_premium(self, df):
        """图1：现货价(Y1) + 各合约 Call 权利金(Y2)"""
        ts_codes, series_dict = self._prep_series(df, ['spot_price', 'premium'])
        if not ts_codes:
            return None
        label_map = self._build_label_map(df)

        fig, ax1 = plt.subplots(figsize=(20, 8))
        fig.suptitle('图1：标的现货价格 + 各合约 Call 权利金 (premium)',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        # Y1: spot
        spot_series = None
        for ts_code in ts_codes:
            sub = series_dict[ts_code]
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

        # Y2: premium
        ax2 = ax1.twinx()
        for idx, ts_code in enumerate(ts_codes):
            sub = series_dict[ts_code]
            if 'premium' in sub.columns and sub['premium'].notna().sum() > 0:
                s = sub['premium'].dropna()
                color = self.CHART_COLORS[idx % len(self.CHART_COLORS)]
                ax2.plot(s.index.tolist(), s.values, color=color, linewidth=0.9,
                         alpha=0.8, marker='o', markersize=3,
                         label=label_map.get(ts_code, ts_code))
        ax2.set_ylabel('premium (Call 权利金)', fontsize=11)

        xlim = ax2.get_xlim()
        if xlim[1] > xlim[0]:
            ax2.set_xlim(xlim[0], xlim[1] + (xlim[1] - xlim[0]) * 0.14)
        for idx, ts_code in enumerate(ts_codes):
            sub = series_dict[ts_code]
            if 'premium' not in sub.columns:
                continue
            s = sub['premium'].dropna()
            if len(s) == 0:
                continue
            color = self.CHART_COLORS[idx % len(self.CHART_COLORS)]
            ax2.annotate(label_map.get(ts_code, ts_code),
                         xy=(s.index[-1], s.iloc[-1]), xytext=(6, 0),
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
            df, 'implied_vol', '隐含波动率 (implied_vol, 小数)',
            chart_num=2, title_prefix='图2：各合约 隐含波动率 IV（买方成本的核心输入）')

    def gen_chart3_iv_rank(self, df):
        return self._gen_metric_chart(
            df, 'iv_rank', 'IV 分位数 iv_rank (0~1)',
            chart_num=3, title_prefix='图3：IV 分位数 — 买方成本温度计',
            ref_lines=[
                (0.35, '#27ae60', '--', '买方有利 (<=0.35)'),
                (0.50, '#f39c12', '--', '中性'),
                (0.80, '#c0392b', '--', '高位买波 (>=0.80, 权利金贵)'),
            ])

    def gen_chart4_leverage(self, df):
        return self._gen_metric_chart(
            df, 'capital_leverage', '资金杠杆 S/C (倍)',
            chart_num=4, title_prefix='图4：资金杠杆(实线) + 弹性杠杆(虚线)',
            y2_col='delta_leverage', y2_label='弹性杠杆 Δ×S/C (现货涨1%的买方收益率%)',
            ref_lines=[
                (3.0, '#c0392b', '--', '杠杆不足 (=3x)'),
                (5.0, '#f39c12', '--', '可参与 (=5x)'),
                (10.0, '#27ae60', '--', '优质 (=10x)'),
                (15.0, '#1a1a2e', '--', '黄金窗口 (=15x)'),
            ])

    def gen_chart5_breakeven(self, df):
        return self._gen_metric_chart(
            df, 'breakeven_required_upside_pct', '回本所需涨幅 (%)',
            chart_num=5, title_prefix='图5：回本所需涨幅(实线) + 到期实值概率(虚线)',
            y2_col='itm_prob', y2_label='到期实值概率 (≈delta)')

    def gen_chart6_cost(self, df):
        return self._gen_metric_chart(
            df, 'premium_ratio_pct', '权利金成本占比 C/S0 (%)',
            chart_num=6, title_prefix='图6：买方成本(实线) + 年化成本(虚线)',
            y2_col='annualized_premium_cost_pct', y2_label='年化权利金成本 (%)',
            ref_lines=[
                (2.0, '#27ae60', '--', '便宜 (=2%)'),
                (5.0, '#f39c12', '--', '中等 (=5%)'),
                (10.0, '#c0392b', '--', '昂贵 (=10%)'),
            ])

    def gen_chart7_payoff_curve(self, df):
        """图7：经典厂字形到期收益结构（代表合约=平值ATM，含时间价值对照曲线）

        教科书式画法：
        - 代表合约（|K−S0| 最小的平值合约）到期收益 max(S_T−K,0)−C 加粗主曲线；
        - 横平台=最大亏损−C（红虚线标注）、K 处拐点（橙点线）、盈亏平衡点 K+C（绿点标注）；
        - 盈利/亏损区间淡绿/淡红着色；其余合约淡化为背景；
        - 叠加当日 BS 理论价曲线（蓝虚线）：时间价值垫在厂字形上方，随到期收敛为厂字形。
        """
        latest_date = df['trade_date'].max()
        df_latest = df[df['trade_date'] == latest_date].dropna(
            subset=['spot_price', 'exercise_price', 'premium'])
        if df_latest.empty:
            return None

        S0 = float(df_latest['spot_price'].iloc[0])
        label_map = self._build_label_map(df)

        # ---- 代表合约：行权价最贴近现货（平值 ATM） ----
        rep_pos = (df_latest['exercise_price'] - S0).abs().argsort().iloc[0]
        rep = df_latest.iloc[rep_pos]
        K, C = float(rep['exercise_price']), float(rep['premium'])
        rep_name = label_map.get(rep['ts_code'], rep['ts_code'])

        x = np.linspace(0.80 * S0, 1.25 * S0, 400)
        payoff = np.maximum(x - K, 0) - C  # 厂字形到期收益

        fig, ax = plt.subplots(figsize=(20, 10))
        fig.suptitle(f'图7：Long Call 经典到期收益结构（厂字形）— {rep_name}（{latest_date}）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        # ---- 其余合约淡化为背景 ----
        for idx, (_, row) in enumerate(df_latest.iterrows()):
            if row['ts_code'] == rep['ts_code']:
                continue
            y_i = np.maximum(x - float(row['exercise_price']), 0) - float(row['premium'])
            ax.plot(x, y_i, color=self.CHART_COLORS[idx % len(self.CHART_COLORS)],
                    linewidth=0.7, alpha=0.25)

        # ---- 盈亏区间着色 ----
        ax.fill_between(x, payoff, 0, where=(payoff > 0), color='#27ae60',
                        alpha=0.10, label='盈利区间 (S_T > K+C)')
        ax.fill_between(x, payoff, 0, where=(payoff <= 0), color='#c0392b',
                        alpha=0.10, label='亏损区间 (锁定于权利金 C)')

        # ---- 厂字形主曲线（加粗） ----
        ax.plot(x, payoff, color='#1a1a2e', linewidth=3.0, zorder=8,
                label=f'到期收益 = max(S_T−K, 0) − C   [{rep_name}]')

        # ---- 关键标注：最大亏损平台 / 行权价拐点 ----
        ax.axhline(y=-C, color='#c0392b', linewidth=1.4, linestyle='--', alpha=0.9, zorder=6)
        ax.text(0.80 * S0, -C, f' 最大亏损平台 = −C = {C:.4g}（亏损封底）',
                fontsize=9.5, color='#c0392b', va='bottom', fontweight='bold')
        ax.axvline(x=K, color='#f39c12', linewidth=1.6, linestyle=':', alpha=0.95, zorder=6)
        ax.text(K, 0.02, f' 行权价拐点 K = {K:.4g}',
                transform=ax.get_xaxis_transform(), fontsize=9.5, color='#f39c12',
                va='bottom', fontweight='bold')

        # ---- 盈亏平衡点 K+C ----
        ax.plot([K + C], [0], marker='o', markersize=10, color='#27ae60', zorder=11)
        ax.annotate(f'盈亏平衡点 S_T = K+C = {K + C:.4g}\n（需上涨 {(K + C - S0) / S0 * 100:+.2f}%）',
                    xy=(K + C, 0), xytext=(14, -46), textcoords='offset points',
                    fontsize=10, fontweight='bold', color='#27ae60',
                    arrowprops=dict(arrowstyle='->', color='#27ae60', linewidth=1.2),
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                              edgecolor='#27ae60', alpha=0.9), zorder=12)

        # ---- 当前现货位置 ----
        ax.axvline(x=S0, color=self.SPOT_COLOR, linewidth=1.0, linestyle=':', alpha=0.6, zorder=5)
        ax.text(S0, 0.55, f' 当前现货 S0 = {S0:.4g}',
                transform=ax.get_xaxis_transform(), fontsize=9, color=self.SPOT_COLOR,
                va='center', rotation=90, alpha=0.8)

        # ---- 当日 BS 理论价曲线（含时间价值，随到期收敛为厂字形） ----
        iv = rep.get('implied_vol')
        d2m = rep.get('days_to_maturity')
        r = rep.get('risk_free_rate')
        if pd.notna(iv) and pd.notna(d2m) and float(d2m) > 0:
            try:
                from scipy.stats import norm
                T_years = float(d2m) / 365.0
                r_val = float(r) if pd.notna(r) else 0.02
                sigma = float(iv)
                d1 = (np.log(x / K) + (r_val + 0.5 * sigma ** 2) * T_years) \
                    / (sigma * np.sqrt(T_years))
                d2 = d1 - sigma * np.sqrt(T_years)
                bs_curve = x * norm.cdf(d1) - K * np.exp(-r_val * T_years) * norm.cdf(d2)
                ax.plot(x, bs_curve - C, color='#3498db', linewidth=1.8, linestyle='--',
                        alpha=0.9, zorder=7,
                        label=f'当日理论价−C（蓝虚线，距到期{float(d2m):.0f}天）：'
                              f'与厂字形的差距即时间价值，随到期收敛')
                # 时间价值区域淡蓝填充
                ax.fill_between(x, payoff, bs_curve - C, where=(bs_curve - C > payoff),
                                color='#3498db', alpha=0.08, zorder=3)
            except ImportError:
                logger.warning("scipy 不可用，跳过 BS 时间价值曲线")

        ax.axhline(y=0, color='gray', linewidth=0.8, linestyle='-', alpha=0.6)
        # Y 轴上下留白：确保厂字形平台、拐点标注、时间价值曲线均有呼吸空间
        ymin, ymax = ax.get_ylim()
        ax.set_ylim(ymin - 0.02 * (ymax - ymin), ymax + 0.05 * (ymax - ymin))
        ax.set_xlabel('到期标的价 S_T', fontsize=12, fontweight='bold')
        ax.set_ylabel('组合盈亏 (元/单位)', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10), fontsize=8.5,
                  ncol=2, frameon=True, handlelength=1.6)
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    def gen_chart8_scenario_pnl(self, df):
        """图8：情景盈亏对比（最新交易日）：X=情景因子，Long Call vs 买现货（元/单位）"""
        latest_date = df['trade_date'].max()
        df_latest = df[df['trade_date'] == latest_date]
        if df_latest.empty:
            return None
        label_map = self._build_label_map(df)

        fig, ax = plt.subplots(figsize=(20, 10))
        fig.suptitle(f'图8：多情景到期盈亏对比（{latest_date}）— X轴=S_T/K 情景因子，'
                     f'Long Call(彩线) vs 买现货(灰虚线)',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        factors = self.SCENARIO_FACTORS
        x = np.arange(len(factors))
        xticklabels = [f'{f:.2f}K' for f in factors]

        # 现货对照（取均值，各合约 S0 相同所以等价于任一合约）
        unhedged_vals = [df_latest[f'unhedged_pnl_{f:.2f}'.replace(".", "_") + "K"].mean()
                         for f in factors]
        ax.plot(x, unhedged_vals, color=self.UNHEDGED_COLOR, linewidth=2.5, linestyle='--',
                 marker='D', markersize=6, alpha=0.9, label='买现货 (直接持有)')

        for idx, (_, row) in enumerate(df_latest.iterrows()):
            vals = [row.get(f'scenario_pnl_{f:.2f}'.replace(".", "_") + "K", np.nan)
                    for f in factors]
            color = self.CHART_COLORS[idx % len(self.CHART_COLORS)]
            name = label_map.get(row['ts_code'], row['ts_code'])
            ax.plot(x, vals, color=color, linewidth=1.2, alpha=0.85,
                    marker='o', markersize=5, label=name)

        ax.axhline(y=0, color='gray', linewidth=0.8, linestyle='-', alpha=0.6)
        ax.set_xticks(x)
        ax.set_xticklabels(xticklabels, fontsize=10)
        ax.set_xlabel('情景因子 (S_T / K)', fontsize=12, fontweight='bold')
        ax.set_ylabel('组合盈亏 (元/单位)', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')

        # ---- 右端标签：每条线最右端(1.20K)打合约名称，颜色与线一致 ----
        xlim = ax.get_xlim()
        if xlim[1] > xlim[0]:
            ax.set_xlim(xlim[0], xlim[1] + (xlim[1] - xlim[0]) * 0.22)

        ax.annotate('买现货', xy=(x[-1], unhedged_vals[-1]), xytext=(6, 0),
                    textcoords='offset points', color=self.UNHEDGED_COLOR, fontsize=7,
                    fontweight='bold', va='center', ha='left',
                    bbox=dict(boxstyle='round,pad=0.18', facecolor='white',
                              edgecolor=self.UNHEDGED_COLOR, linewidth=0.5, alpha=0.85),
                    zorder=10)

        for idx, (_, row) in enumerate(df_latest.iterrows()):
            vals = [row.get(f'scenario_pnl_{f:.2f}'.replace(".", "_") + "K", np.nan)
                    for f in factors]
            if all(pd.isna(v) for v in vals):
                continue
            color = self.CHART_COLORS[idx % len(self.CHART_COLORS)]
            name = label_map.get(row['ts_code'], row['ts_code'])
            # 垂直交错偏移，避免右端标签相互重叠
            y_offset = (idx % 4 - 1.5) * 11
            ax.annotate(name, xy=(x[-1], vals[-1]), xytext=(6, y_offset),
                        textcoords='offset points', color=color, fontsize=7,
                        fontweight='bold', va='center', ha='left',
                        bbox=dict(boxstyle='round,pad=0.18', facecolor='white',
                                  edgecolor=color, linewidth=0.5, alpha=0.85),
                        zorder=10)

        n_items = len(df_latest) + 1
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10), fontsize=6.5,
                  ncol=min(n_items, 8), frameon=True, handlelength=1.2)
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    def gen_chart9_leverage_effect(self, df):
        """图9：1.10K 情景 买Call vs 买现货 平均盈亏时间序列（杠杆效果演变）"""
        col_h = 'scenario_pnl_1_10K'
        col_u = 'unhedged_pnl_1_10K'
        if col_h not in df.columns or col_u not in df.columns:
            return None

        daily = df.groupby('trade_date_dt')[[col_h, col_u]].mean().dropna(how='all')
        if daily.empty:
            return None

        fig, ax = plt.subplots(figsize=(20, 8))
        fig.suptitle('图9：1.10K 情景（标的上涨约10%）平均盈亏 — Long Call(红) vs 买现货(灰)，'
                     '红线上方斜率即杠杆效果',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        ax.plot(daily.index.tolist(), daily[col_u], color=self.UNHEDGED_COLOR,
                linewidth=2.2, linestyle='--', marker='o', markersize=4,
                label='买现货平均盈亏')
        ax.plot(daily.index.tolist(), daily[col_h], color='#c0392b',
                linewidth=2.2, marker='s', markersize=4, label='Long Call平均盈亏')
        ax.fill_between(daily.index.tolist(), daily[col_u], daily[col_h],
                        where=(daily[col_h] > daily[col_u]),
                        color='#27ae60', alpha=0.15, label='杠杆跑赢现货区间')

        ax.axhline(y=0, color='gray', linewidth=0.8, linestyle='-', alpha=0.6)
        ax.set_ylabel('盈亏 (元/单位)', fontsize=12, fontweight='bold')
        ax.set_xlabel('交易日', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12), fontsize=9,
                  ncol=3, frameon=True)

        # 最新数值标注
        if len(daily) > 0:
            ax.annotate(f'最新: 买Call{daily[col_h].iloc[-1]:+.4f} / 现货{daily[col_u].iloc[-1]:+.4f}',
                        xy=(daily.index[-1], daily[col_h].iloc[-1]), xytext=(10, 10),
                        textcoords='offset points', fontsize=9, fontweight='bold',
                        color='#c0392b',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                                  edgecolor='#c0392b', alpha=0.85))

        # ---- 右端标签：两条线末端打名称标签，颜色与线一致 ----
        xlim = ax.get_xlim()
        if xlim[1] > xlim[0]:
            ax.set_xlim(xlim[0], xlim[1] + (xlim[1] - xlim[0]) * 0.14)
        if len(daily) > 0:
            for col, clr, txt in [(col_u, self.UNHEDGED_COLOR, '买现货'),
                                  (col_h, '#c0392b', 'Long Call(+C)')]:
                s = daily[col].dropna()
                if len(s) == 0:
                    continue
                ax.annotate(txt, xy=(s.index[-1], s.iloc[-1]), xytext=(6, 0),
                            textcoords='offset points', color=clr, fontsize=8,
                            fontweight='bold', va='center', ha='left',
                            bbox=dict(boxstyle='round,pad=0.18', facecolor='white',
                                      edgecolor=clr, linewidth=0.5, alpha=0.85),
                            zorder=10)

        fig.autofmt_xdate(rotation=45, ha='right')
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    def gen_chart10_theta(self, df):
        return self._gen_metric_chart(
            df, 'theta_cost_pct_of_premium', '时间衰减成本占权利金比例 (%)',
            chart_num=10, title_prefix='图10：时间损耗速度 — 买方最大的隐性支出',
            ref_lines=[(100.0, '#c0392b', '--', '100%（时间价值全部损耗）')])

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
        stats = {
            'date_start': trade_dates[0] if trade_dates else 'N/A',
            'date_end': trade_dates[-1] if trade_dates else 'N/A',
            'n_days': len(trade_dates),
            'n_rows': len(df),
            'n_contracts': df['ts_code'].nunique(),
            'latest_date': latest_date,
            'n_contracts_latest': len(latest),
            'spot': float(latest['spot_price'].iloc[0]) if len(latest) else np.nan,
            'iv_mean': latest['implied_vol'].mean() if len(latest) else np.nan,
            'iv_rank_mean': latest['iv_rank'].mean() if len(latest) else np.nan,
            'cost_mean': latest['premium_ratio_pct'].mean() if len(latest) else np.nan,
            'ann_cost_mean': latest['annualized_premium_cost_pct'].mean() if len(latest) else np.nan,
            'lev_mean': latest['capital_leverage'].mean() if len(latest) else np.nan,
            'dlev_mean': latest['delta_leverage'].mean() if len(latest) else np.nan,
            'breakeven_mean': latest['breakeven_required_upside_pct'].mean() if len(latest) else np.nan,
            'itm_mean': latest['itm_prob'].mean() if len(latest) else np.nan,
            'capture_mean': latest['upside_capture'].mean() if len(latest) else np.nan,
            'days_min': int(latest['days_to_maturity'].min()) if len(latest) else np.nan,
            'signal_counts': latest['trade_signal'].value_counts().to_dict() if len(latest) else {},
        }
        return stats

    def _build_latest_table_data(self, latest, label_map):
        """最新交易日核心指标总览表数据"""
        col_h = 'scenario_pnl_1_10K_pct'
        col_u = 'unhedged_pnl_1_10K_pct'
        rows = []
        for _, r in latest.sort_values('exercise_price').iterrows():
            name = label_map.get(r['ts_code'], r['ts_code'])
            if len(name) > 14:
                name = name[:13] + '…'
            rows.append([
                name,
                self._fmt(r['exercise_price'], '{:.4g}'),
                self._fmt(r['premium'], '{:.4g}'),
                self._fmt(r['implied_vol'] * 100 if pd.notna(r.get('implied_vol')) else np.nan, '{:.1f}'),
                self._fmt(r.get('iv_rank'), '{:.2f}'),
                self._fmt(r.get('premium_ratio_pct'), '{:.2f}'),
                self._fmt(r.get('annualized_premium_cost_pct'), '{:.1f}'),
                self._fmt(r.get('breakeven_required_upside_pct'), '{:+.2f}'),
                self._fmt(r.get('itm_prob'), '{:.2f}'),
                self._fmt(r.get('capital_leverage'), '{:.1f}'),
                self._fmt(r.get('delta_leverage'), '{:.1f}'),
                self._fmt(r.get('theta_cost_pct_of_premium'), '{:.1f}'),
                self._fmt(r.get(col_h), '{:+.1f}'),
                self._fmt(r.get(col_u), '{:+.2f}'),
                str(r.get('trade_signal', '')),
            ])
        header = ['合约名称', '行权价K', '权利金C', 'IV%', 'IV分位',
                  '成本占比%', '年化成本%', '回本涨幅%', '实值概率',
                  '资金杠杆', '弹性杠杆', 'Theta损耗%',
                  '1.10K买方收益%', '1.10K现货%', '信号']
        return header, rows

    def _build_trader_commentary(self, df, stats):
        """资深交易员综合点评（基于数据自动生成，含具体数字）"""
        latest_date, latest = self._latest_snapshot(df)
        label_map = self._build_label_map(df)
        paras = []

        # ---- 1. 波动率环境（买方视角，与备兑相反） ----
        iv_r = stats['iv_rank_mean']
        iv_m = stats['iv_mean']
        if pd.notna(iv_r):
            if iv_r <= 0.35:
                env_txt = (f"当前 IV 处于近60日 {iv_r*100:.0f}% 的低分位（均值 {iv_m*100:.1f}%），"
                           f"权利金定价偏便宜——这是买方布局牛市的舒适窗口，"
                           f"应优先买入近月低 IV 合约放大杠杆。")
            elif iv_r <= 0.50:
                env_txt = (f"当前 IV 处于近60日 {iv_r*100:.0f}% 的中低位水平（均值 {iv_m*100:.1f}%），"
                           f"权利金公允，可按计划正常建仓买购。")
            elif iv_r <= 0.80:
                env_txt = (f"当前 IV 处于近60日 {iv_r*100:.0f}% 的偏高水平（均值 {iv_m*100:.1f}%），"
                           f"权利金偏贵——买方性价比下降，建议降低仓位或等待 IV 回落再进场。")
            else:
                env_txt = (f"当前 IV 高至近60日 {iv_r*100:.0f}% 分位（均值 {iv_m*100:.1f}%），"
                           f"高位买波是大忌。此时买 Call 是在最贵的时候买保险，"
                           f"除非有极强的短线方向判断，否则建议等待 IV 回落或改用牛市价差压缩成本。")
            paras.append(('波动率环境判断（买方视角）', env_txt))

        # ---- 2. 买方成本评估 ----
        c_m = stats['cost_mean']
        ac_m = stats['ann_cost_mean']
        theta_m = latest['theta_cost_pct_of_premium'].mean() if len(latest) else np.nan
        if pd.notna(c_m):
            paras.append(('买方成本评估',
                          f"最新交易日平均权利金成本 C/S0 = {c_m:.2f}%，"
                          f"年化 {ac_m:.1f}%（按滚动续买口径），"
                          f"平均时间损耗占权利金 {theta_m:.0f}%。"
                          f"年化成本即'持有到期的门票价格'——若标的区间震荡不涨，"
                          f"这笔成本将持续流失；只有方向性行情才能覆盖它。"))

        # ---- 3. 最优买购合约推荐 ----
        cand = latest[latest['delta_leverage'].notna()]
        if len(cand) > 0:
            best = cand.loc[cand['delta_leverage'].idxmax()]
            name = label_map.get(best['ts_code'], best['ts_code'])
            paras.append(('最优买购合约（弹性杠杆维度）',
                          f"{name}：行权价 K={best['exercise_price']:.4g}、权利金 C={best['premium']:.4g}、"
                          f"资金杠杆 {best['capital_leverage']:.1f}x、"
                          f"弹性杠杆 {best['delta_leverage']:.1f}（现货涨1%买方赚{best['delta_leverage']:.1f}%），"
                          f"回本所需涨幅 {best['breakeven_required_upside_pct']:+.2f}%，"
                          f"到期实值概率≈{self._fmt(best.get('itm_prob'), '{:.2f}')}，"
                          f"IV分位 {self._fmt(best.get('iv_rank'), '{:.2f}')}，"
                          f"信号：{best.get('trade_signal', 'N/A')}。"
                          f"注意弹性杠杆越高通常虚值程度越深，双刃剑：涨得猛赚得多，不涨亏得也快。"))

        # ---- 4. 上行杠杆效果（1.10K 情景） ----
        col_h, col_u = 'scenario_pnl_1_10K', 'unhedged_pnl_1_10K'
        if col_h in latest.columns and col_u in latest.columns:
            h_m, u_m = latest[col_h].mean(), latest[col_u].mean()
            capture = stats['capture_mean']
            if pd.notna(h_m) and pd.notna(u_m) and u_m > 0:
                paras.append(('上行杠杆效果（1.10K 情景）',
                              f"若标的上涨约 10%（S_T=1.10K），买现货平均盈利 {u_m:+.4g} 元/单位，"
                              f"买Call平均盈利 {h_m:+.4g} 元/单位，平均上行捕获率 {capture:.2f}"
                              f"（>1=杠杆跑赢现货）。"
                              f"买方资金收益率见总览表'1.10K买方收益%'列——分母是权利金C而非S0，"
                              f"这是买方高弹性的来源，也是亏损放大的根源。"))

        # ---- 5. 下行风险对照（0.95K 情景） ----
        col_h95, col_u95 = 'scenario_pnl_0_95K', 'unhedged_pnl_0_95K'
        if col_h95 in latest.columns and col_u95 in latest.columns:
            h_m, u_m = latest[col_h95].mean(), latest[col_u95].mean()
            if pd.notna(h_m) and pd.notna(u_m) and u_m < 0:
                paras.append(('下行风险对照（0.95K 情景）',
                              f"若标的下跌约 5%（S_T=0.95K），买现货平均亏损 {u_m:+.4g} 元/单位，"
                              f"买Call平均亏损 {h_m:+.4g} 元/单位（即权利金全损）。"
                              f"买方亏损严格锁定在权利金以内——这是与现货最大的区别："
                              f"现货深跌亏损无限放大，买购最多亏 C。"))

        # ---- 6. 到期与时间价值风险 ----
        d_min = stats['days_min']
        if pd.notna(d_min):
            if d_min <= 14:
                paras.append(('到期与时间价值风险',
                              f"距最近合约到期仅 {d_min:.0f} 天，theta 衰减进入非线性加速区，"
                              f"时间价值将快速归零——买方应立即移仓远月，切勿持有近月合约'等反转'。"))
            elif d_min <= 30:
                paras.append(('到期与时间价值风险',
                              f"距最近合约到期 {d_min:.0f} 天，应开始规划移仓远月，"
                              f"避免时间价值加速损耗侵蚀本金。"))
            else:
                paras.append(('到期与时间价值风险',
                              f"距最近合约到期 {d_min:.0f} 天，期限结构健康，时间损耗暂缓。"))

        # ---- 7. 深度虚值与彩票合约风险 ----
        d_min_delta = latest['delta'].min() if len(latest) else np.nan
        if pd.notna(d_min_delta) and d_min_delta < 0.10:
            paras.append(('深度虚值与彩票合约风险',
                          f"存在 delta 低至 {d_min_delta:.2f} 的深度虚值合约——"
                          f"到期实值概率不足 10%，本质是彩票：杠杆极高但胜率极低。"
                          f"资金管理上单笔权利金占总资金比例应严格控制（建议 <1%），"
                          f"避免'便宜'幻觉下的重仓归零。"))

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
        label_map = self._build_label_map(df)

        report_date = datetime.now().strftime('%Y-%m-%d %H:%M')
        now_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        symbol_filter = config.get('symbol_filter')
        call_put = config.get('call_put', 'C')
        name = config.get('name', 'Long Call')

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
            f"LongCallStrategy_{filter_tag}_{date_tag}_{now_ts}.pdf")

        doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4),
                                rightMargin=40, leftMargin=40, topMargin=36, bottomMargin=28)
        page_width = landscape(A4)[0] - 80
        story = []

        # ===== 封面 =====
        story.append(Spacer(1, 1.4 * inch))
        story.append(Paragraph('牛市买购策略分析报告', styles['title']))
        story.append(Paragraph('Long Call (Bull) Strategy Analysis Report',
                               ParagraphStyle('Sub', parent=styles['normal'], alignment=1,
                                              fontSize=11, fontName=self.reportlab_font,
                                              textColor=colors.HexColor('#888888'))))
        story.append(Spacer(1, 0.35 * inch))

        contract_names = sorted(set(label_map.values()))
        names_display = '、'.join(contract_names[:40])
        if len(contract_names) > 40:
            names_display += f" 等 {len(contract_names)} 个合约"

        cover_text = (
            f"策略：Long Call 牛市买购（买入认购期权，单腿买方）<br/>"
            f"数据区间：{stats['date_start']} — {stats['date_end']}（{stats['n_days']} 个交易日）<br/>"
            f"报告生成时间：{report_date}<br/>"
            f"分析时间戳：{analysis_time_str}（算法版本 {analysis_version}）<br/>"
            f"合约过滤：symbol LIKE '{symbol_filter or '无'}' | 方向：{call_put}<br/>"
            f"数据记录：{stats['n_rows']} 条 | 合约数量：{stats['n_contracts']}<br/>"
            f"合约名称：{names_display or '无'}<br/>"
            f"<br/>INFINITY 量化系统 · 期权策略研究"
        )
        story.append(Paragraph(cover_text, styles['cover_info']))
        story.append(PageBreak())

        # ===== 一、数据概览 =====
        story.append(Paragraph('一、数据概览（关键数字）', styles['h1']))
        overview_text = (
            f"本报告基于 {self.TABLE_SOURCE} 表（strategy_type='{self.STRATEGY_TYPE}'）"
            f"{stats['n_rows']} 条记录，覆盖 {stats['date_start']} 至 {stats['date_end']} "
            f"共 {stats['n_days']} 个交易日、{stats['n_contracts']} 个认购合约。<br/>"
            f"最新交易日 {stats['latest_date']}：现货价 {stats['spot']:.4g}，"
            f"IV 均值 {stats['iv_mean']*100:.1f}%（IV 分位均值 {stats['iv_rank_mean']:.2f}），"
            f"平均权利金成本 {stats['cost_mean']:.2f}%（年化 {stats['ann_cost_mean']:.1f}%），"
            f"平均资金杠杆 {stats['lev_mean']:.1f}x（弹性杠杆 {stats['dlev_mean']:.1f}），"
            f"平均回本所需涨幅 {stats['breakeven_mean']:+.2f}%，"
            f"平均到期实值概率≈{stats['itm_mean']:.2f}，平均上行捕获率 {stats['capture_mean']:.2f}，"
            f"最近到期 {stats['days_min']:.0f} 天。"
        )
        story.append(Paragraph(overview_text, styles['normal']))
        story.append(PageBreak())

        # ===== 二、最新交易日核心指标总览 =====
        story.append(Paragraph(f'二、最新交易日（{latest_date}）核心指标总览', styles['h1']))
        header, rows = self._build_latest_table_data(latest, label_map)
        n_cols = len(header)
        name_w = 100
        rest_w = (page_width - name_w - 100) / (n_cols - 2)
        col_widths = [name_w] + [rest_w] * (n_cols - 2) + [62]
        story.append(self._make_table(header, rows, col_widths))
        story.append(Spacer(1, 0.08 * inch))
        story.append(Paragraph(
            '注：成本占比% = C/S0（每一份现货敞口支付的权利金）；年化成本% = C/S0/T×100（滚动续买口径）；'
            '回本涨幅% = (K+C-S0)/S0（到期需涨过K+C才盈利）；实值概率≈delta=N(d1)（到期S_T>K概率）；'
            '资金杠杆 = S0/C（同等敞口资金占用比）；弹性杠杆 = Δ×S0/C（现货涨1%的买方资金收益率%）；'
            'Theta损耗% = |theta|×天数/C（持有到期时间价值损耗比例）；'
            '1.10K买方收益%以权利金C为分母、1.10K现货%以S0为分母——两者口径不同即杠杆来源；'
            '上行捕获率 = 买方盈亏/现货盈亏（1.10K情景，>1=杠杆跑赢现货）；IV分位基于合约近60日IV历史。',
            styles['table_note']))
        story.append(PageBreak())

        # ===== 三~十二、图表（各配数字说明） =====
        chart_sections = []
        if chart_buffers.get('chart1'):
            prem_last = latest['premium'].mean()
            chart_sections.append(('chart1', '图1：现货价格 + Call 权利金',
                                   f"最新现货 {stats['spot']:.4g}，平均权利金 {prem_last:.4g} 元/单位。"
                                   f"权利金随现货上涨而上升（Call 价值与标的相关），"
                                   f"IV 走低时权利金与现货背离——那正是买方进场的黄金窗口。"))
        if chart_buffers.get('chart2'):
            iv_max = latest['implied_vol'].max()
            iv_min = latest['implied_vol'].min()
            chart_sections.append(('chart2', '图2：隐含波动率 IV',
                                   f"最新 IV 区间 {iv_min*100:.1f}% ~ {iv_max*100:.1f}%。"
                                   f"高行权价（虚值）Call 通常 IV 更低——买方博杠杆时倾向虚值合约，"
                                   f"但低成本对应低实值概率，胜率与赔率不可兼得。"))
        if chart_buffers.get('chart3'):
            chart_sections.append(('chart3', '图3：IV 分位数（买方成本温度计）',
                                   f"最新 IV 分位均值 {stats['iv_rank_mean']:.2f}。"
                                   f"低于 0.35（绿线）= 权利金便宜，买方有利；高于 0.80（红线）= 高位买波，"
                                   f"成本最贵，是最差的买方窗口。"))
        if chart_buffers.get('chart4'):
            chart_sections.append(('chart4', '图4：资金杠杆 + 弹性杠杆',
                                   f"最新平均资金杠杆 {stats['lev_mean']:.1f}x，"
                                   f"弹性杠杆 {stats['dlev_mean']:.1f}。资金杠杆衡量'便宜程度'，"
                                   f"弹性杠杆衡量'赚钱速度'——现货涨1%时买方资金收益率即弹性杠杆%。"
                                   f"高于 10x（绿线）为优质买购窗口。"))
        if chart_buffers.get('chart5'):
            chart_sections.append(('chart5', '图5：回本所需涨幅 + 到期实值概率',
                                   f"最新平均回本所需涨幅 {stats['breakeven_mean']:+.2f}%。"
                                   f"虚线（到期实值概率）衡量'涨过K的概率'，实线衡量'涨过K+C的幅度'——"
                                   f"两者组合决定买方的真实胜率：回本涨幅越小于预期涨幅、实值概率越高，买方越占优。"))
        if chart_buffers.get('chart6'):
            chart_sections.append(('chart6', '图6：买方成本 + 年化成本',
                                   f"最新平均权利金成本 {stats['cost_mean']:.2f}%，"
                                   f"年化 {stats['ann_cost_mean']:.1f}%。年化口径反映滚动续买的真实'门票价格'，"
                                   f"是衡量长期持有买方头寸成本压力的黄金标准——高于 10%/年（红线）"
                                   f"意味着震荡市中持续失血。"))
        if chart_buffers.get('chart7'):
            chart_sections.append(('chart7', '图7：经典到期收益结构（厂字形）',
                                   "黑色粗线为平值代表合约的到期收益 max(S_T−K,0)−C，呈教科书厂字形："
                                   "左侧横线为最大亏损平台（权利金C封底，红虚线标注），K 处拐点（橙点线）后"
                                   "以斜率1上行、涨幅无限；绿点为盈亏平衡点 K+C。"
                                   "蓝色虚线为当日含时间价值的 BS 理论价曲线——其与厂字形的差距（淡蓝区域）"
                                   "即时间价值，随到期逐步收敛为厂字形，这正是买方 theta 损耗的可视化。"
                                   "彩色细线为其余行权价合约（淡化背景），行权价越高曲线右移：更便宜但需更大涨幅。"))
        if chart_buffers.get('chart8'):
            chart_sections.append(('chart8', '图8：多情景盈亏对比',
                                   "横轴为情景因子（0.90K~1.20K）。下跌情景下买方线（彩）亏损锁定在权利金，"
                                   f"而现货线（灰）亏损随跌幅线性放大；上涨情景下买方线在涨过K后"
                                   f"与现货线平行但低一个C——凸性优势的完整图景。"))
        if chart_buffers.get('chart9'):
            chart_sections.append(('chart9', '图9：杠杆效果时间序列（1.10K情景）',
                                   "买Call（红）与买现货（灰）的平均盈亏对比随时间变化："
                                   "红色高于灰色即杠杆跑赢现货的区间（绿色阴影）。"
                                   "该差距通常随虚值程度加深而扩大——弹性与胜率的权衡贯穿始终。"))
        if chart_buffers.get('chart10'):
            theta_mean = latest['theta_cost_pct_of_premium'].mean()
            chart_sections.append(('chart10', '图10：时间损耗速度',
                                   f"最新平均时间损耗占权利金 {theta_mean:.0f}%。"
                                   f"对买方而言 theta 是成本而非收入——持有到期时间价值全部流失（100%，红线）。"
                                   f"损耗在最后两周非线性加速，方向判断久不兑现时应果断止损或移仓远月，"
                                   f"切勿与时间赛跑。"))

        for i, (key, title, note) in enumerate(chart_sections):
            section_cn = ['三', '四', '五', '六', '七', '八', '九', '十',
                          '十一', '十二', '十三', '十四'][i] if i < 14 else str(i + 3)
            story.append(Paragraph(f'{section_cn}、{title}', styles['h1']))
            story.append(Spacer(1, 0.08 * inch))
            buf = chart_buffers.get(key)
            if buf is not None:
                # 按图片真实宽高比等比缩放：宽度撑满页面，高度受限于剩余版面，
                # 避免固定 0.42 比例把高图（如图7厂字形）纵向压扁
                img = RLImage(buf)
                w0, h0 = float(img.imageWidth), float(img.imageHeight)
                max_h = 390  # landscape(A4) 可用高度约 530pt，预留标题与说明文字
                scale = min(page_width / w0, max_h / h0)
                img.drawWidth = w0 * scale
                img.drawHeight = h0 * scale
                story.append(img)
            story.append(Spacer(1, 0.06 * inch))
            story.append(Paragraph(note, styles['normal']))
            story.append(PageBreak())

        # ===== 交易信号汇总 =====
        section_cn = '十四'
        story.append(Paragraph(f'{section_cn}、交易信号汇总（最新交易日）', styles['h1']))
        signal_counts = stats['signal_counts']
        sig_rows = [[k, str(v), f"{v / max(len(latest), 1) * 100:.1f}%"]
                    for k, v in sorted(signal_counts.items(), key=lambda x: -x[1])]
        if sig_rows:
            story.append(self._make_table(['信号', '合约数', '占比'], sig_rows,
                                          [150, 100, 100], font_size=9))
            story.append(Spacer(1, 0.12 * inch))
        # 信号明细（代表合约 + 理由）
        detail = latest[latest['trade_signal'].isin(['STRONG_BUY', 'BUY', 'CONSIDER', 'AVOID'])]
        if len(detail) > 0:
            detail = detail.sort_values('trade_signal')
            detail_rows = []
            for _, r in detail.iterrows():
                nm = label_map.get(r['ts_code'], r['ts_code'])
                reason = str(r.get('signal_reason', ''))[:80]
                detail_rows.append([nm[:16], self._fmt(r['exercise_price'], '{:.4g}'),
                                    self._fmt(r.get('capital_leverage'), '{:.1f}'),
                                    self._fmt(r.get('iv_rank'), '{:.2f}'),
                                    str(r['trade_signal']), reason])
            story.append(Paragraph('重点信号明细（含原因）', styles['h2']))
            story.append(self._make_table(
                ['合约名称', '行权价K', '资金杠杆', 'IV分位', '信号', '信号原因'],
                detail_rows, [110, 60, 65, 55, 70, page_width - 360], font_size=6.5))
        story.append(PageBreak())

        # ===== 资深交易员综合点评 =====
        story.append(Paragraph('十五、资深交易员综合点评（自动生成）', styles['h1']))
        commentary = self._build_trader_commentary(df, stats)
        for title, text in commentary:
            story.append(Paragraph(f'{title}', styles['h2']))
            story.append(Paragraph(text, styles['normal']))
            story.append(Spacer(1, 0.10 * inch))
        story.append(PageBreak())

        # ===== 指标口径说明 =====
        story.append(Paragraph('十六、指标口径说明', styles['h1']))
        glossary = (
            "策略定义：买入认购 Call(K)，支付权利金 C（单腿买方，牛市策略）；"
            "到期价值 = max(0, S_T−K) − C，上行无限，下行封底——"
            "到期收益图呈经典厂字形：横线为最大亏损平台（−C），K 处拐点后斜率 1 上行，"
            "盈亏平衡点 = K+C。<br/>"
            "权利金成本 premium_ratio% = C/S0；年化成本 = C/S0/T×100（滚动续买口径）。<br/>"
            "时间损耗 theta_cost% = |theta|×天数/C：持有到期时间价值损耗占权利金比例。<br/>"
            "盈亏平衡点 breakeven = K+C；回本涨幅% = (K+C−S0)/S0：到期需涨过该点才盈利。<br/>"
            "最大亏损 max_loss = C（S_T≤K 时权利金全损），元/张口径乘合约乘数。<br/>"
            "到期实值概率 itm_prob ≈ delta = N(d1)：到期 S_T>K 概率近似。<br/>"
            "资金杠杆 capital_leverage = S0/C：同等敞口下买权与现货的资金占用比。<br/>"
            "弹性杠杆 delta_leverage = Δ×S0/C：现货涨1%时买方资金收益率(%)。<br/>"
            "情景盈亏：S_T=K×factor，买方P&L = max(0,S_T−K)−C；"
            "买方收益率以权利金C为分母，现货对照以S0为分母。<br/>"
            "上行捕获率 upside_capture = 买方盈亏/现货盈亏（1.10K情景）：>1 = 杠杆跑赢现货。<br/>"
            "IV分位 iv_rank：当日 IV 在该合约近 60 日 IV 历史中的分位数（0~1），衡量买方成本贵贱。<br/>"
            "信号规则：STRONG_BUY = 资金杠杆≥15 且 IV分位≤0.35 且 Call 低估；"
            "BUY = 杠杆≥10 且 IV分位≤0.50；CONSIDER = 杠杆≥5；NEUTRAL = 杠杆≥3；其余 AVOID。"
        )
        story.append(Paragraph(glossary, styles['normal']))
        story.append(Spacer(1, 0.15 * inch))

        # ===== 风险提示 =====
        story.append(Paragraph('十七、风险提示', styles['h1']))
        risk_text = (
            "本报告基于历史期权日线数据与 BS 模型理论值进行量化分析，仅供参考，不构成投资建议。<br/>"
            "情景盈亏为到期静态假设（S_T=K×factor），未考虑路径风险、保证金占用与交易成本。<br/>"
            "IV 与 Greeks 为 BS 框架理论值，受流动性、波动率微笑、跳空影响可能与实际偏离。<br/>"
            "买方策略存在时间价值全损风险：标的到期未涨过 K+C 时权利金归零，杠杆放大的不只是收益。<br/>"
            "深度虚值合约到期实值概率极低，重仓买入等同赌博，单笔权利金占比应严格受限。<br/>"
            "ETF 期权存在行权交割与合约调整（除权除息）风险，移仓时需核对合约要素。"
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
        call_put = config.get('call_put', 'C')
        symbol_filter = config.get('symbol_filter')

        self.writeLogInfo(className=self.__class__.__name__,
                          functionName="run",
                          event=f"Generating LongCallStrategyReport: {name}")

        try:
            # Step 1: 拉取数据
            logger.info(f"Step 1/3: 拉取 {self.TABLE_SOURCE} 数据 "
                        f"(symbol_filter={symbol_filter}, call_put={call_put})")
            df = self.fetch_data(start_date=start_date, end_date=end_date,
                                 symbol_filter=symbol_filter, call_put=call_put)
            if df.empty:
                logger.warning("数据为空（请先运行 LongCallStrategyAnalysis 落库），流程终止")
                return None

            # Step 2: 清洗 + 图表
            logger.info("Step 2/3: 数据清洗 & 生成图表")
            df = self.clean_data(df)

            chart_buffers = {}
            chart_buffers['chart1'] = self.gen_chart1_spot_premium(df)
            chart_buffers['chart2'] = self.gen_chart2_iv(df)
            chart_buffers['chart3'] = self.gen_chart3_iv_rank(df)
            chart_buffers['chart4'] = self.gen_chart4_leverage(df)
            chart_buffers['chart5'] = self.gen_chart5_breakeven(df)
            chart_buffers['chart6'] = self.gen_chart6_cost(df)
            chart_buffers['chart7'] = self.gen_chart7_payoff_curve(df)
            chart_buffers['chart8'] = self.gen_chart8_scenario_pnl(df)
            chart_buffers['chart9'] = self.gen_chart9_leverage_effect(df)
            chart_buffers['chart10'] = self.gen_chart10_theta(df)

            chart_count = sum(1 for v in chart_buffers.values() if v is not None)
            logger.info(f"图表生成完成: {chart_count} 张")

            # Step 3: 生成 PDF
            logger.info("Step 3/3: 生成 PDF 报告")
            pdf_path = self._generate_pdf_report(df, chart_buffers, config)

            logger.info("\n" + "=" * 80)
            logger.info("✅ Long Call 牛市买购策略分析报告 生成完成！")
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
    report = LongCallStrategyReport()
    report.run({
        "name": "华夏上证50ETF认购期权（Long Call 牛市买购）",
        "start_date": "20251222",
        "end_date": CommonParameters.today,
        "call_put": "C",
        "symbol_filter": "510050C2612%",
    })

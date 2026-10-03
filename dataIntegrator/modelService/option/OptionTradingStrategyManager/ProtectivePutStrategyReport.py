r"""
Protective Put（保护性认沽）策略 PDF 报告生成器 — 资深交易员/风控视角

数据源：
    tb_option_trading_strategy_protective_put (strategy_type='PROTECTIVE_PUT',
    由 ProtectivePutStrategyAnalysis 写入，含 analysis_time/analysis_params 审计字段)

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


class ProtectivePutStrategyReport:
    """Protective Put 策略 报告生成器"""

    REPORT_DIR = CommonParameters.optionAnalysisReportPath
    TABLE_SOURCE = 'tb_option_trading_strategy_protective_put'
    STRATEGY_TYPE = 'PROTECTIVE_PUT'

    # 情景因子（与分析端 DEFAULT_SCENARIOS 一致）
    SCENARIO_FACTORS = [0.80, 0.85, 0.90, 0.95, 1.00, 1.03, 1.05, 1.10]

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
        """从 tb_option_trading_strategy_protective_put 拉取 PROTECTIVE_PUT 策略分析结果"""
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
            'protected_floor', 'protected_floor_pct_of_spot',
            'max_loss', 'max_loss_cny', 'max_loss_pct_of_spot',
            'protection_per_cost', 'downside_capture',
            'hedge_cost_ratio', 'annualized_hedge_cost_pct',
            'theta_cost_daily', 'theta_cost_total', 'theta_cost_pct_of_premium',
            'breakeven_S_T', 'breakeven_S_T_pct', 'upside_giveup_pct',
            'portfolio_delta', 'residual_exposure_pct',
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
        """图1：现货价(Y1) + 各合约 Put 权利金(Y2)"""
        ts_codes, series_dict = self._prep_series(df, ['spot_price', 'premium'])
        if not ts_codes:
            return None
        label_map = self._build_label_map(df)

        fig, ax1 = plt.subplots(figsize=(20, 8))
        fig.suptitle('图1：标的现货价格 + 各合约 Put 权利金 (premium)',
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
        ax2.set_ylabel('premium (Put 权利金)', fontsize=11)

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
            chart_num=2, title_prefix='图2：各合约 隐含波动率 IV（保险定价的核心输入）')

    def gen_chart3_iv_rank(self, df):
        return self._gen_metric_chart(
            df, 'iv_rank', 'IV 分位数 iv_rank (0~1)',
            chart_num=3, title_prefix='图3：IV 分位数 — 保险贵贱温度计',
            ref_lines=[
                (0.35, '#27ae60', '--', '便宜区间 (<=0.35)'),
                (0.55, '#f39c12', '--', '合理区间'),
                (0.80, '#c0392b', '--', '恐慌定价 (>0.80)'),
            ])

    def gen_chart4_hedge_cost(self, df):
        return self._gen_metric_chart(
            df, 'hedge_cost_ratio', '对冲成本比 P/S0 (%)',
            chart_num=4, title_prefix='图4：对冲成本比(实线) + 年化对冲成本(虚线)',
            y2_col='annualized_hedge_cost_pct', y2_label='年化对冲成本 (%)')

    def gen_chart5_ppc(self, df):
        return self._gen_metric_chart(
            df, 'protection_per_cost', '保险杠杆 protection_per_cost = (K-P)/P',
            chart_num=5, title_prefix='图5：保险杠杆 — 每 1 元保费锁定的下行价值',
            ref_lines=[
                (1.0, '#c0392b', '--', '盈亏平衡线 (=1)'),
                (2.0, '#f39c12', '--', '良好 (=2)'),
                (3.0, '#27ae60', '--', '优秀 (=3)'),
            ])

    def gen_chart6_max_loss_delta(self, df):
        return self._gen_metric_chart(
            df, 'max_loss_pct_of_spot', '对冲后最大亏损占现价 (%)',
            chart_num=6, title_prefix='图6：对冲后最大回撤(实线) + 组合净Delta(虚线)',
            y2_col='portfolio_delta', y2_label='组合净Delta (1+Δput)')

    def gen_chart7_payoff_curve(self, df):
        """图7：到期盈亏曲线（最新交易日）：X=S_T 连续，对冲组合 vs 未对冲"""
        latest_date = df['trade_date'].max()
        df_latest = df[df['trade_date'] == latest_date].dropna(
            subset=['spot_price', 'exercise_price', 'premium'])
        if df_latest.empty:
            return None

        S0 = float(df_latest['spot_price'].iloc[0])
        x = np.linspace(0.75 * S0, 1.25 * S0, 200)
        label_map = self._build_label_map(df)

        fig, ax = plt.subplots(figsize=(20, 10))
        fig.suptitle(f'图7：Protective Put 到期盈亏曲线（{latest_date}）— '
                     f'X轴=到期标的价 S_T，对冲组合(彩线) vs 未对冲(灰虚线)',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        # 未对冲基准
        ax.plot(x, x - S0, color=self.UNHEDGED_COLOR, linewidth=2.5, linestyle='--',
                alpha=0.9, label='未对冲 (仅持有现货)')

        for idx, (_, row) in enumerate(df_latest.iterrows()):
            K, P = float(row['exercise_price']), float(row['premium'])
            y = (x - S0) + np.maximum(K - x, 0) - P
            color = self.CHART_COLORS[idx % len(self.CHART_COLORS)]
            name = label_map.get(row['ts_code'], row['ts_code'])
            ax.plot(x, y, color=color, linewidth=1.2, alpha=0.8, label=name)
            # 右端标签
            ax.annotate(name, xy=(x[-1], y[-1]), xytext=(6, 0),
                        textcoords='offset points', color=color, fontsize=7,
                        fontweight='bold', va='center', ha='left',
                        bbox=dict(boxstyle='round,pad=0.18', facecolor='white',
                                  edgecolor=color, linewidth=0.5, alpha=0.85))

        # 现价 / 零线标注
        ax.axvline(x=S0, color=self.SPOT_COLOR, linewidth=1.2, linestyle=':', alpha=0.8)
        ax.text(S0, ax.get_ylim()[0], f' S0={S0:.3f}', fontsize=8,
                color=self.SPOT_COLOR, va='bottom')
        ax.axhline(y=0, color='gray', linewidth=0.8, linestyle='-', alpha=0.6)

        ax.set_xlabel('到期标的价 S_T', fontsize=12, fontweight='bold')
        ax.set_ylabel('组合盈亏 (元/单位)', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')

        n_items = len(df_latest) + 1
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10), fontsize=6.5,
                  ncol=min(n_items, 8), frameon=True, handlelength=1.2)
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    def gen_chart8_scenario_pnl(self, df):
        """图8：情景盈亏对比（最新交易日）：X=情景因子，对冲 vs 未对冲（元/单位）"""
        latest_date = df['trade_date'].max()
        df_latest = df[df['trade_date'] == latest_date]
        if df_latest.empty:
            return None
        label_map = self._build_label_map(df)

        fig, ax = plt.subplots(figsize=(20, 10))
        fig.suptitle(f'图8：多情景到期盈亏对比（{latest_date}）— X轴=S_T/K 情景因子，'
                     f'对冲组合(彩线) vs 未对冲(灰虚线)',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        factors = self.SCENARIO_FACTORS
        x = np.arange(len(factors))
        xticklabels = [f'{f:.2f}K' for f in factors]

        # 未对冲（取均值，各合约 S0 相同所以等价于任一合约）
        unhedged_vals = [df_latest[f'unhedged_pnl_{f:.2f}'.replace(".", "_") + "K"].mean()
                         for f in factors]
        ax.plot(x, unhedged_vals, color=self.UNHEDGED_COLOR, linewidth=2.5, linestyle='--',
                 marker='D', markersize=6, alpha=0.9, label='未对冲 (仅持有现货)')

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

        # ---- 右端标签：每条线最右端(1.10K)打合约名称，颜色与线一致 ----
        xlim = ax.get_xlim()
        if xlim[1] > xlim[0]:
            ax.set_xlim(xlim[0], xlim[1] + (xlim[1] - xlim[0]) * 0.22)

        ax.annotate('未对冲(现货)', xy=(x[-1], unhedged_vals[-1]), xytext=(6, 0),
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

    def gen_chart9_protection_effect(self, df):
        """图9：0.90K 情景 对冲后 vs 未对冲 平均盈亏时间序列（保护效果演变）"""
        col_h = 'scenario_pnl_0_90K'
        col_u = 'unhedged_pnl_0_90K'
        if col_h not in df.columns or col_u not in df.columns:
            return None

        daily = df.groupby('trade_date_dt')[[col_h, col_u]].mean().dropna(how='all')
        if daily.empty:
            return None

        fig, ax = plt.subplots(figsize=(20, 8))
        fig.suptitle('图9：0.90K 情景（标的下跌约10%）平均盈亏 — 对冲后(红) vs 未对冲(灰)，'
                     '两线差距即保险赔付效果',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        ax.plot(daily.index.tolist(), daily[col_u], color=self.UNHEDGED_COLOR,
                linewidth=2.2, linestyle='--', marker='o', markersize=4,
                label='未对冲平均盈亏')
        ax.plot(daily.index.tolist(), daily[col_h], color='#c0392b',
                linewidth=2.2, marker='s', markersize=4, label='对冲后平均盈亏')
        ax.fill_between(daily.index.tolist(), daily[col_u], daily[col_h],
                        where=(daily[col_h] > daily[col_u]),
                        color='#27ae60', alpha=0.15, label='保险赔付区间')

        ax.axhline(y=0, color='gray', linewidth=0.8, linestyle='-', alpha=0.6)
        ax.set_ylabel('盈亏 (元/单位)', fontsize=12, fontweight='bold')
        ax.set_xlabel('交易日', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12), fontsize=9,
                  ncol=3, frameon=True)

        # 最新数值标注
        if len(daily) > 0:
            ax.annotate(f'最新: 对冲{daily[col_h].iloc[-1]:+.3f} / 未对冲{daily[col_u].iloc[-1]:+.3f}',
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
            for col, clr, txt in [(col_u, self.UNHEDGED_COLOR, '未对冲(现货)'),
                                  (col_h, '#c0392b', '对冲后(现货+Put)')]:
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
            df, 'theta_cost_pct_of_premium', '时间衰减占权利金比例 (%)',
            chart_num=10, title_prefix='图10：时间衰减成本占比 — 保费的每日消耗速度',
            ref_lines=[(100.0, '#c0392b', '--', '100%（保费将全部衰减）')])

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
            'hedge_cost_mean': latest['hedge_cost_ratio'].mean() if len(latest) else np.nan,
            'ann_cost_mean': latest['annualized_hedge_cost_pct'].mean() if len(latest) else np.nan,
            'max_loss_mean': latest['max_loss_pct_of_spot'].mean() if len(latest) else np.nan,
            'ppc_mean': latest['protection_per_cost'].mean() if len(latest) else np.nan,
            'pdelta_mean': latest['portfolio_delta'].mean() if len(latest) else np.nan,
            'days_min': int(latest['days_to_maturity'].min()) if len(latest) else np.nan,
            'signal_counts': latest['trade_signal'].value_counts().to_dict() if len(latest) else {},
        }
        return stats

    def _build_latest_table_data(self, latest, label_map):
        """最新交易日核心指标总览表数据"""
        col_h = 'scenario_pnl_0_90K'
        col_u = 'unhedged_pnl_0_90K'
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
                self._fmt(r.get('protected_floor'), '{:.4g}'),
                self._fmt(r.get('max_loss_pct_of_spot'), '{:+.2f}'),
                self._fmt(r.get('hedge_cost_ratio') * 100 if pd.notna(r.get('hedge_cost_ratio')) else np.nan, '{:.2f}'),
                self._fmt(r.get('annualized_hedge_cost_pct'), '{:.1f}'),
                self._fmt(r.get('protection_per_cost'), '{:.2f}'),
                self._fmt(r.get('breakeven_S_T_pct'), '{:+.2f}'),
                self._fmt(r.get('portfolio_delta'), '{:.3f}'),
                self._fmt(r.get('downside_capture'), '{:.2f}'),
                self._fmt(r.get(col_h), '{:+.4g}') + ' / ' + self._fmt(r.get(col_u), '{:+.4g}'),
                str(r.get('trade_signal', '')),
            ])
        header = ['合约名称', '行权价K', '权利金P', 'IV%', 'IV分位',
                  '价值底K-P', '最大亏损%', '成本比%', '年化成本%',
                  '保险杠杆', '平衡涨幅%', '净Delta', '下跌捕获',
                  '0.90K盈亏(对冲/未对冲)', '信号']
        return header, rows

    def _build_trader_commentary(self, df, stats):
        """资深交易员综合点评（基于数据自动生成，含具体数字）"""
        latest_date, latest = self._latest_snapshot(df)
        label_map = self._build_label_map(df)
        paras = []

        # ---- 1. 波动率环境 ----
        iv_r = stats['iv_rank_mean']
        iv_m = stats['iv_mean']
        if pd.notna(iv_r):
            if iv_r <= 0.35:
                env_txt = (f"当前 IV 处于近60日 {iv_r*100:.0f}% 的低分位（均值 {iv_m*100:.1f}%），"
                           f"保险定价便宜——这是买入保护的舒适窗口，历史经验上应优先锁定长期限保护。")
            elif iv_r <= 0.55:
                env_txt = (f"当前 IV 处于近60日 {iv_r*100:.0f}% 的中位水平（均值 {iv_m*100:.1f}%），"
                           f"保险价格公允，可按计划正常续保。")
            elif iv_r <= 0.80:
                env_txt = (f"当前 IV 已升至近60日 {iv_r*100:.0f}% 分位（均值 {iv_m*100:.1f}%），"
                           f"保险偏贵——若必须对冲，建议降低保护比例或改用领口策略（Collar）对冲成本。")
            else:
                env_txt = (f"当前 IV 高达近60日 {iv_r*100:.0f}% 分位（均值 {iv_m*100:.1f}%），"
                           f"市场处于恐慌定价状态。此时买 Put 是在最贵的时候买保险，"
                           f"除非有明确下行判断，否则建议等待 IV 回落或分批建仓。")
            paras.append(('波动率环境判断', env_txt))

        # ---- 2. 对冲成本 ----
        hc = stats['hedge_cost_mean']
        ac = stats['ann_cost_mean']
        if pd.notna(hc):
            paras.append(('对冲成本评估',
                          f"最新交易日平均对冲成本比 P/S0 = {hc*100:.2f}%，"
                          f"年化对冲成本 {ac:.1f}%（若每月滚动续保）。"
                          f"对照现货长期年化收益，年化保护成本超过 {ac:.0f}% 时，"
                          f"保护策略将显著侵蚀组合收益，需要严格控制对冲比例。"))

        # ---- 3. 最优保护合约推荐 ----
        cand = latest[latest['protection_per_cost'].notna()]
        if len(cand) > 0:
            best = cand.loc[cand['protection_per_cost'].idxmax()]
            name = label_map.get(best['ts_code'], best['ts_code'])
            paras.append(('最优保护合约（保险杠杆维度）',
                          f"{name}：行权价 K={best['exercise_price']:.4g}、权利金 P={best['premium']:.4g}、"
                          f"保险杠杆 (K-P)/P = {best['protection_per_cost']:.2f}"
                          f"（每 1 元保费锁定 {best['protection_per_cost']:.1f} 元下行价值），"
                          f"最大亏损占现价 {best['max_loss_pct_of_spot']:+.2f}%，"
                          f"IV分位 {self._fmt(best.get('iv_rank'), '{:.2f}')}，"
                          f"信号：{best.get('trade_signal', 'N/A')}。"
                          f"交易信号明细可见下方汇总表。"))

        # ---- 4. 下行保护效果（0.90K 情景） ----
        col_h, col_u = 'scenario_pnl_0_90K', 'unhedged_pnl_0_90K'
        if col_h in latest.columns and col_u in latest.columns:
            h_m, u_m = latest[col_h].mean(), latest[col_u].mean()
            if pd.notna(h_m) and pd.notna(u_m) and u_m < 0:
                saved = h_m - u_m
                paras.append(('下行保护效果（0.90K 情景）',
                              f"若标的下跌约 10%（S_T=0.90K），未对冲平均亏损 {u_m:+.4g} 元/单位，"
                              f"对冲后平均亏损收窄至 {h_m:+.4g} 元/单位，"
                              f"保险赔付 {saved:+.4g} 元/单位，平均下跌捕获率 "
                              f"{latest['downside_capture'].mean():.2f}"
                              f"（0=完全保护，1=无保护）。"))

        # ---- 5. 到期与展期风险 ----
        d_min = stats['days_min']
        if pd.notna(d_min):
            if d_min <= 10:
                paras.append(('到期与展期风险',
                              f"距最近合约到期仅 {d_min:.0f} 天，临近到期 Gamma 风险放大、"
                              f"时间衰减加速（年化成本指标将急剧恶化），建议立即展期至远月合约。"))
            elif d_min <= 30:
                paras.append(('到期与展期风险',
                              f"距最近合约到期 {d_min:.0f} 天，应开始规划展期，"
                              f"避免到期前流动性萎缩导致平仓成本上升。"))
            else:
                paras.append(('到期与展期风险',
                              f"距最近合约到期 {d_min:.0f} 天，期限结构健康，暂无展期压力。"))

        # ---- 6. 残余敞口 ----
        pd_mean = stats['pdelta_mean']
        if pd.notna(pd_mean):
            paras.append(('对冲后残余敞口',
                          f"组合平均净 Delta = {pd_mean:.3f}（剩余方向性敞口 {pd_mean*100:.1f}%）。"
                          f"注意：Put 的 Delta 随价格下跌而增大（趋近-1），下跌越深保护越足；"
                          f"但上涨时 Delta 趋近 0，组合几乎完全恢复现货敞口——这正是 Protective Put 的 asymmetric 特性。"))

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
        call_put = config.get('call_put', 'P')
        name = config.get('name', 'Protective Put')

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
            f"ProtectivePutStrategy_{filter_tag}_{date_tag}_{now_ts}.pdf")

        doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4),
                                rightMargin=40, leftMargin=40, topMargin=36, bottomMargin=28)
        page_width = landscape(A4)[0] - 80
        story = []

        # ===== 封面 =====
        story.append(Spacer(1, 1.4 * inch))
        story.append(Paragraph('保护性认沽策略分析报告', styles['title']))
        story.append(Paragraph('Protective Put Strategy Analysis Report',
                               ParagraphStyle('Sub', parent=styles['normal'], alignment=1,
                                              fontSize=11, fontName=self.reportlab_font,
                                              textColor=colors.HexColor('#888888'))))
        story.append(Spacer(1, 0.35 * inch))

        contract_names = sorted(set(label_map.values()))
        names_display = '、'.join(contract_names[:40])
        if len(contract_names) > 40:
            names_display += f" 等 {len(contract_names)} 个合约"

        cover_text = (
            f"策略：Protective Put（持有现货 + 买入认沽）<br/>"
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
            f"共 {stats['n_days']} 个交易日、{stats['n_contracts']} 个认沽合约。<br/>"
            f"最新交易日 {stats['latest_date']}：现货价 {stats['spot']:.4g}，"
            f"IV 均值 {stats['iv_mean']*100:.1f}%（IV 分位均值 {stats['iv_rank_mean']:.2f}），"
            f"平均对冲成本比 {stats['hedge_cost_mean']*100:.2f}%（年化 {stats['ann_cost_mean']:.1f}%），"
            f"对冲后平均最大亏损 {stats['max_loss_mean']:+.2f}%（未对冲跌停风险为 -100%），"
            f"平均保险杠杆 {stats['ppc_mean']:.2f}，组合平均净 Delta {stats['pdelta_mean']:.3f}，"
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
            '注：最大亏损% = (K-P-S0)/S0（对冲后最大回撤）；成本比% = P/S0；保险杠杆 = (K-P)/P；'
            '平衡涨幅% = P/S0（上行需涨过 S0+P 组合才盈利）；净Delta = 1+Δput（残余方向敞口）；'
            '下跌捕获 = 0.90K情景对冲后亏损/未对冲亏损（0=完全保护）；IV分位基于合约近60日IV历史。',
            styles['table_note']))
        story.append(PageBreak())

        # ===== 三~十二、图表（各配数字说明） =====
        chart_sections = []
        if chart_buffers.get('chart1'):
            prem_last = latest['premium'].mean()
            chart_sections.append(('chart1', '图1：现货价格 + Put 权利金',
                                   f"最新现货 {stats['spot']:.4g}，平均权利金 {prem_last:.4g} 元/单位。"
                                   f"权利金随现货下跌而上升（Put 价值与标的负相关），观察两者背离可判断保护成本的日内变化。"))
        if chart_buffers.get('chart2'):
            iv_max = latest['implied_vol'].max()
            iv_min = latest['implied_vol'].min()
            chart_sections.append(('chart2', '图2：隐含波动率 IV',
                                   f"最新 IV 区间 {iv_min*100:.1f}% ~ {iv_max*100:.1f}%。"
                                   f"低行权价（深 OTM）Put 通常 IV 更高——恐慌偏斜（Skew），"
                                   f"是保护成本高的结构性原因。"))
        if chart_buffers.get('chart3'):
            chart_sections.append(('chart3', '图3：IV 分位数（保险贵贱温度计）',
                                   f"最新 IV 分位均值 {stats['iv_rank_mean']:.2f}。"
                                   f"低于 0.35（绿线）= 保险便宜；高于 0.80（红线）= 恐慌定价，"
                                   f"此时应考虑推迟建仓或用 Collar 压缩成本。"))
        if chart_buffers.get('chart4'):
            chart_sections.append(('chart4', '图4：对冲成本比 + 年化对冲成本',
                                   f"最新平均成本比 {stats['hedge_cost_mean']*100:.2f}%，"
                                   f"年化 {stats['ann_cost_mean']:.1f}%。年化口径反映滚动续保的真实成本，"
                                   f"若年化成本超过组合预期收益，保护策略得不偿失。"))
        if chart_buffers.get('chart5'):
            ppc_max = latest['protection_per_cost'].max()
            chart_sections.append(('chart5', '图5：保险杠杆 (K-P)/P',
                                   f"最新平均保险杠杆 {stats['ppc_mean']:.2f}，最高 {ppc_max:.2f}。"
                                   f"高于 2（黄线）为良好，高于 3（绿线）为优秀；低于 1（红线）意味着保费相对保护过贵。"))
        if chart_buffers.get('chart6'):
            ml_best = latest['max_loss_pct_of_spot'].max()
            chart_sections.append(('chart6', '图6：对冲后最大回撤 + 组合净Delta',
                                   f"最新平均最大亏损 {stats['max_loss_mean']:+.2f}%（最好合约 {ml_best:+.2f}%）。"
                                   f"净Delta越接近0对冲越充分，但注意 Delta 的动态性——上涨时敞口会自动恢复。"))
        if chart_buffers.get('chart7'):
            be_mean = latest['breakeven_S_T_pct'].mean()
            chart_sections.append(('chart7', '图7：到期盈亏曲线',
                                   f"彩线为对冲组合、灰虚线为未对冲。对冲曲线左侧被价值底 K-P 托底（水平段），"
                                   f"右侧与未对冲平行但低一个权利金 P。平均盈亏平衡涨幅 {be_mean:+.2f}%。"))
        if chart_buffers.get('chart8'):
            chart_sections.append(('chart8', '图8：多情景盈亏对比',
                                   "横轴为情景因子（0.80K~1.10K）。下跌情景下对冲线（彩）明显高于未对冲线（灰），"
                                   "两者差距即保险赔付；上涨情景下对冲线仅低一个权利金——这就是'付保费买底价'的结构。"))
        if chart_buffers.get('chart9'):
            chart_sections.append(('chart9', '图9：保护效果时间序列（0.90K情景）',
                                   "对冲后（红）与未对冲（灰）的平均盈亏差距随时间变化：差距收窄通常意味着"
                                   "IV 下降或时间衰减侵蚀了 Put 价值，需要评估是否补充保护。"))
        if chart_buffers.get('chart10'):
            theta_mean = latest['theta_cost_pct_of_premium'].mean()
            chart_sections.append(('chart10', '图10：时间衰减成本占比',
                                   f"最新平均时间衰减占权利金 {theta_mean:.1f}%。"
                                   f"接近或超过 100% 意味着持有到期保费将全部耗尽——对保护策略这是预期内的'保费消耗'，"
                                   f"但应避免在到期前一周内建仓（衰减非线性加速）。"))

        for i, (key, title, note) in enumerate(chart_sections):
            section_cn = ['三', '四', '五', '六', '七', '八', '九', '十',
                          '十一', '十二', '十三', '十四'][i] if i < 14 else str(i + 3)
            story.append(Paragraph(f'{section_cn}、{title}', styles['h1']))
            story.append(Spacer(1, 0.08 * inch))
            buf = chart_buffers.get(key)
            if buf is not None:
                story.append(RLImage(buf, width=page_width, height=page_width * 0.42))
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
        # 信号明细（非 NEUTRAL/AVOID 的代表合约 + 理由）
        detail = latest[latest['trade_signal'].isin(['STRONG_BUY', 'BUY', 'CONSIDER', 'AVOID'])]
        if len(detail) > 0:
            detail = detail.sort_values('trade_signal')
            detail_rows = []
            for _, r in detail.iterrows():
                nm = label_map.get(r['ts_code'], r['ts_code'])
                reason = str(r.get('signal_reason', ''))[:80]
                detail_rows.append([nm[:16], self._fmt(r['exercise_price'], '{:.4g}'),
                                    self._fmt(r.get('protection_per_cost'), '{:.2f}'),
                                    self._fmt(r.get('iv_rank'), '{:.2f}'),
                                    str(r['trade_signal']), reason])
            story.append(Paragraph('重点信号明细（含原因）', styles['h2']))
            story.append(self._make_table(
                ['合约名称', '行权价K', '保险杠杆', 'IV分位', '信号', '信号原因'],
                detail_rows, [110, 60, 60, 55, 70, page_width - 355], font_size=6.5))
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
            "策略定义：持有现货 S0 + 买入认沽 Put(K)，支付权利金 P；"
            "到期组合价值 = S_T + max(0, K−S_T)，恒不低于 K（价值硬底）。<br/>"
            "价值底 protected_floor = K−P：组合到期最小价值。<br/>"
            "最大亏损 max_loss = K−P−S0；最大亏损% = (K−P−S0)/S0，即对冲后最大回撤。<br/>"
            "保险杠杆 protection_per_cost = (K−P)/P：每 1 元保费锁定的下行价值，越高保险性价比越好。<br/>"
            "对冲成本比 hedge_cost_ratio = P/S0；年化对冲成本 = P/S0/T×100（T 为年化期限，滚动续保口径）。<br/>"
            "盈亏平衡点 breakeven_S_T = S0+P：上行需涨过此点组合才盈利；平衡涨幅% = P/S0。<br/>"
            "下跌捕获 downside_capture：0.90K 情景对冲后亏损 ÷ 未对冲亏损，0=完全保护，1=无保护。<br/>"
            "组合净Delta portfolio_delta = 1+Δput：对冲后残余方向性敞口。<br/>"
            "IV分位 iv_rank：当日 IV 在该合约近 60 日 IV 历史中的分位数（0~1），衡量保险贵贱。<br/>"
            "信号规则：STRONG_BUY = 保险杠杆≥3 且 IV分位≤0.35 且 Put 低估；"
            "BUY = 杠杆≥2 且 IV分位≤0.55；CONSIDER = 杠杆≥1.5；NEUTRAL = 杠杆≥1.0；其余 AVOID。"
        )
        story.append(Paragraph(glossary, styles['normal']))
        story.append(Spacer(1, 0.15 * inch))

        # ===== 风险提示 =====
        story.append(Paragraph('十七、风险提示', styles['h1']))
        risk_text = (
            "本报告基于历史期权日线数据与 BS 模型理论值进行量化分析，仅供参考，不构成投资建议。<br/>"
            "情景盈亏为到期静态假设（S_T=K×factor），未考虑路径风险、保证金占用与交易成本。<br/>"
            "IV 与 Greeks 为 BS 框架理论值，受流动性、波动率微笑、跳空影响可能与实际偏离。<br/>"
            "ETF 期权存在行权交割与合约调整（除权除息）风险，展期时需核对合约要素。<br/>"
            "保护策略的最大亏损仍为 K−P−S0（非零），极端行情下保险并不能完全消除损失。"
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
                          event=f"Generating ProtectivePutStrategyReport: {name}")

        try:
            # Step 1: 拉取数据
            logger.info(f"Step 1/3: 拉取 {self.TABLE_SOURCE} 数据 "
                        f"(symbol_filter={symbol_filter}, call_put={call_put})")
            df = self.fetch_data(start_date=start_date, end_date=end_date,
                                 symbol_filter=symbol_filter, call_put=call_put)
            if df.empty:
                logger.warning("数据为空（请先运行 ProtectivePutStrategyAnalysis 落库），流程终止")
                return None

            # Step 2: 清洗 + 图表
            logger.info("Step 2/3: 数据清洗 & 生成图表")
            df = self.clean_data(df)

            chart_buffers = {}
            chart_buffers['chart1'] = self.gen_chart1_spot_premium(df)
            chart_buffers['chart2'] = self.gen_chart2_iv(df)
            chart_buffers['chart3'] = self.gen_chart3_iv_rank(df)
            chart_buffers['chart4'] = self.gen_chart4_hedge_cost(df)
            chart_buffers['chart5'] = self.gen_chart5_ppc(df)
            chart_buffers['chart6'] = self.gen_chart6_max_loss_delta(df)
            chart_buffers['chart7'] = self.gen_chart7_payoff_curve(df)
            chart_buffers['chart8'] = self.gen_chart8_scenario_pnl(df)
            chart_buffers['chart9'] = self.gen_chart9_protection_effect(df)
            chart_buffers['chart10'] = self.gen_chart10_theta(df)

            chart_count = sum(1 for v in chart_buffers.values() if v is not None)
            logger.info(f"图表生成完成: {chart_count} 张")

            # Step 3: 生成 PDF
            logger.info("Step 3/3: 生成 PDF 报告")
            pdf_path = self._generate_pdf_report(df, chart_buffers, config)

            logger.info("\n" + "=" * 80)
            logger.info("✅ Protective Put 策略分析报告 生成完成！")
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
    report = ProtectivePutStrategyReport()
    report.run({
        "name": "华夏上证50ETF认沽期权（Protective Put）",
        "start_date": "20251222",
        "end_date": CommonParameters.today,
        "call_put": "P",
        "symbol_filter": "510050P2612%",
    })

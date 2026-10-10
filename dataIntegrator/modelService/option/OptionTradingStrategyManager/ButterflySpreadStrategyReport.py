r"""
Butterfly Spread（蝴蝶价差）策略 PDF 报告生成器 — 资深交易员/风控视角

数据源：
    tb_option_trading_strategy_butterfly_spread (strategy_type='BUTTERFLY_SPREAD',
    由 ButterflySpreadStrategyAnalysis 写入，含 analysis_time/analysis_params 审计字段)

报告结构：
    封面 → 数据概览(数字) → 最新交易日组合总览(表格, 按评分排名) → 10张图表(各配数字说明)
    → 交易信号汇总(表格) → 资深交易员综合点评(自动生成, 含数字) → 指标口径 → 风险提示

核心图表：
    图6 教科书山形（尖顶）到期收益结构图（三条腿 + 组合）——
    两侧最大亏损平台 L=-D、峰值 P=min(翼宽)-D @K2、双盈亏平衡点 B1=K1+D / B2=K3-D

蝴蝶特点（报告端口径）：
    非方向性（赚盘整）、净 Theta 为正（时间有利）、净 Vega 为负（做空波动率）、
    胜率为区间概率 P(B1＜S_T＜B2)（与单边策略不可直接比较）

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
from dataIntegrator.common.ReportJobLogger import ReportJobLogger
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

logger = CommonLib.logger

# 中文字体支持（matplotlib）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class ButterflySpreadStrategyReport:
    """Butterfly Spread 策略 报告生成器"""

    REPORT_DIR = CommonParameters.optionAnalysisReportPath
    TABLE_SOURCE = 'tb_option_trading_strategy_butterfly_spread'
    STRATEGY_TYPE = 'BUTTERFLY_SPREAD'

    # 情景因子（与分析端 DEFAULT_SCENARIOS 一致，S_T = K2 × factor）
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

    def fetch_data(self, start_date=None, end_date=None, symbol_filter=None, call_put='C'):
        """从 tb_option_trading_strategy_butterfly_spread 拉取 BUTTERFLY_SPREAD 策略分析结果"""
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
        ORDER BY trade_date, exercise_price, exercise_price_short, exercise_price_long2
        """
        logger.info(f"SQL:\n{sql}")
        df = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        logger.info(f"Fetched {len(df)} rows, {len(df.columns)} columns")
        return df

    def clean_data(self, df):
        """类型转换与派生列（combo_key = "K1/K2/K3" 作为组合唯一标识）"""
        numeric_cols = [
            'exercise_price', 'exercise_price_short', 'exercise_price_long2',
            'opt_multiplier', 'spot_price',
            'premium', 'premium_short', 'premium_long2',
            'implied_vol', 'implied_vol_short', 'implied_vol_long2',
            'iv_rank', 'iv_rank_short', 'iv_rank_long2',
            'delta', 'gamma', 'theta', 'vega',
            'delta_short', 'gamma_short', 'theta_short', 'vega_short',
            'delta_long2', 'gamma_long2', 'theta_long2', 'vega_long2',
            'bs_theoretical_price', 'bs_theoretical_price_short', 'bs_theoretical_price_long2',
            'close_vs_theoretical', 'close_vs_theoretical_pct',
            'close_vs_theoretical_short', 'close_vs_theoretical_pct_short',
            'close_vs_theoretical_long2', 'close_vs_theoretical_pct_long2',
            'net_delta', 'net_gamma', 'net_theta', 'net_vega',
            'wing_low', 'wing_high', 'wing_min', 'spread_width', 'spread_width_pct',
            'asymmetry_pct',
            'net_debit', 'net_debit_cny', 'net_debit_pct_of_spot', 'net_debit_pct_of_width',
            'max_profit', 'max_profit_cny', 'max_profit_pct_of_spot', 'roi_max_pct',
            'max_loss', 'max_loss_cny', 'max_loss_pct_of_spot', 'reward_risk_ratio',
            'breakeven_S_T', 'breakeven_upside_pct',
            'breakeven_S_T_high', 'breakeven_high_pct', 'profit_zone_width',
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

        # 组合唯一标识："K1/K2/K3"（如 "2.85/2.90/2.95"）
        df['combo_key'] = (df['exercise_price'].map(lambda v: f'{v:.4g}') + '/'
                           + df['exercise_price_short'].map(lambda v: f'{v:.4g}') + '/'
                           + df['exercise_price_long2'].map(lambda v: f'{v:.4g}'))

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
        fig.suptitle('图1：标的现货价格 + 各蝴蝶组合净支出 D = C1-2*C2+C3',
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
        """图2：中间腿（卖出×2）隐含波动率 — 蝴蝶成本的核心输入"""
        return self._gen_metric_chart(
            df, 'implied_vol_short', '中间腿(卖出x2)隐含波动率 (implied_vol, 小数)',
            chart_num=2, title_prefix='图2：中间腿 隐含波动率 IV（卖 2 张收权利金，越贵建仓越有利）')

    def gen_chart3_capital_efficiency(self, df):
        return self._gen_metric_chart(
            df, 'net_debit_pct_of_width', '净支出占总宽 D/(K3-K1) (%)',
            chart_num=3, title_prefix='图3：资本效率 — 净支出占蝴蝶总宽比例（越低越优）',
            ref_lines=[
                (25.0, '#27ae60', '--', '优质 (<=25%)'),
                (35.0, '#f39c12', '--', '中性 (=35%)'),
                (50.0, '#c0392b', '--', '低效 (>=50%)'),
            ])

    def gen_chart4_roi_winprob(self, df):
        return self._gen_metric_chart(
            df, 'roi_max_pct', '峰值资金收益率 max_profit/D (%)',
            chart_num=4, title_prefix='图4：峰值资金收益率(实线) + 区间胜率(虚线)',
            y2_col='win_prob', y2_label='区间胜率 P(B1 < S_T < B2)',
            ref_lines=[
                (25.0, '#27ae60', '--', '优质 (=25%)'),
                (100.0, '#3498db', '--', '高杠杆 (=100%)'),
            ])

    def gen_chart5_reward_risk(self, df):
        return self._gen_metric_chart(
            df, 'reward_risk_ratio', '回报风险比 max_profit/D',
            chart_num=5, title_prefix='图5：回报风险比 — 峰值盈利/最大亏损',
            ref_lines=[
                (1.0, '#c0392b', '--', '盈亏平衡 (=1.0)'),
                (1.5, '#f39c12', '--', '可接受 (=1.5)'),
                (2.0, '#27ae60', '--', '优质 (=2.0)'),
            ])

    def gen_chart6_payoff_textbook(self, df):
        """图6：教科书山形到期收益结构（最新交易日评分最优组合）★核心图表

        买入腿1: max(S_T-K1,0) - C1 (蓝虚线, 低翼)
        卖出腿: 2*(C2 - max(S_T-K2,0)) (橙虚线, 身体x2)
        买入腿2: max(S_T-K3,0) - C3 (紫虚线, 高翼)
        组合: 三腿相加 (红实线加粗, 山形尖顶)
        标注: L=-D 两侧最大亏损平台 / P=min(翼宽)-D 峰值@K2 /
              双盈亏平衡点 B1=K1+D、B2=K3-D（蝴蝶独有）
        """
        latest_date, best = self._best_combo_latest(df)
        if best is None:
            return None

        K1 = float(best['exercise_price'])
        K2 = float(best['exercise_price_short'])
        K3 = float(best['exercise_price_long2'])
        C1 = float(best['premium'])
        C2 = float(best['premium_short'])
        C3 = float(best['premium_long2'])
        S0 = float(best['spot_price'])
        D = C1 - 2.0 * C2 + C3
        wing_min = min(K2 - K1, K3 - K2)
        peak = wing_min - D
        B1, B2 = K1 + D, K3 - D
        combo_name = best['combo_key']

        x = np.linspace(min(0.85 * S0, K1 * 0.90), max(1.30 * S0, K3 * 1.15), 400)

        payoff_leg1 = np.maximum(x - K1, 0) - C1              # 买入腿1（低翼）
        payoff_mid = 2.0 * (C2 - np.maximum(x - K2, 0))      # 卖出腿（身体×2）
        payoff_leg3 = np.maximum(x - K3, 0) - C3              # 买入腿2（高翼）
        payoff_combo = payoff_leg1 + payoff_mid + payoff_leg3  # 组合（红实线，山形）

        fig, ax = plt.subplots(figsize=(20, 10))
        fig.suptitle(f'图6：Butterfly Spread 教科书山形到期收益结构 — 组合 {combo_name}'
                     f'（评分最优，{latest_date}）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        # ---- 盈亏区间着色（山形：中间盈利、两侧亏损） ----
        ax.fill_between(x, payoff_combo, 0, where=(payoff_combo > 0), color='#27ae60',
                        alpha=0.10, label='盈利区间 (B1 < S_T < B2)')
        ax.fill_between(x, payoff_combo, 0, where=(payoff_combo <= 0), color='#c0392b',
                        alpha=0.10, label='亏损区间 (突破两侧翅膀)')

        # ---- 四条线：三条腿（虚线）+ 组合（红实线加粗山形） ----
        ax.plot(x, payoff_leg1, color='#3498db', linewidth=1.4, linestyle='--',
                alpha=0.8, label=f'买入腿1 Call(K1={K1:.4g}): max(S_T-K1,0)-C1')
        ax.plot(x, payoff_mid, color='#f39c12', linewidth=1.4, linestyle='--',
                alpha=0.8, label=f'卖出腿x2 Call(K2={K2:.4g}): 2*(C2-max(S_T-K2,0))')
        ax.plot(x, payoff_leg3, color='#9b59b6', linewidth=1.4, linestyle='--',
                alpha=0.8, label=f'买入腿2 Call(K3={K3:.4g}): max(S_T-K3,0)-C3')
        ax.plot(x, payoff_combo, color='#c0392b', linewidth=3.2, zorder=9,
                label='组合: max(0,S_T-K1)-2*max(0,S_T-K2)+max(0,S_T-K3)-D')

        # ---- 关键标注：两侧最大亏损平台 L ----
        ax.axhline(y=-D, color='#c0392b', linewidth=1.4, linestyle='--', alpha=0.9, zorder=6)
        ax.text(x[0], -D, f' 最大亏损 L = -D = {D:.4g}\n (S_T<=K1 或 S_T>=K3, 两侧亏损封底)',
                fontsize=9.5, color='#c0392b', va='top', fontweight='bold')

        # ---- 山形峰值 @K2 ----
        ax.axhline(y=peak, color='#27ae60', linewidth=1.4, linestyle='--', alpha=0.9, zorder=6)
        ax.plot([K2], [peak], marker='*', markersize=18, color='#27ae60', zorder=12)
        ax.text(K2, peak, f' 峰值 P = min(翼宽)-D = {peak:.4g}\n (S_T=K2 时, 盘整即赚)',
                fontsize=9.5, color='#27ae60', va='bottom', ha='center', fontweight='bold')

        # ---- 行权价竖线 K1/K2/K3 ----
        ax.axvline(x=K1, color='#3498db', linewidth=1.4, linestyle=':', alpha=0.9, zorder=6)
        ax.text(K1, 0.02, f' K1={K1:.4g}\n (低翼拐点)',
                transform=ax.get_xaxis_transform(), fontsize=9, color='#3498db',
                va='bottom', fontweight='bold')
        ax.axvline(x=K2, color='#f39c12', linewidth=1.4, linestyle=':', alpha=0.9, zorder=6)
        ax.text(K2, 0.02, f' K2={K2:.4g}\n (身体拐点/峰值)',
                transform=ax.get_xaxis_transform(), fontsize=9, color='#f39c12',
                va='bottom', fontweight='bold')
        ax.axvline(x=K3, color='#9b59b6', linewidth=1.4, linestyle=':', alpha=0.9, zorder=6)
        ax.text(K3, 0.02, f' K3={K3:.4g}\n (高翼拐点)',
                transform=ax.get_xaxis_transform(), fontsize=9, color='#9b59b6',
                va='bottom', fontweight='bold')

        # ---- 双盈亏平衡点 B1/B2（蝴蝶独有） ----
        ax.plot([B1], [0], marker='o', markersize=10, color='#27ae60', zorder=11)
        ax.plot([B2], [0], marker='o', markersize=10, color='#27ae60', zorder=11)
        ax.annotate(f'下平衡点 B1 = K1+D = {B1:.4g}\n（跌破开始亏损）',
                    xy=(B1, 0), xytext=(-80, -52), textcoords='offset points',
                    fontsize=10, fontweight='bold', color='#27ae60', ha='left',
                    arrowprops=dict(arrowstyle='->', color='#27ae60', linewidth=1.2),
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                              edgecolor='#27ae60', alpha=0.9), zorder=12)
        ax.annotate(f'上平衡点 B2 = K3-D = {B2:.4g}\n（涨过开始亏损）',
                    xy=(B2, 0), xytext=(16, -52), textcoords='offset points',
                    fontsize=10, fontweight='bold', color='#27ae60', ha='right',
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
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10), fontsize=8.5,
                  ncol=2, frameon=True, handlelength=1.8)
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
                marker='o', markersize=7, label=f'蝴蝶组合 {best["combo_key"]}')

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
                               (combo_vals, '#c0392b', f'蝴蝶{best["combo_key"]}')]:
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
        """图8：组合有效前沿散点（最新交易日）：X=区间胜率，Y=峰值收益率，颜色=回报风险比"""
        latest_date = df['trade_date'].max()
        latest = df[df['trade_date'] == latest_date].dropna(
            subset=['win_prob', 'roi_max_pct'])
        if latest.empty:
            return None

        fig, ax = plt.subplots(figsize=(20, 10))
        fig.suptitle(f'图8：组合有效前沿（{latest_date}）— X=区间胜率, Y=峰值资金收益率, '
                     f'颜色=回报风险比（窄蝴蝶高胜率低峰值 vs 宽蝴蝶低胜率高峰值）',
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
                        xytext=(7, 7), textcoords='offset points', fontsize=7,
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
        ax.set_xlabel('区间胜率 P(B1 < S_T < B2)（delta1-delta3 近似）',
                      fontsize=12, fontweight='bold')
        ax.set_ylabel('峰值资金收益率 max_profit/D (%)', fontsize=12, fontweight='bold')
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
        """图10：净 Theta（正值=时间有利）+ 净 Vega（负值=做空波动率）— 蝴蝶独有结构优势"""
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
            df_top, 'net_theta', '净Theta (元/单位/日, 正值=时间衰减有利)',
            chart_num=10, title_prefix='图10：净Theta(实线, 蝴蝶为正=时间帮你) + '
                                      '净Vega(虚线, 为负=做空波动率)',
            y2_col='net_vega', y2_label='净Vega (负值=做空波动率)')

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
            'iv_mean': latest['implied_vol_short'].mean() if len(latest) else np.nan,
            'iv_rank_mean': latest['iv_rank_short'].mean() if len(latest) else np.nan,
            'net_debit_mean': latest['net_debit'].mean() if len(latest) else np.nan,
            'roi_mean': latest['roi_max_pct'].mean() if len(latest) else np.nan,
            'rr_mean': latest['reward_risk_ratio'].mean() if len(latest) else np.nan,
            'wp_mean': latest['win_prob'].mean() if len(latest) else np.nan,
            'be_zone_mean': latest['profit_zone_width'].mean() if len(latest) else np.nan,
            'asym_mean': latest['asymmetry_pct'].mean() if len(latest) else np.nan,
            'net_theta_mean': latest['net_theta'].mean() if len(latest) else np.nan,
            'net_vega_mean': latest['net_vega'].mean() if len(latest) else np.nan,
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
                self._fmt(r['exercise_price_long2'], '{:.4g}'),
                self._fmt(r['net_debit'], '{:.4g}'),
                self._fmt(r.get('spread_width_pct'), '{:.2f}'),
                self._fmt(r.get('asymmetry_pct'), '{:.1f}'),
                self._fmt(r.get('max_profit'), '{:.4g}'),
                self._fmt(r.get('roi_max_pct'), '{:.1f}'),
                self._fmt(r.get('win_prob'), '{:.2f}'),
                self._fmt(r.get('reward_risk_ratio'), '{:.2f}'),
                self._fmt(r.get('breakeven_upside_pct'), '{:+.2f}'),
                self._fmt(r.get('breakeven_high_pct'), '{:+.2f}'),
                self._fmt(r.get('net_theta'), '{:.5f}'),
                self._fmt(r.get('score'), '{:.3f}'),
                str(int(r.get('combo_rank', 0))) if pd.notna(r.get('combo_rank')) else 'N/A',
                str(r.get('trade_signal', '')),
            ])
        header = ['组合 K1/K2/K3', 'K1', 'K2', 'K3', '净支出D', '总宽%',
                  '不对称%', '峰值盈利', 'ROI%', '区间胜率', '回报风险比',
                  '下平衡%', '上平衡%', '净Theta', '评分', '排名', '信号']
        return header, rows

    def _build_trader_commentary(self, df, stats):
        """资深交易员综合点评（基于数据自动生成，含具体数字）"""
        latest_date, latest = self._latest_snapshot(df)
        paras = []

        # ---- 1. 波动率环境（做空波动率视角：与价差相反） ----
        iv_r = stats['iv_rank_mean']
        iv_m = stats['iv_mean']
        if pd.notna(iv_r):
            if iv_r >= 0.65:
                env_txt = (f"中间腿（卖出×2）IV 处于近60日 {iv_r*100:.0f}% 的高分位"
                           f"（均值 {iv_m*100:.1f}%）。蝴蝶净 Vega 为负——IV 高企时建仓，"
                           f"卖 2 张中间腿收得贵、两翼买得相对便宜，"
                           f"若到期前 IV 回落，组合还能额外赚到 Vega 收敛的钱。"
                           f"这是做空波动率策略的舒适窗口。")
            elif iv_r >= 0.35:
                env_txt = (f"中间腿 IV 处于近60日 {iv_r*100:.0f}% 的中性区间（均值 {iv_m*100:.1f}%），"
                           f"权利金定价公允，蝴蝶的盈亏主要由到期时 S_T 是否钉在 K2 决定，"
                           f"而非波动率收敛。")
            else:
                env_txt = (f"中间腿 IV 低至近60日 {iv_r*100:.0f}% 分位（均值 {iv_m*100:.1f}%），"
                           f"卖出收不了几个钱、蝴蝶建仓成本占比高，做空波动率的赔率不足。"
                           f"低 IV 环境更适合做买方（单腿或价差），等 IV 回升再考虑蝴蝶。")
            paras.append(('波动率环境判断（做空波动率视角）', env_txt))

        # ---- 2. 最优组合推荐 ----
        best = stats['best']
        if best is not None:
            paras.append(('最优组合推荐（综合评分第一）',
                          f"组合 {best['combo_key']}（买 Call(K1={best['exercise_price']:.4g}) + "
                          f"卖 2×Call(K2={best['exercise_price_short']:.4g}) + "
                          f"买 Call(K3={best['exercise_price_long2']:.4g})）："
                          f"净支出 D={best['net_debit']:.4g}（占现价 "
                          f"{self._fmt(best.get('net_debit_pct_of_spot'), '{:.2f}')}%），"
                          f"峰值盈利 {best['max_profit']:.4g} 元/单位"
                          f"（资金收益率 {self._fmt(best.get('roi_max_pct'), '{:.1f}')}%，S_T=K2 时取得），"
                          f"最大亏损即净支出 {best['max_loss']:.4g} 元/单位（两侧封底），"
                          f"盈利区间 [{best['breakeven_S_T']:.4g}, "
                          f"{best['breakeven_S_T_high']:.4g}]"
                          f"（区间胜率≈{self._fmt(best.get('win_prob'), '{:.2f}')}），"
                          f"不对称度 {self._fmt(best.get('asymmetry_pct'), '{:.1f}')}%。"
                          f"信号：{best.get('trade_signal', 'N/A')}。"))

        # ---- 3. 宽度选择评估（窄vs宽权衡） ----
        if len(latest.dropna(subset=['spread_width_pct', 'roi_max_pct'])) >= 2:
            cand = latest.dropna(subset=['spread_width_pct', 'roi_max_pct', 'win_prob'])
            narrow = cand.loc[cand['spread_width_pct'].idxmin()]
            wide = cand.loc[cand['spread_width_pct'].idxmax()]
            paras.append(('宽度选择评估（胜率-赔率权衡）',
                          f"最窄组合 {narrow['combo_key']}（总宽 {narrow['spread_width_pct']:.2f}%）："
                          f"区间胜率 {narrow['win_prob']:.2f}、峰值 ROI {narrow['roi_max_pct']:.1f}%——"
                          f"高胜率低峰值，适合'窄幅盘整'判断；"
                          f"最宽组合 {wide['combo_key']}（总宽 {wide['spread_width_pct']:.2f}%）："
                          f"区间胜率 {wide['win_prob']:.2f}、峰值 ROI {wide['roi_max_pct']:.1f}%——"
                          f"低胜率高峰值，适合'宽幅震荡'判断。"
                          f"蝴蝶没有单一最优宽度：窄蝴蝶赚概率、宽蝴蝶赚空间，"
                          f"应结合对震荡幅度的判断自选（见图8有效前沿）。"))

        # ---- 4. Greeks 结构优势（蝴蝶独有：时间站在你这边） ----
        nt = stats['net_theta_mean']
        nv = stats['net_vega_mean']
        if pd.notna(nt):
            if nt > 0:
                paras.append(('时间价值与波动率敞口（蝴蝶独有优势）',
                              f"组合平均净 Theta = +{nt:.5f} 元/单位/日——正值！"
                              f"这与所有买方策略（单腿/牛市价差/保护认沽）相反："
                              f"卖 2 张中间腿收的时间价值超过买两翼的损耗，"
                              f"每持有一天，时间都在帮你把对手的 theta 收进口袋。"
                              f"净 Vega = {nv:.5f}（负值=做空波动率）："
                              f"IV 回落获利、IV 飙升受伤（见图10）。"
                              f"结构解读：蝴蝶 = 卖出跨式的'保险版'——"
                              f"用两翼封住了裸卖跨式的尾部无限风险。"))
            else:
                paras.append(('时间价值与波动率敞口（注意）',
                              f"组合平均净 Theta = {nt:.5f} 元/单位/日（非正值），"
                              f"两翼损耗超过中间腿收入——通常意味着中间腿定价偏低或翼距过宽，"
                              f"该结构的时间优势未兑现，建议对比其他候选组合。"))

        # ---- 5. 盈亏平衡区间与胜率 ----
        bz = stats['be_zone_mean']
        wp = stats['wp_mean']
        if pd.notna(bz) and pd.notna(wp):
            paras.append(('盈亏平衡区间与区间胜率',
                          f"最新组合平均盈利区间宽度 {bz:.4g}（B2-B1），平均区间胜率 {wp:.2f}。"
                          f"解读：到期 S_T 落在 (B1, B2) 区间内即盈利、越靠近 K2 赚越多，"
                          f"突破两侧翅膀则亏损封底于 D。"
                          f"注意区间胜率为 delta1-delta3 的风险中性概率近似，"
                          f"数值天然低于单边策略的胜率，两者不可直接比较；"
                          f"且区间内盈利是渐变的（0 到峰值），评分的期望值已按此折算。"))

        # ---- 6. 到期与展期风险 ----
        d_min = stats['days_min']
        if pd.notna(d_min):
            if d_min <= 10:
                paras.append(('到期与展期风险',
                              f"距到期仅 {d_min:.0f} 天，临近到期三腿价格剧烈分化，"
                              f"且蝴蝶峰值恰在到期日才完全成形（时间价值归零才钉住 K2），"
                              f"Gamma 风险集中于最后几天，建议立即展期至次月合约。"))
            elif d_min <= 30:
                paras.append(('到期与展期风险',
                              f"距到期 {d_min:.0f} 天，应开始规划展期，"
                              f"避免到期前三腿流动性萎缩导致平仓成本上升。"))
            else:
                paras.append(('到期与展期风险',
                              f"距到期 {d_min:.0f} 天，期限结构健康，暂无展期压力。"
                              f"蝴蝶的净 theta 优势随到期临近而增强，持有期本身即收益来源。"))

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
        call_put = config.get('call_put', 'C')

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
            f"ButterflySpreadStrategy_{filter_tag}_{date_tag}_{now_ts}.pdf")

        doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4),
                                rightMargin=40, leftMargin=40, topMargin=36, bottomMargin=28)
        page_width = landscape(A4)[0] - 80
        story = []

        # ===== 封面 =====
        story.append(Spacer(1, 1.4 * inch))
        story.append(Paragraph('蝴蝶价差策略分析报告', styles['title']))
        story.append(Paragraph('Butterfly Spread Strategy Analysis Report',
                               ParagraphStyle('Sub', parent=styles['normal'], alignment=1,
                                              fontSize=11, fontName=self.reportlab_font,
                                              textColor=colors.HexColor('#888888'))))
        story.append(Spacer(1, 0.35 * inch))

        combo_names = sorted(set(df['combo_key'].dropna()))
        names_display = '、'.join(combo_names[:40])
        if len(combo_names) > 40:
            names_display += f" 等 {len(combo_names)} 个组合"

        cover_text = (
            f"策略：Butterfly Spread（买 Call(K1) + 卖 2×Call(K2) + 买 Call(K3)，K1＜K2＜K3）<br/>"
            f"特点：非方向性盘整策略 — 山形收益、双盈亏平衡点、净Theta为正、净Vega为负<br/>"
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
            f"共 {stats['n_days']} 个交易日、{stats['n_combos']} 个候选蝴蝶组合"
            f"（配对规则：中间腿 K2 = ATM 档，两翼各 1~3 档，不对称度≤25%）。<br/>"
            f"最新交易日 {stats['latest_date']}：现货价 {stats['spot']:.4g}，"
            f"{stats['n_combos_latest']} 个候选组合，中间腿 IV 均值 {stats['iv_mean']*100:.1f}%"
            f"（IV 分位均值 {stats['iv_rank_mean']:.2f}），"
            f"平均净支出 {stats['net_debit_mean']:.4g} 元/单位，"
            f"平均峰值资金收益率 {stats['roi_mean']:.1f}%，"
            f"平均回报风险比 {stats['rr_mean']:.2f}，平均区间胜率 {stats['wp_mean']:.2f}，"
            f"平均盈利区间宽度 {stats['be_zone_mean']:.4g}，"
            f"平均不对称度 {stats['asym_mean']:.1f}%，"
            f"平均净 Theta {stats['net_theta_mean']:+.5f}（正=时间有利），"
            f"最近到期 {stats['days_min']:.0f} 天。"
        )
        story.append(Paragraph(overview_text, styles['normal']))
        story.append(PageBreak())

        # ===== 二、最新交易日组合总览 =====
        story.append(Paragraph(f'二、最新交易日（{latest_date}）候选组合总览（按评分排名）',
                               styles['h1']))
        header, rows = self._build_latest_table_data(latest)
        n_cols = len(header)
        name_w = 105
        rest_w = (page_width - name_w - 62) / (n_cols - 2)
        col_widths = [name_w] + [rest_w] * (n_cols - 2) + [62]
        story.append(self._make_table(header, rows, col_widths))
        story.append(Spacer(1, 0.08 * inch))
        story.append(Paragraph(
            '注：净支出D = C1−2×C2+C3（也是最大亏损）；总宽% = (K3−K1)/S0；'
            '不对称% = |(K2−K1)−(K3−K2)|/(K3−K1)×100（0=教科书等宽）；'
            '峰值盈利 = min(翼宽)−D（S_T=K2 时取得）；'
            'ROI% = 峰值盈利/D（以净支出为本金）；'
            '区间胜率≈P(B1＜S_T＜B2)=delta1−delta3（两翼delta差，风险中性近似）；'
            '下平衡% = (K1+D−S0)/S0、上平衡% = (K3−D−S0)/S0（落在两者之间即盈利）；'
            '净Theta = θ1−2×θ2+θ3（正值=时间衰减有利，蝴蝶独有）；'
            '评分 = 期望值/净支出 = [胜率×峰值盈利−(1−胜率)×D]/D；排名按同日评分降序（1=最优）。',
            styles['table_note']))
        story.append(PageBreak())

        # ===== 三~十二、图表（各配数字说明） =====
        chart_sections = []
        if chart_buffers.get('chart1'):
            chart_sections.append(('chart1', '图1：现货价格 + 各组合净支出',
                                   f"最新现货 {stats['spot']:.4g}，平均净支出 "
                                   f"{stats['net_debit_mean']:.4g} 元/单位（最大亏损即此值）。"
                                   f"净支出越低代表中间腿收的权利金越多、两翼买得越便宜——"
                                   f"同样翅膀的蝴蝶，净支出越低性价比越高。"))
        if chart_buffers.get('chart2'):
            iv_min = latest['implied_vol_short'].min()
            iv_max = latest['implied_vol_short'].max()
            chart_sections.append(('chart2', '图2：中间腿（卖出×2）隐含波动率 IV',
                                   f"最新中间腿 IV 区间 {iv_min*100:.1f}% ~ {iv_max*100:.1f}%。"
                                   f"蝴蝶净 Vega 为负：IV 越高建仓时卖 2 张收得越贵（有利），"
                                   f"持有期 IV 回落还能额外获利——与买方策略对 IV 的偏好方向相反。"))
        if chart_buffers.get('chart3'):
            ce_mean = latest['net_debit_pct_of_width'].mean()
            chart_sections.append(('chart3', '图3：资本效率（净支出占总宽）',
                                   f"最新平均净支出占总宽 {ce_mean:.1f}%。"
                                   f"该值越低，同样的峰值空间占用资金越少；"
                                   f"教科书等宽蝴蝶该值通常在 10%~30%（时间价值撑起的结构），"
                                   f">=50%（红线）说明翅膀几乎全靠权利金支出撑起，性价比差。"))
        if chart_buffers.get('chart4'):
            chart_sections.append(('chart4', '图4：峰值资金收益率 + 区间胜率',
                                   f"最新平均峰值资金收益率 {stats['roi_mean']:.1f}%（以净支出为本金）。"
                                   f"注意区间胜率（虚线）天然低于单边策略（盈利区间窄），"
                                   f"两者乘积的期望才是真实收益预期（见评分）。"
                                   f"ROI 与胜率同样呈反向关系：宽蝴蝶 ROI 高但区间胜率低。"))
        if chart_buffers.get('chart5'):
            chart_sections.append(('chart5', '图5：回报风险比',
                                   f"最新平均回报风险比 {stats['rr_mean']:.2f}。"
                                   f"红线 1.0 为盈亏比临界，绿线 2.0 以上为优质建仓窗口——"
                                   f"蝴蝶因净支出极低，该比值经常远高于价差类策略。"))
        if chart_buffers.get('chart6'):
            best = stats['best']
            if best is not None:
                note = (f"红色实线为组合到期收益（教科书山形/尖顶）："
                        f"两侧横线为最大亏损平台 L=−D={-best['net_debit']:.4g}"
                        f"（S_T≤K1 或 S_T≥K3，突破两侧翅膀即亏损封底），"
                        f"峰值 P={best['max_profit']:.4g} 于 S_T=K2 时取得"
                        f"（绿色星标，盘整即赚）；山形与零轴的两个交点为双盈亏平衡点"
                        f" B1={best['breakeven_S_T']:.4g}、B2={best['breakeven_S_T_high']:.4g}"
                        f"——蝴蝶独有结构（单边价差只有一个平衡点）。"
                        f"蓝/橙/紫虚线为三条腿：卖 2×中间腿（橙）削掉两翼（蓝/紫）的尾部敞口，"
                        f"把无限方向的赌博压缩为钉在 K2 的盘整判断。")
            else:
                note = "红实线为组合到期收益：两侧亏损封底 −D、中间峰值 min(翼宽)−D。"
            chart_sections.append(('chart6', '图6：教科书山形到期收益结构（评分最优组合）', note))
        if chart_buffers.get('chart7'):
            chart_sections.append(('chart7', '图7：多情景到期盈亏（最优组合 vs 买现货）',
                                   "横轴为情景因子（0.85×K2~1.15×K2）。蝴蝶线（红）在 K2 附近"
                                   "达到峰值、两侧亏损封底；买现货线（灰虚线）线性无界。"
                                   "小幅波动情景下蝴蝶的资金收益率远超现货（本金只有净支出 D）；"
                                   "大涨大跌情景下锁定亏 D——这是用方向敞口换盘整收益的代价。"))
        if chart_buffers.get('chart8'):
            chart_sections.append(('chart8', '图8：组合有效前沿（区间胜率 vs 峰值ROI）',
                                   "每个点为一个候选组合（标注 K1/K2/K3），颜色为回报风险比，"
                                   "红星为评分最优。左上角=低区间胜率高峰值（宽蝴蝶），"
                                   "右下角=高区间胜率低峰值（窄蝴蝶）。没有绝对最优——"
                                   "按你对震荡幅度的判断在前沿上自选：预期窄幅盘整选右下，"
                                   "预期宽幅震荡选左上。"))
        if chart_buffers.get('chart9'):
            chart_sections.append(('chart9', '图9：Top5 组合评分演变',
                                   "评分 = 期望值/净支出，综合了区间胜率×峰值赔率的期望与资金效率。"
                                   "评分持续为正且稳定的组合是滚动建仓的候选；"
                                   "评分跳水通常意味着现货偏离 K2 导致 delta 结构剧变"
                                   "（蝴蝶的峰值中心失效）。"))
        if chart_buffers.get('chart10'):
            chart_sections.append(('chart10', '图10：净 Theta / 净 Vega（蝴蝶独有结构）',
                                   f"最新平均净 Theta = {stats['net_theta_mean']:+.5f} 元/单位/日"
                                   f"——正值！时间站在持有者一边（卖 2×中间腿收的 theta 超过买两翼的损耗），"
                                   f"这与单腿/价差买方策略完全相反。"
                                   f"净 Vega（虚线）为负 = 做空波动率：IV 回落获利、IV 飙升受伤。"
                                   f"结构解读：蝴蝶 = 卖出跨式 + 两翼保险，"
                                   f"把'方向+波动+时间'三维博弈压缩为接近纯盘整博弈。"))

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
                                    self._fmt(r['exercise_price_long2'], '{:.4g}'),
                                    self._fmt(r.get('score'), '{:.3f}'),
                                    str(r['trade_signal']), reason])
            story.append(Paragraph('重点信号明细（含原因）', styles['h2']))
            story.append(self._make_table(
                ['组合 K1/K2/K3', 'K1', 'K2', 'K3', '评分', '信号', '信号原因'],
                detail_rows, [105, 50, 50, 50, 50, 65, page_width - 370], font_size=6.5))
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
            "策略定义：买入认购 Call(K1) + 卖出 2 张认购 Call(K2) + 买入认购 Call(K3)，"
            "K1＜K2＜K3 同到期月，K2 居中（不对称度≤25%）；"
            "净支出 D = C1−2×C2+C3；到期组合收益 = max(0,S_T−K1) − 2×max(0,S_T−K2) "
            "+ max(0,S_T−K3) − D，呈教科书山形（尖顶）。<br/>"
            "非方向性：与 bull/bear 价差的本质差异——蝴蝶赚'盘整'（S_T 钉在 K2 附近），"
            "两侧突破都亏；净 Delta≈0（方向中性）。<br/>"
            "最大亏损 max_loss = D（S_T≤K1 或 S_T≥K3 时，两侧平台亏损封底）；"
            "最大盈利 max_profit = min(K2−K1, K3−K2)−D（S_T=K2 时，非对称取窄翼）。<br/>"
            "双盈亏平衡点：B1 = K1+D（下平衡）、B2 = K3−D（上平衡），"
            "盈利区间 (B1, B2)——蝴蝶独有，单边价差只有一个平衡点。<br/>"
            "区间胜率 win_prob ≈ P(B1＜S_T＜B2) = delta1−delta3（call delta≈P(S_T＞K)，"
            "风险中性概率近似）：数值天然低于单边策略胜率，两者不可直接比较；"
            "且区间内盈利从 0 渐变到峰值，评分期望值按峰值线性近似（偏保守解读）。<br/>"
            "期望值 expected_value = 胜率×max_profit − (1−胜率)×D；"
            "评分 score = 期望值/D（风险调整后收益，同日排名依据）。<br/>"
            "净 Greeks（持仓 1−2+1）：net_delta = Δ1−2Δ2+Δ3（≈0，方向中性）；"
            "net_theta = θ1−2θ2+θ3（正值=时间衰减有利，与所有买方策略相反——"
            "卖 2 张中间腿收的时间价值超过买两翼的损耗）；"
            "net_vega = vega1−2vega2+vega3（负值=做空波动率，IV 回落获利）。<br/>"
            "对称性 asymmetry_pct = |(K2−K1)−(K3−K2)|/(K3−K1)×100：0=教科书等宽蝴蝶，"
            "越低越接近理论峰值结构。<br/>"
            "组合配对：中间腿 K2 = ATM 档（峰值对准现价），两翼各 1~3 档，"
            "不对称度≤25%——约束剪枝控制组合爆炸，每日最多 9 个候选全量落库。<br/>"
            "信号规则：STRONG_BUY = 回报风险比≥2 且 区间胜率≥0.30 且 峰值ROI≥25%；"
            "BUY = 回报风险比≥1.5 且 区间胜率≥0.22；CONSIDER = 回报风险比≥1.2；"
            "NEUTRAL = 回报风险比≥1.0；其余 AVOID。"
        )
        story.append(Paragraph(glossary, styles['normal']))
        story.append(Spacer(1, 0.15 * inch))

        # ===== 风险提示 =====
        story.append(Paragraph('十六、风险提示', styles['h1']))
        risk_text = (
            "本报告基于历史期权日线数据与 BS 模型理论值进行量化分析，仅供参考，不构成投资建议。<br/>"
            "情景盈亏为到期静态假设（S_T=K2×factor），未考虑路径风险、保证金占用与交易成本。<br/>"
            "区间胜率为 delta1−delta3 的风险中性概率近似，与真实概率存在系统性偏差"
            "（风险中性≠真实分布），且区间内盈利渐变会高估端点附近收益。<br/>"
            "蝴蝶为盘整市策略：单边趋势行情中两端封亏 D，若标的趋势突破 K3 或跌破 K1，"
            "表现将显著差于方向性持仓——判断错震荡区间就是最大风险。<br/>"
            "卖 2 张中间腿涉及保证金占用（三腿中唯一义务仓），实际资金效率低于名义净支出；"
            "临近到期三腿流动性分化可能导致平仓成本高于理论值。<br/>"
            "ETF 期权为欧式，无提前行权风险，但存在行权交割与合约调整（除权除息）风险，"
            "展期时需核对三腿合约要素。"
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
                          event=f"Generating ButterflySpreadStrategyReport: {name}")

        # 报表任务日志（与 BondYieldComparator 相同的 ReportJobLogger 机制）
        job_logger = ReportJobLogger()
        job_logger.start_job(self.__class__.__name__, 'OptionStrategyReport',
                             params={'report_name': config.get('name'),
                                     'start_date': config.get('start_date'),
                                     'end_date': config.get('end_date'),
                                     'call_put': config.get('call_put'),
                                     'symbol_filter': config.get('symbol_filter')})

        try:
            # Step 1: 拉取数据
            logger.info(f"Step 1/3: 拉取 {self.TABLE_SOURCE} 数据 "
                        f"(symbol_filter={symbol_filter}, call_put={call_put})")
            df = self.fetch_data(start_date=start_date, end_date=end_date,
                                 symbol_filter=symbol_filter, call_put=call_put)
            if df.empty:
                logger.warning("数据为空（请先运行 ButterflySpreadStrategyAnalysis 落库），流程终止")
                job_logger.end_job_success(records_processed=0)
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
            logger.info("✅ Butterfly Spread 策略分析报告 生成完成！")
            logger.info(f"   Report: {pdf_path}")
            logger.info(f"   Data rows: {len(df)}")
            logger.info(f"   Charts: {chart_count} 张")
            logger.info("=" * 80)
            job_logger.end_job_success(records_processed=len(df))

            return pdf_path

        except Exception as e:
            import traceback
            logger.error(f"报告生成失败: {e}")
            logger.error(traceback.format_exc())
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise


if __name__ == "__main__":
    report = ButterflySpreadStrategyReport()
    report.run({
        "name": "华夏上证50ETF认购期权（Butterfly Spread）",
        "start_date": "20251222",
        "end_date": CommonParameters.today,
        "call_put": "C",
        "symbol_filter": "510050C2612%",
    })

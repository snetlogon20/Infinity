r"""
Short Straddle（卖出跨式）策略 PDF 报告生成器 — 资深交易员/风控视角

数据源：
    tb_option_trading_strategy_short_straddle (strategy_type='SHORT_STRADDLE',
    由 ShortStraddleStrategyAnalysis 写入，含 analysis_time/analysis_params 审计字段)

报告结构：
    封面 → 数据概览(数字) → 最新交易日组合总览(表格, 按评分排名) → 10张图表(各配数字说明)
    → 交易信号汇总(表格) → 资深交易员综合点评(自动生成, 含数字) → 指标口径 → 风险提示

核心图表：
    图6 教科书三线到期收益结构图（Λ 形倒V：Call腿/Put腿/组合）——
    顶部最大盈利 T（S_T=K）、双盈亏平衡点 K±T（安全垫）、两侧亏损无上限

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


class ShortStraddleStrategyReport:
    """Short Straddle 策略 报告生成器"""

    REPORT_DIR = CommonParameters.optionAnalysisReportPath
    TABLE_SOURCE = 'tb_option_trading_strategy_short_straddle'
    STRATEGY_TYPE = 'SHORT_STRADDLE'

    # 情景因子（与分析端 DEFAULT_SCENARIOS 一致，S_T = S0 × factor）
    SCENARIO_FACTORS = [0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15]

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

    def fetch_data(self, start_date=None, end_date=None, symbol_filter=None, call_put=None):
        """从 tb_option_trading_strategy_short_straddle 拉取 SHORT_STRADDLE 策略分析结果"""
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
        """类型转换与派生列（combo_key = "K=行权价" 作为组合唯一标识）"""
        numeric_cols = [
            'exercise_price', 'opt_multiplier', 'spot_price',
            'premium', 'premium_put', 'implied_vol', 'implied_vol_put',
            'iv_rank', 'iv_rank_put',
            'delta', 'gamma', 'theta', 'vega',
            'delta_put', 'gamma_put', 'theta_put', 'vega_put',
            'bs_theoretical_price', 'bs_theoretical_price_put',
            'close_vs_theoretical', 'close_vs_theoretical_pct',
            'close_vs_theoretical_put', 'close_vs_theoretical_pct_put',
            'net_delta', 'net_gamma', 'net_theta', 'net_vega',
            'total_premium', 'total_premium_cny', 'total_premium_pct_of_spot',
            'expected_move_1sigma_pct',
            'max_profit', 'max_profit_cny', 'max_profit_pct_of_spot',
            'breakeven_up', 'breakeven_up_pct',
            'breakeven_down', 'breakeven_down_pct', 'breakeven_range_pct',
            'win_prob', 'expected_value', 'score', 'combo_rank',
            'risk_free_rate', 'dividend_yield',
        ] + [f'scenario_pnl_{f:.2f}'.replace('.', '_') + suf
             for f in self.SCENARIO_FACTORS for suf in ('S', 'S_cny', 'S_pct')] \
          + [f'unhedged_pnl_{f:.2f}'.replace('.', '_') + suf
             for f in self.SCENARIO_FACTORS for suf in ('S', 'S_pct')]

        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        if 'days_to_maturity' in df.columns:
            df['days_to_maturity'] = pd.to_numeric(df['days_to_maturity'], errors='coerce').astype('Int64')

        # 组合唯一标识："K=2.95"（跨式双腿同行权价）
        df['combo_key'] = df['exercise_price'].map(lambda v: f'K={v:.4g}')

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

    def gen_chart1_spot_total_premium(self, df):
        """图1：现货价(Y1) + 各组合总收入 T=Y2（最大盈利/安全垫）"""
        combo_keys, series_dict = self._prep_series(df, ['spot_price', 'total_premium'])
        if not combo_keys:
            return None

        fig, ax1 = plt.subplots(figsize=(20, 8))
        fig.suptitle('图1：标的现货价格 + 各跨式组合总收入 T = C+P（最大盈利/安全垫）',
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

        # Y2: total_premium
        ax2 = ax1.twinx()
        for idx, key in enumerate(combo_keys):
            sub = series_dict[key]
            if 'total_premium' in sub.columns and sub['total_premium'].notna().sum() > 0:
                s = sub['total_premium'].dropna()
                color = self.CHART_COLORS[idx % len(self.CHART_COLORS)]
                ax2.plot(s.index.tolist(), s.values, color=color, linewidth=0.9,
                         alpha=0.8, marker='o', markersize=3, label=key)
        ax2.set_ylabel('总收入 T = C+P (元/单位)', fontsize=11)

        xlim = ax2.get_xlim()
        if xlim[1] > xlim[0]:
            ax2.set_xlim(xlim[0], xlim[1] + (xlim[1] - xlim[0]) * 0.14)
        for idx, key in enumerate(combo_keys):
            sub = series_dict[key]
            if 'total_premium' not in sub.columns:
                continue
            s = sub['total_premium'].dropna()
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
            df, 'implied_vol', 'Call腿隐含波动率 (implied_vol, 小数)',
            chart_num=2, title_prefix='图2：Call腿 隐含波动率 IV（跨式收入的核心输入，'
                                     'Put腿与其高度相关）')

    def gen_chart3_safety_margin(self, df):
        return self._gen_metric_chart(
            df, 'breakeven_range_pct', '安全垫区间宽度 2T/S0 (%)',
            chart_num=3, title_prefix='图3：安全垫区间宽度（|涨跌|在此区间内即收租，越宽越安全）',
            ref_lines=[
                (6.0, '#c0392b', '--', '偏薄 (<=6%)'),
                (10.0, '#f39c12', '--', '中性 (=10%)'),
                (14.0, '#27ae60', '--', '厚安全垫 (>=14%)'),
            ])

    def gen_chart4_winprob_ev(self, df):
        return self._gen_metric_chart(
            df, 'win_prob', '胜率 P(|S_T-K|<T)',
            chart_num=4, title_prefix='图4：胜率(实线) + 期望值(虚线) — 大概率小赔率结构',
            y2_col='expected_value', y2_label='期望值 (市价-BS理论)',
            ref_lines=[
                (0.80, '#27ae60', '--', '高胜率 (>=0.80)'),
                (0.60, '#f39c12', '--', '及格线 (=0.60)'),
            ])

    def gen_chart5_expected_move(self, df):
        return self._gen_metric_chart(
            df, 'expected_move_1sigma_pct', '1σ预期波动 σ√T年 (%)',
            chart_num=5, title_prefix='图5：1σ预期波动(实线) + 总收入占现价(虚线) — '
                                      '收入高于1σ波动=贵卖波动率',
            y2_col='total_premium_pct_of_spot', y2_label='总收入/现价 T/S0 (%)',
            ref_lines=[(0.0, '#c0392b', '--', '')])

    def gen_chart6_payoff_textbook(self, df):
        """图6：教科书三线到期收益结构（最新交易日评分最优组合）★核心图表

        Call腿: C - max(S_T-K,0) (蓝虚线)
        Put腿:  P - max(K-S_T,0) (橙虚线)
        组合:   T - |S_T-K| (红实线, 教科书 Λ 形倒V)
        标注:   顶部最大盈利 T (S_T=K) / 双盈亏平衡点 K±T(安全垫边界) / 两侧亏损无上限
        """
        latest_date, best = self._best_combo_latest(df)
        if best is None:
            return None

        K = float(best['exercise_price'])
        C = float(best['premium'])
        P = float(best['premium_put'])
        S0 = float(best['spot_price'])
        T = C + P
        BE_up, BE_dn = K + T, K - T
        combo_name = best['combo_key']

        x = np.linspace(min(0.80 * S0, BE_dn * 0.92), max(1.20 * S0, BE_up * 1.08), 400)

        payoff_call = C - np.maximum(x - K, 0)           # Call 腿（卖出）
        payoff_put = P - np.maximum(K - x, 0)             # Put 腿（卖出）
        payoff_combo = payoff_call + payoff_put            # 组合（红实线 Λ 形）

        fig, ax = plt.subplots(figsize=(20, 10))
        fig.suptitle(f'图6：Short Straddle 教科书到期收益结构 — 组合 {combo_name}'
                     f'（评分最优，{latest_date}）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        # ---- 盈亏区间着色（Λ 形：中间盈利、两侧亏损） ----
        ax.fill_between(x, payoff_combo, 0, where=(payoff_combo > 0), color='#27ae60',
                        alpha=0.10, label='盈利区间 (|S_T-K| < T, 安全垫内)')
        ax.fill_between(x, payoff_combo, 0, where=(payoff_combo <= 0), color='#c0392b',
                        alpha=0.10, label='亏损区间 (|S_T-K| > T, 无下限)')

        # ---- 三条线：Call腿/Put腿（虚线）+ 组合（红实线加粗） ----
        ax.plot(x, payoff_call, color='#3498db', linewidth=1.6, linestyle='--',
                alpha=0.85, label=f'卖Call腿(K={K:.4g})：C−max(S_T−K,0)')
        ax.plot(x, payoff_put, color='#f39c12', linewidth=1.6, linestyle='--',
                alpha=0.85, label=f'卖Put腿(K={K:.4g})：P−max(K−S_T,0)')
        ax.plot(x, payoff_combo, color='#c0392b', linewidth=3.2, zorder=9,
                label='组合：T−|S_T−K|（Λ 形，两侧亏损无上限）')

        # ---- 关键标注：顶部最大盈利平台 T（S_T=K） ----
        ax.axhline(y=T, color='#27ae60', linewidth=1.4, linestyle='--', alpha=0.9, zorder=6)
        ax.annotate(f'顶部最大盈利 = T = C+P = {T:.4g}\n（S_T=K 时双腿同时归零，收租最大化）',
                    xy=(K, T), xytext=(0, 42), textcoords='offset points',
                    fontsize=10, fontweight='bold', color='#27ae60', ha='center',
                    arrowprops=dict(arrowstyle='->', color='#27ae60', linewidth=1.2),
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                              edgecolor='#27ae60', alpha=0.9), zorder=12)

        # ---- 行权价竖线 K（Λ 形顶部拐点） ----
        ax.axvline(x=K, color='#f39c12', linewidth=1.4, linestyle=':', alpha=0.9, zorder=6)
        ax.text(K, 0.02, f' 行权价 K = {K:.4g}\n (Λ形顶部拐点, pin风险区)',
                transform=ax.get_xaxis_transform(), fontsize=9, color='#f39c12',
                va='bottom', fontweight='bold')

        # ---- 双盈亏平衡点 K±T（安全垫边界） ----
        ax.plot([BE_up], [0], marker='o', markersize=10, color='#c0392b', zorder=11)
        ax.annotate(f'上平衡点 = K+T = {BE_up:.4g}\n（涨幅超 {(BE_up - S0) / S0 * 100:+.2f}%'
                    f'即击穿安全垫开始亏损）',
                    xy=(BE_up, 0), xytext=(16, -45), textcoords='offset points',
                    fontsize=10, fontweight='bold', color='#c0392b',
                    arrowprops=dict(arrowstyle='->', color='#c0392b', linewidth=1.2),
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                              edgecolor='#c0392b', alpha=0.9), zorder=12)
        if BE_dn > 0:
            ax.plot([BE_dn], [0], marker='o', markersize=10, color='#c0392b', zorder=11)
            ax.annotate(f'下平衡点 = K−T = {BE_dn:.4g}\n（跌幅超 {(BE_dn - S0) / S0 * 100:+.2f}%'
                        f'即击穿安全垫开始亏损）',
                        xy=(BE_dn, 0), xytext=(-16, -45), textcoords='offset points',
                        fontsize=10, fontweight='bold', color='#c0392b', ha='right',
                        arrowprops=dict(arrowstyle='->', color='#c0392b', linewidth=1.2),
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                                  edgecolor='#c0392b', alpha=0.9), zorder=12)

        # ---- 当前现货位置 ----
        ax.axvline(x=S0, color=self.SPOT_COLOR, linewidth=1.0, linestyle=':', alpha=0.6, zorder=5)
        ax.text(S0, 0.55, f' 当前现货 S0={S0:.4g}',
                transform=ax.get_xaxis_transform(), fontsize=9, color=self.SPOT_COLOR,
                va='center', rotation=90, alpha=0.8)

        # ---- Y 轴留白，防止两端线性延伸贴边 ----
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
        xticklabels = [f'{f:.2f}S0' for f in factors]

        combo_vals = [best.get(f'scenario_pnl_{f:.2f}'.replace(".", "_") + "S", np.nan)
                      for f in factors]
        unhedged_vals = [best.get(f'unhedged_pnl_{f:.2f}'.replace(".", "_") + "S", np.nan)
                         for f in factors]

        fig, ax = plt.subplots(figsize=(20, 10))
        fig.suptitle(f'图7：多情景到期盈亏（{latest_date}）— 最优组合 {best["combo_key"]} '
                     f'vs 买现货对照，X轴=S_T/S0 情景因子',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        ax.plot(x, unhedged_vals, color=self.UNHEDGED_COLOR, linewidth=2.5, linestyle='--',
                marker='D', markersize=6, alpha=0.9, label='买现货 (直接持有)')
        ax.plot(x, combo_vals, color='#c0392b', linewidth=2.8,
                marker='o', markersize=7, label=f'跨式组合 {best["combo_key"]}')

        ax.axhline(y=0, color='gray', linewidth=0.8, linestyle='-', alpha=0.6)
        ax.set_xticks(x)
        ax.set_xticklabels(xticklabels, fontsize=10)
        ax.set_xlabel('情景因子 (S_T / S0)', fontsize=12, fontweight='bold')
        ax.set_ylabel('盈亏 (元/单位)', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')

        # 右端标签
        xlim = ax.get_xlim()
        if xlim[1] > xlim[0]:
            ax.set_xlim(xlim[0], xlim[1] + (xlim[1] - xlim[0]) * 0.22)
        for vals, clr, txt in [(unhedged_vals, self.UNHEDGED_COLOR, '买现货(现货)'),
                               (combo_vals, '#c0392b', f'跨式{best["combo_key"]}')]:
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
        """图8：组合有效前沿散点（最新交易日）：X=胜率，Y=评分，颜色=安全垫宽度"""
        latest_date = df['trade_date'].max()
        latest = df[df['trade_date'] == latest_date].dropna(
            subset=['win_prob', 'score'])
        if latest.empty:
            return None

        fig, ax = plt.subplots(figsize=(20, 10))
        fig.suptitle(f'图8：组合有效前沿（{latest_date}）— X=胜率, Y=评分, '
                     f'颜色=安全垫区间宽度%（平值胜率高、偏离行权价胜率降）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        sc = ax.scatter(latest['win_prob'], latest['score'],
                        c=latest['breakeven_range_pct'], cmap='RdYlGn',
                        s=180, alpha=0.85, edgecolors='#1a1a2e', linewidths=0.8,
                        zorder=8)
        cbar = fig.colorbar(sc, ax=ax, pad=0.01)
        cbar.set_label('安全垫区间宽度 2T/S0 (%)', fontsize=11)

        # 每点标注组合名
        for _, r in latest.iterrows():
            ax.annotate(r['combo_key'], xy=(r['win_prob'], r['score']),
                        xytext=(7, 7), textcoords='offset points', fontsize=7.5,
                        color='#1a1a2e', fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                                  edgecolor='#95a5a6', linewidth=0.4, alpha=0.8))

        # 评分最优组合高亮
        cand = latest.dropna(subset=['score'])
        if not cand.empty:
            best = cand.loc[cand['score'].idxmax()]
            ax.scatter([best['win_prob']], [best['score']], marker='*',
                       s=600, color='#c0392b', edgecolors='#1a1a2e',
                       linewidths=1.2, zorder=10, label=f'评分最优 {best["combo_key"]}')

        ax.axhline(y=0, color='gray', linewidth=0.8, linestyle='-', alpha=0.6)
        ax.set_xlabel('胜率 P(|S_T-K|<T)（对数正态近似）', fontsize=12, fontweight='bold')
        ax.set_ylabel('评分 = 期望值/总权利金', fontsize=12, fontweight='bold')
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
            df_top, 'score', '综合评分 = 期望值/总权利金',
            chart_num=9, title_prefix='图9：Top5 组合综合评分演变（期望值/总权利金，越高越优）',
            ref_lines=[(0.0, '#c0392b', '--', '期望值临界 (=0)')])

    def gen_chart10_net_greeks(self, df):
        """图10：净 Theta/净 Vega（跨式卖方：时间收入 vs 波动率负敞口）"""
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
            df_top, 'net_theta', '净Theta (元/单位/日, 双腿收入叠加)',
            chart_num=10, title_prefix='图10：净Theta(实线) + 净Vega(虚线) — '
                                      '跨式卖方的时间收入与波动率负敞口',
            y2_col='net_vega', y2_label='净Vega (双倍为负)')

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
            'tp_mean': latest['total_premium'].mean() if len(latest) else np.nan,
            'tp_pct_mean': latest['total_premium_pct_of_spot'].mean() if len(latest) else np.nan,
            'be_range_mean': latest['breakeven_range_pct'].mean() if len(latest) else np.nan,
            'em_mean': latest['expected_move_1sigma_pct'].mean() if len(latest) else np.nan,
            'wp_mean': latest['win_prob'].mean() if len(latest) else np.nan,
            'ev_mean': latest['expected_value'].mean() if len(latest) else np.nan,
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
                self._fmt(r['premium'], '{:.4g}'),
                self._fmt(r['premium_put'], '{:.4g}'),
                self._fmt(r['total_premium'], '{:.4g}'),
                self._fmt(r.get('total_premium_pct_of_spot'), '{:.2f}'),
                self._fmt(r['implied_vol'] * 100 if pd.notna(r.get('implied_vol')) else np.nan, '{:.1f}'),
                self._fmt(r.get('iv_rank'), '{:.2f}'),
                self._fmt(r.get('breakeven_up_pct'), '{:+.2f}'),
                self._fmt(r.get('breakeven_down_pct'), '{:+.2f}'),
                self._fmt(r.get('max_profit'), '{:.4g}'),
                self._fmt(r.get('win_prob'), '{:.2f}'),
                self._fmt(r.get('expected_value'), '{:+.4g}'),
                self._fmt(r.get('score'), '{:.3f}'),
                str(int(r.get('combo_rank', 0))) if pd.notna(r.get('combo_rank')) else 'N/A',
                str(r.get('trade_signal', '')),
            ])
        header = ['组合', '行权价K', 'Call价C', 'Put价P', '总收入T', '收入%现价',
                  'IV%', 'IV分位', '上平衡涨幅%', '下平衡跌幅%', '最大盈利T',
                  '胜率', '期望值', '评分', '排名', '信号']
        return header, rows

    def _build_trader_commentary(self, df, stats):
        """资深交易员综合点评（基于数据自动生成，含具体数字）"""
        latest_date, latest = self._latest_snapshot(df)
        paras = []

        # ---- 1. 波动率环境判断（跨式卖方视角：高IV=收租窗口） ----
        iv_r = stats['iv_rank_mean']
        iv_m = stats['iv_mean']
        if pd.notna(iv_r):
            if iv_r >= 0.65:
                env_txt = (f"Call 腿 IV 处于近60日 {iv_r*100:.0f}% 的高分位（均值 {iv_m*100:.1f}%）。"
                           f"这是卖跨式的收租窗口：波动率贵、净 Vega 双倍为负，"
                           f"IV 任何回落（事件落地、恐慌消退）都会带来双腿同时盈利；"
                           f"此时收到的权利金最厚。")
            elif iv_r >= 0.35:
                env_txt = (f"Call 腿 IV 处于近60日 {iv_r*100:.0f}% 的中性区间（均值 {iv_m*100:.1f}%）。"
                           f"权利金定价公允，卖跨式赚钱取决于实际波动是否小于隐含定价——"
                           f"适合对'到期前无大事件'有判断的稳健收租，仓位务必保守。")
            else:
                env_txt = (f"Call 腿 IV 低至近60日 {iv_r*100:.0f}% 分位（均值 {iv_m*100:.1f}%）。"
                           f"波动率卖便宜了：权利金薄、安全垫窄，一旦波动放大得不偿失——"
                           f"此时应放弃卖跨式，考虑反向操作 Long Straddle（见对应报告）。")
            paras.append(('波动率环境判断（卖方视角）', env_txt))

        # ---- 2. 最优组合推荐 ----
        best = stats['best']
        if best is not None:
            paras.append(('最优组合推荐（综合评分第一）',
                          f"组合 {best['combo_key']}（卖 Call(K={best['exercise_price']:.4g}) + "
                          f"卖 Put(K={best['exercise_price']:.4g})，同行权价）："
                          f"总收入 T=C+P={best['total_premium']:.4g}（占现价 "
                          f"{self._fmt(best.get('total_premium_pct_of_spot'), '{:.2f}')}%，"
                          f"也是最大盈利），"
                          f"安全垫区间 [{self._fmt(best.get('breakeven_down'), '{:.4g}')}, "
                          f"{self._fmt(best.get('breakeven_up'), '{:.4g}')}]"
                          f"（涨/跌 {self._fmt(best.get('breakeven_up_pct'), '{:+.2f}')}%/"
                          f"{self._fmt(best.get('breakeven_down_pct'), '{:+.2f}')}% 内收租），"
                          f"胜率≈{self._fmt(best.get('win_prob'), '{:.2f}')}，"
                          f"期望值 {self._fmt(best.get('expected_value'), '{:+.4g}')}。"
                          f"信号：{best.get('trade_signal', 'N/A')}。"
                          f"注意亏损无上限，必须纪律止损。"))

        # ---- 3. 安全垫解读（收入 vs 1σ预期波动） ----
        tp_pct = stats['tp_pct_mean']
        em = stats['em_mean']
        if pd.notna(tp_pct) and pd.notna(em):
            if tp_pct > em:
                note_txt = (f"最新组合平均总收入占现价 {tp_pct:.2f}%，高于 1σ 预期波动 "
                            f"{em:.2f}%——权利金比模型隐含波动还厚，卖方定价占优，"
                            f"安全垫足以覆盖 1 倍标准差的波动。")
            else:
                note_txt = (f"最新组合平均总收入占现价 {tp_pct:.2f}%，低于 1σ 预期波动 "
                            f"{em:.2f}%——安全垫不足以覆盖 1 倍标准差的波动，"
                            f"一旦事件冲击超出常态分布即击穿平衡点，建仓需极其谨慎。")
            paras.append(('安全垫解读（收入 vs 1σ预期波动）', note_txt))

        # ---- 4. Theta 双倍收入（时间是朋友） ----
        nt = stats['net_theta_mean']
        if pd.notna(nt) and nt > 0:
            tp_mean = stats['tp_mean']
            if pd.notna(tp_mean) and tp_mean > 0:
                daily_income = nt / tp_mean * 100
                paras.append(('时间收入（时间是卖方的朋友）',
                              f"组合平均净 Theta = {nt:.5f} 元/单位/日，"
                              f"相当于总权利金 {tp_mean:.4g} 的 {daily_income:.1f}%/日——"
                              f"若标的横盘，权利金按此速度双倍流入卖方账户。"
                              f"但注意：临近到期 Theta 收入加速的同时 Gamma 风险也在放大，"
                              f"现货贴着 K 走时损益剧烈摆动（pin 风险区）。"))

        # ---- 5. 胜率与尾部风险结构 ----
        wp = stats['wp_mean']
        if pd.notna(wp):
            paras.append(('胜率与尾部风险结构（大概率小赔率）',
                          f"最新组合平均胜率 {wp:.2f}（>0.5 为常态，卖方优势）。"
                          f"但收益结构是'大概率×封顶赔率 T + 小概率×无上限亏损'——"
                          f"胜率高不代表安全，一次尾部行情即可吞噬数月收租。"
                          f"风险管理优先级高于收益追求：预设止损线（如击穿平衡点即平仓）、"
                          f"控制保证金占用、避免重仓单一到期月。"))

        # ---- 6. 到期与 pin 风险 ----
        d_min = stats['days_min']
        if pd.notna(d_min):
            if d_min <= 10:
                paras.append(('到期与 pin 风险',
                              f"距到期仅 {d_min:.0f} 天：Gamma 双倍放大，"
                              f"现货在 K 附近时损益剧烈摆动（pin 风险区）。"
                              f"建议提前了结最后两周的仓位——"
                              f"剩余 Theta 收入已薄，不值得承担跳价风险。"))
            elif d_min <= 30:
                paras.append(('到期与 pin 风险',
                              f"距到期 {d_min:.0f} 天，时间收入与风险的平衡区间，"
                              f"应开始规划了结时点，避免进入最后两周的 Gamma 放大区。"))
            else:
                paras.append(('到期与 pin 风险',
                              f"距到期 {d_min:.0f} 天：期限偏长，总权利金较厚，"
                              f"但 Theta 收入被摊薄在更长的持有期内——"
                              f"可考虑滚动卖近月合约提高资金效率。"))

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
        call_put = config.get('call_put')

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
            f"ShortStraddleStrategy_{filter_tag}_{date_tag}_{now_ts}.pdf")

        doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4),
                                rightMargin=40, leftMargin=40, topMargin=36, bottomMargin=28)
        page_width = landscape(A4)[0] - 80
        story = []

        # ===== 封面 =====
        story.append(Spacer(1, 1.4 * inch))
        story.append(Paragraph('卖出跨式策略分析报告', styles['title']))
        story.append(Paragraph('Short Straddle Strategy Analysis Report',
                               ParagraphStyle('Sub', parent=styles['normal'], alignment=1,
                                              fontSize=11, fontName=self.reportlab_font,
                                              textColor=colors.HexColor('#888888'))))
        story.append(Spacer(1, 0.35 * inch))

        combo_names = sorted(set(df['combo_key'].dropna()))
        names_display = '、'.join(combo_names[:40])
        if len(combo_names) > 40:
            names_display += f" 等 {len(combo_names)} 个组合"

        cover_text = (
            f"策略：Short Straddle（卖出 Call(K) + 卖出 Put(K)，同行权价）<br/>"
            f"数据区间：{stats['date_start']} — {stats['date_end']}（{stats['n_days']} 个交易日）<br/>"
            f"报告生成时间：{report_date}<br/>"
            f"分析时间戳：{analysis_time_str}（算法版本 {analysis_version}）<br/>"
            f"合约过滤：symbol LIKE '{symbol_filter or '无'}' | 方向：{call_put or 'C+P 双腿'}<br/>"
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
            f"共 {stats['n_days']} 个交易日、{stats['n_combos']} 个候选跨式组合"
            f"（配对规则：同行权价 Call+Put 双腿，行权价限定 ATM±2 档）。<br/>"
            f"最新交易日 {stats['latest_date']}：现货价 {stats['spot']:.4g}，"
            f"{stats['n_combos_latest']} 个候选组合，Call 腿 IV 均值 {stats['iv_mean']*100:.1f}%"
            f"（IV 分位均值 {stats['iv_rank_mean']:.2f}），"
            f"平均总收入 {stats['tp_mean']:.4g} 元/单位（占现价 {stats['tp_pct_mean']:.2f}%，"
            f"即安全垫半径），平均安全垫区间宽度 {stats['be_range_mean']:.2f}%，"
            f"1σ 预期波动 {stats['em_mean']:.2f}%，平均胜率 {stats['wp_mean']:.2f}，"
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
            '注：总收入T = C+P（也是最大盈利，S_T=K 时顶部）；收入%现价 = T/S0（即安全垫半径）；'
            '上/下平衡涨幅% = (K±T−S0)/S0（涨/跌在此幅度内即收租，击穿即亏损）；'
            '胜率 ≈ P(|S_T−K|<T)（对数正态+双腿IV均值，卖方胜率天然>0.5）；'
            '期望值 = (C−BS_C)+(P−BS_P)（市价比理论贵的幅度）；'
            '评分 = 期望值/总权利金；排名按同日评分降序（1=最优）。'
            '注意：卖跨式亏损无上限，信号必须配合止损纪律执行。',
            styles['table_note']))
        story.append(PageBreak())

        # ===== 三~十二、图表（各配数字说明） =====
        chart_sections = []
        if chart_buffers.get('chart1'):
            chart_sections.append(('chart1', '图1：现货价格 + 各组合总收入',
                                   f"最新现货 {stats['spot']:.4g}，平均总收入 "
                                   f"{stats['tp_mean']:.4g} 元/单位（最大盈利即此值）。"
                                   f"总收入随 IV 上升而扩张、随到期临近而收缩——"
                                   f"同样行权价的跨式，收入越厚代表波动率卖得越贵、安全垫越宽。"))
        if chart_buffers.get('chart2'):
            iv_min = latest['implied_vol'].min()
            iv_max = latest['implied_vol'].max()
            chart_sections.append(('chart2', '图2：Call腿隐含波动率 IV',
                                   f"最新 Call 腿 IV 区间 {iv_min*100:.1f}% ~ {iv_max*100:.1f}%"
                                   f"（Put 腿与其高度相关）。"
                                   f"跨式净 Vega 双倍为负：IV 回落双腿同时盈利、"
                                   f"IV 飙升双腿同时受损——卖跨式本质上是在卖出波动率本身，"
                                   f"警惕事件催化导致的 IV 与价格双重打击。"))
        if chart_buffers.get('chart3'):
            chart_sections.append(('chart3', '图3：安全垫区间宽度',
                                   f"最新平均安全垫区间宽度 {stats['be_range_mean']:.2f}%"
                                   f"（=2×总收入/现价）。区间越宽，"
                                   f"标的在区间内波动的收租概率越高、越安全；"
                                   f"区间越薄则一次常态波动即可击穿——"
                                   f"这是卖跨式直观的风险标尺。"))
        if chart_buffers.get('chart4'):
            chart_sections.append(('chart4', '图4：胜率 + 期望值',
                                   f"最新平均胜率 {stats['wp_mean']:.2f}（>0.5 为常态，卖方优势）。"
                                   f"跨式是'大概率×封顶赔率'结构：胜率高不代表安全，"
                                   f"一次尾部行情即可吞噬数月收租；"
                                   f"虚线期望值为正说明市价跨式比 BS 理论价贵（卖方定价占优）。"))
        if chart_buffers.get('chart5'):
            chart_sections.append(('chart5', '图5：1σ预期波动 vs 总收入',
                                   f"实线为 1σ 预期波动 σ√T年（均值 {stats['em_mean']:.2f}%），"
                                   f"虚线为总收入占现价（均值 {stats['tp_pct_mean']:.2f}%）。"
                                   f"收入 > 1σ 波动 = 贵卖的跨式（定价占优）；"
                                   f"收入 < 1σ 波动 = 安全垫不足以覆盖常态波动，谨慎。"))
        if chart_buffers.get('chart6'):
            best = stats['best']
            if best is not None:
                note = (f"红色实线为组合到期收益（教科书 Λ 形）：顶部最大盈利 T="
                        f"{best['total_premium']:.4g}（S_T=K 时双腿同时归零），"
                        f"两侧线性下探、亏损无上限；红点为双盈亏平衡点 K±T="
                        f"{self._fmt(best.get('breakeven_down'), '{:.4g}')}/"
                        f"{self._fmt(best.get('breakeven_up'), '{:.4g}')}"
                        f"（涨/跌 {self._fmt(best.get('breakeven_up_pct'), '{:+.2f}')}%/"
                        f"{self._fmt(best.get('breakeven_down_pct'), '{:+.2f}')}% 内收租）。"
                        f"蓝虚线（卖Call腿）与橙虚线（卖Put腿）相加即为 Λ 形组合——"
                        f"双向收租换来'无论涨跌、超出安全垫即亏'的尾部风险。")
            else:
                note = "红实线为组合到期收益：Λ 形，顶部盈利封顶 T、两侧亏损无上限。"
            chart_sections.append(('chart6', '图6：教科书到期收益结构（三线图，评分最优组合）', note))
        if chart_buffers.get('chart7'):
            chart_sections.append(('chart7', '图7：多情景到期盈亏（最优组合 vs 买现货）',
                                   "横轴为情景因子（0.85×S0~1.15×S0）。跨式线（红）呈 Λ 形："
                                   "中间收租封顶、两端亏损线性放大；买现货线（灰虚线）方向单一。"
                                   "跨式在横盘情景的稳定收租是现货不具备的；"
                                   "代价是大涨/大跌情景下的无上限亏损。"))
        if chart_buffers.get('chart8'):
            chart_sections.append(('chart8', '图8：组合有效前沿（胜率 vs 评分）',
                                   "每个点为一个候选行权价（标注 K），颜色为安全垫宽度，"
                                   "红星为评分最优。平值附近权利金最厚（安全垫宽）、"
                                   "偏离行权价收入变薄——按对区间波动与尾部风险的容忍度自选。"))
        if chart_buffers.get('chart9'):
            chart_sections.append(('chart9', '图9：Top5 组合评分演变',
                                   "评分 = 期望值/总权利金，衡量'贵卖波动率'的程度。"
                                   "评分持续为正且稳定的行权价是滚动收租候选；"
                                   "评分跳水通常意味着 IV 崩塌（卖便宜了）或现货远离行权价。"))
        if chart_buffers.get('chart10'):
            chart_sections.append(('chart10', '图10：净 Theta / 净 Vega（时间收入 vs 波动率敞口）',
                                   f"最新平均净 Theta = {stats['net_theta_mean']:.5f} 元/单位/日"
                                   f"（双腿收入叠加，时间是卖方的朋友）；"
                                   f"净 Vega（虚线）双倍为负：IV 每变动 1 个点，"
                                   f"组合价值反向变动约为单腿的 2 倍——"
                                   f"这就是'卖跨式=卖波动率'的量化表达，"
                                   f"事件季（财报/政策）应主动降仓。"))

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
                                    self._fmt(r.get('score'), '{:.3f}'),
                                    str(r['trade_signal']), reason])
            story.append(Paragraph('重点信号明细（含原因）', styles['h2']))
            story.append(self._make_table(
                ['组合', '行权价K', '评分', '信号', '信号原因'],
                detail_rows, [90, 70, 55, 70, page_width - 285], font_size=6.5))
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
            "策略定义：卖出认购 Call(K) + 卖出认沽 Put(K)，同行权价同到期月；"
            "总收入 T = C+P；到期组合收益 = T − |S_T−K|，呈教科书 Λ 形（倒V）。<br/>"
            "最大盈利 max_profit = T（S_T=K 时顶部）；亏损无上限（双向线性下探）。<br/>"
            "双盈亏平衡点 breakeven = K±T：到期涨/跌在 (K±T−S0)/S0 幅度内即收租，"
            "击穿即亏损——T 即安全垫半径。<br/>"
            "安全垫区间宽度 breakeven_range_pct = 2T/S0×100：|涨跌|在此区间内即收租，"
            "越宽越安全。<br/>"
            "1σ预期波动 expected_move_1sigma_pct = σ√T年×100（σ为双腿IV均值）："
            "模型隐含的到期波动半径，与收入对比判断定价贵贱。<br/>"
            "胜率 win_prob ≈ P(|S_T−K|&lt;T)：以双腿IV均值为 σ 的对数正态近似"
            "（风险中性概率），卖方胜率天然 &gt; 0.5，但不代表安全。<br/>"
            "期望值 expected_value = (C−BS_C)+(P−BS_P)：市价跨式比 BS 理论价贵的幅度；"
            "评分 score = 期望值/T（风险调整后收益，同日排名依据）。<br/>"
            "净 Greeks：net_delta = −(Δcall+Δput)（ATM附近≈0，方向中性）；"
            "net_gamma/net_vega 双倍为负（Gamma 风险与波动率负敞口叠加）；"
            "net_theta 双倍为正（时间双倍收入——时间是卖方的朋友）。<br/>"
            "组合配对：同行权价 Call+Put 双腿，行权价限定 ATM±2 档——"
            "约束剪枝控制组合爆炸，每日约 5 个候选全量落库。<br/>"
            "信号规则：STRONG_BUY = 双腿IV分位≥0.65 且 期望值>0；"
            "BUY = IV分位均值≥0.50 且 期望值≥0；CONSIDER = IV分位均值≥0.35；"
            "NEUTRAL = IV分位均值≥0.20；其余 AVOID。"
            "所有信号均以'亏损无上限、必须纪律止损'为前提。"
        )
        story.append(Paragraph(glossary, styles['normal']))
        story.append(Spacer(1, 0.15 * inch))

        # ===== 风险提示 =====
        story.append(Paragraph('十六、风险提示', styles['h1']))
        risk_text = (
            "本报告基于历史期权日线数据与 BS 模型理论值进行量化分析，仅供参考，不构成投资建议。<br/>"
            "情景盈亏为到期静态假设（S_T=S0×factor），未考虑路径风险、保证金占用与交易成本。<br/>"
            "胜率为风险中性概率近似（对数正态+IV），与真实概率存在系统性偏差；卖方胜率高不代表安全。<br/>"
            "<b>卖跨式亏损无上限</b>：一次尾部行情（跳空/事件冲击）即可吞噬数月收租，"
            "必须预设止损线（如击穿平衡点即平仓）并严格执行。<br/>"
            "裸卖双方向敞口保证金占用高，临近到期 Gamma 双倍放大（pin 风险区），"
            "双腿流动性差异可能放大平仓滑点。<br/>"
            "ETF 期权为欧式，无提前行权风险，但存在行权交割与合约调整（除权除息）风险。"
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
        call_put = config.get('call_put')
        symbol_filter = config.get('symbol_filter')

        self.writeLogInfo(className=self.__class__.__name__,
                          functionName="run",
                          event=f"Generating ShortStraddleStrategyReport: {name}")

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
                logger.warning("数据为空（请先运行 ShortStraddleStrategyAnalysis 落库），流程终止")
                job_logger.end_job_success(records_processed=0)
                return None

            # Step 2: 清洗 + 图表
            logger.info("Step 2/3: 数据清洗 & 生成图表")
            df = self.clean_data(df)

            chart_buffers = {}
            chart_buffers['chart1'] = self.gen_chart1_spot_total_premium(df)
            chart_buffers['chart2'] = self.gen_chart2_iv(df)
            chart_buffers['chart3'] = self.gen_chart3_safety_margin(df)
            chart_buffers['chart4'] = self.gen_chart4_winprob_ev(df)
            chart_buffers['chart5'] = self.gen_chart5_expected_move(df)
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
            logger.info("✅ Short Straddle 策略分析报告 生成完成！")
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
    report = ShortStraddleStrategyReport()
    report.run({
        "name": "华夏上证50ETF期权（Short Straddle）",
        "start_date": "20251222",
        "end_date": CommonParameters.today,
        "call_put": None,
        "symbol_filter": "510050%2612%",
    })

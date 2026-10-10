r"""
Short Strangle（卖出宽跨式）策略 PDF 报告生成器 — 资深交易员/风控视角

数据源：
    tb_option_trading_strategy_short_strangle (strategy_type='SHORT_STRANGLE',
    由 ShortStrangleStrategyAnalysis 写入，含 analysis_time/analysis_params 审计字段)

报告结构：
    封面 → 数据概览(数字) → 最新交易日组合总览(表格, 按评分排名) → 10张图表(各配数字说明)
    → 交易信号汇总(表格) → 资深交易员综合点评(自动生成, 含数字) → 指标口径 → 风险提示

核心图表：
    图6 教科书三线到期收益结构图（倒 V 平顶：Call腿(K2)/Put腿(K1)/组合）——
    平坦盈利区 [K1,K2] 恒收 T（跨式卖方只有单点尖顶，宽跨式卖方是"平台"收租区）、
    双侧盈亏平衡点 上=K2+T / 下=K1-T、亏损无上限（风险管理优先级高于收益追求）

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


class ShortStrangleStrategyReport:
    """Short Strangle 策略 报告生成器"""

    REPORT_DIR = CommonParameters.optionAnalysisReportPath
    TABLE_SOURCE = 'tb_option_trading_strategy_short_strangle'
    STRATEGY_TYPE = 'SHORT_STRANGLE'

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
        """从 tb_option_trading_strategy_short_strangle 拉取 SHORT_STRANGLE 策略分析结果"""
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
        ORDER BY trade_date, exercise_price, exercise_price_put
        """
        logger.info(f"SQL:\n{sql}")
        df = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        logger.info(f"Fetched {len(df)} rows, {len(df.columns)} columns")
        return df

    def clean_data(self, df):
        """类型转换与派生列（combo_key = "K1=低/K2=高" 作为组合唯一标识）"""
        numeric_cols = [
            'exercise_price', 'exercise_price_put', 'opt_multiplier', 'spot_price',
            'premium', 'premium_put', 'implied_vol', 'implied_vol_put',
            'iv_rank', 'iv_rank_put',
            'delta', 'gamma', 'theta', 'vega',
            'delta_put', 'gamma_put', 'theta_put', 'vega_put',
            'bs_theoretical_price', 'bs_theoretical_price_put',
            'close_vs_theoretical', 'close_vs_theoretical_pct',
            'close_vs_theoretical_put', 'close_vs_theoretical_pct_put',
            'net_delta', 'net_gamma', 'net_theta', 'net_vega',
            'strike_gap', 'strike_gap_pct',
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

        # 组合唯一标识："K1=2.90/K2=3.00"（宽跨式双腿行权价不同）
        df['combo_key'] = df.apply(
            lambda r: f"K1={r['exercise_price_put']:.4g}/K2={r['exercise_price']:.4g}", axis=1)

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
        """图1：现货价(Y1) + 各组合双腿总租金 T=P+C（Y2，收了多少=最大盈利）"""
        combo_keys, series_dict = self._prep_series(df, ['spot_price', 'total_premium'])
        if not combo_keys:
            return None

        fig, ax1 = plt.subplots(figsize=(20, 8))
        fig.suptitle('图1：标的现货价格 + 各宽跨式组合双腿总租金 T = P+C（最大盈利）',
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

        # Y2: total_premium（卖方租金）
        ax2 = ax1.twinx()
        for idx, key in enumerate(combo_keys):
            sub = series_dict[key]
            if 'total_premium' in sub.columns and sub['total_premium'].notna().sum() > 0:
                s = sub['total_premium'].dropna()
                color = self.CHART_COLORS[idx % len(self.CHART_COLORS)]
                ax2.plot(s.index.tolist(), s.values, color=color, linewidth=0.9,
                         alpha=0.8, marker='o', markersize=3, label=key)
        ax2.set_ylabel('双腿总租金 T = P+C (元/单位)', fontsize=11)

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
            chart_num=2, title_prefix='图2：Call腿 隐含波动率 IV（Put腿与其高度相关，'
                                     '双腿均值决定卖宽跨式的租金定价）')

    def gen_chart3_breakeven_range(self, df):
        return self._gen_metric_chart(
            df, 'breakeven_range_pct', '安全垫区间宽度 (K2-K1+2T)/S0 (%)',
            chart_num=3, title_prefix='图3：安全垫区间宽度（上K2+T 至 下K1-T，'
                                      '缺口加厚收租安全垫，越宽击穿概率越低）',
            ref_lines=[
                (8.0, '#c0392b', '--', '偏薄 (<8%)'),
                (12.0, '#f39c12', '--', '中性 (=12%)'),
                (16.0, '#27ae60', '--', '厚安全垫 (>=16%)'),
            ])

    def gen_chart4_winprob_ev(self, df):
        return self._gen_metric_chart(
            df, 'win_prob', '胜率 P(K1-T<=S_T<=K2+T)',
            chart_num=4, title_prefix='图4：胜率(实线) + 期望值(虚线) — 大概率小赔率结构'
                                      '（缺口加厚安全垫，宽跨式卖方胜率天然高于跨式卖方）',
            y2_col='expected_value', y2_label='期望值 (市价-BS理论)',
            ref_lines=[
                (0.80, '#27ae60', '--', '高胜率 (>=0.80)'),
                (0.60, '#c0392b', '--', '偏薄 (<0.60)'),
            ])

    def gen_chart5_expected_move(self, df):
        return self._gen_metric_chart(
            df, 'expected_move_1sigma_pct', '1σ预期波动 σ√T年 (%)',
            chart_num=5, title_prefix='图5：1σ预期波动(实线) + 双腿总租金占现价(虚线) — '
                                      '卖方核心权衡：租更薄 vs 缺口加厚的安全垫',
            y2_col='total_premium_pct_of_spot', y2_label='双腿总租金/现价 T/S0 (%)',
            ref_lines=[(0.0, '#c0392b', '--', '')])

    def gen_chart6_payoff_textbook(self, df):
        """图6：教科书三线到期收益结构（最新交易日评分最优组合）★核心图表

        Call腿:   C - max(S_T-K2, 0) （蓝虚线，右侧下行起点在 K2）
        Put腿:    P - max(K1-S_T, 0) （橙虚线，左侧下行起点在 K1）
        组合:     加总（红实线, 倒 V 平顶）
        标注:     平坦盈利区 [K1,K2] 恒收 T（"平台"收租区，区别于跨式卖方的单点尖顶）、
                  双侧平衡点 上=K2+T、下=K1-T、亏损无上限
        """
        latest_date, best = self._best_combo_latest(df)
        if best is None:
            return None

        K2 = float(best['exercise_price'])        # Call 腿（高行权价）
        K1 = float(best['exercise_price_put'])   # Put 腿（低行权价）
        C = float(best['premium'])
        P = float(best['premium_put'])
        S0 = float(best['spot_price'])
        T = P + C
        BE_up = K2 + T
        BE_dn = K1 - T
        combo_name = best['combo_key']

        x = np.linspace(min(0.80 * S0, BE_dn * 0.92), max(1.20 * S0, BE_up * 1.08), 400)

        payoff_call = C - np.maximum(x - K2, 0)      # Call 腿（卖出，OTM）
        payoff_put = P - np.maximum(K1 - x, 0)       # Put 腿（卖出，OTM）
        payoff_combo = payoff_call + payoff_put        # 组合（红实线，倒 V 平顶）

        fig, ax = plt.subplots(figsize=(20, 10))
        fig.suptitle(f'图6：Short Strangle 教科书到期收益结构 — 组合 {combo_name}'
                     f'（评分最优，{latest_date}）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        # ---- 盈亏区间着色（中间平坦盈利区，两侧亏损无上限） ----
        ax.fill_between(x, payoff_combo, 0, where=(payoff_combo > 0), color='#27ae60',
                        alpha=0.10, label='收租区间（落在 [K1-T, K2+T] 内即盈利）')
        ax.fill_between(x, payoff_combo, 0, where=(payoff_combo <= 0), color='#c0392b',
                        alpha=0.10, label='亏损区间（击穿任一侧平衡点后线性放大，无上限）')

        # ---- 三条线：Put腿/Call腿（虚线）+ 组合（红实线加粗） ----
        ax.plot(x, payoff_call, color='#3498db', linewidth=1.6, linestyle='--',
                alpha=0.85, label=f'Call腿(K2={K2:.4g})：C-max(S_T-K2,0)')
        ax.plot(x, payoff_put, color='#f39c12', linewidth=1.6, linestyle='--',
                alpha=0.85, label=f'Put腿(K1={K1:.4g})：P-max(K1-S_T,0)')
        ax.plot(x, payoff_combo, color='#c0392b', linewidth=3.2, zorder=9,
                label='组合：T-max(S_T-K2,0)-max(K1-S_T,0)（倒 V 平顶）')

        # ---- 关键标注：平坦盈利区（宽跨式卖方的结构优势） ----
        ax.axhline(y=T, color='#27ae60', linewidth=1.4, linestyle='--', alpha=0.9, zorder=6)
        mid_gap = (K1 + K2) / 2
        ax.annotate(f'平坦盈利区 [K1,K2]：恒收 +T = P+C = {T:.4g}\n'
                    f'（S_T∈[{K1:.4g},{K2:.4g}] 时双腿同时归零，\n'
                    f'跨式卖方只有单点尖顶，宽跨式卖方是"平台"收租区）',
                    xy=(mid_gap, T), xytext=(0, 55), textcoords='offset points',
                    fontsize=10, fontweight='bold', color='#27ae60', ha='center',
                    arrowprops=dict(arrowstyle='->', color='#27ae60', linewidth=1.2),
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                              edgecolor='#27ae60', alpha=0.9), zorder=12)

        # ---- 双行权价竖线 K1/K2（收租平台边界） ----
        ax.axvline(x=K1, color='#f39c12', linewidth=1.4, linestyle=':', alpha=0.9, zorder=6)
        ax.text(K1, 0.02, f' K1={K1:.4g}\n (Put行权价,\n平台左界)',
                transform=ax.get_xaxis_transform(), fontsize=9, color='#f39c12',
                va='bottom', fontweight='bold')
        ax.axvline(x=K2, color='#3498db', linewidth=1.4, linestyle=':', alpha=0.9, zorder=6)
        ax.text(K2, 0.02, f' K2={K2:.4g}\n (Call行权价,\n平台右界)',
                transform=ax.get_xaxis_transform(), fontsize=9, color='#3498db',
                va='bottom', fontweight='bold')

        # ---- 双侧盈亏平衡点（击穿即亏损） ----
        ax.plot([BE_up], [0], marker='o', markersize=10, color='#c0392b', zorder=11)
        ax.annotate(f'上平衡点 = K2+T = {BE_up:.4g}\n（需涨 {(BE_up - S0) / S0 * 100:+.2f}% 才击穿）',
                    xy=(BE_up, 0), xytext=(16, -40), textcoords='offset points',
                    fontsize=10, fontweight='bold', color='#c0392b',
                    arrowprops=dict(arrowstyle='->', color='#c0392b', linewidth=1.2),
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                              edgecolor='#c0392b', alpha=0.9), zorder=12)
        if BE_dn > 0:
            ax.plot([BE_dn], [0], marker='o', markersize=10, color='#c0392b', zorder=11)
            ax.annotate(f'下平衡点 = K1-T = {BE_dn:.4g}\n（需跌 {(BE_dn - S0) / S0 * 100:+.2f}% 才击穿）',
                        xy=(BE_dn, 0), xytext=(-16, -40), textcoords='offset points',
                        fontsize=10, fontweight='bold', color='#c0392b', ha='right',
                        arrowprops=dict(arrowstyle='->', color='#c0392b', linewidth=1.2),
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                                  edgecolor='#c0392b', alpha=0.9), zorder=12)

        # ---- 当前现货位置 ----
        ax.axvline(x=S0, color=self.SPOT_COLOR, linewidth=1.0, linestyle=':', alpha=0.6, zorder=5)
        ax.text(S0, 0.55, f' 当前现货 S0={S0:.4g}',
                transform=ax.get_xaxis_transform(), fontsize=9, color=self.SPOT_COLOR,
                va='center', rotation=90, alpha=0.8)

        # ---- Y 轴留白，防止两端线性下行贴边 ----
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
                marker='o', markersize=7, label=f'卖宽跨式 {best["combo_key"]}')

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
                               (combo_vals, '#c0392b', f'卖宽跨式{best["combo_key"]}')]:
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
        """图8：组合有效前沿散点（最新交易日）：X=胜率，Y=评分，颜色=安全垫区间宽度"""
        latest_date = df['trade_date'].max()
        latest = df[df['trade_date'] == latest_date].dropna(
            subset=['win_prob', 'score'])
        if latest.empty:
            return None

        fig, ax = plt.subplots(figsize=(20, 10))
        fig.suptitle(f'图8：组合有效前沿（{latest_date}）— X=胜率, Y=评分, '
                     f'颜色=安全垫区间宽度%（缺口大/租金厚=胜率高）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        sc = ax.scatter(latest['win_prob'], latest['score'],
                        c=latest['breakeven_range_pct'], cmap='RdYlGn',
                        s=180, alpha=0.85, edgecolors='#1a1a2e', linewidths=0.8,
                        zorder=8)
        cbar = fig.colorbar(sc, ax=ax, pad=0.01)
        cbar.set_label('安全垫区间宽度 (K2-K1+2T)/S0 (%)', fontsize=11)

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
        ax.set_xlabel('胜率 P(K1-T<=S_T<=K2+T)（对数正态近似）', fontsize=12,
                      fontweight='bold')
        ax.set_ylabel('评分 = 期望值/总租金', fontsize=12, fontweight='bold')
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
            df_top, 'score', '综合评分 = 期望值/总租金',
            chart_num=9, title_prefix='图9：Top5 组合综合评分演变（期望值/总租金，越高越优）',
            ref_lines=[(0.0, '#c0392b', '--', '期望值临界 (=0)')])

    def gen_chart10_net_greeks(self, df):
        """图10：净 Theta/净 Vega（宽跨式卖方：双腿时间收入、负 vega 敞口）"""
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
            df_top, 'net_theta', '净Theta (元/单位/日, 双腿时间收入叠加)',
            chart_num=10, title_prefix='图10：净Theta(实线) + 净Vega(虚线) — '
                                      '宽跨式卖方的时间收入与负波动率敞口',
            y2_col='net_vega', y2_label='净Vega (双倍为负, IV回升双腿受损)')

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
            'gap_pct_mean': latest['strike_gap_pct'].mean() if len(latest) else np.nan,
            'be_range_mean': latest['breakeven_range_pct'].mean() if len(latest) else np.nan,
            'em_mean': latest['expected_move_1sigma_pct'].mean() if len(latest) else np.nan,
            'wp_mean': latest['win_prob'].mean() if len(latest) else np.nan,
            'ev_mean': latest['expected_value'].mean() if len(latest) else np.nan,
            'net_theta_mean': latest['net_theta'].mean() if len(latest) else np.nan,
            'net_delta_mean': latest['net_delta'].mean() if len(latest) else np.nan,
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
                self._fmt(r['exercise_price_put'], '{:.4g}'),
                self._fmt(r['exercise_price'], '{:.4g}'),
                self._fmt(r['premium_put'], '{:.4g}'),
                self._fmt(r['premium'], '{:.4g}'),
                self._fmt(r['total_premium'], '{:.4g}'),
                self._fmt(r.get('total_premium_pct_of_spot'), '{:.2f}'),
                self._fmt(r.get('strike_gap_pct'), '{:.2f}'),
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
        header = ['组合', 'K1(Put)', 'K2(Call)', 'Put价P', 'Call价C', '总租金T=P+C',
                  '租金%现价', '缺口K2-K1%', 'Call IV%', 'IV分位', '上平衡涨幅%',
                  '下平衡跌幅%', '最大盈利T', '胜率', '期望值', '评分', '排名', '信号']
        return header, rows

    def _build_trader_commentary(self, df, stats):
        """资深交易员综合点评（基于数据自动生成，含具体数字）"""
        latest_date, latest = self._latest_snapshot(df)
        paras = []

        # ---- 1. 波动率环境判断（宽跨式卖方视角：高IV=贵卖窗口） ----
        iv_r = stats['iv_rank_mean']
        iv_m = stats['iv_mean']
        if pd.notna(iv_r):
            if iv_r >= 0.65:
                env_txt = (f"Call 腿 IV 高至近60日 {iv_r*100:.0f}% 分位（均值 {iv_m*100:.1f}%）。"
                           f"这是卖宽跨式的黄金窗口：波动率贵、双腿净 Vega 双倍为负，"
                           f"IV 任何回落都是双腿同时收租；高 IV 也意味着 OTM 腿的租金更厚——"
                           f"卖方收的'保险费'处于区间高位。")
            elif iv_r >= 0.35:
                env_txt = (f"Call 腿 IV 处于近60日 {iv_r*100:.0f}% 的中性区间（均值 {iv_m*100:.1f}%）。"
                           f"宽跨式租金定价公允，能否收租取决于实际波动是否小于隐含定价——"
                           f"由于缺口加厚了安全垫，横盘容忍度比卖跨式更高；"
                           f"但租也更薄（OTM 双腿），需权衡'击穿概率低'与'收益薄'。")
            else:
                env_txt = (f"Call 腿 IV 处于近60日 {iv_r*100:.0f}% 的低分位（均值 {iv_m*100:.1f}%）。"
                           f"波动率卖便宜了：OTM 双腿租金本就微薄，低 IV 期卖宽跨式"
                           f"是在'薄租 + 低波动率'的双重不利下承担无上限尾部风险——"
                           f"除非明确预期 IV 持续走低，否则观望。")
            paras.append(('波动率环境判断（卖方视角）', env_txt))

        # ---- 2. 最优组合推荐 ----
        best = stats['best']
        if best is not None:
            paras.append(('最优组合推荐（综合评分第一）',
                          f"组合 {best['combo_key']}（卖 1 份 Put(K1={best['exercise_price_put']:.4g}) + "
                          f"卖 1 份 Call(K2={best['exercise_price']:.4g})，K1 &lt; K2）："
                          f"双腿总租金 T=P+C={best['total_premium']:.4g}（占现价 "
                          f"{self._fmt(best.get('total_premium_pct_of_spot'), '{:.2f}')}%，"
                          f"也是最大盈利），"
                          f"收租安全垫区间 [{self._fmt(best.get('breakeven_down'), '{:.4g}')}, "
                          f"{self._fmt(best.get('breakeven_up'), '{:.4g}')}]"
                          f"（缺口 K2-K1 占现价 {self._fmt(best.get('strike_gap_pct'), '{:.2f}')}%："
                          f"涨 {self._fmt(best.get('breakeven_up_pct'), '{:+.2f}')}%、"
                          f"跌 {self._fmt(best.get('breakeven_down_pct'), '{:+.2f}')}% 以内均收租），"
                          f"胜率≈{self._fmt(best.get('win_prob'), '{:.2f}')}，"
                          f"期望值 {self._fmt(best.get('expected_value'), '{:+.4g}')}。"
                          f"信号：{best.get('trade_signal', 'N/A')}。"))

        # ---- 3. 租更薄 vs 安全垫更厚的核心权衡 ----
        tp_pct = stats['tp_pct_mean']
        em = stats['em_mean']
        gap_pct = stats['gap_pct_mean']
        be_range = stats['be_range_mean']
        if pd.notna(tp_pct) and pd.notna(em) and pd.notna(gap_pct):
            paras.append(('核心权衡：租更薄 vs 缺口加厚的安全垫',
                          f"最新组合平均双腿租金占现价 {tp_pct:.2f}%（通常低于同月跨式——"
                          f"OTM 腿收得少），但缺口 K2-K1 平均占现价 {gap_pct:.2f}%，"
                          f"将收租安全垫拉宽至平均 {be_range:.2f}%。"
                          f"卖宽跨式用'收得更少'换'击穿概率更低'。"
                          f"判断标准：安全垫半宽约 {be_range/2:.2f}% vs 1σ 预期波动 {em:.2f}%——"
                          f"前者显著大于后者，收租才有统计优势。"))

        # ---- 4. 平坦盈利区（平台收租）的结构解读 ----
        if best is not None:
            paras.append(('平坦盈利区解读（宽跨式卖方的结构优势）',
                          f"组合 {best['combo_key']} 的平坦盈利区为 "
                          f"[{best['exercise_price_put']:.4g}, {best['exercise_price']:.4g}]："
                          f"到期价落在该区间内时双腿同时归零、恒收全部租金 T——"
                          f"跨式卖方只有 S_T=K 一个尖顶点，宽跨式卖方是一整片'平台'收租区，"
                          f"横盘容忍度显著更高。这是用更薄租金换来的核心保护，"
                          f"也是卖宽跨式胜率天然高于卖跨式的原因。"))

        # ---- 5. Theta 双腿收入确认（时间是朋友） ----
        nt = stats['net_theta_mean']
        if pd.notna(nt) and nt > 0:
            tp_mean = stats['tp_mean']
            if pd.notna(tp_mean) and tp_mean > 0:
                daily_income = nt / tp_mean * 100
                paras.append(('时间收入确认（双腿卖方的时间朋友）',
                              f"组合平均净 Theta = +{nt:.5f} 元/单位/日，"
                              f"占双腿总租金 {tp_mean:.4g} 的 {daily_income:.1f}%/日——"
                              f"双腿同时收取时间价值衰减。横盘即收租是本策略的存在逻辑；"
                              f"但临近到期 gamma 风险放大（现货贴近任一腿行权价时损益剧烈摆动），"
                              f"建议在到期前 1~2 周主动了结而非持有到期。"))

        # ---- 6. 胜率与赔率结构 ----
        wp = stats['wp_mean']
        if pd.notna(wp):
            paras.append(('胜率与赔率结构（大概率小赔率）',
                          f"最新组合平均胜率 {wp:.2f}（缺口加厚安全垫，"
                          f"天然高于同月卖跨式，>0.7 为常态）。"
                          f"宽跨式卖方是'大概率小赔率'结构：胜率高不代表风险低——"
                          f"单次亏损无上限且可能远超多次租金之和，"
                          f"长期存活依赖止损纪律与仓位控制，而非胜率本身。"))

        # ---- 7. 到期与尾部风险管理 ----
        d_min = stats['days_min']
        if pd.notna(d_min):
            if d_min <= 10:
                paras.append(('到期与尾部风险管理',
                              f"距到期仅 {d_min:.0f} 天：gamma 风险进入放大区——"
                              f"现货贴近任一腿行权价时损益剧烈摆动（pin 风险区）。"
                              f"建议提前平仓锁定剩余租金，切勿'扛'到期。"))
            elif d_min <= 30:
                paras.append(('到期与尾部风险管理',
                              f"距到期 {d_min:.0f} 天，租期适中。"
                              f"应预设止损线（如亏损 = 2×T 即离场）与事件日历检查"
                              f"（财报/政策会议前主动降敞口），避免事件跳空击穿安全垫。"))
            else:
                paras.append(('到期与尾部风险管理',
                              f"距到期 {d_min:.0f} 天：租期偏长，虽然 theta 收入时间充裕，"
                              f"但无上限尾部风险的敞口时间也更长——"
                              f"若仅为收短租，优选更近的到期月。"))

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
            f"ShortStrangleStrategy_{filter_tag}_{date_tag}_{now_ts}.pdf")

        doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4),
                                rightMargin=40, leftMargin=40, topMargin=36, bottomMargin=28)
        page_width = landscape(A4)[0] - 80
        story = []

        # ===== 封面 =====
        story.append(Spacer(1, 1.4 * inch))
        story.append(Paragraph('卖出宽跨式策略分析报告', styles['title']))
        story.append(Paragraph('Short Strangle Strategy Analysis Report',
                               ParagraphStyle('Sub', parent=styles['normal'], alignment=1,
                                              fontSize=11, fontName=self.reportlab_font,
                                              textColor=colors.HexColor('#888888'))))
        story.append(Spacer(1, 0.35 * inch))

        combo_names = sorted(set(df['combo_key'].dropna()))
        names_display = '、'.join(combo_names[:40])
        if len(combo_names) > 40:
            names_display += f" 等 {len(combo_names)} 个组合"

        cover_text = (
            f"策略：Short Strangle（卖出 1 份 Put(K1) + 卖出 1 份 Call(K2)，K1 &lt; K2，同到期月）<br/>"
            f"策略特征：方向中性卖波动率（OTM 双腿收租 + 平坦盈利区 [K1,K2] + 缺口加厚的安全垫；亏损无上限）<br/>"
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
            f"共 {stats['n_days']} 个交易日、{stats['n_combos']} 个候选宽跨式组合"
            f"（配对规则：Put 腿 K1 ∈ ATM 下方 0~2 档 × Call 腿 K2 ∈ ATM 上方 0~2 档，"
            f"且 K2&gt;K1 的跨档配对）。<br/>"
            f"最新交易日 {stats['latest_date']}：现货价 {stats['spot']:.4g}，"
            f"{stats['n_combos_latest']} 个候选组合，Call 腿 IV 均值 {stats['iv_mean']*100:.1f}%"
            f"（IV 分位均值 {stats['iv_rank_mean']:.2f}），"
            f"平均双腿总租金 {stats['tp_mean']:.4g} 元/单位（占现价 {stats['tp_pct_mean']:.2f}%，"
            f"通常低于同月跨式），平均行权价缺口 {stats['gap_pct_mean']:.2f}%，"
            f"平均安全垫区间宽度 {stats['be_range_mean']:.2f}%，"
            f"1σ 预期波动 {stats['em_mean']:.2f}%，平均胜率 {stats['wp_mean']:.2f}，"
            f"平均净 Delta {stats['net_delta_mean']:+.3f}（方向中性），"
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
            '注：K1=Put腿行权价（低），K2=Call腿行权价（高），K1&lt;K2；'
            '总租金 T = P+C（OTM 双腿合计，也是最大盈利，S_T∈[K1,K2] 平坦盈利区时锁定）；'
            '缺口K2-K1% = (K2-K1)/S0×100（拉宽平坦盈利区与安全垫）；'
            '上平衡涨幅% = (K2+T-S0)/S0（涨超即亏损）；下平衡跌幅% = (K1-T-S0)/S0（跌超即亏损）；'
            '胜率 ≈ P(K1-T≤S_T≤K2+T)（对数正态+双腿 IV 均值，'
            '宽跨式卖方胜率天然高于卖跨式）；'
            '期望值 = (C-BS_C)+(P-BS_P)（市价比理论贵的幅度）；'
            '评分 = 期望值/总租金；排名按同日评分降序（1=最优）。',
            styles['table_note']))
        story.append(PageBreak())

        # ===== 三~十二、图表（各配数字说明） =====
        chart_sections = []
        if chart_buffers.get('chart1'):
            chart_sections.append(('chart1', '图1：现货价格 + 各组合双腿总租金',
                                   f"最新现货 {stats['spot']:.4g}，平均双腿总租金 "
                                   f"{stats['tp_mean']:.4g} 元/单位（最大盈利即此值）。"
                                   f"OTM 双腿租金低于同月跨式——用'收得更少'换'击穿概率更低'；"
                                   f"租金随 IV 上升而扩张、随到期临近而收敛。"))
        if chart_buffers.get('chart2'):
            iv_min = latest['implied_vol'].min()
            iv_max = latest['implied_vol'].max()
            chart_sections.append(('chart2', '图2：Call腿隐含波动率 IV',
                                   f"最新 Call 腿 IV 区间 {iv_min*100:.1f}% ~ {iv_max*100:.1f}%"
                                   f"（Put 腿与其高度相关，双腿均值决定卖宽跨式的租金定价）。"
                                   f"净 Vega 双倍为负：IV 回落双腿同时收租、"
                                   f"IV 飙升双腿同时受损——卖宽跨式本质上是在卖出波动率本身。"))
        if chart_buffers.get('chart3'):
            chart_sections.append(('chart3', '图3：安全垫区间宽度（上K2+T 至 下K1-T）',
                                   f"最新平均安全垫区间宽度 {stats['be_range_mean']:.2f}%"
                                   f"（=(缺口 K2-K1+2T)/现价）。区间越宽击穿概率越低；"
                                   f"跨式仅 2T/S0——宽出的'缺口'部分是收租安全垫的加厚来源，"
                                   f"也是租更薄的对价。选择宽缺口=更安全但收更少，"
                                   f"窄缺口=接近跨式特征（租厚但尖顶）。"))
        if chart_buffers.get('chart4'):
            chart_sections.append(('chart4', '图4：胜率 + 期望值',
                                   f"最新平均胜率 {stats['wp_mean']:.2f}（>0.7 为常态，"
                                   f"天然高于卖跨式——缺口加厚安全垫）。"
                                   f"宽跨式卖方是'大概率小赔率'结构：高胜率不代表低风险——"
                                   f"单次亏损无上限，长期存活依赖止损纪律；"
                                   f"虚线期望值为正说明市价宽跨式比 BS 理论价贵（卖得值）。"))
        if chart_buffers.get('chart5'):
            chart_sections.append(('chart5', '图5：1σ预期波动 vs 双腿总租金',
                                   f"实线为 1σ 预期波动 σ√T年（均值 {stats['em_mean']:.2f}%），"
                                   f"虚线为双腿总租金占现价（均值 {stats['tp_pct_mean']:.2f}%）。"
                                   f"租金远低于 1σ 波动是卖宽跨式的常态（OTM 腿本就便宜）——"
                                   f"关键判断应结合安全垫区间宽度（图3，均值 "
                                   f"{stats['be_range_mean']:.2f}%）："
                                   f"安全垫半宽需显著大于 1σ 波动才有统计优势。"))
        if chart_buffers.get('chart6'):
            best = stats['best']
            if best is not None:
                note = (f"红色实线为组合到期收益（倒 V 平顶）："
                        f"平坦盈利区 [{best['exercise_price_put']:.4g}, {best['exercise_price']:.4g}] "
                        f"恒收 +T={best['total_premium']:.4g}"
                        f"（S_T 落在两腿行权价之间时双腿同时归零，区别于跨式卖方的单点尖顶），"
                        f"双侧线性下行亏损无上限；"
                        f"红点为双侧盈亏平衡点：上 K2+T="
                        f"{self._fmt(best.get('breakeven_up'), '{:.4g}')}"
                        f"（需涨 {self._fmt(best.get('breakeven_up_pct'), '{:+.2f}')}% 才击穿）、"
                        f"下 K1-T="
                        f"{self._fmt(best.get('breakeven_down'), '{:.4g}')}"
                        f"（需跌 {self._fmt(best.get('breakeven_down_pct'), '{:+.2f}')}% 才击穿）。"
                        f"蓝虚线（Call 腿 K2）与橙虚线（Put 腿 K1）相加即为组合——"
                        f"两腿起点分离（K1≠K2）正是宽跨式与跨式的全部结构差异。")
            else:
                note = "红实线为组合到期收益：平坦盈利区恒收 +T，双侧线性下行亏损无上限。"
            chart_sections.append(('chart6', '图6：教科书到期收益结构（三线图，评分最优组合）', note))
        if chart_buffers.get('chart7'):
            chart_sections.append(('chart7', '图7：多情景到期盈亏（最优组合 vs 买现货）',
                                   "横轴为情景因子（0.85×S0~1.15×S0）。卖宽跨式线（红）中部平坦"
                                   "（0.95~1.05 情景多处于平坦盈利区，恒收 T）、"
                                   "两端线性下行（亏损无上限）；买现货线（灰虚线）方向单一。"
                                   "深度涨跌情景的无上限亏损是本策略的尾部风险——"
                                   "事件跳空可一举击穿安全垫，这是高胜率的代价。"))
        if chart_buffers.get('chart8'):
            chart_sections.append(('chart8', '图8：组合有效前沿（胜率 vs 评分）',
                                   "每个点为一个候选组合（标注 K1/K2），颜色为安全垫区间宽度，"
                                   "红星为评分最优。缺口大、租厚=胜率高（更安全）；"
                                   "缺口大、租薄=胜率高但收益微薄——按风险偏好与保证金效率自选权衡点。"))
        if chart_buffers.get('chart9'):
            chart_sections.append(('chart9', '图9：Top5 组合评分演变',
                                   "评分 = 期望值/双腿总租金，衡量'卖贵波动率'的程度。"
                                   "评分持续为正且稳定的组合是滚动收租候选；"
                                   "评分跳水通常意味着 IV 骤降（卖便宜了）或现货移近缺口边缘"
                                   "（击穿风险上升）。"))
        if chart_buffers.get('chart10'):
            chart_sections.append(('chart10', '图10：净 Theta / 净 Vega（双腿敞口）',
                                   f"最新平均净 Theta = +{stats['net_theta_mean']:.5f} 元/单位/日"
                                   f"（双腿时间收入叠加，时间是卖方的朋友）；"
                                   f"净 Vega（虚线）双倍为负：IV 每变动 1 个点，"
                                   f"组合价值双份反向联动——这就是'卖宽跨式=卖波动率'的量化表达，"
                                   f"也是事件前必须降敞口的原因。"))

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
                                    self._fmt(r['exercise_price_put'], '{:.4g}'),
                                    self._fmt(r['exercise_price'], '{:.4g}'),
                                    self._fmt(r.get('score'), '{:.3f}'),
                                    str(r['trade_signal']), reason])
            story.append(Paragraph('重点信号明细（含原因）', styles['h2']))
            story.append(self._make_table(
                ['组合', 'K1(Put)', 'K2(Call)', '评分', '信号', '信号原因'],
                detail_rows, [105, 55, 55, 50, 65, page_width - 330], font_size=6.5))
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
            "策略定义：卖出 1 份认沽 Put(K1) + 1 份认购 Call(K2)，K1&lt;K2，同到期月（双腿 OTM）；"
            "双腿总租金 T = P+C；到期组合收益 = T - max(0,S_T-K2) - max(0,K1-S_T)，"
            "呈倒 V 平顶（平坦盈利区 + 双侧线性下行）。<br/>"
            "行权价缺口 strike_gap = K2-K1：拉宽平坦盈利区与安全垫的结构性因素——"
            "与跨式的唯一结构差异（K1=K2 时退化为跨式）。<br/>"
            "最大盈利 max_profit = T：S_T∈[K1,K2] 时双腿同时归零锁定"
            "（'平台'收租区而非跨式卖方的单点尖顶）；亏损无上限（双向裸卖）。<br/>"
            "双侧盈亏平衡点：上 = K2+T（涨超即亏损），下 = K1-T（跌超即亏损）；"
            "安全垫区间宽度 breakeven_range_pct = (K2-K1+2T)/S0×100："
            "跨式仅 2T/S0，宽出的'缺口'部分是收租安全垫的加厚来源。<br/>"
            "1σ预期波动 expected_move_1sigma_pct = σ√T年×100（σ为双腿 IV 均值）："
            "模型隐含的到期波动半径，与安全垫半宽对比判断收租的统计优势。<br/>"
            "胜率 win_prob ≈ P(K1-T ≤ S_T ≤ K2+T)：以双腿 IV 均值为 σ 的对数正态近似"
            "（风险中性概率）= 1 - 买宽跨式胜率；缺口使宽跨式卖方胜率天然高于卖跨式。<br/>"
            "期望值 expected_value = (C-BS_C) + (P-BS_P)：市价宽跨式比 BS 理论价贵的幅度"
            "（卖方正期望，双腿均为 OTM，受波动率微笑两端斜率影响）；"
            "评分 score = 期望值/T（同日排名依据）。<br/>"
            "净 Greeks（卖方敞口取负叠加）：net_delta = -(Δcall+Δput)"
            "（两腿对称 OTM 时约 0，方向中性）；"
            "net_gamma 为负（现货贴近任一腿行权价时绝对值骤增）；"
            "net_theta = -(Θcall+Θput) 为正（双腿时间双倍收入）；"
            "net_vega = -(Vcall+Vput) 为负（IV 回升双腿同时受损）。<br/>"
            "组合配对：Put 腿 K1 ∈ ATM 下方 0~2 档 × Call 腿 K2 ∈ ATM 上方 0~2 档，"
            "且 K2&gt;K1（跨档配对借鉴价差类，约束剪枝控制组合爆炸），"
            "每日至多 8 个候选全量落库。<br/>"
            "信号规则：STRONG_BUY = 双腿IV分位≥0.65 且 期望值&gt;0；"
            "BUY = 双腿IV分位均值≥0.50 且 期望值≥0；"
            "CONSIDER = 双腿IV分位均值≥0.35；NEUTRAL = ≥0.20；其余 AVOID。"
            "宽跨式卖方信号以'贵卖波动'为核心，任何信号都必须配合止损纪律执行"
            "（亏损无上限，风险管理优先级高于收益追求）。"
        )
        story.append(Paragraph(glossary, styles['normal']))
        story.append(Spacer(1, 0.15 * inch))

        # ===== 风险提示 =====
        story.append(Paragraph('十六、风险提示', styles['h1']))
        risk_text = (
            "本报告基于历史期权日线数据与 BS 模型理论值进行量化分析，仅供参考，不构成投资建议。<br/>"
            "宽跨式卖方亏损无上限（双向裸卖）：一次极端行情的亏损可能超过多次租金之和，"
            "风险管理优先级高于收益追求。<br/>"
            "保证金风险：裸卖双方向保证金占用高，交易所可能动态上调保证金率，"
            "触发强制平仓风险。<br/>"
            "事件跳空风险：财报、政策会议、外围市场暴跌等事件可能导致现货跳空穿越安全垫，"
            "止损单无法在理想价位成交。<br/>"
            "胜率为风险中性概率近似（对数正态+双腿IV均值），高估了真实'含跳空分布'下的安全性；"
            "肥尾分布下击穿概率被系统性低估。<br/>"
            "临近到期 gamma 风险：现货贴近任一腿行权价时损益剧烈摆动（pin 风险区），"
            "建议到期前主动了结而非持有到期。<br/>"
            "情景盈亏为到期静态假设（S_T=S0×factor），未考虑路径风险、保证金追加与交易成本。<br/>"
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
                          event=f"Generating ShortStrangleStrategyReport: {name}")

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
                logger.warning("数据为空（请先运行 ShortStrangleStrategyAnalysis 落库），流程终止")
                job_logger.end_job_success(records_processed=0)
                return None

            # Step 2: 清洗 + 图表
            logger.info("Step 2/3: 数据清洗 & 生成图表")
            df = self.clean_data(df)

            chart_buffers = {}
            chart_buffers['chart1'] = self.gen_chart1_spot_total_premium(df)
            chart_buffers['chart2'] = self.gen_chart2_iv(df)
            chart_buffers['chart3'] = self.gen_chart3_breakeven_range(df)
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
            logger.info("✅ Short Strangle 策略分析报告 生成完成！")
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
    report = ShortStrangleStrategyReport()
    report.run({
        "name": "华夏上证50ETF期权（Short Strangle）",
        "start_date": "20251222",
        "end_date": CommonParameters.today,
        "call_put": None,
        "symbol_filter": "510050%2612%",
    })

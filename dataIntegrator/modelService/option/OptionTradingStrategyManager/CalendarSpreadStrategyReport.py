r"""
Calendar Spread（日历价差）策略 PDF 报告生成器 — 资深交易员/风控视角

数据源：
    tb_option_trading_strategy_calendar (strategy_type='CALENDAR',
    由 CalendarSpreadStrategyAnalysis 写入，含 analysis_time/analysis_params 审计字段)

报告结构：
    封面 → 数据概览(数字) → 最新交易日组合总览(表格, 按评分排名) → 10张图表(各配数字说明)
    → 交易信号汇总(表格) → 资深交易员综合点评(自动生成, 含数字) → 指标口径 → 风险提示

核心图表：
    图6 教科书三线"近月到期日组合价值曲线"——
    近月腿 payoff（封闭形式）/ 远月腿 BS 残值曲线 / 组合（尖峰形）：
    S_T≈K 处盈利峰值标注（数值解）、双侧盈亏平衡点、亏损封顶 = 净支出 D

输出：
    PDF → CommonParameters.optionAnalysisReportPath
    (D:\workspace_python\infinity_data\outbound\report\OptionAnalysis)
"""

import io
import os
from datetime import datetime
from scipy.special import erf

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


def _norm_cdf(z):
    """标准正态分布 CDF（scipy.special.erf，标量与 numpy 数组通用）"""
    return 0.5 * (1.0 + erf(z / np.sqrt(2.0)))


def _bs_call_price(S, K, r, q, sigma, T):
    """欧式 Call BS 定价（S 可为数组，其余为标量）——远月腿残值定价"""
    S = np.asarray(S, dtype=float)
    sigma_t = sigma * np.sqrt(T)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / sigma_t
    d2 = d1 - sigma_t
    return S * np.exp(-q * T) * _norm_cdf(d1) - K * np.exp(-r * T) * _norm_cdf(d2)


class CalendarSpreadStrategyReport:
    """Calendar Spread 策略 报告生成器"""

    REPORT_DIR = CommonParameters.optionAnalysisReportPath
    TABLE_SOURCE = 'tb_option_trading_strategy_calendar'
    STRATEGY_TYPE = 'CALENDAR'

    # 情景因子（与分析端 DEFAULT_SCENARIOS 一致，S_T = S0 × factor，情景日=近月到期日）
    SCENARIO_FACTORS = [0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15]

    # 图6 价值曲线网格（与分析端 GRID_* 一致）
    GRID_LO, GRID_HI, GRID_N = 0.80, 1.20, 81

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
        """从 tb_option_trading_strategy_calendar 拉取 CALENDAR 策略分析结果"""
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName="fetch_data",
                          event=f"Fetching data from {self.TABLE_SOURCE}")

        where_clauses = [f"strategy_type = '{self.STRATEGY_TYPE}'"]
        if start_date:
            where_clauses.append(f"trade_date >= '{start_date}'")
        if end_date:
            where_clauses.append(f"trade_date <= '{end_date}'")
        if symbol_filter:
            where_clauses.append(f"symbol_near LIKE '{symbol_filter}'")
        if call_put:
            where_clauses.append(f"call_put = '{call_put}'")

        where_str = " AND ".join(where_clauses)
        sql = f"""
        SELECT *
        FROM indexsysdb.{self.TABLE_SOURCE}
        WHERE {where_str}
        ORDER BY trade_date, s_month_near, s_month_far, exercise_price
        """
        logger.info(f"SQL:\n{sql}")
        df = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        logger.info(f"Fetched {len(df)} rows, {len(df.columns)} columns")
        return df

    def clean_data(self, df):
        """类型转换与派生列（combo_key = "近月/远月@K" 作为组合唯一标识）"""
        numeric_cols = [
            'exercise_price', 'opt_multiplier', 'spot_price',
            'premium_near', 'premium_far', 'implied_vol_near', 'implied_vol_far',
            'iv_rank_near', 'iv_rank_far',
            'delta_near', 'gamma_near', 'theta_near', 'vega_near',
            'delta_far', 'gamma_far', 'theta_far', 'vega_far',
            'bs_theoretical_price_near', 'bs_theoretical_price_far',
            'close_vs_theoretical_near', 'close_vs_theoretical_pct_near',
            'close_vs_theoretical_far', 'close_vs_theoretical_pct_far',
            'net_delta', 'net_gamma', 'net_theta', 'net_vega',
            'iv_term_spread', 'theta_differential',
            'net_debit', 'net_debit_cny', 'net_debit_pct_of_spot',
            'expected_move_1sigma_pct',
            'max_loss', 'max_loss_cny', 'max_loss_pct_of_spot',
            'max_profit', 'max_profit_cny', 'max_profit_pct_of_spot',
            'breakeven_down', 'breakeven_down_pct',
            'breakeven_up', 'breakeven_up_pct',
            'win_prob', 'expected_value', 'score', 'combo_rank',
            'month_gap_days', 'days_to_maturity_near', 'days_to_maturity_far',
            'risk_free_rate', 'dividend_yield',
        ] + [f'scenario_pnl_{f:.2f}'.replace('.', '_') + suf
             for f in self.SCENARIO_FACTORS for suf in ('S', 'S_cny', 'S_pct')] \
          + [f'unhedged_pnl_{f:.2f}'.replace('.', '_') + suf
             for f in self.SCENARIO_FACTORS for suf in ('S', 'S_pct')]

        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # 派生列：IV 期限结构差（vol 点，绘图用）
        if {'implied_vol_near', 'implied_vol_far'}.issubset(df.columns):
            df['iv_term_spread_pct'] = (df['implied_vol_near'] - df['implied_vol_far']) * 100

        # 组合唯一标识："2610/2612@K2.95"（近/远月+行权价）
        df['combo_key'] = df.apply(
            lambda r: f"{r['s_month_near']}/{r['s_month_far']}@K{r['exercise_price']:.4g}", axis=1)

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
        """图1：现货价(Y1) + 各组合净支出 D=C_far-C_near（Y2，最大亏损）"""
        combo_keys, series_dict = self._prep_series(df, ['spot_price', 'net_debit'])
        if not combo_keys:
            return None

        fig, ax1 = plt.subplots(figsize=(20, 8))
        fig.suptitle('图1：标的现货价格 + 各日历价差组合净支出 D = C_far-C_near（最大亏损）',
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

        # Y2: net_debit（净支出）
        ax2 = ax1.twinx()
        for idx, key in enumerate(combo_keys):
            sub = series_dict[key]
            if 'net_debit' in sub.columns and sub['net_debit'].notna().sum() > 0:
                s = sub['net_debit'].dropna()
                color = self.CHART_COLORS[idx % len(self.CHART_COLORS)]
                ax2.plot(s.index.tolist(), s.values, color=color, linewidth=0.9,
                         alpha=0.8, marker='o', markersize=3, label=key)
        ax2.set_ylabel('净支出 D = C_far-C_near (元/单位)', fontsize=11)

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

    def gen_chart2_iv_near_far(self, df):
        """图2：近月 IV（实线）vs 远月 IV（虚线）——期限结构的原料"""
        return self._gen_metric_chart(
            df, 'implied_vol_near', '近月腿隐含波动率 (implied_vol_near, 小数)',
            chart_num=2, title_prefix='图2：近月IV(实线) vs 远月IV(虚线) — '
                                     '两线之差即期限结构（近月在上=近贵远贱）',
            y2_col='implied_vol_far', y2_label='远月腿隐含波动率 (小数)')

    def gen_chart3_iv_term_spread(self, df):
        """图3：IV 期限结构差（本策略的灵魂指标）"""
        return self._gen_metric_chart(
            df, 'iv_term_spread_pct', 'IV期限结构差 (IV_near-IV_far, vol点)',
            chart_num=3, title_prefix='图3：IV期限结构差 — 正值=近贵远贱（正期望入场条件），'
                                      '倒挂=远月贵（reverse calendar 场景）',
            ref_lines=[
                (1.0, '#27ae60', '--', '显著正价差 (>=+1vol点)'),
                (0.0, '#7f8c8d', '-', '平坦 (=0)'),
                (-1.0, '#c0392b', '--', '倒挂 (<=-1vol点)'),
            ])

    def gen_chart4_winprob_ev(self, df):
        return self._gen_metric_chart(
            df, 'win_prob', '胜率 P(V(S_T)>0)',
            chart_num=4, title_prefix='图4：胜率(实线) + 期望值(虚线) — 尖峰结构的概率刻画'
                                      '（近月到期日S_T网格数值积分）',
            y2_col='expected_value', y2_label='期望值 (近月卖贵+远月买便宜)',
            ref_lines=[
                (0.50, '#27ae60', '--', '过半 (>=0.50)'),
                (0.30, '#c0392b', '--', '偏窄 (<0.30, 尖峰区间窄)'),
            ])

    def gen_chart5_expected_move(self, df):
        return self._gen_metric_chart(
            df, 'expected_move_1sigma_pct', '1σ预期波动 σ√T_near年 (%)',
            chart_num=5, title_prefix='图5：近月1σ预期波动(实线) + 净支出占现价(虚线) — '
                                      '尖峰区间 vs 正常波动的覆盖关系',
            y2_col='net_debit_pct_of_spot', y2_label='净支出/现价 D/S0 (%)')

    def gen_chart6_payoff_textbook(self, df):
        """图6：教科书三线"近月到期日组合价值曲线"（最新交易日评分最优组合）★核心图表

        近月腿:   C_near - max(S_T-K, 0) （橙虚线，卖方，封闭形式）
        远月腿:   BS_call(S_T; K, r, q, IV_far, T_rem) - C_far（蓝虚线，BS 残值曲线）
        组合:     加总（红实线，尖峰形）
        标注:     S_T≈K 处盈利峰值（数值解）、双侧盈亏平衡点、亏损封顶 = 净支出 D
        """
        latest_date, best = self._best_combo_latest(df)
        if best is None:
            return None

        K = float(best['exercise_price'])
        C_near = float(best['premium_near'])
        C_far = float(best['premium_far'])
        S0 = float(best['spot_price'])
        r = float(best['risk_free_rate'])
        q = float(best['dividend_yield'])
        iv_far = float(best['implied_vol_far'])
        years_near = float(best['days_to_maturity_near']) / 365.0
        years_far = float(best['days_to_maturity_far']) / 365.0
        t_rem = years_far - years_near
        D = C_far - C_near
        combo_name = best['combo_key']

        if pd.isna(iv_far) or t_rem <= 0:
            logger.warning("Chart6: invalid iv_far or remaining maturity, skipping")
            return None

        grid = np.linspace(self.GRID_LO, self.GRID_HI, self.GRID_N)
        x = S0 * grid

        payoff_near = C_near - np.maximum(x - K, 0)                     # 近月腿（卖方）
        far_leg = _bs_call_price(x, K, r, q, iv_far, t_rem) - C_far      # 远月腿（BS残值）
        payoff_combo = payoff_near + far_leg                             # 组合（尖峰形）

        fig, ax = plt.subplots(figsize=(20, 10))
        fig.suptitle(f'图6：Calendar Spread 近月到期日组合价值曲线 — 组合 {combo_name}'
                     f'（评分最优，{latest_date}）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        # ---- 盈亏区间着色（中间尖峰盈利区，双侧亏损封顶） ----
        ax.fill_between(x, payoff_combo, 0, where=(payoff_combo > 0), color='#27ae60',
                        alpha=0.10, label='盈利区间（尖峰内）')
        ax.fill_between(x, payoff_combo, 0, where=(payoff_combo <= 0), color='#c0392b',
                        alpha=0.10, label='亏损区间（封底 -D，双侧收敛）')

        # ---- 三条线：近月腿/远月腿（虚线）+ 组合（红实线加粗） ----
        ax.plot(x, far_leg, color='#3498db', linewidth=1.6, linestyle='--',
                alpha=0.85, label=f'远月腿：BS残值(S_T)-C_far（IV_far={iv_far*100:.1f}%，剩{t_rem*365:.0f}天）')
        ax.plot(x, payoff_near, color='#f39c12', linewidth=1.6, linestyle='--',
                alpha=0.85, label=f'近月腿：C_near-max(S_T-K,0)（到期归零区）')
        ax.plot(x, payoff_combo, color='#c0392b', linewidth=3.2, zorder=9,
                label='组合：近月payoff+远月BS残值（尖峰形）')

        # ---- 尖峰最大盈利标注（数值解） ----
        j_max = int(np.nanargmax(payoff_combo))
        s_star = x[j_max]
        mp = payoff_combo[j_max]
        ax.annotate(f'尖峰最大盈利 +{mp:.4g} @ S_T={s_star:.4g}\n'
                    f'（近月腿归零 + 远月残值最大处，\n'
                    f'最大亏损封底 -D = {D:.4g}）',
                    xy=(s_star, mp), xytext=(0, 55), textcoords='offset points',
                    fontsize=10, fontweight='bold', color='#27ae60', ha='center',
                    arrowprops=dict(arrowstyle='->', color='#27ae60', linewidth=1.2),
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                              edgecolor='#27ae60', alpha=0.9), zorder=12)

        # ---- 行权价竖线（两腿同行权价） ----
        ax.axvline(x=K, color='#8e44ad', linewidth=1.4, linestyle=':', alpha=0.9, zorder=6)
        ax.text(K, 0.02, f' K={K:.4g}\n (两腿同行权价,\n尖峰锚点)',
                transform=ax.get_xaxis_transform(), fontsize=9, color='#8e44ad',
                va='bottom', fontweight='bold')

        # ---- 双侧盈亏平衡点（数值解） ----
        crossings = []
        for j in range(len(payoff_combo) - 1):
            if (payoff_combo[j] > 0) >= (payoff_combo[j + 1] > 0) and payoff_combo[j] != payoff_combo[j + 1]:
                t0 = payoff_combo[j] / (payoff_combo[j] - payoff_combo[j + 1])
                crossings.append(x[j] + t0 * (x[j + 1] - x[j]))
        for be in crossings:
            ax.plot([be], [0], marker='o', markersize=10, color='#c0392b', zorder=11)
            ax.annotate(f'平衡点 = {be:.4g}\n（偏离 {(be - S0) / S0 * 100:+.2f}%）',
                        xy=(be, 0), xytext=(16 if be > S0 else -16, -40),
                        textcoords='offset points',
                        fontsize=10, fontweight='bold', color='#c0392b',
                        ha='left' if be > S0 else 'right',
                        arrowprops=dict(arrowstyle='->', color='#c0392b', linewidth=1.2),
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                                  edgecolor='#c0392b', alpha=0.9), zorder=12)

        # ---- 当前现货位置 ----
        ax.axvline(x=S0, color=self.SPOT_COLOR, linewidth=1.0, linestyle=':', alpha=0.6, zorder=5)
        ax.text(S0, 0.55, f' 当前现货 S0={S0:.4g}',
                transform=ax.get_xaxis_transform(), fontsize=9, color=self.SPOT_COLOR,
                va='center', rotation=90, alpha=0.8)

        # ---- Y 轴留白 ----
        ymin, ymax = ax.get_ylim()
        ax.set_ylim(ymin - 0.05 * (ymax - ymin), ymax + 0.05 * (ymax - ymin))

        ax.axhline(y=0, color='gray', linewidth=0.8, linestyle='-', alpha=0.6)
        ax.set_xlabel('近月到期日标的价 S_T', fontsize=12, fontweight='bold')
        ax.set_ylabel('组合价值 (元/单位)', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10), fontsize=9,
                  ncol=3, frameon=True, handlelength=1.8)
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    def gen_chart7_scenario_pnl(self, df):
        """图7：多情景到期盈亏（最优组合 vs 买现货对照，情景日=近月到期日）"""
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
        fig.suptitle(f'图7：多情景到期盈亏（{latest_date}，情景日=近月到期日）— 最优组合 '
                     f'{best["combo_key"]} vs 买现货对照',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        ax.plot(x, unhedged_vals, color=self.UNHEDGED_COLOR, linewidth=2.5, linestyle='--',
                marker='D', markersize=6, alpha=0.9, label='买现货 (直接持有)')
        ax.plot(x, combo_vals, color='#c0392b', linewidth=2.8,
                marker='o', markersize=7, label=f'日历价差 {best["combo_key"]}')

        ax.axhline(y=0, color='gray', linewidth=0.8, linestyle='-', alpha=0.6)
        ax.set_xticks(x)
        ax.set_xticklabels(xticklabels, fontsize=10)
        ax.set_xlabel('情景因子 (S_T / S0，近月到期日)', fontsize=12, fontweight='bold')
        ax.set_ylabel('盈亏 (元/单位)', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')

        # 右端标签
        xlim = ax.get_xlim()
        if xlim[1] > xlim[0]:
            ax.set_xlim(xlim[0], xlim[1] + (xlim[1] - xlim[0]) * 0.22)
        for vals, clr, txt in [(unhedged_vals, self.UNHEDGED_COLOR, '买现货(现货)'),
                               (combo_vals, '#c0392b', f'日历价差{best["combo_key"]}')]:
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
        """图8：组合有效前沿散点（最新交易日）：X=胜率，Y=评分，颜色=期限结构差"""
        latest_date = df['trade_date'].max()
        latest = df[df['trade_date'] == latest_date].dropna(
            subset=['win_prob', 'score'])
        if latest.empty:
            return None

        fig, ax = plt.subplots(figsize=(20, 10))
        fig.suptitle(f'图8：组合有效前沿（{latest_date}）— X=胜率, Y=评分, '
                     f'颜色=IV期限结构差(vol点)',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        color_col = 'iv_term_spread_pct' if 'iv_term_spread_pct' in latest.columns \
            else 'iv_term_spread'
        sc = ax.scatter(latest['win_prob'], latest['score'],
                        c=latest[color_col], cmap='RdYlGn',
                        s=180, alpha=0.85, edgecolors='#1a1a2e', linewidths=0.8,
                        zorder=8)
        cbar = fig.colorbar(sc, ax=ax, pad=0.01)
        cbar.set_label('IV期限结构差 IV_near-IV_far (vol点)', fontsize=11)

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
        ax.set_xlabel('胜率 P(V(S_T)>0)（近月到期日数值积分）', fontsize=12,
                      fontweight='bold')
        ax.set_ylabel('评分 = 期望值/净支出', fontsize=12, fontweight='bold')
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
        """图10：净 Theta/净 Vega（日历价差：时间收入与正 vega 敞口）"""
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
            df_top, 'net_theta', '净Theta (元/单位/日, 近月衰减快于远月)',
            chart_num=10, title_prefix='图10：净Theta(实线) + 净Vega(虚线) — '
                                      '日历价差的时间收入与正波动率敞口',
            y2_col='net_vega', y2_label='净Vega (正=买远月波动率, IV整体下行受损)')

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
            'iv_near_mean': latest['implied_vol_near'].mean() if len(latest) else np.nan,
            'iv_far_mean': latest['implied_vol_far'].mean() if len(latest) else np.nan,
            'ivs_mean': latest['iv_term_spread'].mean() if len(latest) else np.nan,
            'ivs_pct_mean': (latest['iv_term_spread'].mean() * 100) if len(latest) else np.nan,
            'nd_mean': latest['net_debit'].mean() if len(latest) else np.nan,
            'nd_pct_mean': latest['net_debit_pct_of_spot'].mean() if len(latest) else np.nan,
            'td_mean': latest['theta_differential'].mean() if len(latest) else np.nan,
            'mp_mean': latest['max_profit'].mean() if len(latest) else np.nan,
            'wp_mean': latest['win_prob'].mean() if len(latest) else np.nan,
            'ev_mean': latest['expected_value'].mean() if len(latest) else np.nan,
            'net_theta_mean': latest['net_theta'].mean() if len(latest) else np.nan,
            'net_vega_mean': latest['net_vega'].mean() if len(latest) else np.nan,
            'net_delta_mean': latest['net_delta'].mean() if len(latest) else np.nan,
            'gap_mean': latest['month_gap_days'].mean() if len(latest) else np.nan,
            'days_near_min': int(latest['days_to_maturity_near'].min()) if len(latest) else np.nan,
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
                str(r.get('s_month_near', '')),
                self._fmt(r.get('days_to_maturity_near'), '{:.0f}'),
                str(r.get('s_month_far', '')),
                self._fmt(r.get('month_gap_days'), '{:.0f}'),
                self._fmt(r['premium_near'], '{:.4g}'),
                self._fmt(r['premium_far'], '{:.4g}'),
                self._fmt(r['net_debit'], '{:.4g}'),
                self._fmt(r.get('net_debit_pct_of_spot'), '{:.2f}'),
                self._fmt(r['iv_term_spread'] * 100 if pd.notna(r.get('iv_term_spread')) else np.nan,
                          '{:+.2f}'),
                self._fmt(r.get('iv_rank_near'), '{:.2f}'),
                self._fmt(r.get('iv_rank_far'), '{:.2f}'),
                self._fmt(r.get('max_profit'), '{:.4g}'),
                self._fmt(r.get('max_loss'), '{:.4g}'),
                self._fmt(r.get('breakeven_down_pct'), '{:+.2f}'),
                self._fmt(r.get('breakeven_up_pct'), '{:+.2f}'),
                self._fmt(r.get('win_prob'), '{:.2f}'),
                self._fmt(r.get('expected_value'), '{:+.4g}'),
                self._fmt(r.get('score'), '{:.3f}'),
                str(int(r.get('combo_rank', 0))) if pd.notna(r.get('combo_rank')) else 'N/A',
                str(r.get('trade_signal', '')),
            ])
        header = ['组合(近/远@K)', 'K', '近月', '近月剩余天', '远月', '间隔天',
                  'C_near', 'C_far', '净支出D', 'D%现价', '期限差vol点',
                  '近IV分位', '远IV分位', '最大盈利', '最大亏损D',
                  '下平衡%', '上平衡%', '胜率', '期望值', '评分', '排名', '信号']
        return header, rows

    def _build_trader_commentary(self, df, stats):
        """资深交易员综合点评（基于数据自动生成，含具体数字）"""
        latest_date, latest = self._latest_snapshot(df)
        paras = []

        # ---- 1. 期限结构环境判断 ----
        ivs = stats['ivs_mean']
        iv_near = stats['iv_near_mean']
        iv_far = stats['iv_far_mean']
        if pd.notna(ivs):
            if ivs >= 0.01:
                env_txt = (f"近月 IV 均值 {iv_near*100:.1f}% vs 远月 {iv_far*100:.1f}%，"
                          f"期限结构差 +{ivs*100:.2f} 个 vol 点（近贵远贱）。"
                          f"这是日历价差的黄金窗口：卖近月的时间溢价、买远月的低波动率——"
                          f"期限结构回归常态化（近远收敛）的过程中双腿同时受益。")
            elif ivs > 0:
                env_txt = (f"期限结构差 +{ivs*100:.2f} 个 vol 点（近月略贵，近月 IV "
                          f"{iv_near*100:.1f}% vs 远月 {iv_far*100:.1f}%）。"
                          f"结构轻度有利：卖近买远的 theta 时间差存在，但入场安全边际不厚，"
                          f"依赖近月到期前现货平稳。")
            elif ivs >= -0.01:
                env_txt = (f"期限结构差 {ivs*100:+.2f} 个 vol 点（结构平坦，近月 IV "
                          f"{iv_near*100:.1f}% vs 远月 {iv_far*100:.1f}%）。"
                          f"卖近买近无结构优势，日历价差的收益仅剩 theta 时间差——"
                          f"盈亏比通常不吸引，观望为宜。")
            else:
                env_txt = (f"期限结构差 {ivs*100:+.2f} 个 vol 点（倒挂，远月贵于近月）。"
                          f"本表为买远卖近的 Calendar 结构，倒挂期入场是负期望——"
                          f"倒挂场景属 reverse calendar（卖远买近）的机会，不在本策略范围内。")
            paras.append(('期限结构环境判断（本策略的灵魂）', env_txt))

        # ---- 2. 最优组合推荐 ----
        best = stats['best']
        if best is not None:
            paras.append(('最优组合推荐（综合评分第一）',
                          f"组合 {best['combo_key']}（卖 1 份 {best['s_month_near']} Call(K="
                          f"{best['exercise_price']:.4g}) @ C_near={best['premium_near']:.4g} + "
                          f"买 1 份 {best['s_month_far']} Call(K={best['exercise_price']:.4g}) "
                          f"@ C_far={best['premium_far']:.4g}，月份间隔 "
                          f"{best['month_gap_days']:.0f} 天）："
                          f"净支出 D={best['net_debit']:.4g}（占现价 "
                          f"{self._fmt(best.get('net_debit_pct_of_spot'), '{:.2f}')}%，"
                          f"即最大亏损，亏损封顶），"
                          f"尖峰最大盈利 +{self._fmt(best.get('max_profit'), '{:.4g}')}，"
                          f"盈亏平衡区间 [{self._fmt(best.get('breakeven_down'), '{:.4g}')}, "
                          f"{self._fmt(best.get('breakeven_up'), '{:.4g}')}]"
                          f"（跌 {self._fmt(best.get('breakeven_down_pct'), '{:+.2f}')}%、"
                          f"涨 {self._fmt(best.get('breakeven_up_pct'), '{:+.2f}')}% 以内盈利），"
                          f"胜率≈{self._fmt(best.get('win_prob'), '{:.2f}')}，"
                          f"期望值 {self._fmt(best.get('expected_value'), '{:+.4g}')}。"
                          f"信号：{best.get('trade_signal', 'N/A')}。"))

        # ---- 3. Theta 时间差确认 ----
        td = stats['td_mean']
        nt = stats['net_theta_mean']
        if pd.notna(td) and td > 0:
            nd = stats['nd_mean']
            if pd.notna(nd) and nd > 0:
                daily_edge = td / nd * 100
                paras.append(('时间差确认（时间是朋友）',
                              f"最新组合平均 Theta 时间差 = +{td:.5f} 元/单位/日"
                              f"（近月衰减快于远月），占平均净支出 {nd:.4g} 的 "
                              f"{daily_edge:.1f}%/日——结构的收益来源健康："
                              f"近月腿每天归零的速度快于远月腿的贬值。"
                              f"注意该优势在近月到期前 30~7 天最明显，"
                              f"最后 7 天 gamma 风险将超过 theta 收益。"))
        elif pd.notna(td) and td <= 0:
            paras.append(('时间差确认（时间是朋友）',
                          f"最新组合平均 Theta 时间差 = {td:+.5f}（非正）——"
                          f"近月衰减不快于远月，日历价差的结构收益来源缺失。"
                          f"通常意味着远月 IV 相对过高或月份间隔异常，建议回避。"))

        # ---- 4. 尖峰结构解读 ----
        if best is not None:
            mp = best.get('max_profit')
            ml = best.get('max_loss')
            if pd.notna(mp) and pd.notna(ml) and ml > 0:
                rr = mp / ml
                paras.append(('尖峰收益结构解读（盈亏比）',
                              f"最优组合最大盈利 {mp:.4g} vs 最大亏损（封顶）{ml:.4g}，"
                              f"盈亏比 ≈ {rr:.2f}:1。日历价差是'亏损封顶 + 盈利尖峰'结构："
                              f"盈利区间窄（需 S_T 落在平衡点之间），"
                              f"但亏损绝不超过净支出 D——与卖宽跨式的'盈利封顶+亏损无上限'"
                              f"完全互补。盈亏比高于 1 说明尖峰足够厚，"
                              f"低于 1 则需期限结构更极端的入场时机。"))

        # ---- 5. Greeks 敞口画像 ----
        nv = stats['net_vega_mean']
        ng_note = ('负 Gamma 敞口：现货快速移动时近月腿亏损加速——'
                   '临近月到期时该效应放大（pin 风险区），建议到期前 1 周主动了结或展期。')
        if pd.notna(nv):
            paras.append(('Greeks 敞口画像（正theta/正vega/负gamma）',
                          f"最新平均净 Theta +{stats['net_theta_mean']:.5f}（时间收入）、"
                          f"净 Vega +{nv:.5f}（买远月波动率：IV 整体上行受益、"
                          f"下行受损——期限结构走阔与 IV 崩塌是两种截然不同的情景）、"
                          f"净 Delta {stats['net_delta_mean']:+.3f}（准中性）。"
                          + ng_note))

        # ---- 6. 到期与展期管理 ----
        d_min = stats['days_near_min']
        if pd.notna(d_min):
            if d_min <= 7:
                paras.append(('到期与展期管理',
                              f"最近月仅剩 {d_min:.0f} 天：进入 gamma/pin 风险区——"
                              f"现货贴 K 时近月腿损益剧烈摆动。"
                              f"建议：了结近月腿（买回）保留远月腿成为裸 Call 需谨慎，"
                              f"更稳妥是整组平仓或滚动到下一对月份（roll the calendar）。"))
            elif d_min <= 30:
                paras.append(('到期与展期管理',
                              f"最近月剩余 {d_min:.0f} 天：theta 时间差的兑现窗口。"
                              f"到期前一周需做展期决策：平近月 + 卖下一个近月 = 滚动日历，"
                              f"远月腿逐渐变为新的近月时结构自然衰减。"))
            else:
                paras.append(('到期与展期管理',
                              f"最近月剩余 {d_min:.0f} 天：结构尚处等待期，"
                              f"theta 差异随到期临近才逐步拉开。"
                              f"入场前确认两腿流动性（远月买卖价差通常更宽）。"))

        # ---- 7. 分红敞口提示 ----
        mat_fars = latest['maturity_date_far'].dropna().astype(str)
        div_months = [m for m in mat_fars if len(m) >= 6 and m[4:6] in ('11', '12')]
        if len(div_months) > 0:
            paras.append(('分红敞口提示（Call Calendar 特有）',
                          f"最新 {len(latest)} 个候选组合中有 {len(div_months)} 个的远月到期日"
                          f"落在 11~12 月（50ETF 分红季）。除息会使远月 Call 跌价"
                          f"（S0 下移、远月内在价值受损）——持有跨越分红季的日历价差"
                          f"需在分红公告后重新评估：若分红超预期，远月腿的 BS 残值"
                          f"将被高估，尖峰最大盈利打折扣。"))

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
            f"CalendarSpreadStrategy_{filter_tag}_{date_tag}_{now_ts}.pdf")

        doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4),
                                rightMargin=40, leftMargin=40, topMargin=36, bottomMargin=28)
        page_width = landscape(A4)[0] - 80
        story = []

        # ===== 封面 =====
        story.append(Spacer(1, 1.4 * inch))
        story.append(Paragraph('日历价差策略分析报告', styles['title']))
        story.append(Paragraph('Calendar Spread Strategy Analysis Report',
                               ParagraphStyle('Sub', parent=styles['normal'], alignment=1,
                                              fontSize=11, fontName=self.reportlab_font,
                                              textColor=colors.HexColor('#888888'))))
        story.append(Spacer(1, 0.35 * inch))

        combo_names = sorted(set(df['combo_key'].dropna()))
        names_display = '、'.join(combo_names[:40])
        if len(combo_names) > 40:
            names_display += f" 等 {len(combo_names)} 个组合"

        cover_text = (
            f"策略：Calendar Spread（卖 1 份近月 Call(K) + 买 1 份远月 Call(K)，同行权价跨月）<br/>"
            f"策略特征：赚时间差（正Theta）+ 买远月波动率（正Vega）+ 亏损封顶=净支出D；"
            f"盈利尖峰结构（S_T约等于K处峰值），负Gamma敞口<br/>"
            f"数据区间：{stats['date_start']} — {stats['date_end']}（{stats['n_days']} 个交易日）<br/>"
            f"报告生成时间：{report_date}<br/>"
            f"分析时间戳：{analysis_time_str}（算法版本 {analysis_version}）<br/>"
            f"合约过滤：symbol_near LIKE '{symbol_filter or '无'}' | 方向：{call_put or 'C'}<br/>"
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
            f"共 {stats['n_days']} 个交易日、{stats['n_combos']} 个候选日历价差组合"
            f"（配对规则：近月剩余 7~45 天 × 远月间隔不超过 95 天 × 行权价 ATM±2 档，"
            f"同行权价跨月配对）。<br/>"
            f"最新交易日 {stats['latest_date']}：现货价 {stats['spot']:.4g}，"
            f"{stats['n_combos_latest']} 个候选组合，近月 IV 均值 {stats['iv_near_mean']*100:.1f}% vs "
            f"远月 {stats['iv_far_mean']*100:.1f}%（期限结构差 {stats['ivs_pct_mean']:+.2f} 个 vol 点），"
            f"平均净支出 {stats['nd_mean']:.4g} 元/单位（占现价 {stats['nd_pct_mean']:.2f}%，"
            f"即平均最大亏损），平均月份间隔 {stats['gap_mean']:.0f} 天，"
            f"平均尖峰最大盈利 {stats['mp_mean']:.4g}，平均胜率 {stats['wp_mean']:.2f}，"
            f"平均净 Delta {stats['net_delta_mean']:+.3f}（准中性），"
            f"最近近月到期 {stats['days_near_min']:.0f} 天。"
        )
        story.append(Paragraph(overview_text, styles['normal']))
        story.append(PageBreak())

        # ===== 二、最新交易日组合总览 =====
        story.append(Paragraph(f'二、最新交易日（{latest_date}）候选组合总览（按评分排名）',
                               styles['h1']))
        header, rows = self._build_latest_table_data(latest)
        n_cols = len(header)
        name_w = 120
        rest_w = (page_width - name_w - 62) / (n_cols - 2)
        col_widths = [name_w] + [rest_w] * (n_cols - 2) + [62]
        story.append(self._make_table(header, rows, col_widths))
        story.append(Spacer(1, 0.08 * inch))
        story.append(Paragraph(
            '注：组合=近月/远月@K（同行权价跨月）；净支出 D = C_far-C_near（最大亏损，亏损封顶）；'
            '期限差vol点 = (IV_near-IV_far)×100（正值=近贵远贱，正期望入场条件）；'
            '最大盈利 = 近月到期日 S_T 网格数值解（尖峰，S_T 约等于 K 处）；'
            '下/上平衡% = (平衡点-S0)/S0×100（数值解，区间内即盈利）；'
            '胜率 ≈ P(V(S_T)>0)（近月到期日 S_T 对数正态权重数值积分，σ=IV_near）；'
            '期望值 = (C_near-BS_near)+(BS_far-C_far)（近月卖贵+远月买便宜）；'
            '评分 = 期望值/净支出；排名按同日评分降序（1=最优）。',
            styles['table_note']))
        story.append(PageBreak())

        # ===== 三~十二、图表（各配数字说明） =====
        chart_sections = []
        if chart_buffers.get('chart1'):
            chart_sections.append(('chart1', '图1：现货价格 + 各组合净支出',
                                   f"最新现货 {stats['spot']:.4g}，平均净支出 "
                                   f"{stats['nd_mean']:.4g} 元/单位（即最大亏损）。"
                                   f"净支出随远月月份拉远而增大（更多时间价值差）、"
                                   f"随 IV 期限结构收敛而收窄——D 同时是成本与封顶亏损，"
                                   f"是本策略风险预算的全部。"))
        if chart_buffers.get('chart2'):
            chart_sections.append(('chart2', '图2：近月IV vs 远月IV',
                                   f"实线为近月 IV（均值 {stats['iv_near_mean']*100:.1f}%），"
                                   f"虚线为远月 IV（均值 {stats['iv_far_mean']*100:.1f}%）。"
                                   f"两线之差即期限结构：近月在上=事件溢价集中在近月"
                                   f"（卖近买远的正期望条件）；近月在下=倒挂，"
                                   f"远月更贵属 reverse calendar 场景。"))
        if chart_buffers.get('chart3'):
            chart_sections.append(('chart3', '图3：IV期限结构差',
                                   f"最新平均期限结构差 {stats['ivs_pct_mean']:+.2f} 个 vol 点。"
                                   f"+1 个 vol 点以上为显著正价差（STRONG_BUY 的结构条件），"
                                   f"0 附近为平坦（结构无优势），负值为倒挂（本策略回避）。"
                                   f"期限结构是日历价差的灵魂指标——它决定了'卖近买远'"
                                   f"是否在定价层面占优。"))
        if chart_buffers.get('chart4'):
            chart_sections.append(('chart4', '图4：胜率 + 期望值',
                                   f"最新平均胜率 {stats['wp_mean']:.2f}（尖峰结构的概率刻画："
                                   f"近月到期日 S_T 落入盈亏平衡区间内的概率）。"
                                   f"日历价差胜率通常 0.4~0.6（介于买方策略与卖方策略之间）；"
                                   f"虚线期望值为正说明'近月卖贵+远月买便宜'双腿定价均占优。"))
        if chart_buffers.get('chart5'):
            chart_sections.append(('chart5', '图5：1σ预期波动 vs 净支出',
                                   "实线为近月 1σ 预期波动（近月到期分布半径），"
                                   "虚线为净支出占现价。尖峰盈利区间需覆盖近月正常波动"
                                   "才有统计优势——盈亏平衡区间宽度应与 1σ 波动对比评估"
                                   "（图6 的平衡点偏离 vs 本图波动半径）。"))
        if chart_buffers.get('chart6'):
            best = stats['best']
            if best is not None:
                note = (f"红色实线为组合在近月到期日的价值曲线（尖峰形）："
                        f"S_T 约等于 K={best['exercise_price']:.4g} 处盈利峰值 "
                        f"+{self._fmt(best.get('max_profit'), '{:.4g}')}，"
                        f"双侧收敛至 -D={best['net_debit']:.4g}（亏损封顶）。"
                        f"蓝虚线为远月腿的 BS 残值曲线（IV_far="
                        f"{best['implied_vol_far']*100:.1f}%，近月到期后剩余"
                        f"{best['month_gap_days']:.0f} 天）——远月腿不能按到期 payoff 计算，"
                        f"这正是日历价差与同月策略族的计算本质差异；"
                        f"橙虚线为近月腿 payoff（S_T 超过 K 后线性下行）。"
                        f"红点为双侧盈亏平衡点（数值解）。")
            else:
                note = "红实线为近月到期日组合价值曲线：尖峰盈利 + 双侧亏损封顶 -D。"
            chart_sections.append(('chart6', '图6：近月到期日组合价值曲线（三线图，评分最优组合）', note))
        if chart_buffers.get('chart7'):
            chart_sections.append(('chart7', '图7：多情景到期盈亏（最优组合 vs 买现货）',
                                   "横轴为情景因子（0.85×S0~1.15×S0，情景日=近月到期日）。"
                                   "日历价差线（红）中部隆起（尖峰盈利区）、"
                                   "两端收敛至 -D（亏损封顶）；买现货线（灰虚线）方向单一。"
                                   "与卖方策略的'两端无上限亏损'不同——"
                                   "本策略极端行情下的损失是确定的、可预算的。"))
        if chart_buffers.get('chart8'):
            chart_sections.append(('chart8', '图8：组合有效前沿（胜率 vs 评分）',
                                   "每个点为一个候选组合（标注 近/远月@K），颜色为期限结构差，"
                                   "红星为评分最优。绿点（期限差为正）且胜率居中偏高的组合"
                                   "是结构与概率双重占优的候选。"))
        if chart_buffers.get('chart9'):
            chart_sections.append(('chart9', '图9：Top5 组合评分演变',
                                   "评分 = 期望值/净支出，衡量'期限结构+定价偏差'的综合占优程度。"
                                   "评分持续为正且稳定的组合是滚动持有候选；"
                                   "评分跳水通常意味着期限结构收敛（结构优势消退）"
                                   "或远月 IV 骤升（远月买贵了）。"))
        if chart_buffers.get('chart10'):
            chart_sections.append(('chart10', '图10：净 Theta / 净 Vega（结构敞口）',
                                   f"最新平均净 Theta = +{stats['net_theta_mean']:.5f} 元/单位/日"
                                   f"（近月衰减快于远月——时间是朋友）；"
                                   f"净 Vega（虚线）为正：IV 整体上行受益、"
                                   f"下行受损（买远月波动率）。注意两种利好不要混淆："
                                   f"期限结构走阔（近远 IV 差扩大）是结构性利好，"
                                   f"IV 整体崩塌对净 vega 为正的本策略是伤害——"
                                   f"只有近月 IV 涨、远月 IV 不涨的'期限结构走阔'"
                                   f"才是完美情景。"))

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
                ['组合', 'K', '评分', '信号', '信号原因'],
                detail_rows, [130, 60, 55, 70, page_width - 335], font_size=6.5))
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
            "策略定义：卖出近月认购 Call(K, T_near) + 买入远月认购 Call(K, T_far)，"
            "同行权价同方向跨月（Call Calendar 基线；Put 版本由平价关系冗余，未单列）。"
            "净支出 D = C_far-C_near，即最大亏损（亏损封顶，买方结构）。<br/>"
            "近月到期日组合价值 V(S_T) = C_near - max(0,S_T-K) + BS_call(S_T) - C_far："
            "远月腿在近月到期日仍存活，用 BS 残值定价（IV_far + 远月剩余期限）——"
            "这是与同月策略族（到期 payoff 封闭解）的计算本质差异，"
            "因此最大盈利/盈亏平衡/胜率均为数值解。<br/>"
            "IV期限结构差 iv_term_spread = IV_near - IV_far（小数，+0.01 = 1 个 vol 点）："
            "正值=近贵远贱，是卖近买远的正期望入场条件；负值=倒挂（reverse calendar 场景）。<br/>"
            "Theta时间差 theta_differential = |Theta_near|-|Theta_far|："
            "正值=近月衰减快于远月（结构收益来源确认）。<br/>"
            "最大盈利 max_profit：近月到期日 S_T 网格（0.8~1.2 倍现货，81 点）数值解，"
            "尖峰位于 S_T 约等于 K 处（近月归零+远月残值最大）。<br/>"
            "双侧盈亏平衡点：组合价值曲线与 0 的交点（线性插值，数值解）。<br/>"
            "胜率 win_prob ≈ P(V(S_T)>0)：S_T 网格 × 对数正态权重"
            "（σ=IV_near，期限=近月剩余）数值积分（网格区间外概率忽略，近似）。<br/>"
            "期望值 expected_value = (C_near-BS_near)+(BS_far-C_far)："
            "近月卖贵 + 远月买便宜（双腿均有利定价）；评分 score = 期望值/净支出"
            "（同日排名依据）。<br/>"
            "净 Greeks（买远卖近）：net_delta = delta_far-delta_near（准中性）；"
            "net_gamma = gamma_far-gamma_near（负：现货快速移动时近月腿亏损加速）；"
            "net_theta = theta_far-theta_near（正：时间是朋友）；"
            "net_vega = vega_far-vega_near（正：买远月波动率，IV 整体下行受损）。<br/>"
            "组合配对：近月剩余 7~45 天（&lt;7 天 gamma/pin 风险，&gt;45 天 theta 差不明显）× "
            "远月同 K 更晚月份且间隔不超过 95 天 × 行权价 ATM±2 档，"
            "每日候选全量落库。<br/>"
            "信号规则：STRONG_BUY = 期限结构差≥+1 个 vol 点 且 近月IV分位≥0.60 且 "
            "远月IV分位≤0.40 且 期望值&gt;0；BUY = 期限结构差&gt;0 且 期望值≥0；"
            "CONSIDER = 期限结构差&gt;0（定价未占优）；NEUTRAL = 结构平坦（≥-1 个 vol 点）；"
            "AVOID = 倒挂（&lt;-1 个 vol 点，reverse calendar 场景）。"
            "亏损封顶 = 净支出 D，但负 gamma 与尖峰结构要求严格的到期前管理。"
        )
        story.append(Paragraph(glossary, styles['normal']))
        story.append(Spacer(1, 0.15 * inch))

        # ===== 风险提示 =====
        story.append(Paragraph('十六、风险提示', styles['h1']))
        risk_text = (
            "本报告基于历史期权日线数据与 BS 模型理论值进行量化分析，仅供参考，不构成投资建议。<br/>"
            "模型依赖风险：远月腿价值为 BS 定价估计而非市场成交价——"
            "尖峰最大盈利与盈亏平衡点均为模型数值解，实际平仓价受远月流动性"
            "（买卖价差更宽）影响可能显著偏离。<br/>"
            "负 Gamma 风险：现货快速移动时近月腿亏损加速，临近月到期该效应放大"
            "（pin 风险区），建议到期前 1 周主动了结或展期。<br/>"
            "IV 崩塌风险：净 Vega 为正，IV 整体下行（而非期限结构收敛）将使远月腿贬值"
            "超过近月腿的时间收益。<br/>"
            "分红风险：远月存续期内除息使远月 Call 跌价（Call Calendar 特有敞口），"
            "50ETF 分红季（11~12 月）前后需重新评估。<br/>"
            "胜率为风险中性概率近似（对数正态+网格积分），未包含跳空与肥尾分布，"
            "高估了极端行情下的安全性。<br/>"
            "情景盈亏为近月到期日静态假设（S_T=S0×factor），未考虑路径风险、"
            "保证金占用与交易成本。<br/>"
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
                          event=f"Generating CalendarSpreadStrategyReport: {name}")

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
                logger.warning("数据为空（请先运行 CalendarSpreadStrategyAnalysis 落库），流程终止")
                job_logger.end_job_success(records_processed=0)
                return None

            # Step 2: 清洗 + 图表
            logger.info("Step 2/3: 数据清洗 & 生成图表")
            df = self.clean_data(df)

            chart_buffers = {}
            chart_buffers['chart1'] = self.gen_chart1_spot_net_debit(df)
            chart_buffers['chart2'] = self.gen_chart2_iv_near_far(df)
            chart_buffers['chart3'] = self.gen_chart3_iv_term_spread(df)
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
            logger.info("✅ Calendar Spread 策略分析报告 生成完成！")
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
    report = CalendarSpreadStrategyReport()
    report.run({
        "name": "华夏上证50ETF期权（Calendar Spread）",
        "start_date": "20251222",
        "end_date": CommonParameters.today,
        "call_put": "C",
        "symbol_filter": "510050%",
    })

"""
期权日线指标 报告生成器

流程：
1. 从 tb_tushare_opt_daily_indicator 拉取数据
2. 生成8张图表（不保存PNG，直接嵌入PDF）
3. 生成 PDF 报告（reportlab 风格，参照 MacroEconomicIndicatorReport）
"""

import io
import os
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
                                 PageBreak)
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


class OptDailyIndicatorReport:
    """期权日线指标 报告生成器"""

    REPORT_DIR = os.path.join(CommonParameters.reportPath, 'OptDailyIndicator')
    # 用户指定输出目录
    OUTPUT_DIR = r"E:\tmp"

    CHART_COLORS = [
        '#e74c3c', '#3498db', '#2ecc71', '#9b59b6', '#f39c12',
        '#1abc9c', '#e67e22', '#2980b9', '#c0392b', '#27ae60',
        '#8e44ad', '#d35400', '#16a085', '#2c3e50', '#7f8c8d',
        '#f1c40f', '#00bcd4', '#ff5722', '#795548', '#607d8b',
    ]

    def __init__(self):
        os.makedirs(self.REPORT_DIR, exist_ok=True)
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        self.reportlab_font = self._register_chinese_font()

    def _register_chinese_font(self):
        """注册 reportlab 中文字体（参照 MacroEconomicIndicatorReport）"""
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
        print("%s.%s: %s" % (className, functionName, event))
        logger.info("%s.%s: %s" % (className, functionName, event))

    # ===================== 数据获取 =====================

    def fetch_data(self, start_date=None, end_date=None, ts_code_filter=None, call_put=None):
        """从 ClickHouse 拉取 tb_tushare_opt_daily_indicator 表数据

        Args:
            start_date: 起始日期 YYYYMMDD
            end_date: 截止日期 YYYYMMDD
            ts_code_filter: 合约代码过滤（LIKE），如 'HO2612%'
            call_put: 行权方向 'C'/'P'，None 不过滤

        Returns:
            pd.DataFrame
        """
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName="fetch_data",
                          event="Fetching data from tb_tushare_opt_daily_indicator")

        where_clauses = []
        if start_date:
            where_clauses.append(f"trade_date >= '{start_date}'")
        if end_date:
            where_clauses.append(f"trade_date <= '{end_date}'")
        if ts_code_filter:
            where_clauses.append(f"ts_code LIKE '{ts_code_filter}'")
        if call_put:
            where_clauses.append(f"call_put = '{call_put}'")

        where_str = " AND ".join(where_clauses) if where_clauses else "1=1"
        sql = f"""
        SELECT *
        FROM indexsysdb.tb_tushare_opt_daily_indicator
        WHERE {where_str}
        ORDER BY trade_date, ts_code
        """
        logger.info(f"SQL:\n{sql}")
        df = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        logger.info(f"Fetched {len(df)} rows, {len(df.columns)} columns")
        return df

    def clean_data(self, df):
        """数据清洗：类型转换、排序"""
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName="clean_data",
                          event="Cleaning data")

        # 数值列转换
        numeric_cols = [
            'spot_price', 'close', 'implied_vol', 'bs_theoretical_price',
            'delta', 'gamma', 'vega', 'theta', 'rho',
            'exercise_price', 'pre_close', 'pre_settle', 'settle',
            'open', 'high', 'low', 'vol', 'amount', 'oi',
            'mtm_pnl_close', 'mtm_pnl_settle', 'point_change', 'pct_change',
            'turnover_ratio', 'avg_unit_price',
            'years_to_maturity_calendar', 'years_to_maturity_trading',
            'moneyness_log', 'risk_free_rate',
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        if 'days_to_maturity' in df.columns:
            df['days_to_maturity'] = pd.to_numeric(df['days_to_maturity'], errors='coerce').astype('Int64')

        # 排序
        df = df.sort_values(['ts_code', 'trade_date']).reset_index(drop=True)

        # trade_date 转 datetime 方便画图
        df['trade_date_dt'] = pd.to_datetime(df['trade_date'], format='%Y%m%d', errors='coerce')

        return df

    # ===================== 图表通用工具 =====================

    def _fig_to_bytesio(self, fig, dpi=180):
        """matplotlib figure → BytesIO"""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        return buf

    def _build_legend(self, ax, n_items, ncol_max=6):
        """统一图例（居中上方）"""
        ncol = min(n_items, ncol_max)
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12),
                  fontsize=7, ncol=ncol, frameon=True, borderaxespad=0.5,
                  handlelength=1.2)

    def _add_end_labels(self, ax, ts_codes, series_dict, y_col, colors=None,
                         x_pad_frac=0.10, label_fontsize=7, single_label=None):
        """在每条折线最右端打上 ts_code 标签（颜色与线一致），并扩展右侧空间

        Args:
            ax: matplotlib axes（数据坐标系，用于定位标签位置）
            ts_codes: 合约代码列表（按颜色索引顺序）
            series_dict: {ts_code: DataFrame（以 trade_date_dt 为索引）}
            y_col: 用于取最后一个点的列名
            colors: 自定义颜色列表，默认使用 self.CHART_COLORS
            x_pad_frac: 右侧扩展比例，给标签留出空间
            label_fontsize: 标签字号
            single_label: 若提供，则所有线共用此单一标签（用于 spot_price 等）
        """
        if colors is None:
            colors = self.CHART_COLORS

        # 先扩展 xlim 给标签留位（在画标签之前做，确保标签落在 axes 内）
        xlim = ax.get_xlim()
        if xlim[1] > xlim[0]:
            ax.set_xlim(xlim[0], xlim[1] + (xlim[1] - xlim[0]) * x_pad_frac)

        for idx, ts_code in enumerate(ts_codes):
            if y_col not in series_dict[ts_code].columns:
                continue
            sub = series_dict[ts_code][y_col].dropna()
            if len(sub) == 0:
                continue
            color = colors[idx % len(colors)]
            x_last = sub.index[-1]
            y_last = sub.iloc[-1]
            label_text = single_label if single_label else ts_code
            ax.annotate(
                label_text,
                xy=(x_last, y_last),
                xytext=(6, 0),
                textcoords='offset points',
                color=color,
                fontsize=label_fontsize,
                fontweight='bold',
                va='center',
                ha='left',
                bbox=dict(boxstyle='round,pad=0.18',
                          facecolor='white',
                          edgecolor=color,
                          linewidth=0.5,
                          alpha=0.85),
                zorder=10,
            )

    def _prep_ts_code_data(self, df, value_cols):
        """将 DataFrame 按 ts_code pivot，便于画多条折线

        Returns:
            trade_dates: X 轴日期列表
            ts_codes: 合约代码列表
            series_dict: {ts_code: pd.Series(index=trade_date_dt, values)}
            valid_mask: 哪些 ts_code 在指定列有有效数据
        """
        # 获取唯一的 trade_date 排序
        all_dates = sorted(df['trade_date_dt'].unique())

        ts_codes = sorted(df['ts_code'].unique())
        series_dict = {}
        valid_ts = set()

        for ts_code in ts_codes:
            sub = df[df['ts_code'] == ts_code].set_index('trade_date_dt')
            for col in value_cols:
                if col in sub.columns and sub[col].notna().sum() > 0:
                    # 有至少一个有效值就算有效
                    valid_ts.add(ts_code)
                    break

        # 只为有效的 ts_code 构建 series
        for ts_code in sorted(valid_ts):
            sub = df[df['ts_code'] == ts_code].set_index('trade_date_dt')
            series_dict[ts_code] = sub

        return all_dates, sorted(valid_ts), series_dict

    # ===================== 通用双Y轴图表 =====================

    def _draw_spot_price_on_ax1(self, ax1, df, series_dict, ts_codes):
        """在左轴画 spot_price（一条线），并打上 end label"""
        spot_series = None
        for ts_code in ts_codes:
            sub = series_dict[ts_code]
            if 'spot_price' in sub.columns and sub['spot_price'].notna().sum() > 0:
                spot_series = sub['spot_price']
                break

        if spot_series is not None:
            spot_dates = spot_series.dropna().index.tolist()
            spot_vals = spot_series.dropna().values
            spot_color = '#1a1a2e'
            ax1.plot(spot_dates, spot_vals, color=spot_color, linewidth=2.0,
                     marker='o', markersize=4, alpha=0.9, label='spot_price (标的物)')
            # 右端标签
            spot_ts_code = ts_codes[0] if ts_codes else 'spot_price'
            spot_dict = {spot_ts_code: spot_series.to_frame(name='spot_price')}
            self._add_end_labels(ax1, [spot_ts_code], spot_dict, 'spot_price',
                                  colors=[spot_color], x_pad_frac=0.02,
                                  label_fontsize=8, single_label='spot_price')

    def _gen_dual_y_chart(self, df, y_col, y_col_cn, chart_num, title_prefix=None,
                          extra_y3_col=None, extra_y3_label=None):
        """通用双Y轴折线图模板（可选第三轴）：
        Y1（左轴）= spot_price（一条粗线）
        Y2（右轴）= 各 ts_code 的指定指标列（多条彩色细线）
        Y3（可选外轴）= extra_y3_col（如 risk_free_rate）

        所有折线在最右端打上标签。
        """
        title = title_prefix if title_prefix else f'图{chart_num}：spot_price + 各合约 {y_col_cn}'
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName=f"gen_chart{chart_num}",
                          event=f"Generating chart {chart_num}")

        all_dates, ts_codes, series_dict = self._prep_ts_code_data(df, ['spot_price', y_col])
        y2_ts_codes = [t for t in ts_codes if y_col in series_dict[t].columns
                        and series_dict[t][y_col].notna().sum() > 0]

        if len(ts_codes) == 0:
            logger.warning(f"No valid ts_code for chart {chart_num}, skipping")
            return None

        fig, ax1 = plt.subplots(figsize=(20, 8))
        fig.suptitle(title, fontsize=14, fontweight='bold', color='#1a1a2e')

        # ---- Y1: spot_price ----
        self._draw_spot_price_on_ax1(ax1, df, series_dict, ts_codes)
        ax1.set_ylabel('spot_price (标的物价格)', fontsize=11, color='#1a1a2e')
        ax1.tick_params(axis='y', labelcolor='#1a1a2e')
        ax1.grid(True, alpha=0.3, linestyle='--')

        # ---- Y2: 各 ts_code 的指标 ----
        ax2 = ax1.twinx()
        for idx, ts_code in enumerate(ts_codes):
            sub = series_dict[ts_code]
            if y_col in sub.columns and sub[y_col].notna().sum() > 0:
                series = sub[y_col].dropna()
                color = self.CHART_COLORS[idx % len(self.CHART_COLORS)]
                ax2.plot(series.index.tolist(), series.values,
                         color=color, linewidth=0.8, alpha=0.78,
                         marker='o', markersize=3, label=ts_code)

        ax2.axhline(y=0, color='gray', linewidth=0.5, linestyle='-')
        ax2.set_ylabel(y_col_cn, fontsize=11)
        ax2.tick_params(axis='y')

        # ---- Y3: extra_y3_col (e.g., risk_free_rate) ----
        ax3 = None
        if extra_y3_col and extra_y3_col in df.columns:
            ax3 = ax1.twinx()
            ax3.spines['right'].set_position(('outward', 60))
            ax3.spines['right'].set_color('#e67e22')

            rf_data = df[['trade_date_dt', extra_y3_col]].dropna().drop_duplicates(subset='trade_date_dt')
            rf_data = rf_data.sort_values('trade_date_dt').set_index('trade_date_dt')[extra_y3_col]

            if not rf_data.empty:
                y3_label = extra_y3_label or extra_y3_col
                ax3.plot(rf_data.index.tolist(), rf_data.values,
                         color='#e67e22', linewidth=2.0, alpha=0.9,
                         marker='s', markersize=3, linestyle='--',
                         label=y3_label)

                rf_dict = {y3_label: rf_data.to_frame(name=extra_y3_col)}
                self._add_end_labels(ax3, [y3_label], rf_dict, extra_y3_col,
                                     colors=['#e67e22'], x_pad_frac=0.02,
                                     single_label=y3_label)

            ax3.set_ylabel(y3_label, fontsize=11, color='#e67e22')
            ax3.tick_params(axis='y', labelcolor='#e67e22')

        # ---- 右端标签 ----
        self._add_end_labels(ax2, ts_codes, series_dict, y_col)

        # ---- X 轴格式 ----
        fig.autofmt_xdate(rotation=45, ha='right')

        # ---- 合并图例 ----
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        all_lines = lines1 + lines2
        all_labels = labels1 + labels2
        if ax3 is not None:
            lines3, labels3 = ax3.get_legend_handles_labels()
            all_lines += lines3
            all_labels += labels3
        n_items = len(all_lines)
        ncol = min(n_items, 8)
        ax1.legend(all_lines, all_labels, loc='upper center',
                   bbox_to_anchor=(0.5, -0.12), fontsize=6.5, ncol=ncol,
                   frameon=True, borderaxespad=0.5, handlelength=1.2)

        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    # ===================== 8 张图表（均委托 _gen_dual_y_chart） =====================

    def gen_chart1_spot_and_close(self, df):
        return self._gen_dual_y_chart(df, 'close', 'close (合约收盘价)', chart_num=1,
                                      title_prefix='图1：spot_price + 各合约 收盘价 (close)')

    def gen_chart2_implied_vol(self, df):
        return self._gen_dual_y_chart(df, 'implied_vol', '隐含波动率 (implied_vol)', chart_num=2,
                                      title_prefix='图2：spot_price + 各合约 隐含波动率')

    def gen_chart3_bs_theoretical_price(self, df):
        return self._gen_dual_y_chart(df, 'bs_theoretical_price', 'BS理论价', chart_num=3,
                                      title_prefix='图3：spot_price + 各合约 BS理论价')

    def gen_chart4_delta(self, df):
        return self._gen_dual_y_chart(df, 'delta', 'Delta', chart_num=4,
                                      title_prefix='图4：spot_price + 各合约 Delta')

    def gen_chart5_gamma(self, df):
        return self._gen_dual_y_chart(df, 'gamma', 'Gamma', chart_num=5,
                                      title_prefix='图5：spot_price + 各合约 Gamma')

    def gen_chart6_vega(self, df):
        return self._gen_dual_y_chart(df, 'vega', 'Vega', chart_num=6,
                                      title_prefix='图6：spot_price + 各合约 Vega')

    def gen_chart7_theta(self, df):
        return self._gen_dual_y_chart(df, 'theta', 'Theta', chart_num=7,
                                      title_prefix='图7：spot_price + 各合约 Theta')

    def gen_chart8_rho(self, df):
        return self._gen_dual_y_chart(df, 'rho', 'Rho', chart_num=8,
                                      extra_y3_col='risk_free_rate',
                                      extra_y3_label='risk_free_rate (无风险利率)',
                                      title_prefix='图8：spot_price + 各合约 Rho + risk_free_rate')

    # ===================== 图9：多日隐含波动率微笑演变仪表盘 =====================

    def gen_chart9_ivol_smile_dashboard(self, df, call_put='C'):
        """多日隐含波动率微笑演变 —— 专业交易员三合一仪表盘

        Panel A (左上): 热力图 — X: moneyness (K/S), Y: trade_date, Color: IV%
                       交易台最核心的监控图，一眼看出偏斜变化和波动率聚集
        Panel B (右上): 代表性日期叠加 — 时间渐变着色，观察曲线形态演变
        Panel C (底部):  关键指标时间序列 — ATM IV, 偏斜度, 微笑曲率

        数据来源: tb_tushare_opt_daily_indicator 真实 ClickHouse 数据
        """
        import matplotlib.gridspec as gridspec

        self.writeLogInfo(className=self.__class__.__name__,
                          functionName="gen_chart9_ivol_smile_dashboard",
                          event="Generating IV smile evolution dashboard")

        # ---- Step 0: 数据预处理 ----
        df_sub = df[df['call_put'] == call_put].copy()
        if df_sub.empty:
            logger.warning(f"No data for call_put={call_put}, skipping smile dashboard")
            return None

        # 计算 moneyness
        df_sub['moneyness'] = df_sub['exercise_price'] / df_sub['spot_price']

        # 过滤 moneyness 在合理范围内
        df_sub = df_sub[(df_sub['moneyness'] >= 0.80) & (df_sub['moneyness'] <= 1.20)]
        df_sub = df_sub.dropna(subset=['implied_vol', 'moneyness', 'trade_date_dt'])

        # 获取所有交易日（按时间排序）
        trade_dates = sorted(df_sub['trade_date_dt'].unique())
        if len(trade_dates) < 2:
            logger.warning(f"Insufficient dates ({len(trade_dates)}) for smile dashboard")
            return None
        date_labels = [d.strftime('%m-%d') for d in trade_dates]
        n_days = len(trade_dates)

        # ---- Step 1: 构建规则网格 (moneyness bins × trade_dates) ----
        moneyness_bins = np.linspace(0.85, 1.15, 31)  # 30 个区间
        moneyness_centers = 0.5 * (moneyness_bins[:-1] + moneyness_bins[1:])

        iv_grid = np.full((n_days, len(moneyness_centers)), np.nan)
        for di, dt in enumerate(trade_dates):
            day_data = df_sub[df_sub['trade_date_dt'] == dt]
            for bi in range(len(moneyness_centers)):
                lo, hi = moneyness_bins[bi], moneyness_bins[bi + 1]
                bucket = day_data[(day_data['moneyness'] >= lo) & (day_data['moneyness'] < hi)]
                if len(bucket) > 0:
                    iv_grid[di, bi] = bucket['implied_vol'].median()

        # 对稀疏日期做行内线性插值 + 首尾外推
        for di in range(n_days):
            row = iv_grid[di]
            valid = ~np.isnan(row)
            if valid.sum() >= 2:
                iv_grid[di] = np.interp(np.arange(len(row)),
                                        np.where(valid)[0], row[valid],
                                        left=row[valid][0], right=row[valid][-1])
            elif valid.sum() == 1:
                iv_grid[di, :] = row[valid][0]

        # ---- Step 2: 提取关键指标 ----
        # ATM IV: moneyness 最接近 1.0 的 bin
        atm_idx = np.argmin(np.abs(moneyness_centers - 1.0))
        atm_iv = iv_grid[:, atm_idx]

        # 偏斜度: moneyness 0.90 vs 1.10
        skew_lo_idx = np.argmin(np.abs(moneyness_centers - 0.90))
        skew_hi_idx = np.argmin(np.abs(moneyness_centers - 1.10))
        skew_series = iv_grid[:, skew_lo_idx] - iv_grid[:, skew_hi_idx]

        # 曲率: ATM - avg(0.90, 0.95, 1.05, 1.10)
        curv_indices = [skew_lo_idx, np.argmin(np.abs(moneyness_centers - 0.95)),
                        np.argmin(np.abs(moneyness_centers - 1.05)), skew_hi_idx]
        curvature_series = atm_iv - np.nanmean(iv_grid[:, curv_indices], axis=1)

        # ---- Step 3: 绘图 ----
        fig = plt.figure(figsize=(26, 17))
        gs = gridspec.GridSpec(2, 2, height_ratios=[1.1, 1], hspace=0.32, wspace=0.28,
                               left=0.05, right=0.97, top=0.93, bottom=0.07)

        ax_heatmap = fig.add_subplot(gs[0, 0])
        ax_overlay = fig.add_subplot(gs[0, 1])
        ax_metrics = fig.add_subplot(gs[1, :])

        BULL_COLOR = '#1a5276'
        BEAR_COLOR = '#c0392b'
        HEAT_CMAP = plt.cm.viridis

        # ---- Panel A: 热力图 ----
        vmin_val = max(5.0, np.nanmin(iv_grid) * 100 * 0.8)
        vmax_val = min(80.0, np.nanmax(iv_grid) * 100 * 1.2)
        im = ax_heatmap.pcolormesh(moneyness_centers, np.arange(n_days),
                                    iv_grid * 100, cmap=HEAT_CMAP,
                                    shading='auto', vmin=vmin_val, vmax=vmax_val)
        cbar = plt.colorbar(im, ax=ax_heatmap, shrink=0.8, pad=0.02)
        cbar.set_label('隐含波动率 (%)', fontsize=11, fontweight='bold')

        ax_heatmap.axvline(x=1.0, color='white', linestyle='--', linewidth=1.0, alpha=0.6)
        ax_heatmap.text(1.0, -1.2, 'ATM', color='white', fontsize=8, ha='center', va='bottom')

        ytick_step = max(1, n_days // 25)
        yticks_pos = np.arange(0, n_days, ytick_step)
        ax_heatmap.set_yticks(yticks_pos)
        ax_heatmap.set_yticklabels([date_labels[i] for i in yticks_pos], fontsize=7)
        ax_heatmap.set_xticks([0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15])
        ax_heatmap.set_xticklabels(['0.85', '0.90', '0.95', '1.00', '1.05', '1.10', '1.15'], fontsize=8)
        ax_heatmap.set_xlabel('Moneyness (K/S)', fontsize=12, fontweight='bold')
        ax_heatmap.set_ylabel('交易日（越晚越靠上）', fontsize=12, fontweight='bold')
        ax_heatmap.set_title(f'Panel A: IV Smile 热力图 ({call_put}期权)\n颜色越亮 IV越高 | 横看=微笑曲线 | 竖看=IV时序',
                             fontsize=13, fontweight='bold', pad=10)

        # ---- Panel B: 选取代表性日期叠加 ----
        n_select = min(7, n_days)
        selected = np.linspace(0, n_days - 1, n_select, dtype=int)
        colors_overlay = plt.cm.coolwarm(np.linspace(0.15, 0.85, n_select))

        for idx, (di, c) in enumerate(zip(selected, colors_overlay)):
            alpha_val = 0.50 + 0.50 * (idx / max(n_select - 1, 1))
            lw = 1.2 + 2.0 * (idx / max(n_select - 1, 1))
            ax_overlay.plot(moneyness_centers, iv_grid[di] * 100,
                            color=c, linewidth=lw, alpha=alpha_val,
                            label=f'{date_labels[di]} ({atm_iv[di]*100:.1f}%)')

        ax_overlay.axvline(x=1.0, color='gray', linestyle='--', linewidth=0.8, alpha=0.4)
        ax_overlay.set_xlabel('Moneyness (K/S)', fontsize=12, fontweight='bold')
        ax_overlay.set_ylabel('隐含波动率 (%)', fontsize=12, fontweight='bold')
        ax_overlay.set_title(f'Panel B: 代表性日期微笑曲线叠加 ({call_put}期权)',
                             fontsize=13, fontweight='bold', pad=10)
        ax_overlay.legend(fontsize=7.5, loc='upper left', ncol=2, framealpha=0.75)
        ax_overlay.grid(True, linestyle='--', alpha=0.25)

        # ---- Panel C: 关键指标时间序列 ----
        ax_atm = ax_metrics
        ax_skew = ax_metrics.twinx()

        ax_atm.fill_between(np.arange(n_days), atm_iv * 100, alpha=0.12, color=BULL_COLOR)
        ax_atm.plot(np.arange(n_days), atm_iv * 100,
                    color=BULL_COLOR, linewidth=2.2, marker='o', markersize=3,
                    label='ATM 隐含波动率 (%)', zorder=5)

        skew_plot = -skew_series * 100  # 转正: 越大=偏斜越严重
        ax_skew.fill_between(np.arange(n_days), skew_plot, alpha=0.10, color=BEAR_COLOR)
        ax_skew.plot(np.arange(n_days), skew_plot,
                     color=BEAR_COLOR, linewidth=2.2, marker='s', markersize=3,
                     linestyle='--', label='偏斜度 (90%−110% IV差, %pts)', zorder=4)

        ax_skew.plot(np.arange(n_days), curvature_series * 100 * 3,
                     color='#e67e22', linewidth=1.5, marker='^', markersize=3,
                     linestyle=':', label='曲率指标 (×3)', zorder=3, alpha=0.7)

        xtick_step_metrics = max(1, n_days // 20)
        ax_atm.set_xticks(np.arange(0, n_days, xtick_step_metrics))
        ax_atm.set_xticklabels([date_labels[i] for i in range(0, n_days, xtick_step_metrics)], fontsize=7)
        ax_atm.set_xlabel('交易日', fontsize=12, fontweight='bold')
        ax_atm.set_ylabel('ATM 隐含波动率 (%)', fontsize=11, fontweight='bold', color=BULL_COLOR)
        ax_skew.set_ylabel('偏斜度 / 曲率', fontsize=11, fontweight='bold', color=BEAR_COLOR)
        ax_atm.tick_params(axis='y', labelcolor=BULL_COLOR)
        ax_skew.tick_params(axis='y', labelcolor=BEAR_COLOR)

        lines1, labels1 = ax_atm.get_legend_handles_labels()
        lines2, labels2 = ax_skew.get_legend_handles_labels()
        ax_atm.legend(lines1 + lines2, labels1 + labels2, loc='upper left',
                      fontsize=9, framealpha=0.75)

        ax_atm.set_title('Panel C: 微笑关键指标时间序列 — ATM IV / 偏斜度 / 曲率',
                         fontsize=13, fontweight='bold', pad=10)
        ax_atm.grid(True, linestyle='--', alpha=0.25)

        # ---- 总标题 ----
        fig.suptitle(f'隐含波动率微笑曲线多日演变 ({call_put}期权) — 数据来源: tb_tushare_opt_daily_indicator',
                     fontsize=16, fontweight='bold', y=0.98)

        buf = self._fig_to_bytesio(fig, dpi=180)
        plt.close(fig)
        return buf

    # ===================== 图11~18：行权价-指标双Y轴（trade_date为系列） =====================

    def _gen_exercise_price_dual_y_chart(self, df, y1_col, y1_label, y2_col, y2_label,
                                          chart_num, title_prefix=None, call_put=None):
        """通用 exercise_price 双Y轴图

        X轴: exercise_price（行权价）
        Y1轴: 指标列（如 implied_vol, delta, gamma...）
        Y2轴: 辅助列（如 vol, d2, nd2）
        系列: 每个 trade_date 一条不同颜色的折线
        """
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName=f"_gen_exercise_price_chart{chart_num}",
                          event=f"Generating exercise_price dual-Y chart {chart_num}: {y1_label} + {y2_label}")

        df_work = df.copy()
        if call_put:
            df_work = df_work[df_work['call_put'] == call_put]
        if df_work.empty:
            logger.warning(f"No data for chart {chart_num}, skipping")
            return None

        # 按 trade_date 分组
        trade_dates = sorted(df_work['trade_date_dt'].unique())
        if len(trade_dates) < 1:
            logger.warning(f"Insufficient trade_dates for chart {chart_num}")
            return None

        n_dates = len(trade_dates)
        date_labels = [d.strftime('%m-%d') for d in trade_dates]
        colors = plt.cm.tab20(np.linspace(0, 1, max(n_dates, 20)))[:n_dates] if n_dates <= 20 else \
                 plt.cm.viridis(np.linspace(0.1, 0.9, n_dates))

        title = title_prefix if title_prefix else f'图{chart_num}：exercise_price vs {y1_label} + {y2_label}（按trade_date）'

        fig, ax1 = plt.subplots(figsize=(24, 10))
        fig.suptitle(title, fontsize=14, fontweight='bold', color='#1a1a2e')

        for di, dt in enumerate(trade_dates):
            day_data = df_work[df_work['trade_date_dt'] == dt].sort_values('exercise_price')
            if day_data.empty:
                continue
            x_vals = day_data['exercise_price'].values
            y1_vals = day_data[y1_col].values

            color = colors[di]
            alpha_val = max(0.5, 0.90 - 0.02 * abs(di - n_dates // 2))
            lw = 1.0 + 1.0 * (di / max(n_dates - 1, 1))

            ax1.plot(x_vals, y1_vals, color=color, linewidth=lw, alpha=alpha_val,
                     marker='o', markersize=2.5, label=date_labels[di])

        ax1.set_xlabel('行权价 (exercise_price)', fontsize=12, fontweight='bold')
        ax1.set_ylabel(y1_label, fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.25, linestyle='--')

        # ---- Y2 轴 ----
        ax2 = ax1.twinx()
        for di, dt in enumerate(trade_dates):
            day_data = df_work[df_work['trade_date_dt'] == dt].sort_values('exercise_price')
            if day_data.empty or y2_col not in day_data.columns:
                continue
            x_vals = day_data['exercise_price'].values
            y2_vals = day_data[y2_col].values

            color = colors[di]
            ax2.plot(x_vals, y2_vals, color=color, linewidth=0.7, alpha=0.45,
                     linestyle='--', marker='s', markersize=2)

        ax2.set_ylabel(y2_label, fontsize=12, fontweight='bold')

        # ---- 右端标签（在 Y1 轴各线上标注 trade_date） ----
        xlim = ax1.get_xlim()
        if xlim[1] > xlim[0]:
            ax1.set_xlim(xlim[0], xlim[1] + (xlim[1] - xlim[0]) * 0.12)

        for di, dt in enumerate(trade_dates):
            day_data = df_work[df_work['trade_date_dt'] == dt].sort_values('exercise_price')
            if day_data.empty or y1_col not in day_data.columns:
                continue
            y1_series = day_data[y1_col].dropna()
            x_series = day_data.loc[y1_series.index, 'exercise_price']
            if len(y1_series) == 0:
                continue
            color = colors[di]
            label_text = date_labels[di]
            ax1.annotate(
                label_text,
                xy=(x_series.iloc[-1], y1_series.iloc[-1]),
                xytext=(6, 0),
                textcoords='offset points',
                color=color,
                fontsize=7,
                fontweight='bold',
                va='center',
                ha='left',
                bbox=dict(boxstyle='round,pad=0.18',
                          facecolor='white',
                          edgecolor=color,
                          linewidth=0.5,
                          alpha=0.85),
                zorder=10,
            )

        # ---- 图例 ----
        ncol = min(n_dates, 10)
        ax1.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12),
                   fontsize=6, ncol=ncol, frameon=True, borderaxespad=0.5,
                   handlelength=1.0, columnspacing=0.6)

        # ---- Y1/Y2 零线 ----
        if y1_col in ('delta', 'gamma', 'theta', 'rho', 'd1', 'd2', 'nd1', 'nd2'):
            ax1.axhline(y=0, color='gray', linewidth=0.5, linestyle='-', alpha=0.3)

        fig.autofmt_xdate(rotation=45, ha='right')
        plt.tight_layout()
        buf = self._fig_to_bytesio(fig, dpi=150)
        plt.close(fig)
        return buf

    def gen_chart11_exercise_price_iv_vol(self, df):
        return self._gen_exercise_price_dual_y_chart(
            df, 'implied_vol', '隐含波动率 (implied_vol)', 'vol', '成交量 (vol)',
            chart_num=11, call_put='C',
            title_prefix='图11：行权价 vs 隐含波动率(Y1) + 成交量(Y2) — 按trade_date (Call)')

    def gen_chart12_exercise_price_delta_vol(self, df):
        return self._gen_exercise_price_dual_y_chart(
            df, 'delta', 'Delta', 'vol', '成交量 (vol)',
            chart_num=12, call_put='C',
            title_prefix='图12：行权价 vs Delta(Y1) + 成交量(Y2) — 按trade_date (Call)')

    def gen_chart13_exercise_price_gamma_vol(self, df):
        return self._gen_exercise_price_dual_y_chart(
            df, 'gamma', 'Gamma', 'vol', '成交量 (vol)',
            chart_num=13, call_put='C',
            title_prefix='图13：行权价 vs Gamma(Y1) + 成交量(Y2) — 按trade_date (Call)')

    def gen_chart14_exercise_price_vega_vol(self, df):
        return self._gen_exercise_price_dual_y_chart(
            df, 'vega', 'Vega', 'vol', '成交量 (vol)',
            chart_num=14, call_put='C',
            title_prefix='图14：行权价 vs Vega(Y1) + 成交量(Y2) — 按trade_date (Call)')

    def gen_chart15_exercise_price_theta_vol(self, df):
        return self._gen_exercise_price_dual_y_chart(
            df, 'theta', 'Theta', 'vol', '成交量 (vol)',
            chart_num=15, call_put='C',
            title_prefix='图15：行权价 vs Theta(Y1) + 成交量(Y2) — 按trade_date (Call)')

    def gen_chart16_exercise_price_rho_vol(self, df):
        return self._gen_exercise_price_dual_y_chart(
            df, 'rho', 'Rho', 'vol', '成交量 (vol)',
            chart_num=16, call_put='C',
            title_prefix='图16：行权价 vs Rho(Y1) + 成交量(Y2) — 按trade_date (Call)')

    def gen_chart17_exercise_price_d1_d2(self, df):
        return self._gen_exercise_price_dual_y_chart(
            df, 'd1', 'd1', 'd2', 'd2',
            chart_num=17, call_put='C',
            title_prefix='图17：行权价 vs d1(Y1) + d2(Y2) — 按trade_date (Call)')

    def gen_chart18_exercise_price_nd1_nd2(self, df):
        return self._gen_exercise_price_dual_y_chart(
            df, 'nd1', 'N(d1)', 'nd2', 'N(d2)',
            chart_num=18, call_put='C',
            title_prefix='图18：行权价 vs N(d1)(Y1) + N(d2)(Y2) — 按trade_date (Call)')

    # ===================== 图19~22：trade_date-X轴 exercise_price为系列 单Y轴 =====================

    def _gen_trade_date_x_single_y_chart(self, df, y_col, y_label,
                                          chart_num, title_prefix=None, call_put=None):
        """通用 trade_date 为 X 轴单Y图

        X轴: trade_date（交易日）
        系列: 每个 exercise_price 一条不同颜色的折线
        Y轴: 指标列（如 d1, d2, nd1, nd2）
        每条线最右端标上 exercise_price 标签
        """
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName=f"_gen_trade_date_x_chart{chart_num}",
                          event=f"Generating trade_date X-axis chart {chart_num}: {y_label}")

        df_work = df.copy()
        if call_put:
            df_work = df_work[df_work['call_put'] == call_put]
        if df_work.empty:
            logger.warning(f"No data for chart {chart_num}, skipping")
            return None

        exercise_prices = sorted(df_work['exercise_price'].dropna().unique())
        if len(exercise_prices) < 1:
            logger.warning(f"Insufficient exercise_prices for chart {chart_num}")
            return None

        n_prices = len(exercise_prices)
        colors = plt.cm.tab20(np.linspace(0, 1, max(n_prices, 20)))[:n_prices] if n_prices <= 20 else \
                 plt.cm.viridis(np.linspace(0.1, 0.9, n_prices))

        title = title_prefix if title_prefix else f'图{chart_num}：trade_date vs {y_label}（按exercise_price）'

        fig, ax = plt.subplots(figsize=(24, 10))
        fig.suptitle(title, fontsize=14, fontweight='bold', color='#1a1a2e')

        # 存储每条线的右端点，用于 end label
        end_points = []  # (x_last, y_last, exercise_price_label, color)

        for pi, ep in enumerate(exercise_prices):
            ep_data = df_work[df_work['exercise_price'] == ep].sort_values('trade_date_dt')
            if ep_data.empty:
                continue
            x_dates = ep_data['trade_date_dt'].values
            y_vals = ep_data[y_col].values

            color = colors[pi]
            alpha_val = max(0.5, 0.90 - 0.02 * abs(pi - n_prices // 2))
            lw = 1.0 + 1.0 * (pi / max(n_prices - 1, 1))

            label_text = f"{int(ep)}"
            ax.plot(x_dates, y_vals, color=color, linewidth=lw, alpha=alpha_val,
                    marker='o', markersize=3, label=label_text)

            # 记录右端点
            valid_mask = ~np.isnan(y_vals)
            if valid_mask.sum() > 0:
                end_points.append((
                    x_dates[valid_mask][-1],
                    y_vals[valid_mask][-1],
                    label_text,
                    color
                ))

        ax.set_xlabel('交易日 (trade_date)', fontsize=12, fontweight='bold')
        ax.set_ylabel(y_label, fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.25, linestyle='--')

        # ---- 零线 ----
        if y_col in ('delta', 'gamma', 'theta', 'rho', 'd1', 'd2', 'nd1', 'nd2'):
            ax.axhline(y=0, color='gray', linewidth=0.5, linestyle='-', alpha=0.3)

        # ---- 右端标签（标注 exercise_price） ----
        xlim = ax.get_xlim()
        if xlim[1] > xlim[0]:
            ax.set_xlim(xlim[0], xlim[1] + (xlim[1] - xlim[0]) * 0.12)

        for x_last, y_last, label_text, color in end_points:
            ax.annotate(
                label_text,
                xy=(x_last, y_last),
                xytext=(6, 0),
                textcoords='offset points',
                color=color,
                fontsize=7,
                fontweight='bold',
                va='center',
                ha='left',
                bbox=dict(boxstyle='round,pad=0.18',
                          facecolor='white',
                          edgecolor=color,
                          linewidth=0.5,
                          alpha=0.85),
                zorder=10,
            )

        # ---- 图例 ----
        ncol = min(n_prices, 10)
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12),
                   fontsize=6, ncol=ncol, frameon=True, borderaxespad=0.5,
                   handlelength=1.0, columnspacing=0.6)

        fig.autofmt_xdate(rotation=45, ha='right')
        plt.tight_layout()
        buf = self._fig_to_bytesio(fig, dpi=150)
        plt.close(fig)
        return buf

    def gen_chart19_trade_date_x_d1(self, df):
        return self._gen_trade_date_x_single_y_chart(
            df, 'd1', 'd1',
            chart_num=19, call_put='C',
            title_prefix='图19：交易日 vs d1 — 按行权价exercise_price为系列 (Call)')

    def gen_chart20_trade_date_x_d2(self, df):
        return self._gen_trade_date_x_single_y_chart(
            df, 'd2', 'd2',
            chart_num=20, call_put='C',
            title_prefix='图20：交易日 vs d2 — 按行权价exercise_price为系列 (Call)')

    def gen_chart21_trade_date_x_nd1(self, df):
        return self._gen_trade_date_x_single_y_chart(
            df, 'nd1', 'N(d1)',
            chart_num=21, call_put='C',
            title_prefix='图21：交易日 vs N(d1) — 按行权价exercise_price为系列 (Call)')

    def gen_chart22_trade_date_x_nd2(self, df):
        return self._gen_trade_date_x_single_y_chart(
            df, 'nd2', 'N(d2)',
            chart_num=22, call_put='C',
            title_prefix='图22：交易日 vs N(d2) — 按行权价exercise_price为系列 (Call)')

    # ===================== PDF 报告生成 =====================

    def _build_pdf_styles(self):
        """构建 PDF 样式"""
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'ReportTitle', parent=styles['Heading1'],
            fontSize=22, leading=30, alignment=1,
            fontName=self.reportlab_font, spaceAfter=24,
        )
        heading1 = ParagraphStyle(
            'Heading1Style', parent=styles['Heading1'],
            fontSize=16, leading=22, fontName=self.reportlab_font,
            spaceAfter=12, spaceBefore=12,
        )
        heading2 = ParagraphStyle(
            'Heading2Style', parent=styles['Heading2'],
            fontSize=13, leading=18, fontName=self.reportlab_font,
            spaceAfter=8, spaceBefore=8,
        )
        normal = ParagraphStyle(
            'NormalStyle', parent=styles['Normal'],
            fontSize=10, leading=15, fontName=self.reportlab_font,
        )
        cover_info = ParagraphStyle(
            'CoverInfo', parent=styles['Normal'],
            fontSize=13, leading=20, alignment=1,
            fontName=self.reportlab_font, textColor=colors.HexColor('#333333'),
        )
        return {
            'title': title_style,
            'h1': heading1,
            'h2': heading2,
            'normal': normal,
            'cover_info': cover_info,
        }

    def _generate_pdf_report(self, df, chart_buffers,
                              start_date=None, end_date=None, ts_code_filter=None, call_put=None):
        """生成完整 PDF 报告"""
        styles = self._build_pdf_styles()

        report_date = datetime.now().strftime('%Y-%m-%d %H:%M')
        now_ts = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 文件名基于日期范围 + 产品标识
        filter_tag = ts_code_filter.replace('%', '') if ts_code_filter else 'all'
        cp_tag = f"_{call_put}" if call_put else ""
        date_tag = f"{start_date}-{end_date}" if start_date and end_date else "custom"
        pdf_path = os.path.join(
            self.OUTPUT_DIR,
            f"OptDailyIndicator_{filter_tag}{cp_tag}_{date_tag}_{now_ts}.pdf"
        )

        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=landscape(A4),
            rightMargin=50, leftMargin=50,
            topMargin=40, bottomMargin=30,
        )
        page_width = landscape(A4)[0] - 100

        story = []

        # ===== 封面 =====
        call_put_cn = {'C': '看涨 (Call)', 'P': '看跌 (Put)'}
        product_desc = f" — {call_put_cn.get(call_put, '')}" if call_put else ""
        story.append(Spacer(1, 1.5 * inch))
        story.append(Paragraph(f'期权日线指标分析报告{product_desc}', styles['title']))
        story.append(Spacer(1, 0.25 * inch))
        story.append(Paragraph(
            'Option Daily Indicator Analysis Report',
            ParagraphStyle('Sub', parent=styles['normal'], alignment=1,
                           fontSize=11, textColor=colors.HexColor('#888888'),
                           fontName=self.reportlab_font),
        ))
        story.append(Spacer(1, 0.35 * inch))

        trade_dates = sorted(df['trade_date'].unique()) if 'trade_date' in df.columns else []
        cover_date_range = f"{trade_dates[0]} — {trade_dates[-1]}" if len(trade_dates) > 0 else "N/A"
        unique_ts = df['ts_code'].nunique() if 'ts_code' in df.columns else 0
        cover_text = (
            f"数据区间：{cover_date_range}<br/>"
            f"生成时间：{report_date}<br/>"
            f"合约过滤：ts_code LIKE '{ts_code_filter or '无'}' | 方向：{call_put or '全部'}<br/>"
            f"数据记录：{len(df)} 条 | 合约数量：{unique_ts}<br/>"
            f"<br/>INFINITY 量化系统 · 期权研究专用"
        )
        story.append(Paragraph(cover_text, styles['cover_info']))
        story.append(PageBreak())

        # ===== 简述 =====
        story.append(Paragraph('一、数据概览', styles['h1']))
        story.append(Spacer(1, 0.1 * inch))

        if len(trade_dates) > 0:
            story.append(Paragraph(
                f"数据区间：{trade_dates[0]} 至 {trade_dates[-1]}，共 {len(trade_dates)} 个交易日。",
                styles['normal']
            ))
        story.append(Paragraph(
            f"合约数量：{unique_ts} 个合约。",
            styles['normal']
        ))
        if 'implied_vol' in df.columns:
            iv_valid = df['implied_vol'].notna().sum()
            story.append(Paragraph(
                f"隐含波动率有效数据：{iv_valid}/{len(df)} 行（{iv_valid/len(df)*100:.1f}%）。"
                f"NaN 行多为深度实值期权市价低于欧式期权无套利下界（Call: S-Ke^(-rT)），BS公式无实数解。",
                styles['normal']
            ))
        story.append(PageBreak())

        # ===== 图表 =====
        cp_label_full = {'C': 'Call', 'P': 'Put'}
        cp_display = cp_label_full.get(call_put, 'Call')

        chart_config = [
            ('chart1_spot_close', '图1：spot_price + 各合约 收盘价 (close)', '二、', 0.45),
            ('chart2_implied_vol', '图2：spot_price + 各合约 隐含波动率 (implied_vol)', '三、', 0.45),
            ('chart3_bs_price', '图3：spot_price + 各合约 BS理论价', '四、', 0.45),
            ('chart4_delta', '图4：spot_price + 各合约 Delta', '五、', 0.45),
            ('chart5_gamma', '图5：spot_price + 各合约 Gamma', '六、', 0.45),
            ('chart6_vega', '图6：spot_price + 各合约 Vega', '七、', 0.45),
            ('chart7_theta', '图7：spot_price + 各合约 Theta', '八、', 0.45),
            ('chart8_rho', '图8：spot_price + 各合约 Rho + risk_free_rate', '九、', 0.45),
        ]

        # IV Smile 仪表盘：按 call_put 动态插入
        if call_put is None:
            chart_config.append(
                ('chart9_smile_call', '图9：IV Smile 多日演变仪表盘 (Call期权)', '十、', 0.65))
            chart_config.append(
                ('chart10_smile_put', '图10：IV Smile 多日演变仪表盘 (Put期权)', '十、', 0.65))
        else:
            chart_config.append(
                ('chart9_smile', '图9：IV Smile 多日演变仪表盘', '十、', 0.65))

        chart_config.extend([
            ('chart11_exercise_price_iv_vol',
             f'图11：行权价 vs 隐含波动率 + 成交量 ({cp_display}, 按trade_date)', '十一、', 0.45),
            ('chart12_exercise_price_delta_vol',
             f'图12：行权价 vs Delta + 成交量 ({cp_display}, 按trade_date)', '十二、', 0.45),
            ('chart13_exercise_price_gamma_vol',
             f'图13：行权价 vs Gamma + 成交量 ({cp_display}, 按trade_date)', '十三、', 0.45),
            ('chart14_exercise_price_vega_vol',
             f'图14：行权价 vs Vega + 成交量 ({cp_display}, 按trade_date)', '十四、', 0.45),
            ('chart15_exercise_price_theta_vol',
             f'图15：行权价 vs Theta + 成交量 ({cp_display}, 按trade_date)', '十五、', 0.45),
            ('chart16_exercise_price_rho_vol',
             f'图16：行权价 vs Rho + 成交量 ({cp_display}, 按trade_date)', '十六、', 0.45),
            ('chart17_exercise_price_d1_d2',
             f'图17：行权价 vs d1 + d2 ({cp_display}, 按trade_date)', '十七、', 0.45),
            ('chart18_exercise_price_nd1_nd2',
             f'图18：行权价 vs N(d1) + N(d2) ({cp_display}, 按trade_date)', '十八、', 0.45),
            ('chart19_trade_date_x_d1',
             f'图19：交易日 vs d1 ({cp_display}, 按exercise_price)', '十九、', 0.45),
            ('chart20_trade_date_x_d2',
             f'图20：交易日 vs d2 ({cp_display}, 按exercise_price)', '二十、', 0.45),
            ('chart21_trade_date_x_nd1',
             f'图21：交易日 vs N(d1) ({cp_display}, 按exercise_price)', '二十一、', 0.45),
            ('chart22_trade_date_x_nd2',
             f'图22：交易日 vs N(d2) ({cp_display}, 按exercise_price)', '二十二、', 0.45),
        ])

        last_chart_key = chart_config[-1][0] if chart_config else 'chart22_trade_date_x_nd2'

        for buf_key, chart_title, section_label, height_frac in chart_config:
            buf = chart_buffers.get(buf_key)
            if buf is None:
                continue

            story.append(Paragraph(f'{section_label} {chart_title}', styles['h1']))
            story.append(Spacer(1, 0.1 * inch))
            img = RLImage(buf, width=page_width, height=page_width * height_frac)
            story.append(img)
            story.append(Spacer(1, 0.15 * inch))
            if buf_key != last_chart_key:  # 最后一张图后不换页，直接接风险提示
                story.append(PageBreak())

        # ===== 风险提示 =====
        story.append(Paragraph('二十三、风险提示', styles['h1']))
        story.append(Spacer(1, 0.15 * inch))
        risk_text = (
            "本报告基于历史期权日线数据进行量化分析，仅供参考，不构成投资建议。<br/>"
            "隐含波动率为BS模型反向求解，深度实值期权因市价低于理论下界可能导致部分行IV为空(NULL)。<br/>"
            "Greeks为BS框架下的理论值，实际交易中受流动性、波动率微笑、跳空等因素影响可能存在偏差。<br/>"
            "建议投资者结合自身情况，进行独立判断和决策。"
        )
        story.append(Paragraph(risk_text, styles['normal']))

        doc.build(story)
        logger.info(f"✅ PDF 报告已生成: {pdf_path}")
        return pdf_path

    # ===================== 主流程 =====================

    def run(self, start_date=None, end_date=None, ts_code_filter=None, call_put=None):
        """运行期权日线指标报告生成主流程

        Args:
            start_date: 起始日期 YYYYMMDD
            end_date: 截止日期 YYYYMMDD
            ts_code_filter: 合约代码过滤（LIKE），如 'HO2612%'
            call_put: 行权方向 'C'/'P'，None 表示全部

        Returns:
            pdf_path or None
        """
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName="run",
                          event="Starting OptDailyIndicatorReport generation")

        try:
            # Step 1: 拉取数据
            logger.info("=" * 60)
            logger.info(f"Step 1/3: 从 ClickHouse 拉取数据 "
                        f"(ts_code_filter={ts_code_filter}, call_put={call_put})")
            logger.info("=" * 60)
            df = self.fetch_data(
                start_date=start_date, end_date=end_date,
                ts_code_filter=ts_code_filter, call_put=call_put
            )
            if df.empty:
                logger.warning("数据为空，流程终止")
                return None

            # Step 2: 数据清洗
            logger.info("=" * 60)
            logger.info("Step 2/3: 数据清洗 & 生成图表")
            logger.info("=" * 60)
            df = self.clean_data(df)

            # Step 3: 生成图表
            chart_buffers = {}

            logger.info("生成图1: spot_price + close (双Y轴)...")
            chart_buffers['chart1_spot_close'] = self.gen_chart1_spot_and_close(df)

            logger.info("生成图2: implied_vol...")
            chart_buffers['chart2_implied_vol'] = self.gen_chart2_implied_vol(df)

            logger.info("生成图3: bs_theoretical_price...")
            chart_buffers['chart3_bs_price'] = self.gen_chart3_bs_theoretical_price(df)

            logger.info("生成图4: delta...")
            chart_buffers['chart4_delta'] = self.gen_chart4_delta(df)

            logger.info("生成图5: gamma...")
            chart_buffers['chart5_gamma'] = self.gen_chart5_gamma(df)

            logger.info("生成图6: vega...")
            chart_buffers['chart6_vega'] = self.gen_chart6_vega(df)

            logger.info("生成图7: theta...")
            chart_buffers['chart7_theta'] = self.gen_chart7_theta(df)

            logger.info("生成图8: rho...")
            chart_buffers['chart8_rho'] = self.gen_chart8_rho(df)

            # IV Smile 仪表盘：按 call_put 生成对应的
            if call_put is None or call_put == 'C':
                logger.info("生成图9: IV Smile 多日演变仪表盘 (Call)...")
                chart_buffers['chart9_smile_call'] = self.gen_chart9_ivol_smile_dashboard(df, call_put='C')
            if call_put is None or call_put == 'P':
                chart_key = 'chart10_smile_put' if call_put is None else 'chart9_smile'
                log_label = '图10' if call_put is None else '图9'
                logger.info(f"生成{log_label}: IV Smile 多日演变仪表盘 (Put)...")
                chart_buffers[chart_key] = self.gen_chart9_ivol_smile_dashboard(df, call_put='P')

            # 行权价 × trade_date 图表：按 call_put 动态过滤
            cp_filter = call_put if call_put else 'C'
            cp_label = call_put if call_put else 'Call'
            logger.info(f"生成图11: 行权价 vs 隐含波动率 + 成交量 ({cp_label})...")
            chart_buffers['chart11_exercise_price_iv_vol'] = self._gen_exercise_price_dual_y_chart(
                df, 'implied_vol', '隐含波动率 (implied_vol)', 'vol', '成交量 (vol)',
                chart_num=11, call_put=cp_filter,
                title_prefix=f'图11：行权价 vs 隐含波动率(Y1) + 成交量(Y2) — 按trade_date ({cp_label})')

            logger.info(f"生成图12: 行权价 vs Delta + 成交量 ({cp_label})...")
            chart_buffers['chart12_exercise_price_delta_vol'] = self._gen_exercise_price_dual_y_chart(
                df, 'delta', 'Delta', 'vol', '成交量 (vol)',
                chart_num=12, call_put=cp_filter,
                title_prefix=f'图12：行权价 vs Delta(Y1) + 成交量(Y2) — 按trade_date ({cp_label})')

            logger.info(f"生成图13: 行权价 vs Gamma + 成交量 ({cp_label})...")
            chart_buffers['chart13_exercise_price_gamma_vol'] = self._gen_exercise_price_dual_y_chart(
                df, 'gamma', 'Gamma', 'vol', '成交量 (vol)',
                chart_num=13, call_put=cp_filter,
                title_prefix=f'图13：行权价 vs Gamma(Y1) + 成交量(Y2) — 按trade_date ({cp_label})')

            logger.info(f"生成图14: 行权价 vs Vega + 成交量 ({cp_label})...")
            chart_buffers['chart14_exercise_price_vega_vol'] = self._gen_exercise_price_dual_y_chart(
                df, 'vega', 'Vega', 'vol', '成交量 (vol)',
                chart_num=14, call_put=cp_filter,
                title_prefix=f'图14：行权价 vs Vega(Y1) + 成交量(Y2) — 按trade_date ({cp_label})')

            logger.info(f"生成图15: 行权价 vs Theta + 成交量 ({cp_label})...")
            chart_buffers['chart15_exercise_price_theta_vol'] = self._gen_exercise_price_dual_y_chart(
                df, 'theta', 'Theta', 'vol', '成交量 (vol)',
                chart_num=15, call_put=cp_filter,
                title_prefix=f'图15：行权价 vs Theta(Y1) + 成交量(Y2) — 按trade_date ({cp_label})')

            logger.info(f"生成图16: 行权价 vs Rho + 成交量 ({cp_label})...")
            chart_buffers['chart16_exercise_price_rho_vol'] = self._gen_exercise_price_dual_y_chart(
                df, 'rho', 'Rho', 'vol', '成交量 (vol)',
                chart_num=16, call_put=cp_filter,
                title_prefix=f'图16：行权价 vs Rho(Y1) + 成交量(Y2) — 按trade_date ({cp_label})')

            logger.info(f"生成图17: 行权价 vs d1 + d2 ({cp_label})...")
            chart_buffers['chart17_exercise_price_d1_d2'] = self._gen_exercise_price_dual_y_chart(
                df, 'd1', 'd1', 'd2', 'd2',
                chart_num=17, call_put=cp_filter,
                title_prefix=f'图17：行权价 vs d1(Y1) + d2(Y2) — 按trade_date ({cp_label})')

            logger.info(f"生成图18: 行权价 vs N(d1) + N(d2) ({cp_label})...")
            chart_buffers['chart18_exercise_price_nd1_nd2'] = self._gen_exercise_price_dual_y_chart(
                df, 'nd1', 'N(d1)', 'nd2', 'N(d2)',
                chart_num=18, call_put=cp_filter,
                title_prefix=f'图18：行权价 vs N(d1)(Y1) + N(d2)(Y2) — 按trade_date ({cp_label})')

            logger.info(f"生成图19: 交易日 vs d1 按exercise_price ({cp_label})...")
            chart_buffers['chart19_trade_date_x_d1'] = self._gen_trade_date_x_single_y_chart(
                df, 'd1', 'd1',
                chart_num=19, call_put=cp_filter,
                title_prefix=f'图19：交易日 vs d1 — 按行权价exercise_price为系列 ({cp_label})')

            logger.info(f"生成图20: 交易日 vs d2 按exercise_price ({cp_label})...")
            chart_buffers['chart20_trade_date_x_d2'] = self._gen_trade_date_x_single_y_chart(
                df, 'd2', 'd2',
                chart_num=20, call_put=cp_filter,
                title_prefix=f'图20：交易日 vs d2 — 按行权价exercise_price为系列 ({cp_label})')

            logger.info(f"生成图21: 交易日 vs N(d1) 按exercise_price ({cp_label})...")
            chart_buffers['chart21_trade_date_x_nd1'] = self._gen_trade_date_x_single_y_chart(
                df, 'nd1', 'N(d1)',
                chart_num=21, call_put=cp_filter,
                title_prefix=f'图21：交易日 vs N(d1) — 按行权价exercise_price为系列 ({cp_label})')

            logger.info(f"生成图22: 交易日 vs N(d2) 按exercise_price ({cp_label})...")
            chart_buffers['chart22_trade_date_x_nd2'] = self._gen_trade_date_x_single_y_chart(
                df, 'nd2', 'N(d2)',
                chart_num=22, call_put=cp_filter,
                title_prefix=f'图22：交易日 vs N(d2) — 按行权价exercise_price为系列 ({cp_label})')

            chart_count = sum(1 for v in chart_buffers.values() if v is not None)
            logger.info(f"图表生成完成: {chart_count} 张")

            # Step 4: 生成 PDF
            logger.info("=" * 60)
            logger.info("Step 3/3: 生成 PDF 报告")
            logger.info("=" * 60)
            pdf_path = self._generate_pdf_report(
                df, chart_buffers,
                start_date=start_date, end_date=end_date,
                ts_code_filter=ts_code_filter, call_put=call_put
            )

            logger.info("\n" + "=" * 80)
            logger.info("✅ 期权日线指标分析报告 生成完成！")
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
    report = OptDailyIndicatorReport()
    report.run(start_date="20260701", end_date="20260717", ts_code_filter="HO2612%")

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

    def fetch_data(self, start_date=None, end_date=None, ts_code_filter=None):
        """从 ClickHouse 拉取 tb_tushare_opt_daily_indicator 表数据

        Args:
            start_date: 起始日期 YYYYMMDD
            end_date: 截止日期 YYYYMMDD
            ts_code_filter: 合约代码过滤（LIKE），如 'HO2612%'

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

    def _gen_dual_y_chart(self, df, y_col, y_col_cn, chart_num, title_prefix=None):
        """通用双Y轴折线图模板：
        Y1（左轴）= spot_price（一条粗线）
        Y2（右轴）= 各 ts_code 的指定指标列（多条彩色细线）

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

        # ---- 右端标签 ----
        self._add_end_labels(ax2, ts_codes, series_dict, y_col)

        # ---- X 轴格式 ----
        fig.autofmt_xdate(rotation=45, ha='right')

        # ---- 合并图例 ----
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        all_lines = lines1 + lines2
        all_labels = labels1 + labels2
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
                                      title_prefix='图8：spot_price + 各合约 Rho')

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
                              start_date=None, end_date=None, ts_code_filter=None):
        """生成完整 PDF 报告"""
        styles = self._build_pdf_styles()

        report_date = datetime.now().strftime('%Y-%m-%d %H:%M')
        now_ts = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 文件名基于日期范围
        date_tag = f"{start_date}-{end_date}" if start_date and end_date else "custom"
        pdf_path = os.path.join(
            self.OUTPUT_DIR,
            f"OptDailyIndicator_Report_{date_tag}_{now_ts}.pdf"
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
        story.append(Spacer(1, 1.5 * inch))
        story.append(Paragraph('期权日线指标分析报告', styles['title']))
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
            f"过滤条件：ts_code LIKE '{ts_code_filter or '无'}'<br/>"
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
        chart_config = [
            ('chart1_spot_close', '图1：spot_price + 各合约 收盘价 (close)', '二、'),
            ('chart2_implied_vol', '图2：spot_price + 各合约 隐含波动率 (implied_vol)', '三、'),
            ('chart3_bs_price', '图3：spot_price + 各合约 BS理论价', '四、'),
            ('chart4_delta', '图4：spot_price + 各合约 Delta', '五、'),
            ('chart5_gamma', '图5：spot_price + 各合约 Gamma', '六、'),
            ('chart6_vega', '图6：spot_price + 各合约 Vega', '七、'),
            ('chart7_theta', '图7：spot_price + 各合约 Theta', '八、'),
            ('chart8_rho', '图8：spot_price + 各合约 Rho', '九、'),
        ]

        for buf_key, chart_title, section_label in chart_config:
            buf = chart_buffers.get(buf_key)
            if buf is None:
                continue

            story.append(Paragraph(f'{section_label} {chart_title}', styles['h1']))
            story.append(Spacer(1, 0.1 * inch))
            img = RLImage(buf, width=page_width, height=page_width * 0.45)
            story.append(img)
            story.append(Spacer(1, 0.15 * inch))
            story.append(PageBreak())

        # ===== 风险提示 =====
        story.append(Paragraph('十、风险提示', styles['h1']))
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

    def run(self, start_date=None, end_date=None, ts_code_filter=None):
        """运行期权日线指标报告生成主流程

        Args:
            start_date: 起始日期 YYYYMMDD
            end_date: 截止日期 YYYYMMDD
            ts_code_filter: 合约代码过滤（LIKE），如 'HO2612%'

        Returns:
            pdf_path or None
        """
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName="run",
                          event="Starting OptDailyIndicatorReport generation")

        try:
            # Step 1: 拉取数据
            logger.info("=" * 60)
            logger.info(f"Step 1/3: 从 ClickHouse 拉取数据 (ts_code_filter={ts_code_filter})")
            logger.info("=" * 60)
            df = self.fetch_data(
                start_date=start_date, end_date=end_date, ts_code_filter=ts_code_filter
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

            chart_count = sum(1 for v in chart_buffers.values() if v is not None)
            logger.info(f"图表生成完成: {chart_count}/8")

            # Step 4: 生成 PDF
            logger.info("=" * 60)
            logger.info("Step 3/3: 生成 PDF 报告")
            logger.info("=" * 60)
            pdf_path = self._generate_pdf_report(
                df, chart_buffers,
                start_date=start_date, end_date=end_date, ts_code_filter=ts_code_filter
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

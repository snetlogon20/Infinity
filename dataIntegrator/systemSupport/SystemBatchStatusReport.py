"""
系统批量任务状态报告生成器
读取 df_tushare_manager_job_log 和 df_akshare_manager_job_log 当日日志，
生成包含饼图、明细表、30天趋势折线图的 PDF 报告。
"""
import os
import tempfile
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.utility.FileUtility import FileUtility

logger = CommonLib.logger


class SystemBatchStatusReport:
    """系统批量任务状态报告"""

    def __init__(self):
        self.report_dir = CommonParameters.SystemBatchStatusReportPath
        self._ensure_output_directory()
        self._register_chinese_font()

    def _ensure_output_directory(self):
        """确保报告输出目录存在"""
        if not os.path.exists(self.report_dir):
            os.makedirs(self.report_dir)
            logger.info(f"创建 SystemBatchStatus 报告目录: {self.report_dir}")

    def _register_chinese_font(self):
        """注册中文字体（matplotlib + ReportLab）"""
        self.chinese_font = 'SimHei'
        self.reportlab_font = 'Helvetica'

        font_mapping = [
            (r'C:\Windows\Fonts\msyh.ttc', 'MicrosoftYaHei'),
            (r'C:\Windows\Fonts\simhei.ttf', 'SimHei'),
            (r'C:\Windows\Fonts\simfang.ttf', 'FangSong'),
            (r'C:\Windows\Fonts\simsun.ttc', 'SimSun'),
        ]

        # matplotlib 全局字体
        for font_path, font_name in font_mapping:
            if os.path.exists(font_path):
                try:
                    from matplotlib.font_manager import FontProperties
                    self.chinese_font = FontProperties(fname=font_path).get_name()
                    plt.rcParams['font.family'] = 'sans-serif'
                    plt.rcParams['font.sans-serif'] = [self.chinese_font, 'DejaVu Sans']
                    plt.rcParams['axes.unicode_minus'] = False
                    logger.info(f"matplotlib 成功加载中文字体: {font_path}")
                    break
                except Exception as e:
                    logger.warning(f"matplotlib 字体加载失败 {font_path}: {e}")

        # ReportLab 字体注册
        for font_path, font_name in font_mapping:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    self.reportlab_font = font_name
                    logger.info(f"ReportLab 成功加载中文字体: {font_path} -> {font_name}")
                    break
                except Exception as e:
                    logger.warning(f"ReportLab 字体加载失败 {font_path}: {e}")

        if self.reportlab_font == 'Helvetica':
            logger.warning("ReportLab 未找到中文字体，PDF 中的中文可能无法正常显示")

    # ----------------------------------------------------------------
    # 数据查询
    # ----------------------------------------------------------------

    def _fetch_today_logs(self, target_date):
        """查询当日日志明细（包含 extra_params）"""
        sql = f"""
        SELECT 'TuShare' AS source, job_name, job_status, start_time, end_time,
               duration_seconds, records_processed, error_message, comment
        FROM indexsysdb.df_tushare_manager_job_log
        WHERE toDate(start_time) = toDate('{target_date}')
        UNION ALL
        SELECT 'AKShare' AS source, job_name, job_status, start_time, end_time,
               duration_seconds, records_processed, error_message, comment
        FROM indexsysdb.df_akshare_manager_job_log
        WHERE toDate(start_time) = toDate('{target_date}')
        UNION ALL
        SELECT 'Report' AS source, job_name, job_status, start_time, end_time,
               duration_seconds, records_processed, error_message, comment
        FROM indexsysdb.df_report_job_log
        WHERE toDate(start_time) = toDate('{target_date}')
        ORDER BY source, start_time
        """
        logger.info(f"查询当日日志: target_date={target_date}")
        df = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        if df.empty:
            logger.warning(f"当日 ({target_date}) 无日志记录")
        else:
            logger.info(f"当日日志记录数: {len(df)}")
        return df

    def _fetch_today_group_stats(self, target_date):
        """查询当日按 source + status 的分组统计"""
        sql = f"""
        SELECT source, job_status, count() AS cnt
        FROM (
            SELECT 'TuShare' AS source, job_status
            FROM indexsysdb.df_tushare_manager_job_log
            WHERE toDate(start_time) = toDate('{target_date}')
            UNION ALL
            SELECT 'AKShare' AS source, job_status
            FROM indexsysdb.df_akshare_manager_job_log
            WHERE toDate(start_time) = toDate('{target_date}')
            UNION ALL
            SELECT 'Report' AS source, job_status
            FROM indexsysdb.df_report_job_log
            WHERE toDate(start_time) = toDate('{target_date}')
        )
        GROUP BY source, job_status
        ORDER BY source, job_status
        """
        logger.info(f"查询当日分组统计: target_date={target_date}")
        df = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        return df

    def _fetch_30day_trend(self, target_date):
        """查询近30天每日成功/失败趋势"""
        sql = f"""
        SELECT toDate(start_time) AS date,
               countIf(job_status = 'SUCCESS') AS success_count,
               countIf(job_status = 'FAILED') AS failure_count,
               count() AS total_count
        FROM (
            SELECT start_time, job_status
            FROM indexsysdb.df_tushare_manager_job_log
            WHERE toDate(start_time) >= toDate('{target_date}') - 30
            UNION ALL
            SELECT start_time, job_status
            FROM indexsysdb.df_akshare_manager_job_log
            WHERE toDate(start_time) >= toDate('{target_date}') - 30
            UNION ALL
            SELECT start_time, job_status
            FROM indexsysdb.df_report_job_log
            WHERE toDate(start_time) >= toDate('{target_date}') - 30
        )
        GROUP BY date
        ORDER BY date
        """
        logger.info(f"查询近30天趋势: target_date={target_date}")
        df = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        if not df.empty:
            logger.info(f"30天趋势数据: {len(df)} 天, 共 {df['total_count'].sum()} 条记录")
        return df

    # ----------------------------------------------------------------
    # 图表生成
    # ----------------------------------------------------------------

    def _generate_pie_chart(self, group_stats_df, target_date):
        """生成饼图：按 source 分别展示成功/失败/运行中占比"""
        if group_stats_df.empty:
            return None

        sources = group_stats_df['source'].unique()
        n_sources = len(sources)
        fig, axes = plt.subplots(1, n_sources, figsize=(7 * n_sources, 5))
        if n_sources == 1:
            axes = [axes]

        status_colors = {
            'SUCCESS': '#4CAF50',
            'FAILED': '#F44336',
            'RUNNING': '#FF9800',
        }
        status_labels = {
            'SUCCESS': '成功',
            'FAILED': '失败',
            'RUNNING': '运行中',
        }

        for idx, source in enumerate(sources):
            ax = axes[idx]
            source_data = group_stats_df[group_stats_df['source'] == source]

            labels = []
            sizes = []
            pie_colors = []
            for _, row in source_data.iterrows():
                status = row['job_status']
                labels.append(status_labels.get(status, status))
                sizes.append(row['cnt'])
                pie_colors.append(status_colors.get(status, '#9E9E9E'))

            wedges, texts, autotexts = ax.pie(
                sizes, labels=labels, colors=pie_colors, autopct='%1.1f%%',
                startangle=90, pctdistance=0.6,
                textprops={'fontsize': 11}
            )
            for at in autotexts:
                at.set_fontsize(10)
                at.set_color('white')
                at.set_fontweight('bold')
            ax.set_title(f'{source} - 批量任务状态分布\n({target_date})',
                         fontsize=14, fontweight='bold')

        plt.tight_layout()
        pie_path = os.path.join(tempfile.gettempdir(), 'system_batch_status_pie.png')
        fig.savefig(pie_path, dpi=200, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        logger.info(f"饼图已保存: {pie_path}")
        return pie_path

    def _generate_trend_line_chart(self, trend_df, target_date):
        """生成近30天成功/失败数量折线图"""
        if trend_df.empty:
            return None

        trend_df = trend_df.copy()
        trend_df['date'] = pd.to_datetime(trend_df['date'])

        fig, ax1 = plt.subplots(figsize=(14, 5))

        ax1.plot(trend_df['date'], trend_df['success_count'],
                 color='#4CAF50', marker='o', linewidth=2, markersize=5, label='成功')
        ax1.plot(trend_df['date'], trend_df['failure_count'],
                 color='#F44336', marker='s', linewidth=2, markersize=5, label='失败')

        # 填充区域
        ax1.fill_between(trend_df['date'], 0, trend_df['success_count'],
                         color='#4CAF50', alpha=0.15)
        ax1.fill_between(trend_df['date'], 0, trend_df['failure_count'],
                         color='#F44336', alpha=0.15)

        ax1.set_title(f'近30天批量任务执行趋势 ({target_date})',
                      fontsize=14, fontweight='bold')
        ax1.set_xlabel('日期', fontsize=10)
        ax1.set_ylabel('任务数量', fontsize=10)
        ax1.legend(loc='upper left', fontsize=10, framealpha=0.9)
        ax1.grid(True, alpha=0.3, linestyle='--')

        # 右侧 Y 轴总数
        ax2 = ax1.twinx()
        ax2.plot(trend_df['date'], trend_df['total_count'],
                 color='#2196F3', marker='d', linewidth=1.5, markersize=4,
                 linestyle='--', alpha=0.6, label='总数')
        ax2.set_ylabel('任务总数', fontsize=10, color='#2196F3')
        ax2.tick_params(axis='y', labelcolor='#2196F3')
        ax2.legend(loc='upper right', fontsize=9, framealpha=0.9)

        ax1.xaxis.set_major_formatter(mticker.FuncFormatter(
            lambda x, _: pd.Timestamp('1970-01-01') + pd.Timedelta(days=int(x)) if x < 100000 else pd.Timestamp(x)
        ))

        fig.autofmt_xdate(rotation=45)

        plt.tight_layout()
        trend_path = os.path.join(tempfile.gettempdir(), 'system_batch_status_trend.png')
        fig.savefig(trend_path, dpi=200, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        logger.info(f"趋势折线图已保存: {trend_path}")
        return trend_path

    # ----------------------------------------------------------------
    # PDF 报告生成
    # ----------------------------------------------------------------

    def _build_detail_table(self, df, page_width=None):
        """构建带状态颜色的明细表（不含数据源列，因为已按源分组）"""
        detail_columns = ['任务名称', '状态', '开始时间', '结束时间',
                          '耗时(秒)', '处理记录数', '关键参数', '错误信息']
        col_widths = [2.6 * inch, 0.55 * inch, 1.25 * inch, 1.25 * inch,
                      0.65 * inch, 0.75 * inch, 1.5 * inch, 2.2 * inch]

        table_data = [detail_columns]

        for _, row in df.iterrows():
            start_str = str(row.get('start_time', ''))[:19] if pd.notna(row.get('start_time')) else ''
            end_str = str(row.get('end_time', ''))[:19] if pd.notna(row.get('end_time')) else ''
            dur_str = f"{row['duration_seconds']:.1f}" if pd.notna(row.get('duration_seconds')) else ''
            rec_str = str(int(row['records_processed'])) if pd.notna(row.get('records_processed')) else ''
            err_str = str(row.get('error_message', ''))[:60] if pd.notna(row.get('error_message')) else ''

            comment = row.get('comment', '')
            if pd.isna(comment):
                comment = ''
            elif len(str(comment)) > 30:
                comment = str(comment)[:30]

            table_data.append([
                row['job_name'],
                row['job_status'],
                start_str,
                end_str,
                dur_str,
                rec_str,
                comment,
                err_str,
            ])

        detail_table = Table(table_data, colWidths=col_widths, repeatRows=1)

        table_styles = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#455A64')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),   # 任务名称左对齐
            ('ALIGN', (6, 1), (7, -1), 'LEFT'),    # 参数、错误信息左对齐
            ('FONTNAME', (0, 0), (-1, -1), self.reportlab_font),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#B0BEC5')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]

        for i in range(1, len(table_data)):
            status = table_data[i][1]
            if status == 'FAILED':
                row_bg = colors.HexColor('#FFCDD2')
                row_fg = colors.HexColor('#B71C1C')
            elif status == 'SUCCESS':
                row_bg = colors.HexColor('#C8E6C9')
                row_fg = colors.HexColor('#1B5E20')
            else:
                row_bg = colors.HexColor('#FFF9C4')
                row_fg = colors.HexColor('#F57F17')

            table_styles.append(('BACKGROUND', (0, i), (-1, i), row_bg))
            table_styles.append(('TEXTCOLOR', (0, i), (-1, i), row_fg))

        detail_table.setStyle(TableStyle(table_styles))
        return detail_table

    def generate_report(self, target_date=None):
        """
        生成系统批量任务状态 PDF 报告

        参数:
        - target_date: 目标日期 (格式: 'YYYY-MM-DD')，默认今天
        """
        if target_date is None:
            target_date = datetime.now().strftime('%Y-%m-%d')

        logger.info("=" * 80)
        logger.info(f"开始生成 系统批量任务状态报告 - {target_date}")
        logger.info("=" * 80)

        # ---- 1. 数据查询 ----
        today_logs_df = self._fetch_today_logs(target_date)
        group_stats_df = self._fetch_today_group_stats(target_date)
        trend_df = self._fetch_30day_trend(target_date)

        # ---- 2. 统计汇总 ----
        total_jobs = 0
        total_success = 0
        total_failed = 0
        if not group_stats_df.empty:
            total_jobs = int(group_stats_df['cnt'].sum())
            success_rows = group_stats_df[group_stats_df['job_status'] == 'SUCCESS']
            total_success = int(success_rows['cnt'].sum()) if not success_rows.empty else 0
            failed_rows = group_stats_df[group_stats_df['job_status'] == 'FAILED']
            total_failed = int(failed_rows['cnt'].sum()) if not failed_rows.empty else 0

        logger.info(f"当日统计: 总数={total_jobs}, 成功={total_success}, 失败={total_failed}")

        # ---- 3. 图表生成 ----
        temp_files = []

        pie_chart_path = self._generate_pie_chart(group_stats_df, target_date)
        if pie_chart_path:
            temp_files.append(pie_chart_path)

        trend_chart_path = self._generate_trend_line_chart(trend_df, target_date)
        if trend_chart_path:
            temp_files.append(trend_chart_path)

        # ---- 4. PDF 构建 ----
        today_display = target_date.replace('-', '')
        pdf_filename = FileUtility.generate_filename_by_timestamp(
            f'SystemBatchStatusReport_{today_display}', 'pdf')
        pdf_path = os.path.join(self.report_dir, pdf_filename)

        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=landscape(A4),
            rightMargin=60,
            leftMargin=60,
            topMargin=50,
            bottomMargin=30
        )
        page_width = landscape(A4)[0] - 120

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'ReportTitle', parent=styles['Heading1'],
            fontSize=22, leading=30, alignment=1,
            fontName=self.reportlab_font, spaceAfter=20
        )
        heading_style = ParagraphStyle(
            'SectionHeading', parent=styles['Heading2'],
            fontSize=16, leading=22,
            fontName=self.reportlab_font, spaceAfter=12, spaceBefore=12
        )
        subheading_style = ParagraphStyle(
            'SubHeading', parent=styles['Heading3'],
            fontSize=13, leading=18,
            fontName=self.reportlab_font, spaceAfter=8, spaceBefore=8
        )
        normal_style = ParagraphStyle(
            'ReportNormal', parent=styles['Normal'],
            fontSize=10, leading=15,
            fontName=self.reportlab_font
        )
        cell_style = ParagraphStyle(
            'TableCell', parent=styles['Normal'],
            fontSize=8, leading=11,
            fontName=self.reportlab_font
        )

        story = []

        # ---- 封面 / 标题 ----
        story.append(Paragraph('系统批量任务状态报告', title_style))
        story.append(Spacer(1, 0.15 * inch))
        story.append(Paragraph(f'报告日期: {target_date}', normal_style))
        story.append(Paragraph(f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', normal_style))
        story.append(Spacer(1, 0.3 * inch))

        # ---- 一、当日执行概览 ----
        story.append(Paragraph('一、当日执行概览', heading_style))

        overview_data = [
            ['指标', '数值'],
            ['任务总数', str(total_jobs)],
            ['成功数', str(total_success)],
            ['失败数', str(total_failed)],
            ['成功率', f'{total_success / total_jobs * 100:.1f}%' if total_jobs > 0 else 'N/A'],
        ]
        overview_table = Table(overview_data, colWidths=[2.5 * inch, 2 * inch])
        overview_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#455A64')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), self.reportlab_font),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ECEFF1')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#B0BEC5')),
        ]))
        story.append(overview_table)
        story.append(Spacer(1, 0.2 * inch))

        # 各 source 分项统计
        if not group_stats_df.empty:
            story.append(Paragraph('各数据源统计:', subheading_style))
            for source in group_stats_df['source'].unique():
                sd = group_stats_df[group_stats_df['source'] == source]
                src_total = int(sd['cnt'].sum())
                src_ok = int(sd[sd['job_status'] == 'SUCCESS']['cnt'].sum()) if 'SUCCESS' in sd['job_status'].values else 0
                src_fail = int(sd[sd['job_status'] == 'FAILED']['cnt'].sum()) if 'FAILED' in sd['job_status'].values else 0
                src_rate = f'{src_ok / src_total * 100:.1f}%' if src_total > 0 else 'N/A'
                story.append(Paragraph(
                    f'&nbsp;&nbsp;&nbsp;{source}: 总数 {src_total}, 成功 {src_ok}, 失败 {src_fail}, 成功率 {src_rate}',
                    normal_style
                ))

        story.append(PageBreak())

        # ---- 二、任务状态分布饼图 ----
        story.append(Paragraph('二、任务状态分布', heading_style))
        if pie_chart_path and os.path.exists(pie_chart_path):
            img = Image(pie_chart_path, width=page_width * 0.85, height=page_width * 0.55)
            story.append(img)
            story.append(Spacer(1, 0.15 * inch))
            story.append(Paragraph('上图展示了当日各数据源批量任务的成功/失败/运行中占比分布。', normal_style))
        else:
            story.append(Paragraph('（当日无日志记录，无法生成饼图）', normal_style))
        story.append(PageBreak())

        # ---- 三、日志明细（按数据源分开展示）----
        story.append(Paragraph('三、日志明细', heading_style))

        if not today_logs_df.empty:
            source_order = ['AKShare', 'TuShare', 'Report']
            for src in source_order:
                src_df = today_logs_df[today_logs_df['source'] == src]
                if src_df.empty:
                    continue

                # 统计该源
                src_total = len(src_df)
                src_ok = len(src_df[src_df['job_status'] == 'SUCCESS'])
                src_fail = len(src_df[src_df['job_status'] == 'FAILED'])
                src_running = len(src_df[src_df['job_status'] == 'RUNNING'])

                story.append(Paragraph(
                    f'3.{source_order.index(src) + 1} {src} 日志明细'
                    f' (共 {src_total} 条: 成功 {src_ok}, 失败 {src_fail}, 运行中 {src_running})',
                    subheading_style
                ))

                detail_table = self._build_detail_table(src_df)
                story.append(detail_table)
                story.append(Spacer(1, 0.25 * inch))
        else:
            story.append(Paragraph('（当日无日志记录）', normal_style))
        story.append(PageBreak())

        # ---- 四、近30天趋势 ----
        story.append(Paragraph('四、近30天执行趋势', heading_style))
        if trend_chart_path and os.path.exists(trend_chart_path):
            img = Image(trend_chart_path, width=page_width, height=page_width * 0.42)
            story.append(img)
            story.append(Spacer(1, 0.15 * inch))
            story.append(Paragraph('上图展示了近30天每日批量任务的成功/失败数量变化趋势。', normal_style))

            # 30天统计汇总
            if not trend_df.empty:
                story.append(Spacer(1, 0.15 * inch))
                total_30d = int(trend_df['total_count'].sum())
                success_30d = int(trend_df['success_count'].sum())
                failure_30d = int(trend_df['failure_count'].sum())
                rate_30d = f'{success_30d / (success_30d + failure_30d) * 100:.1f}%' if (success_30d + failure_30d) > 0 else 'N/A'
                story.append(Paragraph(
                    f'近30天汇总: 总任务 {total_30d}, 成功 {success_30d}, 失败 {failure_30d}, 成功率 {rate_30d}',
                    normal_style
                ))
        else:
            story.append(Paragraph('（近30天无日志记录，无法生成趋势图）', normal_style))

        # ---- 构建 PDF ----
        doc.build(story)

        # 清理临时文件
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except Exception:
                pass

        logger.info(f"PDF 报告已生成: {pdf_path}")
        return pdf_path


"""
信息比率分析报告生成器 - 用于将多个 PNG 图表合并为专业 PDF 报告
"""
import os
import numpy as np
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.common.ReportJobLogger import ReportJobLogger

logger = CommonLib.logger


class InformationRatioAnalysisReport:
    """信息比率分析报告生成器"""

    def __init__(self):
        self.reportlab_font = self._register_chinese_font()
        self._ensure_output_directory()
        self.job_logger = ReportJobLogger()

    def _ensure_output_directory(self):
        """确保输出目录存在"""
        self.output_dir = os.path.join(CommonParameters.outBoundPath, "report", "InformationRatioAnalysis")
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"✅ 创建 InformationRatioAnalysis 报告目录: {self.output_dir}")

    def _register_chinese_font(self):
        """注册中文字体"""
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
                    logger.info(f"✅ ReportLab 成功加载中文字体: {font_path} -> {font_name}")
                    break
                except Exception as e:
                    logger.warning(f"⚠️ ReportLab 字体加载失败 {font_path}: {e}")
                    continue

        if reportlab_font == 'Helvetica':
            logger.warning("⚠️ ReportLab 未找到中文字体，PDF 中的中文可能无法正常显示")

        return reportlab_font

    def generate_multi_chart_pdf(self, chart_paths, report_title, report_subtitle=None, output_path=None):
        """
        将多个 PNG 图表合并为 PDF 报告

        参数:
        - chart_paths: PNG 图表路径列表 [(path, title), ...]
        - report_title: 报告标题
        - report_subtitle: 报告副标题（可选）
        - output_path: 输出 PDF 路径（可选，默认自动生成）

        返回:
        - pdf_path: PDF 文件路径
        """
        if not chart_paths:
            logger.warning("⚠️ 没有图表路径，无法生成 PDF")
            return None

        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(
                self.output_dir,
                f"{report_title}_{timestamp}.pdf"
            )

        logger.info(f"📄 开始生成 PDF 报告: {output_path}")

        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(A4),
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )

        page_width = landscape(A4)[0] - 144

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            leading=32,
            alignment=1,
            fontName=self.reportlab_font,
            spaceAfter=30
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            leading=24,
            fontName=self.reportlab_font,
            spaceAfter=12,
            spaceBefore=12
        )
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            fontName=self.reportlab_font
        )

        story = []

        story.append(Paragraph(report_title, title_style))
        if report_subtitle:
            story.append(Spacer(1, 0.3 * inch))
            story.append(Paragraph(report_subtitle, normal_style))
        story.append(Paragraph(f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', normal_style))
        story.append(PageBreak())

        for idx, (chart_path, chart_title) in enumerate(chart_paths, 1):
            if not os.path.exists(chart_path):
                logger.warning(f"⚠️ 图表文件不存在，跳过: {chart_path}")
                continue

            story.append(Paragraph(f'第 {idx} 部分: {chart_title}', heading_style))
            img = Image(chart_path, width=page_width, height=page_width * 0.6)
            story.append(img)
            story.append(Spacer(1, 0.3 * inch))

            if idx < len(chart_paths):
                story.append(PageBreak())

        doc.build(story)
        logger.info(f"✅ PDF 报告已生成: {output_path}")

        return output_path

    def generate_ir_analysis_pdf(self, chart_paths, report_name, market_type="CN", start_date=None, end_date=None, output_path=None):
        """
        生成信息比率分析专用 PDF 报告
        """
        self.job_logger.start_job('InformationRatioAnalysisReport', 'IR',
                                  params={'report_name': report_name, 'market_type': market_type,
                                          'start_date': start_date, 'end_date': end_date,
                                          'chart_count': len(chart_paths) if chart_paths else 0})
        try:
            report_title = '信息比率 (Information Ratio) 分析报告'
            report_subtitle = f'报告名称: {report_name}\n市场类型: {market_type}'
            if start_date and end_date:
                report_subtitle += f'\n日期范围: {start_date} 至 {end_date}'

            result = self.generate_multi_chart_pdf(
                chart_paths=chart_paths,
                report_title=report_title,
                report_subtitle=report_subtitle,
                output_path=output_path
            )
            self.job_logger.end_job_success(records_processed=len(chart_paths) if chart_paths else 0)
            return result
        except Exception as e:
            import traceback
            self.job_logger.end_job_failed(str(e), traceback.format_exc())
            raise

    def generate_comprehensive_pdf(self, all_results, report_title="信息比率 (IR) 综合分析研究报告", output_path=None):
        """
        生成综合分析报告，合并所有测试案例并添加专业分析

        参数:
        - all_results: 所有测试结果列表，每个元素包含 {
            'name': 案例名称,
            'market_type': 市场类型,
            'chart_path': PNG 路径,
            'information_ratios': 信息比率字典,
            'active_returns': 主动收益字典,
            'tracking_errors': 跟踪误差字典,
            'benchmark': 基准指数,
            'start_date': 开始日期,
            'end_date': 结束日期
          }
        - report_title: 报告标题
        - output_path: 输出路径

        返回:
        - pdf_path: PDF 文件路径
        """
        if not all_results:
            logger.warning("⚠️ 没有测试结果，无法生成综合报告")
            return None

        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(
                self.output_dir,
                f"{report_title}_{timestamp}.pdf"
            )

        logger.info(f"📄 开始生成综合分析报告: {output_path}")

        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(A4),
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )

        page_width = landscape(A4)[0] - 144

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            leading=32,
            alignment=1,
            fontName=self.reportlab_font,
            spaceAfter=30
        )
        heading1_style = ParagraphStyle(
            'CustomHeading1',
            parent=styles['Heading1'],
            fontSize=18,
            leading=28,
            fontName=self.reportlab_font,
            spaceAfter=15,
            spaceBefore=15
        )
        heading2_style = ParagraphStyle(
            'CustomHeading2',
            parent=styles['Heading2'],
            fontSize=14,
            leading=20,
            fontName=self.reportlab_font,
            spaceAfter=10,
            spaceBefore=10
        )
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            fontName=self.reportlab_font
        )

        story = []

        story.append(Paragraph(report_title, title_style))
        story.append(Paragraph(f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', normal_style))
        story.append(Paragraph(f'测试案例数量: {len(all_results)}', normal_style))
        story.append(PageBreak())

        story.append(Paragraph('一、执行摘要', heading1_style))
        summary_text = f"""本报告对 {len(all_results)} 个投资组合进行了信息比率 (Information Ratio) 分析，涵盖美股和 A 股市场。
通过计算各资产相对于基准指数的超额收益和跟踪误差，评估资产的主动管理能力。
信息比率越高，表示单位主动风险所获得的超额收益越大，资产配置效率越高。"""
        story.append(Paragraph(summary_text, normal_style))
        story.append(Spacer(1, 0.3 * inch))
        story.append(PageBreak())

        story.append(Paragraph('二、方法论', heading1_style))
        methodology_text = """本报告采用以下分析方法：
1. 数据获取：从 ClickHouse 数据库获取历史日线价格数据
2. 收益率计算：采用对数收益率计算日收益率序列
3. 基准选择：美股使用 SPY，A股使用 000001.SH 或 399001.SZ
4. 主动收益计算：资产收益率减去基准收益率
5. 跟踪误差计算：主动收益的标准差（年化）
6. 信息比率计算：IR = 年化主动收益 / 年化跟踪误差
7. 可视化展示：绘制跟踪误差-主动收益散点图，射线斜率代表信息比率"""
        story.append(Paragraph(methodology_text, normal_style))
        story.append(Spacer(1, 0.3 * inch))
        story.append(PageBreak())

        for idx, result in enumerate(all_results, 1):
            story.append(Paragraph(f'三.{idx}. {result["name"]}', heading1_style))

            info_text = f"""市场类型: {result['market_type']}
基准指数: {result.get('benchmark', 'N/A')}
分析期间: {result.get('start_date', 'N/A')} 至 {result.get('end_date', 'N/A')}
分析资产数: {len(result.get('information_ratios', {}))}"""
            story.append(Paragraph(info_text, normal_style))
            story.append(Spacer(1, 0.2 * inch))

            story.append(Paragraph(f'三.{idx}.1 信息比率分析图', heading2_style))
            chart_path = result.get('chart_path')
            if chart_path and os.path.exists(chart_path):
                img = Image(chart_path, width=page_width, height=page_width * 0.6)
                story.append(img)
            story.append(Spacer(1, 0.2 * inch))

            story.append(Paragraph(f'三.{idx}.2 关键指标统计', heading2_style))
            information_ratios = result.get('information_ratios', {})
            active_returns = result.get('active_returns', {})
            tracking_errors = result.get('tracking_errors', {})
            benchmark = result.get('benchmark', None)

            if information_ratios:
                # 过滤掉基准指数
                filtered_assets = [asset for asset in information_ratios.keys() if asset != benchmark]
                
                table_data = [['资产代码', '主动收益 (%)', '跟踪误差 (%)', '信息比率 (IR)', '绩效评级']]

                # 按信息比率排序
                sorted_assets = [(asset, ir) for asset, ir in information_ratios.items() 
                                if asset != benchmark and not np.isnan(ir)]
                sorted_assets.sort(key=lambda x: x[1], reverse=True)

                for asset, ir in sorted_assets:
                    ar = active_returns.get(asset, 0) * 100
                    te = tracking_errors.get(asset, 0) * 100

                    # 绩效评级
                    if ir > 1.0:
                        rating = '优秀'
                    elif ir > 0.5:
                        rating = '良好'
                    elif ir > 0:
                        rating = '一般'
                    else:
                        rating = '较差'

                    table_data.append([
                        str(asset)[:20],
                        f"{ar:.2f}",
                        f"{te:.2f}",
                        f"{ir:.4f}",
                        rating
                    ])

                table = Table(table_data, colWidths=[2.0 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch, 1.0 * inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), self.reportlab_font),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('FONTNAME', (0, 1), (-1, -1), self.reportlab_font),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                story.append(table)

                # 统计摘要
                valid_irs = [ir for _, ir in sorted_assets]
                if valid_irs:
                    avg_ir = np.mean(valid_irs)
                    max_ir = max(valid_irs)
                    min_ir = min(valid_irs)
                    positive_count = sum(1 for ir in valid_irs if ir > 0)
                    
                    stats_text = f"""
信息比率统计摘要：
• 平均信息比率: {avg_ir:.4f}
• 最高信息比率: {max_ir:.4f}
• 最低信息比率: {min_ir:.4f}
• 正 IR 资产数量: {positive_count}/{len(valid_irs)}
"""
                    story.append(Paragraph(stats_text, normal_style))

            story.append(Spacer(1, 0.2 * inch))

            story.append(Paragraph(f'三.{idx}.3 投资建议', heading2_style))
            if information_ratios and active_returns:
                # 过滤掉基准
                filtered_ir = {k: v for k, v in information_ratios.items() if k != benchmark and not np.isnan(v)}
                filtered_ar = {k: v for k, v in active_returns.items() if k != benchmark}
                
                high_ir_assets = [k for k, v in filtered_ir.items() if v > 0.5]
                positive_ar_assets = [k for k, v in filtered_ar.items() if v > 0]

                advice_text = f"""根据信息比率分析结果：

高信息比率资产 (IR > 0.5)：
{', '.join(str(a)[:15] for a in high_ir_assets[:5]) if high_ir_assets else '无'}

正主动收益资产：
{', '.join(str(a)[:15] for a in positive_ar_assets[:5]) if positive_ar_assets else '无'}

投资建议：
• 优选高 IR 资产：信息比率高的资产具有更好的风险调整后收益
• 关注主动收益：选择能够持续跑赢基准的资产
• 控制跟踪误差：过高的跟踪误差可能意味着过度偏离基准
• 分散化配置：结合不同 IR 特征的资产，平衡收益与风险
• 定期再平衡：根据 IR 变化动态调整资产配置比例
"""
                story.append(Paragraph(advice_text, normal_style))

            if idx < len(all_results):
                story.append(PageBreak())

        story.append(PageBreak())
        story.append(Paragraph('四、综合对比分析', heading1_style))

        us_results = [r for r in all_results if r.get('market_type') == 'US']
        cn_results = [r for r in all_results if r.get('market_type') == 'CN']

        comparison_text = f"""美股组合数量: {len(us_results)}
A 股组合数量: {len(cn_results)}

市场特征对比：
• 美股市场：成熟度高，基准（SPY）表现稳定，IR 分布相对集中
• A 股市场：波动性较大，个股分化明显，高 IR 资产机会更多

跨市场配置建议：
• 建议采用全球化资产配置策略，分散单一市场风险
• 可结合美股稳定资产 + A 股高 IR 资产的组合配置
• 关注汇率风险对不同市场 IR 的影响
• 根据不同市场的经济周期调整配置比例
"""
        story.append(Paragraph(comparison_text, normal_style))
        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph('五、风险提示', heading1_style))
        risk_text = """本报告基于历史数据进行量化分析，仅供参考，不构成投资建议。投资有风险，入市需谨慎。

主要风险因素：
1. 模型风险：信息比率假设收益率服从正态分布，实际情况可能存在偏差
2. 基准选择风险：不同的基准指数会导致 IR 计算结果差异
3. 参数估计风险：跟踪误差的估计可能受到样本期间影响
4. 市场风险：市场环境变化可能导致历史关系失效
5. 流动性风险：部分资产可能存在流动性不足的问题
6. 再平衡成本：实际调仓过程中会产生交易成本

建议投资者结合自身风险承受能力，进行独立判断和决策。"""
        story.append(Paragraph(risk_text, normal_style))

        doc.build(story)
        logger.info(f"✅ 综合分析报告已生成: {output_path}")

        return output_path

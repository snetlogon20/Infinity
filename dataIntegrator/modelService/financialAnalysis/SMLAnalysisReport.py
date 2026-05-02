"""
SML 分析报告生成器 - 用于将多个 PNG 图表合并为专业 PDF 报告
"""
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from dataIntegrator import CommonLib, CommonParameters

logger = CommonLib.logger


class SMLAnalysisReport:
    """SML 分析报告生成器"""

    def __init__(self):
        self.reportlab_font = self._register_chinese_font()
        self._ensure_output_directory()

    def _ensure_output_directory(self):
        """确保输出目录存在"""
        self.output_dir = os.path.join(CommonParameters.outBoundPath, "report", "SMLAnalysis")
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"✅ 创建 SMLAnalysis 报告目录: {self.output_dir}")

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
            logger.warning("️ 没有图表路径，无法生成 PDF")
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

    def generate_sml_analysis_pdf(self, chart_paths, report_name, market_type="CN", start_date=None, end_date=None, output_path=None):
        """
        生成 SML 分析专用 PDF 报告

        参数:
        - chart_paths: SML 图表路径列表 [(path, title), ...]
        - report_name: 报告名称
        - market_type: 市场类型
        - start_date: 开始日期
        - end_date: 结束日期
        - output_path: 输出路径

        返回:
        - pdf_path: PDF 文件路径
        """
        report_title = '证券市场线 (SML) 分析报告'
        report_subtitle = f'报告名称: {report_name}\n市场类型: {market_type}'
        if start_date and end_date:
            report_subtitle += f'\n日期范围: {start_date} 至 {end_date}'

        return self.generate_multi_chart_pdf(
            chart_paths=chart_paths,
            report_title=report_title,
            report_subtitle=report_subtitle,
            output_path=output_path
        )

    def generate_comprehensive_pdf(self, all_results, report_title="SML 综合分析研究报告", output_path=None):
        """
        生成综合分析报告，合并所有测试案例并添加专业分析

        参数:
        - all_results: 所有测试结果列表，每个元素包含 {
            'name': 案例名称,
            'market_type': 市场类型,
            'chart_path': PNG 路径,
            'betas': β值字典,
            'expected_returns': 预期收益率字典,
            'market_symbol': 市场指数,
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
        summary_text = f"""本报告对 {len(all_results)} 个投资组合进行了证券市场线 (SML) 分析，涵盖美股和 A 股市场。
通过计算各资产的 β 值和预期收益率，评估其风险收益特征。
报告基于资本资产定价模型 (CAPM)，为投资决策提供量化参考。"""
        story.append(Paragraph(summary_text, normal_style))
        story.append(Spacer(1, 0.3 * inch))
        story.append(PageBreak())

        story.append(Paragraph('二、方法论', heading1_style))
        methodology_text = """本报告采用以下分析方法：
1. 数据获取：从 ClickHouse 数据库获取历史日线价格数据
2. 收益率计算：采用对数收益率计算日收益率序列
3. β 值计算：通过线性回归计算各资产相对于市场指数的系统性风险
4. 预期收益率：基于 CAPM 模型计算理论预期收益率
5. SML 绘制：可视化展示风险与收益的关系"""
        story.append(Paragraph(methodology_text, normal_style))
        story.append(Spacer(1, 0.3 * inch))
        story.append(PageBreak())

        for idx, result in enumerate(all_results, 1):
            story.append(Paragraph(f'三.{idx}. {result["name"]}', heading1_style))

            info_text = f"""市场类型: {result['market_type']}
市场指数: {result.get('market_symbol', 'N/A')}
分析期间: {result.get('start_date', 'N/A')} 至 {result.get('end_date', 'N/A')}
分析资产数: {len(result.get('betas', {}))}"""
            story.append(Paragraph(info_text, normal_style))
            story.append(Spacer(1, 0.2 * inch))

            story.append(Paragraph(f'三.{idx}.1 SML 分析图', heading2_style))
            chart_path = result.get('chart_path')
            if chart_path and os.path.exists(chart_path):
                img = Image(chart_path, width=page_width, height=page_width * 0.6)
                story.append(img)
            story.append(Spacer(1, 0.2 * inch))

            story.append(Paragraph(f'三.{idx}.2 关键指标统计', heading2_style))
            betas = result.get('betas', {})
            expected_returns = result.get('expected_returns', {})

            if betas:
                table_data = [['资产代码', 'β 值', '预期收益率 (%)', '风险特征']]

                sorted_betas = sorted(betas.items(), key=lambda x: x[1], reverse=True)

                for asset, beta in sorted_betas:
                    if asset == result.get('market_symbol'):
                        continue
                    exp_return = expected_returns.get(asset, 0) * 100

                    if beta < 0.8:
                        risk_feature = '防御型'
                    elif beta > 1.2:
                        risk_feature = '进攻型'
                    else:
                        risk_feature = '稳健型'

                    table_data.append([
                        str(asset)[:15],
                        f"{beta:.4f}",
                        f"{exp_return:.2f}",
                        risk_feature
                    ])

                table = Table(table_data, colWidths=[2.5 * inch, 1 * inch, 1.5 * inch, 1.5 * inch])
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

                betas_values = [v for k, v in betas.items() if k != result.get('market_symbol')]
                if betas_values:
                    avg_beta = sum(betas_values) / len(betas_values)
                    max_beta = max(betas_values)
                    min_beta = min(betas_values)

                    stats_text = f"""
统计分析：
• 平均 β 值: {avg_beta:.4f}
• 最高 β 值: {max_beta:.4f} (最高系统性风险)
• 最低 β 值: {min_beta:.4f} (最低系统性风险)
• 资产分散度: {'高' if (max_beta - min_beta) > 0.5 else '中' if (max_beta - min_beta) > 0.3 else '低'}
"""
                    story.append(Paragraph(stats_text, normal_style))

            story.append(Spacer(1, 0.2 * inch))

            story.append(Paragraph(f'三.{idx}.3 投资建议', heading2_style))
            if betas:
                defensive_assets = [k for k, v in betas.items() if v < 0.8 and k != result.get('market_symbol')]
                aggressive_assets = [k for k, v in betas.items() if v > 1.2 and k != result.get('market_symbol')]

                advice_text = f"""根据 SML 分析结果：

防御型资产 (β < 0.8)：
{', '.join(str(a)[:12] for a in defensive_assets[:5]) if defensive_assets else '无'}

进攻型资产 (β > 1.2)：
{', '.join(str(a)[:12] for a in aggressive_assets[:5]) if aggressive_assets else '无'}

投资建议：
• 保守型投资者：建议增加防御型资产配置比例
• 激进型投资者：可适当配置进攻型资产以获取超额收益
• 平衡型投资者：建议采用核心-卫星策略，核心配置稳健型资产
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
• 美股市场：资产类别丰富，涵盖科技、金融、消费等多个行业
• A 股市场：以蓝筹股为主，受政策影响较大，波动性相对较高

跨市场配置建议：
• 建议采用全球化资产配置策略，分散单一市场风险
• 可考虑美股科技股 + A 股消费股的组合配置
• 关注汇率风险，适当使用对冲工具
"""
        story.append(Paragraph(comparison_text, normal_style))
        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph('五、风险提示', heading1_style))
        risk_text = """本报告基于历史数据进行量化分析，仅供参考，不构成投资建议。投资有风险，入市需谨慎。

主要风险因素：
1. 市场风险：β 值基于历史数据计算，未来可能发生变化
2. 模型风险：CAPM 模型假设市场完全有效，实际情况可能存在偏差
3. 数据风险：数据质量和完整性可能影响分析结果
4. 流动性风险：部分资产可能存在流动性不足的问题

建议投资者结合自身风险承受能力，进行独立判断和决策。"""
        story.append(Paragraph(risk_text, normal_style))

        doc.build(story)
        logger.info(f"✅ 综合分析报告已生成: {output_path}")

        return output_path

"""
SOR (索提诺比率) 分析报告生成器 - 用于将多个 PNG 图表合并为专业 PDF 报告
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

logger = CommonLib.logger


class SORAnalysisReport:
    """SOR (索提诺比率) 分析报告生成器"""

    def __init__(self):
        self.reportlab_font = self._register_chinese_font()
        self._ensure_output_directory()

    def _ensure_output_directory(self):
        """确保输出目录存在"""
        self.output_dir = os.path.join(CommonParameters.outBoundPath, "report", "SORAnalysis")
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"✅ 创建 SORAnalysis 报告目录: {self.output_dir}")

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

    def generate_sor_analysis_pdf(self, chart_paths, report_name, market_type="CN", start_date=None, end_date=None, output_path=None):
        """
        生成 SOR 分析专用 PDF 报告

        参数:
        - chart_paths: SOR 图表路径列表 [(path, title), ...]
        - report_name: 报告名称
        - market_type: 市场类型
        - start_date: 开始日期
        - end_date: 结束日期
        - output_path: 输出路径

        返回:
        - pdf_path: PDF 文件路径
        """
        report_title = '索提诺比率 (Sortino Ratio) 分析报告'
        report_subtitle = f'报告名称: {report_name}\n市场类型: {market_type}'
        if start_date and end_date:
            report_subtitle += f'\n日期范围: {start_date} 至 {end_date}'

        return self.generate_multi_chart_pdf(
            chart_paths=chart_paths,
            report_title=report_title,
            report_subtitle=report_subtitle,
            output_path=output_path
        )

    def generate_comprehensive_pdf(self, all_results, report_title="SOR 综合分析研究报告", output_path=None):
        """
        生成综合分析报告，合并所有测试案例并添加专业分析

        参数:
        - all_results: 所有测试结果列表，每个元素包含 {
            'name': 案例名称,
            'market_type': 市场类型,
            'chart_path': PNG 路径,
            'expected_returns': 预期收益率字典,
            'downside_deviations': 下行偏差字典,
            'sor_ratios': 索提诺比率字典,
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
            logger.warning("️ 没有测试结果，无法生成综合报告")
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
        summary_text = f"""本报告对 {len(all_results)} 个投资组合进行了索提诺比率 (Sortino Ratio) 分析，涵盖美股和 A 股市场。
索提诺比率只考虑下行风险，更适合评估风险厌恶型投资者的资产配置。
报告基于现代投资组合理论 (MPT)，为资产配置提供量化参考。"""
        story.append(Paragraph(summary_text, normal_style))
        story.append(Spacer(1, 0.3 * inch))
        story.append(PageBreak())

        story.append(Paragraph('二、方法论', heading1_style))
        methodology_text = """本报告采用以下分析方法：
1. 数据获取：从 ClickHouse 数据库获取历史日线价格数据
2. 收益率计算：采用对数收益率计算日收益率序列
3. 下行偏差计算：只考虑负收益的波动，计算年化下行偏差
4. 索提诺比率计算：SOR = (预期收益率 - 无风险利率) / 下行偏差
5. SOR 分析图绘制：可视化展示各资产的下行风险与预期收益关系
6. 跨市场对比：对比不同市场的下行风险特征"""
        story.append(Paragraph(methodology_text, normal_style))
        story.append(Spacer(1, 0.3 * inch))
        story.append(PageBreak())

        for idx, result in enumerate(all_results, 1):
            story.append(Paragraph(f'三.{idx}. {result["name"]}', heading1_style))

            info_text = f"""市场类型: {result['market_type']}
市场指数: {result.get('market_symbol', 'N/A')}
分析期间: {result.get('start_date', 'N/A')} 至 {result.get('end_date', 'N/A')}
分析资产数: {len(result.get('expected_returns', {}))}"""
            story.append(Paragraph(info_text, normal_style))
            story.append(Spacer(1, 0.2 * inch))

            story.append(Paragraph(f'三.{idx}.1 SOR 分析图', heading2_style))
            chart_path = result.get('chart_path')
            if chart_path and os.path.exists(chart_path):
                img = Image(chart_path, width=page_width, height=page_width * 0.6)
                story.append(img)
            story.append(Spacer(1, 0.2 * inch))

            story.append(Paragraph(f'三.{idx}.2 关键指标统计', heading2_style))
            expected_returns = result.get('expected_returns', {})
            downside_deviations = result.get('downside_deviations', {})
            sor_ratios = result.get('sor_ratios', {})
            market_symbol = result.get('market_symbol', None)

            if expected_returns:
                # 过滤掉市场指数
                filtered_assets = [(asset, exp_return) for asset, exp_return in expected_returns.items()
                                  if asset != market_symbol]
                filtered_assets.sort(key=lambda x: x[1], reverse=True)

                table_data = [['资产代码', '预期收益率 (%)', '下行偏差 (%)', '索提诺比率', '风险评级']]

                for asset, exp_return in filtered_assets:
                    dd = downside_deviations.get(asset, 0) * 100
                    exp_ret_pct = exp_return * 100
                    sr = sor_ratios.get(asset, np.nan)

                    if sr > 1.0:
                        risk_rating = '优秀'
                    elif sr > 0.5:
                        risk_rating = '良好'
                    elif sr > 0:
                        risk_rating = '一般'
                    else:
                        risk_rating = '较差'

                    sr_str = f"{sr:.4f}" if not np.isnan(sr) else 'N/A'

                    table_data.append([
                        str(asset)[:20],
                        f"{exp_ret_pct:.2f}",
                        f"{dd:.2f}",
                        sr_str,
                        risk_rating
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

            story.append(Spacer(1, 0.2 * inch))

            story.append(Paragraph(f'三.{idx}.3 投资建议', heading2_style))
            if expected_returns and downside_deviations:
                filtered_sr = {k: v for k, v in sor_ratios.items()
                              if k != market_symbol and not np.isnan(v)}

                excellent_assets = [k for k, v in filtered_sr.items() if v > 1.0]
                poor_assets = [k for k, v in filtered_sr.items() if v <= 0]

                advice_text = f"""根据 SOR 分析结果：

优秀资产 (SOR > 1.0)：
{', '.join(str(a)[:12] for a in excellent_assets[:5]) if excellent_assets else '无'}

较差资产 (SOR ≤ 0)：
{', '.join(str(a)[:12] for a in poor_assets[:5]) if poor_assets else '无'}

投资建议：
• 风险厌恶型投资者：优先选择 SOR > 1.0 的资产，获取优异的下行风险调整后收益
• 稳健型投资者：选择 SOR > 0.5 的资产，平衡收益与下行风险
• 避免 SOR ≤ 0 的资产，预期收益无法覆盖无风险利率
• 下行风险控制：索提诺比率更适合评估熊市或市场下跌时的资产表现
• 资产配置：结合夏普比率和索提诺比率，全面评估资产的风险收益特征
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
• 美股市场：资产类别丰富，下行风险控制较好，SOR 普遍较高
• A 股市场：波动性较大，下行风险相对较高，SOR 分化明显

跨市场配置建议：
• 建议采用全球化资产配置策略，分散单一市场下行风险
• 可考虑美股稳定资产 + A 股成长资产的组合配置
• 关注汇率风险，适当使用对冲工具
• 根据不同市场的经济周期调整配置比例
"""
        story.append(Paragraph(comparison_text, normal_style))
        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph('五、风险提示', heading1_style))
        risk_text = """本报告基于历史数据进行量化分析，仅供参考，不构成投资建议。投资有风险，入市需谨慎。

主要风险因素：
1. 模型风险：SOR 假设收益率分布对称，实际可能存在偏态分布
2. 参数估计风险：下行偏差的估计误差可能影响 SOR 计算结果
3. 市场风险：市场环境变化可能导致历史关系失效
4. 流动性风险：部分资产可能存在流动性不足的问题
5. 尾部风险：SOR 未考虑极端事件的影响

建议投资者结合自身风险承受能力，进行独立判断和决策。"""
        story.append(Paragraph(risk_text, normal_style))

        doc.build(story)
        logger.info(f"✅ 综合分析报告已生成: {output_path}")

        return output_path

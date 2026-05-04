"""
Treynor Ratio 分析报告生成器 - 用于将多个 PNG 图表合并为专业 PDF 报告
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


class TreynorRatioAnalysisReport:
    """特雷诺比率分析报告生成器"""

    def __init__(self):
        self.reportlab_font = self._register_chinese_font()
        self._ensure_output_directory()

    def _ensure_output_directory(self):
        """确保输出目录存在"""
        self.output_dir = os.path.join(CommonParameters.outBoundPath, "report", "TreynorRatioAnalysis")
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"✅ 创建 TreynorRatioAnalysis 报告目录: {self.output_dir}")

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

    def generate_treynor_analysis_pdf(self, chart_paths, report_name, market_type="CN", start_date=None, end_date=None, output_path=None):
        """
        生成特雷诺比率分析专用 PDF 报告

        参数:
        - chart_paths: 特雷诺比率图表路径列表 [(path, title), ...]
        - report_name: 报告名称
        - market_type: 市场类型
        - start_date: 开始日期
        - end_date: 结束日期
        - output_path: 输出路径

        返回:
        - pdf_path: PDF 文件路径
        """
        report_title = '特雷诺比率 (Treynor Ratio) 分析报告'
        report_subtitle = f'报告名称: {report_name}\n市场类型: {market_type}'
        if start_date and end_date:
            report_subtitle += f'\n日期范围: {start_date} 至 {end_date}'

        return self.generate_multi_chart_pdf(
            chart_paths=chart_paths,
            report_title=report_title,
            report_subtitle=report_subtitle,
            output_path=output_path
        )

    def generate_comprehensive_pdf(self, all_results, report_title="特雷诺比率 (Treynor Ratio) 综合分析研究报告", output_path=None):
        """
        生成综合分析报告，合并所有测试案例并添加专业分析

        参数:
        - all_results: 所有测试结果列表，每个元素包含 {
            'name': 案例名称,
            'market_type': 市场类型,
            'chart_path': PNG 路径,
            'betas': β 字典,
            'expected_returns': 预期收益率字典,
            'treynor_ratios': 特雷诺比率字典,
            'risk_free_rate': 无风险利率,
            'market_return': 市场收益率,
            'market_risk_premium': 市场风险溢价,
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
        summary_text = f"""本报告对 {len(all_results)} 个投资组合进行了特雷诺比率 (Treynor Ratio) 分析，涵盖美股和 A 股市场。
特雷诺比率衡量的是单位系统性风险 (β) 所获得的超额收益，适用于评估充分分散的投资组合。
报告通过线性回归计算各资产的 β 值，结合历史收益率和无风险利率，为资产配置提供量化参考。"""
        story.append(Paragraph(summary_text, normal_style))
        story.append(Spacer(1, 0.3 * inch))
        story.append(PageBreak())

        story.append(Paragraph('二、方法论', heading1_style))
        methodology_text = """本报告采用以下分析方法：
1. 数据获取：从 ClickHouse 数据库获取历史日线价格数据
2. 收益率计算：采用对数收益率计算日收益率序列
3. β 计算：使用 OLS 线性回归计算各资产相对于市场组合的 β 值
4. 预期收益率：使用历史平均年化收益率作为预期收益率
5. 特雷诺比率计算：TR = (E(Rp) - Rf) / βp
6. 可视化分析：绘制 β - 预期收益率散点图，标注特雷诺比率和 SML 参考线"""
        story.append(Paragraph(methodology_text, normal_style))
        story.append(Spacer(1, 0.3 * inch))
        story.append(PageBreak())

        for idx, result in enumerate(all_results, 1):
            story.append(Paragraph(f'三.{idx}. {result["name"]}', heading1_style))

            info_text = f"""市场类型: {result['market_type']}
市场指数: {result.get('market_symbol', 'N/A')}
分析期间: {result.get('start_date', 'N/A')} 至 {result.get('end_date', 'N/A')}
无风险利率: {result.get('risk_free_rate', 0)*100:.2f}%
市场风险溢价: {result.get('market_risk_premium', 0)*100:.2f}%
分析资产数: {len(result.get('betas', {}))}"""
            story.append(Paragraph(info_text, normal_style))
            story.append(Spacer(1, 0.2 * inch))

            story.append(Paragraph(f'三.{idx}.1 特雷诺比率分析图', heading2_style))
            chart_path = result.get('chart_path')
            if chart_path and os.path.exists(chart_path):
                img = Image(chart_path, width=page_width, height=page_width * 0.6)
                story.append(img)
            story.append(Spacer(1, 0.2 * inch))

            story.append(Paragraph(f'三.{idx}.2 关键指标统计', heading2_style))
            betas = result.get('betas', {})
            expected_returns = result.get('expected_returns', {})
            treynor_ratios = result.get('treynor_ratios', {})
            market_symbol = result.get('market_symbol', None)

            if betas:
                # 过滤掉市场指数
                filtered_assets = [asset for asset in betas.keys() if asset != market_symbol]
                
                table_data = [['资产代码', 'β (系统性风险)', '预期收益率 (%)', '特雷诺比率 (%)', '风险特征']]

                # 按特雷诺比率排序
                sorted_assets = [(asset, tr) for asset, tr in treynor_ratios.items() 
                                if asset != market_symbol and not (isinstance(tr, float) and tr != tr)]  # 排除NaN
                sorted_assets.sort(key=lambda x: x[1], reverse=True)

                for asset, tr in sorted_assets:
                    beta = betas.get(asset, 0)
                    exp_ret = expected_returns.get(asset, 0) * 100
                    tr_pct = tr * 100

                    if beta < 0.8:
                        risk_feature = '低系统性风险'
                    elif beta < 1.2:
                        risk_feature = '中等系统性风险'
                    else:
                        risk_feature = '高系统性风险'

                    table_data.append([
                        str(asset)[:15],
                        f"{beta:.4f}",
                        f"{exp_ret:.2f}",
                        f"{tr_pct:.2f}",
                        risk_feature
                    ])

                table = Table(table_data, colWidths=[1.8 * inch, 1.5 * inch, 1.3 * inch, 1.3 * inch, 1.3 * inch])
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

                stats_text = f"""
关键统计：
• 市场收益率: {result.get('market_return', 0)*100:.2f}%
• 市场风险溢价: {result.get('market_risk_premium', 0)*100:.2f}%
• 无风险利率: {result.get('risk_free_rate', 0)*100:.2f}%
• 最高特雷诺比率: {max([tr for asset, tr in treynor_ratios.items() if asset != market_symbol and not (isinstance(tr, float) and tr != tr)], default=0)*100:.2f}%
"""
                story.append(Paragraph(stats_text, normal_style))

            story.append(Spacer(1, 0.2 * inch))

            story.append(Paragraph(f'三.{idx}.3 投资建议', heading2_style))
            if betas and treynor_ratios:
                # 过滤掉市场指数
                filtered_treynor = {k: v for k, v in treynor_ratios.items() 
                                   if k != market_symbol and not (isinstance(v, float) and v != v)}
                filtered_betas = {k: v for k, v in betas.items() if k != market_symbol}
                
                high_tr_assets = [k for k, v in filtered_treynor.items() if v > 0.10]
                low_beta_assets = [k for k, v in filtered_betas.items() if v < 0.8]

                advice_text = f"""根据特雷诺比率分析结果：

高特雷诺比率资产 (TR > 10%)：
{', '.join(str(a)[:12] for a in high_tr_assets[:5]) if high_tr_assets else '无'}

低系统性风险资产 (β < 0.8)：
{', '.join(str(a)[:12] for a in low_beta_assets[:5]) if low_beta_assets else '无'}

投资建议：
• 特雷诺比率高的资产：单位系统性风险获得的超额收益较多，具备较好的风险调整后收益
• 特雷诺比率低的资产：可能存在定价偏差或风险未充分补偿
• 低 β 资产：适合风险厌恶型投资者，波动相对较小
• 高 β 资产：适合风险偏好型投资者，预期收益更高但风险也更大
• 充分分散的投资组合：特雷诺比率比夏普比率更适合评估组合表现
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
• 美股市场：市场成熟度高，β 分布相对集中，特雷诺比率较为稳定
• A 股市场：成长性较强，β 波动较大，特雷诺比率差异显著

跨市场配置建议：
• 建议采用全球化资产配置策略，分散单一市场系统性风险
• 可结合特雷诺比率选择各市场中的优质资产
• 关注不同市场的无风险利率差异，合理评估风险溢价
• 根据经济周期和市场环境动态调整配置比例
"""
        story.append(Paragraph(comparison_text, normal_style))
        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph('五、风险提示', heading1_style))
        risk_text = """本报告基于历史数据进行量化分析，仅供参考，不构成投资建议。投资有风险，入市需谨慎。

主要风险因素：
1. 模型风险：特雷诺比率假设资产已充分分散，仅考虑系统性风险
2. 参数估计风险：β 值的估计误差可能影响特雷诺比率的准确性
3. 市场风险：市场环境变化可能导致历史关系失效
4. 流动性风险：部分资产可能存在流动性不足的问题
5. 无风险利率选择：不同期限的无风险利率会影响计算结果

建议投资者结合自身风险承受能力，进行独立判断和决策。"""
        story.append(Paragraph(risk_text, normal_style))

        doc.build(story)
        logger.info(f"✅ 综合分析报告已生成: {output_path}")

        return output_path

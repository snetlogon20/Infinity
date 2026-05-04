"""
CML 分析报告生成器 - 用于将多个 PNG 图表合并为专业 PDF 报告
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


class CMLAnalysisReport:
    """CML 分析报告生成器"""

    def __init__(self):
        self.reportlab_font = self._register_chinese_font()
        self._ensure_output_directory()

    def _ensure_output_directory(self):
        """确保输出目录存在"""
        self.output_dir = os.path.join(CommonParameters.outBoundPath, "report", "CMLAnalysis")
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"✅ 创建 CMLAnalysis 报告目录: {self.output_dir}")

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

    def generate_cml_analysis_pdf(self, chart_paths, report_name, market_type="CN", start_date=None, end_date=None, output_path=None):
        """
        生成 CML 分析专用 PDF 报告

        参数:
        - chart_paths: CML 图表路径列表 [(path, title), ...]
        - report_name: 报告名称
        - market_type: 市场类型
        - start_date: 开始日期
        - end_date: 结束日期
        - output_path: 输出路径

        返回:
        - pdf_path: PDF 文件路径
        """
        report_title = '资本市场线 (CML) 分析报告'
        report_subtitle = f'报告名称: {report_name}\n市场类型: {market_type}'
        if start_date and end_date:
            report_subtitle += f'\n日期范围: {start_date} 至 {end_date}'

        return self.generate_multi_chart_pdf(
            chart_paths=chart_paths,
            report_title=report_title,
            report_subtitle=report_subtitle,
            output_path=output_path
        )

    def generate_comprehensive_pdf(self, all_results, report_title="CML 综合分析研究报告", output_path=None):
        """
        生成综合分析报告，合并所有测试案例并添加专业分析

        参数:
        - all_results: 所有测试结果列表，每个元素包含 {
            'name': 案例名称,
            'market_type': 市场类型,
            'chart_path': PNG 路径,
            'expected_returns': 预期收益率字典,
            'volatilities': 波动率字典,
            'max_sharpe_return': 最大夏普比率组合收益率,
            'max_sharpe_volatility': 最大夏普比率组合波动率,
            'max_sharpe_ratio': 最大夏普比率,
            'min_vol_return': 最小方差组合收益率,
            'min_vol_volatility': 最小方差组合波动率,
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
        summary_text = f"""本报告对 {len(all_results)} 个投资组合进行了资本市场线 (CML) 分析，涵盖美股和 A 股市场。
通过蒙特卡洛模拟和优化算法，寻找最优风险收益组合。
报告基于现代投资组合理论 (MPT)，为资产配置提供量化参考。"""
        story.append(Paragraph(summary_text, normal_style))
        story.append(Spacer(1, 0.3 * inch))
        story.append(PageBreak())

        story.append(Paragraph('二、方法论', heading1_style))
        methodology_text = """本报告采用以下分析方法：
1. 数据获取：从 ClickHouse 数据库获取历史日线价格数据
2. 收益率计算：采用对数收益率计算日收益率序列
3. 统计量计算：计算年化预期收益率、波动率和协方差矩阵
4. 投资组合优化：使用 SLSQP 算法优化最大夏普比率和最小方差组合
5. 有效前沿生成：通过约束优化生成有效前沿曲线
6. 蒙特卡洛模拟：随机生成 10000 个投资组合进行对比分析
7. CML 绘制：可视化展示资本市场线与有效前沿的关系"""
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

            story.append(Paragraph(f'三.{idx}.1 CML 分析图', heading2_style))
            chart_path = result.get('chart_path')
            if chart_path and os.path.exists(chart_path):
                img = Image(chart_path, width=page_width, height=page_width * 0.6)
                story.append(img)
            story.append(Spacer(1, 0.2 * inch))

            story.append(Paragraph(f'三.{idx}.2 关键指标统计', heading2_style))
            expected_returns = result.get('expected_returns', {})
            volatilities = result.get('volatilities', {})
            max_sharpe_weights = result.get('max_sharpe_weights', None)
            min_vol_weights = result.get('min_vol_weights', None)
            market_symbol = result.get('market_symbol', None)

            if expected_returns:
                # 获取股票代码列表（与权重数组顺序一致）
                stock_list = list(expected_returns.keys())
                
                # 过滤掉市场指数（如SPY、000001.SH等）
                filtered_stocks = [stock for stock in stock_list if stock != market_symbol]
                
                table_data = [['资产代码', '预期收益率 (%)', '波动率 (%)', '风险特征', 
                              '最小方差组合配置 (%)', '切点组合配置 (%)']]

                # 只统计非市场指数的资产
                sorted_assets = [(asset, exp_return) for asset, exp_return in expected_returns.items() 
                                if asset != market_symbol]
                sorted_assets.sort(key=lambda x: x[1], reverse=True)

                for asset, exp_return in sorted_assets:
                    vol = volatilities.get(asset, 0) * 100
                    exp_ret_pct = exp_return * 100

                    if vol < 15:
                        risk_feature = '低风险'
                    elif vol < 25:
                        risk_feature = '中风险'
                    else:
                        risk_feature = '高风险'

                    # 获取该资产在两种组合中的配置比例
                    min_vol_weight = 0.0
                    max_sharpe_weight = 0.0
                    
                    if min_vol_weights is not None and asset in stock_list:
                        asset_idx = stock_list.index(asset)
                        min_vol_weight = min_vol_weights[asset_idx] * 100
                    
                    if max_sharpe_weights is not None and asset in stock_list:
                        asset_idx = stock_list.index(asset)
                        max_sharpe_weight = max_sharpe_weights[asset_idx] * 100

                    table_data.append([
                        str(asset)[:15],
                        f"{exp_ret_pct:.2f}",
                        f"{vol:.2f}",
                        risk_feature,
                        f"{min_vol_weight:.2f}" if min_vol_weight > 0.01 else '-',
                        f"{max_sharpe_weight:.2f}" if max_sharpe_weight > 0.01 else '-'
                    ])

                table = Table(table_data, colWidths=[1.8 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch])
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
优化结果：
• 最大夏普比率: {result.get('max_sharpe_ratio', 0):.4f}
• 切点组合收益率: {result.get('max_sharpe_return', 0)*100:.2f}%
• 切点组合波动率: {result.get('max_sharpe_volatility', 0)*100:.2f}%
• 最小方差组合收益率: {result.get('min_vol_return', 0)*100:.2f}%
• 最小方差组合波动率: {result.get('min_vol_volatility', 0)*100:.2f}%
"""
                story.append(Paragraph(stats_text, normal_style))

            story.append(Spacer(1, 0.2 * inch))

            story.append(Paragraph(f'三.{idx}.3 投资建议', heading2_style))
            if expected_returns and volatilities:
                # 过滤掉市场指数
                filtered_volatilities = {k: v for k, v in volatilities.items() if k != market_symbol}
                filtered_expected_returns = {k: v for k, v in expected_returns.items() if k != market_symbol}
                
                low_risk_assets = [k for k, v in filtered_volatilities.items() if v < 0.15]
                high_return_assets = [k for k, v in filtered_expected_returns.items() if v > 0.15]

                advice_text = f"""根据 CML 分析结果：

低风险资产 (波动率 < 15%)：
{', '.join(str(a)[:12] for a in low_risk_assets[:5]) if low_risk_assets else '无'}

高收益资产 (预期收益率 > 15%)：
{', '.join(str(a)[:12] for a in high_return_assets[:5]) if high_return_assets else '无'}

投资建议：
• 保守型投资者：建议配置最小方差组合，降低整体风险
• 激进型投资者：可参考切点组合（最大夏普比率），获取最优风险调整后收益
• 平衡型投资者：建议在有效前沿上选择适合自身风险偏好的组合
• 分散化策略：通过资产配置降低非系统性风险，提升组合稳定性
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
• 美股市场：资产类别丰富，市场成熟度高，波动性相对较低
• A 股市场：成长性较强，政策影响显著，波动性相对较高

跨市场配置建议：
• 建议采用全球化资产配置策略，分散单一市场风险
• 可考虑美股稳定资产 + A 股成长资产的组合配置
• 关注汇率风险，适当使用对冲工具
• 根据不同市场的经济周期调整配置比例
"""
        story.append(Paragraph(comparison_text, normal_style))
        story.append(Spacer(1, 0.3 * inch))

        story.append(Paragraph('五、风险提示', heading1_style))
        risk_text = """本报告基于历史数据进行量化分析，仅供参考，不构成投资建议。投资有风险，入市需谨慎。

主要风险因素：
1. 模型风险：MPT 假设收益率服从正态分布，实际情况可能存在偏差
2. 参数估计风险：预期收益率和协方差矩阵的估计误差可能影响优化结果
3. 市场风险：市场环境变化可能导致历史关系失效
4. 流动性风险：部分资产可能存在流动性不足的问题
5. 再平衡成本：实际调仓过程中会产生交易成本

建议投资者结合自身风险承受能力，进行独立判断和决策。"""
        story.append(Paragraph(risk_text, normal_style))

        doc.build(story)
        logger.info(f"✅ 综合分析报告已生成: {output_path}")

        return output_path

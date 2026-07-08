"""
中国国债远期收益率计算器

从 df_tushare_yc_cb 读取国债到期收益率曲线数据（curve_type=0），
计算不同期限之间的远期收益率，并生成可视化图表和 PDF 报告
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator import CommonLib, CommonParameters
logger = CommonLib.logger
import os

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


class ChinaTreasuryForwardRateCalculator:
    """中国国债远期收益率计算器"""
    
    def __init__(self, output_dir=None):
        self.clickhouseService = ClickhouseService()
        # 使用 CommonParameters 中的路径配置
        self.output_dir = output_dir if output_dir else os.path.join(CommonParameters.reportPath, "TreasuryForwardRate")
        self.reportlab_font = self._register_chinese_font()
        
        # 期限配置（以年为单位）- 根据国债收益率曲线关键期限节点
        self.tenor_config = {
            '0.25': 0.25,      # 3个月
            '0.5': 0.5,        # 6个月
            '1': 1.0,          # 1年
            '2': 2.0,          # 2年
            '3': 3.0,          # 3年
            '5': 5.0,          # 5年
            '7': 7.0,          # 7年
            '10': 10.0,        # 10年
            '20': 20.0,        # 20年
            '30': 30.0,        # 30年
        }
        
        # 期限中文名称映射
        self.tenor_names = {
            '0.25': '3M',
            '0.5': '6M',
            '1': '1Y',
            '2': '2Y',
            '3': '3Y',
            '5': '5Y',
            '7': '7Y',
            '10': '10Y',
            '20': '20Y',
            '30': '30Y',
        }
    
    def _register_chinese_font(self):
        """注册中文字体用于 PDF 生成"""
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
    
    def _generate_forward_rate_pdf(self, chart_images, forward_rates_df, treasury_df, start_date, end_date, output_path=None):
        """
        生成国债远期收益率分析 PDF 报告
        
        参数:
        - chart_images: 图表对象列表 [(fig, title), ...]
        - forward_rates_df: 远期收益率 DataFrame
        - treasury_df: 原始国债收益率数据 DataFrame
        - start_date: 开始日期
        - end_date: 结束日期
        - output_path: 输出 PDF 路径
        
        返回:
        - pdf_path: PDF 文件路径
        """
        if not chart_images:
            logger.warning("⚠️ 没有图表，无法生成 PDF")
            return None

        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(
                self.output_dir,
                f"China_Treasury_Forward_Rate_Analysis_Report_{timestamp}.pdf"
            )

        logger.info(f"📄 开始生成 PDF 报告: {output_path}")
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

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

        # 封面
        story.append(Paragraph('中国国债远期收益率分析报告', title_style))
        story.append(Paragraph(f'分析期间: {start_date} 至 {end_date}', normal_style))
        story.append(Paragraph(f'数据来源: 中债国债收益率曲线 (curve_type=0)', normal_style))
        story.append(Paragraph(f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', normal_style))
        story.append(PageBreak())

        # 执行摘要
        story.append(Paragraph('一、执行摘要', heading1_style))
        summary_text = f"""本报告对中国国债到期收益率曲线进行了远期收益率分析，
分析期间从 {start_date} 至 {end_date}，涵盖 3M、6M、1Y、2Y、3Y、5Y、7Y、10Y、20Y、30Y 共 10 个期限。

报告通过计算不同期限之间的远期收益率，揭示市场对未来收益率走势的预期。
国债远期收益率是重要的无风险收益率基准，反映了市场对未来经济走势和货币政策
的预期，对债券定价、收益率衍生品定价和资产配置具有重要意义。"""
        story.append(Paragraph(summary_text, normal_style))
        story.append(Spacer(1, 0.3 * inch))
        story.append(PageBreak())

        # 方法论
        story.append(Paragraph('二、方法论', heading1_style))
        methodology_text = """本报告采用以下分析方法：

1. 数据获取：从 ClickHouse 数据库获取中国国债到期收益率曲线历史数据
   - 数据表：df_tushare_yc_cb
   - 筛选条件：curve_type = 0 (到期收益率)

2. 远期收益率计算：采用无套利定价原理计算远期收益率
   公式：F(t1, t2) = [(1 + R2 * T2) / (1 + R1 * T1)]^(1/(T2-T1)) - 1
   其中：
   - R1 = 较短期限的到期收益率
   - R2 = 较长期限的到期收益率  
   - T1 = 较短期限（以年为单位）
   - T2 = 较长期限（以年为单位）

3. 时间序列分析：绘制远期收益率历史走势，观察期限利差变化

4. 期限结构分析：绘制最新日期的远期收益率曲线，分析收益率曲线形态

5. 可视化展示：生成专业图表和 PDF 报告

主要期限组合包括：
- F(3M, 6M): 3个月至6个月远期收益率
- F(6M, 1Y): 6个月至1年远期收益率
- F(1Y, 2Y): 1年至2年远期收益率
- F(2Y, 3Y): 2年至3年远期收益率
- F(3Y, 5Y): 3年至5年远期收益率
- F(5Y, 7Y): 5年至7年远期收益率
- F(7Y, 10Y): 7年至10年远期收益率
- F(10Y, 20Y): 10年至20年远期收益率
- F(20Y, 30Y): 20年至30年远期收益率"""
        story.append(Paragraph(methodology_text, normal_style))
        story.append(Spacer(1, 0.3 * inch))
        story.append(PageBreak())

        # 图表展示
        story.append(Paragraph('三、图表分析', heading1_style))
        
        from io import BytesIO
        
        for idx, (fig, chart_title) in enumerate(chart_images, 1):
            story.append(Paragraph(f'三.{idx}. {chart_title}', heading2_style))
            
            # 将 matplotlib figure 转换为图片
            buf = BytesIO()
            fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            buf.seek(0)
            
            img = Image(buf, width=page_width, height=page_width * 0.6)
            story.append(img)
            story.append(Spacer(1, 0.3 * inch))
            
            # 关闭 figure 释放内存
            plt.close(fig)

            # 为不同图表添加专业解析
            if idx == 1:
                analysis_text = """图表说明：
本图展示了国债即期收益率的历史走势。即期收益率是国债到期收益率曲线的
基础数据，反映了不同期限国债在当前时点的收益率水平。

观察要点：
• 短期收益率（如3M、6M）对货币政策变化更敏感
• 长期收益率（如10Y、20Y、30Y）反映市场对未来经济的预期
• 收益率曲线形态：向上倾斜（正常）、平坦或倒挂
• 期限利差变化：反映市场对未来利率走势的预期"""
                story.append(Paragraph(analysis_text, normal_style))
            
            elif idx == 2:
                analysis_text = """图表说明：
本图展示了国债远期收益率的历史走势，便于观察不同期限组合的远期收益率变化趋势。

观察要点：
• 短期远期收益率（如 F(3M,6M)）波动性通常较大
• 长期远期收益率（如 F(20Y,30Y)）相对平稳
• 不同期限远期收益率的收敛或发散反映市场预期变化"""
                story.append(Paragraph(analysis_text, normal_style))
            
            elif idx == 3:
                analysis_text = """图表说明：
本图展示了国债远期收益率与即期收益率的历史对比走势。通过对比可以看出
远期收益率与即期收益率的偏离程度，反映市场对未来收益率走势的预期。

观察要点：
• 远期收益率高于即期收益率：市场预期未来收益率上升
• 远期收益率低于即期收益率：市场预期未来收益率下降
• 期限利差扩大：市场波动性增加
• 期限利差收窄：市场趋于稳定"""
                story.append(Paragraph(analysis_text, normal_style))

            if idx < len(chart_images):
                story.append(PageBreak())

        # 统计分析
        story.append(PageBreak())
        story.append(Paragraph('四、统计分析', heading1_style))
        
        # 构建统计表格
        forward_columns = [col for col in forward_rates_df.columns if col.startswith('F(')]
        if forward_columns:
            table_data = [['期限组合', '均值 (%)', '标准差 (%)', '最小值 (%)', '最大值 (%)', '最新值 (%)']]
            
            for col in forward_columns:
                mean_val = forward_rates_df[col].mean()
                std_val = forward_rates_df[col].std()
                min_val = forward_rates_df[col].min()
                max_val = forward_rates_df[col].max()
                latest_val = forward_rates_df[col].iloc[-1]
                
                table_data.append([
                    col,
                    f"{mean_val:.3f}",
                    f"{std_val:.3f}",
                    f"{min_val:.3f}",
                    f"{max_val:.3f}",
                    f"{latest_val:.3f}"
                ])
            
            table = Table(table_data, colWidths=[2.5 * inch, 1.3 * inch, 1.3 * inch, 1.3 * inch, 1.3 * inch, 1.3 * inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), self.reportlab_font),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('FONTNAME', (0, 1), (-1, -1), self.reportlab_font),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(table)

        story.append(Spacer(1, 0.3 * inch))
        
        # 投资建议
        story.append(Paragraph('五、市场解读与投资建议', heading1_style))
        interpretation_text = """基于上述国债远期收益率分析，我们提供以下市场解读：

1. 收益率预期：远期收益率反映了市场对未来即期收益率的预期。
   如果远期收益率曲线向上倾斜，表明市场预期未来收益率将上升；
   如果曲线向下倾斜（倒挂），则预期未来收益率将下降。

2. 宏观经济信号：国债远期收益率的期限结构可以解读为市场对未来
   经济增长和通胀的预期。陡峭的曲线通常预示着经济增长和通胀上升，
   平坦或倒挂的曲线可能预示着经济放缓或衰退风险。

3. 货币政策信号：远期收益率可以反映市场对未来货币政策走向的预期，
   包括央行加息、降息或维持收益率不变的可能性。

4. 风险管理：金融机构可以利用国债远期收益率进行收益率风险管理，
   通过国债期货、收益率互换等衍生品对冲收益率风险。

5. 资产配置：国债远期收益率为固定收益投资者提供了重要的参考基准，
   帮助判断债券定价是否合理，优化资产配置策略。

风险提示：
• 远期收益率基于无套利假设，实际市场可能存在流动性溢价和税收因素
• 历史数据不能完全预测未来走势
• 宏观经济政策变化可能改变收益率预期
• 市场突发事件可能导致远期收益率剧烈波动
• 国债收益率受供需关系、国际资本流动等多重因素影响

本报告仅供参考，不构成投资建议。"""
        story.append(Paragraph(interpretation_text, normal_style))

        doc.build(story)
        logger.info(f"✅ PDF 报告已生成: {output_path}")

        return output_path
    
    def fetch_treasury_data(self, start_date=None, end_date=None):
        """
        从ClickHouse获取国债收益率曲线数据
        
        参数:
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')
        
        返回:
        - pivot_df: 按日期透视后的国债收益率 DataFrame（列为不同期限）
        """
        if start_date is None:
            # 默认获取最近2年数据
            start_date = (datetime.now() - timedelta(days=720)).strftime('%Y%m%d')
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        
        # 构建期限列表字符串
        term_list = ','.join([f"'{term}'" for term in self.tenor_config.keys()])
        
        sql = f"""
        SELECT 
            trade_date,
            curve_term,
            yield
        FROM df_tushare_yc_cb
        WHERE trade_date >= '{start_date}' 
          AND trade_date <= '{end_date}'
          AND curve_type = '0'
          AND ts_code = '1001.CB'
          AND curve_term IN ({term_list})
        ORDER BY trade_date ASC, curve_term ASC
        """
        
        logger.info(f"查询国债收益率数据: {start_date} 至 {end_date}")
        logger.info(f"筛选条件: curve_type=0 (到期收益率), ts_code=1001.CB")

        df = self.clickhouseService.getDataFrameWithoutColumnsName(sql)
        
        if df.empty:
            raise ValueError(f"在 {start_date} 至 {end_date} 期间没有找到国债收益率数据")
        
        logger.info(f"成功获取 {len(df)} 条国债收益率记录")
        
        # 数据透视：将 curve_term 转为列
        pivot_df = df.pivot_table(
            index='trade_date',
            columns='curve_term',
            values='yield'
        ).reset_index()
        
        # 将列名转换为字符串（因为curve_term是float类型）
        pivot_df.columns = [str(col) for col in pivot_df.columns]
        
        # 重命名列 - 需要处理float转字符串后的差异（如1.0 vs 1）
        column_mapping = {}
        for term in self.tenor_config.keys():
            # 尝试多种字符串形式匹配
            for possible_str in [term, f"{float(term):.1f}", f"{float(term):.2f}"]:
                if possible_str in pivot_df.columns:
                    column_mapping[possible_str] = f'Y_{self.tenor_names[term]}'
                    break
        
        pivot_df.rename(columns=column_mapping, inplace=True)
        
        logger.info(f"数据透视完成，生成 {len(pivot_df)} 行 × {len(pivot_df.columns)} 列")
        return pivot_df
    
    def calculate_forward_rate(self, df):
        """
        计算远期收益率
        
        远期收益率公式:
        F(t1, t2) = [(1 + R2 * T2) / (1 + R1 * T1)]^(1/(T2-T1)) - 1
        
        其中:
        - R1 = 较短期限的即期收益率
        - R2 = 较长期限的即期收益率
        - T1 = 较短期限（以年为单位）
        - T2 = 较长期限（以年为单位）
        
        参数:
        - df: 包含即期收益率的DataFrame
        
        返回:
        - forward_rates_df: 远期收益率 DataFrame
        """
        logger.info("开始计算远期收益率...")
        
        # 复制原始数据
        forward_rates_df = df[['trade_date']].copy()
        
        # 获取期限列（格式为 Y_3M, Y_1Y 等）
        yield_columns = [col for col in df.columns if col.startswith('Y_')]
        
        if len(yield_columns) < 2:
            raise ValueError(f"数据中期限列不足，无法计算远期收益率。当前期限列: {yield_columns}")
        
        # 构建从简称到年数的映射 (如 '3M' -> 0.25)
        name_to_years = {self.tenor_names[k]: v for k, v in self.tenor_config.items()}
        
        # 按照期限排序
        def get_tenor_years(col_name):
            tenor_name = col_name.replace('Y_', '')
            return name_to_years.get(tenor_name, 0)
        
        sorted_yield_columns = sorted(yield_columns, key=get_tenor_years)
        
        # 计算所有相邻期限之间的远期收益率
        for i in range(len(sorted_yield_columns) - 1):
            shorter_col = sorted_yield_columns[i]
            longer_col = sorted_yield_columns[i + 1]
            
            # 获取期限对应的年数
            shorter_tenor_name = shorter_col.replace('Y_', '')
            longer_tenor_name = longer_col.replace('Y_', '')
            
            t1_years = name_to_years[shorter_tenor_name]
            t2_years = name_to_years[longer_tenor_name]
            
            # 获取收益率（转换为小数）
            r1 = df[shorter_col] / 100.0
            r2 = df[longer_col] / 100.0
            
            # 计算远期收益率
            # F = [(1 + R2 * T2) / (1 + R1 * T1)]^(1/(T2-T1)) - 1
            numerator = 1 + r2 * t2_years
            denominator = 1 + r1 * t1_years
            time_diff = t2_years - t1_years
            
            forward_rate = (numerator / denominator) ** (1 / time_diff) - 1
            
            # 创建远期收益率列名
            forward_col_name = f'F({shorter_tenor_name},{longer_tenor_name})'
            
            # 转换为百分比
            forward_rates_df[forward_col_name] = forward_rate * 100.0
            
            logger.info(f"计算 {forward_col_name} 远期收益率")
        
        logger.info(f"远期收益率计算完成，共 {len(forward_rates_df.columns) - 1} 个期限组合")
        return forward_rates_df
    
    def run(self, start_date=None, end_date=None, output_dir=None):
        """
        运行完整分析流程
        
        参数:
        - start_date: 开始日期
        - end_date: 结束日期
        - output_dir: 输出目录（可选，默认使用 CommonParameters.outBoundPath/report/TreasuryForwardRate）
        """
        logger.info("=" * 80)
        logger.info(" 中国国债远期收益率分析开始")
        logger.info("=" * 80)
        
        # 1. 获取数据
        treasury_df = self.fetch_treasury_data(start_date, end_date)
        
        # 2. 计算远期收益率
        forward_rates_df = self.calculate_forward_rate(treasury_df)
        
        # 3. 确保输出目录存在
        if output_dir is None:
            output_dir = self.output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成时间戳
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 4. 生成图表（仅用于PDF报告，不保存为单独文件）
        logger.info("📊 开始生成图表...")
        
        # 创建临时图表用于PDF报告
        import matplotlib.pyplot as plt
        from io import BytesIO
        
        chart_images = []
        
        # 4.1 即期收益率图表
        logger.info("生成即期收益率图表...")
        spot_fig = self._create_spot_rates_chart(treasury_df)
        chart_images.append((spot_fig, '国债即期收益率历史走势'))
        
        # 4.2 远期收益率图表（纯远期）
        logger.info("生成远期收益率图表...")
        forward_fig = self._create_forward_rates_chart(forward_rates_df, original_spot_df=None)
        chart_images.append((forward_fig, '国债远期收益率历史走势'))
        
        # 4.3 远期与即期对比图表
        logger.info("生成远期与即期对比图表...")
        comparison_fig = self._create_forward_rates_chart(forward_rates_df, original_spot_df=treasury_df)
        chart_images.append((comparison_fig, '国债远期收益率与即期收益率历史对比走势'))
        
        # 5. 生成 PDF 报告（直接传入图表对象）
        logger.info("📄 开始生成 PDF 报告...")
        pdf_path = self._generate_forward_rate_pdf(
            chart_images=chart_images,
            forward_rates_df=forward_rates_df,
            treasury_df=treasury_df,
            start_date=start_date,
            end_date=end_date
        )
        if pdf_path:
            logger.info(f"✅ PDF 报告已生成: {pdf_path}")
        
        logger.info("=" * 80)
        logger.info("✅ 中国国债远期收益率分析完成")
        logger.info(f"📁 输出目录: {output_dir}")
        logger.info("=" * 80)
        
        return forward_rates_df
    
    def _create_spot_rates_chart(self, spot_df, figsize=(14, 8)):
        """
        创建即期收益率图表（返回 Figure 对象，不保存）
        """
        import matplotlib.dates as mdates
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 获取即期收益率列
        spot_columns = [col for col in spot_df.columns if col.startswith('Y_')]
        
        if not spot_columns:
            raise ValueError("没有即期收益率数据可供绘制")
        
        # 转换日期为 datetime 对象
        spot_df_copy = spot_df.copy()
        spot_df_copy['trade_date_dt'] = [datetime.strptime(str(d), '%Y%m%d') for d in spot_df_copy['trade_date']]
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # 使用专业配色方案
        professional_colors = [
            '#E41A1C', '#377EB8', '#4DAF4A', '#984EA3', '#FF7F00',
            '#A65628', '#F781BF', '#999999', '#66C2A5', '#FC8D62',
            '#8DA0CB', '#E78AC3', '#A6D854', '#FFD92F', '#E5C494'
        ]
        # 如果即期收益率列超过预设颜色数量，循环使用
        if len(spot_columns) > len(professional_colors):
            spot_colors = professional_colors * (len(spot_columns) // len(professional_colors) + 1)
        else:
            spot_colors = professional_colors[:len(spot_columns)]
        
        for idx, col in enumerate(spot_columns):
            tenor_name = col.replace('Y_', '')
            label = f"Y({tenor_name})"
            ax.plot(spot_df_copy['trade_date_dt'], spot_df_copy[col], 
                   linewidth=1.5, label=label, color=spot_colors[idx], alpha=0.9)
        
        ax.set_xlabel('交易日期', fontsize=12)
        ax.set_ylabel('收益率 (%)', fontsize=12)
        ax.set_title('中国国债即期收益率历史走势', fontsize=14, fontweight='bold')
        ax.legend(loc='upper left', fontsize=9, ncol=2, framealpha=0.9)
        ax.grid(True, alpha=0.3)
        
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_minor_locator(mdates.MonthLocator(interval=1))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=10)
        
        if len(spot_df_copy) > 0:
            last_date = spot_df_copy['trade_date_dt'].iloc[-1]
            spot_labels = []
            for idx, col in enumerate(spot_columns):
                last_value = spot_df_copy[col].iloc[-1]
                if pd.notna(last_value):
                    spot_labels.append((col.replace('Y_', ''), last_value, spot_colors[idx]))
            spot_labels.sort(key=lambda x: x[1], reverse=True)
            for idx, (label, value, color) in enumerate(spot_labels):
                ax.text(last_date, value, f'  Y({label})', 
                       fontsize=9, fontweight='bold', color=color,
                       verticalalignment='center', horizontalalignment='left')
        
        fig.autofmt_xdate(bottom=0.2)
        plt.tight_layout()
        fig.subplots_adjust(right=0.85)
        
        return fig
    
    def _create_forward_rates_chart(self, forward_rates_df, original_spot_df=None, figsize=(14, 8)):
        """
        创建远期收益率图表（返回 Figure 对象，不保存）
        """
        import matplotlib.dates as mdates
        
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        forward_columns = [col for col in forward_rates_df.columns if col.startswith('F(')]
        
        if not forward_columns:
            raise ValueError("没有远期收益率数据可供绘制")
        
        forward_df_copy = forward_rates_df.copy()
        forward_df_copy['trade_date_dt'] = [datetime.strptime(str(d), '%Y%m%d') for d in forward_df_copy['trade_date']]
        
        spot_df_copy = None
        if original_spot_df is not None:
            spot_df_copy = original_spot_df.copy()
            spot_df_copy['trade_date_dt'] = [datetime.strptime(str(d), '%Y%m%d') for d in spot_df_copy['trade_date']]
        
        fig, ax = plt.subplots(figsize=figsize)
        
        if spot_df_copy is not None:
            spot_columns = [col for col in spot_df_copy.columns if col.startswith('Y_')]
            spot_styles = [
                {'linestyle': '--', 'linewidth': 1.0, 'alpha': 0.5, 'marker': 's', 'markersize': 3},
                {'linestyle': '-.', 'linewidth': 1.0, 'alpha': 0.5, 'marker': 'd', 'markersize': 3},
                {'linestyle': ':', 'linewidth': 1.0, 'alpha': 0.5, 'marker': '^', 'markersize': 3},
            ]
            for idx, col in enumerate(spot_columns):
                style = spot_styles[idx % len(spot_styles)]
                tenor_name = col.replace('Y_', '')
                label = f"即期 {tenor_name}"
                ax.plot(spot_df_copy['trade_date_dt'], spot_df_copy[col], 
                       label=label, color='gray', **style)
        
        professional_colors = [
            '#E41A1C', '#377EB8', '#4DAF4A', '#984EA3', '#FF7F00',
            '#A65628', '#F781BF', '#999999', '#66C2A5', '#FC8D62',
            '#8DA0CB', '#E78AC3', '#A6D854', '#FFD92F', '#E5C494'
        ]
        # 如果远期收益率列超过预设颜色数量，循环使用
        if len(forward_columns) > len(professional_colors):
            forward_colors = professional_colors * (len(forward_columns) // len(professional_colors) + 1)
        else:
            forward_colors = professional_colors[:len(forward_columns)]
        
        for idx, col in enumerate(forward_columns):
            ax.plot(forward_df_copy['trade_date_dt'], forward_df_copy[col], 
                   linewidth=2.0, label=col, color=forward_colors[idx], alpha=0.9)
        
        ax.set_xlabel('交易日期', fontsize=12)
        ax.set_ylabel('收益率 (%)', fontsize=12)
        title = '中国国债远期收益率 vs 即期收益率对比曲线' if spot_df_copy is not None else '中国国债远期收益率历史走势'
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.legend(loc='upper left', fontsize=9, ncol=2, framealpha=0.9)
        ax.grid(True, alpha=0.3)
        
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_minor_locator(mdates.MonthLocator(interval=1))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=10)
        
        if len(forward_df_copy) > 0:
            last_date = forward_df_copy['trade_date_dt'].iloc[-1]
            forward_labels = []
            for idx, col in enumerate(forward_columns):
                last_value = forward_df_copy[col].iloc[-1]
                if pd.notna(last_value):
                    forward_labels.append((col, last_value, forward_colors[idx]))
            forward_labels.sort(key=lambda x: x[1], reverse=True)
            for idx, (label, value, color) in enumerate(forward_labels):
                ax.text(last_date, value, f'  {label}', 
                       fontsize=9, fontweight='bold', color=color,
                       verticalalignment='center', horizontalalignment='left')
        
        fig.autofmt_xdate(bottom=0.2)
        plt.tight_layout()
        fig.subplots_adjust(right=0.85)
        
        return fig


if __name__ == '__main__':
    # 使用示例
    calculator = ChinaTreasuryForwardRateCalculator()
    
    # 运行分析（获取最近1年数据）
    result_df = calculator.run(
        start_date='20250510',  # 可选：指定开始日期
        end_date='20260510',    # 可选：指定结束日期
        output_dir=r'D:\workspace_python\infinity_data\outbound\report\TreasuryForwardRate'
    )
    
    # 显示结果统计
    print("\n" + "=" * 80)
    print("国债远期收益率统计摘要:")
    print("=" * 80)
    print(result_df.describe())
    print("\n最新日期的远期收益率:")
    print(result_df.iloc[-1])
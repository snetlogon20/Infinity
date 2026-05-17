"""
SHIBOR 远期利率计算器

从 df_tushare_shibor_daily 读取即期利率数据，
计算不同期限之间的远期利率，并生成可视化图表和 PDF 报告
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


class ShiborForwardRateCalculator:
    """SHIBOR 远期利率计算器"""
    
    def __init__(self, output_dir=None):
        self.clickhouseService = ClickhouseService()
        self.output_dir = output_dir if output_dir else os.path.join(CommonParameters.outBoundPath, "report", "ForwardRateCurve")
        self.reportlab_font = self._register_chinese_font()
        
        # 期限配置（以天为单位）
        self.tenor_config = {
            'tenor_on': 1,       # O/N (隔夜)
            'tenor_1w': 7,       # 1周
            'tenor_2w': 14,      # 2周
            'tenor_1m': 30,      # 1月（近似）
            'tenor_3m': 90,      # 3月
            'tenor_6m': 180,     # 6月
            'tenor_9m': 270,     # 9月
            'tenor_1y': 365,     # 1年
        }
        
        # 期限中文名称映射
        self.tenor_names = {
            'tenor_on': 'O/N',
            'tenor_1w': '1W',
            'tenor_2w': '2W',
            'tenor_1m': '1M',
            'tenor_3m': '3M',
            'tenor_6m': '6M',
            'tenor_9m': '9M',
            'tenor_1y': '1Y',
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
    
    def _generate_forward_rate_pdf(self, chart_paths, forward_rates_df, shibor_df, start_date, end_date, output_path=None):
        """
        生成远期利率分析 PDF 报告
        
        参数:
        - chart_paths: 图表路径列表 [(path, title), ...]
        - forward_rates_df: 远期利率 DataFrame
        - shibor_df: 原始 SHIBOR 数据 DataFrame
        - start_date: 开始日期
        - end_date: 结束日期
        - output_path: 输出 PDF 路径
        
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
                f"SHIBOR_远期利率分析报告_{timestamp}.pdf"
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
        story.append(Paragraph('SHIBOR 远期利率分析报告', title_style))
        story.append(Paragraph(f'分析期间: {start_date} 至 {end_date}', normal_style))
        story.append(Paragraph(f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', normal_style))
        story.append(PageBreak())

        # 执行摘要
        story.append(Paragraph('一、执行摘要', heading1_style))
        summary_text = f"""本报告对 SHIBOR（上海银行间同业拆放利率）进行了远期利率分析，
分析期间从 {start_date} 至 {end_date}，共 {len(shibor_df)} 个交易日。

报告通过计算不同期限之间的远期利率，揭示市场对未来利率走势的预期。
分析涵盖 O/N、1W、2W、1M、3M、6M、9M、1Y 共 8 个期限，
生成 7 个期限组合的远期利率曲线。

远期利率是金融市场重要的定价基准，反映了市场参与者对未来短期利率的预期，
对货币政策传导、债券定价和利率衍生品定价具有重要意义。"""
        story.append(Paragraph(summary_text, normal_style))
        story.append(Spacer(1, 0.3 * inch))
        story.append(PageBreak())

        # 方法论
        story.append(Paragraph('二、方法论', heading1_style))
        methodology_text = """本报告采用以下分析方法：

1. 数据获取：从 ClickHouse 数据库获取 SHIBOR 历史日线数据
2. 远期利率计算：采用无套利定价原理计算远期利率
   公式：F(t1, t2) = [(1 + R2 * T2) / (1 + R1 * T1)]^(1/(T2-T1)) - 1
   其中：
   - R1 = 较短期限的即期利率
   - R2 = 较长期限的即期利率  
   - T1 = 较短期限（以年为单位）
   - T2 = 较长期限（以年为单位）
3. 时间序列分析：绘制远期利率历史走势，观察期限利差变化
4. 期限结构分析：绘制最新日期的远期利率曲线，分析收益率曲线形态
5. 可视化展示：生成专业图表和 PDF 报告

期限组合包括：
- F(O/N, 1W): 隔夜至1周远期利率
- F(1W, 2W): 1周至2周远期利率
- F(2W, 1M): 2周至1月远期利率
- F(1M, 3M): 1月至3月远期利率
- F(3M, 6M): 3月至6月远期利率
- F(6M, 9M): 6月至9月远期利率
- F(9M, 1Y): 9月至1年远期利率"""
        story.append(Paragraph(methodology_text, normal_style))
        story.append(Spacer(1, 0.3 * inch))
        story.append(PageBreak())

        # 图表展示
        story.append(Paragraph('三、图表分析', heading1_style))
        
        for idx, (chart_path, chart_title) in enumerate(chart_paths, 1):
            if not os.path.exists(chart_path):
                logger.warning(f"⚠️ 图表文件不存在，跳过: {chart_path}")
                continue

            story.append(Paragraph(f'三.{idx}. {chart_title}', heading2_style))
            img = Image(chart_path, width=page_width, height=page_width * 0.6)
            story.append(img)
            story.append(Spacer(1, 0.3 * inch))

            # 为不同图表添加专业解析
            if idx == 1:
                analysis_text = """图表说明：
本图展示了SHIBOR即期利率的历史走势。即期利率是SHIBOR的基础数据，
反映了不同期限银行间同业拆借在当前时点的利率水平。

观察要点：
• 短期利率（如O/N、1W）对货币政策变化更敏感
• 长期利率（如9M、1Y）反映市场对未来经济的预期
• 利率曲线形态：向上倾斜（正常）、平坦或倒挂
• 期限利差变化：反映市场对未来利率走势的预期"""
                story.append(Paragraph(analysis_text, normal_style))
            
            elif idx == 2:
                analysis_text = """图表说明：
本图展示了SHIBOR远期利率的历史走势，便于观察不同期限组合的远期利率变化趋势。

观察要点：
• 短期远期利率（如 F(O/N,1W)）波动性通常较大
• 长期远期利率（如 F(9M,1Y)）相对平稳
• 不同期限远期利率的收敛或发散反映市场预期变化"""
                story.append(Paragraph(analysis_text, normal_style))
            
            elif idx == 3:
                analysis_text = """图表说明：
本图展示了SHIBOR远期利率与即期利率的历史对比走势。通过对比可以看出
远期利率与即期利率的偏离程度，反映市场对未来利率走势的预期。

观察要点：
• 远期利率高于即期利率：市场预期未来利率上升
• 远期利率低于即期利率：市场预期未来利率下降
• 期限利差扩大：市场波动性增加
• 期限利差收窄：市场趋于稳定"""
                story.append(Paragraph(analysis_text, normal_style))

            if idx < len(chart_paths):
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
        interpretation_text = f"""基于上述远期利率分析，我们提供以下市场解读：

1. 利率预期：远期利率反映了市场对未来即期利率的预期。
   如果远期利率曲线向上倾斜，表明市场预期未来利率将上升；
   如果曲线向下倾斜（倒挂），则预期未来利率将下降。

2. 货币政策信号：远期利率的期限结构可以解读为市场对未来
   货币政策的预期。央行加息预期会推高远期利率，
   降息预期则会压低远期利率。

3. 风险管理：金融机构可以利用远期利率进行利率风险管理，
   通过利率互换、远期利率协议等衍生品对冲利率风险。

4. 投资决策：债券投资者可以参考远期利率曲线判断债券定价
   是否合理，寻找套利机会。

风险提示：
• 远期利率基于无套利假设，实际市场可能存在流动性溢价
• 历史数据不能完全预测未来走势
• 宏观经济政策变化可能改变利率预期
• 市场突发事件可能导致远期利率剧烈波动

本报告仅供参考，不构成投资建议。"""
        story.append(Paragraph(interpretation_text, normal_style))

        doc.build(story)
        logger.info(f"✅ PDF 报告已生成: {output_path}")

        return output_path
    
    def fetch_shibor_data(self, start_date=None, end_date=None):
        """
        从ClickHouse获取SHIBOR数据
        
        参数:
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')
        
        返回:
        - df: SHIBOR数据 DataFrame
        """
        if start_date is None:
            # 默认获取最近2年数据
            start_date = (datetime.now() - timedelta(days=720)).strftime('%Y%m%d')
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        
        sql = f"""
        SELECT 
            trade_date,
            tenor_on,
            tenor_1w,
            tenor_2w,
            tenor_1m,
            tenor_3m,
            tenor_6m,
            tenor_9m,
            tenor_1y
        FROM df_tushare_shibor_daily
        WHERE trade_date >= '{start_date}' 
          AND trade_date <= '{end_date}'
        ORDER BY trade_date ASC
        """
        
        logger.info(f"查询SHIBOR数据: {start_date} 至 {end_date}")
        df = self.clickhouseService.getDataFrameWithoutColumnsName(sql)
        
        if df.empty:
            raise ValueError(f"在 {start_date} 至 {end_date} 期间没有找到SHIBOR数据")
        
        logger.info(f"成功获取 {len(df)} 条SHIBOR记录")
        return df
    
    def calculate_forward_rate(self, df):
        """
        计算远期利率
        
        远期利率公式:
        F(t1, t2) = [(1 + R2 * T2) / (1 + R1 * T1)]^(1/(T2-T1)) - 1
        
        其中:
        - R1 = 较短期限的即期利率
        - R2 = 较长期限的即期利率
        - T1 = 较短期限（以年为单位）
        - T2 = 较长期限（以年为单位）
        
        参数:
        - df: 包含即期利率的DataFrame
        
        返回:
        - forward_rates_df: 远期利率 DataFrame
        """
        logger.info("开始计算远期利率...")
        
        # 复制原始数据
        forward_rates_df = df[['trade_date']].copy()
        
        # 获取期限列
        tenor_columns = [col for col in self.tenor_config.keys() if col in df.columns]
        
        if len(tenor_columns) < 2:
            raise ValueError("数据中期限列不足，无法计算远期利率")
        
        # 计算所有相邻期限之间的远期利率
        for i in range(len(tenor_columns) - 1):
            shorter_tenor = tenor_columns[i]
            longer_tenor = tenor_columns[i + 1]
            
            # 获取期限对应的天数
            t1_days = self.tenor_config[shorter_tenor]
            t2_days = self.tenor_config[longer_tenor]
            
            # 转换为年
            t1_years = t1_days / 365.0
            t2_years = t2_days / 365.0
            
            # 获取利率（转换为小数）
            r1 = df[shorter_tenor] / 100.0
            r2 = df[longer_tenor] / 100.0
            
            # 计算远期利率
            # F = [(1 + R2 * T2) / (1 + R1 * T1)]^(1/(T2-T1)) - 1
            numerator = 1 + r2 * t2_years
            denominator = 1 + r1 * t1_years
            time_diff = t2_years - t1_years
            
            forward_rate = (numerator / denominator) ** (1 / time_diff) - 1
            
            # 创建远期利率列名
            shorter_name = self.tenor_names[shorter_tenor]
            longer_name = self.tenor_names[longer_tenor]
            forward_col_name = f'F({shorter_name},{longer_name})'
            
            # 转换为百分比
            forward_rates_df[forward_col_name] = forward_rate * 100.0
            
            logger.info(f"计算 {forward_col_name} 远期利率")
        
        logger.info(f"远期利率计算完成，共 {len(forward_rates_df.columns) - 1} 个期限组合")
        return forward_rates_df
    
    def plot_spot_rates(self, spot_df, save_path=None, figsize=(14, 8)):
        """
        绘制即期利率曲线
        
        参数:
        - spot_df: 即期利率DataFrame
        - save_path: 保存路径（如果为None，则显示图形）
        - figsize: 图形大小
        """
        logger.info("开始绘制即期利率曲线...")
        
        import matplotlib.dates as mdates
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 获取即期利率列
        spot_columns = [col for col in self.tenor_config.keys() if col in spot_df.columns]
        
        if not spot_columns:
            raise ValueError("没有即期利率数据可供绘制")
        
        # 转换日期为 datetime 对象（创建副本避免修改原始数据）
        spot_df_copy = spot_df.copy()
        spot_df_copy['trade_date_dt'] = [datetime.strptime(str(d), '%Y%m%d') for d in spot_df_copy['trade_date']]
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # 使用 viridis 颜色映射，与远期利率图表保持一致
        spot_colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(spot_columns)))
        
        for idx, col in enumerate(spot_columns):
            # 从期限配置中提取期限名称
            tenor_name = self.tenor_names[col]
            label = f"S({tenor_name})"
            ax.plot(spot_df_copy['trade_date_dt'], spot_df_copy[col], 
                   linewidth=1.5, label=label, color=spot_colors[idx], alpha=0.9)
        
        # 设置图形属性
        ax.set_xlabel('交易日期', fontsize=12)
        ax.set_ylabel('利率 (%)', fontsize=12)
        ax.set_title('SHIBOR 即期利率历史走势', fontsize=14, fontweight='bold')
        
        # 添加图例（分两列显示）
        ax.legend(loc='upper left', fontsize=9, ncol=2, framealpha=0.9)
        ax.grid(True, alpha=0.3)
        
        # 优化日期显示：只显示月份，自动调整间隔
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))  # 每2个月显示一次
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))  # 格式：YYYY-MM
        ax.xaxis.set_minor_locator(mdates.MonthLocator(interval=1))  # 每月小刻度
        
        # 设置标签格式
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=10)
        
        # ========== 在每条线的末端添加清晰标注 ==========
        if len(spot_df_copy) > 0:
            # 找到最后一个有效数据点的日期
            last_date = spot_df_copy['trade_date_dt'].iloc[-1]
            
            # 即期利率标注
            spot_labels = []
            for idx, col in enumerate(spot_columns):
                # 获取最后一行的值
                last_value = spot_df_copy[col].iloc[-1]
                if pd.notna(last_value):
                    spot_labels.append((self.tenor_names[col], last_value, spot_colors[idx]))
            
            # 按数值从大到小排序，从上到下标注
            spot_labels.sort(key=lambda x: x[1], reverse=True)
            
            # 添加即期利率标注
            for idx, (label, value, color) in enumerate(spot_labels):
                # 标注位置：直接在最后数据点处
                x_label_pos = last_date
                # y轴位置：使用实际数据值
                y_label_pos = value
                
                # 添加标注文字（去掉边框，紧贴线条）
                ax.text(x_label_pos, y_label_pos, f'  S({label})', 
                       fontsize=9, fontweight='bold', color=color,
                       verticalalignment='center',
                       horizontalalignment='left')
        
        # 调整布局，右侧留出标注空间
        fig.autofmt_xdate(bottom=0.2)  # 自动格式化日期，底部留出空间
        plt.tight_layout()
        # 调整右侧边距，为标注留出空间
        fig.subplots_adjust(right=0.85)
        
        # 保存或显示
        if save_path:
            # 确保目录存在
            os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else '.', exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"SHIBOR即期利率曲线已保存至: {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def plot_spot_rates(self, spot_df, save_path=None, figsize=(14, 8)):
        """
        绘制即期利率曲线
        
        参数:
        - spot_df: 即期利率DataFrame
        - save_path: 保存路径（如果为None，则显示图形）
        - figsize: 图形大小
        """
        logger.info("开始绘制即期利率曲线...")
        
        import matplotlib.dates as mdates
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 获取即期利率列
        spot_columns = [col for col in self.tenor_config.keys() if col in spot_df.columns]
        
        if not spot_columns:
            raise ValueError("没有即期利率数据可供绘制")
        
        # 转换日期为 datetime 对象（创建副本避免修改原始数据）
        spot_df_copy = spot_df.copy()
        spot_df_copy['trade_date_dt'] = [datetime.strptime(str(d), '%Y%m%d') for d in spot_df_copy['trade_date']]
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # 使用 viridis 颜色映射，与远期利率图表保持一致
        spot_colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(spot_columns)))
        
        for idx, col in enumerate(spot_columns):
            # 从期限配置中提取期限名称
            tenor_name = self.tenor_names[col]
            label = f"S({tenor_name})"
            ax.plot(spot_df_copy['trade_date_dt'], spot_df_copy[col], 
                   linewidth=1.5, label=label, color=spot_colors[idx], alpha=0.9)
        
        # 设置图形属性
        ax.set_xlabel('交易日期', fontsize=12)
        ax.set_ylabel('利率 (%)', fontsize=12)
        ax.set_title('SHIBOR 即期利率历史走势', fontsize=14, fontweight='bold')
        
        # 添加图例（分两列显示）
        ax.legend(loc='upper left', fontsize=9, ncol=2, framealpha=0.9)
        ax.grid(True, alpha=0.3)
        
        # 优化日期显示：只显示月份，自动调整间隔
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))  # 每2个月显示一次
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))  # 格式：YYYY-MM
        ax.xaxis.set_minor_locator(mdates.MonthLocator(interval=1))  # 每月小刻度
        
        # 设置标签格式
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=10)
        
        # ========== 在每条线的末端添加清晰标注 ==========
        if len(spot_df_copy) > 0:
            # 找到最后一个有效数据点的日期
            last_date = spot_df_copy['trade_date_dt'].iloc[-1]
            
            # 即期利率标注
            spot_labels = []
            for idx, col in enumerate(spot_columns):
                # 获取最后一行的值
                last_value = spot_df_copy[col].iloc[-1]
                if pd.notna(last_value):
                    spot_labels.append((self.tenor_names[col], last_value, spot_colors[idx]))
            
            # 按数值从大到小排序，从上到下标注
            spot_labels.sort(key=lambda x: x[1], reverse=True)
            
            # 添加即期利率标注
            for idx, (label, value, color) in enumerate(spot_labels):
                # 标注位置：直接在最后数据点处
                x_label_pos = last_date
                # y轴位置：使用实际数据值
                y_label_pos = value
                
                # 添加标注文字（去掉边框，紧贴线条）
                ax.text(x_label_pos, y_label_pos, f'  S({label})', 
                       fontsize=9, fontweight='bold', color=color,
                       verticalalignment='center',
                       horizontalalignment='left')
        
        # 调整布局，右侧留出标注空间
        fig.autofmt_xdate(bottom=0.2)  # 自动格式化日期，底部留出空间
        plt.tight_layout()
        # 调整右侧边距，为标注留出空间
        fig.subplots_adjust(right=0.85)
        
        # 保存或显示
        if save_path:
            # 确保目录存在
            os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else '.', exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"SHIBOR即期利率曲线已保存至: {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def plot_forward_rates(self, forward_rates_df, original_spot_df=None, save_path=None, figsize=(14, 8)):
        """
        绘制远期利率曲线（同时显示即期利率作为对比）
        
        参数:
        - forward_rates_df: 远期利率DataFrame
        - original_spot_df: 原始即期利率DataFrame（可选）
        - save_path: 保存路径（如果为None，则显示图形）
        - figsize: 图形大小
        """
        logger.info("开始绘制远期利率曲线...")
        
        import matplotlib.dates as mdates
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 获取远期利率列
        forward_columns = [col for col in forward_rates_df.columns if col.startswith('F(')]
        
        if not forward_columns:
            raise ValueError("没有远期利率数据可供绘制")
        
        # 转换日期为 datetime 对象（创建副本避免修改原始数据）
        forward_df_copy = forward_rates_df.copy()
        forward_df_copy['trade_date_dt'] = [datetime.strptime(str(d), '%Y%m%d') for d in forward_df_copy['trade_date']]
        
        spot_df_copy = None
        if original_spot_df is not None:
            spot_df_copy = original_spot_df.copy()
            spot_df_copy['trade_date_dt'] = [datetime.strptime(str(d), '%Y%m%d') for d in spot_df_copy['trade_date']]
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # 绘制即期利率曲线（如果提供）
        if spot_df_copy is not None:
            spot_columns = [col for col in self.tenor_config.keys() if col in spot_df_copy.columns]
            
            # 使用虚线、较细线宽、半透明来区分即期利率
            spot_styles = [
                {'linestyle': '--', 'linewidth': 1.0, 'alpha': 0.5, 'marker': 's', 'markersize': 3},
                {'linestyle': '-.', 'linewidth': 1.0, 'alpha': 0.5, 'marker': 'd', 'markersize': 3},
                {'linestyle': ':', 'linewidth': 1.0, 'alpha': 0.5, 'marker': '^', 'markersize': 3},
            ]
            
            for idx, col in enumerate(spot_columns):
                style = spot_styles[idx % len(spot_styles)]
                label = f"即期 {self.tenor_names[col]}"
                ax.plot(spot_df_copy['trade_date_dt'], spot_df_copy[col], 
                       label=label, color='gray', **style)
        
        # 绘制远期利率曲线（使用实线、较粗线宽、高对比度颜色）
        forward_colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(forward_columns)))
        
        for idx, col in enumerate(forward_columns):
            # 数据点太多，不显示标记点，只画连续曲线
            ax.plot(forward_df_copy['trade_date_dt'], forward_df_copy[col], 
                   linewidth=2.0, label=col, color=forward_colors[idx], alpha=0.9)
        
        # 设置图形属性
        ax.set_xlabel('交易日期', fontsize=12)
        ax.set_ylabel('利率 (%)', fontsize=12)
        ax.set_title('SHIBOR 远期利率 vs 即期利率对比曲线', fontsize=14, fontweight='bold')
        
        # 添加图例（分两列显示）
        ax.legend(loc='upper left', fontsize=9, ncol=2, framealpha=0.9)
        ax.grid(True, alpha=0.3)
        
        # 优化日期显示：只显示月份，自动调整间隔
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))  # 每2个月显示一次
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))  # 格式：YYYY-MM
        ax.xaxis.set_minor_locator(mdates.MonthLocator(interval=1))  # 每月小刻度
        
        # 设置标签格式
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=10)
        
        # 调整布局
        fig.autofmt_xdate(bottom=0.2)  # 自动格式化日期，底部留出空间
        plt.tight_layout()
        
        # 保存或显示
        if save_path:
            # 确保目录存在
            os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else '.', exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"远期利率曲线已保存至: {save_path}")
        else:
            plt.show()
        
        plt.close()
        
    def plot_latest_forward_curve(self, forward_rates_df, save_path=None, figsize=(12, 6)):
        """
        绘制最新日期的远期利率曲线（横轴为期限，纵轴为利率）
        
        参数:
        - forward_rates_df: 远期利率DataFrame
        - save_path: 保存路径
        - figsize: 图形大小
        """
        logger.info("绘制最新远期利率曲线...")
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 获取最新日期的数据
        latest_date = forward_rates_df['trade_date'].iloc[-1]
        latest_data = forward_rates_df.iloc[-1]
        
        # 提取远期利率数据
        forward_columns = [col for col in forward_rates_df.columns if col.startswith('F(')]
        
        # 解析期限组合，用于横轴
        periods = []
        rates = []
        
        for col in forward_columns:
            # 从列名中提取期限信息 F(1M,3M) -> 1M-3M
            period_label = col.replace('F(', '').replace(')', '')
            periods.append(period_label)
            rates.append(latest_data[col])
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # 绘制折线图和柱状图
        x = range(len(periods))
        ax.plot(x, rates, 'o-', linewidth=2, markersize=8, color='b', label='远期利率')
        ax.bar(x, rates, alpha=0.3, color='skyblue', label='利率柱状图')
        
        # 设置x轴标签
        ax.set_xticks(x)
        ax.set_xticklabels(periods, rotation=45, ha='right')
        
        # 设置图形属性
        ax.set_xlabel('期限组合', fontsize=12)
        ax.set_ylabel('远期利率 (%)', fontsize=12)
        ax.set_title(f'SHIBOR 远期利率曲线 ({latest_date})', fontsize=14, fontweight='bold')
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # 添加数值标签
        for i, rate in enumerate(rates):
            ax.text(i, rate + 0.05, f'{rate:.3f}%', ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        
        # 保存或显示
        if save_path:
            os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else '.', exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"最新远期利率曲线已保存至: {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def run(self, start_date=None, end_date=None, output_dir=None):
        """
        运行完整分析流程
        
        参数:
        - start_date: 开始日期
        - end_date: 结束日期
        - output_dir: 输出目录（可选，默认使用 CommonParameters.outBoundPath/report/ForwardRateCurve）
        """
        logger.info("=" * 80)
        logger.info("🚀 SHIBOR 远期利率分析开始")
        logger.info("=" * 80)
        
        # 1. 获取数据
        shibor_df = self.fetch_shibor_data(start_date, end_date)
        
        # 2. 计算远期利率
        forward_rates_df = self.calculate_forward_rate(shibor_df)
        
        # 3. 确保输出目录存在
        if output_dir is None:
            output_dir = self.output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成时间戳
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 4. 绘制即期利率时间序列图
        spot_only_path = os.path.join(output_dir, f'shibor_spot_rates_{timestamp}.png')
        self.plot_spot_rates(shibor_df, save_path=spot_only_path)
        
        # 4.1 绘制纯远期利率时间序列图（不包含即期利率）
        forward_only_path = os.path.join(output_dir, f'shibor_forward_rates_{timestamp}.png')
        self.plot_forward_rates(forward_rates_df, original_spot_df=None, save_path=forward_only_path)
        
        # 4.2 绘制时间序列图（包含即期利率对比）
        time_series_path = os.path.join(output_dir, f'shibor_forward_rates_timeseries_{timestamp}.png')
        self.plot_forward_rates(forward_rates_df, original_spot_df=shibor_df, save_path=time_series_path)
        
        # 5. 绘制最新远期利率曲线
        latest_curve_path = os.path.join(output_dir, f'shibor_forward_rates_latest_{timestamp}.png')
        self.plot_latest_forward_curve(forward_rates_df, save_path=latest_curve_path)
        
        # 6. 生成 PDF 报告
        logger.info("📊 开始生成 PDF 报告...")
        chart_paths = [
            (spot_only_path, 'SHIBOR即期利率历史走势'),
            (forward_only_path, 'SHIBOR远期利率历史走势'),
            (time_series_path, 'SHIBOR远期利率与即期利率历史对比走势'),
        ]
        pdf_path = self._generate_forward_rate_pdf(
            chart_paths=chart_paths,
            forward_rates_df=forward_rates_df,
            shibor_df=shibor_df,
            start_date=start_date,
            end_date=end_date
        )
        if pdf_path:
            logger.info(f"✅ PDF 报告已生成: {pdf_path}")
        
        # 7. 保存数据到CSV（包含即期利率和远期利率）
        csv_path = os.path.join(output_dir, f'shibor_forward_rates_{timestamp}.csv')
        
        # 合并即期利率和远期利率数据
        combined_df = pd.merge(
            shibor_df[['trade_date'] + [col for col in self.tenor_config.keys() if col in shibor_df.columns]],
            forward_rates_df,
            on='trade_date',
            how='left'
        )
        
        # 重新排列列顺序：日期、即期利率、远期利率
        spot_columns = [col for col in self.tenor_config.keys() if col in combined_df.columns]
        forward_columns = [col for col in combined_df.columns if col.startswith('F(')]
        ordered_columns = ['trade_date'] + spot_columns + forward_columns
        combined_df = combined_df[ordered_columns]
        
        combined_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        logger.info(f"远期利率和即期利率数据已保存至: {csv_path}")
        
        logger.info("=" * 80)
        logger.info("✅ SHIBOR 远期利率分析完成")
        logger.info(f"📁 输出目录: {output_dir}")
        logger.info("=" * 80)
        
        return forward_rates_df


if __name__ == '__main__':
    # 使用示例
    calculator = ShiborForwardRateCalculator()
    
    # 运行分析（获取最近1年数据）
    result_df = calculator.run(
        start_date='20250510',  # 可选：指定开始日期
        end_date='20260510',    # 可选：指定结束日期
        output_dir=r'E:\tmp\forwardrate'
    )
    
    # 显示结果统计
    print("\n" + "=" * 80)
    print("远期利率统计摘要:")
    print("=" * 80)
    print(result_df.describe())
    print("\n最新日期的远期利率:")
    print(result_df.iloc[-1])

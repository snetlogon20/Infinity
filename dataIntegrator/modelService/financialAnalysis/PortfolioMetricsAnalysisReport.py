"""
投资组合指标分析报告生成器 - 用于将多个 Excel 分析结果合并为专业 PDF 报告
"""
import os
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import pandas as pd

from dataIntegrator import CommonLib, CommonParameters

logger = CommonLib.logger


class PortfolioMetricsAnalysisReport:
    """投资组合指标分析报告生成器（参考 CMLAnalysisReport）"""

    def __init__(self):
        self.reportlab_font = self._register_chinese_font()
        self._ensure_output_directory()

    def _ensure_output_directory(self):
        """确保输出目录存在"""
        self.output_dir = os.path.join(CommonParameters.outBoundPath, "report", "PortfolioMetricsAnalysis")
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"✅ 创建 PortfolioMetricsAnalysis 报告目录: {self.output_dir}")

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

    def generate_professional_comment(self, metric_col, pivot_df):
        """
        为指定指标生成专业的分析评论
        
        参数:
        - metric_col: 指标列名
        - pivot_df: Pivot 数据 DataFrame
        
        返回:
        - comment: 专业分析评论文本
        """
        import numpy as np
        
        comments = {
            '均数 (%)': self._generate_mean_comment,
            'Skewness': self._generate_skewness_comment,
            'Kurtosis': self._generate_kurtosis_comment,
            'Sigma (%)': self._generate_sigma_comment,
            '与上证相关系数': self._generate_correlation_comment,
            'Beta': self._generate_beta_comment,
            'Treynor Ratio': self._generate_treynor_comment,
            'Sharpe Ratio': self._generate_sharpe_comment,
            'Information Ratio': self._generate_information_comment,
            'SOR Ratio': self._generate_sor_comment,
            'CML Weight': self._generate_cml_weight_comment,
        }
        
        generator = comments.get(metric_col)
        if generator:
            return generator(pivot_df)
        else:
            return f"{metric_col} 指标分析：该指标反映了投资组合的重要特征，建议结合其他指标综合评估。"
    
    def _generate_mean_comment(self, pivot_df):
        """生成均数指标的评论 - 增强版"""
        import numpy as np
        
        numeric_cols = [col for col in pivot_df.columns if col != '回测日期']
        if not numeric_cols:
            return "数据不足，无法进行分析。"
        
        # 计算每只股票的统计信息
        stock_stats = {}
        for col in numeric_cols:
            values = pivot_df[col].dropna()
            if len(values) > 0:
                stock_stats[col] = {
                    'mean': values.mean(),
                    'std': values.std(),
                    'min': values.min(),
                    'max': values.max(),
                    'median': values.median(),
                    'trend': '上升' if values.iloc[-1] > values.iloc[0] else '下降'
                }
        
        if not stock_stats:
            return "数据不足，无法进行分析。"
        
        # 排序
        sorted_stocks = sorted(stock_stats.items(), key=lambda x: x[1]['mean'], reverse=True)
        best_stock, best_stats = sorted_stocks[0]
        worst_stock, worst_stats = sorted_stocks[-1]
        
        # 计算整体统计
        all_means = [stats['mean'] for stats in stock_stats.values()]
        portfolio_mean = np.mean(all_means)
        portfolio_std = np.std(all_means)
        
        comment = f"【收益率深度分析】\n"
        comment += f"\n📊 整体表现:\n"
        comment += f"• 组合平均年化收益率: {portfolio_mean:.2f}%\n"
        comment += f"• 收益率离散度(标准差): {portfolio_std:.2f}%\n"
        comment += f"• 最高收益率: {best_stats['mean']:.2f}% ({best_stock})\n"
        comment += f"• 最低收益率: {worst_stats['mean']:.2f}% ({worst_stock})\n"
        comment += f"• 收益极差: {best_stats['mean'] - worst_stats['mean']:.2f}%\n"
        
        comment += f"\n📈 趋势分析:\n"
        upward = [(stock, stats) for stock, stats in sorted_stocks if stats['trend'] == '上升']
        downward = [(stock, stats) for stock, stats in sorted_stocks if stats['trend'] == '下降']
        comment += f"• 呈上升趋势资产: {len(upward)}只\n"
        comment += f"• 呈下降趋势资产: {len(downward)}只\n"
        
        if upward:
            comment += f"  上升领头羊: {upward[0][0]} (最新值: {upward[0][1]['max']:.2f}%)\n"
        if downward:
            comment += f"  下降警示: {downward[-1][0]} (最新值: {downward[-1][1]['min']:.2f}%)\n"
        
        comment += f"\n⚠️ 风险评估:\n"
        high_vol_stocks = [(stock, stats) for stock, stats in stock_stats.items() if stats['std'] > portfolio_std * 1.5]
        if high_vol_stocks:
            comment += f"• 高波动资产({len(high_vol_stocks)}只): 收益率波动剧烈\n"
            for stock, stats in high_vol_stocks[:3]:
                comment += f"  - {stock}: 波动率{stats['std']:.2f}%, 区间[{stats['min']:.2f}%, {stats['max']:.2f}%]\n"
        
        comment += f"\n💡 投资建议:\n"
        comment += f"• 收益领先资产({best_stock})表现突出，但需关注其波动风险\n"
        comment += f"• 建议采用核心-卫星策略: 核心配置稳定收益资产，卫星配置高收益资产\n"
        comment += f"• 收益率差异达{best_stats['mean'] - worst_stats['mean']:.2f}%，存在显著分化，建议优化组合结构\n"
        comment += f"• 关注趋势向下的资产，及时止损或调整仓位\n"
        comment += f"• 高收益率通常伴随高风险，务必结合波动率、夏普比率等指标综合评估"
        
        return comment
    
    def _generate_skewness_comment(self, pivot_df):
        """生成偏度指标的评论 - 增强版"""
        import numpy as np
        
        numeric_cols = [col for col in pivot_df.columns if col != '回测日期']
        if not numeric_cols:
            return "数据不足，无法进行分析。"
        
        positive_skew = []
        negative_skew = []
        neutral_skew = []
        
        skew_stats = {}
        for col in numeric_cols:
            values = pivot_df[col].dropna()
            if len(values) > 0:
                skew = values.mean()
                skew_stats[col] = {
                    'mean': skew,
                    'std': values.std(),
                    'min': values.min(),
                    'max': values.max(),
                    'latest': values.iloc[-1]
                }
                
                if skew > 0.5:
                    positive_skew.append((col, skew))
                elif skew < -0.5:
                    negative_skew.append((col, skew))
                else:
                    neutral_skew.append((col, skew))
        
        comment = f"【偏度深度分析】\n"
        comment += f"\n📊 偏度分布统计:\n"
        
        if positive_skew:
            comment += f"• ➕ 正偏资产 ({len(positive_skew)}只): 收益分布右偏\n"
            comment += f"  特征: 存在向上突破潜力，极端正收益概率较高\n"
            for stock, skew in sorted(positive_skew, key=lambda x: x[1], reverse=True)[:5]:
                stats = skew_stats[stock]
                comment += f"  - {stock}: {skew:.3f} (区间: {stats['min']:.3f}~{stats['max']:.3f})\n"
        
        if negative_skew:
            comment += f"• ➖ 负偏资产 ({len(negative_skew)}只): 收益分布左偏\n"
            comment += f"  特征: 需警惕下行风险，极端负收益概率较高\n"
            for stock, skew in sorted(negative_skew, key=lambda x: x[1])[:5]:
                stats = skew_stats[stock]
                comment += f"  - {stock}: {skew:.3f} (区间: {stats['min']:.3f}~{stats['max']:.3f})\n"
        
        if neutral_skew:
            comment += f"• ️ 对称分布资产 ({len(neutral_skew)}只): 偏度接近0\n"
            comment += f"  特征: 收益分布较为对称，风险相对可控\n"
        
        comment += f"\n️ 风险警示:\n"
        if negative_skew:
            comment += f"• 高风险警示: {len(negative_skew)}只负偏资产在市场下跌时可能出现更大跌幅\n"
            comment += f"  建议: 设置严格止损线，控制仓位在5-10%以内\n"
            worst_skew = min(negative_skew, key=lambda x: x[1])
            comment += f"  重点关注: {worst_skew[0]} (偏度: {worst_skew[1]:.3f})\n"
        
        comment += f"\n💡 投资策略:\n"
        if positive_skew:
            comment += f"• 正偏资产可作为卫星仓位，捕捉向上突破机会\n"
            best_skew = max(positive_skew, key=lambda x: x[1])
            comment += f"  推荐关注: {best_skew[0]} (偏度: {best_skew[1]:.3f})\n"
        
        comment += f"• 负偏资产应降低配置比例，或采用期权对冲策略\n"
        comment += f"• 建议结合峰度指标综合评估尾部风险\n"
        comment += f"• 偏度>0.5或<-0.5的资产需特别关注其极端行情表现"
        
        return comment
    
    def _generate_kurtosis_comment(self, pivot_df):
        """生成峰度指标的评论 - 增强版"""
        import numpy as np
        
        numeric_cols = [col for col in pivot_df.columns if col != '回测日期']
        if not numeric_cols:
            return "数据不足，无法进行分析。"
        
        high_kurtosis = []
        moderate_kurtosis = []
        low_kurtosis = []
        
        kurt_stats = {}
        for col in numeric_cols:
            values = pivot_df[col].dropna()
            if len(values) > 0:
                kurt = values.mean()
                kurt_stats[col] = {
                    'mean': kurt,
                    'std': values.std(),
                    'min': values.min(),
                    'max': values.max(),
                    'latest': values.iloc[-1]
                }
                
                if kurt > 2:
                    high_kurtosis.append((col, kurt))
                elif kurt > 0:
                    moderate_kurtosis.append((col, kurt))
                else:
                    low_kurtosis.append((col, kurt))
        
        comment = f"【峰度深度分析】\n"
        comment += f"\n📊 峰度分布统计:\n"
        
        if high_kurtosis:
            comment += f"• ⚠️ 高峰度资产 ({len(high_kurtosis)}只): 峰度 > 2\n"
            comment += f"  特征: 存在严重肥尾效应，极端行情概率显著高于正态分布\n"
            for stock, kurt in sorted(high_kurtosis, key=lambda x: x[1], reverse=True)[:5]:
                stats = kurt_stats[stock]
                comment += f"  - {stock}: {kurt:.3f} (区间: {stats['min']:.3f}~{stats['max']:.3f})\n"
        
        if moderate_kurtosis:
            comment += f"• ⚖️ 中等峰度资产 ({len(moderate_kurtosis)}只): 0 < 峰度 ≤ 2\n"
            comment += f"  特征: 轻微肥尾，极端行情概率略高于正态分布\n"
        
        if low_kurtosis:
            comment += f"• ✅ 低峰度资产 ({len(low_kurtosis)}只): 峰度 ≤ 0\n"
            comment += f"  特征: 收益分布接近或薄于正态分布，极端行情概率较低\n"
        
        comment += f"\n 尾部风险评估:\n"
        if high_kurtosis:
            comment += f"• 高风险警示: {len(high_kurtosis)}只高峰度资产存在显著肥尾效应\n"
            comment += f"  风险表现: 暴涨暴跌概率高，黑天鹅事件风险大\n"
            worst_kurt = max(high_kurtosis, key=lambda x: x[1])
            comment += f"  重点关注: {worst_kurt[0]} (峰度: {worst_kurt[1]:.3f})\n"
            comment += f"  建议: 降低仓位至5%以内，或采用期权对冲策略\n"
        
        comment += f"\n💡 风险管理建议:\n"
        if high_kurtosis:
            comment += f"• 高峰度资产必须设置严格止损线(建议-8%~-10%)\n"
            comment += f"• 避免在高峰度资产上过度集中，单只仓位不超过5%\n"
            comment += f"• 建议采用VaR(风险价值)模型量化极端损失风险\n"
        
        if low_kurtosis:
            comment += f"• 低峰度资产风险相对可控，可适当增加配置比例\n"
        
        comment += f"• 峰度>2的资产需加强实时监控，设置预警机制\n"
        comment += f"• 建议结合偏度指标综合评估收益分布特征\n"
        comment += f"• 对于高峰度+负偏度的资产组合，风险极高，应果断减仓"
        
        return comment
    
    def _generate_sigma_comment(self, pivot_df):
        """生成波动率指标的评论 - 增强版"""
        import numpy as np
        
        numeric_cols = [col for col in pivot_df.columns if col != '回测日期']
        if not numeric_cols:
            return "数据不足，无法进行分析。"
        
        # 计算详细的波动率统计
        vol_stats = {}
        for col in numeric_cols:
            values = pivot_df[col].dropna()
            if len(values) > 0:
                vol_stats[col] = {
                    'mean': values.mean(),
                    'std': values.std(),
                    'min': values.min(),
                    'max': values.max(),
                    'latest': values.iloc[-1],
                    'trend': '上升' if values.iloc[-1] > values.iloc[0] else '下降'
                }
        
        if not vol_stats:
            return "数据不足，无法进行分析。"
        
        # 分类
        low_vol = [(k, v) for k, v in vol_stats.items() if v['mean'] < 15]
        mid_vol = [(k, v) for k, v in vol_stats.items() if 15 <= v['mean'] < 25]
        high_vol = [(k, v) for k, v in vol_stats.items() if v['mean'] >= 25]
        
        # 找出极端波动
        extreme_vol = [(k, v) for k, v in vol_stats.items() if v['max'] - v['min'] > 10]
        
        comment = f"【波动率深度分析】\n"
        comment += f"\n📊 风险分级统计:\n"
        comment += f"• 低风险资产 ({len(low_vol)}只): 年化波动率 < 15%\n"
        if low_vol:
            for stock, stats in sorted(low_vol, key=lambda x: x[1]['mean'])[:3]:
                comment += f"  - {stock}: {stats['mean']:.2f}% (区间: {stats['min']:.2f}%-{stats['max']:.2f}%)\n"
        
        comment += f"• 中等风险资产 ({len(mid_vol)}只): 15% ≤ 波动率 < 25%\n"
        if mid_vol:
            for stock, stats in sorted(mid_vol, key=lambda x: x[1]['mean'])[:3]:
                comment += f"  - {stock}: {stats['mean']:.2f}% (区间: {stats['min']:.2f}%-{stats['max']:.2f}%)\n"
        
        comment += f"• 高风险资产 ({len(high_vol)}只): 波动率 ≥ 25%\n"
        if high_vol:
            for stock, stats in sorted(high_vol, key=lambda x: x[1]['mean'], reverse=True)[:3]:
                comment += f"  - {stock}: {stats['mean']:.2f}% (区间: {stats['min']:.2f}%-{stats['max']:.2f}%)\n"
        
        comment += f"\n📈 波动率趋势分析:\n"
        increasing_vol = [(k, v) for k, v in vol_stats.items() if v['trend'] == '上升']
        decreasing_vol = [(k, v) for k, v in vol_stats.items() if v['trend'] == '下降']
        comment += f"• 波动率上升资产: {len(increasing_vol)}只 (风险加剧)\n"
        comment += f"• 波动率下降资产: {len(decreasing_vol)}只 (风险缓解)\n"
        
        if increasing_vol:
            comment += f"  ️ 风险警示: {increasing_vol[0][0]} 波动率从{increasing_vol[0][1]['min']:.2f}%升至{increasing_vol[0][1]['max']:.2f}%\n"
        
        if extreme_vol:
            comment += f"\n⚡ 极端波动资产 ({len(extreme_vol)}只): 波动区间>10%\n"
            for stock, stats in extreme_vol[:3]:
                comment += f"  - {stock}: 波动区间[{stats['min']:.2f}%, {stats['max']:.2f}%], 最新{stats['latest']:.2f}%\n"
        
        comment += f"\n 资产配置建议:\n"
        comment += f"• 保守型投资者: 优选{len(low_vol)}只低风险资产，预期波动率<15%\n"
        comment += f"• 平衡型投资者: 配置中低风险资产组合，控制整体波动率在15-20%\n"
        comment += f"• 激进型投资者: 可适度配置高风险资产，但需设置止损线\n"
        
        if high_vol:
            comment += f"• 高风险资产警示: {', '.join([s[0] for s in high_vol[:3]])} 波动率超过25%，建议降低仓位或采用对冲策略\n"
        
        comment += f"• 建议结合夏普比率评估风险调整后收益，避免单纯追求低波动而牺牲收益\n"
        comment += f"• 波动率上升阶段应谨慎加仓，等待波动率企稳后再调整仓位"
        
        return comment
    
    def _generate_correlation_comment(self, pivot_df):
        """生成相关系数指标的评论 - 增强版"""
        import numpy as np
        
        numeric_cols = [col for col in pivot_df.columns if col != '回测日期']
        if not numeric_cols:
            return "数据不足，无法进行分析。"
        
        high_corr = []
        moderate_corr = []
        low_corr = []
        negative_corr = []
        
        corr_stats = {}
        for col in numeric_cols:
            values = pivot_df[col].dropna()
            if len(values) > 0:
                corr = values.mean()
                corr_stats[col] = {
                    'mean': corr,
                    'std': values.std(),
                    'min': values.min(),
                    'max': values.max(),
                    'latest': values.iloc[-1]
                }
                
                if corr > 0.7:
                    high_corr.append((col, corr))
                elif corr > 0.3:
                    moderate_corr.append((col, corr))
                elif corr >= -0.3:
                    low_corr.append((col, corr))
                else:
                    negative_corr.append((col, corr))
        
        comment = f"【相关系数深度分析】\n"
        comment += f"\n 指标解读:\n"
        comment += f"• 相关系数衡量资产与市场基准的同步程度\n"
        comment += f"• 高相关(>0.7): 与市场高度同步，系统性风险高\n"
        comment += f"• 低相关(<0.3): 与市场关联度低，分散化价值大\n"
        comment += f"• 负相关(<0): 与市场反向运动，对冲价值突出\n"
        
        comment = f"\n📊 相关性分布统计:\n"
        
        if high_corr:
            comment += f"• 🔴 高相关资产 ({len(high_corr)}只): 相关系数 > 0.7\n"
            comment += f"  特征: 与市场高度同步，系统性风险较高\n"
            for stock, corr in sorted(high_corr, key=lambda x: x[1], reverse=True)[:5]:
                stats = corr_stats[stock]
                comment += f"  - {stock}: {corr:.3f} (区间: {stats['min']:.3f}~{stats['max']:.3f})\n"
        
        if moderate_corr:
            comment += f"• 🟡 中等相关资产 ({len(moderate_corr)}只): 0.3 < 相关系数 ≤ 0.7\n"
            comment += f"  特征: 与市场部分同步，适度分散化\n"
        
        if low_corr:
            comment += f"• 🟢 低相关资产 ({len(low_corr)}只): -0.3 ≤ 相关系数 ≤ 0.3\n"
            comment += f"  特征: 与市场关联度低，具有显著分散化价值\n"
            for stock, corr in sorted(low_corr, key=lambda x: x[1])[:5]:
                stats = corr_stats[stock]
                comment += f"  - {stock}: {corr:.3f}\n"
        
        if negative_corr:
            comment += f"• 🔵 负相关资产 ({len(negative_corr)}只): 相关系数 < -0.3\n"
            comment += f"  特征: 与市场反向运动，对冲价值突出\n"
            for stock, corr in sorted(negative_corr, key=lambda x: x[1])[:5]:
                stats = corr_stats[stock]
                comment += f"  - {stock}: {corr:.3f}\n"
        
        comment += f"\n 组合优化建议:\n"
        if high_corr:
            comment += f"• 高相关资产过多会导致组合风险集中，建议降低配置比例\n"
            comment += f"• 当前高相关资产{len(high_corr)}只，占比{len(high_corr)/len(numeric_cols)*100:.1f}%\n"
        
        if low_corr or negative_corr:
            comment += f"• 低/负相关资产具有显著分散化价值，应增加配置\n"
            if negative_corr:
                best_hedge = min(negative_corr, key=lambda x: x[1])
                comment += f"• 最佳对冲标的: {best_hedge[0]} (相关系数: {best_hedge[1]:.3f})\n"
        
        comment += f"• 理想组合应包含不同相关性层级的资产，实现真正分散化\n"
        comment += f"• 建议高相关资产总仓位不超过60%，低相关资产不低于30%\n"
        
        comment += f"\n💡 投资策略:\n"
        comment += f"• 牛市: 可适度超配高相关资产，获取市场beta收益\n"
        comment += f"• 熊市: 增配低/负相关资产，对冲市场风险\n"
        comment += f"• 震荡市: 均衡配置，利用低相关资产降低组合波动\n"
        comment += f"• 建议定期计算组合整体相关系数，监控风险集中度"
        
        return comment
    
    def _generate_beta_comment(self, pivot_df):
        """生成Beta指标的评论 - 增强版"""
        import numpy as np
        
        numeric_cols = [col for col in pivot_df.columns if col != '回测日期']
        if not numeric_cols:
            return "数据不足，无法进行分析。"
        
        defensive = []
        moderate = []
        aggressive = []
        
        beta_stats = {}
        for col in numeric_cols:
            values = pivot_df[col].dropna()
            if len(values) > 0:
                beta = values.mean()
                beta_stats[col] = {
                    'mean': beta,
                    'std': values.std(),
                    'min': values.min(),
                    'max': values.max(),
                    'latest': values.iloc[-1]
                }
                
                if beta < 0.8:
                    defensive.append((col, beta))
                elif beta > 1.2:
                    aggressive.append((col, beta))
                else:
                    moderate.append((col, beta))
        
        comment = f"【Beta系数深度分析】\n"
        comment += f"\n📊 Beta分布统计:\n"
        
        if defensive:
            comment += f"• 🛡️ 防御型资产 ({len(defensive)}只): Beta < 0.8\n"
            comment += f"  特征: 市场下跌时相对抗跌，适合熊市配置\n"
            for stock, beta in sorted(defensive, key=lambda x: x[1])[:5]:
                stats = beta_stats[stock]
                comment += f"  - {stock}: {beta:.3f} (区间: {stats['min']:.3f}~{stats['max']:.3f})\n"
        
        if moderate:
            comment += f"• ⚖️ 平衡型资产 ({len(moderate)}只): 0.8 ≤ Beta ≤ 1.2\n"
            comment += f"  特征: 与市场同步波动，风险收益均衡\n"
        
        if aggressive:
            comment += f"•  进攻型资产 ({len(aggressive)}只): Beta > 1.2\n"
            comment += f"  特征: 市场上涨时弹性较大，适合牛市配置\n"
            for stock, beta in sorted(aggressive, key=lambda x: x[1], reverse=True)[:5]:
                stats = beta_stats[stock]
                comment += f"  - {stock}: {beta:.3f} (区间: {stats['min']:.3f}~{stats['max']:.3f})\n"
        
        comment += f"\n📈 市场环境适应性:\n"
        comment += f"• 牛市策略: 超配进攻型资产(Beta>1.2)，获取超额收益\n"
        if aggressive:
            top_aggressive = max(aggressive, key=lambda x: x[1])
            comment += f"  推荐: {top_aggressive[0]} (Beta: {top_aggressive[1]:.3f})\n"
        
        comment += f"• 熊市策略: 超配防御型资产(Beta<0.8)，控制回撤\n"
        if defensive:
            top_defensive = min(defensive, key=lambda x: x[1])
            comment += f"  推荐: {top_defensive[0]} (Beta: {top_defensive[1]:.3f})\n"
        
        comment += f"• 震荡市策略: 均衡配置，Beta接近1.0的资产\n"
        
        comment += f"\n💡 配置建议:\n"
        comment += f"• 当前若判断为牛市: 进攻型资产仓位可提升至40-60%\n"
        comment += f"• 当前若判断为熊市: 防御型资产仓位应提升至50-70%\n"
        comment += f"• Beta>1.5的资产波动剧烈，单只仓位建议不超过10%\n"
        comment += f"• 建议结合市场趋势指标(如均线系统)动态调整Beta暴露\n"
        comment += f"• 高Beta资产需配合止损策略，防止大幅回撤"
        
        return comment
    
    def _generate_treynor_comment(self, pivot_df):
        """生成特雷诺比率指标的评论 - 增强版"""
        import numpy as np
        
        numeric_cols = [col for col in pivot_df.columns if col != '回测日期']
        if not numeric_cols:
            return "数据不足，无法进行分析。"
        
        # 计算详细统计
        treynor_stats = {}
        for col in numeric_cols:
            values = pivot_df[col].dropna()
            if len(values) > 0:
                treynor_stats[col] = {
                    'mean': values.mean(),
                    'std': values.std(),
                    'min': values.min(),
                    'max': values.max(),
                    'latest': values.iloc[-1],
                    'positive_ratio': (values > 0).sum() / len(values) * 100
                }
        
        if not treynor_stats:
            return "数据不足，无法进行分析。"
        
        # 分级
        excellent = [(k, v) for k, v in treynor_stats.items() if v['mean'] > 0.15]
        good = [(k, v) for k, v in treynor_stats.items() if 0.10 < v['mean'] <= 0.15]
        acceptable = [(k, v) for k, v in treynor_stats.items() if 0 < v['mean'] <= 0.10]
        poor = [(k, v) for k, v in treynor_stats.items() if v['mean'] <= 0]
        
        # Top/Bottom 3
        sorted_treynor = sorted(treynor_stats.items(), key=lambda x: x[1]['mean'], reverse=True)
        top3 = sorted_treynor[:3]
        bottom3 = sorted_treynor[-3:]
        
        comment = f"【特雷诺比率深度分析】\n"
        comment += f"\n 指标解读:\n"
        comment += f"• 特雷诺比率衡量单位系统性风险(Beta)的超额收益\n"
        comment += f"• 与夏普比率不同，特雷诺比率只考虑系统性风险，忽略非系统性风险\n"
        comment += f"• 适用于充分分散化的投资组合评估\n"
        comment += f"• 特雷诺比率越高，说明承担单位系统性风险获得的超额收益越多\n"
        
        comment += f"\n📊 风险调整收益分级:\n"
        
        if excellent:
            comment += f"• ⭐⭐⭐ 优秀 ({len(excellent)}只): 特雷诺比率 > 0.15\n"
            comment += f"  特征: 单位系统性风险的超额收益极高\n"
            for stock, stats in excellent[:5]:
                comment += f"  - {stock}: {stats['mean']:.4f} (正收益周期{stats['positive_ratio']:.1f}%)\n"
        
        if good:
            comment += f"• ⭐⭐ 良好 ({len(good)}只): 0.10 < 特雷诺比率 ≤ 0.15\n"
            comment += f"  特征: 风险调整后收益较好\n"
        
        if acceptable:
            comment += f"• ⭐ 可接受 ({len(acceptable)}只): 0 < 特雷诺比率 ≤ 0.10\n"
        
        if poor:
            comment += f"• ❌ 待改善 ({len(poor)}只): 特雷诺比率 ≤ 0\n"
            comment += f"  特征: 系统性风险未能获得补偿\n"
            for stock, stats in poor[:3]:
                comment += f"  - {stock}: {stats['mean']:.4f}\n"
        
        comment += f"\n📈 最佳/最差表现:\n"
        comment += f"• 最优风险调整收益: {top3[0][0]} ({top3[0][1]['mean']:.4f})\n"
        comment += f"  波动区间: [{top3[0][1]['min']:.4f}, {top3[0][1]['max']:.4f}]\n"
        comment += f"• 最差风险调整收益: {bottom3[0][0]} ({bottom3[0][1]['mean']:.4f})\n"
        comment += f"  波动区间: [{bottom3[0][1]['min']:.4f}, {bottom3[0][1]['max']:.4f}]\n"
        
        comment += f"\n💡 与夏普比率对比:\n"
        comment += f"• 特雷诺比率适合评估分散化组合(非系统性风险已被分散)\n"
        comment += f"• 夏普比率适合评估单一资产或未充分分散的组合\n"
        comment += f"• 两者结合使用可全面评估风险调整后收益\n\n"
        
        comment += f" 投资建议:\n"
        comment += f"• 优先配置特雷诺比率>0.10的资产，系统性风险补偿充足\n"
        comment += f"• 对于已充分分散的组合，特雷诺比率比夏普比率更具参考价值\n"
        comment += f"• 特雷诺比率<0的资产说明承担系统性风险却未获补偿，应减仓\n"
        comment += f"• 建议结合Beta系数综合评估，高Beta+高特雷诺为最佳组合\n"
        comment += f"• 定期监控特雷诺比率变化，及时调整仓位配置"
        
        return comment
    
    def _generate_sharpe_comment(self, pivot_df):
        """生成夏普比率指标的评论 - 增强版"""
        import numpy as np
        
        numeric_cols = [col for col in pivot_df.columns if col != '回测日期']
        if not numeric_cols:
            return "数据不足，无法进行分析。"
        
        # 计算详细统计
        sharpe_stats = {}
        for col in numeric_cols:
            values = pivot_df[col].dropna()
            if len(values) > 0:
                sharpe_stats[col] = {
                    'mean': values.mean(),
                    'std': values.std(),
                    'min': values.min(),
                    'max': values.max(),
                    'latest': values.iloc[-1],
                    'positive_ratio': (values > 0).sum() / len(values) * 100
                }
        
        if not sharpe_stats:
            return "数据不足，无法进行分析。"
        
        # 分级
        excellent = [(k, v) for k, v in sharpe_stats.items() if v['mean'] > 1.0]
        good = [(k, v) for k, v in sharpe_stats.items() if 0.5 < v['mean'] <= 1.0]
        acceptable = [(k, v) for k, v in sharpe_stats.items() if 0 < v['mean'] <= 0.5]
        poor = [(k, v) for k, v in sharpe_stats.items() if v['mean'] <= 0]
        
        # Top/Bottom 3
        sorted_sharpe = sorted(sharpe_stats.items(), key=lambda x: x[1]['mean'], reverse=True)
        top3 = sorted_sharpe[:3]
        bottom3 = sorted_sharpe[-3:]
        
        comment = f"【夏普比率深度分析】\n"
        comment += f"\n 风险调整后收益分级:\n"
        
        if excellent:
            comment += f"• ⭐⭐⭐ 优秀资产 ({len(excellent)}只): 夏普比率 > 1.0\n"
            for stock, stats in excellent[:5]:
                comment += f"  - {stock}: {stats['mean']:.4f} (正收益周期{stats['positive_ratio']:.1f}%)\n"
        
        if good:
            comment += f"• ⭐⭐ 良好资产 ({len(good)}只): 0.5 < 夏普比率 ≤ 1.0\n"
            for stock, stats in good[:3]:
                comment += f"  - {stock}: {stats['mean']:.4f}\n"
        
        if acceptable:
            comment += f"• ⭐ 可接受资产 ({len(acceptable)}只): 0 < 夏普比率 ≤ 0.5\n"
        
        if poor:
            comment += f"• ❌ 待改善资产 ({len(poor)}只): 夏普比率 ≤ 0，风险补偿不足\n"
            for stock, stats in poor[:3]:
                comment += f"  - {stock}: {stats['mean']:.4f}\n"
        
        comment += f"\n📈 最佳/最差表现:\n"
        comment += f"• 最优风险调整收益: {top3[0][0]} ({top3[0][1]['mean']:.4f})\n"
        comment += f"  波动区间: [{top3[0][1]['min']:.4f}, {top3[0][1]['max']:.4f}]\n"
        comment += f"• 最差风险调整收益: {bottom3[0][0]} ({bottom3[0][1]['mean']:.4f})\n"
        comment += f"  波动区间: [{bottom3[0][1]['min']:.4f}, {bottom3[0][1]['max']:.4f}]\n"
        comment += f"• 夏普比率极差: {top3[0][1]['mean'] - bottom3[0][1]['mean']:.4f}\n"
        
        comment += f"\n💡 投资标准与建议:\n"
        comment += f"• 夏普比率>1.0: 优秀，单位风险获得的超额收益高，优先配置\n"
        comment += f"• 夏普比率0.5-1.0: 良好，可接受的风险收益比\n"
        comment += f"• 夏普比率<0.5: 风险补偿不足，建议减仓或剔除\n"
        comment += f"• 夏普比率<0: 收益无法覆盖风险，应立即止损\n\n"
        
        comment += f"🎯 配置策略:\n"
        comment += f"• 核心仓位应配置夏普比率>0.8的优质资产\n"
        comment += f"• 卫星仓位可适度配置高波动高收益资产，但需控制仓位\n"
        comment += f"• 建议定期 rebalance，淘汰夏普比率持续<0.5的资产\n"
        comment += f"• 结合Sortino比率进一步评估下行风险控制能力"
        
        return comment
    
    def _generate_information_comment(self, pivot_df):
        """生成信息比率指标的评论 - 增强版"""
        import numpy as np
        
        numeric_cols = [col for col in pivot_df.columns if col != '回测日期']
        if not numeric_cols:
            return "数据不足，无法进行分析。"
        
        positive_ir = []
        negative_ir = []
        neutral_ir = []
        
        ir_stats = {}
        for col in numeric_cols:
            values = pivot_df[col].dropna()
            if len(values) > 0:
                ir = values.mean()
                ir_stats[col] = {
                    'mean': ir,
                    'std': values.std(),
                    'min': values.min(),
                    'max': values.max(),
                    'latest': values.iloc[-1],
                    'positive_ratio': (values > 0).sum() / len(values) * 100
                }
                
                if ir > 0.5:
                    positive_ir.append((col, ir))
                elif ir < 0:
                    negative_ir.append((col, ir))
                else:
                    neutral_ir.append((col, ir))
        
        comment = f"【信息比率深度分析】\n"
        comment += f"\n 指标解读:\n"
        comment += f"• 信息比率(IR)衡量单位跟踪误差的超额收益\n"
        comment += f"• IR > 0: 跑赢基准，具备主动管理能力\n"
        comment += f"• IR < 0: 跑输基准，主动管理未能创造价值\n"
        comment += f"• IR越高，说明基金经理的选股能力越强\n"
        
        comment += f"\n📊 超额收益表现分级:\n"
        
        if positive_ir:
            comment += f"• ✅ 跑赢基准 ({len(positive_ir)}只): IR > 0.5\n"
            comment += f"  特征: 主动管理能力突出，持续创造超额收益\n"
            for stock, ir in sorted(positive_ir, key=lambda x: x[1], reverse=True)[:5]:
                stats = ir_stats[stock]
                comment += f"  - {stock}: {ir:.4f} (正超额周期{stats['positive_ratio']:.1f}%)\n"
        
        if neutral_ir:
            comment += f"• ⚖️ 接近基准 ({len(neutral_ir)}只): 0 ≤ IR ≤ 0.5\n"
            comment += f"  特征: 超额收益不明显，接近被动跟踪\n"
        
        if negative_ir:
            comment += f"•  跑输基准 ({len(negative_ir)}只): IR < 0\n"
            comment += f"  特征: 未能创造超额收益，主动管理失败\n"
            for stock, ir in sorted(negative_ir, key=lambda x: x[1])[:5]:
                stats = ir_stats[stock]
                comment += f"  - {stock}: {ir:.4f}\n"
        
        comment += f"\n📈 最佳/最差表现:\n"
        if positive_ir:
            best_ir = max(positive_ir, key=lambda x: x[1])
            comment += f"• 最强超额收益能力: {best_ir[0]} (IR: {best_ir[1]:.4f})\n"
        if negative_ir:
            worst_ir = min(negative_ir, key=lambda x: x[1])
            comment += f"• 最差超额收益能力: {worst_ir[0]} (IR: {worst_ir[1]:.4f})\n"
        
        comment += f"\n💡 评价标准与建议:\n"
        comment += f"• IR > 0.5: 优秀的主动管理能力，建议重点配置\n"
        comment += f"• 0 < IR ≤ 0.5: 具备一定的超额收益能力，可适度配置\n"
        comment += f"• IR ≈ 0: 接近被动指数，建议考虑指数基金替代\n"
        comment += f"• IR < 0: 主动管理失败，应减仓或更换标的\n\n"
        
        comment += f"🎯 配置策略:\n"
        comment += f"• 优先选择IR持续>0.5的资产，说明基金经理选股能力稳定\n"
        comment += f"• IR波动大的资产需关注其稳定性，避免业绩大幅波动\n"
        comment += f"• 建议结合跟踪误差评估，低跟踪误差+高IR为最佳组合\n"
        comment += f"• 对于IR<0的资产，应分析原因：是风格不匹配还是选股能力不足"
        
        return comment
    
    def _generate_sor_comment(self, pivot_df):
        """生成索提诺比率指标的评论 - 增强版"""
        import numpy as np
        
        numeric_cols = [col for col in pivot_df.columns if col != '回测日期']
        if not numeric_cols:
            return "数据不足，无法进行分析。"
        
        # 计算详细统计
        sor_stats = {}
        for col in numeric_cols:
            values = pivot_df[col].dropna()
            if len(values) > 0:
                sor_stats[col] = {
                    'mean': values.mean(),
                    'std': values.std(),
                    'min': values.min(),
                    'max': values.max(),
                    'latest': values.iloc[-1],
                    'positive_ratio': (values > 0).sum() / len(values) * 100
                }
        
        if not sor_stats:
            return "数据不足，无法进行分析。"
        
        # 分级
        excellent = [(k, v) for k, v in sor_stats.items() if v['mean'] > 1.5]
        good = [(k, v) for k, v in sor_stats.items() if 1.0 < v['mean'] <= 1.5]
        acceptable = [(k, v) for k, v in sor_stats.items() if 0.5 < v['mean'] <= 1.0]
        poor = [(k, v) for k, v in sor_stats.items() if v['mean'] <= 0.5]
        
        # Top/Bottom 3
        sorted_sor = sorted(sor_stats.items(), key=lambda x: x[1]['mean'], reverse=True)
        top3 = sorted_sor[:3]
        bottom3 = sorted_sor[-3:]
        
        comment = f"【索提诺比率(SOR)深度分析】\n"
        comment += f"\n 指标特点:\n"
        comment += f"• SOR仅考虑下行风险(负收益波动)，更适合评估不对称风险资产\n"
        comment += f"• 相比夏普比率，SOR更能反映投资者对下行风险的真实厌恶\n"
        comment += f"• SOR通常高于夏普比率，差值越大说明上行波动占比越高\n"
        
        comment += f"\n📊 下行风险控制分级:\n"
        
        if excellent:
            comment += f"• ⭐⭐⭐ 优秀 ({len(excellent)}只): SOR > 1.5\n"
            comment += f"  特征: 下行风险控制极佳，上行潜力充足\n"
            for stock, stats in excellent[:5]:
                comment += f"  - {stock}: {stats['mean']:.4f} (正收益周期{stats['positive_ratio']:.1f}%)\n"
        
        if good:
            comment += f"• ⭐⭐ 良好 ({len(good)}只): 1.0 < SOR ≤ 1.5\n"
            comment += f"  特征: 下行风险控制较好\n"
        
        if acceptable:
            comment += f"• ⭐ 可接受 ({len(acceptable)}只): 0.5 < SOR ≤ 1.0\n"
        
        if poor:
            comment += f"• ❌ 待改善 ({len(poor)}只): SOR ≤ 0.5\n"
            comment += f"  特征: 下行风险控制不足，需警惕\n"
            for stock, stats in poor[:3]:
                comment += f"  - {stock}: {stats['mean']:.4f}\n"
        
        comment += f"\n📈 最佳/最差表现:\n"
        comment += f"• 最优下行风险控制: {top3[0][0]} (SOR: {top3[0][1]['mean']:.4f})\n"
        comment += f"• 最差下行风险控制: {bottom3[0][0]} (SOR: {bottom3[0][1]['mean']:.4f})\n"
        comment += f"• SOR极差: {top3[0][1]['mean'] - bottom3[0][1]['mean']:.4f}\n"
        
        comment += f"\n💡 SOR vs 夏普比率对比:\n"
        comment += f"• SOR > 夏普比率: 说明资产上行波动大于下行波动，投资价值佳\n"
        comment += f"• SOR ≈ 夏普比率: 说明收益分布对称，风险均衡\n"
        comment += f"• SOR < 夏普比率: 罕见情况，可能存在数据异常\n\n"
        
        comment += f"🎯 投资建议:\n"
        comment += f"• 优先配置SOR>1.0的资产，下行风险可控\n"
        comment += f"• SOR<0.5的资产下行风险过大，建议减仓或设置严格止损\n"
        comment += f"• 对于高波动资产，SOR比夏普比率更具参考价值\n"
        comment += f"• 建议结合最大回撤指标综合评估下行风险"
        
        return comment
    
    def _generate_cml_weight_comment(self, pivot_df):
        """生成CML权重指标的评论 - 增强版"""
        import numpy as np
        
        numeric_cols = [col for col in pivot_df.columns if col != '回测日期']
        if not numeric_cols:
            return "数据不足，无法进行分析。"
        
        # 计算详细的权重统计
        weight_stats = {}
        for col in numeric_cols:
            values = pivot_df[col].dropna()
            if len(values) > 0:
                weight_stats[col] = {
                    'mean': values.mean() * 100,  # 转换为百分比
                    'std': values.std() * 100,
                    'min': values.min() * 100,
                    'max': values.max() * 100,
                    'latest': values.iloc[-1] * 100,
                    'positive_ratio': (values > 0).sum() / len(values) * 100
                }
        
        if not weight_stats:
            return "数据不足，无法进行分析。"
        
        # 分级
        core_holdings = [(k, v) for k, v in weight_stats.items() if v['mean'] > 10]
        satellite_holdings = [(k, v) for k, v in weight_stats.items() if 5 <= v['mean'] <= 10]
        watch_list = [(k, v) for k, v in weight_stats.items() if 0 < v['mean'] < 5]
        zero_weight = [(k, v) for k, v in weight_stats.items() if v['mean'] == 0]
        
        # Top 5 核心持仓
        sorted_weights = sorted(weight_stats.items(), key=lambda x: x[1]['mean'], reverse=True)
        top5 = sorted_weights[:5]
        
        comment = f"【CML最优权重深度分析】\n"
        comment += f"\n 理论基础:\n"
        comment += f"• 资本市场线(CML)上的切点组合代表最优风险收益比\n"
        comment += f"• CML权重反映在给定风险水平下最大化夏普比率的资产配置\n"
        comment += f"• 权重动态调整反映市场环境变化对最优组合的影响\n"
        
        comment += f"\n 权重分布统计:\n"
        
        if core_holdings:
            comment += f"• 🏆 核心持仓 ({len(core_holdings)}只): 权重 > 10%\n"
            comment += f"  特征: 组合的基石资产，长期稳定配置\n"
            for stock, stats in core_holdings[:5]:
                comment += f"  - {stock}: 平均{stats['mean']:.2f}% (区间: {stats['min']:.2f}%-{stats['max']:.2f}%)\n"
        
        if satellite_holdings:
            comment += f"• 🎯 卫星持仓 ({len(satellite_holdings)}只): 5% ≤ 权重 ≤ 10%\n"
            comment += f"  特征: 增强收益的战术性配置\n"
            for stock, stats in satellite_holdings[:5]:
                comment += f"  - {stock}: 平均{stats['mean']:.2f}%\n"
        
        if watch_list:
            comment += f"•  观察仓 ({len(watch_list)}只): 0 < 权重 < 5%\n"
            comment += f"  特征: 配置比例较低，需持续观察\n"
        
        if zero_weight:
            comment += f"• ❌ 零配置资产 ({len(zero_weight)}只): 权重 = 0%\n"
            comment += f"  原因: 风险收益比不佳，CML优化器自动剔除\n"
            for stock, stats in zero_weight[:5]:
                comment += f"  - {stock}\n"
        
        comment += f"\n📈 核心持仓分析:\n"
        if top5:
            comment += f"• Top 5 核心资产配置:\n"
            total_core_weight = sum([stats['mean'] for _, stats in top5])
            for rank, (stock, stats) in enumerate(top5, 1):
                comment += f"  {rank}. {stock}: {stats['mean']:.2f}% (稳定性: {100-stats['std']:.1f}%)\n"
            comment += f"• Top 5 合计权重: {total_core_weight:.2f}%\n"
        
        comment += f"\n💡 配置策略建议:\n"
        comment += f"• 核心-卫星策略: 核心仓位(>10%)长期持有，卫星仓位(5-10%)动态调整\n"
        
        if core_holdings:
            top_core = max(core_holdings, key=lambda x: x[1]['mean'])
            comment += f"• 首要核心: {top_core[0]} (权重{top_core[1]['mean']:.2f}%)，建议作为组合基石\n"
        
        if satellite_holdings:
            comment += f"• 卫星仓位应定期 rebalance，根据CML权重变化调整\n"
        
        if zero_weight:
            comment += f"• 零配置资产({len(zero_weight)}只)风险收益比不佳，建议暂时规避\n"
        
        comment += f"• 权重波动大的资产(std>5%)需密切监控，及时调整仓位\n"
        comment += f"• 建议每季度根据最新数据重新计算CML最优权重\n"
        comment += f"• CML权重应与基本面分析结合，避免纯量化配置的局限性"
        
        return comment

    def _generate_chart_image(self, pivot_df, metric_col, sheet_name):
        """
        生成图表图片（内存中的 PNG）- 在折线图尾部标注股票名称

        参数:
        - pivot_df: Pivot 数据 DataFrame
        - metric_col: 指标列名
        - sheet_name: 工作表名称

        返回:
        - image_bytes: 图片字节流
        """
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        try:
            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']  # 用来正常显示中文标签
            plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

            # 准备数据
            dates = pivot_df['回测日期'].values
            numeric_cols = pivot_df.columns[pivot_df.columns != '回测日期']

            if len(numeric_cols) == 0 or len(dates) == 0:
                return None

            # 转换日期为 datetime 对象
            date_objects = []
            for d in dates:
                date_str = str(d)
                if len(date_str) == 8:  # 'YYYYMMDD' 格式
                    date_objects.append(datetime.strptime(date_str, '%Y%m%d'))
                elif '-' in date_str:  # 'YYYY-MM-DD' 格式
                    date_objects.append(datetime.strptime(date_str[:10], '%Y-%m-%d'))
                else:
                    date_objects.append(datetime.strptime(date_str, '%Y%m%d'))

            # 创建图表
            fig, ax = plt.subplots(figsize=(14, 7))

            # 根据指标类型选择图表类型
            if metric_col == 'CML Weight':
                # CML Weight 使用堆积面积图 - 使用专业的配色方案
                from matplotlib.colors import ListedColormap
                
                # 专业配色方案：温暖的渐变色，避免绿蓝色系
                professional_colors = [
                    '#E41A1C',  # 红色
                    '#377EB8',  # 蓝色
                    '#4DAF4A',  # 绿色
                    '#984EA3',  # 紫色
                    '#FF7F00',  # 橙色
                    '#A65628',  # 棕色
                    '#F781BF',  # 粉色
                    '#999999',  # 灰色
                    '#66C2A5',  # 青绿色
                    '#FC8D62',  # 桃红色
                    '#8DA0CB',  # 浅蓝色
                    '#E78AC3',  # 浅紫色
                    '#A6D854',  # 黄绿色
                    '#FFD92F',  # 黄色
                    '#E5C494',  # 浅棕色
                    '#B3B3B3',  # 中灰色
                ]
                
                # 如果资产数量超过预设颜色，循环使用
                if len(numeric_cols) > len(professional_colors):
                    professional_colors = professional_colors * (len(numeric_cols) // len(professional_colors) + 1)
                
                # 创建堆积面积图
                stacked_data = ax.stackplot(date_objects, 
                                          [pivot_df[col].fillna(0).values for col in numeric_cols],
                                          labels=numeric_cols,
                                          colors=professional_colors[:len(numeric_cols)],
                                          alpha=0.85)
            else:
                # 其他指标使用折线图 - 使用 matplotlib 默认颜色循环
                for col in numeric_cols:
                    values = pivot_df[col].values
                    ax.plot(date_objects, values, label=col, linewidth=1.5, alpha=0.9)

            # 设置标题和标签
            ax.set_title(f"{metric_col} 趋势图", fontsize=14, fontweight='bold')
            ax.set_xlabel('回测日期', fontsize=11)
            ax.set_ylabel(metric_col, fontsize=11)

            # 优化日期显示：只显示月份，自动调整间隔
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))  # 每2个月显示一次
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))  # 格式：YYYY-MM
            ax.xaxis.set_minor_locator(mdates.MonthLocator(interval=1))  # 每月小刻度

            # 设置标签格式
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=10)

            # ========== 在每条线的末端添加股票标签 ==========
            if len(pivot_df) > 0 and metric_col != 'CML Weight':
                # 找到最后一个有效数据点的日期
                last_date = date_objects[-1]

                # 为每条线添加标签
                for col in numeric_cols:
                    last_value = pivot_df[col].iloc[-1]
                    if pd.notna(last_value):
                        # 在线的右端添加标签
                        ax.text(last_date, last_value, f'  {col}',
                                fontsize=8, fontweight='normal',
                                verticalalignment='center',
                                horizontalalignment='left')

            # ========== 在堆积图的右侧添加股票标签 ==========
            if len(pivot_df) > 0 and metric_col == 'CML Weight':
                # 找到最后一个有效数据点的日期
                last_date = date_objects[-1]
                
                # 计算每个资产在最后一个日期的权重
                final_weights = {}
                for col_idx, col in enumerate(numeric_cols):
                    last_weight = pivot_df[col].fillna(0).iloc[-1]
                    if last_weight > 0:
                        final_weights[col] = last_weight
                
                # 按权重降序排序
                sorted_weights = sorted(final_weights.items(), key=lambda x: x[1], reverse=True)
                
                # 只显示权重 > 5% 的标签，并上下交替布局
                label_threshold = 0.05  # 5% 阈值
                for idx, (col, weight) in enumerate(sorted_weights):
                    if weight >= label_threshold:
                        # 找到该资产在numeric_cols中的索引
                        col_idx_in_numeric = numeric_cols.tolist().index(col)
                        
                        # 计算累积高度（从下到上）
                        cumulative_height = sum([pivot_df[numeric_cols[i]].fillna(0).iloc[-1] 
                                                for i in range(col_idx_in_numeric + 1)])
                        # 该层的中心位置
                        y_center = cumulative_height - weight / 2
                        
                        # 根据索引决定标签在上方还是下方
                        if idx % 2 == 0:
                            y_offset = weight * 0.3  # 向上偏移
                            va = 'bottom'
                        else:
                            y_offset = -weight * 0.3  # 向下偏移
                            va = 'top'
                        
                        # 在堆积层的右侧添加标签
                        ax.text(last_date, y_center + y_offset, f'{col}', 
                               fontsize=6, fontweight='normal',
                               verticalalignment=va,
                               horizontalalignment='left',
                               bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7, edgecolor='none'))

            # 添加网格线
            ax.grid(True, linestyle='--', alpha=0.5)

            # ========== 在图表底部添加图例标签（平铺显示） ==========
            if len(numeric_cols) > 0:
                # 计算需要的列数（根据资产数量动态调整）
                num_assets = len(numeric_cols)
                if num_assets <= 10:
                    ncol = num_assets  # 资产少时，每行显示所有
                elif num_assets <= 20:
                    ncol = 10  # 中等数量，每行10个
                else:
                    ncol = 15  # 大量资产，每行15个
                
                # 在图表底部添加图例（平铺显示，带颜色线条）
                ax.legend(loc='upper center', 
                         bbox_to_anchor=(0.5, -0.15),  # 位置在图表底部
                         ncol=ncol,  # 列数
                         fontsize=7,  # 字体大小
                         markerscale=0.8,  # 标记大小
                         columnspacing=0.8,  # 列间距
                         handlelength=1.5,  # 线条长度
                         handletextpad=0.4,  # 线条和文字间距
                         framealpha=0.9,  # 透明度
                         borderaxespad=0.5)  # 边框间距

            # 调整布局，为底部图例留出足够空间
            fig.autofmt_xdate(bottom=0.2)  # 自动格式化日期，底部留出空间
            plt.tight_layout(rect=[0, 0.12, 1, 1])  # 调整布局，为底部图例留出12%的空间

            # 保存到内存缓冲区
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)

            return buf

        except Exception as e:
            logger.warning(f"图表生成异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None


if __name__ == "__main__":
    # 测试代码
    logger.info("PortfolioMetricsAnalysisReport 模块已就绪")
    logger.info(f"输出目录: {PortfolioMetricsAnalysisReport().output_dir}")

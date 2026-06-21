"""
PD (违约概率) 分析报告生成器 —— 逐只股票深度分析

基于 df_akshare_stock_financial_analysis_indicator_matrics 表的数据，
对每只股票生成包含表格、双Y轴图表和专业交易员评论的 PDF 报告。

报告内容:
1. 数据表格: 日期 / Z_Score / 风险等级 / PD / EL / EAD / X1-X5
2. 图表1: 日期 X 轴，Z_Score (左Y轴) + PD (右Y轴) 双轴图
3. 图表2: 日期 X 轴，PD (左Y轴) + EL (右Y轴) 双轴图
4. 专业交易员视角的综合分析评论
"""

import os
import sys
from datetime import datetime
from io import BytesIO

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                PageBreak, Table, TableStyle, KeepTogether)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.common.CommonDataParameters import CommonDataParameters
from dataIntegrator.common.ReportJobLogger import ReportJobLogger
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.LLMSuport.AiAgents.ZhipuGLM4 import ZhipuGLM4

logger = CommonLib.logger

# ======================== 中文字体 + matplotlib 配置 ========================
def _setup_chinese():
    """注册中文字体（reportlab + matplotlib）"""
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
                logger.info(f"✅ ReportLab 字体: {font_path} -> {font_name}")
                break
            except Exception as e:
                logger.warning(f"⚠️ 字体加载失败 {font_path}: {e}")

    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    return reportlab_font


REPORTLAB_FONT = _setup_chinese()


class PDAnalysisReport:
    """PD 违约概率分析报告生成器（参照 PortfolioMetricsAnalysisReport 风格）"""

    MATRICS_TABLE = "indexsysdb.df_akshare_stock_financial_analysis_indicator_matrics"

    # Z-Score 三段论阈值
    Z_SAFE = 3.0
    Z_GREY = 1.8

    # 每个数值指标的列名 → 中文标题
    COLUMN_LABELS = {
        'z_score': 'Z-Score',
        'risk_level': '风险等级',
        'pd': 'PD (违约概率)',
        'el': 'EL (预期损失)',
        'ead': 'EAD (风险敞口)',
        'total_assets': '总资产',
        'total_equity': '股东权益',
        'total_liabilities': '总负债',
        'profit_before_tax': '税前利润',
        'revenue': '主营业务收入',
        'current_assets': '流动资产',
        'current_liabilities': '流动负债',
        'retained_earnings': '留存收益',
        'x1': 'X1 (营运资本/总资产)',
        'x2': 'X2 (留存收益/总资产)',
        'x3': 'X3 (EBIT/总资产)',
        'x4': 'X4 (权益/负债)',
        'x5': 'X5 (收入/总资产)',
    }

    RISK_LEVEL_CN = {
        'green_safe': '[安全区] Z≥3.0',
        'yellow_grey': '[灰色区] 1.8≤Z<3.0',
        'red_distress': '[危机区] Z<1.8',
    }

    def __init__(self):
        self._ensure_output_directory()
        self.job_logger = ReportJobLogger()

    def _ensure_output_directory(self):
        self.output_dir = os.path.join(CommonParameters.outBoundPath, "report", "PDAnalysis")
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"✅ 创建 PDAnalysis 报告目录: {self.output_dir}")

    # ========================= 数据获取 =========================

    def fetch_matrics_data(self, symbol: str) -> pd.DataFrame:
        """
        从 ClickHouse matrics 表读取指定股票的 PD 分析结果

        Args:
            symbol: 股票代码，如 '002093'

        Returns:
            pd.DataFrame，按 date 升序排列
        """
        sql = f"""
            SELECT date, symbol, name, industry,
                   z_score, risk_level, pd, el, ead,
                   total_assets, total_equity, total_liabilities,
                   profit_before_tax, revenue,
                   current_assets, current_liabilities, retained_earnings,
                   x1, x2, x3, x4, x5
            FROM {self.MATRICS_TABLE}
            WHERE symbol = %(symbol)s
            ORDER BY date ASC
        """
        result = ClickhouseService.clickhouseClient.execute(sql, {'symbol': symbol})
        if not result:
            return pd.DataFrame()

        columns = [
            'date', 'symbol', 'name', 'industry',
            'z_score', 'risk_level', 'pd', 'el', 'ead',
            'total_assets', 'total_equity', 'total_liabilities',
            'profit_before_tax', 'revenue',
            'current_assets', 'current_liabilities', 'retained_earnings',
            'x1', 'x2', 'x3', 'x4', 'x5',
        ]
        df = pd.DataFrame(result, columns=columns)

        # 数值列转换
        numeric_cols = [
            'z_score', 'pd', 'el', 'ead',
            'total_assets', 'total_equity', 'total_liabilities',
            'profit_before_tax', 'revenue',
            'current_assets', 'current_liabilities', 'retained_earnings',
            'x1', 'x2', 'x3', 'x4', 'x5',
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    # ========================= 图表生成 =========================

    def _chart_zscore_pd(self, df: pd.DataFrame, stock_label: str) -> BytesIO:
        """
        图表1: 日期 X 轴，Z_Score (左Y) + PD (右Y) 双轴

        Args:
            df: 含 date, z_score, pd 列的 DataFrame
            stock_label: 图表标题后缀

        Returns:
            BytesIO PNG 图片
        """
        fig, ax1 = plt.subplots(figsize=(16, 7))

        # 转换日期
        dates = pd.to_datetime(df['date'], format='%Y%m%d', errors='coerce')
        valid_mask = dates.notna()
        dates = dates[valid_mask]
        z_vals = df.loc[valid_mask, 'z_score'].values
        pd_vals = df.loc[valid_mask, 'pd'].values

        if len(dates) == 0:
            plt.close(fig)
            return None

        # ---- 左 Y 轴: Z-Score (柱状图 + 折线) ----
        bar_colors = []
        for z in z_vals:
            if pd.isna(z):
                bar_colors.append('#cccccc')
            elif z >= self.Z_SAFE:
                bar_colors.append('#2ecc71')
            elif z >= self.Z_GREY:
                bar_colors.append('#f1c40f')
            else:
                bar_colors.append('#e74c3c')

        ax1.bar(dates, z_vals, width=30, color=bar_colors, alpha=0.4, zorder=2, label='Z-Score (柱)')
        ax1.plot(dates, z_vals, 'k-', linewidth=1.2, alpha=0.7, zorder=4, label='Z-Score (线)')

        # 安全区/危机区参考线
        ax1.axhline(y=self.Z_SAFE, color='green', linestyle='--', linewidth=1, alpha=0.6,
                    zorder=1, label=f'安全线 Z={self.Z_SAFE}')
        ax1.axhline(y=self.Z_GREY, color='orange', linestyle='--', linewidth=1, alpha=0.6,
                    zorder=1, label=f'警戒线 Z={self.Z_GREY}')

        ax1.set_xlabel('日期', fontsize=11)
        ax1.set_ylabel('Z-Score', fontsize=11, color='black')
        ax1.tick_params(axis='y', labelcolor='black')

        # X 轴日期格式
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9)

        # ---- 右 Y 轴: PD ----
        ax2 = ax1.twinx()
        ax2.fill_between(dates, 0, pd_vals * 100, color='red', alpha=0.08, zorder=1)
        ax2.plot(dates, pd_vals * 100, color='#e74c3c', linewidth=2.5, alpha=1.0,
                 zorder=5, label='PD (%)')
        ax2.set_ylabel('PD 违约概率 (%)', fontsize=11, color='#e74c3c')
        ax2.tick_params(axis='y', labelcolor='#e74c3c')

        # 合并图例
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=8, framealpha=0.9)

        ax1.set_title(f'{stock_label}  Z-Score 与 PD 违约概率 趋势分析', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3, linestyle='--')

        plt.tight_layout()
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        return buf

    def _chart_pd_el(self, df: pd.DataFrame, stock_label: str) -> BytesIO:
        """
        图表2: 日期 X 轴，PD (左Y) + EL (右Y) 双轴

        Args:
            df: 含 date, pd, el 列的 DataFrame
            stock_label: 图表标题后缀

        Returns:
            BytesIO PNG 图片
        """
        fig, ax1 = plt.subplots(figsize=(16, 7))

        dates = pd.to_datetime(df['date'], format='%Y%m%d', errors='coerce')
        valid_mask = dates.notna()
        dates = dates[valid_mask]
        pd_vals = df.loc[valid_mask, 'pd'].values * 100  # 转为百分比
        el_vals = df.loc[valid_mask, 'el'].values

        if len(dates) == 0:
            plt.close(fig)
            return None

        # ---- 左 Y 轴: PD (%) ---- （先画背景再画线，确保 PD 线在最上层）
        ax1.fill_between(dates, 0, pd_vals, color='red', alpha=0.12, zorder=1)
        ax1.plot(dates, pd_vals, color='#e74c3c', linewidth=2.5, alpha=1.0,
                 zorder=5, label='PD 违约概率 (%)')
        ax1.set_xlabel('日期', fontsize=11)
        ax1.set_ylabel('PD 违约概率 (%)', fontsize=11, color='#e74c3c')
        ax1.tick_params(axis='y', labelcolor='#e74c3c')

        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9)

        # ---- 右 Y 轴: EL (柱状图) ----
        ax2 = ax1.twinx()
        # 根据数据点间隔自动估算柱宽度
        if len(dates) > 1:
            avg_interval = (dates.iloc[-1] - dates.iloc[0]) / len(dates)
            bar_width = max(avg_interval.days * 0.6, 1)
        else:
            bar_width = 15
        ax2.bar(dates, el_vals, width=bar_width, color='#f39c12', alpha=0.7,
                zorder=3, label='EL 预期损失')
        ax2.set_ylabel('EL 预期损失 (CNY)', fontsize=11, color='#f39c12')
        ax2.tick_params(axis='y', labelcolor='#f39c12')

        # 合并图例
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=8, framealpha=0.9)

        ax1.set_title(f'{stock_label}  PD 违约概率 与 EL 预期损失 趋势分析', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3, linestyle='--')

        plt.tight_layout()
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        return buf

    # ========================= 表格生成 =========================

    def _chart_zscore_comparison(self, stock_zscore_map: dict) -> BytesIO:
        """
        图表3（综合对比）：日期 X轴，多股票 Z-Score 折线对比

        Args:
            stock_zscore_map: {stock_label: (dates_pd_series, zscore_pd_series)} 

        Returns:
            BytesIO PNG 图片
        """
        if not stock_zscore_map:
            return None

        fig, ax = plt.subplots(figsize=(18, 9))

        # 为每只股票选择不同颜色
        color_cycle = plt.rcParams['axes.prop_cycle'].by_key()['color']
        num_stocks = len(stock_zscore_map)

        all_dates = []
        line_objects = {}  # 记录每只股票最后的 (x, y, color, stock_label)
        for idx, (stock_label, (dates, z_vals)) in enumerate(stock_zscore_map.items()):
            dates_dt = pd.to_datetime(dates, format='%Y%m%d', errors='coerce')
            valid_mask = dates_dt.notna() & z_vals.notna()
            if valid_mask.sum() == 0:
                continue
            d = dates_dt[valid_mask]
            z = z_vals[valid_mask]
            all_dates.extend(d.tolist())

            color = color_cycle[idx % len(color_cycle)]
            ax.plot(d, z, color=color, linewidth=2.0, alpha=0.85, marker='o', markersize=4,
                    zorder=3, label=stock_label)

            # 记录最后一个有效数据点，用于右侧标注
            line_objects[stock_label] = (d.iloc[-1], z.iloc[-1], color)

        if not all_dates:
            plt.close(fig)
            return None

        # ---- 参考线 ----
        ax.axhline(y=self.Z_SAFE, color='#2ecc71', linestyle='--', linewidth=1.5, alpha=0.7,
                   zorder=1, label=f'安全线 Z={self.Z_SAFE}')
        ax.axhline(y=self.Z_GREY, color='orange', linestyle='--', linewidth=1.5, alpha=0.7,
                   zorder=1, label=f'警戒线 Z={self.Z_GREY}')

        # 区域着色
        y_min = ax.get_ylim()[0]
        y_max = ax.get_ylim()[1]
        ax.axhspan(ymin=self.Z_SAFE, ymax=max(y_max, self.Z_SAFE + 1), color='#2ecc71', alpha=0.04, zorder=0)
        ax.axhspan(ymin=self.Z_GREY, ymax=self.Z_SAFE, color='#f1c40f', alpha=0.04, zorder=0)
        ax.axhspan(ymin=min(y_min, self.Z_GREY - 1), ymax=self.Z_GREY, color='#e74c3c', alpha=0.06, zorder=0)

        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('Z-Score', fontsize=12)
        ax.set_title('全股票 Z-Score 综合对比：一张图看清财务风险全景', fontsize=16, fontweight='bold',
                     color='#1a237e')

        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9)
        ax.grid(True, alpha=0.25, linestyle='--')

        # 图例放在左上角，字体缩小
        ncol = 2 if num_stocks > 8 else 1
        ax.legend(loc='upper left', fontsize=7, framealpha=0.92, ncol=ncol,
                  title='股票名称 (代码)', title_fontsize=8)

        # 在每条折线的右端标上股票名称
        for stock_label, (last_x, last_y, color) in line_objects.items():
            ax.annotate(stock_label, xy=(last_x, last_y), xytext=(10, 0),
                        textcoords='offset points', fontsize=7, color=color,
                        va='center', ha='left', fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                                  edgecolor=color, alpha=0.85))

        plt.tight_layout()
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        return buf

    def _generate_comparison_commentary(self, stock_zscore_map: dict) -> str:
        """
        交易员视角：多股票 Z-Score 横向比较解读

        Args:
            stock_zscore_map: {stock_label: (dates, z_vals)}

        Returns:
            HTML 格式的评论文本
        """
        if not stock_zscore_map:
            return "数据不足，无法生成综合对比分析。"

        # 计算每只股票的关键指标
        stock_stats = {}
        for label, (dates, z_vals) in stock_zscore_map.items():
            z = z_vals.dropna()
            if len(z) < 2:
                stock_stats[label] = {
                    'latest_z': z.iloc[-1] if len(z) > 0 else None,
                    'first_z': z.iloc[0] if len(z) > 0 else None,
                    'trend': 'N/A',
                    'trend_pct': 0,
                    'volatility': 0,
                    'risk_zone': 'N/A',
                    'min_z': z.min() if len(z) > 0 else None,
                    'max_z': z.max() if len(z) > 0 else None,
                    'data_points': len(z),
                }
                continue
            latest_z = z.iloc[-1]
            first_z = z.iloc[0]
            trend_pct = (latest_z - first_z) / abs(first_z) * 100 if first_z != 0 else 0

            if latest_z >= self.Z_SAFE:
                zone = '安全区 [GOOD]'
            elif latest_z >= self.Z_GREY:
                zone = '灰色区 [WARN]'
            else:
                zone = '危机区 [CRITICAL]'

            stock_stats[label] = {
                'latest_z': latest_z,
                'first_z': first_z,
                'trend': '上升' if trend_pct > 0 else '下降' if trend_pct < 0 else '持平',
                'trend_pct': trend_pct,
                'volatility': np.std(z),
                'risk_zone': zone,
                'min_z': z.min(),
                'max_z': z.max(),
                'data_points': len(z),
            }

        # ---- 按最新 Z-Score 排序 ----
        sorted_stocks = sorted(stock_stats.items(), key=lambda x: x[1]['latest_z'] or -999)

        # ---- 构建评论 ----
        parts = []

        # 1. 全景概览
        parts.append('<b>[Z-Score 全景一览]</b><br/>')
        for label, stats in sorted_stocks:
            trend_arrow = '↑' if stats['trend'] == '上升' else '↓' if stats['trend'] == '下降' else '→'
            parts.append(
                f"- {label}: 最新 Z={stats['latest_z']:.2f} "
                f"({stats['risk_zone']})  |  {trend_arrow} {stats['trend_pct']:+.1f}%  |  "
                f"波动率 σ={stats['volatility']:.3f}  |  区间 [{stats['min_z']:.2f}, {stats['max_z']:.2f}]"
            )
        parts.append('<br/>')

        # 2. 最安全 vs 最危险
        safest = sorted_stocks[-1] if sorted_stocks else None
        riskiest = sorted_stocks[0] if sorted_stocks else None

        parts.append('<b>[头尾对比]</b><br/>')
        if safest and riskiest and safest != riskiest:
            parts.append(
                f"- 最安全: {safest[0]} (Z={safest[1]['latest_z']:.2f}) —— {safest[1]['risk_zone']}<br/>"
                f"- 最危险: {riskiest[0]} (Z={riskiest[1]['latest_z']:.2f}) —— {riskiest[1]['risk_zone']}<br/>"
                f"- 安全落差: Z 差距达 {safest[1]['latest_z'] - riskiest[1]['latest_z']:.2f}，"
                f"反映出显著的财务质量分化"
            )
        parts.append('<br/>')

        # 3. 趋势分化
        rising = [(l, s) for l, s in sorted_stocks if s['trend'] == '上升' and s['trend_pct'] > 5]
        falling = [(l, s) for l, s in sorted_stocks if s['trend'] == '下降' and s['trend_pct'] < -5]

        parts.append('<b>[趋势分化]</b><br/>')
        if rising:
            parts.append('- 财务改善组 (Z-Score 趋势上升 &gt; 5%): ')
            parts.append(', '.join([f"{l} ({s['trend_pct']:+.1f}%)" for l, s in rising]))
            parts.append('<br/>')
        if falling:
            parts.append('- 财务恶化组 (Z-Score 趋势下降 &gt; 5%): ')
            parts.append(', '.join([f"{l} ({s['trend_pct']:+.1f}%)" for l, s in falling]))
            parts.append('<br/>')
        if not rising and not falling:
            parts.append('- 各股票 Z-Score 整体趋势温和，未出现超过 5% 的大幅变动<br/>')
        parts.append('<br/>')

        # 4. 高波动股票
        high_vol = [(l, s) for l, s in sorted_stocks if s['volatility'] > 1.0]
        parts.append('<b>[波动率异常]</b><br/>')
        if high_vol:
            parts.append('- 高波动股票 (σ &gt; 1.0): ')
            parts.append(', '.join([f"{l} (σ={s['volatility']:.2f})" for l, s in high_vol]))
            parts.append('<br/>')
            parts.append('- 高波动意味着 Z-Score 不稳定，可能反映盈利/资产结构的剧烈变化，需警惕<br/>')
        else:
            parts.append('- 所有股票 Z-Score 波动率均在合理范围内 (&lt; 1.0)，财务指标整体稳定<br/>')
        parts.append('<br/>')

        # 5. 交易员综合建议
        parts.append('<b>[交易员综合建议]</b><br/>')

        # 统计风险区分布
        safe_count = sum(1 for _, s in stock_stats.items() if s['risk_zone'].startswith('安全'))
        grey_count = sum(1 for _, s in stock_stats.items() if s['risk_zone'].startswith('灰色'))
        crisis_count = sum(1 for _, s in stock_stats.items() if s['risk_zone'].startswith('危机'))

        parts.append(
            f"- 持仓结构: 安全区 {safe_count} 只 | 灰色区 {grey_count} 只 | 危机区 {crisis_count} 只<br/>"
        )

        if crisis_count > 0:
            crisis_names = [l for l, s in sorted_stocks if s['risk_zone'].startswith('危机')]
            parts.append(
                f"- [CRITICAL] 危机区标的: {', '.join(crisis_names)}，"
                f"强烈建议重新评估持仓，考虑减仓或设置严格止损<br/>"
            )

        if falling:
            fall_names = [l for l, s in falling]
            parts.append(
                f"- [WARNING] 趋势恶化标的: {', '.join(fall_names)}，"
                f"若恶化趋势延续，应提前制定退出计划<br/>"
            )

        if safe_count >= len(stock_stats) * 0.5:
            parts.append(
                "- 整体组合偏向安全，风险敞口可控。可适度增加安全区优质标的的配置比例<br/>"
            )
        elif grey_count >= len(stock_stats) * 0.5:
            parts.append(
                "- 整体组合处于灰色地带，建议降低整体仓位至 60%-70%，"
                "对灰色区个股实施分批建仓策略<br/>"
            )
        else:
            parts.append(
                "- [WARNING] 组合整体风险偏高，建议全面的风险审查。"
                "严格控制危机区标的持仓比例不超过总资产的 5%<br/>"
            )

        parts.append(
            "<br/>- 建议定期（每月/每季报后）更新本分析，动态监控 Z-Score 轨迹变化<br/>"
            "- 可将 Z-Score 对比图作为投决会的快速风险扫描工具，一眼识别风险敞口"
        )

        return '<br/>'.join(parts)

    # ========================= PD 对比 + AI 分析 =========================

    def _chart_pd_comparison(self, stock_pd_map: dict) -> BytesIO:
        """
        图表4（PD 综合对比）：日期 X轴，多股票 PD 折线对比

        Args:
            stock_pd_map: {stock_label: (dates_pd_series, pd_pd_series)}

        Returns:
            BytesIO PNG 图片
        """
        if not stock_pd_map:
            return None

        fig, ax = plt.subplots(figsize=(18, 9))

        color_cycle = plt.rcParams['axes.prop_cycle'].by_key()['color']
        num_stocks = len(stock_pd_map)

        all_dates = []
        line_objects = {}  # 记录每只股票最后的 (x, y, color, stock_label)
        for idx, (stock_label, (dates, pd_vals)) in enumerate(stock_pd_map.items()):
            dates_dt = pd.to_datetime(dates, format='%Y%m%d', errors='coerce')
            valid_mask = dates_dt.notna() & pd_vals.notna()
            if valid_mask.sum() == 0:
                continue
            d = dates_dt[valid_mask]
            p = pd_vals[valid_mask] * 100  # 转为百分比
            all_dates.extend(d.tolist())

            color = color_cycle[idx % len(color_cycle)]
            ax.plot(d, p, color=color, linewidth=2.0, alpha=0.85, marker='o', markersize=4,
                    zorder=3, label=stock_label)

            # 记录最后一个有效数据点，用于右侧标注
            line_objects[stock_label] = (d.iloc[-1], p.iloc[-1], color)

        if not all_dates:
            plt.close(fig)
            return None

        # ---- 参考线 ----
        ax.axhline(y=1.0, color='#f1c40f', linestyle='--', linewidth=1.5, alpha=0.7,
                   zorder=1, label='关注线 PD=1%')
        ax.axhline(y=5.0, color='#e74c3c', linestyle='--', linewidth=1.5, alpha=0.7,
                   zorder=1, label='警戒线 PD=5%')

        # 区域着色
        y_min, y_max = ax.get_ylim()
        ax.axhspan(ymin=0, ymax=1.0, color='#2ecc71', alpha=0.04, zorder=0)
        ax.axhspan(ymin=1.0, ymax=5.0, color='#f1c40f', alpha=0.04, zorder=0)
        ax.axhspan(ymin=5.0, ymax=max(y_max, 10), color='#e74c3c', alpha=0.06, zorder=0)

        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('PD 违约概率 (%)', fontsize=12)
        ax.set_title('全股票 PD 违约概率 综合对比：风险全景透视', fontsize=16, fontweight='bold',
                     color='#1a237e')

        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9)
        ax.grid(True, alpha=0.25, linestyle='--')

        # 图例放在左上角，字体缩小
        ncol = 2 if num_stocks > 8 else 1
        ax.legend(loc='upper left', fontsize=7, framealpha=0.92, ncol=ncol,
                  title='股票名称 (代码)', title_fontsize=8)

        # 在每条折线的右端标上股票名称
        for stock_label, (last_x, last_y, color) in line_objects.items():
            ax.annotate(stock_label, xy=(last_x, last_y), xytext=(10, 0),
                        textcoords='offset points', fontsize=7, color=color,
                        va='center', ha='left', fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                                  edgecolor=color, alpha=0.85))

        plt.tight_layout()
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        return buf

    def _generate_pd_comparison_commentary(self, stock_pd_map: dict) -> str:
        """
        交易员视角：多股票 PD 违约概率横向比较解读
        """
        if not stock_pd_map:
            return "数据不足，无法生成 PD 综合对比分析。"

        stock_stats = {}
        for label, (dates, pd_vals) in stock_pd_map.items():
            p = pd_vals.dropna() * 100  # 转百分比
            if len(p) < 2:
                stock_stats[label] = {
                    'latest_pd': p.iloc[-1] if len(p) > 0 else None,
                    'first_pd': p.iloc[0] if len(p) > 0 else None,
                    'trend': 'N/A', 'trend_pct': 0,
                    'min_pd': p.min() if len(p) > 0 else None,
                    'max_pd': p.max() if len(p) > 0 else None,
                }
                continue
            latest_pd = p.iloc[-1]
            first_pd = p.iloc[0]
            trend_pct = (latest_pd - first_pd) / abs(first_pd) * 100 if first_pd != 0 else 0

            if latest_pd < 1.0:
                zone = '低风险 [GOOD]'
            elif latest_pd < 5.0:
                zone = '中等风险 [WARN]'
            else:
                zone = '高风险 [CRITICAL]'

            stock_stats[label] = {
                'latest_pd': latest_pd,
                'first_pd': first_pd,
                'trend': '恶化' if trend_pct > 10 else '改善' if trend_pct < -10 else '平稳',
                'trend_pct': trend_pct,
                'min_pd': p.min(),
                'max_pd': p.max(),
                'risk_zone': zone,
            }

        sorted_stocks = sorted(stock_stats.items(), key=lambda x: x[1]['latest_pd'] or 999)
        parts = []

        # 全景
        parts.append('<b>[PD 违约概率一览]</b><br/>')
        for label, stats in sorted_stocks:
            trend_arrow = '↑' if stats['trend'] == '恶化' else '↓' if stats['trend'] == '改善' else '→'
            parts.append(
                f"- {label}: 最新 PD={stats['latest_pd']:.2f}% "
                f"({stats['risk_zone']})  |  {trend_arrow} {stats['trend_pct']:+.1f}%  |  "
                f"区间 [{stats['min_pd']:.2f}%, {stats['max_pd']:.2f}%]"
            )
        parts.append('<br/>')

        # 风险分布
        high_risk = [(l, s) for l, s in sorted_stocks if s['risk_zone'].startswith('高风险')]
        med_risk = [(l, s) for l, s in sorted_stocks if s['risk_zone'].startswith('中等')]
        low_risk = [(l, s) for l, s in sorted_stocks if s['risk_zone'].startswith('低风险')]

        parts.append('<b>[风险分布]</b><br/>')
        parts.append(f"- 低风险 (PD &lt; 1%): {len(low_risk)} 只 —— "
                     f"{', '.join([l for l, _ in low_risk]) if low_risk else '无'}<br/>")
        parts.append(f"- 中等风险 (1% ≤ PD &lt; 5%): {len(med_risk)} 只 —— "
                     f"{', '.join([l for l, _ in med_risk]) if med_risk else '无'}<br/>")
        parts.append(f"- 高风险 (PD ≥ 5%): {len(high_risk)} 只 —— "
                     f"{', '.join([l for l, _ in high_risk]) if high_risk else '无'}<br/>")
        parts.append('<br/>')

        # 头尾对比
        safest_pd = sorted_stocks[0] if sorted_stocks else None
        riskiest_pd = sorted_stocks[-1] if sorted_stocks else None
        parts.append('<b>[违约概率落差]</b><br/>')
        if safest_pd and riskiest_pd and safest_pd != riskiest_pd:
            parts.append(f"- 最低违约概率: {safest_pd[0]} (PD={safest_pd[1]['latest_pd']:.2f}%)<br/>")
            parts.append(f"- 最高违约概率: {riskiest_pd[0]} (PD={riskiest_pd[1]['latest_pd']:.2f}%)<br/>")
            parts.append(f"- PD 落差达 {riskiest_pd[1]['latest_pd'] - safest_pd[1]['latest_pd']:.2f}%，"
                          f"组合内信用质量严重分化<br/>")
        parts.append('<br/>')

        # 恶化信号
        deteriorating = [(l, s) for l, s in sorted_stocks if s['trend'] == '恶化']
        parts.append('<b>[违约风险恶化预警]</b><br/>')
        if deteriorating:
            parts.append('- PD 持续升高的标的（违约风险在积累）: ')
            parts.append(', '.join([f"{l} ({s['trend_pct']:+.1f}%)" for l, s in deteriorating]))
            parts.append('<br/>')
            parts.append('- [WARNING] 这些标的 PD 呈上升趋势，信用质量正在恶化，建议及时评估持仓风险<br/>')
        else:
            parts.append('- 未检测到 PD 持续恶化的标的，信用风险整体可控<br/>')
        parts.append('<br/>')

        # 交易员建议
        parts.append('<b>[交易员 PD 综合建议]</b><br/>')
        if high_risk:
            high_names = [l for l, _ in high_risk]
            parts.append(
                f"- [CRITICAL] 高风险标的: {', '.join(high_names)}，"
                f"PD 超过 5%，强烈建议设置硬止损，单券仓位不超过 2%<br/>"
            )
        if len(low_risk) >= len(stock_stats) * 0.6:
            parts.append("- 组合信用质量整体优良，可适度加大低风险标的配置比例<br/>")
        elif len(high_risk) > 0:
            parts.append("- 建议定期跟踪 PD 轨迹，关注 PD 上升斜率最大的标的，提前制定应急减仓方案<br/>")
        parts.append("- PD 作为违约概率的前瞻指标，应结合 Z-Score 财务健康度综合判断，避免单一指标误判<br/>")

        return '<br/>'.join(parts)

    def _generate_ai_pd_analysis(self, stock_data_map: dict) -> str:
        """
        调用 AI（ZhipuGLM4）对股票 PD/Z-Score/EL 数据进行综合评估

        Args:
            stock_data_map: {stock_label: {'symbol', 'name', 'latest_date', 
                                            'pd_series', 'zscore_series', 'el_series',
                                            'pd_latest', 'z_latest', 'el_latest',
                                            'risk_level'}}

        Returns:
            AI 分析文本，失败时返回错误信息
        """
        if not stock_data_map:
            logger.warning("无数据，跳过 AI 分析")
            return "数据不足，无法生成 AI 分析。"

        # 构建每只股票的摘要行（处理nan）
        data_lines = []
        for label, info in stock_data_map.items():
            z_val = info.get('z_latest')
            pd_val = info.get('pd_latest')
            el_val = info.get('el_latest')
            z_str = f"{z_val:.4f}" if z_val is not None and not (isinstance(z_val, float) and pd.isna(z_val)) else 'N/A'
            pd_str = f"{pd_val*100:.4f}%" if pd_val is not None and not (isinstance(pd_val, float) and pd.isna(pd_val)) else 'N/A'
            el_str = f"{el_val:,.0f}" if el_val is not None and not (isinstance(el_val, float) and pd.isna(el_val)) else 'N/A'
            data_lines.append(
                f"- {label}: 最新日期={info.get('latest_date','')}, "
                f"Z-Score={z_str}, PD={pd_str}, "
                f"EL(预期损失)={el_str}, 风险等级={info.get('risk_level','')}"
            )

        n = len(data_lines)
        data_block = "\n".join(data_lines)

        prompt = f"""你是一个拥有15年经验的股票交易员和信用风险分析师，擅长将量化信用指标与基本面分析相结合进行投资决策。

以下是 {n} 只股票的 PD（违约概率）分析数据，包括 Z-Score（Altman财务健康度）、PD 违约概率、EL 预期损失和风险等级， 直接给出交易与风控结论。
不要做加权计算，不要重复数据，只做判断和解释。：

【输入数据】
{data_block}

参考阈值：
- Z-Score: ≥3.0 安全区, 1.8-3.0 灰色区, <1.8 危机区
- PD: <1% 低风险, 1-5% 中等风险, >5% 高风险

请回答以下问题（每点不超过 3 句话）：
组合整体风险结论
整体偏向安全、中性还是高危？
是否存在明显的尾部风险？
风险最高的 3 只股票
谁最危险？为什么？（结合 Z / PD / 行业）
风险最低的 3 只股票
谁最安全？是否值得重仓？
最反常的 2 只股票
举例：高 Z 但高 PD，或低 Z 但低 PD，说明可能原因
交易与风控建议（直接可用）
哪些应减仓 / 清仓 / 禁止新建仓？
哪些可作为核心持仓？
是否需要设置硬性止损或对冲？
✅ 输出格式：
用 bullet point
不要表格
不要计算过程
语言像投研晨报，简洁、直接、可上会"""

        logger.info(f"=" * 60)
        logger.info(f"AI PD 分析 Prompt（{n} 只股票）")
        logger.info(f"=" * 60)
        logger.info(prompt)
        logger.info(f"=" * 60)

        if CommonParameters.IF_ENABLE_MOCKED_AI:
            logger.info("IF_ENABLE_MOCKED_AI=True，返回模拟 AI 分析报告")
            return ("（模拟 AI 分析报告）\n\n"
                    "1. 整体信用风险评估: 该组合整体信用风险处于中等水平，存在明显的个券分化...\n\n"
                    "2. 风险分级分析: ...\n\n"
                    "3. 财务健康度分化: ...\n\n"
                    "4. 仓位管理建议: ...\n\n"
                    "5. 投资组合配置建议: ...\n\n"
                    "（以上为 MOCK 数据，实际分析请设置 IF_ENABLE_MOCKED_AI=False）")

        try:
            logger.info("正在调用 ZhipuGLM4 生成 AI PD 分析...")
            result = ZhipuGLM4.inquiry(prompt, "")
            logger.info("ZhipuGLM4 AI PD 分析生成成功")
            return result
        except Exception as e:
            logger.error(f"AI PD 分析生成失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return f"AI 分析生成失败: {e}"

    def _build_data_table(self, df: pd.DataFrame) -> Table:
        """
        构建数据表格（ReportLab Table），显示 PD 核心字段

        列: 日期 | Z-Score | 风险等级 | PD | EL | EAD | X1 | X2 | X3 | X4 | X5
        """
        display_cols = ['date', 'z_score', 'risk_level', 'pd', 'el', 'ead',
                        'x1', 'x2', 'x3', 'x4', 'x5']

        # 表头使用专门的样式（文字白色）
        header_style = self._header_cell_style()
        header = [
            Paragraph('<b><font color="white">日期</font></b>', header_style),
            Paragraph('<b><font color="white">Z-Score</font></b>', header_style),
            Paragraph('<b><font color="white">风险等级</font></b>', header_style),
            Paragraph('<b><font color="white">PD</font></b>', header_style),
            Paragraph('<b><font color="white">EL</font></b>', header_style),
            Paragraph('<b><font color="white">EAD</font></b>', header_style),
            Paragraph('<b><font color="white">X1</font></b>', header_style),
            Paragraph('<b><font color="white">X2</font></b>', header_style),
            Paragraph('<b><font color="white">X3</font></b>', header_style),
            Paragraph('<b><font color="white">X4</font></b>', header_style),
            Paragraph('<b><font color="white">X5</font></b>', header_style),
        ]

        data_rows = [header]

        # 数据行 (倒序: 最新在前)
        for _, row in df.sort_values('date', ascending=False).iterrows():
            risk_cn = self.RISK_LEVEL_CN.get(row.get('risk_level', ''), row.get('risk_level', ''))

            data_rows.append([
                Paragraph(str(row['date']), self._cell_style(font_size=7)),
                Paragraph(f"{row['z_score']:.4f}" if pd.notna(row.get('z_score')) else '-',
                          self._cell_style(font_size=7)),
                Paragraph(risk_cn, self._cell_style(font_size=7)),
                Paragraph(f"{row['pd']*100:.4f}%" if pd.notna(row.get('pd')) else '-',
                          self._cell_style(font_size=7)),
                Paragraph(f"{row['el']:.2f}" if pd.notna(row.get('el')) else '-',
                          self._cell_style(font_size=7)),
                Paragraph(f"{row['ead']:,.0f}" if pd.notna(row.get('ead')) else '-',
                          self._cell_style(font_size=7)),
                Paragraph(f"{row['x1']:.4f}" if pd.notna(row.get('x1')) else '-',
                          self._cell_style(font_size=7)),
                Paragraph(f"{row['x2']:.4f}" if pd.notna(row.get('x2')) else '-',
                          self._cell_style(font_size=7)),
                Paragraph(f"{row['x3']:.4f}" if pd.notna(row.get('x3')) else '-',
                          self._cell_style(font_size=7)),
                Paragraph(f"{row['x4']:.4f}" if pd.notna(row.get('x4')) else '-',
                          self._cell_style(font_size=7)),
                Paragraph(f"{row['x5']:.4f}" if pd.notna(row.get('x5')) else '-',
                          self._cell_style(font_size=7)),
            ])

        col_widths = [65, 58, 90, 58, 58, 70, 52, 52, 52, 52, 52]

        table = Table(data_rows, colWidths=col_widths, repeatRows=1)

        # 表头样式
        style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), REPORTLAB_FONT),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('TOPPADDING', (0, 1), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
        ]

        # 风险等级行着色: 红色行 = 危机区, 黄色行 = 灰色区
        for i, (_, row) in enumerate(df.sort_values('date', ascending=False).iterrows(), start=1):
            rl = row.get('risk_level', '')
            if rl == 'red_distress':
                style_cmds.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#ffebee')))
                style_cmds.append(('TEXTCOLOR', (0, i), (-1, i), colors.HexColor('#c62828')))
            elif rl == 'yellow_grey':
                style_cmds.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fff8e1')))
                style_cmds.append(('TEXTCOLOR', (0, i), (-1, i), colors.HexColor('#f57f17')))

        table.setStyle(TableStyle(style_cmds))
        return table

    def _header_cell_style(self):
        """表头专用样式（白色文字）"""
        return ParagraphStyle(
            'header_cell', fontName=REPORTLAB_FONT, fontSize=8,
            leading=12, alignment=TA_CENTER, textColor=colors.white,
        )

    def _cell_style(self, font_size=7):
        return ParagraphStyle(
            'cell', fontName=REPORTLAB_FONT, fontSize=font_size,
            leading=font_size + 4, alignment=TA_CENTER,
        )

    # ========================= Z-Score 风险热力图 =========================

    def _zscore_heatmap_color(self, z_score, z_min, z_max):
        """
        三区渐变热力图颜色:

        🔴 红色区 Z ∈ [z_min, 1.8]:   深红 → 浅粉红
        🟡 黄色区 Z ∈ (1.8, 3.0):     浅黄 → 琥珀黄
        🟢 绿色区 Z ∈ [3.0, z_max]:   深绿 → 墨绿

        Args:
            z_score: 当前 Z-Score 值
            z_min: 全局最小 Z-Score
            z_max: 全局最大 Z-Score

        Returns:
            reportlab Color
        """
        if pd.isna(z_score):
            return colors.HexColor('#eeeeee')

        # 三区边界
        bound_red = self.Z_GREY       # 1.8  红色区上界
        bound_yellow = self.Z_SAFE    # 3.0  黄色区上界

        if z_score <= bound_red:
            # ── 红色区: 深红(z_min) → 浅粉红(1.8) ──
            if bound_red <= z_min:
                t = 0.0
            else:
                t = (z_score - z_min) / (bound_red - z_min)
            t = max(0.0, min(1.0, t))
            r = int(183 + (255 - 183) * t)  # #b71c1c → #ffcdd2
            g = int(28 + (205 - 28) * t)
            b = int(28 + (210 - 28) * t)

        elif z_score < bound_yellow:
            # ── 黄色区: 浅黄(1.8) → 琥珀黄(3.0) ──
            t = (z_score - bound_red) / (bound_yellow - bound_red)
            t = max(0.0, min(1.0, t))
            r = int(255 + (249 - 255) * t)  # #fff9c4 → #f9a825
            g = int(249 + (168 - 249) * t)
            b = int(196 + (37 - 196) * t)

        else:
            # ── 绿色区: 深绿(3.0) → 墨绿(z_max) ──
            if z_max <= bound_yellow:
                t = 0.0
            else:
                t = (z_score - bound_yellow) / (z_max - bound_yellow)
            t = max(0.0, min(1.0, t))
            r = int(46 + (27 - 46) * t)   # #2e7d32 → #1b5e20
            g = int(125 + (94 - 125) * t)
            b = int(50 + (32 - 50) * t)

        return colors.HexColor('#%02x%02x%02x' % (r, g, b))

    def _pd_heatmap_color(self, pd_val, pd_min, pd_max):
        """
        三区渐变热力图颜色 (PD 违约概率):

        🟢 绿色区 PD ∈ [pd_min, 0.02]:      深绿 → 浅绿  (低违约风险)
        🟡 黄色区 PD ∈ (0.02, 0.10]:          浅黄 → 琥珀黄 (中违约风险)
        🔴 红色区 PD ∈ (0.10, pd_max]:         浅红 → 深红   (高违约风险)

        Args:
            pd_val: 当前 PD 值 (小数，非百分比)
            pd_min: 全局最小 PD
            pd_max: 全局最大 PD

        Returns:
            reportlab Color
        """
        if pd.isna(pd_val):
            return colors.HexColor('#eeeeee')

        bound_green = 0.02   #  2% — 绿/黄分界
        bound_yellow = 0.10  # 10% — 黄/红分界

        if pd_val <= bound_green:
            # ── 绿色区: 深绿(pd_min) → 浅绿(2%) ──
            if bound_green <= pd_min:
                t = 0.0
            else:
                t = (pd_val - pd_min) / (bound_green - pd_min)
            t = max(0.0, min(1.0, t))
            r = int(27 + (165 - 27) * t)    # #1b5e20 → #a5d6a7
            g = int(94 + (214 - 94) * t)
            b = int(32 + (167 - 32) * t)

        elif pd_val < bound_yellow:
            # ── 黄色区: 浅黄(2%) → 琥珀黄(10%) ──
            t = (pd_val - bound_green) / (bound_yellow - bound_green)
            t = max(0.0, min(1.0, t))
            r = int(255 + (249 - 255) * t)  # #fff9c4 → #f9a825
            g = int(249 + (168 - 249) * t)
            b = int(196 + (37 - 196) * t)

        else:
            # ── 红色区: 浅红(10%) → 深红(pd_max) ──
            if pd_max <= bound_yellow:
                t = 0.0
            else:
                t = (pd_val - bound_yellow) / (pd_max - bound_yellow)
            t = max(0.0, min(1.0, t))
            r = int(255 + (183 - 255) * t)  # #ffcdd2 → #b71c1c
            g = int(205 + (28 - 205) * t)
            b = int(210 + (28 - 210) * t)

        return colors.HexColor('#%02x%02x%02x' % (r, g, b))

    def _build_pd_heatmap(self, stock_pd_data, all_dates_raw, stock_industry_map=None):
        """
        构建 PD 违约概率热力图表格

        列：板块 | 股票名称 | 日期1 | 日期2 | ...
        行按板块排序，同板块内按股票名称排序
        颜色从绿 (低PD/低违约风险) 渐变到红 (高PD/高违约风险)

        Args:
            stock_pd_data: dict of stock_label -> (date_series, pd_series)，pd 为小数
            all_dates_raw: 所有日期字符串的列表
            stock_industry_map: dict of stock_label -> industry（可选）

        Returns:
            ReportLab Table 或 None
        """
        if len(stock_pd_data) < 2:
            return None

        # 排序去重日期
        unique_dates = sorted(set(all_dates_raw))
        if not unique_dates:
            return None

        # 构建查表: stock_label -> {date: pd_value}
        stock_date_pd = {}
        for stock_label, (date_series, pd_series) in stock_pd_data.items():
            stock_date_pd[stock_label] = dict(zip(date_series, pd_series))

        # 全局 PD 范围（用于颜色映射）
        all_pd = []
        for pd_map in stock_date_pd.values():
            for p in pd_map.values():
                if pd.notna(p):
                    all_pd.append(p)
        pd_min = min(all_pd) if all_pd else 0
        pd_max = max(all_pd) if all_pd else 0.20

        # 板块映射（未提供则标记为 "-"）
        if stock_industry_map is None:
            stock_industry_map = {label: '-' for label in stock_date_pd}

        # 按板块排序：先板块名，再股票名
        sorted_labels = sorted(stock_date_pd.keys(),
                               key=lambda lb: (stock_industry_map.get(lb, '未知'), lb))

        # ---------- 表头 ----------
        header = [
            Paragraph('<b><font color="white">板块</font></b>',
                      ParagraphStyle('pdhm_hdr_s', fontName=REPORTLAB_FONT, fontSize=5,
                                     leading=6, alignment=TA_CENTER, textColor=colors.white)),
            Paragraph('<b><font color="white">股票名称</font></b>',
                      ParagraphStyle('pdhm_hdr_s', fontName=REPORTLAB_FONT, fontSize=5,
                                     leading=6, alignment=TA_CENTER, textColor=colors.white)),
        ]

        for d in unique_dates:
            date_str = str(d)
            # 格式化: YYYYMMDD → YYMM
            if len(date_str) >= 6:
                short_date = date_str[2:6]
            else:
                short_date = date_str
            header.append(Paragraph(
                f'<b><font color="white">{short_date}</font></b>',
                ParagraphStyle('pdhm_hdr', fontName=REPORTLAB_FONT, fontSize=5,
                               leading=6, alignment=TA_CENTER, textColor=colors.white)
            ))

        data_rows = [header]

        # ---------- 数据行 ----------
        for stock_label in sorted_labels:
            industry = stock_industry_map.get(stock_label, '-')
            row = [
                Paragraph(industry,
                          ParagraphStyle('pdhm_ind', fontName=REPORTLAB_FONT, fontSize=6,
                                         leading=8, alignment=TA_CENTER)),
                Paragraph(stock_label,
                          ParagraphStyle('pdhm_stock', fontName=REPORTLAB_FONT, fontSize=6,
                                         leading=8, alignment=TA_LEFT)),
            ]
            for d in unique_dates:
                p = stock_date_pd[stock_label].get(d)
                if p is not None and pd.notna(p):
                    row.append(Paragraph(f'{p*100:.2f}%', self._cell_style(font_size=5)))
                else:
                    row.append(Paragraph('-', self._cell_style(font_size=5)))
            data_rows.append(row)

        # ---------- 列宽 ----------
        industry_col_width = 2.2 * cm
        stock_col_width = 3.5 * cm
        label_total = industry_col_width + stock_col_width
        n_date_cols = len(unique_dates)
        date_col_width = max(0.9 * cm, (26.0 * cm - label_total) / n_date_cols)
        col_widths = [industry_col_width, stock_col_width] + [date_col_width] * n_date_cols

        table = Table(data_rows, colWidths=col_widths, repeatRows=1)

        # ---------- 基础样式 ----------
        style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#bdc3c7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
            ('LEFTPADDING', (1, 1), (1, -1), 3),
        ]

        # ---------- 按 PD 逐格着色（日期列从 col 2 开始）----------
        for row_idx, stock_label in enumerate(sorted_labels, start=1):
            for col_idx, d in enumerate(unique_dates, start=2):
                p = stock_date_pd[stock_label].get(d)
                if p is not None and pd.notna(p):
                    bg_color = self._pd_heatmap_color(p, pd_min, pd_max)
                    style_cmds.append(('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), bg_color))
                    # 深色背景用白字
                    if p > 0.08:  # PD > 8% 深色区
                        style_cmds.append(('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), colors.white))

        table.setStyle(TableStyle(style_cmds))
        return table

    def _build_zscore_heatmap(self, stock_zscore_data, all_dates_raw, stock_industry_map=None):
        """
        构建 Z-Score 风险热力图表格

        列：板块 | 股票名称 | 日期1 | 日期2 | ...
        行按板块排序，同板块内按股票名称排序
        颜色从红 (低Z/高风险) 渐变到绿 (高Z/低风险)

        Args:
            stock_zscore_data: dict of stock_label -> (date_series, z_score_series)
            all_dates_raw: 所有日期字符串的列表
            stock_industry_map: dict of stock_label -> industry（可选）

        Returns:
            ReportLab Table 或 None
        """
        if len(stock_zscore_data) < 2:
            return None

        # 排序去重日期
        unique_dates = sorted(set(all_dates_raw))
        if not unique_dates:
            return None

        # 构建查表: stock_label -> {date: z_score}
        stock_date_z = {}
        for stock_label, (date_series, z_series) in stock_zscore_data.items():
            stock_date_z[stock_label] = dict(zip(date_series, z_series))

        # 全局 Z-Score 范围（用于颜色映射）
        all_z = []
        for z_map in stock_date_z.values():
            for z in z_map.values():
                if pd.notna(z):
                    all_z.append(z)
        z_min = min(all_z) if all_z else 0
        z_max = max(all_z) if all_z else 6

        # 板块映射（未提供则标记为 "-"）
        if stock_industry_map is None:
            stock_industry_map = {label: '-' for label in stock_date_z}

        # 按板块排序：先板块名，再股票名
        sorted_labels = sorted(stock_date_z.keys(),
                               key=lambda lb: (stock_industry_map.get(lb, '未知'), lb))

        # ---------- 表头 ----------
        header_style = self._header_cell_style()
        header = [
            Paragraph('<b><font color="white">板块</font></b>',
                      ParagraphStyle('hm_hdr_s', fontName=REPORTLAB_FONT, fontSize=5,
                                     leading=6, alignment=TA_CENTER, textColor=colors.white)),
            Paragraph('<b><font color="white">股票名称</font></b>',
                      ParagraphStyle('hm_hdr_s', fontName=REPORTLAB_FONT, fontSize=5,
                                     leading=6, alignment=TA_CENTER, textColor=colors.white)),
        ]

        for d in unique_dates:
            date_str = str(d)
            # 格式化: YYYYMMDD → YYMM（去掉斜杠避免换行）
            if len(date_str) >= 6:
                short_date = date_str[2:6]
            else:
                short_date = date_str
            header.append(Paragraph(
                f'<b><font color="white">{short_date}</font></b>',
                ParagraphStyle('hm_hdr', fontName=REPORTLAB_FONT, fontSize=5,
                               leading=6, alignment=TA_CENTER, textColor=colors.white)
            ))

        data_rows = [header]

        # ---------- 数据行 ----------
        for stock_label in sorted_labels:
            industry = stock_industry_map.get(stock_label, '-')
            row = [
                Paragraph(industry,
                          ParagraphStyle('hm_ind', fontName=REPORTLAB_FONT, fontSize=6,
                                         leading=8, alignment=TA_CENTER)),
                Paragraph(stock_label,
                          ParagraphStyle('hm_stock', fontName=REPORTLAB_FONT, fontSize=6,
                                         leading=8, alignment=TA_LEFT)),
            ]
            for d in unique_dates:
                z = stock_date_z[stock_label].get(d)
                if z is not None and pd.notna(z):
                    row.append(Paragraph(f'{z:.2f}', self._cell_style(font_size=5)))
                else:
                    row.append(Paragraph('-', self._cell_style(font_size=5)))
            data_rows.append(row)

        # ---------- 列宽 ----------
        industry_col_width = 2.2 * cm
        stock_col_width = 3.5 * cm
        label_total = industry_col_width + stock_col_width
        n_date_cols = len(unique_dates)
        # 横版 A4 可用宽度约 26cm
        date_col_width = max(0.9 * cm, (26.0 * cm - label_total) / n_date_cols)
        col_widths = [industry_col_width, stock_col_width] + [date_col_width] * n_date_cols

        table = Table(data_rows, colWidths=col_widths, repeatRows=1)

        # ---------- 基础样式 ----------
        style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#bdc3c7')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('ALIGN', (2, 0), (-1, -1), 'CENTER'),
            ('LEFTPADDING', (1, 1), (1, -1), 3),
        ]

        # ---------- 按 Z-Score 逐格着色（日期列从 col 2 开始）----------
        for row_idx, stock_label in enumerate(sorted_labels, start=1):
            for col_idx, d in enumerate(unique_dates, start=2):
                z = stock_date_z[stock_label].get(d)
                if z is not None and pd.notna(z):
                    bg_color = self._zscore_heatmap_color(z, z_min, z_max)
                    style_cmds.append(('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), bg_color))
                    # 深色背景用白字，提升可读性
                    if z < self.Z_GREY + 0.5:
                        style_cmds.append(('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), colors.white))

        table.setStyle(TableStyle(style_cmds))
        return table

    # ========================= 专业评论 =========================

    def _generate_professional_commentary(self, df: pd.DataFrame, stock_label: str) -> str:
        """
        从交易员专业角度，根据 matrics 表信息对该股票进行分析

        评论要点:
        - Z-Score 趋势与风险等级变化
        - PD 违约概率走势及关键拐点
        - EL 预期损失变化
        - X1~X5 各分量贡献分析
        - 财务健康状况综合判断
        - 建议操作策略
        """
        if df.empty:
            return "数据不足，无法生成分析评论。"

        latest = df.sort_values('date', ascending=False).iloc[0]
        oldest = df.sort_values('date', ascending=True).iloc[0]

        z_latest = latest.get('z_score', np.nan)
        z_oldest = oldest.get('z_score', np.nan)
        risk_level = latest.get('risk_level', '')
        pd_latest = latest.get('pd', np.nan)
        el_latest = latest.get('el', np.nan)

        x1 = latest.get('x1', np.nan)
        x2 = latest.get('x2', np.nan)
        x3 = latest.get('x3', np.nan)
        x4 = latest.get('x4', np.nan)
        x5 = latest.get('x5', np.nan)

        # ---- 趋势判断 ----
        z_values = df['z_score'].dropna().values
        if len(z_values) >= 2:
            z_trend = '上升' if z_values[-1] > z_values[0] else '下降'
            z_trend_pct = (z_values[-1] - z_values[0]) / abs(z_values[0]) * 100 if z_values[0] != 0 else 0
            z_volatility = np.std(z_values)
        else:
            z_trend = 'N/A'
            z_trend_pct = 0
            z_volatility = 0

        # ---- 风险等级解读 ----
        risk_map = {
            'green_safe': '[安全区] 公司财务稳健，违约风险极低，适合长期持有',
            'yellow_grey': '[灰色区] 需关注财务状况，存在一定违约隐患，建议控制仓位',
            'red_distress': '[危机区] 财务压力显著，违约风险较高，建议严格止损或规避',
        }
        risk_comment = risk_map.get(risk_level, f'未知等级: {risk_level}')

        # ---- X 分量分析 ----
        component_analysis = self._analyze_components(x1, x2, x3, x4, x5)

        # ---- 异常检测 ----
        alerts = []
        if pd_latest > 0.05:
            alerts.append(f"[WARNING] 当期 PD 为 {pd_latest*100:.2f}%，超过 5% 警戒线，违约风险显著偏高")
        if el_latest > 25000:
            alerts.append(f"[WARNING] 当期 EL 为 {el_latest:,.0f} CNY，预期损失较高，建议立即评估持仓风险")
        if z_volatility > 1.5:
            alerts.append(f"[WARNING] Z-Score 波动率 {z_volatility:.2f}，财务指标波动剧烈，稳定性存疑")
        if not pd.isna(z_latest) and z_latest < 1.0:
            alerts.append(f"[CRITICAL] Z-Score 仅为 {z_latest:.2f}，远低于 1.8 警戒线，处于严重财务危机区域")

        # ---- 拼接评论 ----
        title_name = df['name'].iloc[0] if 'name' in df.columns and pd.notna(df['name'].iloc[0]) else stock_label
        industry = df['industry'].iloc[0] if 'industry' in df.columns and pd.notna(df['industry'].iloc[0]) else '未知'

        comment = f"""
        <b>[{title_name}] PD 违约概率深度分析报告</b><br/><br/>

        <b>[基本信息]</b><br/>
        - 股票名称: {title_name}<br/>
        - 行业: {industry}<br/>
        - 数据区间: {df['date'].min()} ~ {df['date'].max()} ({len(df)} 期)<br/>
        - 最新 Z-Score: {z_latest:.4f}  |  最新 PD: {pd_latest*100:.4f}%  |  最新 EL: {el_latest:,.0f} CNY<br/><br/>

        <b>[Z-Score 趋势分析]</b><br/>
        - 趋势方向: {z_trend}（变动 {z_trend_pct:+.1f}%）<br/>
        - 波动率: {z_volatility:.3f}<br/>
        - 起始值: {z_oldest:.4f} → 最新值: {z_latest:.4f}<br/>
        - 风险等级: {risk_comment}<br/><br/>

        <b>[Altman Z-Score 分量拆解]</b><br/>
        {component_analysis}<br/><br/>

        <b>[风险警示]</b><br/>
        {'<br/>'.join(alerts) if alerts else '[OK] 未触发重要风险警报，当前财务状况相对可控'}<br/><br/>

        <b>[交易员建议]</b><br/>
        {self._trading_advice(z_latest, z_trend, pd_latest, risk_level)}<br/>
        """

        return comment

    def _analyze_components(self, x1, x2, x3, x4, x5) -> str:
        """分析 Altman Z-Score 五个分量的贡献"""
        parts = []

        # X1 = (流动资产 - 流动负债) / 总资产 → 营运资本效率
        if not pd.isna(x1):
            if x1 > 0.2:
                parts.append(f"- X1 (营运资本占比) = {x1:.4f} [GOOD] 良好，短期流动性充裕")
            elif x1 >= 0:
                parts.append(f"- X1 (营运资本占比) = {x1:.4f} [WARN] 一般，营运资本不足")
            else:
                parts.append(f"- X1 (营运资本占比) = {x1:.4f} [BAD] 负值，流动负债超过流动资产，短期偿债压力大")

        # X2 = 留存收益 / 总资产 → 盈利能力积累
        if not pd.isna(x2):
            if x2 > 0.1:
                parts.append(f"- X2 (留存收益占比) = {x2:.4f} [GOOD] 良好，企业有持续盈利积累")
            elif x2 >= 0:
                parts.append(f"- X2 (留存收益占比) = {x2:.4f} [WARN] 偏低，盈利积累有限")
            else:
                parts.append(f"- X2 (留存收益占比) = {x2:.4f} [BAD] 负值，累计亏损，盈利持续性存疑")

        # X3 = EBIT / 总资产 → 资产回报率
        if not pd.isna(x3):
            if x3 > 0.08:
                parts.append(f"- X3 (资产回报率) = {x3:.4f} [GOOD] 良好，资产盈利能力较强")
            elif x3 >= 0:
                parts.append(f"- X3 (资产回报率) = {x3:.4f} [WARN] 偏低，资产回报不足")
            else:
                parts.append(f"- X3 (资产回报率) = {x3:.4f} [BAD] 负值，主营业务或投资出现亏损")

        # X4 = 股东权益 / 总负债 → 杠杆水平
        if not pd.isna(x4):
            if x4 > 1.5:
                parts.append(f"- X4 (权益负债比) = {x4:.4f} [GOOD] 良好，杠杆率低，财务结构健康")
            elif x4 >= 0.5:
                parts.append(f"- X4 (权益负债比) = {x4:.4f} [WARN] 中等，杠杆水平需关注")
            else:
                parts.append(f"- X4 (权益负债比) = {x4:.4f} [BAD] 偏低，负债水平过高，偿债风险大")

        # X5 = 收入 / 总资产 → 资产周转效率
        if not pd.isna(x5):
            if x5 > 0.8:
                parts.append(f"- X5 (资产周转率) = {x5:.4f} [GOOD] 良好，资产运营效率高")
            elif x5 >= 0.3:
                parts.append(f"- X5 (资产周转率) = {x5:.4f} [WARN] 一般，资产周转效率有待提升")
            else:
                parts.append(f"- X5 (资产周转率) = {x5:.4f} [BAD] 偏低，资产利用效率不足，可能存在大量闲置资产")

        return '<br/>'.join(parts) if parts else '无可用分量数据'

    def _trading_advice(self, z_latest, z_trend, pd_latest, risk_level) -> str:
        """给出交易建议"""
        if pd.isna(z_latest):
            return '数据不足，无法给出具体建议。'

        if risk_level == 'green_safe':
            advice = (
                "- 该股票处于财务安全区，适合作为核心持仓<br/>"
                "- 建议仓位: 可占总仓位的 10%-20%<br/>"
                "- 建议止损线: Z-Score 跌破 2.5 时减仓，跌破 1.8 时清仓<br/>"
                "- 关注 X3 (资产回报率) 和 X5 (周转率) 的变化趋势，把握基本面拐点"
            )
        elif risk_level == 'yellow_grey':
            advice = (
                "- 该股票处于财务灰色区，需审慎评估<br/>"
                "- 建议仓位: 不超过总仓位的 5%-10%<br/>"
                "- 建议止损线: Z-Score 跌破 1.5 时减仓，跌破 1.0 时清仓<br/>"
                "- 重点监控 X1 (流动性) 和 X4 (杠杆) 分量的变化，若持续恶化应果断离场<br/>"
                "- 可结合行业景气度、管理层变动等非量化因素综合判断"
            )
        else:  # red_distress
            advice = (
                "- [WARNING] 该股票处于财务危机区，不建议新增持仓<br/>"
                "- 已持有者建议: 设置硬止损 (价格止损 -8%~-10%)<br/>"
                f"- PD 为 {pd_latest*100:.2f}%，预期损失风险较高<br/>"
                "- 密切关注是否触发债务违约、评级下调等负面事件<br/>"
                "- 考虑通过可转债、期权等方式对冲下行风险<br/>"
                "- 若 X4 (杠杆) 和 X1 (流动性) 同时恶化，应立即清仓"
            )

        # 趋势附加
        if z_trend == '下降':
            advice += (
                "<br/><br/><b>[趋势警示]</b>: Z-Score 处于下降趋势，财务质量在恶化，"
                "建议密切关注下一季报，提前做好风险管理"
            )
        elif z_trend == '上升':
            advice += (
                "<br/><br/><b>[趋势利好]</b>: Z-Score 处于上升趋势，财务质量在改善，"
                "可持续跟踪确认趋势延续后考虑加仓"
            )

        return advice

    # ========================= PDF 生成 =========================

    def _build_stock_section(self, symbol: str, df: pd.DataFrame, stock_label: str) -> list:
        """
        构建单只股票的报告内容（故事元素列表）

        Args:
            symbol: 股票代码
            df: matrics 数据
            stock_label: 显示用标签

        Returns:
            list of ReportLab 故事元素
        """
        story = []

        # ---- 生成图表 ----
        logger.info(f"  生成图表...")
        chart1_buf = self._chart_zscore_pd(df, stock_label)
        chart2_buf = self._chart_pd_el(df, stock_label)

        # ---- 股票标题 ----
        stock_title_style = ParagraphStyle(
            'StockTitle', fontName=REPORTLAB_FONT, fontSize=16,
            leading=20, alignment=TA_CENTER, spaceAfter=8,
            textColor=colors.HexColor('#2c3e50'),
        )
        story.append(Paragraph(f"PD 违约概率分析报告 —— {stock_label}", stock_title_style))
        story.append(Spacer(1, 0.2 * cm))

        # ---- 章节1: 数据表格 ----
        section_style = ParagraphStyle(
            'Section', fontName=REPORTLAB_FONT, fontSize=13, leading=17,
            spaceBefore=8, spaceAfter=6, textColor=colors.HexColor('#34495e'),
        )
        story.append(Paragraph('<b>一、核心指标数据表</b>', section_style))
        story.append(Spacer(1, 0.15 * cm))

        data_table = self._build_data_table(df)
        story.append(data_table)
        story.append(Spacer(1, 0.3 * cm))

        # ---- 章节2: 图表1 (Z-Score + PD) ----
        story.append(Paragraph('<b>二、Z-Score 与 PD 违约概率 趋势图</b>', section_style))
        story.append(Spacer(1, 0.1 * cm))
        if chart1_buf:
            img1 = Image(chart1_buf, width=25 * cm, height=11 * cm)
            story.append(img1)
        else:
            story.append(Paragraph('图表生成失败', self._cell_style(10)))
        story.append(Spacer(1, 0.3 * cm))

        # ---- 章节3: 图表2 (PD + EL) ----
        story.append(Paragraph('<b>三、PD 违约概率 与 EL 预期损失 趋势图</b>', section_style))
        story.append(Spacer(1, 0.1 * cm))
        if chart2_buf:
            img2 = Image(chart2_buf, width=25 * cm, height=11 * cm)
            story.append(img2)
        else:
            story.append(Paragraph('图表生成失败', self._cell_style(10)))
        story.append(Spacer(1, 0.3 * cm))

        # ---- 章节4: 专业交易员评论 ----
        story.append(Paragraph('<b>四、交易员深度分析</b>', section_style))
        story.append(Spacer(1, 0.15 * cm))

        commentary_style = ParagraphStyle(
            'Commentary', fontName=REPORTLAB_FONT, fontSize=9, leading=14,
            spaceBefore=4, spaceAfter=6, alignment=TA_JUSTIFY,
        )
        commentary = self._generate_professional_commentary(df, stock_label)
        for para in commentary.strip().split('\n'):
            para = para.strip()
            if para:
                story.append(Paragraph(para, commentary_style))

        return story

    def _build_report_header(self, total_stocks: int, date_range: str = '') -> list:
        """构建合并报告的封面/标题"""
        story = []
        title_style = ParagraphStyle(
            'MainTitle', fontName=REPORTLAB_FONT, fontSize=22,
            leading=28, alignment=TA_CENTER, spaceAfter=12,
            textColor=colors.HexColor('#1a237e'),
        )
        subtitle_style = ParagraphStyle(
            'SubTitle', fontName=REPORTLAB_FONT, fontSize=12,
            leading=16, alignment=TA_CENTER, spaceAfter=6,
            textColor=colors.HexColor('#546e7a'),
        )
        story.append(Spacer(1, 1.5 * cm))
        story.append(Paragraph('股票 PD 违约概率分析综合报告', title_style))
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph(
            f'基于 Altman Z-Score 模型的多维度风险评估',
            subtitle_style
        ))
        story.append(Paragraph(
            f'分析区间: {date_range}  |  共覆盖 {total_stocks} 只股票',
            subtitle_style
        ))
        story.append(Spacer(1, 1.5 * cm))
        story.append(PageBreak())
        return story

    def generate_sector_report(self, stock_list: list, industry: str) -> str:
        """
        对指定行业板块的股票生成一份合并的 PD 分析报告

        Args:
            stock_list: 该板块的股票列表，如 [{'ts_code': '688498.SH', 'name': '源杰科技'}, ...]
            industry: 行业/板块名称，如 '高科技'、'银行'

        Returns:
            str: 生成的 PDF 文件路径，失败返回 None
        """
        logger.info("=" * 80)
        logger.info(f"  板块 PD 分析组合报告生成 开始 (板块: {industry})")
        logger.info(f"  股票数量: {len(stock_list)}")
        logger.info("=" * 80)

        stock_sections = {}
        stock_zscore_data = {}
        stock_pd_data = {}
        stock_ai_data = {}
        no_data_stocks = []
        all_dates = []

        for idx, stock_info in enumerate(stock_list, 1):
            ts_code = stock_info['ts_code']
            name = stock_info['name']
            symbol = ts_code.split('.')[0]

            logger.info(f"\n[{idx}/{len(stock_list)}] 准备 {name} ({symbol}) 数据...")

            self.job_logger.start_job('PDAnalysisReport', symbol,
                                      params={'name': name, 'ts_code': ts_code, 'industry': industry})
            try:
                df = self.fetch_matrics_data(symbol)
                if df.empty:
                    logger.warning(f"  {name} ({symbol}) 无 matrics 数据，跳过")
                    no_data_stocks.append(f"{name} ({symbol})")
                    self.job_logger.end_job_failed('无数据')
                    continue

                stock_name = df['name'].iloc[0] if 'name' in df.columns and pd.notna(df['name'].iloc[0]) else name
                stock_label = f"{stock_name} ({symbol})"

                section = self._build_stock_section(symbol, df, stock_label)
                stock_sections[ts_code] = (stock_label, section)

                stock_zscore_data[stock_label] = (df['date'], df['z_score'])
                stock_pd_data[stock_label] = (df['date'], df['pd'])
                all_dates.extend(df['date'].tolist())

                latest = df.sort_values('date', ascending=False).iloc[0]
                stock_ai_data[stock_label] = {
                    'symbol': symbol,
                    'name': stock_name,
                    'latest_date': df['date'].max(),
                    'pd_latest': latest.get('pd'),
                    'z_latest': latest.get('z_score'),
                    'el_latest': latest.get('el'),
                    'risk_level': latest.get('risk_level', ''),
                }
                logger.info(f"  {stock_label} 报告内容已构建")
                self.job_logger.end_job_success(records_processed=len(df))

            except Exception as e:
                logger.error(f"  {name} ({symbol}) 数据准备失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
                no_data_stocks.append(f"{name} ({symbol})")
                self.job_logger.end_job_failed(str(e), traceback.format_exc())

        if not stock_sections:
            logger.warning(f"板块 {industry} 所有股票均无数据，无法生成报告")
            return None

        # ---- 合并构建 PDF ----
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if all_dates:
            date_start = min(all_dates)
            date_end = max(all_dates)
            date_range = f"{date_start}_{date_end}"
        else:
            date_range = "无数据"

        safe_industry = industry.replace('/', '_').replace('\\', '_').replace(' ', '_')
        pdf_filename = f"PD分析综合报告_{safe_industry}_[{date_range}]_{timestamp}.pdf"
        pdf_path = os.path.join(self.output_dir, pdf_filename)

        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=landscape(A4),
            rightMargin=1 * cm,
            leftMargin=1 * cm,
            topMargin=1 * cm,
            bottomMargin=0.8 * cm,
        )

        full_story = []

        # 封面（带板块名称）
        full_story.extend(self._build_report_header_for_sector(len(stock_sections), industry, date_range))

        # 目录
        toc_style = ParagraphStyle(
            'TOC', fontName=REPORTLAB_FONT, fontSize=18, leading=24,
            spaceBefore=8, spaceAfter=10, textColor=colors.HexColor('#1a237e'),
        )
        toc_item_style = ParagraphStyle(
            'TOCItem', fontName=REPORTLAB_FONT, fontSize=11, leading=18,
            leftIndent=20, spaceBefore=2, spaceAfter=2,
        )
        full_story.append(Paragraph('<b>报告涵盖股票列表</b>', toc_style))
        full_story.append(Spacer(1, 0.2 * cm))

        for idx_i, (ts_code, (stock_label, _)) in enumerate(stock_sections.items(), 1):
            full_story.append(Paragraph(f'{idx_i}. {stock_label}', toc_item_style))

        if no_data_stocks:
            full_story.append(Spacer(1, 0.3 * cm))
            no_data_style = ParagraphStyle(
                'NoData', fontName=REPORTLAB_FONT, fontSize=9, leading=14,
                textColor=colors.HexColor('#e74c3c'), leftIndent=20,
            )
            full_story.append(Paragraph('<b>以下股票无数据，未纳入报告:</b>', no_data_style))
            for s in no_data_stocks:
                full_story.append(Paragraph(f'  - {s}', no_data_style))

        full_story.append(PageBreak())

        # 逐只股票内容
        section_count = len(stock_sections)
        for idx_i, (ts_code, (stock_label, section)) in enumerate(stock_sections.items(), 1):
            logger.info(f"  追加 [{idx_i}/{section_count}] {stock_label} 到板块报告...")
            full_story.extend(section)
            if idx_i < section_count:
                full_story.append(PageBreak())

        # ======================== 综合对比章节 ========================
        comparison_title_style = ParagraphStyle(
            'ComparisonTitle', fontName=REPORTLAB_FONT, fontSize=16,
            leading=22, alignment=TA_CENTER, spaceAfter=10,
            textColor=colors.HexColor('#1a237e'),
        )
        section_style = ParagraphStyle(
            'Section', fontName=REPORTLAB_FONT, fontSize=13, leading=17,
            spaceBefore=8, spaceAfter=6, textColor=colors.HexColor('#34495e'),
        )

        if len(stock_zscore_data) >= 2:
            full_story.append(PageBreak())
            full_story.append(Paragraph(f'<b>{industry}板块  Z-Score 综合对比</b>', comparison_title_style))
            full_story.append(Spacer(1, 0.3 * cm))

            full_story.append(Paragraph('<b>一、Z-Score 横向对比图（全景一览）</b>', section_style))
            full_story.append(Spacer(1, 0.1 * cm))

            comparison_chart = self._chart_zscore_comparison(stock_zscore_data)
            if comparison_chart:
                img_cmp = Image(comparison_chart, width=27 * cm, height=13.5 * cm)
                full_story.append(img_cmp)
            else:
                full_story.append(Paragraph('综合对比图生成失败', self._cell_style(10)))

            full_story.append(Spacer(1, 0.3 * cm))

            full_story.append(Paragraph('<b>二、交易员视角：跨股票 Z-Score 比较解读</b>', section_style))
            full_story.append(Spacer(1, 0.15 * cm))

            commentary_style = ParagraphStyle(
                'ComparisonCommentary', fontName=REPORTLAB_FONT, fontSize=9, leading=14,
                spaceBefore=4, spaceAfter=6, alignment=TA_JUSTIFY,
            )
            comparison_text = self._generate_comparison_commentary(stock_zscore_data)
            for para in comparison_text.split('<br/>'):
                para = para.strip()
                if para:
                    full_story.append(Paragraph(para, commentary_style))

        if len(stock_pd_data) >= 2:
            full_story.append(PageBreak())
            full_story.append(Paragraph(f'<b>{industry}板块  PD 违约概率 综合对比</b>', comparison_title_style))
            full_story.append(Spacer(1, 0.3 * cm))

            full_story.append(Paragraph('<b>一、PD 违约概率 横向对比图（风险全景透视）</b>', section_style))
            full_story.append(Spacer(1, 0.1 * cm))

            pd_chart = self._chart_pd_comparison(stock_pd_data)
            if pd_chart:
                img_pd = Image(pd_chart, width=27 * cm, height=13.5 * cm)
                full_story.append(img_pd)
            else:
                full_story.append(Paragraph('PD 对比图生成失败', self._cell_style(10)))

            full_story.append(Spacer(1, 0.3 * cm))

            full_story.append(Paragraph('<b>二、交易员视角：跨股票 PD 违约概率 比较解读</b>', section_style))
            full_story.append(Spacer(1, 0.15 * cm))

            pd_commentary_style = ParagraphStyle(
                'PDCommentary', fontName=REPORTLAB_FONT, fontSize=9, leading=14,
                spaceBefore=4, spaceAfter=6, alignment=TA_JUSTIFY,
            )
            pd_text = self._generate_pd_comparison_commentary(stock_pd_data)
            for para in pd_text.split('<br/>'):
                para = para.strip()
                if para:
                    full_story.append(Paragraph(para, pd_commentary_style))

        # ======================== PD 违约概率热力图 ========================
        if len(stock_pd_data) >= 2:
            full_story.append(PageBreak())
            full_story.append(Paragraph(f'<b>{industry}板块  PD 违约概率热力图</b>', comparison_title_style))
            full_story.append(Spacer(1, 0.3 * cm))

            # 板块报告内所有股票行业相同
            pd_stock_industry_map = {lb: industry for lb in stock_pd_data}
            pd_heatmap_table = self._build_pd_heatmap(stock_pd_data, all_dates, pd_stock_industry_map)
            if pd_heatmap_table:
                full_story.append(pd_heatmap_table)
                full_story.append(Spacer(1, 0.3 * cm))
                full_story.append(Paragraph(
                    '<i>热力图说明：绿色 = 低违约风险 (PD&lt;2%)，黄色 = 中违约风险 (2%≤PD&lt;10%)，红色 = 高违约风险 (PD≥10%)；'
                    '颜色越深表示风险程度越极端</i>',
                    ParagraphStyle('PDHeatmapNote', fontName=REPORTLAB_FONT, fontSize=7, leading=10,
                                   textColor=colors.HexColor('#95a5a6'), alignment=TA_CENTER)
                ))
            else:
                full_story.append(Paragraph('PD 热力图生成失败', self._cell_style(10)))

        # ======================== Z-Score 风险热力图 ========================
        if len(stock_zscore_data) >= 2:
            full_story.append(PageBreak())
            full_story.append(Paragraph(f'<b>{industry}板块  Z-Score 风险热力图</b>', comparison_title_style))
            full_story.append(Spacer(1, 0.3 * cm))

            # 板块报告内所有股票行业相同
            stock_industry_map = {lb: industry for lb in stock_zscore_data}
            heatmap_table = self._build_zscore_heatmap(stock_zscore_data, all_dates, stock_industry_map)
            if heatmap_table:
                full_story.append(heatmap_table)
                full_story.append(Spacer(1, 0.3 * cm))
                full_story.append(Paragraph(
                    '<i>热力图说明：绿色 = 安全区 (Z≥3.0)，黄色 = 灰色区 (1.8≤Z&lt;3.0)，红色 = 危机区 (Z&lt;1.8)；'
                    '颜色越深表示风险程度越极端</i>',
                    ParagraphStyle('HeatmapNote', fontName=REPORTLAB_FONT, fontSize=7, leading=10,
                                   textColor=colors.HexColor('#95a5a6'), alignment=TA_CENTER)
                ))
            else:
                full_story.append(Paragraph('热力图生成失败', self._cell_style(10)))

        if len(stock_ai_data) >= 1:
            full_story.append(PageBreak())
            full_story.append(Paragraph(f'<b>{industry}板块  AI 交易员 综合评估</b>', comparison_title_style))
            full_story.append(Spacer(1, 0.3 * cm))

            full_story.append(Paragraph(
                '<b>以下为 AI 基于 PD / Z-Score / EL 数据自动生成的投资组合综合评估</b>',
                section_style
            ))
            full_story.append(Spacer(1, 0.15 * cm))

            ai_style = ParagraphStyle(
                'AICommentary', fontName=REPORTLAB_FONT, fontSize=9, leading=14,
                spaceBefore=4, spaceAfter=6, alignment=TA_JUSTIFY,
                textColor=colors.HexColor('#1a237e'),
            )
            ai_report = self._generate_ai_pd_analysis(stock_ai_data)
            ai_report_html = ai_report.replace('\n', '<br/>')
            full_story.append(Paragraph(ai_report_html, ai_style))

            full_story.append(Spacer(1, 0.3 * cm))
            full_story.append(Paragraph(
                '<i>（以上内容由 ZhipuGLM4 大模型自动生成，仅供参考，不构成投资建议）</i>',
                ParagraphStyle('AIDisclaimer', fontName=REPORTLAB_FONT, fontSize=7, leading=10,
                               textColor=colors.HexColor('#95a5a6'), alignment=TA_CENTER)
            ))

        # 附录: 免责声明
        footer_style = ParagraphStyle(
            'Footer', fontName=REPORTLAB_FONT, fontSize=7, leading=9,
            textColor=colors.HexColor('#95a5a6'), alignment=TA_CENTER,
        )
        full_story.append(Spacer(1, 0.5 * cm))
        full_story.append(Paragraph(
            '免责声明: 本报告基于 Altman Z-Score 模型自动生成，仅供研究参考，不构成投资建议。'
            f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            footer_style
        ))

        doc.build(full_story)

        logger.info("\n" + "=" * 80)
        logger.info(f"  板块 [{industry}] PD 分析报告 生成完成")
        logger.info(f"  分析日期范围: {date_range}")
        logger.info(f"  涵盖股票: {len(stock_sections)} 只")
        logger.info(f"  无数据股票: {len(no_data_stocks)} 只")
        logger.info(f"  PDF 路径: {pdf_path}")
        logger.info("=" * 80)

        return pdf_path

    def _build_report_header_for_sector(self, total_stocks: int, industry: str, date_range: str = '') -> list:
        """构建板块报告的封面/标题"""
        story = []
        title_style = ParagraphStyle(
            'MainTitle', fontName=REPORTLAB_FONT, fontSize=22,
            leading=28, alignment=TA_CENTER, spaceAfter=12,
            textColor=colors.HexColor('#1a237e'),
        )
        subtitle_style = ParagraphStyle(
            'SubTitle', fontName=REPORTLAB_FONT, fontSize=12,
            leading=16, alignment=TA_CENTER, spaceAfter=6,
            textColor=colors.HexColor('#546e7a'),
        )
        story.append(Spacer(1, 1.5 * cm))
        story.append(Paragraph(f'{industry}板块  股票 PD 违约概率分析报告', title_style))
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph(
            f'基于 Altman Z-Score 模型的多维度风险评估',
            subtitle_style
        ))
        story.append(Paragraph(
            f'分析区间: {date_range}  |  板块: {industry}  |  共覆盖 {total_stocks} 只股票',
            subtitle_style
        ))
        story.append(Spacer(1, 1.5 * cm))
        story.append(PageBreak())
        return story

    def generate_single_stock_report(self, symbol: str) -> str:
        """
        生成单只股票的 PD 分析 PDF 报告

        Args:
            symbol: 股票代码

        Returns:
            生成的 PDF 文件路径，失败返回 None
        """
        logger.info(f"=" * 60)
        logger.info(f"  生成 PD 分析报告: symbol={symbol}")
        logger.info(f"=" * 60)

        # 1. 获取数据
        df = self.fetch_matrics_data(symbol)
        if df.empty:
            logger.warning(f"symbol={symbol} 无 matrics 数据，跳过报告生成")
            return None

        stock_name = df['name'].iloc[0] if 'name' in df.columns and pd.notna(df['name'].iloc[0]) else symbol
        stock_label = f"{stock_name} ({symbol})"

        # 2. 构建内容
        story = self._build_stock_section(symbol, df, stock_label)

        # ---- 附录: 免责声明 ----
        footer_style = ParagraphStyle(
            'Footer', fontName=REPORTLAB_FONT, fontSize=7, leading=9,
            textColor=colors.HexColor('#95a5a6'), alignment=TA_CENTER,
        )
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(
            '免责声明: 本报告基于 Altman Z-Score 模型自动生成，仅供研究参考，不构成投资建议。'
            f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            footer_style
        ))

        # 3. 构建 PDF
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = stock_name.replace('*', '').replace('/', '_').replace('\\', '_')
        date_start = df['date'].min()
        date_end = df['date'].max()
        pdf_filename = f"PD分析报告_{safe_name}_{symbol}_[{date_start}_{date_end}]_{timestamp}.pdf"
        pdf_path = os.path.join(self.output_dir, pdf_filename)

        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=landscape(A4),
            rightMargin=1 * cm,
            leftMargin=1 * cm,
            topMargin=1 * cm,
            bottomMargin=0.8 * cm,
        )
        doc.build(story)
        logger.info(f"✅ PDF 报告已生成: {pdf_path}")
        return pdf_path

    # ========================= 批量生成（合并到一个PDF）=========================

    def generate_all_stocks_report(self) -> str:
        """
        对 CommonDataParameters.STOCK_LIST 中所有股票生成一份合并的 PD 分析报告

        Returns:
            str: 生成的 PDF 文件路径，失败返回 None
        """
        logger.info("=" * 80)
        logger.info("  批量 PD 分析组合报告生成 开始 (合并到一个PDF)")
        logger.info(f"  股票数量: {len(CommonDataParameters.STOCK_LIST)}")
        logger.info("=" * 80)

        # 先提前获取所有股票数据，确认哪些有数据
        stock_sections = {}  # ts_code -> (stock_label, story_elements)
        stock_zscore_data = {}  # stock_label -> (date_series, z_score_series)
        stock_pd_data = {}  # stock_label -> (date_series, pd_series)
        stock_ai_data = {}  # stock_label -> {symbol, name, latest_date, pd_latest, z_latest, el_latest, risk_level}
        no_data_stocks = []
        all_dates = []  # 收集所有股票的日期，用于计算分析范围
        stock_industry_map = {}  # stock_label -> industry

        for idx, stock_info in enumerate(CommonDataParameters.STOCK_LIST, 1):
            ts_code = stock_info['ts_code']
            name = stock_info['name']
            symbol = ts_code.split('.')[0]

            logger.info(f"\n[{idx}/{len(CommonDataParameters.STOCK_LIST)}] 准备 {name} ({symbol}) 数据...")

            self.job_logger.start_job('PDAnalysisReport', symbol,
                                      params={'name': name, 'ts_code': ts_code})
            try:
                df = self.fetch_matrics_data(symbol)
                if df.empty:
                    logger.warning(f"  {name} ({symbol}) 无 matrics 数据，跳过")
                    no_data_stocks.append(f"{name} ({symbol})")
                    self.job_logger.end_job_failed('无数据')
                    continue

                stock_name = df['name'].iloc[0] if 'name' in df.columns and pd.notna(df['name'].iloc[0]) else name
                stock_label = f"{stock_name} ({symbol})"

                # 构建该股票的故事元素
                section = self._build_stock_section(symbol, df, stock_label)
                stock_sections[ts_code] = (stock_label, section)

                # 收集 Z-Score 时间序列（用于综合对比图）
                stock_zscore_data[stock_label] = (df['date'], df['z_score'])
                # 收集 PD 时间序列（用于 PD 对比图）
                stock_pd_data[stock_label] = (df['date'], df['pd'])
                all_dates.extend(df['date'].tolist())  # 收集日期范围

                # 记录板块信息（优先从 df 中取，回退到 STOCK_LIST）
                df_industry = df['industry'].iloc[0] if 'industry' in df.columns and pd.notna(df['industry'].iloc[0]) else stock_info.get('industry', '未知')
                stock_industry_map[stock_label] = df_industry

                # 收集 AI 分析所需的数据
                latest = df.sort_values('date', ascending=False).iloc[0]
                stock_ai_data[stock_label] = {
                    'symbol': symbol,
                    'name': stock_name,
                    'latest_date': df['date'].max(),
                    'pd_latest': latest.get('pd'),
                    'z_latest': latest.get('z_score'),
                    'el_latest': latest.get('el'),
                    'risk_level': latest.get('risk_level', ''),
                }
                logger.info(f"  {stock_label} 报告内容已构建")
                self.job_logger.end_job_success(records_processed=len(df))

            except Exception as e:
                logger.error(f"  {name} ({symbol}) 数据准备失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
                no_data_stocks.append(f"{name} ({symbol})")
                self.job_logger.end_job_failed(str(e), traceback.format_exc())

        if not stock_sections:
            logger.warning("所有股票均无数据，无法生成报告")
            return None

        # ---- 合并构建一个 PDF ----
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 计算分析日期范围
        if all_dates:
            date_start = min(all_dates)
            date_end = max(all_dates)
            date_range = f"{date_start}_{date_end}"
        else:
            date_range = "无数据"

        pdf_filename = f"PD分析综合报告_ALL_[{date_range}]_{timestamp}.pdf"
        pdf_path = os.path.join(self.output_dir, pdf_filename)

        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=landscape(A4),
            rightMargin=1 * cm,
            leftMargin=1 * cm,
            topMargin=1 * cm,
            bottomMargin=0.8 * cm,
        )

        # 构建完整故事
        full_story = []

        # 封面
        full_story.extend(self._build_report_header(len(stock_sections), date_range))

        # 目录列表（所有成功分析股票）
        toc_style = ParagraphStyle(
            'TOC', fontName=REPORTLAB_FONT, fontSize=18, leading=24,
            spaceBefore=8, spaceAfter=10, textColor=colors.HexColor('#1a237e'),
        )
        toc_item_style = ParagraphStyle(
            'TOCItem', fontName=REPORTLAB_FONT, fontSize=11, leading=18,
            leftIndent=20, spaceBefore=2, spaceAfter=2,
        )
        full_story.append(Paragraph('<b>报告涵盖股票列表</b>', toc_style))
        full_story.append(Spacer(1, 0.2 * cm))

        for idx, (ts_code, (stock_label, _)) in enumerate(stock_sections.items(), 1):
            full_story.append(Paragraph(f'{idx}. {stock_label}', toc_item_style))

        if no_data_stocks:
            full_story.append(Spacer(1, 0.3 * cm))
            no_data_style = ParagraphStyle(
                'NoData', fontName=REPORTLAB_FONT, fontSize=9, leading=14,
                textColor=colors.HexColor('#e74c3c'), leftIndent=20,
            )
            full_story.append(Paragraph('<b>以下股票无数据，未纳入报告:</b>', no_data_style))
            for s in no_data_stocks:
                full_story.append(Paragraph(f'  - {s}', no_data_style))

        full_story.append(PageBreak())

        # 逐只股票内容，用 PageBreak 分隔
        section_count = len(stock_sections)
        for idx, (ts_code, (stock_label, section)) in enumerate(stock_sections.items(), 1):
            logger.info(f"  追加 [{idx}/{section_count}] {stock_label} 到合并报告...")
            full_story.extend(section)

            # 最后一只股票不加分页符
            if idx < section_count:
                full_story.append(PageBreak())

        # ======================== 综合对比章节 ========================
        comparison_title_style = ParagraphStyle(
            'ComparisonTitle', fontName=REPORTLAB_FONT, fontSize=16,
            leading=22, alignment=TA_CENTER, spaceAfter=10,
            textColor=colors.HexColor('#1a237e'),
        )
        section_style = ParagraphStyle(
            'Section', fontName=REPORTLAB_FONT, fontSize=13, leading=17,
            spaceBefore=8, spaceAfter=6, textColor=colors.HexColor('#34495e'),
        )

        if len(stock_zscore_data) >= 2:
            full_story.append(PageBreak())

            full_story.append(Paragraph('<b>全股票 Z-Score 综合对比</b>', comparison_title_style))
            full_story.append(Spacer(1, 0.3 * cm))

            # 综合对比图表
            full_story.append(Paragraph('<b>一、Z-Score 横向对比图（全景一览）</b>', section_style))
            full_story.append(Spacer(1, 0.1 * cm))

            comparison_chart = self._chart_zscore_comparison(stock_zscore_data)
            if comparison_chart:
                img_cmp = Image(comparison_chart, width=27 * cm, height=13.5 * cm)
                full_story.append(img_cmp)
            else:
                full_story.append(Paragraph('综合对比图生成失败', self._cell_style(10)))

            full_story.append(Spacer(1, 0.3 * cm))

            # 交易员比较解读
            full_story.append(Paragraph('<b>二、交易员视角：跨股票 Z-Score 比较解读</b>', section_style))
            full_story.append(Spacer(1, 0.15 * cm))

            commentary_style = ParagraphStyle(
                'ComparisonCommentary', fontName=REPORTLAB_FONT, fontSize=9, leading=14,
                spaceBefore=4, spaceAfter=6, alignment=TA_JUSTIFY,
            )
            comparison_text = self._generate_comparison_commentary(stock_zscore_data)
            for para in comparison_text.split('<br/>'):
                para = para.strip()
                if para:
                    full_story.append(Paragraph(para, commentary_style))

        # ======================== PD 综合对比章节 ========================
        if len(stock_pd_data) >= 2:
            full_story.append(PageBreak())

            # PD 对比图表
            full_story.append(Paragraph('<b>全股票 PD 违约概率 综合对比</b>', comparison_title_style))
            full_story.append(Spacer(1, 0.3 * cm))

            full_story.append(Paragraph('<b>一、PD 违约概率 横向对比图（风险全景透视）</b>', section_style))
            full_story.append(Spacer(1, 0.1 * cm))

            pd_chart = self._chart_pd_comparison(stock_pd_data)
            if pd_chart:
                img_pd = Image(pd_chart, width=27 * cm, height=13.5 * cm)
                full_story.append(img_pd)
            else:
                full_story.append(Paragraph('PD 对比图生成失败', self._cell_style(10)))

            full_story.append(Spacer(1, 0.3 * cm))

            # PD 交易员解读
            full_story.append(Paragraph('<b>二、交易员视角：跨股票 PD 违约概率 比较解读</b>', section_style))
            full_story.append(Spacer(1, 0.15 * cm))

            pd_commentary_style = ParagraphStyle(
                'PDCommentary', fontName=REPORTLAB_FONT, fontSize=9, leading=14,
                spaceBefore=4, spaceAfter=6, alignment=TA_JUSTIFY,
            )
            pd_text = self._generate_pd_comparison_commentary(stock_pd_data)
            for para in pd_text.split('<br/>'):
                para = para.strip()
                if para:
                    full_story.append(Paragraph(para, pd_commentary_style))

        # ======================== PD 违约概率热力图 ========================
        if len(stock_pd_data) >= 2:
            full_story.append(PageBreak())
            full_story.append(Paragraph('<b>PD 违约概率热力图（全股票 × 全日期）</b>', comparison_title_style))
            full_story.append(Spacer(1, 0.3 * cm))

            pd_heatmap_table = self._build_pd_heatmap(stock_pd_data, all_dates, stock_industry_map)
            if pd_heatmap_table:
                full_story.append(pd_heatmap_table)
                full_story.append(Spacer(1, 0.3 * cm))
                full_story.append(Paragraph(
                    '<i>热力图说明：绿色 = 低违约风险 (PD&lt;2%)，黄色 = 中违约风险 (2%≤PD&lt;10%)，红色 = 高违约风险 (PD≥10%)；'
                    '颜色越深表示风险程度越极端</i>',
                    ParagraphStyle('PDHeatmapNote', fontName=REPORTLAB_FONT, fontSize=7, leading=10,
                                   textColor=colors.HexColor('#95a5a6'), alignment=TA_CENTER)
                ))
            else:
                full_story.append(Paragraph('PD 热力图生成失败', self._cell_style(10)))

        # ======================== Z-Score 风险热力图 ========================
        if len(stock_zscore_data) >= 2:
            full_story.append(PageBreak())
            full_story.append(Paragraph('<b>Z-Score 风险热力图（全股票 × 全日期）</b>', comparison_title_style))
            full_story.append(Spacer(1, 0.3 * cm))

            heatmap_table = self._build_zscore_heatmap(stock_zscore_data, all_dates, stock_industry_map)
            if heatmap_table:
                full_story.append(heatmap_table)
                full_story.append(Spacer(1, 0.3 * cm))
                full_story.append(Paragraph(
                    '<i>热力图说明：绿色 = 安全区 (Z≥3.0)，黄色 = 灰色区 (1.8≤Z&lt;3.0)，红色 = 危机区 (Z&lt;1.8)；'
                    '颜色越深表示风险程度越极端</i>',
                    ParagraphStyle('HeatmapNote', fontName=REPORTLAB_FONT, fontSize=7, leading=10,
                                   textColor=colors.HexColor('#95a5a6'), alignment=TA_CENTER)
                ))
            else:
                full_story.append(Paragraph('热力图生成失败', self._cell_style(10)))

        # ======================== AI 综合评估章节 ========================
        if len(stock_ai_data) >= 1:
            full_story.append(PageBreak())
            full_story.append(Paragraph('<b>AI 交易员 综合评估</b>', comparison_title_style))
            full_story.append(Spacer(1, 0.3 * cm))

            full_story.append(Paragraph(
                '<b>以下为 AI 基于 PD / Z-Score / EL 数据自动生成的投资组合综合评估</b>',
                section_style
            ))
            full_story.append(Spacer(1, 0.15 * cm))

            ai_style = ParagraphStyle(
                'AICommentary', fontName=REPORTLAB_FONT, fontSize=9, leading=14,
                spaceBefore=4, spaceAfter=6, alignment=TA_JUSTIFY,
                textColor=colors.HexColor('#1a237e'),
            )
            ai_report = self._generate_ai_pd_analysis(stock_ai_data)
            # AI 输出中的换行符转为 <br/> 以便 ReportLab 正确渲染
            ai_report_html = ai_report.replace('\n', '<br/>')
            full_story.append(Paragraph(ai_report_html, ai_style))

            full_story.append(Spacer(1, 0.3 * cm))
            full_story.append(Paragraph(
                '<i>（以上内容由 ZhipuGLM4 大模型自动生成，仅供参考，不构成投资建议）</i>',
                ParagraphStyle('AIDisclaimer', fontName=REPORTLAB_FONT, fontSize=7, leading=10,
                               textColor=colors.HexColor('#95a5a6'), alignment=TA_CENTER)
            ))

        # 附录: 免责声明
        footer_style = ParagraphStyle(
            'Footer', fontName=REPORTLAB_FONT, fontSize=7, leading=9,
            textColor=colors.HexColor('#95a5a6'), alignment=TA_CENTER,
        )
        full_story.append(Spacer(1, 0.5 * cm))
        full_story.append(Paragraph(
            '免责声明: 本报告基于 Altman Z-Score 模型自动生成，仅供研究参考，不构成投资建议。'
            f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            footer_style
        ))

        # 构建
        doc.build(full_story)

        logger.info("\n" + "=" * 80)
        logger.info(f"  合并 PD 分析报告 生成完成")
        logger.info(f"  分析日期范围: {date_range}")
        logger.info(f"  涵盖股票: {len(stock_sections)} 只")
        logger.info(f"  无数据股票: {len(no_data_stocks)} 只")
        logger.info(f"  PDF 路径: {pdf_path}")
        logger.info("=" * 80)

        return pdf_path


if __name__ == "__main__":
    report = PDAnalysisReport()

    # ---- 模式选择 ----

    # 模式1: 单只股票报告
    # report.generate_single_stock_report(symbol='002093')

    # 模式2: 批量生成所有股票报告
    report.generate_all_stocks_report()

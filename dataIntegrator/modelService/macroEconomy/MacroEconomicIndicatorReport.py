"""
宏观经济指标 报告生成器

流程：
1. 从 tb_macro_economic_indicator 拉取数据
2. 数据清洗（缺失值/0值前向填充）
3. 生成13张图表（不保存PNG，直接嵌入PDF）
4. 专业分析师文字描述
5. ZhipuGLM4 AI 分析（年底数据全景）
6. 生成 PDF 报告（reportlab 风格，参照 CMLAnalysisReport）
"""

import io
import os
import textwrap
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.outliers_influence import variance_inflation_factor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
                                 PageBreak)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.common.ReportJobLogger import ReportJobLogger
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.LLMSuport.AiAgents.ZhipuGLM4 import ZhipuGLM4

logger = CommonLib.logger

# 中文字体支持（matplotlib）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class MacroEconomicIndicatorReport:
    """宏观经济指标 报告生成器"""

    #REPORT_DIR = r"D:\workspace_python\infinity_data\outbound\report\MacroEconomy"
    REPORT_DIR = os.path.join(CommonParameters.reportPath, 'MacroEconomy')

    # 所有 _pct 字段
    ALL_PCT_FIELDS = [
        'shibor_3m_eom_pct', 'lpr_5y_eom_pct', 'ust_y10_eom_pct',
        'shibor_on_pct', 'shibor_1w_pct', 'shibor_1m_pct', 'shibor_1y_pct',
        'lpr_1y_pct',
        'ust_y2_pct', 'ust_y30_pct',
        'm1_yoy_pct', 'm2_yoy_pct', 'cpi_yoy_pct',
        'ppi_yoy_pct', 'pmi030000_pct',
        'forex_reserves_pct', 'gold_reserves_pct',
        'exports_yoy_pct', 'imports_yoy_pct',
        'total_shrzgm_pct', 'rmb_loan_pct', 'entrusted_loan_pct',
        'trust_loan_pct', 'corporate_bonds_pct', 'equity_financing_pct',
        'usdcnh_bid_close_pct', 'usdcnh_ask_close_pct',
        'cn_yield_2y_pct', 'cn_yield_5y_pct', 'cn_yield_10y_pct',
        'gdp_yoy_pct', 'gdp_pi_yoy_pct', 'gdp_si_yoy_pct', 'gdp_ti_yoy_pct',
        'usdx_index_pct', 'gold_close_pct', 'dji_close_pct',
        'sh_close_pct', 'sz_close_pct',
        'hsi_close_pct', 'twii_close_pct', 'ks11_close_pct', 'n225_close_pct',
        'vix_close_pct',
    ]

    ALL_RAW_FIELDS = [
        'shibor_3m_eom', 'lpr_5y_eom', 'ust_y10_eom',
        'shibor_on', 'shibor_1w', 'shibor_1m', 'shibor_1y',
        'lpr_1y',
        'ust_y2', 'ust_y30',
        'm1_yoy', 'm2_yoy', 'cpi_yoy',
        'ppi_yoy', 'pmi030000',
        'forex_reserves', 'gold_reserves',
        'exports_yoy', 'imports_yoy',
        'total_shrzgm', 'rmb_loan', 'entrusted_loan',
        'trust_loan', 'corporate_bonds', 'equity_financing',
        'usdcnh_bid_close', 'usdcnh_ask_close',
        'cn_yield_2y', 'cn_yield_5y', 'cn_yield_10y',
        'gdp_yoy', 'gdp_pi_yoy', 'gdp_si_yoy', 'gdp_ti_yoy',
        'usdx_index', 'gold_close', 'dji_close', 'sh_close', 'sz_close',
        'hsi_close', 'twii_close', 'ks11_close', 'n225_close',
        'vix_close',
    ]

    FIELD_CN_NAMES = {
        'shibor_3m_eom': 'SHIBOR 3M', 'lpr_5y_eom': 'LPR 5Y',
        'ust_y10_eom': '美国10Y国债',
        'shibor_on': 'SHIBOR O/N', 'shibor_1w': 'SHIBOR 1W',
        'shibor_1m': 'SHIBOR 1M', 'shibor_1y': 'SHIBOR 1Y',
        'lpr_1y': 'LPR 1Y',
        'ust_y2': '美国2Y国债', 'ust_y30': '美国30Y国债',
        'm1_yoy': 'M1同比', 'm2_yoy': 'M2同比',
        'cpi_yoy': 'CPI同比', 'ppi_yoy': 'PPI同比', 'pmi030000': '综合PMI',
        'forex_reserves': '外汇储备(亿美元)',
        'gold_reserves': '黄金储备(万盎司)', 'exports_yoy': '出口同比',
        'imports_yoy': '进口同比', 'total_shrzgm': '社会融资规模(亿)',
        'rmb_loan': '人民币贷款(亿)', 'entrusted_loan': '委托贷款(亿)',
        'trust_loan': '信托贷款(亿)', 'corporate_bonds': '企业债券(亿)',
        'equity_financing': '股权融资(亿)', 'usdcnh_bid_close': 'USDCNH买入价',
        'usdcnh_ask_close': 'USDCNH卖出价', 'cn_yield_2y': '国债2Y收益率',
        'cn_yield_5y': '国债5Y收益率', 'cn_yield_10y': '国债10Y收益率',
        'gdp_yoy': 'GDP同比',
        'gdp_pi_yoy': 'GDP第一产业同比', 'gdp_si_yoy': 'GDP第二产业同比',
        'gdp_ti_yoy': 'GDP第三产业同比',
        'usdx_index': '美元指数', 'gold_close': '黄金期货GC',
        'dji_close': '道琼斯工业', 'sh_close': '上证综指', 'sz_close': '深证成指',
        'shibor_on_pct': 'SHIBOR O/N环比', 'shibor_1w_pct': 'SHIBOR 1W环比',
        'shibor_1m_pct': 'SHIBOR 1M环比', 'shibor_1y_pct': 'SHIBOR 1Y环比',
        'lpr_1y_pct': 'LPR 1Y环比',
        'ust_y2_pct': '美国2Y国债环比', 'ust_y30_pct': '美国30Y国债环比',
        'ppi_yoy_pct': 'PPI环比', 'pmi030000_pct': '综合PMI环比',
        'usdx_index_pct': '美元指数环比', 'gold_close_pct': '黄金GC环比',
        'dji_close_pct': '道琼斯环比', 'sh_close_pct': '上证综指环比', 'sz_close_pct': '深证成指环比',
        'hsi_close': '恒生指数', 'twii_close': '台湾加权', 'ks11_close': '韩国综合', 'n225_close': '日经225',
        'hsi_close_pct': '恒生指数环比', 'twii_close_pct': '台湾加权环比', 'ks11_close_pct': '韩国综合环比', 'n225_close_pct': '日经225环比',
        'gdp_pi_yoy_pct': 'GDP第一产业环比', 'gdp_si_yoy_pct': 'GDP第二产业环比',
        'gdp_ti_yoy_pct': 'GDP第三产业环比',
        'vix_close': 'VIX恐慌指数', 'vix_close_pct': 'VIX环比',
    }

    CHART_COLORS = [
        '#e74c3c', '#3498db', '#2ecc71', '#9b59b6', '#f39c12',
        '#1abc9c', '#e67e22', '#2980b9', '#c0392b', '#27ae60',
        '#8e44ad', '#d35400', '#16a085', '#2c3e50', '#7f8c8d',
        '#f1c40f', '#00bcd4', '#ff5722', '#795548', '#607d8b',
        '#4caf50', '#ff9800',
    ]

    def __init__(self):
        self.job_logger = ReportJobLogger()
        os.makedirs(self.REPORT_DIR, exist_ok=True)
        self.reportlab_font = self._register_chinese_font()

    def _register_chinese_font(self):
        """注册 reportlab 中文字体（参照 CMLAnalysisReport）"""
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
                    logger.info(f"✅ ReportLab 加载中文字体: {font_name}")
                    break
                except Exception as e:
                    logger.warning(f"⚠️ 字体加载失败 {font_path}: {e}")
        if reportlab_font == 'Helvetica':
            logger.warning("⚠️ ReportLab 未找到中文字体，PDF中文可能无法正常显示")
        return reportlab_font

    def writeLogInfo(self, className="unknown", functionName="unknown", event="unknown"):
        print("%s.%s: %s" % (className, functionName, event))
        logger.info("%s.%s: %s" % (className, functionName, event))

    # ===================== 数据获取与清洗 =====================

    def fetch_data(self):
        """从 ClickHouse 拉取 tb_macro_economic_indicator 表数据"""
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName="fetch_data",
                          event="Fetching data from tb_macro_economic_indicator")
        sql = "SELECT * FROM indexsysdb.tb_macro_economic_indicator ORDER BY trade_month"
        df = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        logger.info(f"Fetched {len(df)} rows, {len(df.columns)} columns")
        return df

    def clean_data(self, df):
        """数据清洗：按 trade_month 排序，缺失值/0值前向填充"""
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName="clean_data",
                          event="Cleaning data (forward fill missing/zero)")

        df = df.sort_values('trade_month').reset_index(drop=True)
        df['trade_month_str'] = df['trade_month'].astype(str)
        df['trade_date_dt'] = pd.to_datetime(
            df['trade_month_str'].str[:4] + '-' + df['trade_month_str'].str[4:6] + '-01',
            errors='coerce'
        )
        key_cols = ['trade_year', 'trade_month', 'last_trade_date', 'trade_month_str', 'trade_date_dt']
        data_cols = [c for c in df.columns if c not in key_cols]

        zero_count = 0
        for col in data_cols:
            col_zero = (df[col] == 0).sum()
            if col_zero > 0:
                zero_count += col_zero
                df[col] = df[col].replace(0, np.nan)
            df[col] = df[col].ffill()

        logger.info(f"Forward fill: {zero_count} zero values filled")
        return df

    # ===================== 图表通用工具 =====================

    def _make_trade_month_labels(self, df, every_n=6):
        """生成 trade_month 标签（每 N 个月显示一个）"""
        labels = []
        for i, row in df.iterrows():
            tm = str(int(row['trade_month']))
            month_str = tm[4:6] if len(tm) >= 6 else tm
            year_str = tm[:4] if len(tm) >= 4 else ''
            if i % every_n == 0 or month_str == '01':
                labels.append(year_str + '-' + month_str)
            else:
                labels.append('')
        return labels

    def _fig_to_bytesio(self, fig, dpi=180):
        """matplotlib figure → BytesIO（不保存磁盘）"""
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        return buf

    def _set_chart_style(self, ax, x_vals, labels, ylabel='数值', xlabel='月份'):
        """统一图表样式：参照 Visualizer.py 细线折线图风格"""
        ax.axhline(y=0, color='gray', linewidth=0.5, linestyle='-')
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_xlabel(xlabel, fontsize=11)
        step = 6
        ax.set_xticks(range(0, len(x_vals), step))
        ax.set_xticklabels(
            [labels[i] if i < len(labels) else '' for i in range(0, len(x_vals), step)]
        )
        ax.tick_params(axis='x', labelsize=7)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        ax.grid(True, alpha=0.3, linestyle='--')

    def _build_legend(self, ax, n_items, ncol_max=6):
        """统一图例（居中下方）"""
        ncol = min(n_items, ncol_max)
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.12),
                  fontsize=7, ncol=ncol, frameon=True, borderaxespad=0.5,
                  handlelength=1.2)

    def _annotate_outliers(self, ax, vals, ymin, ymax, color):
        """标注超出 Y 轴范围的数值"""
        span = abs(ymax - ymin)
        for i, val in enumerate(vals):
            if np.isnan(val):
                continue
            if val > ymax:
                ax.annotate(f'{val * 100:.1f}%',
                            (i, ymax - span * 0.01),
                            textcoords="offset points", xytext=(0, 8),
                            ha='center', va='bottom', fontsize=4.5,
                            color=color, fontweight='bold', rotation=45)
            elif val < ymin:
                ax.annotate(f'{val * 100:.1f}%',
                            (i, ymin + span * 0.01),
                            textcoords="offset points", xytext=(0, -10),
                            ha='center', va='top', fontsize=4.5,
                            color=color, fontweight='bold', rotation=45)

    def _draw_line_chart(self, df, field_map, title, figsize, y_limit=None, ylabel='数值'):
        """通用折线图：返回 BytesIO

        field_map: {column: display_label}
        y_limit: (ymin, ymax) or None
        """
        fig, ax = plt.subplots(figsize=figsize)
        fig.suptitle(title, fontsize=14, fontweight='bold', color='#1a1a2e')

        x = range(len(df))
        labels = self._make_trade_month_labels(df)

        # 筛出有效字段
        valid = []
        for col, display_name in field_map.items():
            if col in df.columns and df[col].notna().sum() > 1:
                valid.append((col, display_name))
        if not valid:
            logger.warning(f"No valid fields for: {title}")
            plt.close(fig)
            return None

        # 参照 Visualizer：细线 alpha=0.75~0.85
        n_items = len(valid)
        linewidth = 0.7 if n_items > 6 else 0.9

        for idx, (col, label) in enumerate(valid):
            color = self.CHART_COLORS[idx % len(self.CHART_COLORS)]
            vals = df[col].values
            ax.plot(x, vals, color=color, linewidth=linewidth, alpha=0.78, label=label)

            if y_limit is not None:
                self._annotate_outliers(ax, vals, y_limit[0], y_limit[1], color)

        self._set_chart_style(ax, range(len(df)), labels, ylabel=ylabel)
        self._build_legend(ax, n_items)

        if y_limit is not None:
            ax.set_ylim(*y_limit)

        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    # ===================== 13 张图表 =====================

    def gen_chart1_all_pct(self, df):
        """图1：所有PCT字段，不限制上下界"""
        title = '图1：宏观经济指标环比增幅全景（全部PCT字段）'
        field_map = {f: f.replace('_pct', '').replace('_', ' ').title()
                     for f in self.ALL_PCT_FIELDS}
        return self._draw_line_chart(df, field_map, title, figsize=(22, 11), ylabel='环比增幅')

    def gen_chart2_money_raw(self, df):
        """图2：m1_yoy, m2_yoy, cpi_yoy, ppi_yoy, pmi030000（绝对值）"""
        title = '图2：货币供应量 M1/M2 与 CPI/PPI/PMI 同比（原始值）'
        return self._draw_line_chart(df, {
            'm1_yoy': 'M1同比(%)',
            'm2_yoy': 'M2同比(%)',
            'cpi_yoy': 'CPI同比(%)',
            'ppi_yoy': 'PPI同比(%)',
            'pmi030000': '综合PMI',
        }, title, figsize=(14, 6), ylabel='同比(%)')

    def gen_chart3_money_pct(self, df):
        """图3：m1_yoy_pct, m2_yoy_pct, cpi_yoy_pct, ppi_yoy_pct, pmi030000_pct"""
        title = '图3：货币供应量 M1/M2 与 CPI/PPI/PMI 环比增幅'
        return self._draw_line_chart(df, {
            'm1_yoy_pct': 'M1环比增幅',
            'm2_yoy_pct': 'M2环比增幅',
            'cpi_yoy_pct': 'CPI环比增幅',
            'ppi_yoy_pct': 'PPI环比增幅',
            'pmi030000_pct': '综合PMI环比',
        }, title, figsize=(14, 6), ylabel='环比增幅')

    def gen_chart4_forex_raw(self, df):
        """图4：forex_reserves, gold_reserves, gold_close（绝对值）"""
        title = '图4：外汇储备 & 黄金储备 & 黄金期货GC（原始值）'
        return self._draw_line_chart(df, {
            'forex_reserves': '外汇储备(亿美元)',
            'gold_reserves': '黄金储备(万盎司)',
            'gold_close': '黄金期货GC(美元/盎司)',
        }, title, figsize=(16, 7), ylabel='数值')

    def gen_chart5_forex_pct(self, df):
        """图5：forex_reserves_pct, gold_reserves_pct, gold_close_pct"""
        title = '图5：外汇储备 & 黄金储备 & 黄金期货GC 环比增幅'
        return self._draw_line_chart(df, {
            'forex_reserves_pct': '外汇储备环比',
            'gold_reserves_pct': '黄金储备环比',
            'gold_close_pct': '黄金期货GC环比',
        }, title, figsize=(16, 7), ylabel='环比增幅')

    def gen_chart6_yields_raw(self, df):
        """图6：国债2Y/5Y/10Y收益率 + GDP + CPI（绝对值），不限制上下界"""
        title = '图6：国债收益率 / GDP同比 / CPI同比（原始值）'
        return self._draw_line_chart(df, {
            'cn_yield_2y': '国债2Y收益率(%)',
            'cn_yield_5y': '国债5Y收益率(%)',
            'cn_yield_10y': '国债10Y收益率(%)',
            'gdp_yoy': 'GDP同比(%)',
            'cpi_yoy': 'CPI同比(%)',
            'vix_close': 'VIX恐慌指数',
            'usdx_index': '美元指数',
        }, title, figsize=(15, 7), ylabel='%')

    def gen_chart7_yields_pct(self, df):
        """图7：国债2Y/5Y/10Y + GDP + CPI pct，不限制上下界"""
        title = '图7：国债收益率 / GDP同比 / CPI同比 环比增幅'
        return self._draw_line_chart(df, {
            'cn_yield_2y_pct': '国债2Y环比',
            'cn_yield_5y_pct': '国债5Y环比',
            'cn_yield_10y_pct': '国债10Y环比',
            'gdp_yoy_pct': 'GDP环比',
            'cpi_yoy_pct': 'CPI环比',
        }, title, figsize=(15, 7), ylabel='环比增幅')

    def gen_chart8_trade_raw(self, df):
        """图8：exports_yoy, imports_yoy（绝对值）"""
        title = '图8：进出口同比（原始值）'
        return self._draw_line_chart(df, {
            'exports_yoy': '出口同比(%)',
            'imports_yoy': '进口同比(%)',
            'vix_close': 'VIX恐慌指数',
            'usdx_index': '美元指数',
        }, title, figsize=(14, 6), ylabel='同比(%)')

    def gen_chart9_trade_pct(self, df):
        """图9：exports_yoy_pct, imports_yoy_pct"""
        title = '图9：进出口同比 环比增幅'
        return self._draw_line_chart(df, {
            'exports_yoy_pct': '出口环比',
            'imports_yoy_pct': '进口环比',
            'vix_close_pct': 'VIX环比',
            'usdx_index_pct': '美元指数环比',
        }, title, figsize=(14, 6), ylabel='环比增幅')

    def gen_chart10_financing_raw(self, df):
        """图10：社会融资分项（绝对值），不限制上下界"""
        title = '图10：社会融资分项（原始值）'
        return self._draw_line_chart(df, {
            'total_shrzgm': '社会融资规模(亿)',
            'rmb_loan': '人民币贷款(亿)',
            'entrusted_loan': '委托贷款(亿)',
            'trust_loan': '信托贷款(亿)',
            'corporate_bonds': '企业债券(亿)',
            'equity_financing': '股权融资(亿)',
        }, title, figsize=(16, 7), ylabel='亿元')

    def gen_chart11_financing_pct(self, df):
        """图11：社会融资分项 pct，不限制上下界"""
        title = '图11：社会融资分项 环比增幅'
        return self._draw_line_chart(df, {
            'total_shrzgm_pct': '社融环比',
            'rmb_loan_pct': '人民币贷款环比',
            'entrusted_loan_pct': '委托贷款环比',
            'trust_loan_pct': '信托贷款环比',
            'corporate_bonds_pct': '企业债券环比',
            'equity_financing_pct': '股权融资环比',
        }, title, figsize=(16, 7), ylabel='环比增幅')

    def gen_chart12_market_raw(self, df):
        """图12：dji_close, hsi_close, twii_close, ks11_close, n225_close, sh_close, sz_close（绝对值），不限制上下界"""
        title = '图12：全球主要股指收盘价（原始值）'
        return self._draw_line_chart(df, {
            'dji_close': '道琼斯工业',
            'hsi_close': '恒生指数',
            'twii_close': '台湾加权',
            'ks11_close': '韩国综合',
            'n225_close': '日经225',
            'sh_close': '上证综指',
            'sz_close': '深证成指',
            'vix_close': 'VIX恐慌指数',
            'usdx_index': '美元指数',
        }, title, figsize=(18, 8), ylabel='收盘价')

    def gen_chart13_market_pct(self, df):
        """图13：dji_close_pct, hsi_close_pct, twii_close_pct, ks11_close_pct, n225_close_pct, sh_close_pct, sz_close_pct，不限制上下界"""
        title = '图13：全球主要股指 环比增幅'
        return self._draw_line_chart(df, {
            'dji_close_pct': '道琼斯环比',
            'hsi_close_pct': '恒生指数环比',
            'twii_close_pct': '台湾加权环比',
            'ks11_close_pct': '韩国综合环比',
            'n225_close_pct': '日经225环比',
            'sh_close_pct': '上证综指环比',
            'sz_close_pct': '深证成指环比',
            'vix_close_pct': 'VIX环比',
            'usdx_index_pct': '美元指数环比',
        }, title, figsize=(18, 8), ylabel='环比增幅')

    def gen_chart14_heatmap_raw(self, df):
        """图14：不带有_PCT字段的相关系数热力图"""
        title = '图14：宏观经济指标原始值 相关系数矩阵'
        raw_cols = [c for c in self.ALL_RAW_FIELDS if c in df.columns]
        if len(raw_cols) < 2:
            logger.warning("RAW字段不足，跳过热力图")
            return None
        return self._draw_heatmap(df, raw_cols, title)

    def gen_chart15_heatmap_pct(self, df):
        """图15：带有_PCT字段的相关系数热力图"""
        title = '图15：宏观经济指标环比增幅 相关系数矩阵'
        pct_cols = [c for c in self.ALL_PCT_FIELDS if c in df.columns]
        if len(pct_cols) < 2:
            logger.warning("PCT字段不足，跳过热力图")
            return None
        return self._draw_heatmap(df, pct_cols, title)

    def _draw_heatmap(self, df, cols, title):
        """通用热力图生成"""
        corr_df = df[cols].dropna(how='all').corr()
        short_labels = [c.replace('_pct', '') for c in corr_df.columns]

        fig, ax = plt.subplots(figsize=(18, 14))
        fig.suptitle(title, fontsize=14, fontweight='bold', color='#1a1a2e')

        mask = np.triu(np.ones_like(corr_df, dtype=bool), k=1)
        cmap = sns.diverging_palette(240, 10, as_cmap=True)
        sns.heatmap(
            corr_df, mask=mask, cmap=cmap, vmin=-1, vmax=1, center=0,
            annot=True, fmt='.2f', linewidths=0.5,
            xticklabels=short_labels, yticklabels=short_labels,
            ax=ax,
            cbar_kws={'shrink': 0.8, 'label': 'Pearson 相关系数'},
            annot_kws={'fontsize': 6.5},
        )
        ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right', fontsize=7)
        ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=7)
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    # ===================== 进阶分析：VIF / PCA / 滚动相关性 =====================

    def _vif_analysis(self, df, cols, label):
        """VIF 多重共线性检测，返回分析文字"""
        if len(cols) < 3:
            return [f"{label}字段不足，无法计算VIF。"]

        valid_cols = [c for c in cols if c in df.columns and df[c].notna().sum() > 2]
        if len(valid_cols) < 3:
            return [f"{label}有效字段不足，无法计算VIF。"]

        data = df[valid_cols].dropna()
        if len(data) < 10:
            return [f"{label}有效样本不足({len(data)}行)，无法计算VIF。"]

        # VIF 计算（跳过常数列，处理无限值）
        data = data.replace([np.inf, -np.inf], np.nan).dropna(axis=1, how='any')
        if data.shape[1] < 3:
            return [f"{label}去除异常值后有效字段不足。"]

        vif_df = pd.DataFrame()
        vif_df["feature"] = data.columns
        vif_values = []
        for i in range(data.shape[1]):
            try:
                vif = variance_inflation_factor(data.values, i)
                # 无穷大或极大值标为 999
                vif = 999.0 if np.isinf(vif) or vif > 1000 else round(vif, 2)
            except Exception:
                vif = 999.0
            vif_values.append(vif)
        vif_df["VIF"] = vif_values

        lines = [
            f"【VIF 多重共线性检测 - {label}】",
            "VIF>10 表示严重多重共线性（该变量可被其他变量高度线性解释）。",
        ]

        high_vif = vif_df[vif_df["VIF"] > 10].sort_values("VIF", ascending=False)
        moderate_vif = vif_df[(vif_df["VIF"] >= 5) & (vif_df["VIF"] <= 10)].sort_values("VIF", ascending=False)

        if len(high_vif) > 0:
            items = []
            for _, row in high_vif.iterrows():
                cn = self.FIELD_CN_NAMES.get(row["feature"].replace('_pct', ''), row["feature"])
                items.append(f"{cn}(VIF={row['VIF']:.1f})")
            lines.append(f"严重(VIF>10)：{'，'.join(items[:8])}。")
        if len(moderate_vif) > 0:
            items = []
            for _, row in moderate_vif.iterrows():
                cn = self.FIELD_CN_NAMES.get(row["feature"].replace('_pct', ''), row["feature"])
                items.append(f"{cn}(VIF={row['VIF']:.1f})")
            lines.append(f"中等(VIF 5~10)：{'，'.join(items[:5])}。")
        if len(high_vif) == 0 and len(moderate_vif) == 0:
            lines.append("所有指标的 VIF 均小于 5，指标间不存在严重的多重共线性问题。")

        # 建议剔除策略
        if len(high_vif) > 0:
            top = high_vif.iloc[0]
            cn = self.FIELD_CN_NAMES.get(top["feature"].replace('_pct', ''), top["feature"])
            lines.append(f"建议关注 {cn}(VIF最高)，可考虑在建模时剔除或使用PCA降维处理。")

        return lines

    def _interpret_pc(self, loadings, feature_names):
        """根据载荷分布给每个主成分赋予经济含义标签"""
        # 定义主题关键词映射
        theme_keywords = {
            '货币/信贷': ['m1', 'm2', 'shibor', 'lpr', 'rmb_loan', 'entrusted_loan',
                        'trust_loan', 'corporate_bonds', 'equity_financing', 'total_shrzgm'],
            '外部/贸易': ['exports', 'imports', 'usdx', 'usdcnh', 'forex', 'gold'],
            '增长/通胀': ['cpi', 'gdp_yoy', 'cn_yield', 'ppi', 'pmi'],
            '市场/风险': ['dji', 'hsi', 'sh_close', 'sz_close', 'n225', 'ks11', 'twii', 'vix', 'gold_close'],
            '海外利率': ['ust_y'],
            'GDP结构': ['gdp_pi', 'gdp_si', 'gdp_ti'],
        }
        # 主题的简短别名
        theme_short = {
            '货币/信贷': '货币信贷', '外部/贸易': '外部贸易', '增长/通胀': '增长通胀',
            '市场/风险': '市场风险', '海外利率': '海外利率', 'GDP结构': '产业结构',
        }

        pc_labels = []
        for i in range(loadings.shape[0]):
            feat_series = pd.Series(loadings[i], index=feature_names)
            top_pos = feat_series.nlargest(3).index.tolist()
            top_neg = feat_series.nsmallest(3).index.tolist()
            all_top = top_pos + top_neg

            # 统计每个主题匹配的指标数
            scores = {}
            for theme, kws in theme_keywords.items():
                score = sum(1 for f in all_top if any(kw in f for kw in kws))
                if score > 0:
                    scores[theme] = score

            if scores:
                primary = max(scores, key=scores.get)
                pc_labels.append(theme_short.get(primary, primary))
            else:
                pc_labels.append(f'混合因子')

        return pc_labels

    def gen_chart16_pca(self, df):
        """图16：PCA 主成分分析散点图 + 载荷热力图"""
        title = '图16：宏观经济指标 PCA 主成分分析（基于环比增幅）'
        pct_cols = [c for c in self.ALL_PCT_FIELDS if c in df.columns]
        if len(pct_cols) < 4:
            logger.warning("PCT字段不足，跳过PCA分析")
            return None

        # 筛选有足够有效数据的列（至少50%非空）
        valid_cols = [c for c in pct_cols if df[c].notna().sum() > len(df) * 0.3]
        if len(valid_cols) < 4:
            logger.warning("PCT有效列不足，跳过PCA分析")
            return None

        # 对有效列，只保留所有有效列都有值的行
        data = df[valid_cols].dropna()
        if len(data) < 10:
            logger.warning(f"PCA有效样本不足({len(data)}行)")
            return None

        logger.info(f"PCA: {len(valid_cols)}个字段, {len(data)}行样本")

        # 标准化
        scaler = StandardScaler()
        scaled = scaler.fit_transform(data)

        # PCA
        pca = PCA(n_components=0.95)  # 保留95%方差
        components = pca.fit_transform(scaled)
        explained_var = pca.explained_variance_ratio_

        fig, axes = plt.subplots(1, 2, figsize=(22, 9))
        fig.suptitle(title, fontsize=14, fontweight='bold', color='#1a1a2e')

        # ===== 左图：PC1 vs PC2 散点 =====
        ax1 = axes[0]
        year_labels = df.loc[data.index, 'trade_year'].values if 'trade_year' in df.columns else None
        if year_labels is not None:
            unique_years = np.unique(year_labels)
            colors_map = plt.cm.tab20(np.linspace(0, 1, min(len(unique_years), 20)))
            for idx, yr in enumerate(unique_years):
                mask = year_labels == yr
                label = str(int(yr)) if idx < 20 else ''
                ax1.scatter(components[mask, 0], components[mask, 1],
                           color=colors_map[idx % 20], label=label,
                           alpha=0.7, s=30, edgecolors='white', linewidth=0.5)
            ax1.legend(loc='upper right', fontsize=7, ncol=2, title='年份')
        else:
            ax1.scatter(components[:, 0], components[:, 1], alpha=0.7, s=30,
                       c='steelblue', edgecolors='white', linewidth=0.5)

        ax1.set_xlabel(f'主成分1 ({explained_var[0]*100:.1f}% 方差解释)', fontsize=10)
        ax1.set_ylabel(f'主成分2 ({explained_var[1]*100:.1f}% 方差解释)', fontsize=10)
        ax1.set_title('PC1 vs PC2 散点图（颜色=年份）', fontsize=11)
        ax1.axhline(y=0, color='gray', linewidth=0.5, linestyle='--')
        ax1.axvline(x=0, color='gray', linewidth=0.5, linestyle='--')
        ax1.grid(True, alpha=0.3)

        # ===== 右图：载荷热力图（展示各主成分由哪些指标驱动）=====
        ax2 = axes[1]

        # 取前6个主成分（解释大部分方差）和 top 10 高载荷指标
        n_components_show = min(6, len(explained_var))
        loadings = pca.components_[:n_components_show]  # shape: (n_comp, n_features)

        # 计算每个指标在所有展示的主成分上的最大绝对载荷，取 top 10
        max_abs_load = np.max(np.abs(loadings), axis=0)
        top_idx = np.argsort(max_abs_load)[::-1][:12]  # 最多12个
        top_features = [valid_cols[i] for i in top_idx]

        # 提取这些指标的载荷矩阵
        loadings_subset = loadings[:, top_idx]  # shape: (n_comp, top_n)

        # 标签：中文名
        feature_labels = [self.FIELD_CN_NAMES.get(f.replace('_pct', ''), f) for f in top_features]

        # 语义标签：根据载荷推断每个PC的经济含义
        pc_themes = self._interpret_pc(loadings, valid_cols)
        comp_labels = [
            f'PC{i+1} {pc_themes[i]}\n({explained_var[i]*100:.1f}%)'
            for i in range(n_components_show)
        ]

        # 用 imshow 绘制热力图
        im = ax2.imshow(loadings_subset, cmap='RdBu_r', aspect='auto', vmin=-1, vmax=1)

        # 标注数值
        for i in range(n_components_show):
            for j in range(len(top_features)):
                val = loadings_subset[i, j]
                color = 'white' if abs(val) > 0.6 else 'black'
                ax2.text(j, i, f'{val:.2f}', ha='center', va='center',
                        fontsize=6.5, color=color, fontweight='bold')

        ax2.set_xticks(range(len(top_features)))
        ax2.set_xticklabels(feature_labels, rotation=45, ha='right', fontsize=7)
        ax2.set_yticks(range(n_components_show))
        ax2.set_yticklabels(comp_labels, fontsize=8)
        ax2.set_xlabel('宏观经济指标', fontsize=10)
        ax2.set_title('主成分载荷矩阵（驱动各主成分的关键指标）', fontsize=11)

        # 色条
        cbar = fig.colorbar(im, ax=ax2, shrink=0.8, pad=0.02)
        cbar.set_label('载荷值', fontsize=8)

        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    def gen_chart17_rolling_corr(self, df):
        """图17：滚动相关性（12个月窗口），选中高相关对"""
        title = '图17：滚动相关性分析（12个月窗口）'
        pct_cols = [c for c in self.ALL_PCT_FIELDS if c in df.columns]
        if len(pct_cols) < 4:
            logger.warning("PCT字段不足，跳过滚动相关性分析")
            return None

        # 筛选有足够有效数据的列
        valid_cols = [c for c in pct_cols if df[c].notna().sum() > len(df) * 0.5]
        if len(valid_cols) < 4:
            logger.warning("PCT有效列不足，跳过滚动相关性")
            return None

        # 找相关系数最高的3对（门槛|r|>=0.3）
        corr_df = df[valid_cols].dropna().corr()
        pairs = []
        for i in range(len(corr_df.columns)):
            for j in range(i + 1, len(corr_df.columns)):
                val = corr_df.iloc[i, j]
                if pd.notna(val) and abs(val) >= 0.3:
                    pairs.append((abs(val), corr_df.columns[i], corr_df.columns[j], val))
        pairs.sort(key=lambda x: x[0], reverse=True)
        top_pairs = pairs[:3]

        if len(top_pairs) < 1:
            logger.warning("未找到高相关对(|r|>=0.3)，跳过滚动相关性")
            return None

        fig, axes = plt.subplots(len(top_pairs), 1, figsize=(16, 4 * len(top_pairs)))
        if len(top_pairs) == 1:
            axes = [axes]
        fig.suptitle(title, fontsize=14, fontweight='bold', color='#1a1a2e')

        window = 12  # 12个月滚动窗口
        x = range(len(df))
        labels = self._make_trade_month_labels(df)

        for idx, (abs_val, col_a, col_b, raw_val) in enumerate(top_pairs):
            ax = axes[idx]
            rolling_corr = df[col_a].rolling(window=window).corr(df[col_b])

            name_a = self.FIELD_CN_NAMES.get(col_a.replace('_pct', ''), col_a)
            name_b = self.FIELD_CN_NAMES.get(col_b.replace('_pct', ''), col_b)

            ax.plot(x, rolling_corr.values, color=self.CHART_COLORS[idx % len(self.CHART_COLORS)],
                    linewidth=0.9, alpha=0.8,
                    label=f'{name_a} vs {name_b} (静态r={raw_val:.2f})')
            ax.axhline(y=raw_val, color='gray', linewidth=0.5, linestyle='--', alpha=0.5)
            ax.axhline(y=0, color='black', linewidth=0.4, linestyle='-')
            ax.axhline(y=0.7, color='green', linewidth=0.4, linestyle=':', alpha=0.5)
            ax.axhline(y=-0.7, color='red', linewidth=0.4, linestyle=':', alpha=0.5)

            ax.set_ylabel(f'滚动相关系数 (window={window})', fontsize=9)
            ax.legend(fontsize=8, loc='upper right')
            ax.grid(True, alpha=0.3)
            ax.set_ylim(-1.05, 1.05)

            # 填色
            ax.fill_between(x, 0, rolling_corr.values,
                           where=rolling_corr.values > 0,
                           color='green', alpha=0.08)
            ax.fill_between(x, 0, rolling_corr.values,
                           where=rolling_corr.values < 0,
                           color='red', alpha=0.08)

            self._set_chart_style(ax, range(len(df)), labels, ylabel='相关系数', xlabel='月份')

        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    def gen_rolling_corr_pair_charts(self, df):
        """生成所有|r|>=0.3的独立滚动相关系数图，每对一张独立图表"""
        pct_cols = [c for c in self.ALL_PCT_FIELDS if c in df.columns]
        if len(pct_cols) < 4:
            return []

        valid_cols = [c for c in pct_cols if df[c].notna().sum() > len(df) * 0.5]
        if len(valid_cols) < 4:
            return []

        corr_df = df[valid_cols].dropna().corr()
        pairs = []
        for i in range(len(corr_df.columns)):
            for j in range(i + 1, len(corr_df.columns)):
                val = corr_df.iloc[i, j]
                if pd.notna(val) and abs(val) >= 0.3:
                    pairs.append((abs(val), corr_df.columns[i], corr_df.columns[j], val))
        pairs.sort(key=lambda x: x[0], reverse=True)

        if not pairs:
            logger.warning("未找到高相关对(|r|>=0.3)，跳过滚动相关系数分解图")
            return []

        window = 12
        x = range(len(df))
        labels = self._make_trade_month_labels(df)

        results = []
        for idx, (abs_val, col_a, col_b, raw_val) in enumerate(pairs):
            fig, ax = plt.subplots(figsize=(16, 4.5))

            rolling_corr = df[col_a].rolling(window=window).corr(df[col_b])

            name_a = self.FIELD_CN_NAMES.get(col_a.replace('_pct', ''), col_a)
            name_b = self.FIELD_CN_NAMES.get(col_b.replace('_pct', ''), col_b)

            ax.plot(x, rolling_corr.values, color=self.CHART_COLORS[0],
                    linewidth=1.0, alpha=0.85, label=f'{name_a} vs {name_b}')
            ax.axhline(y=raw_val, color='gray', linewidth=0.5, linestyle='--', alpha=0.5,
                       label=f'静态相关系数 r={raw_val:.2f}')
            ax.axhline(y=0, color='black', linewidth=0.4, linestyle='-')
            ax.axhline(y=0.7, color='green', linewidth=0.4, linestyle=':', alpha=0.5)
            ax.axhline(y=-0.7, color='red', linewidth=0.4, linestyle=':', alpha=0.5)

            ax.fill_between(x, 0, rolling_corr.values,
                           where=rolling_corr.values > 0,
                           color='green', alpha=0.08)
            ax.fill_between(x, 0, rolling_corr.values,
                           where=rolling_corr.values < 0,
                           color='red', alpha=0.08)

            ax.set_title(f'{name_a} vs {name_b} — 滚动相关系数 (12个月窗口)', fontsize=12, fontweight='bold')
            self._set_chart_style(ax, range(len(df)), labels, ylabel='滚动相关系数', xlabel='月份')
            ax.set_ylim(-1.05, 1.05)
            ax.legend(fontsize=8, loc='upper right')

            plt.tight_layout()
            key = f'rolling_pair_{idx}'
            results.append((key, f'{name_a} vs {name_b} (r={raw_val:.2f})', self._fig_to_bytesio(fig)))

        logger.info(f"🔗 生成 {len(results)} 张滚动相关系数分解图")
        return results

    def _get_pca_analysis(self, df):
        """PCA 文字分析，含每个主成分语义解读"""
        pct_cols = [c for c in self.ALL_PCT_FIELDS if c in df.columns]
        if len(pct_cols) < 4:
            return ["PCT字段不足，无法进行PCA分析。"]

        valid_cols = [c for c in pct_cols if df[c].notna().sum() > len(df) * 0.3]
        if len(valid_cols) < 4:
            return ["PCA有效列不足。"]

        data = df[valid_cols].dropna()
        if len(data) < 10:
            return [f"PCA有效样本不足({len(data)}行)。"]

        scaler = StandardScaler()
        scaled = scaler.fit_transform(data)
        pca = PCA(n_components=0.95)
        pca.fit(scaled)

        explained = pca.explained_variance_ratio_
        cumsum = np.cumsum(explained)

        n_95 = next((i + 1 for i, v in enumerate(cumsum) if v >= 0.95), len(explained))
        n_80 = next((i + 1 for i, v in enumerate(cumsum) if v >= 0.80), len(explained))

        # 语义解读
        pc_themes = self._interpret_pc(pca.components_[:6], valid_cols)

        lines = [
            f"【PCA 主成分分析】",
            f"前{n_80}个主成分解释了80%的方差，前{n_95}个主成分解释了95%的方差（共{len(explained)}个主成分）。",
            f"主成分的语义标签根据高载荷指标自动推断（取各PC正负向Top3指标所属经济领域投票决定）。",
            f"",
            f"各主成分经济含义（带%为方差解释比例）：",
        ]

        n_show = min(6, len(explained), len(pc_themes))
        for i in range(n_show):
            feat_series = pd.Series(pca.components_[i], index=valid_cols)
            top_pos = feat_series.nlargest(3)
            top_neg = feat_series.nsmallest(3)
            pos_names = [self.FIELD_CN_NAMES.get(c.replace('_pct', ''), c) for c in top_pos.index]
            neg_names = [self.FIELD_CN_NAMES.get(c.replace('_pct', ''), c) for c in top_neg.index]
            pos_str = '、'.join([f"{n}(+{v:.2f})" for n, v in zip(pos_names, top_pos.values)])
            neg_str = '、'.join([f"{n}({v:.2f})" for n, v in zip(neg_names, top_neg.values)])
            lines.append(
                f"PC{i+1}【{pc_themes[i]}】({explained[i]*100:.1f}%): "
                f"正向→ {pos_str}；"
                f"负向→ {neg_str}。"
            )

        lines.append("")
        lines.append(
            f"注：PC6（{pc_themes[5] if len(pc_themes) > 5 else ''}）仅解释{explained[5]*100:.1f}%的方差，"
            f"属于次要维度，其高载荷指标（如委托贷款）在该PC上虽然显著，但整体解释力有限，"
            f"不宜过度外推其经济含义。"
        )

        lines.append("")
        lines.append(
            f"PCA结果说明宏观经济指标的环比变化可以由{n_95}个潜在因子驱动，"
            f"在后续建模中可考虑降维至{n_95}维以消除冗余。"
        )
        return lines

    def _get_rolling_corr_analysis(self, df):
        """滚动相关性文字分析"""
        pct_cols = [c for c in self.ALL_PCT_FIELDS if c in df.columns]
        if len(pct_cols) < 4:
            return ["PCT字段不足，无法进行滚动相关性分析。"]

        valid_cols = [c for c in pct_cols if df[c].notna().sum() > len(df) * 0.5]
        if len(valid_cols) < 4:
            return ["PCT有效列不足，无法进行滚动相关性分析。"]

        corr_df = df[valid_cols].dropna().corr()
        pairs = []
        for i in range(len(corr_df.columns)):
            for j in range(i + 1, len(corr_df.columns)):
                val = corr_df.iloc[i, j]
                if pd.notna(val) and abs(val) >= 0.3:
                    pairs.append((abs(val), corr_df.columns[i], corr_df.columns[j], val))
        pairs.sort(key=lambda x: x[0], reverse=True)

        lines = [
            "【滚动相关性分析（12个月窗口）】",
            "滚动相关性展示了两个指标之间相关系数的时变特征，",
            "揭示了经济周期不同阶段下指标间联动关系的动态演化。",
        ]
        if pairs:
            window = 12
            top3 = pairs[:3]
            for _, col_a, col_b, raw_val in top3:
                rolling = df[col_a].rolling(window=window).corr(df[col_b])
                rolling_max = rolling.max()
                rolling_min = rolling.min()
                rolling_std = rolling.std()
                name_a = self.FIELD_CN_NAMES.get(col_a.replace('_pct', ''), col_a)
                name_b = self.FIELD_CN_NAMES.get(col_b.replace('_pct', ''), col_b)
                lines.append(
                    f"{name_a} vs {name_b}：静态相关系数{raw_val:.2f}，"
                    f"滚动相关系数区间[{rolling_min:.2f}, {rolling_max:.2f}]，"
                    f"标准差{rolling_std:.2f}，{'关系稳定。' if rolling_std < 0.2 else '关系波动较大，受经济周期切换影响显著。'}"
                )
        else:
            lines.append("未发现强相关(|r|>=0.3)的指标对。")
        return lines

    def _get_summary(self, df):
        """综述分析"""
        pct_cols = [c for c in self.ALL_PCT_FIELDS if c in df.columns]
        recent = df.tail(12)

        lines = [
            "本报告基于 ClickHouse tb_macro_economic_indicator 表数据，",
            f"覆盖 {len(self.ALL_RAW_FIELDS)} 个宏观经济指标（含原始值与环比增幅），",
            f"时间跨度为 {df['trade_month'].min()} 至 {df['trade_month'].max()}。",
            "",
            "报告含15张图表 + 2张进阶分析图（PCA主成分分析 + 滚动相关性），",
            "指标原始值（绝对值/同比）折线图 → 环比增幅折线图 → 相关系数热力图 → 进阶分析。",
            "环比增幅 = (当期值 - 前期值) / 前期值，反映各项指标的边际变化速率。",
            "",
        ]

        latest_vals = {}
        for col in pct_cols:
            vals = recent[col].dropna()
            if len(vals) > 0:
                latest_vals[col] = vals.iloc[-1]
        rising = sum(1 for v in latest_vals.values() if v > 0)
        falling = sum(1 for v in latest_vals.values() if v < 0)
        lines.append(
            f"最新一期数据中，{rising} 项指标环比上升，{falling} 项指标环比下降。"
        )

        all_std = {}
        for col in pct_cols:
            vals = df[col].dropna()
            if len(vals) > 2:
                all_std[col] = vals.std()
        if all_std:
            max_vol_col = max(all_std, key=all_std.get)
            cn_name = self.FIELD_CN_NAMES.get(max_vol_col.replace('_pct', ''), max_vol_col)
            lines.append(
                f"历史波动率最大的环比指标为 {cn_name}，标准差 {all_std[max_vol_col]:.4f}，"
                f"该领域受政策或市场影响最为显著。"
            )

        lines.append(
            "综合来看，各指标间存在较强的联动关系，建议结合两张相关系数热力图进行多维综合分析。"
        )
        return lines

    def _get_chart1_analysis(self, df):
        """图1：全景分析"""
        pct_cols = [c for c in self.ALL_PCT_FIELDS if c in df.columns]
        recent = df.tail(12)
        lines = [
            "图1展示了22个宏观经济指标月度环比增幅的全景。环比增幅=(当期值-前期值)/前期值，"
            "反映各项指标的边际变化速率。本图不设Y轴上下界，完整展示各指标的波动幅度。",
            "",
        ]
        recent_std = {}
        for col in pct_cols:
            vals = recent[col].dropna()
            if len(vals) > 1:
                recent_std[col] = vals.std()
        high_vol = sorted(recent_std.items(), key=lambda x: x[1], reverse=True)[:5]
        names = [self.FIELD_CN_NAMES.get(f.replace('_pct', ''), f) for f, _ in high_vol]
        lines.append(f"近期波动最大的5个指标：{'、'.join(names)}，反映出这些领域政策或市场环境变化较为剧烈。")

        recent_mean = {}
        for col in pct_cols:
            vals = recent[col].dropna()
            if len(vals) > 0:
                recent_mean[col] = vals.iloc[-1]
        rising = [self.FIELD_CN_NAMES.get(c.replace('_pct', ''), c) for c, v in recent_mean.items() if v > 0.005]
        falling = [self.FIELD_CN_NAMES.get(c.replace('_pct', ''), c) for c, v in recent_mean.items() if v < -0.005]
        if rising:
            lines.append(f"最新一期环比为正的指标：{'、'.join(rising)}。")
        if falling:
            lines.append(f"最新一期环比为负的指标：{'、'.join(falling)}。")
        return lines

    def _get_chart2_analysis(self, df):
        """图2：M1/M2 与 CPI/PPI/PMI 原始值"""
        lines = []
        recent = df.tail(12)
        if 'm1_yoy' in df.columns and 'm2_yoy' in df.columns:
            m1_last = recent['m1_yoy'].dropna().iloc[-1]
            m2_last = recent['m2_yoy'].dropna().iloc[-1]
            diff = m1_last - m2_last
            lines.append(
                f"【货币供应水平】M1同比 {m1_last:.2f}%，M2同比 {m2_last:.2f}%，剪刀差 {diff:.2f}%。"
                f"{'M1增速领先，企业活期存款活跃，经济活跃度较高。' if diff > 0 else 'M2增速领先，资金沉淀于定期/储蓄，企业投资意愿偏弱。'}"
            )
            m1_min = df['m1_yoy'].min()
            m2_min = df['m2_yoy'].min()
            lines.append(
                f"历史极值方面，M1最低 {m1_min:.2f}%，M2最低 {m2_min:.2f}%，"
                f"当前水平距历史低点已有显著回升/延续低位震荡。"
            )
        if 'cpi_yoy' in df.columns:
            cpi_last = recent['cpi_yoy'].dropna().iloc[-1]
            lines.append(
                f"【CPI同比】当前 {cpi_last:.2f}%，{'通胀温和。' if cpi_last < 3 else '通胀压力上升。'}"
            )
        if 'ppi_yoy' in df.columns:
            ppi_last = recent['ppi_yoy'].dropna().iloc[-1]
            lines.append(
                f"【PPI同比】当前 {ppi_last:.2f}%，"
                f"{'工业品价格回升，企业利润改善。' if ppi_last > 0 else '工业品价格下行，反映需求偏弱。'}"
            )
        if 'pmi030000' in df.columns:
            pmi_last = recent['pmi030000'].dropna().iloc[-1]
            lines.append(
                f"【综合PMI】当前 {pmi_last:.2f}，"
                f"{'高于荣枯线，经济扩张中。' if pmi_last > 50 else '低于荣枯线，经济收缩。'}"
            )
        return lines

    def _get_chart3_analysis(self, df):
        """图3：M1/M2 与 CPI/PPI/PMI 环比增幅"""
        recent = df.tail(12)
        lines = []
        m1_last = df['m1_yoy_pct'].dropna().iloc[-1] if 'm1_yoy_pct' in df.columns else None
        m2_last = df['m2_yoy_pct'].dropna().iloc[-1] if 'm2_yoy_pct' in df.columns else None

        if m1_last is not None and m2_last is not None:
            diff = m1_last - m2_last
            direction = "M1环比增幅 > M2，企业活期存款增长快于广义货币，经济活跃度提升" \
                if diff > 0 else "M2环比增幅 > M1，可能反映企业投资意愿偏弱，资金沉淀于定期或储蓄"
            lines.append(
                f"【货币供应剪刀差】M1环比增幅 {m1_last * 100:.2f}%，M2环比增幅 {m2_last * 100:.2f}%，"
                f"剪刀差 {diff * 100:.2f}%。{direction}。"
            )
            m1_vals = recent['m1_yoy_pct'].dropna()
            m2_vals = recent['m2_yoy_pct'].dropna()
            if len(m1_vals) >= 3 and len(m2_vals) >= 3:
                m1_trend = "回升" if m1_vals.iloc[-1] > m1_vals.iloc[0] else "回落"
                m2_trend = "回升" if m2_vals.iloc[-1] > m2_vals.iloc[0] else "回落"
                lines.append(
                    f"近期趋势：M1环比{m1_trend}，M2环比{m2_trend}，需持续关注货币政策传导效果。"
                )
        if 'cpi_yoy_pct' in df.columns:
            cpi_last = recent['cpi_yoy_pct'].dropna().iloc[-1]
            label = "通胀压力" if cpi_last > 0.002 else ("通缩风险" if cpi_last < -0.002 else "物价相对稳定")
            lines.append(f"【CPI环比】{cpi_last * 100:.2f}%，当前呈现{label}特征。")
        if 'ppi_yoy_pct' in df.columns:
            ppi_last = recent['ppi_yoy_pct'].dropna().iloc[-1]
            direction = "上涨" if ppi_last > 0 else "下跌"
            lines.append(f"【PPI环比】{direction} {abs(ppi_last) * 100:.2f}%。")
        if 'pmi030000_pct' in df.columns:
            pmi_last = recent['pmi030000_pct'].dropna().iloc[-1]
            direction = "回升" if pmi_last > 0 else "回落"
            lines.append(f"【综合PMI环比】{direction} {abs(pmi_last) * 100:.2f}。")
        return lines

    def _get_chart4_analysis(self, df):
        """图4：外汇/黄金/黄金期货 原始值"""
        lines = []
        if 'forex_reserves' in df.columns:
            forex_last = df['forex_reserves'].dropna().iloc[-1]
            forex_max = df['forex_reserves'].max()
            lines.append(
                f"【外汇储备】当前 {forex_last:.0f} 亿美元，历史峰值 {forex_max:.0f} 亿美元。"
                f"外汇储备充足是国家抵御外部金融冲击的重要屏障。"
            )
        if 'gold_reserves' in df.columns:
            gold_last = df['gold_reserves'].dropna().iloc[-1]
            gold_first = df['gold_reserves'].dropna().iloc[0]
            change = gold_last - gold_first
            lines.append(
                f"【黄金储备】当前 {gold_last:.0f} 万盎司，"
                f"较期初增加 {change:.0f} 万盎司。央行持续增持黄金反映储备多元化战略。"
            )
        if 'gold_close' in df.columns:
            gc_last = df['gold_close'].dropna().iloc[-1]
            gc_min = df['gold_close'].min()
            gc_max = df['gold_close'].max()
            lines.append(
                f"【黄金期货GC】当前 {gc_last:.0f} 美元/盎司，"
                f"区间 [{gc_min:.0f}, {gc_max:.0f}]。"
                f"黄金价格与美元指数、地缘风险高度相关，为全球风险偏好的重要晴雨表。"
                f"{'当前金价处于高位，反映避险需求旺盛。' if gc_last > gc_max * 0.85 else ''}"
            )
        return lines

    def _get_chart5_analysis(self, df):
        """图5：外汇/黄金/黄金期货 环比增幅"""
        lines = []
        forex_last = df['forex_reserves_pct'].dropna().iloc[-1] if 'forex_reserves_pct' in df.columns else None
        gold_last = df['gold_reserves_pct'].dropna().iloc[-1] if 'gold_reserves_pct' in df.columns else None

        if forex_last is not None:
            label = "上升" if forex_last > 0 else "下降"
            lines.append(
                f"【外汇储备】最新环比增幅 {forex_last * 100:.2f}%，外汇储备呈{label}态势。"
                f"{'外汇储备增加有助于增强抵御外部冲击的能力。' if forex_last > 0 else '外汇储备下降需关注资本流动和汇率压力。'}"
            )
        if gold_last is not None:
            label = "增持" if gold_last > 0 else "减持"
            lines.append(
                f"【黄金储备】最新环比增幅 {gold_last * 100:.2f}%，央行{label}黄金储备。"
                f"黄金作为避险资产，其配置变化反映对国际货币体系的判断。"
            )
        if 'gold_close_pct' in df.columns:
            gc_last = df['gold_close_pct'].dropna().iloc[-1]
            direction = "上涨" if gc_last > 0 else "下跌"
            lines.append(
                f"【黄金期货GC环比】{direction} {abs(gc_last) * 100:.2f}%，"
                f"{'市场避险情绪升温。' if gc_last > 0 else '风险偏好回升。'}"
            )
        return lines

    def _get_chart6_analysis(self, df):
        """图6：国债/GDP/CPI 原始值"""
        recent = df.tail(12)
        lines = []
        if 'cn_yield_10y' in df.columns:
            y10 = recent['cn_yield_10y'].dropna().iloc[-1]
            y10_avg = df['cn_yield_10y'].mean()
            lines.append(
                f"【10年期国债收益率】当前 {y10:.2f}%，历史均值 {y10_avg:.2f}%。"
                f"{'高于历史均值，反映市场对经济前景的乐观预期或通胀担忧。' if y10 > y10_avg else '低于历史均值，反映避险情绪或宽松预期。'}"
            )
        if 'cn_yield_2y' in df.columns and 'cn_yield_10y' in df.columns:
            y2 = recent['cn_yield_2y'].dropna().iloc[-1]
            y10 = recent['cn_yield_10y'].dropna().iloc[-1]
            spread = y10 - y2
            lines.append(f"收益率曲线：2Y-10Y利差 {spread:.2f}%，{'曲线陡峭，通常预示经济扩张预期。' if spread > 0.5 else '曲线平坦化，需关注经济动能变化。'}")
        if 'gdp_yoy' in df.columns:
            gdp_last = df['gdp_yoy'].dropna().iloc[-1]
            lines.append(f"【GDP同比】当前 {gdp_last:.2f}%。")
        if 'cpi_yoy' in df.columns:
            cpi_last = recent['cpi_yoy'].dropna().iloc[-1]
            lines.append(f"【CPI同比】当前 {cpi_last:.2f}%，{'通胀温和。' if cpi_last < 3 else '通胀压力上升。'}")
        return lines

    def _get_chart7_analysis(self, df):
        """图7：国债/GDP/CPI 环比增幅"""
        recent = df.tail(12)
        lines = []
        if 'cn_yield_10y_pct' in df.columns:
            y10 = recent['cn_yield_10y_pct'].dropna().iloc[-1]
            direction = "上行" if y10 > 0 else "下行"
            lines.append(
                f"【10年期国债收益率环比】{direction} {abs(y10) * 100:.2f}%，"
                f"{'反映市场对经济前景预期改善或通胀预期升温。' if y10 > 0 else '反映避险情绪升温或宽松预期增强。'}"
            )
        if 'cn_yield_2y_pct' in df.columns and 'cn_yield_10y_pct' in df.columns:
            y2 = recent['cn_yield_2y_pct'].dropna().iloc[-1]
            y10 = recent['cn_yield_10y_pct'].dropna().iloc[-1]
            flattening = y10 - y2
            shape = "陡峭化" if flattening > 0 else "平坦化"
            lines.append(f"【收益率曲线环比】2Y-10Y利差变化 {flattening * 100:.2f}%，曲线呈{shape}趋势。")
        if 'gdp_yoy_pct' in df.columns:
            gdp_last = recent['gdp_yoy_pct'].dropna().iloc[-1]
            lines.append(f"【GDP同比环比】{gdp_last * 100:.2f}%，{'经济增长动能持续。' if gdp_last > 0 else '经济增长面临下行压力。'}")
        if 'cpi_yoy_pct' in df.columns:
            cpi_last = recent['cpi_yoy_pct'].dropna().iloc[-1]
            label = "通胀压力" if cpi_last > 0.002 else ("通缩风险" if cpi_last < -0.002 else "物价相对稳定")
            lines.append(f"【CPI同比环比】{cpi_last * 100:.2f}%，当前呈现{label}特征。")
        return lines

    def _get_chart8_analysis(self, df):
        """图8：进出口 原始值"""
        lines = []
        if 'exports_yoy' in df.columns and 'imports_yoy' in df.columns:
            recent = df.tail(12)
            exp_last = recent['exports_yoy'].dropna().iloc[-1]
            imp_last = recent['imports_yoy'].dropna().iloc[-1]
            diff = exp_last - imp_last
            lines.append(
                f"【对外贸易】出口同比 {exp_last:.2f}%，进口同比 {imp_last:.2f}%，"
                f"贸易差 {diff:.2f}%。{'出口强于进口，贸易顺差。' if diff > 0 else '进口强于出口，需关注贸易逆差。'}"
            )
            exp_min = df['exports_yoy'].min()
            exp_max = df['exports_yoy'].max()
            lines.append(f"出口同比区间 [{exp_min:.2f}%, {exp_max:.2f}%]，反映外部需求波动的完整周期。")
        return lines

    def _get_chart9_analysis(self, df):
        """图9：进出口 环比增幅"""
        lines = []
        exp_last = df['exports_yoy_pct'].dropna().iloc[-1] if 'exports_yoy_pct' in df.columns else None
        imp_last = df['imports_yoy_pct'].dropna().iloc[-1] if 'imports_yoy_pct' in df.columns else None

        if exp_last is not None and imp_last is not None:
            diff = exp_last - imp_last
            if diff > 0.005:
                interpretation = "出口环比强于进口，外需动能相对强劲。"
            elif diff < -0.005:
                interpretation = "进口环比强于出口，内需或有所改善。"
            else:
                interpretation = "进出口增速相对均衡。"
            lines.append(
                f"【对外贸易环比】出口环比增幅 {exp_last * 100:.2f}%，进口环比增幅 {imp_last * 100:.2f}%。{interpretation}"
            )
        return lines

    def _get_chart10_analysis(self, df):
        """图10：融资分项 原始值"""
        lines = []
        recent = df.tail(12)
        if 'total_shrzgm' in df.columns:
            shr_total = recent['total_shrzgm'].dropna().iloc[-1]
            lines.append(f"【社会融资总量】最新 {shr_total:.0f} 亿元。")
        if 'rmb_loan' in df.columns:
            loan = recent['rmb_loan'].dropna().iloc[-1]
            lines.append(f"【人民币贷款】最新 {loan:.0f} 亿元，为社融主力。")

        struct_items = []
        for col, name in [('corporate_bonds', '企业债券'), ('equity_financing', '股权融资'),
                          ('entrusted_loan', '委托贷款'), ('trust_loan', '信托贷款')]:
            if col in df.columns:
                val = recent[col].dropna().iloc[-1]
                struct_items.append(f"{name} {val:.0f}亿")
        if struct_items:
            lines.append("【融资结构】各分项最新： " + "；".join(struct_items) + "。")
        return lines

    def _get_chart11_analysis(self, df):
        """图11：融资分项 环比增幅"""
        lines = []
        recent = df.tail(12)
        if 'total_shrzgm_pct' in df.columns:
            shr = recent['total_shrzgm_pct'].dropna().iloc[-1]
            direction = "扩张" if shr > 0 else "收缩"
            lines.append(f"【社会融资总量环比】{shr * 100:.2f}%，整体呈{direction}态势。")

        if 'rmb_loan_pct' in df.columns:
            loan = recent['rmb_loan_pct'].dropna().iloc[-1]
            lines.append(
                f"【人民币贷款环比】{loan * 100:.2f}%，"
                f"{'信贷扩张加速。' if loan > 0 else '信贷增速放缓，需关注融资可得性。'}"
            )

        bond_items = []
        for col, name in [('corporate_bonds_pct', '企业债券'), ('equity_financing_pct', '股权融资'),
                          ('entrusted_loan_pct', '委托贷款'), ('trust_loan_pct', '信托贷款')]:
            if col in df.columns:
                val = recent[col].dropna().iloc[-1]
                trend = "↑" if val > 0 else "↓"
                bond_items.append(f"{name}{trend} {val * 100:.2f}%")
        if bond_items:
            lines.append("【融资结构环比变化】 " + "；".join(bond_items) + "。")
        return lines

    def _get_chart12_analysis(self, df):
        """图12：全球主要股指 原始值"""
        lines = []
        recent = df.tail(12)
        indices = [
            ('dji_close', '道琼斯'), ('hsi_close', '恒生'), ('twii_close', '台湾加权'),
            ('ks11_close', '韩国综合'), ('n225_close', '日经225'),
            ('sh_close', '上证综指'), ('sz_close', '深证成指'),
        ]
        latest_parts = []
        for col, name in indices:
            if col in df.columns:
                last_val = recent[col].dropna().iloc[-1] if len(recent[col].dropna()) > 0 else None
                if last_val is not None:
                    latest_parts.append(f"{name} {last_val:.0f}")
        if latest_parts:
            lines.append(f"【全球股指】{'，'.join(latest_parts)}。")
        if len(df) > 24:
            perf_parts = []
            for col, name in indices:
                if col in df.columns:
                    vals = df[col].dropna()
                    if len(vals) > 0:
                        first = vals.iloc[0]
                        last = vals.iloc[-1]
                        ret = (last - first) / first * 100
                        perf_parts.append(f"{name} {ret:+.1f}%")
            if perf_parts:
                lines.append(f"区间涨跌：{'，'.join(perf_parts)}。")
        # 亚太vs美股对比
        if 'dji_close' in df.columns and 'hsi_close' in df.columns:
            dji_corr = df['dji_close'].corr(df['hsi_close'])
            lines.append(f"道琼斯与恒生相关系数 {dji_corr:.2f}，{'联动紧密。' if abs(dji_corr) > 0.7 else '存在一定独立性。'}")
        return lines

    def _get_chart13_analysis(self, df):
        """图13：全球主要股指 环比增幅"""
        lines = []
        recent = df.tail(12)
        pct_indices = [
            ('dji_close_pct', '道琼斯'), ('hsi_close_pct', '恒生'), ('twii_close_pct', '台湾加权'),
            ('ks11_close_pct', '韩国综合'), ('n225_close_pct', '日经225'),
            ('sh_close_pct', '上证综指'), ('sz_close_pct', '深证成指'),
        ]
        for col, name in pct_indices:
            if col in df.columns:
                last_val = recent[col].dropna().iloc[-1] if len(recent[col].dropna()) > 0 else None
                if last_val is not None:
                    trend = "↑" if last_val > 0 else "↓"
                    lines.append(f"{name}环比 {trend} {abs(last_val) * 100:.2f}%")
        return lines

    def _get_chart14_analysis(self, df):
        """图14：原始值相关系数 + VIF 分析"""
        raw_cols = [c for c in self.ALL_RAW_FIELDS if c in df.columns]
        lines = self._corr_analysis(df, raw_cols, "原始值")
        # 追加 VIF 分析
        vif_lines = self._vif_analysis(df, raw_cols, "原始值")
        if len(vif_lines) > 1:
            lines.append("")
            lines.extend(vif_lines)
        return lines

    def _get_chart15_analysis(self, df):
        """图15：PCT相关系数 + VIF 分析"""
        pct_cols = [c for c in self.ALL_PCT_FIELDS if c in df.columns]
        lines = self._corr_analysis(df, pct_cols, "环比增幅")
        # 追加 VIF 分析
        vif_lines = self._vif_analysis(df, pct_cols, "环比增幅")
        if len(vif_lines) > 1:
            lines.append("")
            lines.extend(vif_lines)
        return lines

    def _corr_analysis(self, df, cols, label):
        """通用相关系数分析"""
        if len(cols) < 2:
            return [f"{label}字段不足，无法计算相关系数矩阵。"]
        corr_df = df[cols].dropna(how='all').corr()
        short_labels = [c.replace('_pct', '') for c in corr_df.columns]

        lines = [
            f"热力图展示了{label}指标之间的Pearson相关系数矩阵。",
            "|r| > 0.7 为强相关，0.4 < |r| < 0.7 为中等相关，|r| < 0.4 为弱相关。",
            "",
        ]
        high_corr = []
        neg_corr = []
        for i in range(len(short_labels)):
            for j in range(i + 1, len(short_labels)):
                val = corr_df.iloc[i, j]
                if pd.notna(val):
                    if val >= 0.7:
                        high_corr.append((short_labels[i], short_labels[j], val))
                    elif val <= -0.5:
                        neg_corr.append((short_labels[i], short_labels[j], val))

        if high_corr:
            high_corr.sort(key=lambda x: x[2], reverse=True)
            text = '；'.join([f'{a}-{b}({v:.2f})' for a, b, v in high_corr[:8]])
            lines.append(f"【强正相关对】{text}")
            lines.append("这些指标通常受相同的宏观经济因素驱动。")
        if neg_corr:
            neg_corr.sort(key=lambda x: x[2])
            text = '；'.join([f'{a}-{b}({v:.2f})' for a, b, v in neg_corr[:5]])
            lines.append(f"【显著负相关对】{text}")
            lines.append("这些负相关关系可能反映了经济中的对冲机制。")
        return lines

    # ===================== AI 宏观经济分析 =====================

    def _extract_year_end_data(self, df):
        """提取每年年底（12月）数据，从最老到最新，为 AI 分析准备"""
        df_sorted = df.sort_values('trade_month').reset_index(drop=True)
        df_sorted['trade_month_int'] = df_sorted['trade_month'].astype(int)
        df_ye = df_sorted[
            (df_sorted['trade_month_int'] % 100 == 12) |
            (df_sorted['trade_month_int'] == df_sorted['trade_month_int'].max())
        ].copy()
        df_ye = df_ye.drop_duplicates(subset=['trade_year'], keep='last')

        raw_cols = [c for c in self.ALL_RAW_FIELDS if c in df_ye.columns]
        for col in raw_cols:
            df_ye[col] = df_ye[col].round(4)
        return df_ye, raw_cols

    def _generate_ai_macro_analysis(self, df):
        """将每年年底数据发给 ZhipuGLM4，获得专业宏观经济分析（学习 ConvertibleBondManagerReport 模式）"""
        df_ye, raw_cols = self._extract_year_end_data(df)
        if df_ye.empty or len(raw_cols) < 4:
            logger.info("年底数据不足，跳过 AI 宏观经济分析")
            return None

        # 紧凑数据文本，节约 token
        data_lines = []
        for _, row in df_ye.iterrows():
            tm = int(row['trade_month'])
            parts = [f"{tm}:"]
            for col in raw_cols:
                val = row[col]
                if pd.isna(val):
                    continue
                label = self.FIELD_CN_NAMES.get(col, col)
                if abs(val) >= 1000:
                    parts.append(f"{label}={val:.0f}")
                elif abs(val) >= 10:
                    parts.append(f"{label}={val:.1f}")
                elif abs(val) >= 1:
                    parts.append(f"{label}={val:.2f}")
                else:
                    parts.append(f"{label}={val:.3f}")
            data_lines.append(" ".join(parts))
        data_block = "\n".join(data_lines)
        n_years = len(df_ye)

        prompt = f"""你是一位从业25年的资深宏观经济首席分析师，曾任职于央行研究局和大型宏观对冲基金。请以专业、严谨、有前瞻性的视角分析以下中国宏观经济年度数据。

数据为每年12月末截面数据，{df_ye['trade_month'].min()}-{df_ye['trade_month'].max()}，共{n_years}年。字段：
- 货币市场：SHIBOR 3M、LPR 5Y、M1/M2同比、CPI同比、PPI同比、综合PMI、USDCNH汇率
- 国债收益率：2Y/5Y/10Y
- 外部：美国10Y国债、美元指数、外汇储备、黄金储备、黄金期货GC价格、进出口同比
- 全球股指：道琼斯工业、恒生指数、台湾加权、韩国综合、日经225、上证综指、深证成指
- 融资：社会融资规模及各分项（人民币贷款/委托贷款/信托贷款/企业债券/股权融资）
- 实体：GDP同比

数据：
{data_block}

请完成以下分析，每条100-200字，结构清晰：
1.【经济周期定位】当前中国经济处于什么周期阶段？结合GDP/M1-M2剪刀差/CPI/PPI/PMI变化趋势判断
2.【货币政策评估】SHIBOR/LPR/国债收益率走势反映的货币政策取向及流动性环境
3.【外部环境】美国利率、美元指数、人民币汇率、外汇储备、黄金价格、进出口数据揭示的外部压力与机遇
4.【全球市场联动】道琼斯/恒生/台湾加权/韩国综合/日经225/上证综指/深证成指的走势特征及亚太-美股跨境联动性分析
5.【融资结构变迁】社会融资规模及各分项的结构变化说明，企业融资偏好演变
6.【前瞻判断】未来1-2年宏观经济最可能的走势及主要风险点
7.【资产配置启示】当前宏观环境下对固收/权益/大宗商品（含黄金）的配置建议
8.【你作为中国经济专家对中国的看法】你要从中的角度来分析中国的经济参数，请用中文直接给出分析内容。
9.【美国对中国的看法】你要从美国的角度来分析中国的经济参数，请用中文直接给出分析内容。

请用中文直接给出分析内容，以编号和标题开头。"""

        logger.info(f"=============== AI 宏观经济分析 Prompt（{n_years}年数据）===============")
        logger.info(f"Prompt 长度: {len(prompt)} 字符")
        logger.info(f"Prompt : {prompt}")

        if CommonParameters.IF_ENABLE_MOCKED_AI:
            logger.info("IF_ENABLE_MOCKED_AI=True，返回模拟 AI 分析")
            return self._mocked_ai_analysis(df_ye)

        logger.info("正在调用 ZhipuGLM4 生成 AI 宏观经济分析报告...")
        try:
            result = ZhipuGLM4.inquiry(prompt, "")
            logger.info("ZhipuGLM4 AI 分析报告生成成功")
            return result
        except Exception as e:
            logger.error(f"AI 分析报告生成失败: {e}")
            return f"AI 分析报告生成失败: {e}"

    def _mocked_ai_analysis(self, df_ye):
        """模拟 AI 分析（IF_ENABLE_MOCKED_AI=True 时使用）"""
        last_row = df_ye.iloc[-1] if len(df_ye) > 0 else {}
        gdp = last_row.get('gdp_yoy', 'N/A')
        m1 = last_row.get('m1_yoy', 'N/A')
        m2 = last_row.get('m2_yoy', 'N/A')

        return f"""(模拟 AI 宏观经济分析报告)
Nil

(以上为模拟 AI 分析)"""

    # ===================== PDF 报告生成（reportlab，参照 CMLAnalysisReport） =====================

    def _build_pdf_styles(self):
        """构建 PDF 样式"""
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'ReportTitle', parent=styles['Heading1'],
            fontSize=24, leading=32, alignment=1,
            fontName=self.reportlab_font, spaceAfter=30,
        )
        heading1 = ParagraphStyle(
            'Heading1Style', parent=styles['Heading1'],
            fontSize=18, leading=26, fontName=self.reportlab_font,
            spaceAfter=14, spaceBefore=14,
        )
        heading2 = ParagraphStyle(
            'Heading2Style', parent=styles['Heading2'],
            fontSize=14, leading=20, fontName=self.reportlab_font,
            spaceAfter=10, spaceBefore=10,
        )
        normal = ParagraphStyle(
            'NormalStyle', parent=styles['Normal'],
            fontSize=10, leading=15, fontName=self.reportlab_font,
        )
        cover_info = ParagraphStyle(
            'CoverInfo', parent=styles['Normal'],
            fontSize=14, leading=22, alignment=1,
            fontName=self.reportlab_font, textColor=colors.HexColor('#333333'),
        )
        return {
            'title': title_style,
            'h1': heading1,
            'h2': heading2,
            'normal': normal,
            'cover_info': cover_info,
        }

    def _add_text_section(self, story, title, lines, styles):
        """向 story 添加文字分析段落"""
        story.append(Paragraph(title, styles['h1']))
        story.append(Spacer(1, 0.15 * inch))
        for line in lines:
            if line.startswith('【'):
                story.append(Paragraph(line, styles['h2']))
            elif line.strip() == '':
                story.append(Spacer(1, 0.08 * inch))
            else:
                story.append(Paragraph(line, styles['normal']))
        story.append(Spacer(1, 0.2 * inch))

    def _generate_pdf_report(self, df, chart_buffers, ai_analysis, rolling_pair_charts=None):
        """生成完整 PDF 报告（reportlab，不保存中间图片）"""
        styles = self._build_pdf_styles()

        start_month = str(int(df['trade_month'].min()))
        end_month = str(int(df['trade_month'].max()))
        report_date = datetime.now().strftime('%Y-%m-%d %H:%M')
        now_ts = datetime.now().strftime('%Y%m%d_%H%M%S')

        pdf_path = os.path.join(
            self.REPORT_DIR,
            f"MacroEconomy_Indicator_Report_{start_month}-{end_month}_{now_ts}.pdf"
        )

        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=landscape(A4),
            rightMargin=60, leftMargin=60,
            topMargin=50, bottomMargin=30,
        )
        page_width = landscape(A4)[0] - 120

        story = []

        # ===== 封面 =====
        story.append(Spacer(1, 1.8 * inch))
        story.append(Paragraph('宏观经济指标环比分析报告', styles['title']))
        story.append(Spacer(1, 0.3 * inch))
        story.append(Paragraph(
            'Macro Economic Indicator MoM Analysis Report',
            ParagraphStyle('Sub', parent=styles['normal'], alignment=1,
                           fontSize=11, textColor=colors.HexColor('#888888'),
                           fontName=self.reportlab_font),
        ))
        story.append(Spacer(1, 0.4 * inch))
        cover_text = (
            f"数据区间：{start_month} — {end_month}<br/>"
            f"生成时间：{report_date}<br/>"
            f"覆盖指标：{len(self.ALL_PCT_FIELDS)} 项环比增幅指标<br/>"
            f"数据记录：{len(df)} 条月度数据<br/>"
            f"<br/>INFINITY 量化系统 · 内部研究专用"
        )
        story.append(Paragraph(cover_text, styles['cover_info']))
        story.append(PageBreak())

        # ===== 综述 =====
        summary = self._get_summary(df)
        self._add_text_section(story, '一、宏观经济指标环比分析 综述', summary, styles)
        story.append(PageBreak())

        # ===== 图表 + 分析 =====
        chart_config = [
            ('chart1_all', '图1：宏观经济指标环比增幅全景',
             self._get_chart1_analysis, '二、'),
            ('chart2_money_raw', '图2：货币供应量 M1/M2 与 CPI/PPI/PMI 同比（原始值）',
             self._get_chart2_analysis, '三、'),
            ('chart3_money_pct', '图3：货币供应量 M1/M2 与 CPI/PPI/PMI 环比增幅',
             self._get_chart3_analysis, '四、'),
            ('chart4_forex_raw', '图4：外汇储备 & 黄金储备 & 黄金期货GC（原始值）',
             self._get_chart4_analysis, '五、'),
            ('chart5_forex_pct', '图5：外汇储备 & 黄金储备 & 黄金期货GC 环比增幅',
             self._get_chart5_analysis, '六、'),
            ('chart6_yields_raw', '图6：国债收益率 / GDP同比 / CPI同比（原始值）',
             self._get_chart6_analysis, '七、'),
            ('chart7_yields_pct', '图7：国债收益率 / GDP同比 / CPI同比 环比增幅',
             self._get_chart7_analysis, '八、'),
            ('chart8_trade_raw', '图8：进出口同比（原始值）',
             self._get_chart8_analysis, '九、'),
            ('chart9_trade_pct', '图9：进出口同比 环比增幅',
             self._get_chart9_analysis, '十、'),
            ('chart10_financing_raw', '图10：社会融资分项（原始值）',
             self._get_chart10_analysis, '十一、'),
            ('chart11_financing_pct', '图11：社会融资分项 环比增幅',
             self._get_chart11_analysis, '十二、'),
            ('chart12_market_raw', '图12：全球主要股指收盘价（原始值）',
             self._get_chart12_analysis, '十三、'),
            ('chart13_market_pct', '图13：全球主要股指 环比增幅',
             self._get_chart13_analysis, '十四、'),
            ('chart14_heatmap_raw', '图14：指标原始值 相关系数热力图',
             self._get_chart14_analysis, '十五、'),
            ('chart15_heatmap_pct', '图15：指标环比增幅 相关系数热力图',
             self._get_chart15_analysis, '十六、'),
            ('chart16_pca', '图16：PCA 主成分分析（基于环比增幅）',
             self._get_pca_analysis, '十七、'),
            ('chart17_rolling_corr', '图17：滚动相关性分析（12个月窗口）',
             self._get_rolling_corr_analysis, '十八、'),
        ]

        for i, (buf_key, chart_title, analysis_fn, section_label) in enumerate(chart_config):
            buf = chart_buffers.get(buf_key)
            if buf is None:
                continue

            # 图
            story.append(Paragraph(f'{section_label} {chart_title}', styles['h1']))
            story.append(Spacer(1, 0.1 * inch))
            img = RLImage(buf, width=page_width, height=page_width * 0.52)
            story.append(img)
            story.append(Spacer(1, 0.15 * inch))

            # 文字分析
            analysis_lines = analysis_fn(df)
            if analysis_lines:
                self._add_text_section(story, f'{section_label}.1 专业分析', analysis_lines, styles)

            story.append(PageBreak())

        # ===== 滚动相关系数分解图（每对一张独立图表）=====
        if rolling_pair_charts:
            story.append(Paragraph('十九、滚动相关系数分解图', styles['h1']))
            story.append(Spacer(1, 0.1 * inch))
            story.append(Paragraph(
                '以下展示所有|r|≥0.3的指标对的12个月滚动相关系数时变特征。'
                '灰色虚线标记静态相关系数，绿色/红色虚线标记±0.7参考线。',
                ParagraphStyle('Note', parent=styles['normal'], fontSize=9,
                               textColor=colors.HexColor('#555555'))
            ))
            story.append(Spacer(1, 0.15 * inch))
            for i, (buf_key, pair_title, pair_buf) in enumerate(rolling_pair_charts):
                sub_num = i + 1
                story.append(Paragraph(f'图18.{sub_num}: {pair_title} 滚动相关系数', styles['h2']))
                img = RLImage(pair_buf, width=page_width, height=page_width * 0.30)
                story.append(img)
                story.append(Spacer(1, 0.12 * inch))
            story.append(PageBreak())

        # ===== AI 分析 =====
        if ai_analysis:
            story.append(Paragraph('二十、AI 宏观分析师：年度截面数据专业分析', styles['h1']))
            story.append(Spacer(1, 0.15 * inch))
            for line in ai_analysis.strip().split('\n'):
                if line.strip():
                    story.append(Paragraph(line.strip(), styles['normal']))
        story.append(PageBreak())

        # ===== 风险提示 =====
        story.append(Paragraph('二十一、风险提示', styles['h1']))
        story.append(Spacer(1, 0.15 * inch))
        risk_text = (
            "本报告基于历史宏观经济数据进行量化分析，仅供参考，不构成投资建议。"
            "宏观经济指标受政策调整、国际环境、市场情绪等多重因素影响，历史规律不代表未来表现。"
            "建议投资者结合自身情况，进行独立判断和决策。"
        )
        story.append(Paragraph(risk_text, styles['normal']))

        doc.build(story)
        logger.info(f"✅ PDF 报告已生成: {pdf_path}")
        return pdf_path

    # ===================== 主流程 =====================

    def run(self):
        """运行宏观经济指标报告生成主流程"""
        self.job_logger.start_job('MacroEconomicIndicatorReport', 'MacroEconomy', params={})

        self.writeLogInfo(className=self.__class__.__name__,
                          functionName="run",
                          event="Starting Macro Economy Indicator Report generation")

        try:
            # Step 1: 拉取数据
            logger.info("=" * 60)
            logger.info("Step 1/4: 从 ClickHouse 拉取数据")
            logger.info("=" * 60)
            df = self.fetch_data()
            if df.empty:
                logger.warning("数据为空，流程终止")
                self.job_logger.end_job_failed("数据为空")
                return None

            # Step 2: 数据清洗
            logger.info("=" * 60)
            logger.info("Step 2/4: 数据清洗（缺失值/0值前向填充）")
            logger.info("=" * 60)
            df = self.clean_data(df)

            # Step 3: 生成图表（BytesIO）+ 专业分析 + AI 分析
            logger.info("=" * 60)
            logger.info("Step 3/4: 生成15张图表 + 2张进阶分析图 & 专业分析 & AI 分析")
            logger.info("=" * 60)

            chart_buffers = {}

            # 图1: 全部PCT全景
            chart_buffers['chart1_all'] = self.gen_chart1_all_pct(df)

            # 图2-3: M1/M2 原始值 + 环比
            chart_buffers['chart2_money_raw'] = self.gen_chart2_money_raw(df)
            chart_buffers['chart3_money_pct'] = self.gen_chart3_money_pct(df)

            # 图4-5: 外汇/黄金 原始值 + 环比
            chart_buffers['chart4_forex_raw'] = self.gen_chart4_forex_raw(df)
            chart_buffers['chart5_forex_pct'] = self.gen_chart5_forex_pct(df)

            # 图6-7: 国债/GDP/CPI 原始值 + 环比
            chart_buffers['chart6_yields_raw'] = self.gen_chart6_yields_raw(df)
            chart_buffers['chart7_yields_pct'] = self.gen_chart7_yields_pct(df)

            # 图8-9: 进出口 原始值 + 环比
            chart_buffers['chart8_trade_raw'] = self.gen_chart8_trade_raw(df)
            chart_buffers['chart9_trade_pct'] = self.gen_chart9_trade_pct(df)

            # 图10-11: 融资分项 原始值 + 环比
            chart_buffers['chart10_financing_raw'] = self.gen_chart10_financing_raw(df)
            chart_buffers['chart11_financing_pct'] = self.gen_chart11_financing_pct(df)

            # 图12-13: 全球主要股指 原始值 + 环比
            chart_buffers['chart12_market_raw'] = self.gen_chart12_market_raw(df)
            chart_buffers['chart13_market_pct'] = self.gen_chart13_market_pct(df)

            # 图14-15: 热力图
            chart_buffers['chart14_heatmap_raw'] = self.gen_chart14_heatmap_raw(df)
            chart_buffers['chart15_heatmap_pct'] = self.gen_chart15_heatmap_pct(df)

            # 图16: PCA 主成分分析
            chart_buffers['chart16_pca'] = self.gen_chart16_pca(df)

            # 图17: 滚动相关性
            chart_buffers['chart17_rolling_corr'] = self.gen_chart17_rolling_corr(df)

            # 图18+: 滚动相关系数分解图（每对一张独立图表）
            rolling_pair_charts = self.gen_rolling_corr_pair_charts(df)

            chart_count = sum(1 for v in chart_buffers.values() if v is not None)
            logger.info(f"Charts generated: {chart_count}/{17 + len(rolling_pair_charts)}")

            # AI 分析
            ai_analysis = self._generate_ai_macro_analysis(df)
            if ai_analysis:
                logger.info("✅ AI 宏观经济分析报告生成成功")

            # Step 4: 生成 PDF（不保存中间图片）
            logger.info("=" * 60)
            logger.info("Step 4/4: 生成 PDF 报告")
            logger.info("=" * 60)
            pdf_path = self._generate_pdf_report(df, chart_buffers, ai_analysis, rolling_pair_charts)

            logger.info("\n" + "=" * 80)
            logger.info("✅ 宏观经济指标环比分析报告 生成完成！")
            logger.info(f"   Report: {pdf_path}")
            logger.info(f"   Data rows: {len(df)}")
            logger.info(f"   Charts: {chart_count} 张")
            logger.info("=" * 80)

            self.job_logger.end_job_success(records_processed=len(df))
            return pdf_path

        except Exception as e:
            import traceback
            logger.error(f"报告生成失败: {e}")
            logger.error(traceback.format_exc())
            self.job_logger.end_job_failed(str(e), traceback.format_exc())
            raise


if __name__ == "__main__":
    report = MacroEconomicIndicatorReport()
    report.run()

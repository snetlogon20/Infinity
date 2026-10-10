r"""
Put-Call Parity（期权平价关系）监控 PDF 报告生成器 — 资深交易员/风控视角

数据源：
    tb_option_pcp_monitor（由 OptionPutCallParityMonitor 写入，
    含 pcp_deviation / z_score / dividend_contribution / alert_level 等监控指标）

报告结构：
    封面 → 数据概览(数字) → 最新交易日监控明细(表格, 按 |z| 降序) → 4张图表(各配数字说明)
    → 资深交易员综合点评(自动生成, 含数字) → 指标口径 → 风险提示

核心图表：
    图1 PCP 偏差时序（按标的聚合的日均值 ε，0 轴参考线）
    图2 z-score 时序（±2σ WARNING / ±3σ ALERT 参考线）
    图3 告警汇总（按交易日堆叠柱：NORMAL / WARNING / ALERT）
    图4 股息噪声分解（股息贡献 vs 残差散点，按偏差类型着色）

输出：
    PDF → CommonParameters.optionAnalysisReportPath
    (D:\workspace_python\infinity_data\outbound\report\OptionAnalysis)

前置条件：
    先运行 OptionPutCallParityMonitorTest（OptionPutCallParityMonitor.run）落库监控数据。

报告窗口：
    默认回看 90 天（约 60 个交易日）——覆盖一个完整季月合约周期与分红季节点，
    便于区分"季节性噪声"与"真实错价"；监控端滚动统计仍为 20 交易日。
"""

import io
import os
import traceback
from datetime import datetime, timedelta

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
                                 PageBreak, Table, TableStyle)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.common.ReportJobLogger import ReportJobLogger
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

logger = CommonLib.logger

# 中文字体支持（matplotlib）
# 注意：font.sans-serif 是按顺序取第一个「可用」字体（非逐字形回退），
# SimHei 缺少 U+2212（真减号 −）字形，一旦被选中，图内公式的减号会渲染成方框（tofu）。
# 微软雅黑同时覆盖中文、希腊字母（ε/σ/μ）与 −/±/× 等符号，故置于首位。
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
# 图内数学公式统一走 mathtext（DejaVu 数学字形），彻底规避中文字体缺字形问题
plt.rcParams['mathtext.fontset'] = 'dejavusans'


class OptionPutCallParityReport:
    """Put-Call Parity 监控 报告生成器"""

    REPORT_DIR = CommonParameters.optionAnalysisReportPath
    TABLE_SOURCE = 'tb_option_pcp_monitor'
    # 合约基础信息快照：ts_code → 实际合约名称 name（ETF 期权 ts_code 为 8 位数字无语义）
    TABLE_BASIC = 'df_tushare_opt_basic'

    # 报告默认回看窗口（天）——专业交易员视角：覆盖一个季月合约周期 + 分红季节点
    DEFAULT_LOOKBACK_DAYS = 90
    # 明细表默认展示条数（按 |z| 降序）
    DETAIL_TABLE_ROWS = 15

    CHART_COLORS = [
        '#e74c3c', '#3498db', '#2ecc71', '#9b59b6', '#f39c12',
        '#1abc9c', '#e67e22', '#2980b9', '#c0392b', '#27ae60',
    ]

    # 告警/偏差类型配色（与监控端语义一致）
    ALERT_COLORS = {'NORMAL': '#2ecc71', 'WARNING': '#f39c12', 'ALERT': '#e74c3c'}
    TYPE_COLORS = {'NORMAL': '#95a5a6', 'DIVIDEND_NOISE': '#3498db',
                    'REAL_ARBITRAGE': '#e67e22', 'STRONG_ARBITRAGE': '#c0392b'}

    def __init__(self):
        os.makedirs(self.REPORT_DIR, exist_ok=True)
        self.reportlab_font = self._register_chinese_font()
        # 合约名称映射（run 时从 opt_basic 快照加载）
        self._contract_name_map = {}
        self._underlying_display_map = {}

    def _register_chinese_font(self):
        """注册 reportlab 中文字体"""
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
        logger.info("%s.%s: %s" % (className, functionName, event))

    # ===================== 通用工具 =====================

    @staticmethod
    def _fmt(val, fmt='{:.4g}'):
        """数值安全格式化（NaN/None → N/A）"""
        try:
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return 'N/A'
            return fmt.format(val)
        except Exception:
            return 'N/A'

    def _fig_to_bytesio(self, fig, dpi=160):
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        return buf

    # ===================== 数据获取 =====================

    def fetch_data(self, start_date=None, end_date=None, underlying_code=None):
        """从 tb_option_pcp_monitor 拉取 PCP 监控结果"""
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName="fetch_data",
                          event=f"Fetching data from {self.TABLE_SOURCE}")

        where_clauses = []
        if start_date:
            where_clauses.append(f"trade_date >= '{start_date}'")
        if end_date:
            where_clauses.append(f"trade_date <= '{end_date}'")
        if underlying_code:
            where_clauses.append(f"underlying_code = '{underlying_code}'")

        where_str = (" AND ".join(where_clauses)) if where_clauses else "1=1"
        sql = f"""
        SELECT *
        FROM indexsysdb.{self.TABLE_SOURCE}
        WHERE {where_str}
        ORDER BY trade_date, underlying_code, exercise_price, maturity_date
        """
        logger.info(f"SQL:\n{sql}")
        df = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        logger.info(f"Fetched {len(df)} rows, {len(df.columns)} columns")
        return df

    def clean_data(self, df):
        """类型转换与派生列（pair_key = "K/到期日" 作为配对唯一标识）"""
        numeric_cols = [
            'exercise_price', 'days_to_maturity',
            'call_settle', 'put_settle', 'spot_price', 'risk_free_rate', 'dividend_yield',
            'pcp_deviation', 'pcp_deviation_pct', 'pcp_theoretical_put',
            'rolling_mean', 'rolling_std', 'z_score',
            'dividend_q_std', 'dividend_contribution', 'residual_deviation',
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        for col in ['trade_date', 'underlying_code', 'maturity_date',
                    'alert_level', 'deviation_type', 'call_ts_code', 'put_ts_code']:
            if col in df.columns:
                df[col] = df[col].fillna('').astype(str)

        # 配对唯一标识："K/到期日"（如 "2.75/2606"）
        if 'exercise_price' in df.columns:
            df['pair_key'] = (df['exercise_price'].map(lambda v: f'{v:.4g}') + '/'
                              + df['maturity_date'])
        else:
            df['pair_key'] = ''

        df = df.sort_values(['trade_date', 'underlying_code', 'exercise_price']).reset_index(drop=True)
        df['trade_date_dt'] = pd.to_datetime(df['trade_date'], format='%Y%m%d', errors='coerce')
        return df

    # ===================== 合约名称映射（opt_basic.name） =====================

    def _load_contract_names(self):
        """从 opt_basic 最新快照加载 ts_code → 实际合约名称 name 映射

        ETF 期权 ts_code 为 8 位数字（无语义），name 列才是可读合约名
        （如 50ETF购12月2750），用于 PDF 中以实际名称替代原始代码。
        """
        sql = f"""
        SELECT ts_code, argMax(name, trade_date) AS name
        FROM indexsysdb.{self.TABLE_BASIC}
        GROUP BY ts_code
        """
        logger.info(f"SQL:\n{sql}")
        try:
            df_basic = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        except Exception as e:
            logger.warning(f"Failed to load contract names from {self.TABLE_BASIC}: {e}, "
                           f"PDF will show raw ts_code")
            return {}
        if df_basic is None or len(df_basic) == 0:
            logger.warning(f"{self.TABLE_BASIC} snapshot is empty, "
                           f"PDF will show raw ts_code")
            return {}
        name_map = {str(row['ts_code']): str(row['name'] or '')
                    for _, row in df_basic.iterrows()}
        logger.info(f"Loaded names for {len(name_map)} contracts from {self.TABLE_BASIC}")
        return name_map

    def _contract_display(self, ts_code):
        """ts_code → 实际合约名称（opt_basic.name），找不到时回退原代码"""
        ts_code = str(ts_code or '').strip()
        return self._contract_name_map.get(ts_code, '') or ts_code

    def _underlying_display(self, underlying_code, call_ts_code=''):
        """标的代码 → 可读名称（从合约名截取"购/沽"前的标的简称）

        如 name='50ETF购12月2750' → '50ETF(510050.SH)'；解析失败回退原代码。
        """
        underlying_code = str(underlying_code or '')
        name = self._contract_name_map.get(str(call_ts_code or '').strip(), '')
        for sep in ('购', '沽'):
            if sep in name:
                head = name.split(sep)[0].strip()
                if head:
                    return f"{head}({underlying_code})"
        return underlying_code

    def _build_underlying_display_map(self, df):
        """underlying_code → 可读标的名称（取该标的任一非空 Call 合约的 name 截取）"""
        display_map = {}
        if 'call_ts_code' in df.columns and 'underlying_code' in df.columns:
            non_empty = df[df['call_ts_code'] != '']
            if len(non_empty) > 0:
                first_call = non_empty.groupby('underlying_code')['call_ts_code'].first()
                for uc, tc in first_call.items():
                    display_map[uc] = self._underlying_display(uc, tc)
        return display_map

    # ===================== 统计辅助 =====================

    def _latest_snapshot(self, df):
        """最新交易日的数据切片"""
        latest_date = df['trade_date'].max()
        return latest_date, df[df['trade_date'] == latest_date]

    def _daily_by_underlying(self, df, value_col):
        """按 (trade_date, underlying_code) 聚合 value_col 日均值 → {uc: Series}"""
        out = {}
        for uc, grp in df.groupby('underlying_code'):
            s = grp.groupby('trade_date_dt')[value_col].mean().dropna().sort_index()
            if len(s) > 0:
                out[uc] = s
        return out

    def _build_overview_numbers(self, df):
        """数据概览统计（资深交易员关注的关键数字）"""
        latest_date, latest = self._latest_snapshot(df)
        trade_dates = sorted(df['trade_date'].unique())

        eps_latest = latest['pcp_deviation'].dropna()
        z_latest = latest['z_score'].dropna()

        stats = {
            'date_start': trade_dates[0] if trade_dates else 'N/A',
            'date_end': trade_dates[-1] if trade_dates else 'N/A',
            'n_days': len(trade_dates),
            'n_rows': len(df),
            'n_underlyings': df['underlying_code'].nunique(),
            'n_pairs': df['pair_key'].nunique(),
            'latest_date': latest_date,
            'n_pairs_latest': len(latest),
            'eps_mean': eps_latest.mean() if len(eps_latest) else np.nan,
            'eps_absmax': eps_latest.abs().max() if len(eps_latest) else np.nan,
            'eps_pct_absmax': latest['pcp_deviation_pct'].abs().max()
                if len(latest) else np.nan,
            'z_absmax': z_latest.abs().max() if len(z_latest) else np.nan,
            'z_gt2_count': int((z_latest.abs() >= 2).sum()) if len(z_latest) else 0,
            'z_gt3_count': int((z_latest.abs() >= 3).sum()) if len(z_latest) else 0,
            'alert_counts': latest['alert_level'].value_counts().to_dict()
                if len(latest) else {},
            'type_counts': latest['deviation_type'].value_counts().to_dict()
                if len(latest) else {},
            'alert_counts_period': df['alert_level'].value_counts().to_dict(),
        }
        return stats

    # ===================== 图表生成 =====================

    def gen_chart1_deviation_timeseries(self, df):
        """图1：PCP 偏差时序（按标的聚合的日均值 ε）"""
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName="gen_chart1",
                          event="Generating chart 1: PCP deviation timeseries")

        daily = self._daily_by_underlying(df, 'pcp_deviation')
        if not daily:
            logger.warning("No valid data for chart 1, skipping")
            return None

        fig, ax = plt.subplots(figsize=(20, 8))
        # 公式用 mathtext（DejaVu 数学字形）渲染，避免中文字体缺失 − 等符号
        fig.suptitle(r'图1：PCP 偏差日均值时序 $\varepsilon = P - C - K\,e^{-rT} + S\,e^{-qT}$',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        for idx, (uc, s) in enumerate(sorted(daily.items())):
            color = self.CHART_COLORS[idx % len(self.CHART_COLORS)]
            disp = self._underlying_display_map.get(uc, uc)
            ax.plot(s.index.tolist(), s.values, color=color, linewidth=1.6,
                    marker='o', markersize=3, alpha=0.9, label=disp)
            ax.annotate(disp, xy=(s.index[-1], s.iloc[-1]), xytext=(6, 0),
                       textcoords='offset points', color=color, fontsize=8,
                       fontweight='bold', va='center', ha='left',
                       bbox=dict(boxstyle='round,pad=0.18', facecolor='white',
                                 edgecolor=color, linewidth=0.5, alpha=0.85))

        ax.axhline(y=0, color='#1a1a2e', linewidth=1.2, linestyle='-')
        ax.text(0.005, 0, '理论平价（ε=0）', transform=ax.get_yaxis_transform(),
                fontsize=7.5, color='#1a1a2e', va='bottom')
        ax.set_ylabel('ε（日均值，元/单位）', fontsize=11)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10),
                  fontsize=8, ncol=min(len(daily), 8), frameon=True)
        fig.autofmt_xdate(rotation=45, ha='right')
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    def gen_chart2_zscore_timeseries(self, df):
        """图2：z-score 时序（±2σ WARNING / ±3σ ALERT 参考线）"""
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName="gen_chart2",
                          event="Generating chart 2: z-score timeseries")

        daily = self._daily_by_underlying(df, 'z_score')
        if not daily:
            logger.warning("No valid data for chart 2, skipping")
            return None

        fig, ax = plt.subplots(figsize=(20, 8))
        fig.suptitle('图2：PCP 偏差 z-score 日均值时序（20日滚动基准）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        for idx, (uc, s) in enumerate(sorted(daily.items())):
            color = self.CHART_COLORS[idx % len(self.CHART_COLORS)]
            disp = self._underlying_display_map.get(uc, uc)
            ax.plot(s.index.tolist(), s.values, color=color, linewidth=1.4,
                    marker='o', markersize=3, alpha=0.85, label=disp)
            ax.annotate(disp, xy=(s.index[-1], s.iloc[-1]), xytext=(6, 0),
                       textcoords='offset points', color=color, fontsize=8,
                       fontweight='bold', va='center', ha='left',
                       bbox=dict(boxstyle='round,pad=0.18', facecolor='white',
                                 edgecolor=color, linewidth=0.5, alpha=0.85))

        # 告警阈值参考线
        for y_val, clr, txt in [(2, '#f39c12', '+2σ WARNING'), (-2, '#f39c12', '-2σ WARNING'),
                                (3, '#e74c3c', '+3σ ALERT'), (-3, '#e74c3c', '-3σ ALERT')]:
            ax.axhline(y=y_val, color=clr, linewidth=1.2, linestyle='--', alpha=0.8)
            ax.text(0.005, y_val, txt, transform=ax.get_yaxis_transform(),
                    fontsize=7.5, color=clr, va='bottom')
        ax.axhline(y=0, color='gray', linewidth=0.6, alpha=0.6)

        ax.set_ylabel('z-score（日均值）', fontsize=11)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10),
                  fontsize=8, ncol=min(len(daily), 8), frameon=True)
        fig.autofmt_xdate(rotation=45, ha='right')
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    def gen_chart3_alert_summary(self, df):
        """图3：告警汇总（按交易日堆叠柱：NORMAL / WARNING / ALERT）"""
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName="gen_chart3",
                          event="Generating chart 3: alert summary")

        if 'alert_level' not in df.columns or df['alert_level'].dropna().empty:
            logger.warning("No valid data for chart 3, skipping")
            return None

        pivot = df.pivot_table(index='trade_date_dt', columns='alert_level',
                               values='pcp_deviation', aggfunc='count').fillna(0)
        levels = [lv for lv in ['NORMAL', 'WARNING', 'ALERT'] if lv in pivot.columns]
        if not levels:
            logger.warning("No valid alert levels for chart 3, skipping")
            return None
        pivot = pivot.sort_index()

        fig, ax = plt.subplots(figsize=(20, 8))
        fig.suptitle('图3：告警配对数量汇总（按交易日，堆叠柱）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        bottom = np.zeros(len(pivot))
        x = pivot.index.tolist()
        for lv in levels:
            vals = pivot[lv].values
            ax.bar(x, vals, bottom=bottom, width=0.8,
                   color=self.ALERT_COLORS.get(lv, '#7f8c8d'),
                   label=lv, alpha=0.85)
            bottom += vals

        ax.set_ylabel('配对数量', fontsize=11)
        ax.grid(True, alpha=0.3, linestyle='--', axis='y')
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10),
                  fontsize=9, ncol=len(levels), frameon=True)
        fig.autofmt_xdate(rotation=45, ha='right')
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    def gen_chart4_dividend_decomposition(self, df):
        """图4：股息噪声分解（股息贡献 vs 残差散点，按偏差类型着色）"""
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName="gen_chart4",
                          event="Generating chart 4: dividend decomposition")

        sub = df.dropna(subset=['dividend_contribution', 'residual_deviation'])
        if len(sub) == 0:
            logger.warning("No valid data for chart 4, skipping")
            return None

        fig, ax = plt.subplots(figsize=(20, 8))
        fig.suptitle('图4：股息噪声分解（股息贡献 vs 剥离后残差）',
                     fontsize=14, fontweight='bold', color='#1a1a2e')

        for dt_type, grp in sub.groupby('deviation_type'):
            ax.scatter(grp['dividend_contribution'], grp['residual_deviation'],
                       s=18, alpha=0.55, color=self.TYPE_COLORS.get(dt_type, '#7f8c8d'),
                       label=f"{dt_type} ({len(grp)})", edgecolors='none')

        ax.axhline(y=0, color='gray', linewidth=0.8, linestyle='-', alpha=0.7)
        ax.axvline(x=0, color='gray', linewidth=0.8, linestyle='-', alpha=0.7)
        ax.set_xlabel('股息噪声贡献 = S × T × σ_q（元/单位）', fontsize=11)
        ax.set_ylabel('残差 ε_residual（剥离股息噪声后，元/单位）', fontsize=11)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.10),
                  fontsize=9, ncol=4, frameon=True)
        plt.tight_layout()
        return self._fig_to_bytesio(fig)

    # ===================== 明细表与点评 =====================

    def _build_detail_table_data(self, latest):
        """最新交易日监控明细表数据（按 |z| 降序 Top N）"""
        cand = latest.copy()
        if 'z_score' in cand.columns:
            cand = cand.reindex(cand['z_score'].abs().sort_values(ascending=False).index)
        cand = cand.head(self.DETAIL_TABLE_ROWS)

        rows = []
        for _, r in cand.iterrows():
            rows.append([
                str(r.get('trade_date', '')),
                self._underlying_display(r.get('underlying_code', ''),
                                         r.get('call_ts_code', '')),
                self._fmt(r.get('exercise_price'), '{:.4g}'),
                str(r.get('maturity_date', '')),
                self._fmt(r.get('days_to_maturity'), '{:.0f}'),
                self._fmt(r.get('pcp_deviation'), '{:+.4g}'),
                self._fmt(r.get('pcp_deviation_pct'), '{:+.2f}'),
                self._fmt(r.get('z_score'), '{:+.2f}'),
                self._fmt(r.get('dividend_contribution'), '{:.4g}'),
                self._fmt(r.get('residual_deviation'), '{:+.4g}'),
                str(r.get('alert_level', '')),
                str(r.get('deviation_type', '')),
                self._contract_display(r.get('call_ts_code', '')),
                self._contract_display(r.get('put_ts_code', '')),
            ])
        header = ['交易日', '标的', 'K', '到期日', '剩余天数', 'ε', 'ε%', 'z-score',
                  '股息贡献', '残差', '告警', '偏差类型', 'Call合约', 'Put合约']
        return header, rows

    def _build_trader_commentary(self, df, stats):
        """资深交易员综合点评（基于数据自动生成，含具体数字）"""
        _, latest = self._latest_snapshot(df)
        paras = []

        # ---- 1. 平价偏离环境 ----
        eps_absmax = stats['eps_absmax']
        eps_mean = stats['eps_mean']
        if pd.notna(eps_absmax) and pd.notna(eps_mean):
            paras.append(('平价偏离环境判断',
                          f"最新交易日（{stats['latest_date']}）{stats['n_pairs_latest']} 个配对中，"
                          f"偏差绝对值均值 {abs(eps_mean):.4g} 元/单位，"
                          f"极值 {eps_absmax:.4g} 元/单位"
                          f"（占标的价格 {self._fmt(stats['eps_pct_absmax'], '{:.2f}')}%）。"
                          f"理论上 ETF 期权为欧式、无提前行权摩擦，若剔除股息估计误差后残差仍持续为正，"
                          f"通常指向深实值合约流动性折价或结算价失真，而非可执行套利。"))

        # ---- 2. 告警结构解读 ----
        alert_counts = stats['alert_counts']
        n_warn = alert_counts.get('WARNING', 0)
        n_alert = alert_counts.get('ALERT', 0)
        type_counts = stats['type_counts']
        n_noise = type_counts.get('DIVIDEND_NOISE', 0)
        n_real = type_counts.get('REAL_ARBITRAGE', 0)
        n_strong = type_counts.get('STRONG_ARBITRAGE', 0)
        if n_warn + n_alert > 0:
            if n_noise >= (n_real + n_strong):
                verdict = ("告警以股息噪声为主——分红季前后 σ_q 估计不稳是主因，"
                           "属于监控模型的已知盲区而非市场错价，可保持观察频率不变。")
            else:
                verdict = ("告警以真实错价为主——建议核对成交与买卖盘宽度后再下结论；"
                           "ETF 期权欧式结构下真实套利空间通常被交易成本吞噬，"
                           "持续存在的残差更多提示数据质量或流动性问题。")
            paras.append(('告警结构解读',
                          f"最新交易日 WARNING {n_warn} 个、ALERT {n_alert} 个；"
                          f"分类后：股息噪声 {n_noise}、真实套利 {n_real}、强套利 {n_strong}。{verdict}"))
        else:
            paras.append(('告警结构解读',
                          f"最新交易日无任何配对越过 ±2σ 阈值——平价关系维持良好，"
                          f"市场定价效率正常（全区间累计告警 "
                          f"{stats['alert_counts_period'].get('WARNING', 0) + stats['alert_counts_period'].get('ALERT', 0)} 个）。"))

        # ---- 3. z-score 分布 ----
        z_absmax = stats['z_absmax']
        if pd.notna(z_absmax):
            paras.append(('z-score 分布',
                          f"最新 |z| 极值 {z_absmax:.2f}σ，"
                          f"越过 ±2σ 的配对 {stats['z_gt2_count']} 个"
                          f"（占比 {stats['z_gt2_count'] / max(stats['n_pairs_latest'], 1) * 100:.1f}%），"
                          f"越过 ±3σ 的 {stats['z_gt3_count']} 个。"
                          f"滚动基准为 20 日窗口的 μ/σ，注意分红季（股指 5~7 月、ETF 11~12 月）"
                          f"σ_q 抬升会使 z 系统性收敛，属正常现象。"))

        # ---- 4. 数据质量与流动性提醒 ----
        eps_pct_absmax = stats['eps_pct_absmax']
        if pd.notna(eps_pct_absmax) and eps_pct_absmax > 5:
            paras.append(('数据质量与流动性提醒',
                          f"最新交易日最大 |ε%| 高达 {eps_pct_absmax:.2f}%——"
                          f"深度实值/远月合约结算价失真的典型特征。"
                          f"建议将监控端 MIN_VOLUME 从 10 上调至 100 以上，"
                          f"或对 |ε%|>5% 的配对单独标注（数据质量原因），避免污染告警统计。"))

        return paras

    # ===================== PDF 样式与组装 =====================

    def _build_pdf_styles(self):
        styles = getSampleStyleSheet()
        return {
            'title': ParagraphStyle('ReportTitle', parent=styles['Heading1'],
                                    fontSize=22, leading=30, alignment=1,
                                    fontName=self.reportlab_font, spaceAfter=24),
            'h1': ParagraphStyle('H1', parent=styles['Heading1'], fontSize=16, leading=22,
                                 fontName=self.reportlab_font, spaceAfter=10, spaceBefore=10),
            'normal': ParagraphStyle('Normal', parent=styles['Normal'], fontSize=10,
                                     leading=15, fontName=self.reportlab_font),
            'cover_info': ParagraphStyle('CoverInfo', parent=styles['Normal'], fontSize=13,
                                         leading=20, alignment=1, fontName=self.reportlab_font,
                                         textColor=colors.HexColor('#333333')),
            'table_note': ParagraphStyle('TableNote', parent=styles['Normal'], fontSize=8,
                                         leading=11, fontName=self.reportlab_font,
                                         textColor=colors.HexColor('#666666')),
        }

    def _make_table(self, header, rows, col_widths=None, font_size=6.5):
        """构建统一样式的 reportlab 表格（告警列着色）"""
        data = [header] + rows
        table = Table(data, colWidths=col_widths, repeatRows=1)
        style_cmds = [
            ('FONTNAME', (0, 0), (-1, -1), self.reportlab_font),
            ('FONTSIZE', (0, 0), (-1, -1), font_size),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#D9D9D9')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.white, colors.HexColor('#EBF1F8')]),
        ]
        # 告警列（倒数第 3 列）着色
        if '告警' in header:
            alert_col = header.index('告警')
            alert_color = {'NORMAL': '#E8F5E9', 'WARNING': '#FFEB9C', 'ALERT': '#FFC7CE'}
            for ri, row in enumerate(rows, start=1):
                cell_bg = alert_color.get(str(row[alert_col]).strip())
                if cell_bg:
                    style_cmds.append(('BACKGROUND', (alert_col, ri), (alert_col, ri),
                                       colors.HexColor(cell_bg)))
        table.setStyle(TableStyle(style_cmds))
        return table

    def _generate_pdf_report(self, df, chart_buffers, config):
        styles = self._build_pdf_styles()
        stats = self._build_overview_numbers(df)
        latest_date, latest = self._latest_snapshot(df)

        report_date = datetime.now().strftime('%Y-%m-%d %H:%M')
        now_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        underlying_code = config.get('underlying_code')

        uc_tag = underlying_code if underlying_code else 'ALL'
        date_tag = f"{stats['date_start']}-{stats['date_end']}"
        pdf_path = os.path.join(
            self.REPORT_DIR,
            f"OptionPutCallParity_{uc_tag}_{date_tag}_{now_ts}.pdf")

        doc = SimpleDocTemplate(pdf_path, pagesize=landscape(A4),
                                rightMargin=40, leftMargin=40, topMargin=36, bottomMargin=28)
        page_width = landscape(A4)[0] - 80
        story = []

        # ===== 封面 =====
        story.append(Spacer(1, 1.4 * inch))
        story.append(Paragraph('期权平价关系监控报告', styles['title']))
        story.append(Paragraph('Put-Call Parity Monitor Report',
                               ParagraphStyle('Sub', parent=styles['normal'], alignment=1,
                                              fontSize=11, fontName=self.reportlab_font,
                                              textColor=colors.HexColor('#888888'))))
        story.append(Spacer(1, 0.35 * inch))

        uc_names = sorted(set(df['underlying_code'].dropna()))
        uc_display = '、'.join(self._underlying_display_map.get(u, u)
                              for u in uc_names[:20])
        if len(uc_names) > 20:
            uc_display += f" 等 {len(uc_names)} 个标的"

        cover_text = (
            f"监控口径：Put-Call Parity 偏差 ε = P − C − K·e^(−rT) + S·e^(−qT)<br/>"
            f"数据区间：{stats['date_start']} — {stats['date_end']}（{stats['n_days']} 个交易日）<br/>"
            f"报告生成时间：{report_date}<br/>"
            f"标的过滤：{underlying_code or '全部标的'}<br/>"
            f"数据记录：{stats['n_rows']} 条 | 监控配对：{stats['n_pairs']} 个 | 标的：{stats['n_underlyings']} 个<br/>"
            f"标的列表：{uc_display or '无'}<br/>"
            f"<br/>INFINITY 量化系统 · 期权监控研究"
        )
        story.append(Paragraph(cover_text, styles['cover_info']))
        story.append(PageBreak())

        # ===== 一、数据概览 =====
        story.append(Paragraph('一、数据概览（关键数字）', styles['h1']))
        overview_text = (
            f"本报告基于 {self.TABLE_SOURCE} 表 {stats['n_rows']} 条记录，"
            f"覆盖 {stats['date_start']} 至 {stats['date_end']} 共 {stats['n_days']} 个交易日、"
            f"{stats['n_pairs']} 个 C/P 配对（{stats['n_underlyings']} 个标的）。<br/>"
            f"最新交易日 {stats['latest_date']}：{stats['n_pairs_latest']} 个配对，"
            f"偏差绝对值均值 {abs(stats['eps_mean']):.4g} 元/单位"
            f"（若为 N/A 表示当日无有效数据），"
            f"|z| 极值 {self._fmt(stats['z_absmax'], '{:.2f}')}σ，"
            f"越过 ±2σ 的配对 {stats['z_gt2_count']} 个、±3σ 的 {stats['z_gt3_count']} 个；"
            f"告警分布：WARNING {stats['alert_counts'].get('WARNING', 0)} 个、"
            f"ALERT {stats['alert_counts'].get('ALERT', 0)} 个。"
        )
        story.append(Paragraph(overview_text, styles['normal']))
        story.append(PageBreak())

        # ===== 二、最新交易日监控明细 =====
        story.append(Paragraph(f'二、最新交易日（{latest_date}）监控明细（按 |z| 降序 Top {self.DETAIL_TABLE_ROWS}）',
                               styles['h1']))
        header, rows = self._build_detail_table_data(latest)
        n_cols = len(header)
        # 首两列（交易日/标的）与末两列（Call/Put合约实际名称）固定宽度，中间列均分
        fixed_w = 62 + 70 + 95 + 95
        rest_w = (page_width - fixed_w) / (n_cols - 4)
        col_widths = [62, 70] + [rest_w] * (n_cols - 4) + [95, 95]
        story.append(self._make_table(header, rows, col_widths))
        story.append(Spacer(1, 0.08 * inch))
        story.append(Paragraph(
            '注：ε = P − C − K·e^(−rT) + S·e^(−qT)（正=Put高估）；ε% = ε/S；'
            'z-score = (ε−μ)/σ（20日滚动基准，|z|≥2 WARNING、|z|≥3 ALERT）；'
            '股息贡献 = S×T×σ_q（σ_q 为股息率滚动标准差，最低不确定度 0.5%）；'
            '残差 = ε − sign(ε)×股息贡献（剥离股息噪声后的错价）；'
            '偏差类型：DIVIDEND_NOISE=股息噪声主导 / REAL_ARBITRAGE=真实错价 / STRONG_ARBITRAGE=强错价。'
            '标的与 Call/Put 合约列显示 df_tushare_opt_basic 快照中的实际名称（name），'
            '如 50ETF购12月2750。',
            styles['table_note']))
        story.append(PageBreak())

        # ===== 三~六、图表（各配数字说明） =====
        chart_sections = []
        if chart_buffers.get('chart1'):
            chart_sections.append(('chart1', '图1：PCP 偏差时序（按标的日均值）',
                                   f"最新 |ε| 均值 {abs(stats['eps_mean']):.4g} 元/单位、"
                                   f"极值 {stats['eps_absmax']:.4g}。0 轴为理论平价；"
                                   f"系统性偏移通常来自股息率假设与资金成本项，"
                                   f"而围绕 0 轴的宽幅震荡则多为流动性噪声。"))
        if chart_buffers.get('chart2'):
            chart_sections.append(('chart2', '图2：z-score 时序（20日滚动基准）',
                                   f"最新 |z| 极值 {self._fmt(stats['z_absmax'], '{:.2f}')}σ。"
                                   f"±2σ（橙虚线）触发 WARNING、±3σ（红虚线）触发 ALERT。"
                                   f"z 的优势在于剔除各配对的固有偏移，只捕捉'相对自身历史'的突变——"
                                   f"这是区分季节性噪声与异常错价的核心视图。"))
        if chart_buffers.get('chart3'):
            chart_sections.append(('chart3', '图3：告警汇总（按交易日堆叠柱）',
                                   "绿色=NORMAL、橙色=WARNING、红色=ALERT。"
                                   "告警集中出现在分红季（σ_q 估计不稳）或合约换月（远月流动性骤降）"
                                   "属已知模式；若非季节性时点出现大面积告警，才值得深入排查。"))
        if chart_buffers.get('chart4'):
            chart_sections.append(('chart4', '图4：股息噪声分解（贡献 vs 残差）',
                                   "横轴为股息噪声贡献（S×T×σ_q），纵轴为剥离后的残差。"
                                   "蓝色点（DIVIDEND_NOISE）集中在'贡献大、残差小'区域——"
                                   "偏差可被股息估计误差解释，无需行动；"
                                   "橙/红点（REAL/STRONG_ARBITRAGE）残差显著——"
                                   "是真正的错价候选，需结合盘口核实。"))

        for i, (key, title, note) in enumerate(chart_sections):
            section_cn = ['三', '四', '五', '六', '七', '八'][i] if i < 6 else str(i + 3)
            story.append(Paragraph(f'{section_cn}、{title}', styles['h1']))
            story.append(Spacer(1, 0.08 * inch))
            buf = chart_buffers.get(key)
            if buf is not None:
                # 按图片真实宽高比等比缩放，避免纵向压扁
                img = RLImage(buf)
                w0, h0 = float(img.imageWidth), float(img.imageHeight)
                max_h = 390
                scale = min(page_width / w0, max_h / h0)
                img.drawWidth = w0 * scale
                img.drawHeight = h0 * scale
                story.append(img)
            story.append(Spacer(1, 0.08 * inch))
            story.append(Paragraph(note, styles['normal']))
            story.append(PageBreak())

        # ===== 资深交易员综合点评 =====
        next_cn = str(len(chart_sections) + 3)
        story.append(Paragraph(f'{next_cn}、资深交易员综合点评（自动生成）', styles['h1']))
        for title, text in self._build_trader_commentary(df, stats):
            story.append(Paragraph(f'<b>{title}</b>', styles['h1']))
            story.append(Paragraph(text, styles['normal']))
            story.append(Spacer(1, 0.10 * inch))
        story.append(PageBreak())

        # ===== 指标口径 =====
        story.append(Paragraph(f'{int(next_cn) + 1}、指标口径', styles['h1']))
        glossary = (
            "PCP 偏差 ε = P − C − K·e^(−rT) + S·e^(−qT)：Put 市场价与其理论平价值之差"
            "（理论 Put = C + K·e^(−rT) − S·e^(−qT)），正=Put 高估、负=Put 低估。<br/>"
            "ε% = ε/S：占标的价格的百分比，跨标的可比。<br/>"
            "z-score = (ε − μ)/σ：μ/σ 为同配对 (标的,K,到期日) 20 交易日滚动统计，"
            "样本不足 5 日时置 NaN。<br/>"
            "股息贡献 = S × T × max(σ_q, 0.5%)：σ_q 为该标的股息率的滚动标准差——"
            "PCP 检验对 q 的估计误差天然敏感（q 每 1% 的误差 → ε 偏移 S×T×1%），"
            "此项量化'能被股息解释的部分'。<br/>"
            "残差 = ε − sign(ε)×股息贡献：剥离股息噪声后的'真实'错价。<br/>"
            "告警等级：|z|≥2 WARNING、|z|≥3 ALERT；偏差分类：股息贡献/|ε| ≥ 70% 归为 DIVIDEND_NOISE，"
            "否则 REAL_ARBITRAGE（|z|≥3 直接 STRONG_ARBITRAGE）。<br/>"
            "配对与过滤：按 (交易日, 标的, K, 到期日) 一对一配对 C/P，"
            "双腿成交量 ≥ 10 且价格有效才纳入。"
        )
        story.append(Paragraph(glossary, styles['normal']))
        story.append(Spacer(1, 0.15 * inch))

        # ===== 风险提示 =====
        story.append(Paragraph(f'{int(next_cn) + 2}、风险提示', styles['h1']))
        risk_text = (
            "本报告基于期权日线结算/收盘价与 BS 框架参数进行平价检验，仅供监控参考，不构成投资建议。<br/>"
            "结算价失真：深度实值与远月合约成交稀薄，结算价可能严重偏离可成交价，"
            "大 |ε| 多数为此类数据质量问题而非真实套利。<br/>"
            "股息率估计：σ_q 的滚动窗口仅 20 日，分红季前后系统性低估噪声；"
            "已被归类为 DIVIDEND_NOISE 的告警在换季时应重新评估。<br/>"
            "欧式假设：ETF 期权无提前行权摩擦，平价关系应严格成立；"
            "若标的为美式（如部分股指期权），提前行权权利会天然打破平价，ε 的解读需修正。<br/>"
            "交易成本：理论上 |ε| 超过双边手续费+冲击成本才有套利价值，"
            "本报告的告警阈值基于统计显著性（z-score）而非经济显著性，请勿直接作为交易信号。"
        )
        story.append(Paragraph(risk_text, styles['normal']))

        doc.build(story)
        logger.info(f"✅ PDF 报告已生成: {pdf_path}")
        return pdf_path

    # ===================== 主流程 =====================

    def run(self, config):
        """运行报告生成主流程

        Args:
            config: dict with keys:
                - name / start_date / end_date / underlying_code (optional)

        Returns:
            pdf_path or None
        """
        name = config.get('name', 'Unknown')
        underlying_code = config.get('underlying_code')

        # 默认回看 90 天（覆盖一个季月合约周期 + 分红季节点）
        end_date = config.get('end_date') or CommonParameters.today
        start_date = config.get('start_date')
        if not start_date:
            start_dt = datetime.strptime(end_date, '%Y%m%d') - timedelta(days=self.DEFAULT_LOOKBACK_DAYS)
            start_date = start_dt.strftime('%Y%m%d')

        self.writeLogInfo(className=self.__class__.__name__,
                          functionName="run",
                          event=f"Generating OptionPutCallParityReport: {name}")

        # 报表任务日志（与 BondYieldComparator 相同的 ReportJobLogger 机制）
        job_logger = ReportJobLogger()
        job_logger.start_job(self.__class__.__name__, 'OptionPCPReport',
                             params={'report_name': config.get('name'),
                                     'start_date': start_date,
                                     'end_date': end_date,
                                     'underlying_code': underlying_code})

        try:
            # Step 1: 拉取数据
            logger.info(f"Step 1/3: 拉取 {self.TABLE_SOURCE} 数据 "
                        f"(underlying_code={underlying_code}, [{start_date}, {end_date}])")
            df = self.fetch_data(start_date=start_date, end_date=end_date,
                                 underlying_code=underlying_code)
            if df.empty:
                logger.warning("数据为空（请先运行 OptionPutCallParityMonitorTest 落库），流程终止")
                job_logger.end_job_success(records_processed=0)
                return None

            # Step 2: 清洗 + 名称映射 + 图表
            logger.info("Step 2/3: 数据清洗 & 生成图表")
            df = self.clean_data(df)

            # 加载 opt_basic 实际合约名称：PDF 明细表/图表/封面均用 name 列展示
            self._contract_name_map = self._load_contract_names()
            self._underlying_display_map = self._build_underlying_display_map(df)

            chart_buffers = {}
            chart_buffers['chart1'] = self.gen_chart1_deviation_timeseries(df)
            chart_buffers['chart2'] = self.gen_chart2_zscore_timeseries(df)
            chart_buffers['chart3'] = self.gen_chart3_alert_summary(df)
            chart_buffers['chart4'] = self.gen_chart4_dividend_decomposition(df)

            chart_count = sum(1 for v in chart_buffers.values() if v is not None)
            logger.info(f"图表生成完成: {chart_count} 张")

            # Step 3: 生成 PDF
            logger.info("Step 3/3: 生成 PDF 报告")
            pdf_path = self._generate_pdf_report(df, chart_buffers, config)

            logger.info("\n" + "=" * 80)
            logger.info("✅ Put-Call Parity 监控报告 生成完成！")
            logger.info(f"   Report: {pdf_path}")
            logger.info(f"   Data rows: {len(df)}")
            logger.info(f"   Charts: {chart_count} 张")
            logger.info("=" * 80)
            job_logger.end_job_success(records_processed=len(df))

            return pdf_path

        except Exception as e:
            logger.error(f"报告生成失败: {e}")
            logger.error(traceback.format_exc())
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise


if __name__ == "__main__":
    report = OptionPutCallParityReport()
    report.run({
        "name": "期权平价关系（Put-Call Parity）监控报告",
    })

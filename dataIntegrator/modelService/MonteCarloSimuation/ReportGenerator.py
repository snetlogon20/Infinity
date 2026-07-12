"""
ReportGenerator — Generate professional PDF report for Monte Carlo simulation.
Includes: cover page, 4 charts with trader/risk-manager commentary, backtest visualization.
"""

import os
import logging
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from typing import Optional, Dict, Any

from .Visualizer import Visualizer
from dataIntegrator.common.CommonParameters import CommonParameters

# ---------------------------------------------------------------------------
# Font & style — Chinese fonts FIRST for CJK glyph coverage
# ---------------------------------------------------------------------------
matplotlib.rcParams['axes.unicode_minus'] = False
try:
    matplotlib.rcParams['font.sans-serif'] = [
        'Microsoft YaHei', 'SimHei', 'DejaVu Sans', 'Arial']
    matplotlib.rcParams['font.family'] = 'sans-serif'
except Exception:
    pass

# Default PDF output directory via CommonParameters.reportPath
_DEFAULT_PDF_OUTPUT_DIR = os.path.join(
    CommonParameters.reportPath, 'MonteCarloSimulationAnalysis')

logger = logging.getLogger(__name__)


# ======================================================================
#  Commentary content — bilingual, professional
# ======================================================================

_COMMENTARY_CHART1_TITLE = "原始数据分析 — 专家观点"

_COMMENTARY_CHART1_TRADER = (
    "1. 趋势判断\n"
    "   观察 analysis_column（涨跌幅）的波动范围及方向。若 VAR 下限持续下移，\n"
    "   表明风险在积聚，持仓需缩短止损距离。\n\n"
    "2. EMA 交叉信号\n"
    "   短周期 EMA（5/10）与长周期 EMA（20/60）的交叉方向为动量参考。\n"
    "   短 EMA 下穿长 EMA 且 VAR 同步下移 = 强看空信号。\n\n"
    "3. 交易建议\n"
    "   若当前涨跌幅接近 VAR 下限，减仓或对冲；若在 VAR 区间内波动，\n"
    "   维持正常仓位管理。\n"
    "   —— 资深交易员"
)

_COMMENTARY_CHART1_RISK = (
    "1. VAR 与 ES 的间距\n"
    "   ES（预期损失）始终在 VAR 外侧。当 ES 与 VAR 的差距扩大时，说明尾部\n"
    "   风险加重——一旦突破 VAR，损失远超 VAR 值本身。这是\"冰山风险\"的典型信号。\n\n"
    "2. 尾部风险监控\n"
    "   关注 ES 的绝对值是否超出账户可承受范围。若 ES 超出预设阈值，\n"
    "   应立即降低头寸或增加对冲。\n\n"
    "3. 风险预警\n"
    "   当 VAR 下限与 ES 差距持续扩大时，建议启动应急预案。\n"
    "   —— 风险管理专家"
)

_COMMENTARY_CHART2_TITLE = "波动率分析 — 专家观点"

_COMMENTARY_CHART2_TRADER = (
    "1. 波动率聚集效应\n"
    "   GARCH/EGARCH 的尖峰处意味着市场恐慌或重大事件冲击。\n"
    "   若当前处于波动率高位，持仓需降低杠杆以应对剧烈摆动。\n\n"
    "2. 三种波动率的差异\n"
    "   · Normal Sigma: 等权平均，反应最慢——用于基准参考。\n"
    "   · GARCH Sigma: 指数衰减加权，对近期冲击响应快。\n"
    "   · EGARCH Sigma: 额外捕获非对称效应（坏消息对波动的放大 > 好消息）。\n\n"
    "3. 非对称性预警\n"
    "   当 EGARCH >> GARCH 时，市场对下行风险定价更高——\n"
    "   这是典型的避险情绪升温信号，考虑增加对冲头寸。\n"
    "   —— 资深交易员"
)

_COMMENTARY_CHART2_RISK = (
    "1. 波动率均值回归\n"
    "   极端波动率通常回归均值。若当前波动率处于历史 90 分位以上，\n"
    "   短期可能回落，但仍需防范\"波动率持续性\"（高位持续）。\n\n"
    "2. 风险管控建议\n"
    "   波动率聚集期间，应收紧止损并降低仓位，直到波动率确认回落。\n"
    "   同时监控 EGARCH 对坏消息的过度反应，防止恐慌性抛售。\n"
    "   —— 风险管理专家"
)

_COMMENTARY_CHART3_TITLE = "预测结果分析 — 专家观点"

_COMMENTARY_CHART3_TRADER = (
    "1. 预测中枢 (P50)\n"
    "   P50 是蒙特卡罗 5000 条路径的中位数预测，代表\"最可能\"情景。\n"
    "   关注 P50 的方向（上升/下降）和幅度。\n\n"
    "2. 置信带宽度 (P10-P90 / P05-P95)\n"
    "   置信带越宽，不确定性越大。若 P10-P90 带覆盖正负区间，\n"
    "   说明方向性不明确，应降低单边仓位，考虑跨式或宽跨式期权策略。\n\n"
    "3. 预测衰减\n"
    "   越远的预测步数，置信带越宽（σ√t 法则）。\n"
    "   对 5 日后 P50 较有信心，但 P10/P90 边界已大幅扩散。\n"
    "   —— 资深交易员"
)

_COMMENTARY_CHART3_RISK = (
    "1. 尾部风险 (P01 / P05)\n"
    "   P01 代表 1% 最坏情景。若 P01 的跌幅超过保证金比例，\n"
    "   存在被强平的风险。务必确保账户权益覆盖 P01 情景。\n\n"
    "2. 极端风险预案\n"
    "   建议将 P01 作为极端风险预案，设置硬止损线，并预留充足保证金。\n"
    "   同时监控 P05 情景，确保在 5% 尾部压力下账户仍有安全边际。\n"
    "   —— 风险管理专家"
)

_COMMENTARY_CHART4_TITLE = "最终结果总览 — 专家观点"

_COMMENTARY_CHART4_TRADER = (
    "1. 历史 + 预测融合\n"
    "   橙色预测区间叠加在蓝色历史曲线上——直观对比趋势延续性。\n"
    "   若预测方向与历史趋势一致，可顺势操作；若背离，需谨慎。\n\n"
    "2. 综合交易策略\n"
    "   · 趋势 + 低波动 → 持有或加仓\n"
    "   · 趋势 + 高波动 → 减仓止损\n"
    "   · 无方向 + 高波动 → 观望或买期权\n"
    "   · 无方向 + 低波动 → 等待突破信号\n\n"
    "3. 关键行动\n"
    "   将 P10/P90 作为交易计划的参考边界，每日更新数据，滚动重估模型参数。\n"
    "   —— 资深交易员"
)

_COMMENTARY_CHART4_RISK = (
    "1. 波动率叠加\n"
    "   右轴 (EGARCH Sigma) 展示市场\"恐慌温度\"。\n"
    "   预测区间内若 Sigma 持续攀升，说明模型对未来的不确定性在增加。\n\n"
    "2. 极端风险预案\n"
    "   将 P01 作为极端风险预案，建立压力测试机制，确保在尾部情景下账户仍然存活。\n\n"
    "3. 关键行动\n"
    "   每日监控 VAR 与 ES 的偏离度，若连续 3 日扩大，触发风控审查。\n"
    "   —— 风险管理专家"
)


# ======================================================================
#  ReportGenerator
# ======================================================================

class ReportGenerator:
    """Generate comprehensive PDF report with charts and professional commentary."""

    # ------------------------------------------------------------------
    #  Helpers: text-only figure pages
    # ------------------------------------------------------------------

    @staticmethod
    def _make_cover_figure(asset_name: str, start_date: str, end_date: str,
                           simulate_params: Optional[Dict[str, Any]] = None,
                           backtest_summary: str = "") -> plt.Figure:
        """Create a professional cover page."""
        fig, ax = plt.subplots(figsize=(8.27, 11.69))  # A4 portrait
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        # Decorative top bar
        ax.axhline(y=0.92, xmin=0.05, xmax=0.95, color='#1a5276', linewidth=3)
        ax.axhline(y=0.10, xmin=0.05, xmax=0.95, color='#1a5276', linewidth=1.5)

        params = simulate_params or {}
        dist = params.get('distribution_type', 'normal')
        sigma = params.get('segma_calculation_type', 'garch')
        series = params.get('series', 5000)
        alpha = params.get('alpha', 0.05)
        n_days = params.get('times', 5)

        lines = [
            (0.50, 0.82, "蒙特卡罗模拟分析报告", 28, 'bold', '#1a5276'),
            (0.50, 0.76, "Monte Carlo Simulation Analysis Report", 14, 'normal', '#7f8c8d'),
            (0.50, 0.66, f"交易标的：{asset_name}", 18, 'bold', '#2c3e50'),
            (0.50, 0.60, "分析周期", 14, 'bold', '#34495e'),
            (0.50, 0.56, f"{start_date}  —  {end_date}", 13, 'normal', '#555555'),
            (0.50, 0.50, "模型参数", 14, 'bold', '#34495e'),
            (0.50, 0.45, f"分布类型: {dist}    波动率模型: {sigma}    模拟次数: {series}    置信水平: {alpha}    预测步数: {n_days}天",
             10, 'normal', '#666666'),
            (0.50, 0.38, "免责声明", 14, 'bold', '#34495e'),
            (0.50, 0.31, "本报告基于蒙特卡罗模拟方法生成，所有预测结果仅供参考，不构成任何投资建议。",
             9, 'normal', '#999999'),
            (0.50, 0.28, "历史表现不代表未来收益，投资有风险，入市需谨慎。",
             9, 'normal', '#999999'),
            (0.50, 0.17, f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
             9, 'normal', '#aaaaaa'),
        ]

        for x, y, text, size, weight, color in lines:
            ax.text(x, y, text, transform=ax.transAxes, fontsize=size,
                    fontweight=weight, color=color, ha='center', va='center')

        # Backtest recommendation if available
        if backtest_summary:
            ax.text(0.50, 0.06, backtest_summary, transform=ax.transAxes,
                    fontsize=11, fontweight='bold', color='#c0392b',
                    ha='center', va='center')

        return fig

    @staticmethod
    def _make_commentary_figure(title: str, trader_text: str, risk_text: str) -> plt.Figure:
        """Create a text-only commentary page with trader and risk-manager sections."""
        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        # Title bar
        ax.axhline(y=0.94, xmin=0.05, xmax=0.95, color='#1a5276', linewidth=2)
        ax.text(0.07, 0.92, title, fontsize=16, fontweight='bold',
                color='#1a5276', va='center', transform=ax.transAxes)

        # Trader section
        ax.text(0.08, 0.88, "资深交易员观点", transform=ax.transAxes, fontsize=12,
                fontweight='bold', color='#c0392b', va='top', ha='left')
        ax.text(0.08, 0.84, trader_text, transform=ax.transAxes, fontsize=10,
                color='#2c3e50', va='top', ha='left', linespacing=1.5)

        # Risk-manager section
        ax.text(0.08, 0.48, "风险管理专家观点", transform=ax.transAxes, fontsize=12,
                fontweight='bold', color='#2980b9', va='top', ha='left')
        ax.text(0.08, 0.44, risk_text, transform=ax.transAxes, fontsize=10,
                color='#2c3e50', va='top', ha='left', linespacing=1.5)

        return fig

    @staticmethod
    def _make_backtest_text_page(results: dict, recommended: str) -> plt.Figure:
        """Create a summary text page for backtest results."""
        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        ax.axhline(y=0.96, xmin=0.05, xmax=0.95, color='#1a5276', linewidth=2)
        ax.text(0.07, 0.94, "Kupiec POF 回测检验 — 详细结果",
                fontsize=18, fontweight='bold', color='#1a5276',
                va='center', transform=ax.transAxes)

        lines = []
        first_result = next(iter(results.values())) if results else {}
        expected = first_result.get('expected_rate', 0.05)
        lines.append(f"零假设 H0: 实际击穿率 = 预期击穿率 ({expected})")
        lines.append(f"检验方法: Kupiec Proportion of Failures (POF) Test")
        lines.append(f"LR 统计量 ~ χ²(1), 显著性水平 0.05")
        lines.append("")
        lines.append(f"{'分布类型':<16} {'击穿/总':>10} {'击穿率':>10} {'P值':>10} {'结论':>18}")
        lines.append("-" * 72)

        for dist_type, r in results.items():
            if 'error' in r:
                lines.append(f"{dist_type:<16} {'ERROR':>10} {'':>10} {'':>10} {r['error']}")
            else:
                h0 = "未拒绝 H0" if not r.get('reject_h0', True) else "拒绝 H0"
                lines.append(
                    f"{dist_type:<16} {str(r['violations'])+'/'+str(r['total']):>10} "
                    f"{r['observed_rate']:>10.4f} {r.get('p_value', 0):>10.4f} {h0:>18}"
                )

        lines.append("-" * 72)
        lines.append(f"\n推荐分布: {recommended}")
        lines.append("\n若所有分布均拒绝 H0，说明市场结构可能发生突变，建议缩短窗口或分段建模。")

        full_text = "\n".join(lines)
        ax.text(0.07, 0.88, full_text, transform=ax.transAxes, fontsize=10,
                color='#2c3e50', va='top', ha='left',
                linespacing=1.4)

        return fig

    @staticmethod
    def _format_end_date(raw_end: str, analysis_df: pd.DataFrame) -> str:
        """Determine the best end_date string to display.
           Falls back to last trade_date in the original DataFrame if raw_end is empty.
        """
        if raw_end:
            return raw_end
        if analysis_df is not None and len(analysis_df) > 0:
            return str(analysis_df['trade_date'].iloc[-1])
        return ""

    # ------------------------------------------------------------------
    #  Main: generate
    # ------------------------------------------------------------------

    @staticmethod
    def generate(
        original_df: pd.DataFrame,
        prediction_df: pd.DataFrame,
        final_df: pd.DataFrame,
        asset_name: str = "",
        analysis_col_label: str = "涨跌幅",
        start_date: str = "",
        end_date: str = "",
        simulate_params: Optional[Dict[str, Any]] = None,
        backtest_results: Optional[Dict[str, Any]] = None,
        output_dir: str = _DEFAULT_PDF_OUTPUT_DIR,
    ) -> str:
        """Generate comprehensive PDF report.

        Returns:
            Absolute path to the generated PDF file.
        """
        # ---- filename construction ----
        clean_name = asset_name.replace(" ", "_").replace("/", "_") if asset_name else "report"
        start_clean = start_date.replace('-', '') if start_date else ""
        e_date = ReportGenerator._format_end_date(end_date, original_df)
        end_clean = e_date.replace('-', '') if e_date else ""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        pdf_filename = (
            f"Montcarlo_simulation_{clean_name}_预测结果_"
            f"({start_clean}-{end_clean})_{timestamp}.pdf"
        )
        pdf_path = os.path.join(output_dir, pdf_filename)

        logger.info(f"Generating PDF report: {pdf_filename}")
        logger.info(f"  Output dir: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)

        # ---- date-range strings for charts ----
        orig_dates = original_df['trade_date'].astype(str).str.replace('-', '')
        orig_start = orig_dates.iloc[0] if len(orig_dates) > 0 else start_clean
        orig_end = orig_dates.iloc[-1] if len(orig_dates) > 0 else end_clean

        pred_dates = prediction_df['trade_date'].astype(str).str.replace('-', '')
        pred_start = pred_dates.iloc[0] if len(pred_dates) > 0 else ""
        pred_end_d = pred_dates.iloc[-1] if len(pred_dates) > 0 else ""

        final_end = pred_end_d if pred_end_d else orig_end

        # ---- backtest summary for cover ----
        backtest_summary = ""
        recommended = ""
        if backtest_results:
            from .BacktestEngine import BacktestEngine
            recommended = BacktestEngine.recommend_distribution(backtest_results)
            valid = {k: v for k, v in backtest_results.items() if 'error' not in v}
            if valid:
                rec_result = backtest_results.get(recommended, {})
                backtest_summary = (
                    f"回测推荐分布: {recommended}  |  "
                    f"击穿率: {rec_result.get('observed_rate', 0):.4f}  |  "
                    f"P值: {rec_result.get('p_value', 0):.4f}"
                )

        # ================================================================
        #  Build page list
        # ================================================================
        pages = []  # list of (description, figure)

        # --- Cover ---
        logger.info("  Building cover page...")
        cover_fig = ReportGenerator._make_cover_figure(
            asset_name, start_clean, end_clean,
            simulate_params, backtest_summary)
        pages.append(("封面", cover_fig))

        # --- Chart 1 + commentary ---
        logger.info("  Building Chart 1: 原始数据分析...")
        fig1, _ = Visualizer.plot_original_analysis(
            original_df,
            f"[{asset_name}] 原始数据的分析",
            analysis_col_label,
            start_date_str=orig_start,
            end_date_str=orig_end,
            show=False,
        )
        pages.append(("图1: 原始数据分析", fig1))
        pages.append(("图1点评",
                       ReportGenerator._make_commentary_figure(
                           _COMMENTARY_CHART1_TITLE, _COMMENTARY_CHART1_TRADER, _COMMENTARY_CHART1_RISK)))

        # --- Chart 2 + commentary ---
        logger.info("  Building Chart 2: 波动率分析...")
        fig2, _ = Visualizer.plot_volatility_analysis(
            original_df,
            f"[{asset_name}] 波动率分析",
            start_date_str=orig_start,
            end_date_str=orig_end,
            show=False,
        )
        pages.append(("图2: 波动率分析", fig2))
        pages.append(("图2点评",
                       ReportGenerator._make_commentary_figure(
                           _COMMENTARY_CHART2_TITLE, _COMMENTARY_CHART2_TRADER, _COMMENTARY_CHART2_RISK)))

        # --- Chart 3 + commentary ---
        logger.info("  Building Chart 3: 预测结果分析...")
        fig3, _ = Visualizer.plot_prediction_results(
            prediction_df,
            f"[{asset_name}] 预测结果 (P01/P05/P10/P50/P90)",
            analysis_col_label,
            start_date_str=pred_start,
            end_date_str=pred_end_d,
            show=False,
        )
        pages.append(("图3: 预测结果分析", fig3))
        pages.append(("图3点评",
                       ReportGenerator._make_commentary_figure(
                           _COMMENTARY_CHART3_TITLE, _COMMENTARY_CHART3_TRADER, _COMMENTARY_CHART3_RISK)))

        # --- Chart 4 + commentary ---
        logger.info("  Building Chart 4: 最终结果...")
        fig4, _ = Visualizer.plot_final_results(
            final_df,
            f"[{asset_name}] 最终结果",
            analysis_col_label,
            start_date_str=orig_start,
            end_date_str=final_end,
            show=False,
        )
        pages.append(("图4: 最终结果总览", fig4))
        pages.append(("图4点评",
                       ReportGenerator._make_commentary_figure(
                           _COMMENTARY_CHART4_TITLE, _COMMENTARY_CHART4_TRADER, _COMMENTARY_CHART4_RISK)))

        # --- Backtest (if available) ---
        if backtest_results:
            logger.info("  Building backtest pages...")
            from .BacktestEngine import BacktestEngine

            # Backtest summary text page
            pages.append(("回测检验报告",
                           ReportGenerator._make_backtest_text_page(
                               backtest_results, recommended)))

            # Backtest summary bar chart
            fig_bt, _ = BacktestEngine.plot_backtest_results(backtest_results, show=False)
            pages.append(("回测图表: 击穿率与P值", fig_bt))

            # Violation detail charts for top 3 non-error distributions
            non_error = [(k, v) for k, v in backtest_results.items()
                         if 'error' not in v and 'var_lower_series' in v]
            for dist_type, result in non_error[:3]:
                logger.info(f"  Building violation chart for {dist_type}...")
                fig_v = BacktestEngine.plot_var_violations(
                    result,
                    title=f"VAR Violation Detail — {dist_type}",
                    show=False,
                )
                if fig_v is not None:
                    pages.append((f"回测击穿详情: {dist_type}", fig_v))

        # ================================================================
        #  Write PDF
        # ================================================================
        logger.info(f"  Writing {len(pages)} pages to PDF...")
        with PdfPages(pdf_path) as pdf:
            for label, fig in pages:
                logger.info(f"    Saving: {label}")
                pdf.savefig(fig)
                plt.close(fig)

        logger.info(f"PDF report generated: {pdf_path}")
        print(f"\nPDF report generated: {pdf_path}")
        return pdf_path

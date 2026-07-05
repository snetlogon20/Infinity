"""
ReportGenerator — Generate PDF report for Monte Carlo simulation.
"""
import os
import logging
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from typing import Optional, Dict, Any
from .Visualizer import Visualizer

logger = logging.getLogger(__name__)

# Enforce robust font config before any figure creation
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans', 'SimHei', 'Microsoft YaHei', 'Arial']
matplotlib.rcParams['font.family'] = 'sans-serif'


class ReportGenerator:
    """Generate comprehensive PDF report with charts and commentary."""

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
        output_dir: str = r"D:\workspace_python\infinity_data\data\outbound",
    ) -> str:
        """
        Generate PDF report with all 4 charts.

        Returns:
            Absolute path to the generated PDF file.
        """
        # Build filename
        clean_name = asset_name.replace(" ", "_").replace("/", "_") if asset_name else "report"
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"{clean_name}_report_{timestamp}.pdf"
        pdf_path = os.path.join(output_dir, pdf_filename)

        logger.info(f"Generating PDF report: {pdf_path}")

        try:
            # use pgf backend for PDF; fallback to default savefig
            from matplotlib.backends.backend_pgf import FigureCanvasPgf
            logger.info("Using PGF backend for PDF generation")
        except ImportError:
            logger.warning("PGF backend not available, using default PDF backend")

        # Generate charts and save to PDF
        figs = []

        # Chart 1
        orig_start = original_df['trade_date'].iloc[0] if len(original_df) > 0 else ""
        orig_end = original_df['trade_date'].iloc[-1] if len(original_df) > 0 else ""
        fig1, _ = Visualizer.plot_original_analysis(
            original_df,
            f"[{asset_name}] 原始数据的分析",
            analysis_col_label,
            start_date_str=str(orig_start).replace('-', ''),
            end_date_str=str(orig_end).replace('-', ''),
            show=False,
        )
        figs.append(fig1)

        # Chart 2
        fig2, _ = Visualizer.plot_volatility_analysis(
            original_df,
            f"[{asset_name}] 波动率分析",
            start_date_str=str(orig_start).replace('-', ''),
            end_date_str=str(orig_end).replace('-', ''),
            show=False,
        )
        figs.append(fig2)

        # Chart 3
        pred_start = prediction_df['trade_date'].iloc[0] if len(prediction_df) > 0 else ""
        pred_end = prediction_df['trade_date'].iloc[-1] if len(prediction_df) > 0 else ""
        fig3, _ = Visualizer.plot_prediction_results(
            prediction_df,
            f"[{asset_name}] 预测结果 (P01 / P05 / P10 / P50 / P90)",
            analysis_col_label,
            start_date_str=str(pred_start).replace('-', ''),
            end_date_str=str(pred_end).replace('-', ''),
            show=False,
        )
        figs.append(fig3)

        # Chart 4
        final_start = final_df['trade_date'].iloc[0] if len(final_df) > 0 else ""
        final_end = final_df['trade_date'].iloc[-1] if len(final_df) > 0 else ""
        fig4, _ = Visualizer.plot_final_results(
            final_df,
            f"[{asset_name}] 最终结果",
            analysis_col_label,
            start_date_str=str(final_start).replace('-', ''),
            end_date_str=str(final_end).replace('-', ''),
            show=False,
        )
        figs.append(fig4)

        # Save as multi-page PDF
        from matplotlib.backends.backend_pdf import PdfPages
        os.makedirs(output_dir, exist_ok=True)

        with PdfPages(pdf_path) as pdf:
            for fig in figs:
                pdf.savefig(fig)
                plt.close(fig)

        logger.info(f"PDF report generated: {pdf_path}")
        return pdf_path

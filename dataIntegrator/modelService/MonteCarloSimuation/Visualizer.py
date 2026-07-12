"""
Visualizer — 4 line charts for Monte Carlo simulation analysis.
All charts use 折线图 (line plot).
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Fix Unicode minus sign: must be set BEFORE any font configuration
plt.rcParams['axes.unicode_minus'] = False

# Configure fonts: Chinese fonts FIRST for CJK support,
# DejaVu Sans as fallback for Latin glyphs
try:
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans', 'Arial']
    plt.rcParams['font.family'] = 'sans-serif'
except Exception:
    pass


class Visualizer:
    """Generate four key line charts for Monte Carlo analysis."""

    @staticmethod
    def _parse_dates(df: pd.DataFrame) -> pd.Series:
        """Parse trade_date to datetime robustly."""
        s = df['trade_date']
        # Already datetime64 — just return as datetime
        if pd.api.types.is_datetime64_any_dtype(s):
            return pd.to_datetime(s)
        # String / object: normalize then parse
        try:
            s_str = (
                s.astype(str)
                .str.replace('-', '', regex=False)
                .str.replace(r'\s+.*', '', regex=True)
            )
            return pd.to_datetime(s_str, format='%Y%m%d', errors='coerce')
        except Exception:
            return pd.to_datetime(s, errors='coerce')

    @staticmethod
    def _pick_annotate_indices(series: pd.Series | np.ndarray, max_labels: int = 6) -> list:
        """Select indices to annotate: first, last, evenly spaced, and local extrema."""
        values = np.asarray(series)
        n = len(values)
        if n == 0:
            return []
        if n <= max_labels:
            return list(range(n))

        idx_set = {0, n - 1}  # first and last

        # evenly spaced middle points
        step = max(1, n // max_labels)
        for i in range(step, n - 1, step):
            idx_set.add(i)

        # local extrema (peaks and valleys)
        for i in range(1, n - 1):
            if (values[i] > values[i - 1] and values[i] > values[i + 1]) or \
               (values[i] < values[i - 1] and values[i] < values[i + 1]):
                idx_set.add(i)

        return sorted(idx_set)

    @staticmethod
    def _format_date_axis(ax, dates, is_datetime):
        """Auto-scale date ticks by data size; always include year."""
        if not is_datetime:
            return
        n = len(dates)
        if n >= 600:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        elif n >= 200:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=2))
        else:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator())
        ax.tick_params(axis='x', labelsize=7)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # ==================================================================
    #  Chart 1: 原始数据的分析
    # ==================================================================

    @classmethod
    def plot_original_analysis(cls, df: pd.DataFrame, title: str = "原始数据的分析",
                               analysis_col_label: str = "涨跌幅",
                               start_date_str: str = "", end_date_str: str = "",
                               show: bool = True):
        """
        Chart 1 — 原始数据的分析 (折线图)

        X轴 = trade_date, Y轴 = analysis_column的值
        曲线包括: analysis_column, VAR上下限, ES上下限, 平均值, 中位数,
                 5日EMA, 10日EMA, 20日EMA, 60日EMA
        Title: 开始日期：{start_date} 结束日期：{end_date}
        """
        df = df.copy()
        dates = cls._parse_dates(df)
        is_datetime = pd.api.types.is_datetime64_any_dtype(dates)

        # Build title with date range
        full_title = f"{title}\n开始日期：{start_date_str}  结束日期：{end_date_str}"

        fig, ax = plt.subplots(figsize=(18, 8))
        fig.suptitle(full_title, fontsize=14, fontweight='bold')

        # ---- Core analysis column (thick line) ----
        if 'analysis_column' in df.columns:
            ax.plot(dates, df['analysis_column'], 'b-', linewidth=1.0,
                    alpha=0.85, label=analysis_col_label)

        # ---- VAR bounds ----
        if 'var_upper_bound' in df.columns:
            ax.plot(dates, df['var_upper_bound'], 'r--', linewidth=0.8,
                    alpha=0.55, label='VAR Upper')
        if 'var_lower_bound' in df.columns:
            ax.plot(dates, df['var_lower_bound'], 'r--', linewidth=0.8,
                    alpha=0.55, label='VAR Lower')

        # ---- ES bounds ----
        if 'es_upper_bound' in df.columns:
            ax.plot(dates, df['es_upper_bound'], 'm:', linewidth=0.6,
                    alpha=0.45, label='ES Upper')
        if 'es_lower_bound' in df.columns:
            ax.plot(dates, df['es_lower_bound'], 'm:', linewidth=0.6,
                    alpha=0.45, label='ES Lower')

        # ---- Average & Median ----
        if 'average' in df.columns:
            ax.plot(dates, df['average'], 'orange', linewidth=0.8,
                    alpha=0.6, label='Average')
        if 'median_value' in df.columns:
            ax.plot(dates, df['median_value'], 'purple', linewidth=0.8,
                    alpha=0.6, label='Median')

        # ---- EMAs ----
        ema_config = [
            ('pct_change_ema_5', 'cyan', 'EMA 5'),
            ('pct_change_ema_10', 'lime', 'EMA 10'),
            ('pct_change_ema_20', 'gold', 'EMA 20'),
            ('pct_change_ema_60', 'deeppink', 'EMA 60'),
        ]
        for col, color, label in ema_config:
            if col in df.columns:
                ax.plot(dates, df[col], color=color, linewidth=0.8,
                        alpha=0.5, label=label)

        ax.axhline(y=0, color='gray', linewidth=0.5, linestyle='-')
        ax.set_ylabel(analysis_col_label)
        ax.set_xlabel('Trade Date')
        ax.legend(loc='upper left', fontsize=7, ncol=2)
        ax.grid(True, alpha=0.3)
        cls._format_date_axis(ax, dates, is_datetime)

        plt.tight_layout()
        if show:
            plt.show()
        return fig, ax

    # ==================================================================
    #  Chart 2: 波动率分析
    # ==================================================================

    @classmethod
    def plot_volatility_analysis(cls, df: pd.DataFrame, title: str = "波动率分析",
                                 start_date_str: str = "", end_date_str: str = "",
                                 show: bool = True):
        """
        Chart 2 — 波动率分析 (折线图)

        X轴 = trade_date
        Y轴 = 正常分布的方差, GARCH模型的方差, EGARCH模型的方差
        Title: 开始日期：{start_date} 结束日期：{end_date}
        """
        df = df.copy()
        dates = cls._parse_dates(df)
        is_datetime = pd.api.types.is_datetime64_any_dtype(dates)

        # Build title with date range
        full_title = f"{title}\n开始日期：{start_date_str}  结束日期：{end_date_str}"

        fig, ax = plt.subplots(figsize=(18, 6))
        fig.suptitle(full_title, fontsize=14, fontweight='bold')

        sigma_config = [
            ('normal_segma', 'purple', 'Normal Sigma'),
            ('garch_segma', 'orange', 'GARCH Sigma'),
            ('egarch_segma', 'green', 'EGARCH Sigma'),
        ]
        for col, color, label in sigma_config:
            if col in df.columns:
                ax.plot(dates, df[col], color=color, linewidth=1.0,
                        alpha=0.75, label=label)

        ax.set_ylabel('Sigma (Volatility)')
        ax.set_xlabel('Trade Date')
        ax.legend(loc='upper left', fontsize=8)
        ax.grid(True, alpha=0.3)
        cls._format_date_axis(ax, dates, is_datetime)

        plt.tight_layout()
        if show:
            plt.show()
        return fig, ax

    # ==================================================================
    #  Chart 3: 预测结果的分析
    # ==================================================================

    @classmethod
    def plot_prediction_results(cls, df: pd.DataFrame, title: str = "预测结果的分析",
                                analysis_col_label: str = "涨跌幅",
                                start_date_str: str = "", end_date_str: str = "",
                                show: bool = True):
        """
        Chart 3 — 预测结果的分析 (折线图，双Y轴)

        X轴 = trade_date
        Y1轴 = analysis_column
        Y2轴 = predict_p10 / predict_p50 / predict_p90
        Title: 开始日期：{prediction_df最小date} 结束日期：{prediction_df最大date}
        """
        df = df.copy()
        dates = cls._parse_dates(df)
        is_datetime = pd.api.types.is_datetime64_any_dtype(dates)

        # Build title with date range
        full_title = f"{title}\n开始日期：{start_date_str}  结束日期：{end_date_str}"

        fig, ax1 = plt.subplots(figsize=(14, 6))
        fig.suptitle(full_title, fontsize=14, fontweight='bold')

        # Y1 (left): analysis_column as line
        if 'analysis_column' in df.columns:
            ax1.plot(dates, df['analysis_column'], 'b-', linewidth=1.2,
                     alpha=0.8, label=analysis_col_label)
        ax1.set_ylabel(analysis_col_label, color='blue')
        ax1.tick_params(axis='y', labelcolor='blue')

        # Y2 (right): p10, p50, p90 as three lines
        ax2 = ax1.twinx()

        # P10 — dashed steelblue
        if 'predict_p10' in df.columns:
            ax2.plot(dates, df['predict_p10'], color='steelblue', linestyle='--',
                     linewidth=1.0, markersize=2.5, marker='o', alpha=0.7, label='P10')
            idx_p10 = cls._pick_annotate_indices(df['predict_p10'].values)
            for i in idx_p10:
                val = df['predict_p10'].iloc[i]
                va = 'bottom' if val >= 0 else 'top'
                ax2.annotate(f'{val:.4f}',
                             (dates.iloc[i] if is_datetime else i, val),
                             textcoords="offset points", xytext=(0, 8 if val >= 0 else -12),
                             ha='center', va=va, fontsize=5, color='steelblue', rotation=45)

        # P50 — solid red (main prediction)
        if 'predict_p50' in df.columns:
            ax2.plot(dates, df['predict_p50'], 'r-o', linewidth=1.4,
                     markersize=3.5, alpha=0.9, label='P50 (主预测)')
            idx_p50 = cls._pick_annotate_indices(df['predict_p50'].values)
            for i in idx_p50:
                val = df['predict_p50'].iloc[i]
                va = 'bottom' if val >= 0 else 'top'
                ax2.annotate(f'{val:.4f}',
                             (dates.iloc[i] if is_datetime else i, val),
                             textcoords="offset points", xytext=(0, 8 if val >= 0 else -12),
                             ha='center', va=va, fontsize=6, color='red', fontweight='bold', rotation=45)

        # P90 — dashed darkorange
        if 'predict_p90' in df.columns:
            ax2.plot(dates, df['predict_p90'], color='darkorange', linestyle='--',
                     linewidth=1.0, markersize=2.5, marker='o', alpha=0.7, label='P90')
            idx_p90 = cls._pick_annotate_indices(df['predict_p90'].values)
            for i in idx_p90:
                val = df['predict_p90'].iloc[i]
                va = 'bottom' if val >= 0 else 'top'
                ax2.annotate(f'{val:.4f}',
                             (dates.iloc[i] if is_datetime else i, val),
                             textcoords="offset points", xytext=(0, 8 if val >= 0 else -12),
                             ha='center', va=va, fontsize=5, color='darkorange', rotation=45)

        # P05 — solid darkgreen (like P50 style)
        if 'predict_p05' in df.columns:
            ax2.plot(dates, df['predict_p05'], color='darkgreen', linestyle='-',
                     linewidth=1.2, markersize=3, marker='o', alpha=0.7, label='P05')
            idx_p05 = cls._pick_annotate_indices(df['predict_p05'].values)
            for i in idx_p05:
                val = df['predict_p05'].iloc[i]
                va = 'bottom' if val >= 0 else 'top'
                ax2.annotate(f'{val:.4f}',
                             (dates.iloc[i] if is_datetime else i, val),
                             textcoords="offset points", xytext=(0, 8 if val >= 0 else -12),
                             ha='center', va=va, fontsize=5, color='darkgreen', fontweight='bold', rotation=45)

        # P01 — solid darkcyan (like P50 style)
        if 'predict_p01' in df.columns:
            ax2.plot(dates, df['predict_p01'], color='darkcyan', linestyle='-',
                     linewidth=1.2, markersize=3, marker='o', alpha=0.7, label='P01')
            idx_p01 = cls._pick_annotate_indices(df['predict_p01'].values, max_labels=4)
            for i in idx_p01:
                val = df['predict_p01'].iloc[i]
                va = 'bottom' if val >= 0 else 'top'
                ax2.annotate(f'{val:.4f}',
                             (dates.iloc[i] if is_datetime else i, val),
                             textcoords="offset points", xytext=(0, 8 if val >= 0 else -12),
                             ha='center', va=va, fontsize=4, color='darkcyan', fontweight='bold', rotation=45)

        ax2.axhline(y=0, color='gray', linewidth=0.5)
        ax2.set_ylabel('Predict (P01 / P05 / P10 / P50 / P90)', color='red')
        ax2.tick_params(axis='y', labelcolor='red')

        if is_datetime:
            cls._format_date_axis(ax1, dates, is_datetime)
        else:
            ax1.set_xticks(range(len(df)))
            ax1.set_xticklabels(df['trade_date'].values, rotation=45, ha='right')

        ax1.set_xlabel('Trade Date')
        ax1.grid(True, alpha=0.3, axis='y')

        # Combined legend
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=9)

        plt.tight_layout()
        if show:
            plt.show()
        return fig, (ax1, ax2)

    # ==================================================================
    #  Chart 4: 最终结果
    # ==================================================================

    @classmethod
    def plot_final_results(cls, df: pd.DataFrame, title: str = "最终结果",
                           analysis_col_label: str = "涨跌幅",
                           start_date_str: str = "", end_date_str: str = "",
                           show: bool = True):
        """
        Chart 4 — 最终结果 (折线图，双Y轴)

        X轴 = trade_date
        Y轴 = analysis_column的值 + predict_p10/p50/p90
        Y1轴 = EGARCH模型的方差
        Title: 开始日期：{start_date} 结束日期：{预测最大date}
        """
        df = df.copy()
        dates = cls._parse_dates(df)
        is_datetime = pd.api.types.is_datetime64_any_dtype(dates)

        hist_mask = df['step_num'] == 0
        pred_mask = df['step_num'] > 0

        # Build title with date range
        full_title = f"{title}\n开始日期：{start_date_str}  结束日期：{end_date_str}"

        fig, ax = plt.subplots(figsize=(18, 8))
        fig.suptitle(full_title, fontsize=14, fontweight='bold')

        # Y-axis (left): analysis_column (historical) + predict_p10/p50/p90 (future)
        if 'analysis_column' in df.columns:
            ax.plot(dates[hist_mask], df.loc[hist_mask, 'analysis_column'],
                    'b-', linewidth=1.0, alpha=0.7, label='Historical ' + analysis_col_label)

        # VAR bands on historical portion
        if 'var_upper_bound' in df.columns:
            ax.plot(dates[hist_mask], df.loc[hist_mask, 'var_upper_bound'],
                    'r--', linewidth=0.5, alpha=0.4, label='VAR Upper')
        if 'var_lower_bound' in df.columns:
            ax.plot(dates[hist_mask], df.loc[hist_mask, 'var_lower_bound'],
                    'r--', linewidth=0.5, alpha=0.4, label='VAR Lower')

        # Prediction zone highlight
        if pred_mask.any():
            ax.axvspan(dates[pred_mask].iloc[0], dates[pred_mask].iloc[-1],
                       alpha=0.12, color='orange', label='Predict Zone')

        # Predicted values: p10/p50/p90 three lines with confidence band
        if pred_mask.any():
            has_p10 = 'predict_p10' in df.columns
            has_p50 = 'predict_p50' in df.columns
            has_p90 = 'predict_p90' in df.columns

            # Confidence band: fill between p10 and p90
            if has_p10 and has_p90:
                ax.fill_between(dates[pred_mask],
                                df.loc[pred_mask, 'predict_p10'],
                                df.loc[pred_mask, 'predict_p90'],
                                alpha=0.15, color='steelblue', label='P10-P90 置信带')

            # P10 line
            if has_p10:
                ax.plot(dates[pred_mask], df.loc[pred_mask, 'predict_p10'],
                        '--', color='steelblue', linewidth=1.0, markersize=2,
                        marker='s', alpha=0.7, zorder=4, label='P10')

            pred_idx = df[pred_mask].index

            # P50 line (main prediction)
            if has_p50:
                ax.plot(dates[pred_mask], df.loc[pred_mask, 'predict_p50'],
                        'o-', color='red', linewidth=1.4, markersize=3,
                        zorder=5, marker='o', label='P50 (主预测)')
                # Annotate P50 values (selective, rotated)
                idx_p50 = cls._pick_annotate_indices(df.loc[pred_idx, 'predict_p50'].values)
                for i in idx_p50:
                    idx = pred_idx[i]
                    val = df.loc[idx, 'predict_p50']
                    d = dates[idx]
                    ax.annotate(f'{val:.4f}', (d, val),
                                textcoords="offset points", xytext=(0, 10),
                                ha='center', fontsize=5, color='red', fontweight='bold', rotation=45)

            # P90 line
            if has_p90:
                ax.plot(dates[pred_mask], df.loc[pred_mask, 'predict_p90'],
                        '--', color='darkorange', linewidth=1.0, markersize=2,
                        marker='s', alpha=0.7, zorder=4, label='P90')

            # P05 line (solid, circle marker, like P50 but darkgreen)
            has_p05 = 'predict_p05' in df.columns
            if has_p05:
                ax.plot(dates[pred_mask], df.loc[pred_mask, 'predict_p05'],
                        'o-', color='darkgreen', linewidth=1.2, markersize=3,
                        zorder=5, marker='o', label='P05')
                idx_p05 = cls._pick_annotate_indices(df.loc[pred_idx, 'predict_p05'].values)
                for i in idx_p05:
                    idx = pred_idx[i]
                    val = df.loc[idx, 'predict_p05']
                    d = dates[idx]
                    ax.annotate(f'{val:.4f}', (d, val),
                                textcoords="offset points", xytext=(0, 10),
                                ha='center', fontsize=5, color='darkgreen', fontweight='bold', rotation=45)

            # P01 line (solid, circle marker, like P50 but darkcyan)
            has_p01 = 'predict_p01' in df.columns
            if has_p01:
                ax.plot(dates[pred_mask], df.loc[pred_mask, 'predict_p01'],
                        'o-', color='darkcyan', linewidth=1.2, markersize=3,
                        zorder=5, marker='o', label='P01')
                idx_p01 = cls._pick_annotate_indices(df.loc[pred_idx, 'predict_p01'].values, max_labels=4)
                for i in idx_p01:
                    idx = pred_idx[i]
                    val = df.loc[idx, 'predict_p01']
                    d = dates[idx]
                    ax.annotate(f'{val:.4f}', (d, val),
                                textcoords="offset points", xytext=(0, 10),
                                ha='center', fontsize=4, color='darkcyan', fontweight='bold', rotation=45)

        ax.set_ylabel(analysis_col_label + ' / Predict P01/P05/P10/P50/P90')
        ax.axhline(y=0, color='gray', linewidth=0.5)

        # Y1-axis (right): sigma curves (normal, garch, egarch)
        ax1 = ax.twinx()
        if 'normal_segma' in df.columns:
            ax1.plot(dates, df['normal_segma'], 'purple', linewidth=1.0,
                     alpha=0.65, label='Normal Sigma')
        if 'garch_segma' in df.columns:
            ax1.plot(dates, df['garch_segma'], 'orange', linewidth=1.0,
                     alpha=0.65, label='GARCH Sigma')
        if 'egarch_segma' in df.columns:
            ax1.plot(dates, df['egarch_segma'], 'green', linewidth=1.0,
                     alpha=0.65, label='EGARCH Sigma')
        ax1.set_ylabel('Sigma', color='green')
        ax1.tick_params(axis='y', labelcolor='green')

        ax.set_xlabel('Trade Date')
        cls._format_date_axis(ax, dates, is_datetime)

        # Legend from both axes
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax1.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=7)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        if show:
            plt.show()
        return fig, (ax, ax1)

    # ==================================================================
    #  Show all 4 charts
    # ==================================================================

    @classmethod
    def show_all(cls, original_df: pd.DataFrame, prediction_df: pd.DataFrame,
                 final_df: pd.DataFrame, asset_name: str = "",
                 analysis_col_label: str = "涨跌幅",
                 start_date_str: str = "", end_date_str: str = ""):
        """Display all 4 line charts in sequence."""

        # Compute date ranges for titles
        # Chart 1 & 2: original data range
        orig_dates = original_df['trade_date'].astype(str).str.replace('-', '')
        orig_start = orig_dates.iloc[0] if len(orig_dates) > 0 else start_date_str
        orig_end = orig_dates.iloc[-1] if len(orig_dates) > 0 else end_date_str

        # Chart 3: prediction data range
        pred_dates = prediction_df['trade_date'].astype(str).str.replace('-', '')
        pred_start = pred_dates.iloc[0] if len(pred_dates) > 0 else ""
        pred_end = pred_dates.iloc[-1] if len(pred_dates) > 0 else ""

        # Chart 4: original start to prediction end
        final_start = orig_start
        final_end = pred_end if pred_end else orig_end

        logger.info(f"Plotting all 4 charts for {asset_name}")
        prefix = f"[{asset_name}] " if asset_name else ""

        # Chart 1
        cls.plot_original_analysis(
            original_df,
            f"{prefix}原始数据的分析",
            analysis_col_label,
            start_date_str=orig_start,
            end_date_str=orig_end,
        )

        # Chart 2
        cls.plot_volatility_analysis(
            original_df,
            f"{prefix}波动率分析",
            start_date_str=orig_start,
            end_date_str=orig_end,
        )

        # Chart 3
        cls.plot_prediction_results(
            prediction_df,
            f"{prefix}预测结果的分析",
            analysis_col_label,
            start_date_str=pred_start,
            end_date_str=pred_end,
        )

        # Chart 4
        cls.plot_final_results(
            final_df,
            f"{prefix}最终结果",
            analysis_col_label,
            start_date_str=final_start,
            end_date_str=final_end,
        )

        logger.info("All 4 charts plotted successfully")

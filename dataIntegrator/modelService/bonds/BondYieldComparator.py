"""
收益率比较器：比较 SHIBOR、国债收益率、可转债收益率
支持批量日期分析，输出PDF报告（含专业金融分析）
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
import os
import textwrap
from datetime import datetime
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

logger = CommonLib.logger


class BondYieldComparator:
    """收益率比较器：比较 SHIBOR、国债、可转债的收益率"""

    def __init__(self, output_dir=None):
        self.clickhouseService = ClickhouseService()
        self.output_dir = output_dir if output_dir else os.path.join(
            CommonParameters.reportPath, "YieldComparison"
        )
        os.makedirs(self.output_dir, exist_ok=True)

        # 期限标准化映射（将各种期限格式统一）
        # SHIBOR 期限 -> 标准化期限（年）
        self.shibor_tenor_to_years = {
            'tenor_on': 1/365,    # 隔夜
            'tenor_1w': 7/365,    # 1周
            'tenor_2w': 14/365,   # 2周
            'tenor_1m': 1/12,     # 1个月
            'tenor_3m': 0.25,     # 3个月
            'tenor_6m': 0.5,      # 6个月
            'tenor_9m': 0.75,     # 9个月
            'tenor_1y': 1.0,      # 1年
        }

        # SHIBOR 期限 -> 显示名称
        self.shibor_tenor_names = {
            'tenor_on': 'ON',
            'tenor_1w': '1W',
            'tenor_2w': '2W',
            'tenor_1m': '1M',
            'tenor_3m': '3M',
            'tenor_6m': '6M',
            'tenor_9m': '9M',
            'tenor_1y': '1Y',
        }

        # 国债 curve_term（年）-> 显示名称
        self.treasury_term_to_name = {
            0.08: '1M',
            0.1: '1.2M',
            0.25: '3M',
            0.5: '6M',
            1.0: '1Y',
            2.0: '2Y',
            3.0: '3Y',
            5.0: '5Y',
            7.0: '7Y',
            10.0: '10Y',
            20.0: '20Y',
            30.0: '30Y',
        }

        # 年限 -> 显示名称（用于可转债）
        self.years_to_name = {
            0.25: '3M',
            0.5: '6M',
            1.0: '1Y',
            2.0: '2Y',
            3.0: '3Y',
            5.0: '5Y',
        }

    def fetch_shibor_rates(self, trade_date):
        """
        获取指定交易日的 SHIBOR 利率

        参数:
        - trade_date: 交易日期 (格式: 'YYYYMMDD')

        返回:
        - df: DataFrame with columns [trade_date, tenor, rate]
        """
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
        WHERE trade_date = '{trade_date}'
        """

        logger.info(f"查询 SHIBOR 数据: {trade_date}")
        df = self.clickhouseService.getDataFrameWithoutColumnsName(sql)

        if df.empty:
            logger.warning(f"未找到 {trade_date} 的 SHIBOR 数据")
            return pd.DataFrame()

        # 转换为长格式
        result_rows = []
        for col in df.columns:
            if col.startswith('tenor_') and col != 'trade_date':
                years = self.shibor_tenor_to_years.get(col, 0)
                name = self.shibor_tenor_names.get(col, col)
                rate = df[col].values[0]
                if pd.notna(rate):
                    result_rows.append({
                        'trade_date': trade_date,
                        'tenor': name,
                        'tenor_years': years,
                        'shibor_rate': rate
                    })

        result_df = pd.DataFrame(result_rows)
        logger.info(f"SHIBOR 数据获取完成: {len(result_df)} 条记录")
        return result_df

    def fetch_treasury_yields(self, trade_date):
        """
        获取指定交易日的国债收益率，并将 curve_term 转换为标准期限格式

        参数:
        - trade_date: 交易日期 (格式: 'YYYYMMDD')

        返回:
        - df: DataFrame with columns [trade_date, tenor, yield]
        """
        sql = f"""
        SELECT 
            trade_date,
            curve_term,
            yield
        FROM df_tushare_yc_cb
        WHERE trade_date = '{trade_date}'
          AND curve_type = '0'
          AND ts_code = '1001.CB'
        ORDER BY curve_term ASC
        """

        logger.info(f"查询国债收益率数据: {trade_date}")
        df = self.clickhouseService.getDataFrameWithoutColumnsName(sql)

        if df.empty:
            # 诊断：检查该日期是否有任何收益率曲线数据
            diag_sql = f"""
            SELECT DISTINCT ts_code, COUNT(*) AS cnt
            FROM df_tushare_yc_cb
            WHERE trade_date = '{trade_date}'
            GROUP BY ts_code
            """
            diag_df = self.clickhouseService.getDataFrameWithoutColumnsName(diag_sql)
            if not diag_df.empty:
                ts_codes = diag_df['ts_code'].tolist()
                logger.warning(f"未找到 {trade_date} 的 ts_code='1001.CB' 国债收益率数据，"
                             f"但该日期存在以下 ts_code: {ts_codes}")
            else:
                logger.warning(f"未找到 {trade_date} 的国债收益率数据（可能非交易日或数据未更新）")
            return pd.DataFrame()

        # 转换 curve_term 为标准化期限名称
        result_rows = []
        for _, row in df.iterrows():
            curve_term = float(row['curve_term'])
            yield_val = row['yield']

            # 找到最接近的标准期限
            closest_term = min(self.treasury_term_to_name.keys(),
                             key=lambda x: abs(x - curve_term))
            tenor_name = self.treasury_term_to_name[closest_term]

            result_rows.append({
                'trade_date': trade_date,
                'tenor': tenor_name,
                'tenor_years': curve_term,
                'treasury_yield': yield_val
            })

        result_df = pd.DataFrame(result_rows)
        logger.info(f"国债收益率数据获取完成: {len(result_df)} 条记录")
        return result_df

    def fetch_convertible_bond_yields(self, trade_date, top_n=10, bottom_n=10):
        """
        获取指定交易日的可转债收益率（最高和最低 N 个）

        参数:
        - trade_date: 交易日期 (格式: 'YYYYMMDD')
        - top_n: 获取收益率最高的 N 只债券
        - bottom_n: 获取收益率最低的 N 只债券

        返回:
        - df: DataFrame with columns [trade_date, ts_code, bond_full_name, maturity, current_yield]
        """
        sql = f"""
        SELECT 
            b.ts_code AS ts_code,
            b.bond_full_name AS bond_full_name,
            b.maturity AS maturity,
            m.current_yield AS current_yield,
            m.modified_duration AS duration,
            m.convexity AS convexity
        FROM indexsysdb.df_tushare_cb_daily d
        LEFT JOIN indexsysdb.df_tushare_cb_basic b ON d.ts_code = b.ts_code
        LEFT JOIN indexsysdb.df_tushare_cb_metrics m ON d.ts_code = m.ts_code AND d.trade_date = m.trade_date
        WHERE d.trade_date = '{trade_date}'
          AND (m.current_yield IS NOT NULL AND m.current_yield <> 0)
        ORDER BY COALESCE(m.current_yield, 999) ASC
        """

        logger.info(f"查询可转债收益率数据: {trade_date}")
        df = self.clickhouseService.getDataFrameWithoutColumnsName(sql)

        if df.empty:
            # 诊断：检查 cb_daily 是否有当日数据（可能 metrics 未更新）
            diag_sql = f"""
            SELECT COUNT(*) AS cnt
            FROM indexsysdb.df_tushare_cb_daily
            WHERE trade_date = '{trade_date}'
            """
            diag_df = self.clickhouseService.getDataFrameWithoutColumnsName(diag_sql)
            daily_cnt = int(diag_df['cnt'].values[0]) if not diag_df.empty else 0

            if daily_cnt > 0:
                logger.warning(f"{trade_date} 有 {daily_cnt} 条 cb_daily 记录，但 cb_metrics 缺失（当前收益率/久期/凸性未更新）")
            else:
                logger.warning(f"未找到 {trade_date} 的可转债日线数据（可能非交易日）")
            return pd.DataFrame()

        # 获取最低 N 个和最高 N 个
        bottom_df = df.head(bottom_n).copy()
        top_df = df.tail(top_n).copy()

        # 添加标签
        bottom_df['yield_type'] = '最低收益率'
        top_df['yield_type'] = '最高收益率'

        result_df = pd.concat([bottom_df, top_df], ignore_index=True)
        result_df['trade_date'] = trade_date

        # 将 maturity 转换为期限名称
        result_df['tenor'] = result_df['maturity'].apply(self._maturity_to_tenor)
        result_df['tenor_years'] = result_df['maturity']
        result_df.rename(columns={'current_yield': 'convertible_yield'}, inplace=True)

        logger.info(f"可转债收益率数据获取完成: {len(result_df)} 条记录")
        return result_df[['trade_date', 'ts_code', 'bond_full_name', 'tenor',
                          'tenor_years', 'convertible_yield', 'yield_type',
                          'duration', 'convexity']]

    def _maturity_to_tenor(self, maturity):
        """将 maturity（年）转换为标准期限名称"""
        if pd.isna(maturity):
            return 'N/A'

        try:
            maturity = float(maturity)
        except (ValueError, TypeError):
            return 'N/A'

        # 找到最接近的标准期限
        closest_term = min(self.years_to_name.keys(),
                         key=lambda x: abs(x - maturity))
        return self.years_to_name[closest_term]

    def compare_yields(self, trade_date):
        """
        比较三个市场的收益率

        参数:
        - trade_date: 交易日期 (格式: 'YYYYMMDD')

        返回:
        - comparison_df: SHIBOR vs 国债 对比 DataFrame（按标准期限聚合）
        - convertible_df: 可转债 DataFrame
        - treasury_full_df: 国债完整数据（用于绘图）
        """
        logger.info("=" * 80)
        logger.info(f"开始比较收益率: {trade_date}")
        logger.info("=" * 80)

        # 1. 获取 SHIBOR 利率
        shibor_df = self.fetch_shibor_rates(trade_date)

        # 2. 获取国债收益率（完整数据，保留用于绘图）
        treasury_full_df = self.fetch_treasury_yields(trade_date)

        # 3. 获取可转债收益率
        convertible_df = self.fetch_convertible_bond_yields(trade_date)

        # 4. 国债按标准期限聚合（取最接近标准期限的那个点的收益率）
        treasury_agg = pd.DataFrame()
        if not treasury_full_df.empty:
            # 为每个标准期限找最接近的 curve_term 对应的 yield
            agg_rows = []
            for std_term, std_name in self.treasury_term_to_name.items():
                match = treasury_full_df.iloc[
                    (treasury_full_df['tenor_years'] - std_term).abs().argsort()[:1]
                ]
                if not match.empty:
                    agg_rows.append({
                        'tenor': std_name,
                        'tenor_years': std_term,
                        'treasury_yield': match['treasury_yield'].values[0]
                    })
            treasury_agg = pd.DataFrame(agg_rows)

        # 5. 合并 SHIBOR 和国债（按期限对齐）
        if not shibor_df.empty and not treasury_agg.empty:
            merged_df = pd.merge(
                shibor_df[['tenor', 'tenor_years', 'shibor_rate']],
                treasury_agg[['tenor', 'treasury_yield']],
                on='tenor',
                how='outer'
            )
        elif not shibor_df.empty:
            merged_df = shibor_df[['tenor', 'tenor_years', 'shibor_rate']].copy()
            merged_df['treasury_yield'] = np.nan
        elif not treasury_agg.empty:
            merged_df = treasury_agg[['tenor', 'tenor_years', 'treasury_yield']].copy()
            merged_df['shibor_rate'] = np.nan
        else:
            merged_df = pd.DataFrame()

        # 添加交易日期
        if not merged_df.empty:
            merged_df['trade_date'] = trade_date

        logger.info("=" * 80)
        logger.info("收益率比较完成")
        logger.info("=" * 80)

        return merged_df, convertible_df, treasury_full_df

    def plot_comparison(self, shibor_treasury_df, convertible_df, trade_date, treasury_full_df=None, output_path=None, return_fig=False):
        """
        绘制收益率对比图

        参数:
        - shibor_treasury_df: SHIBOR 和国债的对比 DataFrame（聚合后）
        - convertible_df: 可转债 DataFrame
        - trade_date: 交易日期
        - treasury_full_df: 国债完整收益率曲线数据（可选，用于绘制完整曲线）
        - output_path: 输出图片路径
        - return_fig: 是否返回 figure 对象（用于嵌入 PDF）
        """
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False

        fig, ax = plt.subplots(figsize=(14, 8))

        # 1. 绘制 SHIBOR 利率
        if not shibor_treasury_df.empty and 'shibor_rate' in shibor_treasury_df.columns:
            shibor_data = shibor_treasury_df.dropna(subset=['shibor_rate']).sort_values('tenor_years')
            if not shibor_data.empty:
                ax.plot(shibor_data['tenor_years'], shibor_data['shibor_rate'],
                       marker='o', linewidth=2, label='SHIBOR 利率', color='#E41A1C', markersize=8)

        # 2. 绘制国债收益率（优先使用完整数据绘制完整曲线）
        if treasury_full_df is not None and not treasury_full_df.empty:
            treasury_all = treasury_full_df.dropna(subset=['treasury_yield']).sort_values('tenor_years')
            if not treasury_all.empty:
                ax.plot(treasury_all['tenor_years'], treasury_all['treasury_yield'],
                       linewidth=2, label='国债收益率曲线', color='#377EB8', alpha=0.8)
                # 在标准期限点打标记
                std_terms = sorted(self.treasury_term_to_name.keys())
                for term in std_terms:
                    match = treasury_all.iloc[(treasury_all['tenor_years'] - term).abs().argsort()[:1]]
                    if not match.empty:
                        ax.scatter(match['tenor_years'], match['treasury_yield'],
                                  marker='s', s=60, color='#377EB8', zorder=5)
        elif not shibor_treasury_df.empty and 'treasury_yield' in shibor_treasury_df.columns:
            # 备用：聚合数据画线
            treasury_data = shibor_treasury_df.dropna(subset=['treasury_yield']).sort_values('tenor_years')
            if not treasury_data.empty:
                ax.plot(treasury_data['tenor_years'], treasury_data['treasury_yield'],
                       marker='s', linewidth=2, label='国债收益率', color='#377EB8')

        # 3. 绘制可转债收益率（散点图 + 标签）
        if not convertible_df.empty:
            # 最低收益率
            bottom_df = convertible_df[convertible_df['yield_type'] == '最低收益率']
            if not bottom_df.empty:
                ax.scatter(bottom_df['tenor_years'], bottom_df['convertible_yield'],
                          marker='^', s=100, label='可转债收益率（最低10只）', color='#4DAF4A', alpha=0.7, edgecolors='black')
                for _, row in bottom_df.iterrows():
                    label_text = f"{row['ts_code']} {row['bond_full_name']}\nY={row.get('convertible_yield', 0):.2f}% D={row.get('duration', 0):.2f} C={row.get('convexity', 0):.2f}"
                    ax.annotate(label_text,
                               xy=(row['tenor_years'], row['convertible_yield']),
                               xytext=(8, -5), textcoords='offset points',
                               fontsize=6, ha='left', va='top', alpha=0.85)

            # 最高收益率
            top_df = convertible_df[convertible_df['yield_type'] == '最高收益率']
            if not top_df.empty:
                ax.scatter(top_df['tenor_years'], top_df['convertible_yield'],
                          marker='v', s=100, label='可转债收益率（最高10只）', color='#984EA3', alpha=0.7, edgecolors='black')
                for _, row in top_df.iterrows():
                    label_text = f"{row['ts_code']} {row['bond_full_name']}\nY={row.get('convertible_yield', 0):.2f}% D={row.get('duration', 0):.2f} C={row.get('convexity', 0):.2f}"
                    ax.annotate(label_text,
                               xy=(row['tenor_years'], row['convertible_yield']),
                               xytext=(8, 5), textcoords='offset points',
                               fontsize=6, ha='left', va='bottom', alpha=0.85)

        ax.set_xlabel('期限（年）', fontsize=12)
        ax.set_ylabel('利率 / 收益率 (%)', fontsize=12)
        ax.set_title(f'收益率对比分析 ({trade_date})', fontsize=14, fontweight='bold')
        ax.legend(loc='upper left', fontsize=10, framealpha=0.9)
        ax.grid(True, alpha=0.3)

        # 设置 x 轴刻度
        ax.set_xscale('log')
        ax.set_xticks([0.1, 0.25, 0.5, 1, 2, 3, 5, 10])
        ax.get_xaxis().set_major_formatter(plt.ScalarFormatter())
        ax.set_xticklabels(['0.1', '0.25', '0.5', '1', '2', '3', '5', '10'])

        plt.tight_layout()

        if return_fig:
            return fig

        # 保存图片
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(
                self.output_dir,
                f"收益率对比_{trade_date}_{timestamp}.png"
            )

        plt.savefig(output_path, dpi=200, bbox_inches='tight')
        logger.info(f"✅ 对比图已保存: {output_path}")

        plt.close()
        return output_path

    def run(self, trade_dates=None):
        """
        运行批量收益率比较流程，生成包含所有图表和专业金融分析的 PDF 报告

        参数:
        - trade_dates: 交易日期列表 (格式: ['YYYYMMDD', ...])，默认为今天
        """
        output_dir = os.path.join(CommonParameters.reportPath, 'YieldComparison')

        if trade_dates is None:
            trade_dates = [CommonParameters.today]
        elif isinstance(trade_dates, str):
            trade_dates = [trade_dates]

        if output_dir is None:
            output_dir = self.output_dir
        os.makedirs(output_dir, exist_ok=True)

        logger.info("=" * 80)
        logger.info(f"收益率批量比较分析开始，共 {len(trade_dates)} 个日期")
        logger.info(f"日期列表: {trade_dates}")
        logger.info("=" * 80)

        # 收集所有日期的分析结果
        all_results = []
        for trade_date in trade_dates:
            logger.info(f"\n>>> 处理日期: {trade_date}")
            try:
                shibor_treasury_df, convertible_df, treasury_full_df = self.compare_yields(trade_date)

                if not shibor_treasury_df.empty:
                    logger.info(f"SHIBOR vs 国债收益率对比 ({trade_date}):")
                    print(shibor_treasury_df.to_string(index=False))

                if not convertible_df.empty:
                    logger.info(f"可转债收益率（最高/最低）({trade_date}):")
                    print(convertible_df.to_string(index=False))

                all_results.append({
                    'trade_date': trade_date,
                    'shibor_treasury_df': shibor_treasury_df,
                    'convertible_df': convertible_df,
                    'treasury_full_df': treasury_full_df
                })
                logger.info(f">>> {trade_date} 处理完成")
            except Exception as e:
                logger.error(f">>> {trade_date} 处理失败: {e}", exc_info=True)
                continue

        if not all_results:
            logger.error("所有日期均未获取到有效数据，无法生成报告")
            return [], []

        # 生成 PDF 报告
        pdf_path = self._generate_pdf_report(all_results, output_dir)

        logger.info("=" * 80)
        logger.info(f"✅ 收益率批量比较分析完成")
        logger.info(f"📁 输出目录: {output_dir}")
        logger.info(f"📄 PDF 报告: {pdf_path}")
        logger.info("=" * 80)

        return [r['shibor_treasury_df'] for r in all_results], [r['convertible_df'] for r in all_results]

    # ============================================================
    # PDF 报告生成
    # ============================================================

    def _generate_pdf_report(self, all_results, output_dir):
        """
        生成包含所有日期图表和专业金融分析的 PDF 报告

        参数:
        - all_results: 每个日期分析结果的列表
        - output_dir: 输出目录
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f"收益率对比分析报告_{timestamp}.pdf"
        pdf_path = os.path.join(output_dir, pdf_filename)

        plt.rcParams['savefig.dpi'] = 200

        with PdfPages(pdf_path) as pdf:

            # ===== 封面 =====
            self._add_cover_page(pdf, all_results)

            # ===== 逐日图表 + 分析 =====
            prev_result = None
            for i, result in enumerate(all_results):
                trade_date = result['trade_date']
                logger.info(f"生成 PDF 页面: {trade_date} ({i+1}/{len(all_results)})")

                # 绘制收益率对比图
                fig = self.plot_comparison(
                    result['shibor_treasury_df'],
                    result['convertible_df'],
                    trade_date,
                    treasury_full_df=result['treasury_full_df'],
                    return_fig=True
                )
                pdf.savefig(fig)
                plt.close(fig)

                # 添加该日的金融分析
                analysis_fig = self._plot_single_day_analysis(result, prev_result)
                if analysis_fig is not None:
                    pdf.savefig(analysis_fig)
                    plt.close(analysis_fig)

                prev_result = result

            # ===== 跨日对比汇总分析 =====
            if len(all_results) >= 2:
                summary_fig = self._plot_cross_date_summary(all_results)
                if summary_fig is not None:
                    pdf.savefig(summary_fig)
                    plt.close(summary_fig)

                trend_fig = self._plot_cross_date_trend(all_results)
                if trend_fig is not None:
                    pdf.savefig(trend_fig)
                    plt.close(trend_fig)

                # ===== SHIBOR 跨日走势 =====
                shibor_ts_fig = self._plot_shibor_cross_date(all_results)
                if shibor_ts_fig is not None:
                    pdf.savefig(shibor_ts_fig)
                    plt.close(shibor_ts_fig)

                # ===== 可转债收益率-期限截面跨日对比 =====
                cb_curve_fig = self._plot_convertible_curve_cross_date(all_results)
                if cb_curve_fig is not None:
                    pdf.savefig(cb_curve_fig)
                    plt.close(cb_curve_fig)

                # ===== 可转债跨日走势（单独一页） =====
                cb_ts_fig = self._plot_convertible_cross_date(all_results)
                if cb_ts_fig is not None:
                    pdf.savefig(cb_ts_fig)
                    plt.close(cb_ts_fig)

        logger.info(f"PDF 报告已保存: {pdf_path}")
        return pdf_path

    def _add_cover_page(self, pdf, all_results):
        """生成 PDF 封面页"""
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

        fig = plt.figure(figsize=(12, 14))
        ax = fig.add_subplot(111)
        ax.axis('off')

        dates = [r['trade_date'] for r in all_results]

        title_lines = [
            "收益率对比分析报告",
            "Yield Comparison Analysis Report",
            "",
            f"分析日期范围: {dates[0]} ~ {dates[-1]}",
            f"共 {len(dates)} 个交易日",
            "",
            f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "分析内容:",
            "  1. SHIBOR 利率 (货币市场基准利率)",
            "  2. 国债收益率曲线 (无风险利率期限结构)",
            "  3. 可转债收益率 (信用债市场截面)",
            "",
            "分析维度:",
            "  - 利率期限结构 (Term Structure)",
            "  - 信用利差 (Credit Spread)",
            "  - 流动性溢价 (Liquidity Premium)",
            "  - 交易信号 (Trading Signals)",
        ]

        y_pos = 0.92
        for i, line in enumerate(title_lines):
            if i == 0:
                ax.text(0.5, y_pos, line, transform=ax.transAxes, fontsize=28,
                       fontweight='bold', ha='center', va='top', color='#1a1a2e')
                y_pos -= 0.07
            elif i == 1:
                ax.text(0.5, y_pos, line, transform=ax.transAxes, fontsize=14,
                       ha='center', va='top', color='#555555', style='italic')
                y_pos -= 0.05
            elif line == "":
                y_pos -= 0.02
            elif line.startswith("  -") or line.startswith("  1") or line.startswith("  2") or line.startswith("  3"):
                ax.text(0.15, y_pos, line, transform=ax.transAxes, fontsize=12,
                       ha='left', va='top', color='#333333')
                y_pos -= 0.025
            elif line.startswith("分析"):
                ax.text(0.5, y_pos, line, transform=ax.transAxes, fontsize=14,
                       fontweight='bold', ha='center', va='top', color='#1a1a2e')
                y_pos -= 0.035
            else:
                ax.text(0.5, y_pos, line, transform=ax.transAxes, fontsize=13,
                       ha='center', va='top', color='#444444')
                y_pos -= 0.03

        # 免责声明
        disclaimer = (
            "免责声明: 本报告仅供内部研究参考，不构成任何投资建议。"
            "数据来源: SHIBOR (Tushare) / 国债收益率 (Tushare yc_cb) / 可转债 (Tushare cb_daily)。"
        )
        ax.text(0.5, 0.05, disclaimer, transform=ax.transAxes, fontsize=8,
               ha='center', va='center', color='#999999', style='italic')

        pdf.savefig(fig)
        plt.close(fig)

    # ============================================================
    # 单日金融分析
    # ============================================================

    def _plot_single_day_analysis(self, result, prev_result=None):
        """
        生成单日的专业金融分析页（嵌入 PDF）

        参数:
        - result: 当前日期的分析结果 dict
        - prev_result: 前一日期的分析结果 dict（用于计算变动）
        """
        shibor_treasury_df = result['shibor_treasury_df']
        convertible_df = result['convertible_df']
        treasury_full_df = result['treasury_full_df']
        trade_date = result['trade_date']

        analysis_lines = self._generate_financial_analysis(
            shibor_treasury_df, convertible_df, treasury_full_df,
            trade_date, prev_result
        )

        if not analysis_lines:
            return None

        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

        fig = plt.figure(figsize=(12, len(analysis_lines) * 0.38 + 1.5))
        ax = fig.add_subplot(111)
        ax.axis('off')

        ax.text(0.5, 0.95, f"金融分析 — {trade_date}",
                transform=ax.transAxes, fontsize=15, fontweight='bold',
                ha='center', va='top', color='#1a1a2e')

        y_pos = 0.89
        for line in analysis_lines:
            if line.startswith("## "):
                # 小标题
                ax.text(0.05, y_pos, line[3:], transform=ax.transAxes,
                       fontsize=12, fontweight='bold', ha='left', va='top',
                       color='#2c3e50')
                y_pos -= 0.04
            elif line == "":
                y_pos -= 0.015
            elif line.startswith(">>> "):
                # 交易信号高亮
                ax.text(0.08, y_pos, line[4:], transform=ax.transAxes,
                       fontsize=10, ha='left', va='top',
                       color='#c0392b', fontweight='bold',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='#ffeaa7', alpha=0.8))
                y_pos -= 0.035
            else:
                wrapped = textwrap.fill(line, width=130)
                line_count = wrapped.count('\n') + 1
                ax.text(0.08, y_pos, wrapped, transform=ax.transAxes,
                       fontsize=9.5, ha='left', va='top', color='#333333')
                y_pos -= line_count * 0.028 + 0.008

        plt.tight_layout()
        return fig

    def _generate_financial_analysis(self, shibor_treasury_df, convertible_df, treasury_full_df,
                                      trade_date, prev_result=None):
        """
        从交易员视角生成专业金融分析文本

        返回:
        - analysis_lines: 分析文本行列表
        """
        lines = []

        if shibor_treasury_df.empty and convertible_df.empty:
            return None

        # ===== 1. 期限结构分析 (Term Structure) =====
        lines.append("## 1. 期限结构分析 (Term Structure)")

        # SHIBOR 分析
        if not shibor_treasury_df.empty and 'shibor_rate' in shibor_treasury_df.columns:
            shibor_valid = shibor_treasury_df.dropna(subset=['shibor_rate']).sort_values('tenor_years')
            if len(shibor_valid) >= 2:
                on_rate = shibor_valid[shibor_valid['tenor'] == 'ON']
                w1_rate = shibor_valid[shibor_valid['tenor'] == '1W']
                m1_rate = shibor_valid[shibor_valid['tenor'] == '1M']
                m3_rate = shibor_valid[shibor_valid['tenor'] == '3M']
                m6_rate = shibor_valid[shibor_valid['tenor'] == '6M']
                y1_rate = shibor_valid[shibor_valid['tenor'] == '1Y']

                on_val = on_rate['shibor_rate'].values[0] if not on_rate.empty else None
                m3_val = m3_rate['shibor_rate'].values[0] if not m3_rate.empty else None
                y1_val = y1_rate['shibor_rate'].values[0] if not y1_rate.empty else None

                lines.append(f"SHIBOR: O/N={on_val:.4f}% | 3M={m3_val:.4f}% | 1Y={y1_val:.4f}%" if all(v is not None for v in [on_val, m3_val, y1_val]) else "SHIBOR: 部分期限数据缺失")

                if on_val is not None and m3_val is not None:
                    spread_3m_on = (m3_val - on_val) * 100  # bp
                    lines.append(f"  SHIBOR 3M-ON 利差: {spread_3m_on:.1f}bp，"
                               f"反映{'流动性偏紧' if spread_3m_on > 50 else '流动性中性' if spread_3m_on > 20 else '流动性充裕'}")

        # 国债收益率期限结构
        if treasury_full_df is not None and not treasury_full_df.empty:
            treasury_sorted = treasury_full_df.sort_values('tenor_years')
            y2_row = treasury_sorted.iloc[(treasury_sorted['tenor_years'] - 2.0).abs().argsort()[:1]]
            y10_row = treasury_sorted.iloc[(treasury_sorted['tenor_years'] - 10.0).abs().argsort()[:1]]
            y1_row = treasury_sorted.iloc[(treasury_sorted['tenor_years'] - 1.0).abs().argsort()[:1]]
            y30_row = treasury_sorted.iloc[(treasury_sorted['tenor_years'] - 30.0).abs().argsort()[:1]]

            y2_val = y2_row['treasury_yield'].values[0] if not y2_row.empty else None
            y10_val = y10_row['treasury_yield'].values[0] if not y10_row.empty else None
            y1_val_t = y1_row['treasury_yield'].values[0] if not y1_row.empty else None
            y30_val = y30_row['treasury_yield'].values[0] if not y30_row.empty else None

            if y10_val is not None and y2_val is not None:
                spread_10y2y = (y10_val - y2_val) * 100
                signal = "曲线陡峭化 (Steepening)，长端风险溢价高" if spread_10y2y > 80 else \
                         "曲线平坦化 (Flattening)，市场预期经济放缓" if spread_10y2y < 30 else \
                         "期限结构正常"
                lines.append(f"国债: 1Y={y1_val_t:.2f}% | 2Y={y2_val:.2f}% | 10Y={y10_val:.2f}% | 30Y={y30_val:.2f}%" if y1_val_t is not None else "国债: 部分期限数据缺失")
                lines.append(f"  10Y-2Y 利差: {spread_10y2y:.1f}bp → {signal}")

                if y30_val is not None and y10_val is not None:
                    spread_30y10y = (y30_val - y10_val) * 100
                    lines.append(f"  30Y-10Y 利差: {spread_30y10y:.1f}bp，"
                               f"超长端{'仍有溢价' if spread_30y10y > 15 else '溢价压缩'}")

        # ===== 2. 信用利差分析 (Credit Spread) =====
        lines.append("")
        lines.append("## 2. 信用利差分析 (Credit Spread)")

        if not convertible_df.empty:
            bottom_cb = convertible_df[convertible_df['yield_type'] == '最低收益率']
            top_cb = convertible_df[convertible_df['yield_type'] == '最高收益率']

            if not bottom_cb.empty:
                min_cb = bottom_cb.iloc[0]
                lines.append(f"最低收益可转债: {min_cb['ts_code']} {min_cb['bond_full_name']} "
                           f"YTM={min_cb['convertible_yield']:.2f}% 久期={min_cb['duration']:.2f}")

            if not top_cb.empty:
                max_cb = top_cb.iloc[0]
                lines.append(f"最高收益可转债: {max_cb['ts_code']} {max_cb['bond_full_name']} "
                           f"YTM={max_cb['convertible_yield']:.2f}% 久期={max_cb['duration']:.2f}")

            if not bottom_cb.empty and not top_cb.empty:
                cb_spread = (max_cb['convertible_yield'] - min_cb['convertible_yield']) * 100
                lines.append(f"  可转债收益率极差: {cb_spread:.0f}bp，"
                           f"反映信用分层{'加剧' if cb_spread > 500 else '温和' if cb_spread > 200 else '较窄'}")

        # 可转债 vs 国债利差
        if not convertible_df.empty and treasury_full_df is not None and not treasury_full_df.empty:
            avg_cb_yield = convertible_df['convertible_yield'].mean()
            # 找相近期限的国债
            median_maturity = convertible_df['tenor_years'].median()
            nearest_t = treasury_full_df.iloc[(treasury_full_df['tenor_years'] - median_maturity).abs().argsort()[:1]]
            if not nearest_t.empty:
                credit_spread = (avg_cb_yield - nearest_t['treasury_yield'].values[0]) * 100
                lines.append(f"  平均信用利差 (CB vs 国债): {credit_spread:.0f}bp")

        # ===== 3. SHIBOR-国债流动性溢价 =====
        lines.append("")
        lines.append("## 3. 流动性溢价 (Liquidity Premium)")

        if not shibor_treasury_df.empty and 'shibor_rate' in shibor_treasury_df.columns and 'treasury_yield' in shibor_treasury_df.columns:
            common = shibor_treasury_df.dropna(subset=['shibor_rate', 'treasury_yield'])
            if not common.empty:
                avg_spread = (common['shibor_rate'] - common['treasury_yield']).mean() * 100
                m1_row = common[common['tenor'] == '1M']
                y1_row2 = common[common['tenor'] == '1Y']
                m1_spread = (m1_row['shibor_rate'] - m1_row['treasury_yield']).values[0] * 100 if not m1_row.empty else None
                y1_spread = (y1_row2['shibor_rate'] - y1_row2['treasury_yield']).values[0] * 100 if not y1_row2.empty else None

                lines.append(f"SHIBOR-国债平均利差: {avg_spread:.0f}bp (银行间资金成本 vs 无风险利率)")
                if m1_spread is not None:
                    lines.append(f"  1M 流动性溢价: {m1_spread:.0f}bp")
                if y1_spread is not None:
                    lines.append(f"  1Y 流动性溢价: {y1_spread:.0f}bp")

        # ===== 4. 与前日对比 =====
        if prev_result is not None:
            lines.append("")
            lines.append("## 4. 日间变动 (Day-over-Day Change)")

            prev_df = prev_result['shibor_treasury_df']
            if not shibor_treasury_df.empty and not prev_df.empty:
                curr_1y = shibor_treasury_df[shibor_treasury_df['tenor'] == '1Y']
                prev_1y = prev_df[prev_df['tenor'] == '1Y']
                if not curr_1y.empty and not prev_1y.empty and 'treasury_yield' in curr_1y.columns:
                    change_1y = (curr_1y['treasury_yield'].values[0] - prev_1y['treasury_yield'].values[0]) * 100
                    direction = "↑ 上行" if change_1y > 0 else "↓ 下行" if change_1y < 0 else "→ 持平"
                    lines.append(f"  1Y 国债收益率变动: {change_1y:+.1f}bp {direction}")

                curr_3m = shibor_treasury_df[shibor_treasury_df['tenor'] == '3M']
                prev_3m = prev_df[prev_df['tenor'] == '3M']
                if not curr_3m.empty and not prev_3m.empty and 'shibor_rate' in curr_3m.columns:
                    change_shibor = (curr_3m['shibor_rate'].values[0] - prev_3m['shibor_rate'].values[0]) * 100
                    lines.append(f"  3M SHIBOR 变动: {change_shibor:+.1f}bp "
                               f"{'↑ 上行' if change_shibor > 0 else '↓ 下行' if change_shibor < 0 else '→ 持平'}")

            # 可转债变动
            prev_cb = prev_result['convertible_df']
            if not convertible_df.empty and not prev_cb.empty:
                curr_avg = convertible_df['convertible_yield'].mean()
                prev_avg = prev_cb['convertible_yield'].mean()
                change_cb = (curr_avg - prev_avg) * 100
                lines.append(f"  可转债平均收益率变动: {change_cb:+.1f}bp")

        # ===== 5. 交易信号 (Trading Signals) =====
        lines.append("")
        lines.append("## 5. 交易信号 (Trading Signals)")

        signals = self._generate_trading_signals(
            shibor_treasury_df, convertible_df, treasury_full_df
        )
        if signals:
            for sig in signals:
                lines.append(f">>> {sig}")
        else:
            lines.append("  无显著交易信号")

        return lines

    def _generate_trading_signals(self, shibor_treasury_df, convertible_df, treasury_full_df):
        """
        生成可操作的交易信号

        返回:
        - signals: 交易信号字符串列表
        """
        signals = []

        # 信号1: 国债10Y-2Y 利差信号
        if treasury_full_df is not None and not treasury_full_df.empty:
            treasury_sorted = treasury_full_df.sort_values('tenor_years')
            y2_row = treasury_sorted.iloc[(treasury_sorted['tenor_years'] - 2.0).abs().argsort()[:1]]
            y10_row = treasury_sorted.iloc[(treasury_sorted['tenor_years'] - 10.0).abs().argsort()[:1]]
            y2_val = y2_row['treasury_yield'].values[0] if not y2_row.empty else None
            y10_val = y10_row['treasury_yield'].values[0] if not y10_row.empty else None

            if y10_val is not None and y2_val is not None:
                spread = (y10_val - y2_val) * 100
                if spread < 20:
                    signals.append(f"[利率] 10Y-2Y 利差仅 {spread:.0f}bp，曲线极度平坦，警惕衰退信号—建议减仓长端利率债")
                elif spread > 100:
                    signals.append(f"[利率] 10Y-2Y 利差达 {spread:.0f}bp，曲线陡峭—做陡曲线策略(Short 2Y, Long 10Y)有利")

        # 信号2: 可转债高收益机会
        if not convertible_df.empty:
            top_cb = convertible_df[convertible_df['yield_type'] == '最高收益率']
            if not top_cb.empty:
                high_yield_cbs = top_cb[top_cb['convertible_yield'] > 4.0]
                if not high_yield_cbs.empty:
                    cb_list = ", ".join(high_yield_cbs['ts_code'].tolist()[:3])
                    signals.append(f"[可转债] {len(high_yield_cbs)}只可转债YTM>4%: {cb_list}—高收益机会，关注信用风险")

            # 可转债利差极端
            bottom_cb = convertible_df[convertible_df['yield_type'] == '最低收益率']
            if not top_cb.empty and not bottom_cb.empty:
                spread = (top_cb.iloc[0]['convertible_yield'] - bottom_cb.iloc[0]['convertible_yield']) * 100
                if spread > 600:
                    signals.append(f"[信用] 可转债收益率极差 {spread:.0f}bp，信用分层严重—建议回避低评级CB，聚焦AAA")

        # 信号3: SHIBOR 流动性信号
        if not shibor_treasury_df.empty and 'shibor_rate' in shibor_treasury_df.columns:
            on_row = shibor_treasury_df[shibor_treasury_df['tenor'] == 'ON']
            m3_row = shibor_treasury_df[shibor_treasury_df['tenor'] == '3M']
            if not on_row.empty and not m3_row.empty:
                on_val = on_row['shibor_rate'].values[0]
                m3_val = m3_row['shibor_rate'].values[0]
                spread = (m3_val - on_val) * 100
                if spread > 80:
                    signals.append(f"[流动性] SHIBOR 3M-ON 利差 {spread:.0f}bp，资金面紧张—短端承压，关注央行OMO操作")
                elif spread < 15:
                    signals.append(f"[流动性] SHIBOR 3M-ON 利差仅 {spread:.0f}bp，流动性极度宽松—杠杆策略友好")

        # 信号4: SHIBOR vs 国债
        if not shibor_treasury_df.empty and 'shibor_rate' in shibor_treasury_df.columns and 'treasury_yield' in shibor_treasury_df.columns:
            common = shibor_treasury_df.dropna(subset=['shibor_rate', 'treasury_yield'])
            if not common.empty:
                avg_spread = (common['shibor_rate'] - common['treasury_yield']).mean() * 100
                if avg_spread > 80:
                    signals.append(f"[利差] SHIBOR-国债平均利差 {avg_spread:.0f}bp，银行间资金成本高企—关注利率债回调风险")

        return signals

    # ============================================================
    # 跨日对比汇总分析
    # ============================================================

    def _plot_cross_date_summary(self, all_results):
        """
        跨日对比汇总分析：展示各关键利率指标的时间序列变化
        """
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

        # 过滤无效日期
        valid_results = []
        pre_dates = []
        for r in all_results:
            try:
                pre_dates.append(datetime.strptime(r['trade_date'], '%Y%m%d'))
                valid_results.append(r)
            except ValueError:
                logger.warning(f"跨日汇总跳过无效日期: {r['trade_date']}")
                continue

        if len(valid_results) == 0:
            return None

        dates = []
        on_rates = []
        m3_rates = []
        y1_treasury = []
        y10_treasury = []
        cb_avg_yields = []
        cb_min_yields = []
        cb_max_yields = []
        spread_10y2y = []

        for idx, result in enumerate(valid_results):
            trade_date = result['trade_date']
            dates.append(pre_dates[idx])
            df = result['shibor_treasury_df']
            tf = result['treasury_full_df']
            cf = result['convertible_df']

            # SHIBOR
            on_row = df[df['tenor'] == 'ON']['shibor_rate'] if not df.empty and 'shibor_rate' in df.columns else pd.Series()
            m3_row = df[df['tenor'] == '3M']['shibor_rate'] if not df.empty and 'shibor_rate' in df.columns else pd.Series()
            on_rates.append(on_row.values[0] if not on_row.empty else np.nan)
            m3_rates.append(m3_row.values[0] if not m3_row.empty else np.nan)

            # 国债
            if tf is not None and not tf.empty:
                ts = tf.sort_values('tenor_years')
                yr1 = ts.iloc[(ts['tenor_years'] - 1.0).abs().argsort()[:1]]
                yr10 = ts.iloc[(ts['tenor_years'] - 10.0).abs().argsort()[:1]]
                yr2 = ts.iloc[(ts['tenor_years'] - 2.0).abs().argsort()[:1]]
                y1_t = yr1['treasury_yield'].values[0] if not yr1.empty else np.nan
                y10_t = yr10['treasury_yield'].values[0] if not yr10.empty else np.nan
                y2_t = yr2['treasury_yield'].values[0] if not yr2.empty else np.nan
                y1_treasury.append(y1_t)
                y10_treasury.append(y10_t)
                spread_10y2y.append((y10_t - y2_t) * 100 if not np.isnan(y10_t) and not np.isnan(y2_t) else np.nan)
            else:
                y1_treasury.append(np.nan)
                y10_treasury.append(np.nan)
                spread_10y2y.append(np.nan)

            # 可转债
            cb_avg_yields.append(cf['convertible_yield'].mean() if not cf.empty else np.nan)
            cb_min_yields.append(cf[cf['yield_type'] == '最低收益率']['convertible_yield'].min() if not cf.empty and 'yield_type' in cf.columns else np.nan)
            cb_max_yields.append(cf[cf['yield_type'] == '最高收益率']['convertible_yield'].max() if not cf.empty and 'yield_type' in cf.columns else np.nan)

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('跨日收益率走势汇总', fontsize=16, fontweight='bold', y=0.98)

        # 子图1: SHIBOR & 国债关键期限
        ax1 = axes[0, 0]
        ax1.plot(dates, on_rates, 'o-', color='#E41A1C', linewidth=1.5, markersize=5, label='SHIBOR ON')
        ax1.plot(dates, m3_rates, 's-', color='#FF7F00', linewidth=1.5, markersize=5, label='SHIBOR 3M')
        ax1.plot(dates, y1_treasury, '^-', color='#377EB8', linewidth=1.5, markersize=5, label='国债 1Y')
        ax1.plot(dates, y10_treasury, 'D-', color='#4DAF4A', linewidth=1.5, markersize=5, label='国债 10Y')
        ax1.set_title('关键期限收益率走势', fontsize=12, fontweight='bold')
        ax1.set_ylabel('收益率 (%)')
        ax1.legend(fontsize=8, loc='best')
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=30)

        # 子图2: 10Y-2Y 利差
        ax2 = axes[0, 1]
        valid_spreads = [(d, s) for d, s in zip(dates, spread_10y2y) if not np.isnan(s)]
        if valid_spreads:
            vd, vs = zip(*valid_spreads)
            colors = ['#c0392b' if s < 0 else '#FF7F00' if s < 30 else '#27ae60' for s in vs]
            ax2.bar(vd, vs, width=0.6, color=colors, alpha=0.8)
            ax2.axhline(y=0, color='#999999', linestyle='--', linewidth=1)
            ax2.axhline(y=50, color='#3498db', linestyle=':', linewidth=1, label='正常阈值 50bp')
        ax2.set_title('国债 10Y-2Y 利差 (期限结构陡峭度)', fontsize=12, fontweight='bold')
        ax2.set_ylabel('利差 (bp)')
        ax2.legend(fontsize=8)
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30)

        # 子图3: 可转债收益率
        ax3 = axes[1, 0]
        ax3.plot(dates, cb_avg_yields, 'o-', color='#8E44AD', linewidth=1.5, markersize=5, label='平均')
        ax3.plot(dates, cb_min_yields, 'v-', color='#27ae60', linewidth=1.5, markersize=5, label='最低10只')
        ax3.plot(dates, cb_max_yields, '^-', color='#e74c3c', linewidth=1.5, markersize=5, label='最高10只')
        ax3.fill_between(dates, cb_min_yields, cb_max_yields, alpha=0.15, color='#8E44AD')
        ax3.set_title('可转债收益率区间', fontsize=12, fontweight='bold')
        ax3.set_ylabel('收益率 (%)')
        ax3.legend(fontsize=8, loc='best')
        ax3.grid(True, alpha=0.3)
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=30)

        # 子图4: 信用利差 (CB平均 vs 国债)
        ax4 = axes[1, 1]
        cb_credit_spread = []
        for i, (cf, tf) in enumerate(zip(
            [r['convertible_df'] for r in valid_results],
            [r['treasury_full_df'] for r in valid_results]
        )):
            if not cf.empty and tf is not None and not tf.empty:
                avg_cb = cf['convertible_yield'].mean()
                median_mat = cf['tenor_years'].median()
                near_t = tf.iloc[(tf['tenor_years'] - median_mat).abs().argsort()[:1]]
                cs = (avg_cb - near_t['treasury_yield'].values[0]) * 100 if not near_t.empty else np.nan
            else:
                cs = np.nan
            cb_credit_spread.append(cs)

        ax4.plot(dates, cb_credit_spread, 's-', color='#E67E22', linewidth=2, markersize=6)
        ax4.axhline(y=200, color='#999999', linestyle='--', linewidth=1, label='200bp 参考线')
        ax4.set_title('信用利差 (可转债vs国债)', fontsize=12, fontweight='bold')
        ax4.set_ylabel('利差 (bp)')
        ax4.legend(fontsize=8)
        ax4.grid(True, alpha=0.3)
        ax4.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.setp(ax4.xaxis.get_majorticklabels(), rotation=30)

        plt.tight_layout(rect=[0, 0, 1, 0.95])
        return fig

    def _plot_cross_date_trend(self, all_results):
        """
        跨日趋势分析：SHIBOR各期限联动变化 & 国债曲线位移
        """
        if len(all_results) < 2:
            return None

        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

        # 过滤无效日期
        valid_results = []
        dates = []
        for r in all_results:
            try:
                dates.append(datetime.strptime(r['trade_date'], '%Y%m%d'))
                valid_results.append(r)
            except ValueError:
                logger.warning(f"跨日趋势跳过无效日期: {r['trade_date']}")
                continue

        if len(valid_results) < 2:
            return None

        # 提取每个日期SHIBOR各期限
        shibor_tenors = ['ON', '1W', '1M', '3M', '6M', '1Y']
        shibor_matrix = {t: [] for t in shibor_tenors}
        treasury_tenors = [1.0, 2.0, 3.0, 5.0, 10.0]
        treasury_matrix = {t: [] for t in treasury_tenors}

        for result in valid_results:
            df = result['shibor_treasury_df']
            tf = result['treasury_full_df']
            for tenor in shibor_tenors:
                if not df.empty and 'tenor' in df.columns and 'shibor_rate' in df.columns:
                    row = df[df['tenor'] == tenor]
                    shibor_matrix[tenor].append(row['shibor_rate'].values[0] if not row.empty else np.nan)
                else:
                    shibor_matrix[tenor].append(np.nan)
            if tf is not None and not tf.empty:
                for ty in treasury_tenors:
                    near = tf.iloc[(tf['tenor_years'] - ty).abs().argsort()[:1]]
                    treasury_matrix[ty].append(near['treasury_yield'].values[0] if not near.empty else np.nan)
            else:
                for ty in treasury_tenors:
                    treasury_matrix[ty].append(np.nan)

        fig, axes = plt.subplots(1, 2, figsize=(16, 7))
        fig.suptitle('利率曲线跨日移动分析', fontsize=14, fontweight='bold', y=0.98)

        # 子图1: SHIBOR 各期限变化
        ax1 = axes[0]
        x_pos = np.arange(len(shibor_tenors))
        width = 0.12
        colors = plt.cm.Reds(np.linspace(0.3, 0.9, len(dates)))

        for i, (date, d) in enumerate(zip(valid_results, dates)):
            values = [shibor_matrix[t][i] for t in shibor_tenors]
            valid = [v if not np.isnan(v) else 0 for v in values]
            ax1.bar(x_pos + i * width, valid, width, color=colors[i],
                   alpha=0.85, label=d.strftime('%m-%d'))

        ax1.set_title('SHIBOR 期限结构对比', fontsize=12, fontweight='bold')
        ax1.set_xticks(x_pos + width * (len(dates) - 1) / 2)
        ax1.set_xticklabels(shibor_tenors)
        ax1.set_ylabel('利率 (%)')
        ax1.legend(fontsize=8, ncol=min(len(dates), 4))
        ax1.grid(True, alpha=0.3, axis='y')

        # 子图2: 国债收益率曲线位移
        ax2 = axes[1]
        colors2 = plt.cm.Blues(np.linspace(0.3, 0.9, len(dates)))
        for i, (result, d) in enumerate(zip(valid_results, dates)):
            values = [treasury_matrix[ty][i] for ty in treasury_tenors]
            valid_points = [(tx, v) for tx, v in zip(treasury_tenors, values) if not np.isnan(v)]
            if valid_points:
                tx_vals, ty_vals = zip(*valid_points)
                ax2.plot(tx_vals, ty_vals, 'o-', color=colors2[i], linewidth=1.5,
                        markersize=5, label=d.strftime('%m-%d'), alpha=0.85)
                # 在最右边有效点加标签
                ax2.text(tx_vals[-1] + 0.15, ty_vals[-1], d.strftime('%m-%d'),
                        color=colors2[i], fontsize=9, va='center')

        ax2.set_title('国债收益率曲线位移', fontsize=12, fontweight='bold')
        ax2.set_xlabel('期限（年）')
        ax2.set_ylabel('收益率 (%)')
        ax2.legend(fontsize=8)
        ax2.grid(True, alpha=0.3)

        # 分析注释
        if len(dates) >= 2:
            first = valid_results[0]
            last = valid_results[-1]
            # 国债 10Y 变化
            first_tf = first['treasury_full_df']
            last_tf = last['treasury_full_df']
            if first_tf is not None and not first_tf.empty and last_tf is not None and not last_tf.empty:
                f10 = first_tf.iloc[(first_tf['tenor_years'] - 10.0).abs().argsort()[:1]]
                l10 = last_tf.iloc[(last_tf['tenor_years'] - 10.0).abs().argsort()[:1]]
                if not f10.empty and not l10.empty:
                    change = (l10['treasury_yield'].values[0] - f10['treasury_yield'].values[0]) * 100
                    direction = "上行" if change > 0 else "下行"
                    trend_type = ("熊平 (Bear Flattening)—短端上行更快" if change > 0 and
                        valid_results[-1]['shibor_treasury_df']['shibor_rate'].dropna().mean() >
                        valid_results[0]['shibor_treasury_df']['shibor_rate'].dropna().mean() else
                        "牛陡 (Bull Steepening)—长端下行") if change < 0 else "横盘整理"

                    ax2.text(0.5, -0.2,
                           f"期间10Y国债变动: {change:+.0f}bp ({direction}) | 形态: {trend_type}",
                           transform=ax2.transAxes, fontsize=10, ha='center',
                           color='#c0392b' if change > 0 else '#27ae60',
                           fontweight='bold')

        plt.tight_layout(rect=[0, 0.05, 1, 0.93])
        return fig

    def _plot_shibor_cross_date(self, all_results):
        """
        SHIBOR 收益率曲线跨日对比：期限作 X 轴，收益率作 Y 轴
        """
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

        # 过滤无效日期
        valid_results = []
        for r in all_results:
            try:
                datetime.strptime(r['trade_date'], '%Y%m%d')
                valid_results.append(r)
            except ValueError:
                logger.warning(f"SHIBOR跨日跳过无效日期: {r['trade_date']}")
                continue

        if len(valid_results) < 2:
            return None

        shibor_tenors = ['ON', '1W', '1M', '3M', '6M', '1Y']
        x_positions = list(range(len(shibor_tenors)))

        fig, ax = plt.subplots(figsize=(14, 8))
        colors = plt.cm.tab10(np.linspace(0, 1, len(valid_results)))
        markers = ['o', 's', '^', 'D', 'v', 'p', 'h', '*', 'X', 'P']

        for i, result in enumerate(valid_results):
            df = result['shibor_treasury_df']
            date_str = result['trade_date']
            y_vals = []
            for tenor in shibor_tenors:
                if not df.empty and 'tenor' in df.columns and 'shibor_rate' in df.columns:
                    row = df[df['tenor'] == tenor]
                    y_vals.append(row['shibor_rate'].values[0] if not row.empty else np.nan)
                else:
                    y_vals.append(np.nan)

            ax.plot(x_positions, y_vals, marker=markers[i % len(markers)],
                    color=colors[i], linewidth=1.8, markersize=7,
                    label=date_str, alpha=0.85)

            # 在最右边有效点加日期标签
            valid_xy = [(x, y) for x, y in zip(x_positions, y_vals) if not np.isnan(y)]
            if valid_xy:
                last_x, last_y = valid_xy[-1]
                ax.text(last_x + 0.15, last_y, date_str,
                        color=colors[i], fontsize=9, va='center')

            # 添加数值标签（数据点不多时）
            if len(valid_results) <= 6:
                for x, y in zip(x_positions, y_vals):
                    if not np.isnan(y):
                        ax.annotate(f'{y:.2f}', (x, y), textcoords="offset points",
                                   xytext=(0, 10), fontsize=7, ha='center', alpha=0.7)

        ax.set_title('SHIBOR 收益率曲线跨日对比', fontsize=16, fontweight='bold')
        ax.set_ylabel('利率 (%)', fontsize=12)
        ax.set_xlabel('期限', fontsize=12)
        ax.set_xticks(x_positions)
        ax.set_xticklabels(shibor_tenors)
        ax.legend(fontsize=10, ncol=2, loc='best', framealpha=0.9)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        return fig

    def _plot_convertible_cross_date(self, all_results):
        """
        可转债跨日对比走势图（前10/后10，单独一页，内容较多）
        """
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

        # 过滤无效日期
        valid_results = []
        dates = []
        for r in all_results:
            try:
                dates.append(datetime.strptime(r['trade_date'], '%Y%m%d'))
                valid_results.append(r)
            except ValueError:
                logger.warning(f"可转债跨日跳过无效日期: {r['trade_date']}")
                continue

        # 筛选有可转债数据的日期
        cb_valid_results = []
        cb_dates = []
        for r in valid_results:
            cf = r['convertible_df']
            if not cf.empty and 'convertible_yield' in cf.columns:
                cb_valid_results.append(r)
                cb_dates.append(datetime.strptime(r['trade_date'], '%Y%m%d'))

        if len(cb_valid_results) < 2:
            return None

        # 追踪每只可转债在各日期的收益率
        # 收集所有在任意日期出现的可转债
        all_bonds = set()
        bond_meta = {}  # ts_code -> (name, duration, convexity)
        for r in cb_valid_results:
            cf = r['convertible_df']
            for _, row in cf.iterrows():
                ts = row['ts_code']
                all_bonds.add(ts)
                if ts not in bond_meta:
                    name = row.get('bond_full_name', ts)
                    dur = row.get('duration', np.nan)
                    cvx = row.get('convexity', np.nan)
                    bond_meta[ts] = (name, dur, cvx)

        # 构建每只可转债的时间序列
        date_str_list = [r['trade_date'] for r in cb_valid_results]
        bond_series = {}
        for bond in all_bonds:
            bond_series[bond] = []
            for r in cb_valid_results:
                cf = r['convertible_df']
                row = cf[cf['ts_code'] == bond]
                if not row.empty:
                    bond_series[bond].append(row['convertible_yield'].values[0])
                else:
                    bond_series[bond].append(np.nan)

        # 计算每只可转债的平均收益率，用于分类前10/后10
        bond_avg_yield = {}
        for bond, vals in bond_series.items():
            valid_vals = [v for v in vals if not np.isnan(v)]
            if valid_vals:
                bond_avg_yield[bond] = np.mean(valid_vals)

        sorted_bonds = sorted(bond_avg_yield.items(), key=lambda x: x[1])
        top10_bonds = sorted_bonds[:10]  # 最低收益率（前10 = 最强信用）
        bottom10_bonds = sorted_bonds[-10:]  # 最高收益率（后10 = 最弱信用）

        # 按收益率排序后10
        bottom10_bonds = sorted(bottom10_bonds, key=lambda x: x[1], reverse=True)

        fig, axes = plt.subplots(2, 1, figsize=(20, 16))
        fig.suptitle('可转债收益率跨日走势（前10 / 后10）', fontsize=18, fontweight='bold', y=0.98)

        # ===== 上子图：前10（最低收益率） =====
        ax1 = axes[0]
        colors_top = plt.cm.Greens(np.linspace(0.3, 0.9, 10))
        markers_top = ['o', 's', '^', 'D', 'v', 'p', 'h', '*', 'X', 'P']

        for i, (bond, avg_y) in enumerate(top10_bonds):
            values = bond_series[bond]
            # 只画有数据的点
            valid_idx = [(j, v) for j, v in enumerate(values) if not np.isnan(v)]
            if valid_idx:
                idxs, vals = zip(*valid_idx)
                plot_dates = [cb_dates[j] for j in idxs]
                name, dur, cvx = bond_meta.get(bond, (bond, np.nan, np.nan))
                # 截断长名称
                short_name = name[:10] + '...' if len(str(name)) > 10 else name
                dur_str = f'D={dur:.1f}' if not np.isnan(dur) else 'D=-'
                cvx_str = f'C={cvx:.1f}' if not np.isnan(cvx) else 'C=-'
                label = f'{bond} | {short_name} | {dur_str} | {cvx_str}'
                ax1.plot(plot_dates, vals, marker=markers_top[i], color=colors_top[i],
                        linewidth=1.5, markersize=7, label=label, alpha=0.85)

        ax1.set_title('前10可转债（最低收益率 — 信用最强）', fontsize=14, fontweight='bold', color='#27ae60')
        ax1.set_ylabel('收益率 (%)', fontsize=11)
        ax1.legend(fontsize=7, ncol=2, loc='best', framealpha=0.9)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=30)

        # Min-Max 填充带
        all_top_vals = []
        for j in range(len(cb_dates)):
            day_vals = [bond_series[b][j] for b, _ in top10_bonds if not np.isnan(bond_series[b][j])]
            if day_vals:
                all_top_vals.append((min(day_vals), max(day_vals)))
            else:
                all_top_vals.append((np.nan, np.nan))

        top_min = [x[0] for x in all_top_vals]
        top_max = [x[1] for x in all_top_vals]
        if not all(np.isnan(top_min)):
            ax1.fill_between(cb_dates, top_min, top_max, alpha=0.1, color='#27ae60')
            ax1.plot(cb_dates, top_min, '--', color='#27ae60', alpha=0.4, linewidth=0.8)
            ax1.plot(cb_dates, top_max, '--', color='#27ae60', alpha=0.4, linewidth=0.8)

        # ===== 下子图：后10（最高收益率） =====
        ax2 = axes[1]
        colors_bot = plt.cm.Reds(np.linspace(0.3, 0.9, 10))
        markers_bot = ['o', 's', '^', 'D', 'v', 'p', 'h', '*', 'X', 'P']

        for i, (bond, avg_y) in enumerate(bottom10_bonds):
            values = bond_series[bond]
            valid_idx = [(j, v) for j, v in enumerate(values) if not np.isnan(v)]
            if valid_idx:
                idxs, vals = zip(*valid_idx)
                plot_dates = [cb_dates[j] for j in idxs]
                name, dur, cvx = bond_meta.get(bond, (bond, np.nan, np.nan))
                short_name = name[:10] + '...' if len(str(name)) > 10 else name
                dur_str = f'D={dur:.1f}' if not np.isnan(dur) else 'D=-'
                cvx_str = f'C={cvx:.1f}' if not np.isnan(cvx) else 'C=-'
                label = f'{bond} | {short_name} | {dur_str} | {cvx_str}'
                ax2.plot(plot_dates, vals, marker=markers_bot[i], color=colors_bot[i],
                        linewidth=1.5, markersize=7, label=label, alpha=0.85)

        ax2.set_title('后10可转债（最高收益率 — 信用最弱）', fontsize=14, fontweight='bold', color='#e74c3c')
        ax2.set_ylabel('收益率 (%)', fontsize=11)
        ax2.set_xlabel('日期', fontsize=11)
        ax2.legend(fontsize=7, ncol=2, loc='best', framealpha=0.9)
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30)

        # Min-Max 填充带
        all_bot_vals = []
        for j in range(len(cb_dates)):
            day_vals = [bond_series[b][j] for b, _ in bottom10_bonds if not np.isnan(bond_series[b][j])]
            if day_vals:
                all_bot_vals.append((min(day_vals), max(day_vals)))
            else:
                all_bot_vals.append((np.nan, np.nan))

        bot_min = [x[0] for x in all_bot_vals]
        bot_max = [x[1] for x in all_bot_vals]
        if not all(np.isnan(bot_min)):
            ax2.fill_between(cb_dates, bot_min, bot_max, alpha=0.1, color='#e74c3c')
            ax2.plot(cb_dates, bot_min, '--', color='#e74c3c', alpha=0.4, linewidth=0.8)
            ax2.plot(cb_dates, bot_max, '--', color='#e74c3c', alpha=0.4, linewidth=0.8)

        plt.tight_layout(rect=[0, 0, 1, 0.96])
        return fig

    def _plot_convertible_curve_cross_date(self, all_results):
        """
        可转债收益率-期限截面跨日对比（参考 SHIBOR 曲线风格）
        X 轴=期限（年），Y 轴=收益率，每个日期一条散点+趋势线
        """
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

        valid_results = []
        for r in all_results:
            try:
                datetime.strptime(r['trade_date'], '%Y%m%d')
                valid_results.append(r)
            except ValueError:
                continue

        cb_results = [r for r in valid_results if not r['convertible_df'].empty]
        if len(cb_results) < 1:
            return None

        fig, axes = plt.subplots(1, 2, figsize=(16, 7))
        fig.suptitle('可转债收益率-期限截面跨日对比', fontsize=16, fontweight='bold', y=0.98)

        colors = plt.cm.tab10(np.linspace(0, 1, len(cb_results)))
        markers = ['o', 's', '^', 'D', 'v', 'p', 'h', '*', 'X', 'P']

        # ===== 左子图：前10最低收益率 =====
        ax1 = axes[0]
        for i, result in enumerate(cb_results):
            df = result['convertible_df']
            bottom = df[df['yield_type'] == '最低收益率']
            if bottom.empty:
                continue
            x = bottom['tenor_years'].astype(float).values
            y = bottom['convertible_yield'].astype(float).values
            ax1.scatter(x, y, color=colors[i], s=80, alpha=0.7,
                       label=result['trade_date'], marker=markers[i % len(markers)],
                       edgecolors='black', linewidth=0.5, zorder=3)
            # 线性拟合趋势线
            if len(x) >= 2:
                z = np.polyfit(x, y, 1)
                p = np.poly1d(z)
                x_line = np.linspace(np.min(x), np.max(x), 100)
                ax1.plot(x_line, p(x_line), '--', color=colors[i], alpha=0.5, linewidth=1.5)

        ax1.set_title('前10最低收益率', fontsize=13, fontweight='bold', color='#27ae60')
        ax1.set_xlabel('期限（年）', fontsize=11)
        ax1.set_ylabel('收益率 (%)', fontsize=11)
        ax1.legend(fontsize=8, ncol=2, loc='best')
        ax1.grid(True, alpha=0.3)

        # ===== 右子图：后10最高收益率 =====
        ax2 = axes[1]
        for i, result in enumerate(cb_results):
            df = result['convertible_df']
            top = df[df['yield_type'] == '最高收益率']
            if top.empty:
                continue
            x = top['tenor_years'].astype(float).values
            y = top['convertible_yield'].astype(float).values
            ax2.scatter(x, y, color=colors[i], s=80, alpha=0.7,
                       label=result['trade_date'], marker=markers[i % len(markers)],
                       edgecolors='black', linewidth=0.5, zorder=3)
            if len(x) >= 2:
                z = np.polyfit(x, y, 1)
                p = np.poly1d(z)
                x_line = np.linspace(np.min(x), np.max(x), 100)
                ax2.plot(x_line, p(x_line), '--', color=colors[i], alpha=0.5, linewidth=1.5)

        ax2.set_title('后10最高收益率', fontsize=13, fontweight='bold', color='#e74c3c')
        ax2.set_xlabel('期限（年）', fontsize=11)
        ax2.set_ylabel('收益率 (%)', fontsize=11)
        ax2.legend(fontsize=8, ncol=2, loc='best')
        ax2.grid(True, alpha=0.3)

        plt.tight_layout(rect=[0, 0, 1, 0.93])
        return fig







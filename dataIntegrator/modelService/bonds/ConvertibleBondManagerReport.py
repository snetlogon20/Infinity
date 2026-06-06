import os
import textwrap
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd

from dataIntegrator import CommonLib
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

logger = CommonLib.logger

# 中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class ConvertibleBondManagerReport:
    """可转债全景报表：查询三表 JOIN 结果、落盘、生成 PDF 策略报告"""

    REPORT_DIR = r"D:\workspace_python\infinity_data\outbound\report\ConvertibleBondAnalysis"

    CHART_FIELDS = [
        ('d.pre_close',          'Pre_Close',          'Pre_Close 走势'),
        ('d.pct_chg',            'Pct_Chg(%)',         '涨跌幅 走势'),
        ('d.vol',                '成交量(手)',            '成交量 走势'),
        ('d.amount',             '成交额(千元)',          '成交额 走势'),
        ('m.ytm',                'YTM',                '到期收益率(YTM) 走势'),
        ('m.modified_duration',  '修正久期',              '修正久期 走势'),
        ('m.convexity',          '凸性',                '凸性 走势'),
        ('m.dv01',               'DV01',               'DV01 走势'),
        ('m.pvbp',               'PVBP',               'PVBP 走势'),
        ('m.simple_ytm',         'Simple YTM',         '简易到期收益率 走势'),
        ('m.current_yield',      'Current Yield',       '当期收益率 走势'),
        ('m.var_hist_99',        '历史VaR 99%(%)',      '历史VaR(99%置信) 走势'),
        ('m.var_param_99',       '参数VaR 99%(%)',      '参数VaR(99%置信) 走势'),
        ('m.es_99',              'ES 99%(%)',          'Expected Shortfall(99%) 走势'),
        ('m.var_price_hist_99',  '历史VaR 99%(元)',      '历史VaR(99%置信,元) 走势'),
        ('m.var_price_param_99', '参数VaR 99%(元)',      '参数VaR(99%置信,元) 走势'),
        ('m.es_price_99',        'ES 99%(元)',          'ES(99%置信,元) 走势'),
        ('m.effective_duration',    '有效久期',              '有效久期 走势'),
        ('m.effective_convexity',   '有效凸性',              '有效凸性 走势'),
        ('m.pct_price_chg_p50bp',   '价格变动 +50bp(%)',      '收益率+50bp价格变动 走势'),
        ('m.pct_price_chg_m50bp',   '价格变动 -50bp(%)',      '收益率-50bp价格变动 走势'),
        ('m.pct_price_chg_p100bp',  '价格变动 +100bp(%)',     '收益率+100bp价格变动 走势'),
        ('m.pct_price_chg_m100bp',  '价格变动 -100bp(%)',     '收益率-100bp价格变动 走势'),
    ]

    def __init__(self):
        self.clickhouse_service = ClickhouseService()

    # ==================== 数据查询 ====================

    def query_panorama(self, start_date, end_date):
        sql = f"""
            SELECT
                b.ts_code,
                b.bond_full_name,
                b.bond_short_name,
                b.cb_code,
                b.cb_type,
                b.stk_code,
                b.stk_short_name,
                b.maturity,
                b.par,
                b.issue_price,
                b.issue_size,
                b.remain_size,
                b.value_date,
                b.maturity_date,
                b.rate_type,
                b.coupon_rate,
                b.add_rate,
                b.pay_per_year,
                b.list_date,
                b.delist_date,
                b.exchange,
                b.conv_start_date,
                b.conv_end_date,
                b.conv_stop_date,
                b.first_conv_price,
                b.conv_price,
                b.rate_clause,
                b.put_clause,
                b.maturity_call_price,
                b.call_clause,
                b.reset_clause,
                b.conv_clause,
                b.guarantor,
                b.guarantee_type,
                b.issue_rating,
                b.newest_rating,
                b.rating_comp,
                d.ts_code        AS daily_ts_code,
                d.trade_date,
                d.pre_close,
                d.open,
                d.high,
                d.low,
                d.close,
                d.change,
                d.pct_chg,
                d.vol,
                d.amount,
                d.bond_value,
                d.bond_over_rate,
                d.cb_value,
                d.cb_over_rate,
                m.is_feasible,
                m.description,
                m.ytm,
                m.macaulay_duration,
                m.modified_duration,
                m.convexity,
                m.dv01,
                m.pvbp,
                m.remaining_years,
                m.current_yield,
                m.simple_ytm,
                m.market_price,
                m.par             AS metrics_par,
                m.coupon_rate     AS metrics_coupon_rate,
                m.pay_per_year    AS metrics_pay_per_year,
                m.var_hist_99,
                m.var_param_99,
                m.es_99,
                m.var_price_hist_99,
                m.var_price_param_99,
                m.es_price_99,
                m.effective_duration,
                m.effective_convexity,
                m.pct_price_chg_p50bp,
                m.pct_price_chg_m50bp,
                m.pct_price_chg_p100bp,
                m.pct_price_chg_m100bp
            FROM indexsysdb.df_tushare_cb_daily d
            LEFT JOIN indexsysdb.df_tushare_cb_basic b
                ON d.ts_code = b.ts_code
            LEFT JOIN indexsysdb.df_tushare_cb_metrics m
                ON d.ts_code = m.ts_code AND d.trade_date = m.trade_date
            WHERE d.trade_date >= '{start_date}'
              AND d.trade_date <= '{end_date}'
            ORDER BY d.trade_date, b.ts_code
            """

        logger.info(f"查询可转债全景数据: {start_date} ~ {end_date}")
        df = self.clickhouse_service.getDataFrameWithoutColumnsName(sql)
        logger.info(f"查询完成，共 {len(df)} 条记录")
        return df

    # ==================== 数据落盘 ====================

    def save_to_file(self, df, file_name_prefix):
        os.makedirs(self.REPORT_DIR, exist_ok=True)
        file_path = os.path.join(self.REPORT_DIR, f"{file_name_prefix}.parquet")
        df.to_parquet(file_path, index=False)
        logger.info(f"数据已保存: {file_path}")
        return file_path

    # ==================== 数据准备 ====================

    def _prepare_data(self, df):
        """统一数据预处理：添加 series_name, 转换日期"""
        ts_code_col = 'daily_ts_code' if 'daily_ts_code' in df.columns else 'b.ts_code'
        name_col = 'b.bond_full_name'
        date_col = 'd.trade_date'

        df = df.copy()
        df['series_name'] = df[ts_code_col].fillna('') + ' ' + df[name_col].fillna('')
        df[date_col] = pd.to_datetime(df[date_col], format='%Y%m%d')
        return df

    # ==================== 统计分析 ====================

    def _compute_analysis_stats(self, df):
        """计算策略分析所需的核心统计指标"""
        stats = {}

        # ----- 基础信息 -----
        stats['total_bonds'] = df['series_name'].nunique()
        stats['total_dates'] = df['d.trade_date'].nunique()
        stats['total_records'] = len(df)

        # ----- 涨跌统计 -----
        pct = df['d.pct_chg'].dropna()
        stats['avg_pct_chg'] = pct.mean()
        stats['median_pct_chg'] = pct.median()
        stats['std_pct_chg'] = pct.std()
        stats['positive_days_pct'] = (pct > 0).mean() * 100
        stats['up_days'] = int((pct > 0).sum())
        stats['down_days'] = int((pct < 0).sum())

        # ----- 成交量统计 -----
        vol = df['d.vol'].dropna()
        stats['avg_vol'] = vol.mean()
        stats['max_vol'] = vol.max()
        stats['vol_trend'] = '放量' if vol.iloc[-10:].mean() > vol.iloc[:10].mean() else '缩量'

        # ----- YTM 统计 -----
        ytm = df['m.ytm'].dropna()
        stats['avg_ytm'] = ytm.mean()
        stats['min_ytm'] = ytm.min()
        stats['max_ytm'] = ytm.max()
        # 债券收益率区间分布
        stats['ytm_positive_pct'] = (ytm > 0).mean() * 100

        # ----- 久期与凸性 -----
        dur = df['m.modified_duration'].dropna()
        stats['avg_duration'] = dur.mean()
        stats['max_duration'] = dur.max()

        conv = df['m.convexity'].dropna()
        stats['avg_convexity'] = conv.mean()

        # ----- 有效久期 & 有效凸性 & 价格变动 -----
        eff_dur = df['m.effective_duration'].dropna()
        stats['avg_effective_duration'] = eff_dur.mean()
        stats['max_effective_duration'] = eff_dur.max()

        eff_conv = df['m.effective_convexity'].dropna()
        stats['avg_effective_convexity'] = eff_conv.mean()
        stats['max_effective_convexity'] = eff_conv.max()

        pct_50 = df['m.pct_price_chg_p50bp'].dropna()
        stats['avg_pct_price_chg_p50bp'] = pct_50.mean()
        stats['min_pct_price_chg_p50bp'] = pct_50.min()
        stats['max_pct_price_chg_p50bp'] = pct_50.max()

        pct_100 = df['m.pct_price_chg_p100bp'].dropna()
        stats['avg_pct_price_chg_p100bp'] = pct_100.mean()
        stats['min_pct_price_chg_p100bp'] = pct_100.min()
        stats['max_pct_price_chg_p100bp'] = pct_100.max()

        # ----- VaR & ES 统计 -----
        var_hist = df['m.var_hist_99'].dropna()
        stats['avg_var_hist_99'] = var_hist.mean()
        stats['max_var_hist_99'] = var_hist.max()

        var_param = df['m.var_param_99'].dropna()
        stats['avg_var_param_99'] = var_param.mean()
        stats['max_var_param_99'] = var_param.max()

        es = df['m.es_99'].dropna()
        stats['avg_es_99'] = es.mean()
        stats['max_es_99'] = es.max()

        var_price_hist = df['m.var_price_hist_99'].dropna()
        stats['avg_var_price_hist_99'] = var_price_hist.mean()
        stats['max_var_price_hist_99'] = var_price_hist.max()

        var_price_param = df['m.var_price_param_99'].dropna()
        stats['avg_var_price_param_99'] = var_price_param.mean()
        stats['max_var_price_param_99'] = var_price_param.max()

        es_price = df['m.es_price_99'].dropna()
        stats['avg_es_price_99'] = es_price.mean()
        stats['max_es_price_99'] = es_price.max()

        # ----- 首末日数据对比（趋势判断）-----
        first_date = df['d.trade_date'].min()
        last_date = df['d.trade_date'].max()
        first_day = df[df['d.trade_date'] == first_date]
        last_day = df[df['d.trade_date'] == last_date]

        if not first_day.empty and not last_day.empty:
            common_bonds = set(first_day['series_name']) & set(last_day['series_name'])
            if common_bonds:
                first_avg = first_day[first_day['series_name'].isin(common_bonds)]['d.pre_close'].mean()
                last_avg = last_day[last_day['series_name'].isin(common_bonds)]['d.pre_close'].mean()
                stats['price_change_pct'] = (last_avg - first_avg) / first_avg * 100 if first_avg else 0
                stats['period_return'] = stats['price_change_pct']
            else:
                stats['price_change_pct'] = 0
                stats['period_return'] = 0
        else:
            stats['price_change_pct'] = 0
            stats['period_return'] = 0

        # ----- 活跃度 -----
        stats['active_bonds'] = df.groupby('series_name')['d.vol'].sum().gt(0).sum()
        stats['inactive_bonds'] = stats['total_bonds'] - stats['active_bonds']

        return stats

    # ==================== PDF 策略报告 ====================

    def _add_text_page(self, pdf, title, lines, subtitle=None):
        """向 PDF 添加一页纯文本分析页"""
        fig, ax = plt.subplots(figsize=(12, 14))
        ax.axis('off')
        y = 0.96

        # 标题
        ax.text(0.5, y, title, transform=ax.transAxes, ha='center', fontsize=20,
                fontweight='bold', color='#1a1a2e')
        y -= 0.06

        if subtitle:
            ax.text(0.5, y, subtitle, transform=ax.transAxes, ha='center', fontsize=11,
                    color='#666666')
            y -= 0.04

        # 分隔线
        ax.axhline(y=y + 0.005, xmin=0.15, xmax=0.85, color='#e94560', linewidth=2)

        y -= 0.03

        # 正文
        for line in lines:
            if line.startswith('##'):
                y -= 0.01
                ax.text(0.08, y, line[2:].strip(), transform=ax.transAxes, fontsize=14,
                        fontweight='bold', color='#16213e')
                y -= 0.045
            elif line.startswith('###'):
                ax.text(0.08, y, line[3:].strip(), transform=ax.transAxes, fontsize=12,
                        fontweight='bold', color='#0f3460')
                y -= 0.04
            elif line == '---':
                y -= 0.01
                ax.axhline(y=y, xmin=0.08, xmax=0.92, color='#cccccc', linewidth=0.5,
                           transform=ax.transAxes)
                y -= 0.02
            elif line.strip() == '':
                y -= 0.01
            else:
                wrapped = textwrap.wrap(line, width=90)
                for w in wrapped:
                    ax.text(0.08, y, w, transform=ax.transAxes, fontsize=10,
                            color='#333333', linespacing=1.3)
                    y -= 0.03
                y -= 0.005

            if y < 0.04:
                break

        pdf.savefig(fig)
        plt.close(fig)

    def _generate_line_chart_fig(self, df, value_col, y_label, title_suffix, top_n=20):
        """返回折线图 Figure（用于拼入 PDF），只展示 y 值最大的 top_n 条"""
        df = df.dropna(subset=[value_col])
        if df.empty:
            return None

        pivot = df.pivot_table(
            index='d.trade_date',
            columns='series_name',
            values=value_col,
            aggfunc='first'
        ).sort_index()

        # 选出 y 绝对值最大的 top_n 条曲线
        if len(pivot.columns) > top_n:
            max_abs_values = pivot.abs().max()
            top_columns = max_abs_values.nlargest(top_n).index.tolist()
            pivot = pivot[top_columns]

        series_count = len(pivot.columns)

        # 高分辨率 + 大画布，确保清晰度
        fig, ax = plt.subplots(figsize=(20, 10), dpi=200)
        fig.set_dpi(200)

        # 使用支持中文的字体，避免模糊渲染
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False

        colors = plt.cm.tab20.colors + plt.cm.tab20b.colors

        for i, col in enumerate(pivot.columns):
            series_data = pivot[col].dropna()
            if series_data.empty:
                continue

            color = colors[i % len(colors)]
            ax.plot(
                series_data.index, series_data.values,
                marker='o' if series_count <= 15 else None,
                markersize=3,
                linewidth=1.2,
                color=color,
                label=col,
                alpha=0.8
            )

            # 在曲线最右侧添加 ts_code + 名称标签（放大字号）
            last_date = series_data.index[-1]
            last_val = series_data.values[-1]
            ax.annotate(
                col, xy=(last_date, last_val),
                xytext=(6, 0), textcoords='offset points',
                fontsize=5.5, color=color,
                va='center', ha='left',
                clip_on=False
            )

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        fig.autofmt_xdate(rotation=45, ha='right')

        ax.set_title(f'可转债 {title_suffix} (Top {series_count})', fontsize=18, fontweight='bold')
        ax.set_xlabel('交易日期', fontsize=12)
        ax.set_ylabel(y_label, fontsize=12)
        ax.grid(True, alpha=0.3)

        ncol = min(series_count, 8)
        ax.legend(
            loc='upper center', bbox_to_anchor=(0.5, -0.08),
            fontsize=6 if series_count > 15 else 7,
            ncol=ncol, frameon=True, borderaxespad=1
        )

        plt.tight_layout()
        return fig

    def _build_strategy_report(self, stats):
        """构建策略分析文字内容"""
        lines = []

        # ===== 市场总览 =====
        lines.append("## 一、市场总览")
        ret_dir = "上涨" if stats.get('period_return', 0) >= 0 else "下跌"
        lines.append(
            f"报告期内共覆盖 {stats['total_bonds']} 只可转债，横跨 {stats['total_dates']} 个交易日，"
            f"累计 {stats['total_records']} 条日频记录。整体市场呈{ret_dir}态势，"
            f"加权均价变动 {stats.get('period_return', 0):+.2f}%。"
        )

        market_sentiment = "偏多"
        if stats.get('period_return', 0) < -2:
            market_sentiment = "偏空"
        elif stats.get('period_return', 0) > 2:
            market_sentiment = "强势偏多"
        elif stats.get('period_return', 0) < 0:
            market_sentiment = "弱势震荡"

        lines.append(
            f"市场情绪判断：{market_sentiment}。上涨天数占比 {stats['positive_days_pct']:.1f}%，"
            f"上涨记录 {stats['up_days']} 条，下跌 {stats['down_days']} 条。"
        )

        lines.append('')

        # ===== 价格与涨跌幅分析 =====
        lines.append("## 二、价格与涨跌幅分析")
        lines.append(
            f"平均涨跌幅 {stats['avg_pct_chg']:+.3f}%，中位数 {stats['median_pct_chg']:+.3f}%，"
            f"标准差 {stats['std_pct_chg']:.3f}%。涨跌幅标准差越大，表明个券分化越严重。"
        )

        if stats.get('std_pct_chg', 0) > 3:
            lines.append(
                "【策略提示】涨跌幅标准差较高，个券表现分化明显，建议精选个券、分散配置，"
                "不宜采用指数化被动跟踪策略。重点关注正股驱动逻辑清晰的标的。"
            )
        elif stats.get('std_pct_chg', 0) > 1.5:
            lines.append(
                "【策略提示】市场存在一定分化，可适度采用行业/风格轮动策略，"
                "关注高景气赛道转债与防御性转债之间的切换机会。"
            )
        else:
            lines.append(
                "【策略提示】涨跌幅收敛，市场趋于同涨同跌，系统性风险是主要矛盾。"
                "建议以久期管理和仓位控制为主，关注整体利率环境和股市 beta。"
            )

        lines.append('')

        # ===== 成交与流动性分析 =====
        lines.append("## 三、成交与流动性分析")
        lines.append(
            f"日均成交量约 {stats['avg_vol']:,.0f} 手，期间最大单日成交 {stats['max_vol']:,.0f} 手。"
            f"整体成交呈{stats.get('vol_trend', '平稳')}态势。"
        )

        if stats.get('vol_trend') == '放量':
            lines.append(
                "【策略提示】成交量放大通常伴随市场分歧加大或新资金入场。关注量价关系："
                "若量增价升，可顺势加仓；若量增价跌，需警惕资金出逃风险，建议降低仓位。"
            )
        else:
            lines.append(
                "【策略提示】成交量萎缩，市场交投清淡。流动性折价风险上升，"
                "建议避免大规模进出场操作，优先选择流动性较好的大盘转债。"
            )

        active_ratio = stats['active_bonds'] / max(stats['total_bonds'], 1) * 100
        lines.append(
            f"活跃个券占比 {active_ratio:.1f}%（{stats['active_bonds']}/{stats['total_bonds']}），"
            f"非活跃 {stats['inactive_bonds']} 只。非活跃券流动性风险较高，需注意冲击成本。"
        )

        lines.append('')

        # ===== 估值与收益率分析 =====
        lines.append("## 四、估值与收益率分析")
        lines.append(
            f"平均 YTM（到期收益率）{stats['avg_ytm']:.2f}%，区间 [{stats['min_ytm']:.2f}%, {stats['max_ytm']:.2f}%]。"
        )

        ytm_pos = stats.get('ytm_positive_pct', 0)
        if ytm_pos < 30:
            lines.append(
                "【策略提示】市场中多数转债 YTM 为负，表明投资者普遍给予转股期权较高溢价。"
                "此类环境下纯债底保护较弱，建议关注转股溢价率适中、正股估值合理的标的。"
                "若利率上行预期升温，高溢价转债面临双重压力，应适当降低转债仓位。"
            )
        elif ytm_pos > 60:
            lines.append(
                "【策略提示】市场存在较多正 YTM 标的，债底保护相对充裕。"
                "可采用'固收+'策略，配置高 YTM 低溢价转债构建底仓，辅以少量高弹性标的博取超额收益。"
                "当前配置性价比较高。"
            )
        else:
            lines.append(
                "【策略提示】YTM 分布分化，需结合个券的信用资质和剩余期限综合评估。"
                "建议构建'核心-卫星'组合：核心仓位选择中等 YTM 高评级转债，"
                "卫星仓位配置高弹性标的捕捉交易机会。"
            )

        lines.append('')

        # ===== 风险指标分析 =====
        lines.append("## 五、风险指标分析")
        lines.append(
            f"平均修正久期 {stats['avg_duration']:.2f} 年，最大 {stats['max_duration']:.2f} 年。"
        )
        lines.append(
            f"平均凸性 {stats['avg_convexity']:.2f}。凸性越高，利率下行时价格涨速越快，"
            "是衡量债券价格对利率变化非线性敏感度的重要指标。"
        )

        if stats.get('avg_duration', 0) > 4:
            lines.append(
                "【策略提示】整体久期偏高，利率风险敞口较大。若预期加息或利率上行，"
                "建议：1) 降低仓位或缩短组合久期；2) 配置浮息转债或临近到期的短久期标的；"
                "3) 利用国债期货对冲利率风险。"
            )
        else:
            lines.append(
                "【策略提示】久期处于适中水平，利率风险可控。可通过微调久期在 ±1 年范围内优化组合，"
                "关注利率曲线形态变化带来的骑乘收益机会。"
            )

        lines.append('')

        # ===== VaR & ES 尾部分析 =====
        lines.append("## 六、VaR 与 Expected Shortfall 风险分析")

        avg_var_hist = stats.get('avg_var_hist_99', 0)
        max_var_hist = stats.get('max_var_hist_99', 0)
        avg_var_param = stats.get('avg_var_param_99', 0)
        max_var_param = stats.get('max_var_param_99', 0)
        avg_es = stats.get('avg_es_99', 0)
        max_es = stats.get('max_es_99', 0)
        avg_var_price = stats.get('avg_var_price_hist_99', 0)
        avg_es_price = stats.get('avg_es_price_99', 0)

        lines.append(
            f"历史模拟法 VaR(99%): 均值 {avg_var_hist:.2f}%，最大 {max_var_hist:.2f}%。"
        )
        lines.append(
            f"参数法 VaR(99%): 均值 {avg_var_param:.2f}%，最大 {max_var_param:.2f}%。"
        )
        lines.append(
            f"Expected Shortfall(99%): 均值 {avg_es:.2f}%，最大 {max_es:.2f}%。"
        )
        lines.append(
            f"VaR 代表的日均最大潜在亏损约 {avg_var_price:.2f} 元/张，"
            f"极端尾部损失(ES)日均约 {avg_es_price:.2f} 元/张。"
        )

        # 判断风险等级
        if avg_es > 3:
            lines.append(
                "【策略提示】尾部风险较高（ES > 3%），个券在极端行情下回撤幅度大。"
                "建议：1) 严格止损纪律，单券设置 2%-3% 硬止损线；"
                "2) 降低单券仓位上限至组合 3% 以下；"
                "3) 避免重仓高波动、低流动性标的；"
                "4) 考虑配置国债期货或利率衍生品对冲尾部风险。"
            )
        elif avg_es > 1.5:
            lines.append(
                "【策略提示】尾部风险处于中等水平（1.5% < ES ≤ 3%）。"
                "建议：1) 设置单券 3%-5% 止损线；"
                "2) 分散行业配置，避免单一行业敞口过大；"
                "3) 关注ES变动趋势，若持续扩大需及时调降仓位。"
            )
        else:
            lines.append(
                "【策略提示】尾部风险较低（ES ≤ 1.5%），市场波动可控。"
                "可适度放宽止损阈值至 5%，便于趋势行情中充分获利。"
                "但需持续监控 ES 变化，防范尾部风险突然放大。"
            )

        # 参数法 vs 历史模拟法 对比
        if abs(avg_var_hist - avg_var_param) > 1:
            lines.append(
                "【模型提示】历史模拟法与参数法 VaR 偏差较大（>1%），说明收益率分布存在"
                "明显的肥尾或偏态特征，参数法的正态假设可能低估尾部风险。建议以历史模拟法"
                "和 ES 作为主要风险度量参考。"
            )

        lines.append('')

        # ===== 有效久期与利率敏感性分析 =====
        lines.append("## 七、有效久期与利率敏感性分析")

        avg_eff_dur = stats.get('avg_effective_duration', 0)
        max_eff_dur = stats.get('max_effective_duration', 0)
        avg_eff_conv = stats.get('avg_effective_convexity', 0)
        max_eff_conv = stats.get('max_effective_convexity', 0)

        lines.append(
            f"平均有效久期 {avg_eff_dur:.2f} 年，最大 {max_eff_dur:.2f} 年。"
        )
        lines.append(
            f"平均有效凸性 {avg_eff_conv:.2f}，最大 {max_eff_conv:.2f}。"
        )
        lines.append(
            "有效久期通过实际收益率波动±1bp计算，相比修正久期更能反映含权债券的真实利率敏感度。"
            "有效凸性衡量了债券价格-收益率曲线的弯曲程度，凸性越大，收益率变动时的价格变化非对称性越强。"
        )
        lines.append('')

        # 场景分析
        avg_pct_50 = stats.get('avg_pct_price_chg_p50bp', 0)
        avg_pct_100 = stats.get('avg_pct_price_chg_p100bp', 0)
        min_pct_50 = stats.get('min_pct_price_chg_p50bp', 0)
        max_pct_50 = stats.get('max_pct_price_chg_p50bp', 0)
        min_pct_100 = stats.get('min_pct_price_chg_p100bp', 0)
        max_pct_100 = stats.get('max_pct_price_chg_p100bp', 0)

        lines.append(
            f"利率上行 50bp 场景：平均价格变动 {avg_pct_50:+.2f}%，"
            f"区间 [{min_pct_50:+.2f}%, {max_pct_50:+.2f}%]。"
        )
        lines.append(
            f"利率上行 100bp 场景：平均价格变动 {avg_pct_100:+.2f}%，"
            f"区间 [{min_pct_100:+.2f}%, {max_pct_100:+.2f}%]。"
        )
        lines.append(
            f"利率下行 50bp 场景：平均价格变动 {-avg_pct_50:+.2f}%（对称估算）。"
        )
        lines.append('')

        lines.append(
            "价格变动公式：ΔP% ≈ -Eff_Dur × Δy + ½ × Eff_Conv × (Δy)²"
        )
        lines.append(
            "其中第一项 -Eff_Dur×Δy 为久期效应（一阶线性），"
            "第二项 ½×Eff_Conv×(Δy)² 为凸性调整（二阶非线性），"
            "凸性越大，利率下行时收益增强越显著，利率上行时损失缓冲越明显。"
        )
        lines.append('')

        # 策略建议
        if abs(avg_pct_100) > 5:
            lines.append(
                "【策略提示】利率敏感性较高（±100bp 平均价格波动 > 5%）。"
                "若预期加息周期来临，建议：1) 大幅降低长久期转债仓位；"
                "2) 重点配置剩余期限 < 2 年的短久期转债；"
                "3) 利用国债期货或利率互换对冲利率风险敞口；"
                "4) 关注浮息转债或临近到期的品种降低利率敏感度。"
            )
        elif abs(avg_pct_100) > 3:
            lines.append(
                "【策略提示】利率敏感性中等（±100bp 价格波动 3%-5%）。"
                "建议：1) 根据利率预期动态调整久期敞口；"
                "2) 预期利率下行时可适度拉长久期，上行时缩短久期；"
                "3) 关注凸性较高的标的，在利率下行时获取超额收益。"
            )
        else:
            lines.append(
                "【策略提示】利率敏感性较低（±100bp 价格波动 < 3%），利率风险可控。"
                "组合对利率变动的防御性较强，可将更多精力放在信用分析和转股价值评估上。"
            )

        if avg_eff_conv > 10:
            lines.append(
                "【凸性提示】组合平均有效凸性较高（> 10），表明市场存在较多长久期或高票息标的。"
                "高凸性在利率下行时提供放大收益的非对称优势，但需注意流动性风险和久期错配风险。"
            )

        lines.append('')

        # ===== 综合策略建议 =====
        lines.append("## 八、综合策略建议")

        if stats.get('period_return', 0) > 2 and stats.get('vol_trend') == '放量':
            lines.append(
                "【市场阶段】量价齐升，市场处于强势阶段。"
            )
            lines.append(
                "【操作建议】1) 维持中性偏高仓位(60%-80%)，积极把握趋势行情；"
                "2) 重点配置高弹性、正股基本面扎实的偏股型转债；"
                "3) 设好移动止盈位，避免回撤侵蚀利润；"
                "4) 关注正股技术形态，对于突破关键阻力位的正股对应的转债可适当加仓。"
            )
        elif stats.get('period_return', 0) < -2:
            lines.append("【市场阶段】价格下行，市场处于弱势。")
            lines.append(
                "【操作建议】1) 降低仓位至 30%-50%，优先减持高溢价、低流动性的标的；"
                "2) 配置偏债型转债和临近回售/到期的品种获取债底保护；"
                "3) 利用转债 T+0 特性进行日内短线交易降低持仓成本；"
                "4) 密切关注下修条款触发情况，博弈下修机会。"
            )
        else:
            lines.append("【市场阶段】震荡整理，方向不明。")
            lines.append(
                "【操作建议】1) 保持中性仓位(50%-60%)，灵活应对；"
                "2) 采用双低策略(低价格+低溢价率)构建防御性组合；"
                "3) 关注下修博弈和回售套利机会；"
                "4) 利用网格交易捕捉波动中的价差收益；"
                "5) 密切跟踪正股业绩和行业轮动信号，待方向明确后加仓。"
            )

        lines.append('')
        lines.append("---")
        lines.append("⚠ 免责声明：以上分析基于历史数据和量化模型，仅供参考，不构成投资建议。"
                     "可转债投资存在市场风险、信用风险和流动性风险，请结合自身风险偏好审慎决策。")

        return lines

    def _generate_pdf_report(self, df, stats, start_date, end_date):
        """生成完整 PDF 策略报告"""
        os.makedirs(self.REPORT_DIR, exist_ok=True)
        pdf_path = os.path.join(
            self.REPORT_DIR,
            f"ConvertibleBond_Strategy_Report_{start_date}_{end_date}.pdf"
        )

        df = self._prepare_data(df)
        strategy_lines = self._build_strategy_report(stats)
        report_date = datetime.now().strftime('%Y-%m-%d %H:%M')

        # 全局设置 PDF 输出 DPI，确保清晰
        plt.rcParams['savefig.dpi'] = 200

        with PdfPages(pdf_path) as pdf:

            # ===== 封面 =====
            fig = plt.figure(figsize=(12, 14))
            ax = fig.add_subplot(111)
            ax.axis('off')

            ax.text(0.5, 0.82, '可转债策略分析报告', transform=ax.transAxes,
                    ha='center', fontsize=32, fontweight='bold', color='#1a1a2e')
            ax.text(0.5, 0.72, 'Convertible Bond Strategy Report',
                    transform=ax.transAxes, ha='center', fontsize=16,
                    color='#888888', style='italic')

            ax.axhline(y=0.68, xmin=0.2, xmax=0.8, color='#e94560', linewidth=3)

            info_text = (
                f"报告区间：{start_date} — {end_date}\n"
                f"生成时间：{report_date}\n"
                f"覆盖标的：{stats['total_bonds']} 只可转债\n"
                f"数据记录：{stats['total_records']:,} 条"
            )
            ax.text(0.5, 0.52, info_text, transform=ax.transAxes, ha='center',
                    fontsize=14, linespacing=2.0, color='#333333')

            ax.text(0.5, 0.08, 'INFINITY 量化系统 · 内部研究专用',
                    transform=ax.transAxes, ha='center', fontsize=10,
                    color='#aaaaaa')
            pdf.savefig(fig)
            plt.close(fig)

            # ===== 策略总览 =====
            self._add_text_page(
                pdf,
                '策略分析总览',
                strategy_lines,
                subtitle=f'数据区间 {start_date} ~ {end_date}  |  覆盖 {stats["total_bonds"]} 只可转债'
            )

            # ===== 逐一生成图表页 =====
            for value_col, y_label, title_suffix in self.CHART_FIELDS:
                logger.info(f"生成图表: {title_suffix}")
                fig = self._generate_line_chart_fig(df, value_col, y_label, title_suffix)
                if fig:
                    pdf.savefig(fig)
                    plt.close(fig)

        logger.info(f"PDF 策略报告已生成: {pdf_path}")
        return pdf_path

    # ==================== 一键流程 ====================

    def run(self, start_date, end_date):
        logger.info(f"====== ConvertibleBondManagerReport 开始执行 ======")
        logger.info(f"日期范围: {start_date} ~ {end_date}")

        # 1) 查询
        df = self.query_panorama(start_date, end_date)
        if df.empty:
            logger.warning("查询结果为空，流程终止")
            return

        # 2) 保存原始数据
        self.save_to_file(df, f"panorama_{start_date}_{end_date}")

        # 3) 数据预处理（添加 series_name、转换日期）
        df = self._prepare_data(df)

        # 4) 统计计算
        stats = self._compute_analysis_stats(df)
        logger.info(f"统计完成：{stats['total_bonds']} 只可转债，"
                     f"区间涨跌 {stats.get('period_return', 0):+.2f}%")

        # 5) 生成 PDF 策略报告
        self._generate_pdf_report(df, stats, start_date, end_date)

        logger.info(f"====== ConvertibleBondManagerReport 执行完成 ======")


if __name__ == "__main__":
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)

    report = ConvertibleBondManagerReport()
    report.run("20260101", "20260525")

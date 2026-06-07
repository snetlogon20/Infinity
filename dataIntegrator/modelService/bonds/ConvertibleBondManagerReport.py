import os
import textwrap
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd

from dataIntegrator import CommonLib
from dataIntegrator.common.CommonParameters import CommonParameters
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

    # 需要同时展示高风险 top20 和低风险 top20 的字段
    RISK_DUAL_FIELDS = {
        'm.var_price_hist_99',
        'm.var_price_param_99',
        'm.es_price_99',
        'm.es_99',
    }

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
        ax.plot([0.15, 0.85], [y + 0.005, y + 0.005], color='#e94560', linewidth=2,
                transform=ax.transAxes)

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
                ax.plot([0.08, 0.92], [y, y], color='#cccccc', linewidth=0.5,
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

    def _get_top_pivot(self, df, value_col, top_n=20, select_smallest=False):
        """提取 pivot 表并筛选 top_n 条极端曲线，供图表和数据表复用"""
        df = df.dropna(subset=[value_col])
        if df.empty:
            return None

        pivot = df.pivot_table(
            index='d.trade_date',
            columns='series_name',
            values=value_col,
            aggfunc='first'
        ).sort_index()

        if len(pivot.columns) > top_n:
            max_abs_values = pivot.abs().max()
            if select_smallest:
                top_columns = max_abs_values.nsmallest(top_n).index.tolist()
            else:
                top_columns = max_abs_values.nlargest(top_n).index.tolist()
            pivot = pivot[top_columns]

        return pivot

    def _generate_data_table_fig(self, pivot, y_label, title_suffix):
        """生成一条折线图对应的数据明细表 Figure"""
        if pivot is None or pivot.empty:
            return None

        # 先收集原始数值，按 |最新值| 降序排列，方便交易员快速定位极值标的
        raw_data = []
        for col in pivot.columns:
            series = pivot[col].dropna()
            if series.empty:
                continue
            last_date = series.index[-1]
            date_str = last_date.strftime('%Y-%m-%d') if hasattr(last_date, 'strftime') else str(last_date)[:10]
            raw_data.append((
                col,
                date_str,
                float(series.iloc[-1]),
                float(series.mean()),
                float(series.std()),
                float(series.min()),
                float(series.max()),
            ))

        if not raw_data:
            return None

        # 按最新值的绝对值降序排列，极值标的最显眼
        raw_data.sort(key=lambda x: abs(x[2]), reverse=True)

        # 格式化成展示字符串
        table_data = []
        for item in raw_data:
            table_data.append([
                item[0],
                item[1],
                f"{item[2]:.4f}",
                f"{item[3]:.4f}",
                f"{item[4]:.4f}",
                f"{item[5]:.4f}",
                f"{item[6]:.4f}",
            ])

        col_labels = ['代码/名称', '最新日期', '最新值', '均值', '标准差', '最小值', '最大值']
        n_rows = len(table_data)
        zero_count = 0
        for row in table_data:
            try:
                if abs(float(row[2])) < 1e-8:
                    zero_count += 1
            except ValueError:
                pass
        suffix_note = f"（注：{zero_count}只标的最新值接近0）" if zero_count > 0 else ""
        title = f'可转债 {title_suffix} (Top {n_rows}) 数据明细{suffix_note}'

        fig_height = max(3, 1.0 + n_rows * 0.42)
        fig, ax = plt.subplots(figsize=(22, fig_height))
        ax.axis('off')
        ax.set_title(title, fontsize=13, fontweight='bold', pad=16)

        table = ax.table(
            cellText=table_data,
            colLabels=col_labels,
            cellLoc='center',
            loc='center',
            colWidths=[0.28, 0.11, 0.12, 0.12, 0.12, 0.12, 0.13]
        )
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1.0, 1.45)

        # header style
        for i in range(len(col_labels)):
            table[0, i].set_facecolor('#2F5496')
            table[0, i].set_text_props(color='white', fontweight='bold', fontsize=8.5)

        # alternating row color
        for i in range(1, n_rows + 1):
            bg = '#D6E4F0' if i % 2 == 0 else '#FFFFFF'
            for j in range(len(col_labels)):
                table[i, j].set_facecolor(bg)

        plt.tight_layout(pad=1.0)
        return fig

    def _get_trader_explanation(self, value_col):
        """返回交易员层面的专业解读文本列表"""
        mapping = {
            'd.pre_close': [
                "## 交易员视角：前收盘价 (Pre_Close)",
                "前收盘价是每日开盘前的锚定价格，也是计算涨跌幅的基准。",
                "",
                "【市场含义】",
                "• 连续上行 → 多头趋势确立，市场共识偏强，可顺势持有或加仓",
                "• 连续下行 → 空头主导，持仓面临浮亏压力，需审视止损位",
                "• 横盘整理 → 多空均衡，等待方向选择，观望或轻仓参与",
                "",
                "【交易策略】突破前高可追多，设前收盘价下方1%为止损；跌破前低应减仓。",
            ],
            'd.pct_chg': [
                "## 交易员视角：涨跌幅 (Pct_Chg%)",
                "涨跌幅是日内多空博弈的直接体现。高波动意味着分歧大、机会多，也意味着风险敞口大。",
                "",
                "【实战解读】",
                "• 涨幅 >5%：强势标的，关注是否触发短线止盈信号",
                "• 涨幅 1-3%：温和上行，适合中线持有",
                "• 跌幅 >3%：风险信号，检查是否有信用事件或正股利空",
                "• 跌幅 1-3%：正常波动，不必过度反应",
                "",
                "【操作建议】转债T+0特性使日内波动放大是常态。涨幅过大先兑现部分利润，",
                "跌幅过大不宜盲目补仓，先判断是否为系统性风险。",
            ],
            'd.vol': [
                "## 交易员视角：成交量 (Vol)",
                "成交量是市场情绪的体温计——放量代表分歧加大或资金进场，缩量代表观望或流动性枯竭。",
                "",
                "【量价关系】",
                "• 放量上涨 → 多头强势，可靠性高，可顺势加仓",
                "• 放量下跌 → 恐慌抛售或主力出货，果断减仓",
                "• 缩量上涨 → 上攻乏力，可能冲高回落，谨慎追多",
                "• 缩量下跌 → 抛压减轻，接近底部但未确认反转前不抄底",
                "",
                "【流动性管理】日均成交低于1000手的标的，冲击成本可能超0.5%，大资金谨慎参与。",
            ],
            'd.amount': [
                "## 交易员视角：成交额 (Amount)",
                "成交额直接反映资金参与规模，大额成交意味着机构参与度高，趋势更具持续性。",
                "",
                "【实战信号】",
                "• 成交额持续放大 → 增量资金入场，行情有望延续",
                "• 成交额急剧放大后萎缩 → 短期高点信号，注意止盈",
                "• 成交额低迷 → 市场缺乏方向，降低交易频率",
                "",
                "【策略建议】大额成交标的适合趋势跟踪；小额成交标的需警惕流动性折价。",
            ],
            'm.ytm': [
                "## 交易员视角：到期收益率 (YTM)",
                "YTM是持有至到期的年化总回报。转债YTM通常低于同评级信用债，差额即为转股期权隐含价格。",
                "",
                "【关键判断】",
                "• YTM > 0 → 债底保护充分，下行空间有限，安全性较高",
                "• YTM < 0 → 完全依赖转股价值，纯债安全垫为负",
                "• YTM 上升 → 债券价格下跌或信用利差走阔，可能是买入机会",
                "• YTM 下降 → 债券价格上涨，持有者盈利但新增持仓性价比降低",
                "",
                "【策略应用】利率下行周期可配置高YTM转债获取骑乘收益。",
            ],
            'm.modified_duration': [
                "## 交易员视角：修正久期 (Modified Duration)",
                "修正久期衡量可转债价格对收益率变化1%的线性敏感度。数值越大，利率风险暴露越高。",
                "",
                "【关键阈值】",
                "• 修正久期 < 2 → 短久期，利率风险低，适合防御性配置",
                "• 修正久期 2-5 → 中等久期，利率波动产生明显影响",
                "• 修正久期 > 5 → 长久期，利率下行时收益放大，上行时亏损加剧",
                "",
                "【对冲建议】组合久期超目标水平时：减持长久期标的 / 配置短久期品种 / 国债期货对冲。",
            ],
            'm.convexity': [
                "## 交易员视角：凸性 (Convexity)",
                "凸性衡量久期随收益率变化的速率，是利率风险管理的二阶工具。",
                "正凸性 → 利率下行时价格涨幅 > 利率上行时价格跌幅（非对称优势）。",
                "",
                "【交易者视角】",
                "• 凸性越高，降息时久期拉长，进一步放大价格上涨弹性",
                "• 高凸性转债在降息周期表现优异",
                "• 临近到期转债凸性趋近于零，投资者应关注剩余期限影响",
            ],
            'm.dv01': [
                "## 交易员视角：DV01",
                "DV01表示收益率每变动1bp时，每张可转债价格的变动金额（元）。",
                "",
                "【实战应用】",
                "• 持仓DV01 = 单券DV01 × 持仓张数，汇总得组合整体利率风险敞口",
                "• DV01匹配可对冲利率风险：多空DV01相等即实现免疫",
                "• DV01越大 → 利率微小变动造成盈亏波动越大，需关注止损设定",
            ],
            'm.pvbp': [
                "## 交易员视角：PVBP",
                "PVBP（Price Value of a Basis Point）与DV01含义相同，标准化为每百元面值。",
                "是国际通行的利率风险度量标准。",
                "",
                "【交易应用】比较不同面额标的风险时，PVBP提供标准化标尺。",
                "【经验法则】每PVBP=0.05元时，收益率变动50bp ≈ 每张盈亏2.5元。",
            ],
            'm.simple_ytm': [
                "## 交易员视角：简易到期收益率 (Simple YTM)",
                "不考虑复利效应的YTM，计算简便直观。短期标的与标准YTM差异不大。",
                "",
                "【使用建议】",
                "• 短期(<1年)：Simple YTM ≈ 标准YTM，可直接参考",
                "• 中长期：Simple YTM低估复利效应，应以标准YTM为准",
                "• 一般仅作快速筛选参考，不用于精确估值决策",
            ],
            'm.current_yield': [
                "## 交易员视角：当期收益率 (Current Yield)",
                "当期收益率 = 年票息 / 当前市价，仅反映利息收入，不考虑资本利得。",
                "",
                "【策略意义】高当期收益率标的提供稳定现金流，适合收入导向型策略。",
                "转债通常票息较低，当前收益率对总回报贡献有限，主要依赖转股价值驱动。",
            ],
            'm.var_hist_99': [
                "## 交易员视角：历史VaR(99%置信, %)",
                "基于历史收益率分布，99%置信度下单日最大可能亏损比例。",
                "如VaR=2% → 99%情况下单日亏损不超过2%。",
                "",
                "【风控阈值】",
                "• VaR 1-2%：低风险，适合稳健型组合",
                "• VaR 2-5%：中度风险，需设止损线并控仓",
                "• VaR >5%：高风险，仅适合激进策略，单券仓位≤2%",
                "",
                "【局限性】依赖历史样本代表性，市场突变时可能低估风险，需结合参数法+ES综合判断。",
            ],
            'm.var_param_99': [
                "## 交易员视角：参数VaR(99%置信, %)",
                "假设收益率正态分布，基于均值和标准差计算。简洁但无法捕捉肥尾特征。",
                "",
                "【对比判断】",
                "• 参数VaR << 历史VaR → 分布存在明显肥尾，参数法低估风险",
                "• 参数VaR > 历史VaR → 近期波动率下降，历史样本含极端行情",
                "• 参数VaR ≈ 历史VaR → 正态假设可接受",
            ],
            'm.es_99': [
                "## 交易员视角：Expected Shortfall(ES, 99%)",
                "ES衡量损失超过VaR阈值时的平均损失幅度，是比VaR更全面的尾部风险度量。",
                "",
                "【实战价值】",
                "• ES给出\"最糟糕情况平均亏多少\"，比VaR的\"不会超过多少\"更有指导意义",
                "• ES > VaR 幅度越大 → 尾部风险越不对称，极端行情伤害越深",
                "• 监管机构越来越倾向使用ES替代VaR",
                "",
                "【风控建议】ES超3%的标的，极端行情下可能单日跌5-10%，需严格控仓。",
            ],
            'm.var_price_hist_99': [
                "## 交易员视角：历史VaR(99%置信, 元/张)",
                "以每张可转债绝对元计价计量的VaR，直观展示最大潜在亏损金额。",
                "",
                "【实用解读】",
                "• VaR_price=3元/张 → 99%概率每张单日亏损≤3元",
                "• 乘以持仓张数即得组合VaR金额",
                "• 低VaR_price标的适合组合稳定器，高VaR_price标的需严格控仓",
                "",
                "【实操步骤】每日监控持仓券VaR_price变化，单券VaR_price超总资产0.5%即为重仓风险信号。",
            ],
            'm.var_price_param_99': [
                "## 交易员视角：参数VaR(99%置信, 元/张)",
                "基于正态假设的参数法VaR（元/张），对近期波动率变化更敏感。",
                "",
                "【交易应用】若参数VaR突然跳升，提示波动率骤增，应立即降低风险敞口。",
                "若参数VaR持续下降，表明市场趋于稳定。",
            ],
            'm.es_price_99': [
                "## 交易员视角：ES(99%置信, 元/张)",
                "ES_price计量极端情景下平均损失金额（元/张），是最保守的风险度量。",
                "",
                "【风控纪律】",
                "• 单券ES_price > 5元/张 → 高风险券，单券仓位≤2%",
                "• 单券ES_price > 10元/张 → 极高风险券，仅投机性参与",
                "• 组合总ES = Σ(各券ES_price × 持仓张数)，确保不超过组合净值5%",
            ],
            'm.effective_duration': [
                "## 交易员视角：有效久期 (Effective Duration)",
                "通过数值法（±1bp冲击）计算，比修正久期更准确反映含权债券真实利率敏感度。",
                "",
                "【交易逻辑】",
                "• 有效久期 < 修正久期 → 存在负凸性或嵌入期权约束（如赎回条款）",
                "• 有效久期 ≈ 修正久期 → 定价接近普通债券，期权价值较低",
                "• 有效久期越大 → 利率对冲需要的国债期货手数越多",
            ],
            'm.effective_convexity': [
                "## 交易员视角：有效凸性 (Effective Convexity)",
                "有效凸性通过数值模拟计算，反映价格-收益率曲线的弯曲程度。",
                "",
                "【交易优势】",
                "• 正凸性越大 → 利率下行时收益放大效应越明显",
                "• 高凸性标的在降息周期是优质配置选择",
                "• 低凸性或负凸性标的需警惕，利率不利时损失可能急剧放大",
            ],
            'm.pct_price_chg_p50bp': [
                "## 交易员视角：收益率+50bp价格变动(%)",
                "模拟利率上行50bp时价格预期变动。是压力测试的基础情景之一。",
                "",
                "【风控场景】美联储加息50bp或央行MLF利率上调时，快速评估持仓损失：",
                "损失 ≈ |pct_chg| × 持仓市值。若超风险预算，应提前调仓。",
            ],
            'm.pct_price_chg_m50bp': [
                "## 交易员视角：收益率-50bp价格变动(%)",
                "模拟利率下行50bp时价格预期变动。",
                "",
                "【交易应用】预期降息时可筛选涨幅最大的标的超配，预期加息时规避该数值大的标的。",
            ],
            'm.pct_price_chg_p100bp': [
                "## 交易员视角：收益率+100bp价格变动(%)",
                "极端利率上行冲击（+100bp）下的价格变动，属于严重压力情景。",
                "",
                "【风控红线】持仓中 pct_chg_p100bp < -5% 的标的，在加息周期必须设硬性减仓纪律。",
                "组合该指标加权均值超-3%时，应立即启动利率对冲。",
            ],
            'm.pct_price_chg_m100bp': [
                "## 交易员视角：收益率-100bp价格变动(%)",
                "极端降息情景下的价格变动。",
                "",
                "【策略启示】该数值大的标的在宽松周期弹性最大，但加息周期也面临最大反向风险。",
                "货币政策转折期应动态调整该类标的配置权重。",
            ],
        }
        return mapping.get(value_col, None)

    # ==================== 量化组合推荐（交易员三步法） ====================

    def _run_trader_screening_pipeline(self, df):
        """交易员三步量化筛选：1) 数据对齐 2) 硬过滤 3) 四维度策略精筛

        Returns:
            dict with keys: total_count, hard_filter, dim1, dim2, dim3, dim4, final
            无标的时返回 None
        """
        dfm = self._prepare_data(df)
        latest_date = dfm['d.trade_date'].max()
        latest = dfm[dfm['d.trade_date'] == latest_date].copy()
        if latest.empty:
            logger.warning("无法获取最新交易日数据")
            return None

        total_count = latest['series_name'].nunique()
        logger.info(f"[三步筛选] 全市场 {total_count} 只可转债，最新日期 {latest_date.strftime('%Y-%m-%d')}")

        def _f(col):
            """安全获取 float 列"""
            return latest[col].fillna(0).astype(float)

        def _s(col):
            """安全获取 string 列"""
            return latest[col].fillna('')

        # ==================== Step 1: 核心字段对齐 ====================
        pool = pd.DataFrame({
            'ts_code':        _s('b.ts_code'),
            'bond_name':      _s('b.bond_short_name'),
            'close':          _f('d.close'),
            'par':            _f('b.par'),
            'rem_years':      _f('m.remaining_years'),
            'cur_yield':      _f('m.current_yield'),
            'ytm':            _f('m.ytm'),
            'mod_dur':        _f('m.modified_duration'),
            'var_price':      _f('m.var_price_param_99'),
            'var_pct':        _f('m.var_param_99'),
            'es_pct':         _f('m.es_99'),
            'es_price':       _f('m.es_price_99'),
            'remain_size':    _f('b.remain_size'),
            'stk_name':       _s('b.stk_short_name'),
            'cb_type':        _s('b.cb_type'),
            'series_name':    _s('series_name'),
            'trade_date':     latest['d.trade_date'],
            # 新增关键指标
            'mac_dur':        _f('m.macaulay_duration'),
            'eff_dur':        _f('m.effective_duration'),
            'convexity':      _f('m.convexity'),
            'eff_conv':       _f('m.effective_convexity'),
            'dv01':           _f('m.dv01'),
            'pvbp':           _f('m.pvbp'),
            'ytm_simple':     _f('m.simple_ytm'),
            'var_price_hist': _f('m.var_price_hist_99'),
            'pct_p50bp':      _f('m.pct_price_chg_p50bp'),
            'pct_m50bp':      _f('m.pct_price_chg_m50bp'),
        })
        pool = pool.drop_duplicates(subset=['ts_code']).reset_index(drop=True)

        # ==================== Step 2: 硬过滤 ====================
        reason = pd.Series('', index=pool.index)

        mask_rem       = pool['rem_years'] >= 0.01
        reason[~mask_rem]       = reason[~mask_rem] + '剩余年限不足;'

        mask_size      = pool['remain_size'] >= 10000
        reason[~mask_size]      = reason[~mask_size] + '剩余规模<1亿;'

        mask_stk       = ~pool['stk_name'].str.contains('退', na=False)
        reason[~mask_stk]       = reason[~mask_stk] + '正股含退市风险;'

        mask_close     = pool['close'] <= 130
        reason[~mask_close]     = reason[~mask_close] + f'收盘价{pool.loc[~mask_close,"close"].round(1).values}超130;'

        mask_var       = pool['var_pct'] <= 3
        reason[~mask_var]       = reason[~mask_var] + f'VaR99={pool.loc[~mask_var,"var_pct"].round(2).values}%超3%;'

        mask_es        = pool['es_pct'] <= 6
        reason[~mask_es]        = reason[~mask_es] + f'ES99={pool.loc[~mask_es,"es_pct"].round(2).values}%超6%;'

        passed = mask_rem & mask_size & mask_stk & mask_close & mask_var & mask_es

        retained = pool[passed].copy()
        eliminated = pool[~passed].copy()
        eliminated['淘汰原因'] = reason[~passed].values

        logger.info(f"[三步筛选] Step2 硬过滤: {len(retained)}/{len(pool)} 通过 (淘汰 {len(eliminated)} 只)")

        if retained.empty:
            return None

        # ==================== Step 3: 四维度策略精筛 ====================
        r = retained.copy()

        # --- 辅助函数：归一化得分到0-100 ---
        def _norm(s):
            mn, mx = s.min(), s.max()
            if mx - mn < 1e-9:
                return pd.Series(50, index=s.index)
            return ((s - mn) / (mx - mn) * 100).round(1)

        # ---------- 维度1：稳健收息型 ----------
        r['dim1_raw'] = (
            r['cur_yield'] * 0.40 +
            (-r['ytm'])  * 0.30 +
            (1 / r['rem_years'].clip(lower=0.01)) * 0.20 +
            (1 / r['var_price'].clip(lower=0.01)) * 0.10
        )
        r['dim1_score'] = _norm(r['dim1_raw'])
        dim1_mask = (r['cur_yield'] >= 1.8) & (r['ytm'] >= -5) & (r['var_pct'] <= 1.5)
        dim1 = r[dim1_mask].nlargest(min(10, dim1_mask.sum()), 'dim1_score').copy()
        logger.info(f"[三步筛选] 维度1-稳健收息: {dim1_mask.sum()} 只候选, 取Top{len(dim1)}")

        # ---------- 维度2：深度价值型 ----------
        r['dim2_raw'] = (
            (100 - r['close']) * 0.50 +
            r['ytm']           * 0.30 +
            (1 / r['rem_years'].clip(lower=0.01)) * 0.20
        )
        r['dim2_score'] = _norm(r['dim2_raw'])
        dim2_mask = (r['close'] < 100) & (r['ytm'] > 0) & (r['rem_years'] < 2)
        dim2 = r[dim2_mask].nlargest(min(10, dim2_mask.sum()), 'dim2_score').copy()
        logger.info(f"[三步筛选] 维度2-深度价值: {dim2_mask.sum()} 只候选, 取Top{len(dim2)}")

        # ---------- 维度3：久期博弈型 ----------
        r['dim3_raw'] = (
            r['rem_years'] * 0.40 +
            r['mod_dur']  * 0.30 +
            (1 / r['var_price'].clip(lower=0.01)) * 0.20 +
            r['cur_yield'] * 0.10
        )
        r['dim3_score'] = _norm(r['dim3_raw'])
        dim3_mask = (r['rem_years'] >= 1.5) & (r['mod_dur'] >= 1.1) & (r['var_pct'] <= 2)
        dim3 = r[dim3_mask].nlargest(min(10, dim3_mask.sum()), 'dim3_score').copy()
        logger.info(f"[三步筛选] 维度3-久期博弈: {dim3_mask.sum()} 只候选, 取Top{len(dim3)}")

        # ---------- 维度4：风险调整收益 ----------
        r['dim4_val'] = (r['cur_yield'] / r['var_price'].clip(lower=0.01)).round(3)
        dim4 = r.nlargest(min(10, len(r)), 'dim4_val').copy()
        logger.info(f"[三步筛选] 维度4-风险调整收益: 取Top{len(dim4)}")

        # ==================== 最终综合推荐 ====================
        # 交集法：找出多少只出现在多个维度
        all_dim_codes = []
        for d, label in [(dim1, '稳健收息'), (dim2, '深度价值'), (dim3, '久期博弈'), (dim4, '风险调整')]:
            if not d.empty:
                for _, row in d.iterrows():
                    all_dim_codes.append((row['ts_code'], row['bond_name'], label, row.get('dim1_score', row.get('dim2_score', row.get('dim3_score', 0))), row.get('dim4_val', 0)))

        from collections import Counter
        code_counter = Counter(c[0] for c in all_dim_codes)
        multi_dim = {code for code, cnt in code_counter.items() if cnt >= 2}

        # 综合推荐表：取多维度标的重叠 + 各维度首位
        final_recs = []
        seen = set()
        # 先加满足2个维度以上的
        for code in multi_dim:
            hits = [c for c in all_dim_codes if c[0] == code]
            row = retained[retained['ts_code'] == code].iloc[0] if len(retained[retained['ts_code'] == code]) > 0 else None
            if row is not None and code not in seen:
                dims_tag = ','.join([h[2] for h in hits])
                final_recs.append({
                    'ts_code': code, 'bond_name': row['bond_name'], 'close': row['close'],
                    'ytm': row['ytm'], 'cur_yield': row['cur_yield'], 'rem_years': row['rem_years'],
                    'mod_dur': row['mod_dur'], 'var_pct': row['var_pct'], 'es_pct': row['es_pct'],
                    'mac_dur': row['mac_dur'], 'eff_dur': row['eff_dur'],
                    'convexity': row['convexity'], 'eff_conv': row['eff_conv'],
                    'dv01': row['dv01'], 'pvbp': row['pvbp'],
                    'ytm_simple': row['ytm_simple'], 'var_price_hist': row['var_price_hist'],
                    'pct_p50bp': row['pct_p50bp'], 'pct_m50bp': row['pct_m50bp'],
                    'dim_tags': dims_tag, 'dim_count': len(hits),
                })
                seen.add(code)

        # 如果不足5只，每个维度补首位
        for d, label in [(dim1, '稳健收息'), (dim2, '深度价值'), (dim3, '久期博弈'), (dim4, '风险调整')]:
            if len(final_recs) >= 8:
                break
            if d.empty:
                continue
            top_code = d.iloc[0]['ts_code']
            if top_code not in seen:
                row = retained[retained['ts_code'] == top_code].iloc[0]
                final_recs.append({
                    'ts_code': top_code, 'bond_name': row['bond_name'], 'close': row['close'],
                    'ytm': row['ytm'], 'cur_yield': row['cur_yield'], 'rem_years': row['rem_years'],
                    'mod_dur': row['mod_dur'], 'var_pct': row['var_pct'], 'es_pct': row['es_pct'],
                    'mac_dur': row['mac_dur'], 'eff_dur': row['eff_dur'],
                    'convexity': row['convexity'], 'eff_conv': row['eff_conv'],
                    'dv01': row['dv01'], 'pvbp': row['pvbp'],
                    'ytm_simple': row['ytm_simple'], 'var_price_hist': row['var_price_hist'],
                    'pct_p50bp': row['pct_p50bp'], 'pct_m50bp': row['pct_m50bp'],
                    'dim_tags': label, 'dim_count': 1,
                })
                seen.add(top_code)

        logger.info(f"[三步筛选] 最终综合推荐: {len(final_recs)} 只")

        return {
            'total_count': total_count,
            'retained_count': len(retained),
            'eliminated_count': len(eliminated),
            'eliminated': eliminated,
            'dim1': dim1,
            'dim2': dim2,
            'dim3': dim3,
            'dim4': dim4,
            'dim4_full': r,
            'final_recs': final_recs,
        }

    def _generate_screening_table_fig(self, data_rows, col_labels, title, subtitle=None, col_widths=None):
        """通用筛选表格 Figure 生成器"""
        n = len(data_rows)
        if n == 0:
            return None
        nc = len(col_labels)
        fig_height = max(3, 1.2 + n * 0.44)
        fig, ax = plt.subplots(figsize=(24, fig_height))
        ax.axis('off')
        ax.set_title(title, fontsize=14, fontweight='bold', pad=12)
        if subtitle:
            ax.text(0.5, 0.97, subtitle, transform=ax.transAxes, ha='center', fontsize=9, color='#666')

        if col_widths is None:
            col_widths = [1.0 / nc] * nc

        table = ax.table(
            cellText=data_rows, colLabels=col_labels,
            cellLoc='center', loc='center', colWidths=col_widths,
        )
        table.auto_set_font_size(False)
        table.set_fontsize(7.5)
        table.scale(1.0, 1.5)
        for i in range(nc):
            table[0, i].set_facecolor('#2F5496')
            table[0, i].set_text_props(color='white', fontweight='bold', fontsize=8)
        for i in range(1, n + 1):
            bg = '#D6E4F0' if i % 2 == 0 else '#FFFFFF'
            for j in range(nc):
                table[i, j].set_facecolor(bg)
        plt.tight_layout(pad=1.2)
        return fig

    def _generate_line_chart_fig(self, df, value_col, y_label, title_suffix, top_n=20, select_smallest=False, pivot=None):
        """返回折线图 Figure（用于拼入 PDF），只展示 y 值最极端的 top_n 条"""
        if pivot is None:
            pivot = self._get_top_pivot(df, value_col, top_n, select_smallest)
            if pivot is None or pivot.empty:
                return None

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
        now_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_path = os.path.join(
            self.REPORT_DIR,
            f"ConvertibleBond_Strategy_Report_{start_date}-{end_date}_{now_ts}.pdf"
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

            ax.plot([0.2, 0.8], [0.68, 0.68], color='#e94560', linewidth=3,
                    transform=ax.transAxes)

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

                # 获取数据 pivot
                pivot = self._get_top_pivot(df, value_col)
                if pivot is None or pivot.empty:
                    continue

                # 折线图
                fig = self._generate_line_chart_fig(df, value_col, y_label, title_suffix, pivot=pivot)
                if fig:
                    pdf.savefig(fig)
                    plt.close(fig)

                # 数据明细表
                logger.info(f"生成数据表: {title_suffix}")
                table_fig = self._generate_data_table_fig(pivot, y_label, title_suffix)
                if table_fig:
                    pdf.savefig(table_fig)
                    plt.close(table_fig)

                # 交易员解读
                explanation = self._get_trader_explanation(value_col)
                if explanation:
                    self._add_text_page(pdf, f'交易员解读: {title_suffix}', explanation)

                # 风险字段额外生成低风险 Top 20（数值最小的）
                if value_col in self.RISK_DUAL_FIELDS:
                    low_pivot = self._get_top_pivot(df, value_col, select_smallest=True)
                    if low_pivot is not None and not low_pivot.empty:
                        low_title = title_suffix + ' (低风险Top20)'
                        logger.info(f"生成图表: {low_title}")
                        low_fig = self._generate_line_chart_fig(
                            df, value_col, y_label, low_title, select_smallest=True, pivot=low_pivot)
                        if low_fig:
                            pdf.savefig(low_fig)
                            plt.close(low_fig)
                        logger.info(f"生成数据表: {low_title}")
                        low_table_fig = self._generate_data_table_fig(low_pivot, y_label, low_title)
                        if low_table_fig:
                            pdf.savefig(low_table_fig)
                            plt.close(low_table_fig)

            # ============ 量化组合推荐（交易员三步筛选法） ============
            logger.info("开始量化组合推荐（三步法）...")
            screening = self._run_trader_screening_pipeline(df)

            if screening:
                # ---------- 总览页 ----------
                overview_lines = [
                    "## 交易员量化组合推荐",
                    "",
                    "以下按实盘交易逻辑，使用「硬指标量化打分 -> 人工排除噪音 -> 归类策略」三步筛选法，从全市场可转债中精选组合。",
                    "",
                    "### 第一步：核心字段对齐",
                    f"全市场共 {screening['total_count']} 只可转债，提取 16 个核心字段：",
                    "收盘价、面值、剩余年限、当期收益率、YTM、修正久期、麦考利久期、",
                    "有效久期、凸性、有效凸性、DV01、PVBP、参数VaR(价格/%)、ES(价格/%)、",
                    "剩余规模、正股名称、转债类型、+50bp价格变动、-50bp价格变动",
                    "",
                    "### 第二步：硬过滤规则（必须全部通过）",
                    "- 剩余年限 >= 0.01 年          （排除已到期标的）",
                    "- 剩余规模 >= 1 亿元            （避免流动性枯竭）",
                    "- 正股不含\"退\"字              （规避违约风险）",
                    "- 收盘价 <= 130 元              （超过130博弈空间小）",
                    "- 参数VaR99 <= 3%              （单日极端跌幅可控）",
                    "- ES99 <= 6%                   （尾部风险不过大）",
                    "",
                    f">> 结果：{screening['total_count']} 只中保留 {screening['retained_count']} 只，淘汰 {screening['eliminated_count']} 只。",
                    "",
                    "### 第三步：四维度策略因子精筛",
                    "- 维度1：稳健收息型（防守）- 当期收益率×40% + (-YTM)×30% + 1/剩余年限×20% + 1/VaR×10%",
                    "- 维度2：深度价值型（折价套利）- (100-收盘价)×50% + YTM×30% + 1/剩余年限×20%",
                    "- 维度3：久期博弈型（利率敏感）- 剩余年限×40% + 修正久期×30% + 1/VaR×20% + 当期收益率×10%",
                    "- 维度4：风险调整收益（夏普替代）- 当期收益率 / VaR99",
                    "",
                    "---",
                    "最终推荐：交集法取同时满足多个策略维度的标的，辅以各维度首位。",
                ]
                self._add_text_page(pdf, '量化组合推荐总览', overview_lines)

                # ---------- 淘汰明细表 ----------
                elim = screening['eliminated']
                if not elim.empty:
                    elim_data = []
                    for _, row in elim.iterrows():
                        elim_data.append([
                            str(row.get('ts_code', ''))[:12],
                            str(row.get('bond_name', ''))[:10],
                            f"{row.get('close', 0):.1f}",
                            f"{row.get('var_pct', 0):.1f}%",
                            f"{row.get('es_pct', 0):.1f}%",
                            f"{row.get('rem_years', 0):.2f}",
                            f"{row.get('ytm', 0):.1f}%",
                            str(row.get('淘汰原因', ''))[:50],
                        ])
                    elim_cols = ['代码', '简称', '收盘价', 'VaR%', 'ES%', '剩余年', 'YTM%', '淘汰原因']
                    fig = self._generate_screening_table_fig(
                        elim_data, elim_cols,
                        f'硬过滤淘汰明细（共 {len(elim)} 只）',
                        col_widths=[0.10, 0.10, 0.08, 0.08, 0.08, 0.08, 0.08, 0.40],
                    )
                    if fig:
                        pdf.savefig(fig)
                        plt.close(fig)

                # ---------- 四维度表 ----------
                dim_columns = ['ts_code', 'bond_name', 'close', 'ytm', 'cur_yield', 'rem_years',
                               'mod_dur', 'mac_dur', 'eff_dur', 'convexity', 'eff_conv',
                               'dv01', 'pvbp', 'ytm_simple', 'var_price_hist',
                               'pct_p50bp', 'pct_m50bp',
                               'var_pct', 'es_pct',
                               'dim1_score', 'dim2_score', 'dim3_score', 'dim4_val']

                for dim_idx, (dim_df, dim_name, dim_key, score_col) in enumerate([
                    (screening['dim1'], '维度1-稳健收息型（防守）', 'dim1', 'dim1_score'),
                    (screening['dim2'], '维度2-深度价值型（折价套利）', 'dim2', 'dim2_score'),
                    (screening['dim3'], '维度3-久期博弈型（利率敏感）', 'dim3', 'dim3_score'),
                    (screening['dim4'], '维度4-风险调整收益（夏普替代）', 'dim4', 'dim4_val'),
                ]):
                    if dim_df is None or dim_df.empty:
                        continue
                    logger.info(f"生成 {dim_name} 表格 ({len(dim_df)} 只)")

                    dim_data = []
                    for _, row in dim_df.iterrows():
                        dim_data.append([
                            str(row.get('ts_code', ''))[:12],
                            str(row.get('bond_name', ''))[:10],
                            f"{row.get('close', 0):.1f}",
                            f"{row.get('ytm', 0):.1f}%",
                            f"{row.get('ytm_simple', 0):.1f}%",
                            f"{row.get('cur_yield', 0):.2f}%",
                            f"{row.get('rem_years', 0):.2f}",
                            f"{row.get('mod_dur', 0):.2f}",
                            f"{row.get('mac_dur', 0):.2f}",
                            f"{row.get('eff_dur', 0):.2f}",
                            f"{row.get('convexity', 0):.3f}",
                            f"{row.get('eff_conv', 0):.3f}",
                            f"{row.get('dv01', 0):.4f}",
                            f"{row.get('pvbp', 0):.4f}",
                            f"{row.get('pct_p50bp', 0):.2f}%",
                            f"{row.get('pct_m50bp', 0):.2f}%",
                            f"{row.get('var_price_hist', 0):.2f}",
                            f"{row.get('var_pct', 0):.1f}%",
                            f"{row.get('es_pct', 0):.1f}%",
                            f"{row.get(score_col, 0):.1f}",
                        ])
                    dim_cols = ['代码', '简称', '收盘', 'YTM%', '简式YTM%', '当期收%', '剩余年',
                                '修久期', '麦久期', '有久期', '凸性', '有效凸性',
                                'DV01', 'PVBP', '+50bp%', '-50bp%', 'HistVaR价',
                                'VaR%', 'ES%', '得分']
                    fig = self._generate_screening_table_fig(
                        dim_data, dim_cols, dim_name,
                        col_widths=[0.06, 0.06, 0.04, 0.05, 0.05, 0.05, 0.04,
                                    0.04, 0.04, 0.04, 0.05, 0.05,
                                    0.04, 0.04, 0.05, 0.05, 0.05,
                                    0.04, 0.04, 0.04],
                    )
                    if fig:
                        pdf.savefig(fig)
                        plt.close(fig)

                # ---------- 最终综合推荐 ----------
                final_recs = screening['final_recs']
                if final_recs:
                    final_data = []
                    for i, rec in enumerate(final_recs, 1):
                        final_data.append([
                            f"#{i}",
                            str(rec.get('ts_code', ''))[:12],
                            str(rec.get('bond_name', ''))[:10],
                            f"{rec.get('close', 0):.1f}",
                            f"{rec.get('ytm', 0):.1f}%",
                            f"{rec.get('ytm_simple', 0):.1f}%",
                            f"{rec.get('cur_yield', 0):.2f}%",
                            f"{rec.get('rem_years', 0):.2f}",
                            f"{rec.get('mod_dur', 0):.2f}",
                            f"{rec.get('mac_dur', 0):.2f}",
                            f"{rec.get('eff_dur', 0):.2f}",
                            f"{rec.get('convexity', 0):.3f}",
                            f"{rec.get('eff_conv', 0):.3f}",
                            f"{rec.get('dv01', 0):.4f}",
                            f"{rec.get('pvbp', 0):.4f}",
                            f"{rec.get('pct_p50bp', 0):.2f}%",
                            f"{rec.get('pct_m50bp', 0):.2f}%",
                            f"{rec.get('var_price_hist', 0):.2f}",
                            f"{rec.get('var_pct', 0):.1f}%",
                            f"{rec.get('es_pct', 0):.1f}%",
                            str(rec.get('dim_tags', '')),
                            str(rec.get('dim_count', 0)),
                        ])
                    final_cols = ['排名', '代码', '简称', '收盘', 'YTM%', '简式YTM%', '当期收%', '剩余年',
                                  '修久期', '麦久期', '有久期', '凸性', '有效凸性',
                                  'DV01', 'PVBP', '+50bp%', '-50bp%', 'HistVaR价',
                                  'VaR%', 'ES%', '匹配维度', '匹配数']
                    fig = self._generate_screening_table_fig(
                        final_data, final_cols,
                        f'最终量化推荐组合（共 {len(final_recs)} 只）',
                        subtitle='综合四维度交叉验证，优先选出多维度同时认可的标的',
                        col_widths=[0.03, 0.06, 0.06, 0.04, 0.04, 0.04, 0.05, 0.04,
                                    0.04, 0.04, 0.04, 0.04, 0.04,
                                    0.04, 0.04, 0.04, 0.04, 0.05,
                                    0.04, 0.04, 0.10, 0.03],
                    )
                    if fig:
                        pdf.savefig(fig)
                        plt.close(fig)

                    # 推荐理由页
                    rec_lines = [
                        "## 量化推荐总结",
                        "",
                        f"从 {screening['total_count']} 只可转债出发，经过硬过滤保留 {screening['retained_count']} 只，",
                        f"再经四维度独立精筛，最终综合推荐 {len(final_recs)} 只。",
                        "",
                        "### 筛选逻辑",
                        "本推荐完全基于硬指标量化打分，无主观拍脑袋。每一步阈值和权重均来自交易员实际风控框架。",
                        "",
                        "### 推荐要点",
                    ]
                    # 按维度分组展示
                    from collections import defaultdict
                    dim_groups = defaultdict(list)
                    for rec in final_recs:
                        for tag in rec['dim_tags'].split(','):
                            dim_groups[tag.strip()].append(rec)
                    for dim_tag, recs in dim_groups.items():
                        codes = [f"{r['ts_code'][:12]} {r['bond_name'][:8]}" for r in recs]
                        rec_lines.append(f"- **{dim_tag}**（{len(recs)}只）: {', '.join(codes[:5])}")
                    rec_lines.append("")
                    rec_lines.append("### 风险提示")
                    rec_lines.append("- 以上推荐基于量化模型和历史数据，不构成投资建议。")
                    rec_lines.append("- 实际交易需结合流动性、信用评级、正股基本面综合判断。")
                    rec_lines.append("- 建议单券仓位不超过组合的5%，定期再平衡。")
                    rec_lines.append("---")
                    self._add_text_page(pdf, '量化推荐总结与理由', rec_lines)

                    # ---------- AI 分析报告 ----------
                    ai_report = self._generate_ai_analysis_report(screening['dim4'])
                    if ai_report:
                        ai_lines = [
                            "以下为 AI 交易员基于维度4-风险调整收益的债券池，自动生成的可转债组合推荐分析：",
                            "",
                        ]
                        for line in ai_report.strip().split('\n'):
                            if line.strip():
                                ai_lines.append(line.strip())
                        self._add_text_page(pdf, 'AI 量化组合推荐分析', ai_lines)

        logger.info(f"PDF 策略报告已生成: {pdf_path}")
        return pdf_path

    # ==================== AI 分析报告 ====================

    def _generate_ai_analysis_report(self, dim4):
        """从维度4（风险调整收益）的债券中提取数据，调用 AI 生成可转债组合推荐分析报告

        Args:
            dim4: 维度4 DataFrame，包含 ts_code, bond_name, ytm, mod_dur, dv01, close, es_price 等列

        Returns:
            AI 分析报告字符串，失败时返回错误信息
        """
        if dim4 is None or dim4.empty:
            logger.info("维度4 无数据，跳过 AI 分析报告生成")
            return None

        # 提取必要列
        ai_bonds = dim4[['ts_code', 'bond_name', 'ytm', 'mod_dur', 'dv01', 'close', 'es_price']].copy()

        # 保留 2 位小数，节省 token
        ai_bonds['ytm'] = ai_bonds['ytm'].round(2)
        ai_bonds['mod_dur'] = ai_bonds['mod_dur'].round(2)
        ai_bonds['dv01'] = ai_bonds['dv01'].round(4)
        ai_bonds['close'] = ai_bonds['close'].round(2)
        ai_bonds['es_price'] = ai_bonds['es_price'].round(2)

        # 构建每行数据
        data_lines = []
        for _, row in ai_bonds.iterrows():
            data_lines.append(
                f"{row['ts_code']}, {row['bond_name']}, "
                f"ytm={row['ytm']:+.2f}, duration={row['mod_dur']:.2f}, "
                f"dv01={row['dv01']:.4f}, price={row['close']:.2f}, "
                f"es_price_99={row['es_price']:.2f}"
            )

        n = len(ai_bonds)
        data_block = "\n".join(data_lines)

        prompt = f"""你是一个资深的银行债券交易员。
以下是 {n} 只可转债的量化数据（ts_code, name, ytm, duration, dv01, price, es_price_99）：

{data_block}

请从这 {n} 只中，选出最适合构建投资组合的 5 只债券，并逐只简要说明选择理由。
只需要输出选出的 5 只债券的 ts_code 和理由，不需要计算组合权重。"""

        if CommonParameters.IF_ENABLE_MOCKED_AI:
            logger.info("IF_ENABLE_MOCKED_AI=True，返回模拟 AI 分析报告")
            return "（模拟 AI 分析报告）mocked AI analysis..."

        from dataIntegrator.LLMSuport.AiAgents.SparkAIX import SparkX2

        logger.info(f"正在调用 SparkX2 生成 AI 分析报告，输入 {n} 只债券数据")
        try:
            result = SparkX2.inquiry(prompt, "")
            logger.info("SparkX2 AI 分析报告生成成功")
            return result
        except Exception as e:
            logger.error(f"AI 分析报告生成失败: {e}")
            return f"AI 分析报告生成失败: {e}"

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

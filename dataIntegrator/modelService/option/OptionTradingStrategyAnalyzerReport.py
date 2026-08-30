r"""
OptionTradingStrategyAnalyzerReport — 期权策略分析报告生成器（读 ClickHouse 表 → 透视矩阵 Excel）

数据源：
    indexsysdb.tb_option_trading_strategy_indicator
    （由 OptionTradingStrategyAnalyzer 写入，内容 = Excel 报表各 Sheet 写入列的并集）

报告形式：
    单一 Excel 文件，Sheet 内容为「指标 × 合约」透视矩阵：
        - 行 = 指标/字段（按交易员视角排序，重复字段去重）
        - 列 = 合约（按行权价 exercise_price 升序排列）
        - 在 cost_efficiency 行之后插入扩展指标块，再跟多情景盈亏等剩余字段

文件名：
    OptionTradingStrategyAnalyzerReport_{trade_date}_{生成时间yyyymmdd_hhmmss}_{合约前缀}_{C/P}.xlsx
    示例: OptionTradingStrategyAnalyzerReport_20260717_20260830_103000_HO2612_C.xlsx
    （加入生成时间戳，避免同一交易日重复生成时文件被 Excel 占用导致覆盖失败）

输出路径：
    CommonParameters.optionAnalysisReportPath
    (D:\workspace_python\infinity_data\outbound\report\OptionAnalysis\)

运行方式：
    python -m dataIntegrator.modelService.option.OptionTradingStrategyAnalyzerReport
"""

import os
import io
import numpy as np
import pandas as pd
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

# 尝试定位系统中可用的中文字体（Windows 常见路径）
def _get_chinese_font():
    """返回系统中可用的中文字体 FontProperties，找不到则返回 None"""
    candidates = [
        # Windows 常见中文字体（按推荐优先级）
        r'C:\Windows\Fonts\msyh.ttc',      # Microsoft YaHei
        r'C:\Windows\Fonts\msyhbd.ttc',    # Microsoft YaHei Bold
        r'C:\Windows\Fonts\simhei.ttf',    # SimHei
        r'C:\Windows\Fonts\simsun.ttc',    # SimSun
        r'C:\Windows\Fonts\msjh.ttc',      # Microsoft JhengHei
        r'C:\Windows\Fonts\msgothic.ttc',  # MS Gothic（日文，但含中文）
        # Linux 常见中文字体
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]
    for path in candidates:
        if os.path.exists(path):
            return FontProperties(fname=path)
    return None

_CHINESE_FONT = _get_chinese_font()

# 同时设置 rcParams 作为后备
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.drawing.image import Image as XLImage

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.modelService.option.OptionTradingStrategyAnalyzer import \
    OptionTradingStrategyAnalyzer

logger = CommonLib.logger


class OptionTradingStrategyAnalyzerReport:
    """期权策略分析报告生成器

    读取 tb_option_trading_strategy_indicator，按 trade_date + ts_code 过滤，
    转置为「行 = 字段，列 = 合约(按行权价升序)」的透视矩阵并导出 Excel。
    """

    # === 表名 ===
    TABLE_SOURCE = 'tb_option_trading_strategy_indicator'

    # === 输出路径（与分析器一致） ===
    REPORT_DIR = CommonParameters.optionAnalysisReportPath

    # === 基础字段（用户示例矩阵顺序） ===
    BASE_FIELDS = [
        'trade_date', 'ts_code', 'exercise_price', 'close',
        'spot_price', 'days_to_maturity', 'moneyness_status',
        'cost_efficiency',
    ]

    # === 扩展指标块（插入在 cost_efficiency 之后，按交易员视角排序） ===
    # 交易员读完 cost_efficiency 后，紧接着关心：
    #   到期盈亏 → 盈亏平衡 → 概率加权 → 年化 → 最大风险 → 杠杆 →
    #   时间衰减成本 → 定价偏差 → IV/Greeks → 交易信号
    EXTENDED_FIELDS = [
        # --- 到期盈亏 (S_T = K) ---
        'total_pnl_at_K', 'total_pnl_at_K_cny',
        # --- 盈亏平衡 ---
        'breakeven_S_T', 'breakeven_S_T_pct', 'breakeven_type',
        'pure_call_breakeven', 'pure_call_breakeven_pct',
        # --- 概率加权 / 年化收益 ---
        'delta_weighted_pnl', 'annualized_return_pct',
        # --- 最大风险 / 杠杆 ---
        'strategy_max_loss', 'strategy_max_loss_cny', 'strategy_max_loss_pct_of_spot',
        'leverage_notional',
        # --- 时间衰减成本 ---
        'theta_cost_daily', 'theta_cost_total', 'theta_cost_pct_of_premium',
        'pnl_after_theta',
        # --- 定价偏差 (市价 vs BS 理论价) ---
        'close_vs_theoretical', 'close_vs_theoretical_pct', 'price_bias',
        # --- IV 与 Greeks ---
        'implied_vol', 'bs_theoretical_price',
        'delta', 'gamma', 'theta', 'vega', 'rho',
        # --- 交易信号 ---
        'trade_signal', 'signal_reason',
        # --- 价态细化 ---
        'moneyness_log', 'K_S_ratio', 'spot_to_strike', 'spot_to_strike_pct',
    ]

    # === 需要从字段列表中排除的表元数据列 ===
    EXCLUDE_COLUMNS = {'insert_time'}

    # === 需要按数值从小到大（绿→黄→红）着色的字段 ===
    COLOR_SCALE_FIELDS = {
        'moneyness_log', 'K_S_ratio', 'spot_to_strike', 'spot_to_strike_pct',
        'opt_name', 'opt_exchange', 'call_put', 'opt_multiplier',
        's_month', 'maturity_date', 'years_to_maturity_calendar',
        'open', 'high', 'low', 'settle', 'pre_close',
        'vol', 'amount', 'oi', 'pct_change', 'turnover_ratio',
        'd1', 'd2', 'nd1', 'nd2',
        # --- 扩展指标 / 盈亏平衡 / 年化收益 ---
        'breakeven_S_T', 'breakeven_S_T_pct',
        'pure_call_breakeven', 'pure_call_breakeven_pct',
        'delta_weighted_pnl', 'annualized_return_pct',
        # --- 最大风险 / 杠杆 ---
        'strategy_max_loss', 'strategy_max_loss_cny', 'strategy_max_loss_pct_of_spot',
        'leverage_notional',
        # --- 时间衰减成本 ---
        'theta_cost_daily', 'theta_cost_total', 'theta_cost_pct_of_premium',
        'pnl_after_theta',
        # --- 定价偏差 / IV / Greeks ---
        'close_vs_theoretical', 'close_vs_theoretical_pct', 'price_bias',
        'implied_vol', 'bs_theoretical_price',
        'delta', 'gamma', 'theta', 'vega', 'rho',
    }

    # === 字段说明（说明列显示，覆盖全部字段） ===
    # 说明 = 字段作用 + 核心算法（与 OptionTradingStrategyAnalyzer 计算逻辑一致）
    FIELD_DESCRIPTIONS = {
        # ---------- 基础标识字段 ----------
        'trade_date': '交易日期 YYYYMMDD，本报表数据所属交易日',
        'ts_code': '合约代码，如 HO2612-C-2700.CFX（品种+月份+类型+行权价+交易所）',
        'exercise_price': '行权价 K，期权合约约定的到期买入/卖出标的的执行价格',
        'close': '期权当日收盘价 C（策略成本组成部分，权利金单价）',
        'spot_price': '标的指数当日收盘价 S0（现货买入成本基准）',
        'days_to_maturity': '距到期日历天数 T（剩余交易自然日）',
        'moneyness_status': '价态判定：ITM实值/ATM平值/OTM虚值（按 |S-K|/K 与 call_put 判定）',
        'cost_efficiency': '收益成本比 = (K-S0)/C，核心指标：>1 到期 S_T=K 时现货涨幅可覆盖权利金成本',
        # ---------- 扩展指标块（到期盈亏 / 盈亏平衡 / 概率加权 / 风险 / 时间衰减 / 定价 / Greeks / 信号） ----------
        'total_pnl_at_K': '到期 S_T=K 时组合净盈亏 = K - S0 - C（现货盈利 K-S0 减去权利金 C）',
        'total_pnl_at_K_cny': '到期组合盈亏金额 = total_pnl_at_K × opt_multiplier（元）',
        'breakeven_S_T': '策略盈亏平衡标的价：cost_efficiency≤1 时 =(S0+K+C)/2（需 S_T>K）；>1 时 =S0+C',
        'breakeven_S_T_pct': '盈亏平衡涨幅 = (breakeven_S_T/S0-1)×100%',
        'breakeven_type': '盈亏平衡情景类型：S_T>K（期权有价值）/ S_T<K（期权作废亦可盈利）',
        'pure_call_breakeven': '纯买Call盈亏平衡价 = K + C（不买现货时需标的涨过此价）',
        'pure_call_breakeven_pct': '纯Call盈亏平衡涨幅 = (K+C)/S0-1 的百分比',
        'delta_weighted_pnl': '概率加权期望盈亏 = delta × total_pnl_at_K（按Delta概率折算的期望收益）',
        'annualized_return_pct': '年化收益率 = total_pnl_at_K / C / years × 100%（权利金投入的年化回报）',
        'strategy_max_loss': '策略最大亏损 = -C（最多亏掉全部权利金，现货不跌则无额外损失）',
        'strategy_max_loss_cny': '最大亏损金额 = -C × opt_multiplier（元）',
        'strategy_max_loss_pct_of_spot': '最大亏损占现货比例 = -C/S0×100%',
        'leverage_notional': '杠杆倍数 = S0/C（一份权利金撬动的现货名义价值）',
        'theta_cost_daily': '每日时间衰减成本 = |theta|（期权价值每日损耗）',
        'theta_cost_total': '持有到期总时间衰减 = |theta| × days_to_maturity',
        'theta_cost_pct_of_premium': '时间衰减占权利金比例 = theta_cost_total/C×100%',
        'pnl_after_theta': '扣除时间成本后的净盈亏 = total_pnl_at_K - theta_cost_total',
        'close_vs_theoretical': '市价偏离BS理论价 = close - bs_theoretical_price',
        'close_vs_theoretical_pct': '市价偏离率 = (close - BS价)/BS价 × 100%',
        'price_bias': '定价偏离判定：<-5%严重低估 / -5~-1%低估 / ±1%公允 / 1~5%高估 / >5%严重高估',
        'implied_vol': '隐含波动率 σ（BS模型反解，小数，衡量市场对标的波动的预期）',
        'bs_theoretical_price': 'BS模型理论价（用隐含波动率回算的期权公允价格）',
        'delta': 'Delta：标的价格变动1单位时期权价格变化量（Call 0~1，虚值越小）',
        'gamma': 'Gamma：标的价格变动1单位时 Delta 的变化量（凸性度量）',
        'theta': 'Theta：每过1天期权价格的时间衰减（通常为负）',
        'vega': 'Vega：波动率每变动1%（0.01）时期权价格变化量',
        'rho': 'Rho：无风险利率每变动1%时期权价格变化量',
        'trade_signal': '交易信号：STRONG_BUY/BUY/CONSIDER/NEUTRAL/AVOID（综合 cost_efficiency+定价偏差+Delta 判定）',
        'signal_reason': '信号依据：触发该信号的具体原因组合（如成本效率>1.05 且 市价低估等）',
        # ---------- 价态细化 ----------
        'moneyness_log': '对数价态 = ln(K/S)/√T，衡量行权价偏离标的价格的程度（Call正值=虚值）',
        'K_S_ratio': '行权价与标的价格比值 = K/S0（>1 表示行权价高于现价）',
        'spot_to_strike': '标的需要上涨的绝对幅度 = K - S0（现货到行权价的空间）',
        'spot_to_strike_pct': '标的需要上涨的百分比 = (K/S0-1)×100%',
        # ---------- 合约要素 ----------
        'opt_name': '合约名称（如：上证50指数期权2612认购2700）',
        'opt_exchange': '期权交易所代码（如 CFFEX 中金所）',
        'call_put': '期权类型：C=认购(Call) / P=认沽(Put)',
        'opt_multiplier': '合约乘数（每点对应金额，如 100 元/点），盈亏金额 = 点数 × 乘数',
        's_month': '结算月份 YYYYMM（合约到期结算的月份）',
        'maturity_date': '到期日 YYYYMMDD（合约最后交易日/行权日）',
        'years_to_maturity_calendar': '距到期年数 = 日历天数/365（BS定价的时间参数）',
        # ---------- 标的市场参数 ----------
        'risk_free_rate': '无风险利率 r（SHIBOR 年化，BS定价折现参数）',
        'dividend_yield': '股息率 q = payout_ratio/pe_ttm（BS定价股息调整参数）',
        # ---------- 期权行情 ----------
        'open': '开盘价（当日第一笔成交价）',
        'high': '最高价（当日最高成交价）',
        'low': '最低价（当日最低成交价）',
        'settle': '结算价（交易所公布的当日结算参考价）',
        'pre_close': '前收盘价（上一交易日收盘价）',
        'vol': '成交量（手）',
        'amount': '成交金额（万元）',
        'oi': '持仓量（手，未平仓合约总数）',
        'pct_change': '日内涨跌幅 = (close/pre_close-1)×100%',
        'turnover_ratio': '换手率 ≈ vol/oi，反映交易活跃度',
        # ---------- BS 中间参数 ----------
        'd1': 'BS参数 d1 = [ln(S/K)+(r-q+σ²/2)T]/(σ√T)',
        'd2': 'BS参数 d2 = d1 - σ√T',
        'nd1': '标准正态累积概率 N(d1)，即期权 Delta',
        'nd2': '标准正态累积概率 N(d2)，即到期行权概率（S_T>K 概率）',
    }

    # 多情景盈亏字段说明（动态生成，与 DEFAULT_SCENARIOS 对应）
    SCENARIO_FACTORS = [1.00, 1.03, 1.05, 1.08, 1.10, 1.15, 1.20]
    SCENARIO_DESCRIPTIONS = {
        'scenario_pnl': '情景盈亏 = S_T + max(0, S_T-K) - S0 - C（S_T=K×{factor:.2f}，组合到期总盈亏）',
        'scenario_pnl_cny': '情景盈亏金额 = scenario_pnl × opt_multiplier（元）',
        'scenario_pnl_pct': '情景收益率 = scenario_pnl/(S0+C)×100%（投入资金回报率）',
        'pure_call_pnl': '纯期权盈亏 = max(0, S_T-K) - C（不买现货仅持Call）',
        'pure_call_pnl_cny': '纯期权盈亏金额 = pure_call_pnl × opt_multiplier（元）',
        'pure_call_pnl_pct': '纯期权收益率 = pure_call_pnl/C×100%（权利金回报率）',
    }

    # === Excel 样式常量（与分析器保持一致） ===
    HEADER_FILL = PatternFill(start_color='1F4E79', end_color='1F4E79', fill_type='solid')
    HEADER_FONT = Font(name='Microsoft YaHei', size=10, bold=True, color='FFFFFF')
    BODY_FONT = Font(name='Microsoft YaHei', size=9)
    TITLE_FONT = Font(name='Microsoft YaHei', size=14, bold=True, color='1F4E79')
    SUBTITLE_FONT = Font(name='Microsoft YaHei', size=11, bold=True, color='2E75B6')
    GREEN_FILL = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
    RED_FILL = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
    YELLOW_FILL = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')
    LIGHT_BLUE_FILL = PatternFill(start_color='BDD7EE', end_color='BDD7EE', fill_type='solid')
    THIN_BORDER = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9'),
    )
    CENTER_ALIGN = Alignment(horizontal='center', vertical='center', wrap_text=True)
    LEFT_ALIGN = Alignment(horizontal='left', vertical='center', wrap_text=True)

    def __init__(self):
        os.makedirs(self.REPORT_DIR, exist_ok=True)
        # 合并多情景盈亏字段的动态说明到字段说明字典
        self.FIELD_DESCRIPTIONS = {**self.FIELD_DESCRIPTIONS,
                                   **self._build_scenario_descriptions()}
        logger.info(f"OptionTradingStrategyAnalyzerReport initialized. "
                    f"Report dir: {self.REPORT_DIR}, "
                    f"{len(self.FIELD_DESCRIPTIONS)} field descriptions loaded")

    @classmethod
    def _build_scenario_descriptions(cls):
        """动态生成多情景盈亏字段的说明（scenario_pnl_* / pure_call_pnl_*）"""
        desc = {}
        for factor in cls.SCENARIO_FACTORS:
            label = f'{factor:.2f}'.replace('.', '_')
            for suffix, template in cls.SCENARIO_DESCRIPTIONS.items():
                desc[f'{suffix}_{label}K'] = template.format(factor=factor)
        return desc

    # ================================================================
    # Step 1: 数据拉取
    # ================================================================
    def fetch_data(self, trade_date, ts_code_filter=None, call_put=None):
        """从 tb_option_trading_strategy_indicator 拉取指定日期的数据

        Args:
            trade_date: 交易日期 YYYYMMDD
            ts_code_filter: LIKE 过滤，如 'HO2612%'
            call_put: 'C' 看涨 / 'P' 看跌 / None 不过滤

        Returns:
            pd.DataFrame: 按行权价升序排列的当日数据
        """
        logger.info("=" * 80)
        logger.info(f"Fetching strategy indicator data: trade_date={trade_date}, "
                    f"filter={ts_code_filter}, call_put={call_put}")

        where_clauses = [f"trade_date = '{trade_date}'"]
        if ts_code_filter:
            where_clauses.append(f"ts_code LIKE '{ts_code_filter}'")
        if call_put:
            where_clauses.append(f"call_put = '{call_put}'")

        sql = f"""
        SELECT *
        FROM indexsysdb.{self.TABLE_SOURCE}
        WHERE {' AND '.join(where_clauses)}
        ORDER BY exercise_price
        """
        logger.info(f"SQL:\n{sql}")
        df = ClickhouseService.getDataFrameWithoutColumnsName(sql)

        if len(df) == 0:
            logger.warning("No data fetched, returning empty DataFrame")
            return pd.DataFrame()

        logger.info(f"Fetched {len(df)} rows, {len(df.columns)} columns")

        # 类型转换：数值列转 float，字符串列转 str
        str_cols = {'trade_date', 'ts_code', 'opt_name', 'opt_exchange', 'call_put',
                    's_month', 'maturity_date', 'moneyness_status', 'price_bias',
                    'breakeven_type', 'trade_signal', 'signal_reason'}
        for col in df.columns:
            if col in str_cols:
                df[col] = df[col].fillna('').astype(str)
            elif col not in self.EXCLUDE_COLUMNS:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    # ================================================================
    # Step 2: 构建字段行列表（去重 + 交易员视角排序）
    # ================================================================
    def build_field_order(self, df):
        """构建透视矩阵的字段行列表

        顺序规则（按交易员视角）：
            1. BASE_FIELDS：基础标识字段（示例矩阵顺序）
            2. EXTENDED_FIELDS：扩展指标块（插入在 cost_efficiency 之后）
            3. 按 TARGET_COLUMNS 顺序补全剩余字段（多情景盈亏、纯期权盈亏等）
            4. 兜底：df 中仍存在的其他字段
        所有字段去重（保留首次出现），并排除表元数据列。

        Args:
            df: fetch_data 返回的 DataFrame

        Returns:
            list[str]: 去重后的有序字段列表
        """
        ordered = []
        seen = set()

        # 1 + 2: 基础字段 + 扩展指标块（交易员视角核心顺序）
        for field in self.BASE_FIELDS + self.EXTENDED_FIELDS:
            if field in df.columns and field not in seen:
                seen.add(field)
                ordered.append(field)

        # 3: 按目标表字段顺序补全剩余字段
        target_columns = OptionTradingStrategyAnalyzer.TARGET_COLUMNS
        for field in target_columns:
            if field in df.columns and field not in seen:
                seen.add(field)
                ordered.append(field)

        # 4: 兜底补全（如 insert_time 之外的其余列）
        for field in df.columns:
            if field in self.EXCLUDE_COLUMNS:
                continue
            if field not in seen:
                seen.add(field)
                ordered.append(field)

        logger.info(f"Field order built: {len(ordered)} fields "
                    f"(deduplicated from {len(df.columns)} raw columns)")
        return ordered

    # ================================================================
    # Step 3: 导出 Excel 透视矩阵
    # ================================================================
    # ================================================================
    # 图表：到期盈亏曲线 & 到期收益率曲线
    # ================================================================
    def _plot_payoff_curves(self, df_sorted, trade_date, call_put_str):
        """绘制到期盈亏曲线（左）和到期收益率曲线（右），返回 BytesIO

        左图：纯Call买方到期盈亏（元/张，×乘数），max(0, S_T-K) - C
        右图：到期收益率（盈亏/权利金 %），杠杆效应

        Args:
            df_sorted: 按行权价升序排列的合约 DataFrame
            trade_date: 交易日 YYYYMMDD
            call_put_str: 'C'/'P'

        Returns:
            io.BytesIO: PNG 图像字节流
        """
        if len(df_sorted) == 0:
            return None

        S0 = df_sorted['spot_price'].iloc[0]
        mult = df_sorted['opt_multiplier'].iloc[0]
        spot_label = f'现货 {int(S0)}'

        # X 轴：到期标的价格范围（从最低行权价的 0.88 到最高行权价的 1.15）
        K_min = df_sorted['exercise_price'].min()
        K_max = df_sorted['exercise_price'].max()
        S_T_range = np.linspace(K_min * 0.88, K_max * 1.15, 500)

        # 颜色映射（按行权价从小到大，颜色从深到浅 viridis）
        colors = plt.cm.viridis(np.linspace(0.15, 0.85, len(df_sorted)))

        fig, axes = plt.subplots(1, 2, figsize=(16, 7))
        fp = _CHINESE_FONT  # 显式中文字体（若系统找不到则为 None）

        # ---------- 左图：到期盈亏曲线（元/张，×乘数） ----------
        ax1 = axes[0]
        for idx, (_, row) in enumerate(df_sorted.iterrows()):
            K = row['exercise_price']
            C = row['close']
            # 纯Call到期盈亏 = max(0, S_T - K) - C，再 × 乘数
            pnl = np.maximum(0, S_T_range - K) - C
            pnl_cny = pnl * mult
            label = f"C-{int(K)} (Close={C:.2f})"
            ax1.plot(S_T_range, pnl_cny, color=colors[idx], linewidth=2, label=label)

        ax1.axhline(0, color='gray', linewidth=1, linestyle='--')
        ax1.axvline(S0, color='red', linewidth=1.5, linestyle=':', label=spot_label)
        ax1.set_title(f'到期盈亏曲线（纯Call买方，元/张，乘数{int(mult)}）', fontsize=13, fontproperties=fp)
        ax1.set_xlabel('到期标的价格 S_T', fontsize=11, fontproperties=fp)
        ax1.set_ylabel('盈亏（元）', fontsize=11, fontproperties=fp)
        ax1.legend(loc='upper left', fontsize=7, ncol=2, prop=fp)
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(S_T_range.min(), S_T_range.max())

        # ---------- 右图：到期收益率曲线（盈亏/权利金 %） ----------
        ax2 = axes[1]
        for idx, (_, row) in enumerate(df_sorted.iterrows()):
            K = row['exercise_price']
            C = row['close']
            # 收益率 = (max(0, S_T - K) - C) / C × 100%
            pnl = np.maximum(0, S_T_range - K) - C
            ret_pct = np.where(C > 0, pnl / C * 100, 0)
            label = f"C-{int(K)} (Close={C:.2f})"
            ax2.plot(S_T_range, ret_pct, color=colors[idx], linewidth=2, label=label)

        ax2.axhline(0, color='gray', linewidth=1, linestyle='--')
        ax2.axvline(S0, color='red', linewidth=1.5, linestyle=':', label=spot_label)
        ax2.set_title('到期收益率曲线（盈亏/权利金，%，凸显杠杆）', fontsize=13, fontproperties=fp)
        ax2.set_xlabel('到期标的价格 S_T', fontsize=11, fontproperties=fp)
        ax2.set_ylabel('收益率（%）', fontsize=11, fontproperties=fp)
        ax2.legend(loc='upper left', fontsize=7, ncol=2, prop=fp)
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim(S_T_range.min(), S_T_range.max())

        fig.suptitle(f'{trade_date} {call_put_str} 期权到期盈亏与收益率分析',
                     fontsize=15, fontweight='bold', y=1.02, fontproperties=fp)
        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        return buf

    def export_to_excel(self, df, trade_date, ts_code_filter=None, call_put=None):
        """导出「指标 × 合约」透视矩阵 Excel，并附加图表 Sheet

        行 = 字段，列 = 合约（按行权价升序），最右增加说明列。
        对指定字段行按数值从小到大应用绿→黄→红色阶。
        新增 Sheet「到期盈亏曲线」嵌入两张图表。

        Args:
            df: fetch_data 返回的当日数据
            trade_date: 交易日期 YYYYMMDD（用于文件名与标题）
            ts_code_filter: LIKE 过滤，用于文件名前缀
            call_put: 'C'/'P'，用于文件名

        Returns:
            str or None: Excel 文件路径
        """
        if len(df) == 0:
            logger.warning("Empty DataFrame, nothing to export")
            return None

        # 按行权价升序排列合约
        df_sorted = df.sort_values('exercise_price', ascending=True).reset_index(drop=True)
        n_contracts = len(df_sorted)
        data_end_col = 1 + n_contracts        # A列指标 + 合约列
        desc_col = data_end_col + 1           # 说明列（K列在9合约时）
        total_cols = desc_col                 # 总列数

        # 字段行列表
        fields = self.build_field_order(df_sorted)

        # 文件名: OptionTradingStrategyAnalyzerReport_{date}_{生成时间yyyymmdd_hhmmss}_{prefix}_{call_put}.xlsx
        # 加入生成时间戳，避免同一交易日重复生成时文件被 Excel 占用导致覆盖失败
        prefix = self._extract_prefix(ts_code_filter)
        call_put_str = call_put or 'ALL'
        gen_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = (f'OptionTradingStrategyAnalyzerReport_{trade_date}_{gen_ts}'
                    f'_{prefix}_{call_put_str}.xlsx')
        filepath = os.path.join(self.REPORT_DIR, filename)

        logger.info(f"Exporting Excel to: {filepath}")

        wb = Workbook()
        ws = wb.active
        ws.title = "策略指标透视"

        # --- 标题 ---
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=total_cols)
        spot_price = float(df_sorted['spot_price'].iloc[0])
        title_cell = ws.cell(
            row=1, column=1,
            value=f'期权策略指标透视 — {trade_date} {call_put_str} | spot_price ： {spot_price:.2f}'
        )
        title_cell.font = self.TITLE_FONT
        title_cell.alignment = Alignment(horizontal='left', vertical='center')
        ws.row_dimensions[1].height = 30

        # --- 副标题 ---
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=total_cols)
        sub_cell = ws.cell(
            row=2, column=1,
            value=f'数据源: indexsysdb.{self.TABLE_SOURCE} | 交易日: {trade_date} | '
                  f'共 {n_contracts} 个合约 | 按行权价升序排列 | 行 = 指标, 列 = 合约 | '
                  f'右侧列 = 字段说明'
        )
        sub_cell.font = self.SUBTITLE_FONT
        sub_cell.alignment = Alignment(horizontal='left', vertical='center')
        ws.row_dimensions[2].height = 22

        # --- 表头 (row 3): A3=指标, B3..=ts_code, 最右=说明 ---
        header_row = 3
        h0 = ws.cell(row=header_row, column=1, value='指标/字段')
        h0.font = self.HEADER_FONT
        h0.fill = self.HEADER_FILL
        h0.alignment = self.CENTER_ALIGN
        h0.border = self.THIN_BORDER
        for col_idx, (_, row) in enumerate(df_sorted.iterrows(), 2):
            cell = ws.cell(row=header_row, column=col_idx, value=str(row['ts_code']))
            cell.font = self.HEADER_FONT
            cell.fill = self.HEADER_FILL
            cell.alignment = self.CENTER_ALIGN
            cell.border = self.THIN_BORDER
        h_desc = ws.cell(row=header_row, column=desc_col, value='说明')
        h_desc.font = self.HEADER_FONT
        h_desc.fill = self.HEADER_FILL
        h_desc.alignment = self.CENTER_ALIGN
        h_desc.border = self.THIN_BORDER
        ws.row_dimensions[header_row].height = 28
        ws.freeze_panes = ws.cell(row=header_row + 1, column=1)

        # --- 数据行 ---
        start_row = header_row + 1
        for row_idx, field in enumerate(fields, start_row):
            name_cell = ws.cell(row=row_idx, column=1, value=field)
            name_cell.font = Font(name='Microsoft YaHei', size=9, bold=True)
            name_cell.alignment = self.LEFT_ALIGN
            name_cell.border = self.THIN_BORDER

            fmt = self._resolve_number_format(field)
            for col_idx, (_, row) in enumerate(df_sorted.iterrows(), 2):
                val = row.get(field)
                if isinstance(val, float) and (pd.isna(val) or np.isinf(val)):
                    val = None
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.font = self.BODY_FONT
                cell.alignment = self.CENTER_ALIGN
                cell.border = self.THIN_BORDER
                if fmt and val is not None:
                    cell.number_format = fmt

            # 说明列
            desc_text = self.FIELD_DESCRIPTIONS.get(field, '')
            desc_cell = ws.cell(row=row_idx, column=desc_col, value=desc_text)
            desc_cell.font = Font(name='Microsoft YaHei', size=9, color='404040')
            desc_cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
            desc_cell.border = self.THIN_BORDER

            # 关键指标行着色（静态 fill）
            self._paint_pivot_row(ws, row_idx, field, df_sorted)

            # 条件格式：绿→黄→红色阶（从小到大）
            if field in self.COLOR_SCALE_FIELDS and n_contracts > 0:
                data_range = f'B{row_idx}:{get_column_letter(data_end_col)}{row_idx}'
                color_rule = ColorScaleRule(
                    start_type='min', start_color='C6EFCE',      # 绿
                    mid_type='percentile', mid_value=50, mid_color='FFEB9C',  # 黄
                    end_type='max', end_color='FFC7CE'           # 红
                )
                ws.conditional_formatting.add(data_range, color_rule)

        # --- 列宽 ---
        ws.column_dimensions['A'].width = 32
        for col_idx in range(2, data_end_col + 1):
            ws.column_dimensions[get_column_letter(col_idx)].width = 18
        ws.column_dimensions[get_column_letter(desc_col)].width = 55

        # --- 备注 ---
        note_row = start_row + len(fields) + 1
        ws.merge_cells(start_row=note_row, start_column=1,
                       end_row=note_row, end_column=total_cols)
        note_cell = ws.cell(row=note_row, column=1, value=self._build_note())
        note_cell.font = Font(name='Microsoft YaHei', size=9, color='808080')
        note_cell.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
        ws.row_dimensions[note_row].height = 440

        # --- 图表 Sheet：到期盈亏曲线 ---
        chart_buf = self._plot_payoff_curves(df_sorted, trade_date, call_put_str)
        if chart_buf:
            ws_chart = wb.create_sheet(title="到期盈亏曲线")
            img = XLImage(chart_buf)
            img.width = 1100
            img.height = 500
            ws_chart.add_image(img, 'A1')
            ws_chart.column_dimensions['A'].width = 25
            ws_chart.row_dimensions[1].height = 380
            logger.info("Chart sheet '到期盈亏曲线' added")

        wb.save(filepath)
        logger.info(f"Excel report saved: {filepath}")
        return filepath

    # ================================================================
    # 辅助方法
    # ================================================================
    @staticmethod
    def _extract_prefix(ts_code_filter):
        """从 LIKE 过滤条件提取文件名前缀，如 'HO2612%' → 'HO2612'"""
        if not ts_code_filter:
            return 'ALL'
        return str(ts_code_filter).replace('%', '').strip()

    def _resolve_number_format(self, field):
        """根据字段名解析 Excel 数值格式（与分析器保持一致）"""
        if field in ('pct_change', 'spot_to_strike_pct', 'breakeven_S_T_pct',
                     'pure_call_breakeven_pct', 'theta_cost_pct_of_premium',
                     'close_vs_theoretical_pct', 'annualized_return_pct',
                     'strategy_max_loss_pct_of_spot'):
            return '0.00"%"'
        if field in ('implied_vol', 'risk_free_rate', 'dividend_yield'):
            return '0.00%'
        if field in ('delta', 'gamma', 'theta', 'vega', 'rho',
                     'd1', 'd2', 'nd1', 'nd2'):
            return '0.0000'
        if field in ('cost_efficiency', 'K_S_ratio', 'moneyness_log'):
            return '0.0000'
        if field in ('close', 'settle', 'open', 'high', 'low', 'pre_close',
                     'exercise_price', 'spot_price',
                     'spot_to_strike', 'total_pnl_at_K',
                     'breakeven_S_T', 'pure_call_breakeven',
                     'delta_weighted_pnl', 'theta_cost_daily',
                     'theta_cost_total', 'pnl_after_theta',
                     'bs_theoretical_price', 'close_vs_theoretical',
                     'spot_gain_at_K', 'strategy_max_loss', 'avg_unit_price'):
            return '#,##0.00'
        if field in ('mtm_pnl_close', 'mtm_pnl_settle',
                     'total_pnl_at_K_cny', 'strategy_max_loss_cny',
                     'pure_call_max_loss_cny', 'days_to_maturity',
                     'vol', 'amount', 'oi'):
            return '#,##0'
        if 'scenario_pnl' in field or 'pure_call_pnl' in field:
            if '_pct' in field:
                return '0.00"%"'
            if '_cny' in field:
                return '#,##0'
            return '#,##0.00'
        if field == 'leverage_notional':
            return '0.0"x"'
        return None

    def _paint_pivot_row(self, ws, row_idx, field, df_sorted):
        """对透视矩阵的特定指标行着色"""
        if field == 'cost_efficiency':
            for col_idx, (_, row) in enumerate(df_sorted.iterrows(), 2):
                val = row.get(field)
                if isinstance(val, (int, float)) and not pd.isna(val):
                    cell = ws.cell(row=row_idx, column=col_idx)
                    if val >= 1.0:
                        cell.fill = self.GREEN_FILL
                    elif val >= 0.85:
                        cell.fill = self.YELLOW_FILL
                    else:
                        cell.fill = self.RED_FILL
        elif field == 'trade_signal':
            for col_idx, (_, row) in enumerate(df_sorted.iterrows(), 2):
                val = str(row.get(field) or '')
                cell = ws.cell(row=row_idx, column=col_idx)
                if val == 'STRONG_BUY':
                    cell.fill = self.GREEN_FILL
                elif val == 'BUY':
                    cell.fill = self.YELLOW_FILL
                elif val == 'AVOID':
                    cell.fill = self.RED_FILL
        elif field.startswith('scenario_pnl_') or field.startswith('pure_call_pnl_'):
            # 只给盈亏金额列着色 (跳过 _cny / _pct)
            if field.endswith('_cny') or field.endswith('_pct'):
                return
            for col_idx, (_, row) in enumerate(df_sorted.iterrows(), 2):
                val = row.get(field)
                if isinstance(val, (int, float)) and not pd.isna(val):
                    cell = ws.cell(row=row_idx, column=col_idx)
                    if val > 0:
                        cell.fill = self.GREEN_FILL
                    elif val < 0:
                        cell.fill = self.RED_FILL

    def _build_note(self):
        """报表备注说明（字段作用 + 公式）"""
        lines = [
            '【策略指标透视 说明】',
            '本报表读取 indexsysdb.tb_option_trading_strategy_indicator（由 OptionTradingStrategyAnalyzer 写入），',
            '按交易日 + 合约前缀生成「指标 × 合约」透视矩阵：行 = 指标/字段, 列 = 合约(按行权价升序)。',
            '策略定义: 买入现货 + 买入 Call（Spot + Long Call），到期标的价格 S_T = K 为基准情景。',
            '最右侧列为「说明」，对该行字段含义与算法进行简要注释。',
            '',
            '【核心指标公式】',
            'cost_efficiency = (K - S0) / C : 收益成本比，> 1 表示到期 S_T=K 时现货涨幅可覆盖权利金成本',
            'total_pnl_at_K = K - S0 - C : 到期 S_T=K 时组合净盈亏;  total_pnl_at_K_cny = total_pnl_at_K × 乘数',
            'breakeven_S_T: 策略盈亏平衡标的价 (cost_efficiency<=1 时 = (S0+K+C)/2; >1 时 = S0+C)',
            'delta_weighted_pnl = delta × total_pnl_at_K : 概率加权期望盈亏',
            'theta_cost_total = |theta| × days_to_maturity : 持有到期总时间衰减成本',
            'pnl_after_theta = total_pnl_at_K - theta_cost_total : 扣除时间成本后的净盈亏',
            'close_vs_theoretical = close - bs_theoretical_price : 市价偏离 BS 理论价',
            'price_bias: 定价偏离判定 (严重低估/低估/公允/高估/严重高估)',
            'strategy_max_loss = -C : 最大亏损(权利金);  leverage_notional = S0 / C : 杠杆倍数',
            'annualized_return_pct = total_pnl_at_K / C / 剩余年限 × 100% : 年化收益率',
            '',
            '【多情景盈亏】(S_T = K × 系数, 系数 1.00/1.03/1.05/1.08/1.10/1.15/1.20)',
            'scenario_pnl_1_xxK = S_T + max(0, S_T - K) - S0 - C : 组合盈亏 (Spot + Long Call)',
            'scenario_pnl_1_xxK_cny = scenario_pnl × 乘数',
            'scenario_pnl_1_xxK_pct = scenario_pnl / (S0 + C) × 100% : 组合收益率',
            'pure_call_pnl_1_xxK = max(0, S_T - K) - C : 纯期权盈亏 (不买现货)',
            'pure_call_pnl_1_xxK_cny = pure_call_pnl × 乘数',
            'pure_call_pnl_1_xxK_pct = pure_call_pnl / C × 100% : 权利金收益率',
            '',
            '【着色规则】',
            '1) 条件格式色阶（绿→黄→红，从小到大）：open/high/low/settle/vol/amount/oi/pct_change/ '
            'turnover_ratio/d1/d2/nd1/nd2/moneyness_log/K_S_ratio/spot_to_strike/spot_to_strike_pct/ '
            'breakeven_S_T/breakeven_S_T_pct/pure_call_breakeven/pure_call_breakeven_pct/ '
            'delta_weighted_pnl/annualized_return_pct/strategy_max_loss/strategy_max_loss_cny/ '
            'strategy_max_loss_pct_of_spot/leverage_notional/theta_cost_daily/theta_cost_total/ '
            'theta_cost_pct_of_premium/pnl_after_theta/close_vs_theoretical/close_vs_theoretical_pct/ '
            'price_bias/implied_vol/bs_theoretical_price/delta/gamma/theta/vega/rho 等行',
            '2) 静态着色: cost_efficiency: 绿(≥1) / 黄(0.85~1) / 红(<0.85);  '
            'trade_signal: 绿=STRONG_BUY / 黄=BUY / 红=AVOID;  盈亏列: 绿=盈利 / 红=亏损',
        ]
        return '\n'.join(lines)

    # ================================================================
    # 主流程
    # ================================================================
    def run(self, trade_date, ts_code_filter=None, call_put=None):
        """主流程：拉取 → 构建字段 → 导出 Excel

        Args:
            trade_date: 交易日期 YYYYMMDD
            ts_code_filter: LIKE 过滤，如 'HO2612%'
            call_put: 'C'/'P'/None

        Returns:
            str or None: Excel 文件路径
        """
        logger.info("\n" + "=" * 80)
        logger.info(f"OptionTradingStrategyAnalyzerReport.run: "
                    f"trade_date={trade_date}, filter={ts_code_filter}, call_put={call_put}")
        logger.info("=" * 80)

        # Step 1: 拉取数据
        df = self.fetch_data(trade_date=trade_date,
                             ts_code_filter=ts_code_filter,
                             call_put=call_put)
        if len(df) == 0:
            logger.warning("No data found, skipping report generation")
            return None

        # Step 2: 构建字段顺序（去重，交易员视角）
        fields = self.build_field_order(df)
        logger.info(f"Field order: {fields}")

        # Step 3: 导出 Excel
        filepath = self.export_to_excel(df, trade_date=trade_date,
                                        ts_code_filter=ts_code_filter,
                                        call_put=call_put)

        logger.info(f"\n{'=' * 80}")
        logger.info(f"Report generated: {filepath}")
        logger.info(f"{'=' * 80}")
        return filepath


# ================================================================
# 独立运行入口
# ================================================================
if __name__ == "__main__":
    report_configs = [
        {
            "name": "HO2612看涨欧式期权",
            "trade_date": "20260717",
            "call_put": "C",
            "ts_code_filter": "HO2612%",
        },
        {
            "name": "HO2612看跌欧式期权",
            "trade_date": "20260717",
            "call_put": "P",
            "ts_code_filter": "HO2612%",
        },
    ]

    reporter = OptionTradingStrategyAnalyzerReport()

    for config in report_configs:
        name = config.get("name")
        logger.info(f"\n{'#' * 80}")
        logger.info(f"# Running config: {name}")
        logger.info(f"{'#' * 80}")
        try:
            filepath = reporter.run(
                trade_date=config.get("trade_date"),
                ts_code_filter=config.get("ts_code_filter"),
                call_put=config.get("call_put"),
            )
            if filepath:
                logger.info(f"✅ [{name}] Excel: {filepath}")
            else:
                logger.warning(f"⚠️ [{name}] No data, report skipped")
        except Exception as e:
            logger.error(f"❌ [{name}] Failed: {e}", exc_info=True)

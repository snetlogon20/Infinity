r"""
OptionSingleTradingStrategyAnalyzerReport — 期权策略分析报告生成器（读 ClickHouse 表 → 透视矩阵 Excel）

数据源：
    indexsysdb.tb_option_trading_strategy_indicator
    （由 OptionTradingSingleStrategyAnalyzer 写入，内容 = Excel 报表各 Sheet 写入列的并集）

报告形式：
    单一 Excel 文件，Sheet 内容为「指标 × 合约」透视矩阵：
        - 行 = 指标/字段（按交易员视角排序，重复字段去重）
        - 列 = 合约（按行权价 exercise_price 升序排列）
        - 在 cost_efficiency 行之后插入扩展指标块，再跟多情景盈亏等剩余字段

文件名：
    OptionSingleTradingStrategyAnalyzerReport_{trade_date}_{生成时间yyyymmdd_hhmmss}_{合约前缀}_{C/P}.xlsx
    示例: OptionSingleTradingStrategyAnalyzerReport_20260717_20260830_103000_HO2612_C.xlsx
    （加入生成时间戳，避免同一交易日重复生成时文件被 Excel 占用导致覆盖失败）

输出路径：
    CommonParameters.optionAnalysisReportPath
    (D:\workspace_python\infinity_data\outbound\report\OptionAnalysis\)

运行方式：
    python -m dataIntegrator.modelService.option.OptionTradingSingleStrategyAnalyzer.OptionSingleTradingStrategyAnalyzerReport
"""

import os
import io
import math
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

# reportlab PDF 报告生成
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Image as RLImage, Table, TableStyle, PageBreak)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.common.ReportJobLogger import ReportJobLogger
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.modelService.option.OptionTradingSingleStrategyAnalyzer.OptionSingleTradingStrategyAnalyzer import \
    OptionSingleTradingStrategyAnalyzer

logger = CommonLib.logger


class OptionSingleTradingStrategyAnalyzerReport:
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
        # --- 胜率与赔率（量化盈亏概率） ---
        'win_rate_pct', 'loss_rate_pct', 'prob_itm_pct',
        'avg_win_cny', 'avg_loss_cny', 'payoff_ratio', 'risk_reward_ratio',
        'profit_factor', 'expected_value_cny', 'edge_pct',
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
        # --- 胜率与赔率 ---
        'win_rate_pct', 'loss_rate_pct', 'prob_itm_pct',
        'avg_win_cny', 'avg_loss_cny', 'payoff_ratio', 'risk_reward_ratio',
        'profit_factor', 'expected_value_cny', 'edge_pct',
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
    # 说明 = 字段作用 + 核心算法（与 OptionTradingSingleStrategyAnalyzer 计算逻辑一致）
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
        # ---------- 胜率与赔率（量化盈亏概率） ----------
        'win_rate_pct': '到期盈利概率 = N(d2_BE)×100%：以盈亏平衡价 BE 代入 BS d2 公式所得 P(S_T>BE)',
        'loss_rate_pct': '到期亏损概率 = 100% - win_rate_pct',
        'prob_itm_pct': '到期行权概率 = P(S_T>K)×100%（Call）/ P(S_T<K)×100%（Put）：到期实值概率',
        'avg_win_cny': '平均盈利金额 = 盈利情景 scenario_pnl_1_xxK_cny 的均值（元/张）',
        'avg_loss_cny': '平均亏损金额 = |亏损情景均值|（元/张）',
        'payoff_ratio': '盈亏比（情景法）= avg_win_cny / avg_loss_cny：平均盈利/平均亏损',
        'risk_reward_ratio': '盈亏比（基准法）= total_pnl_at_K_cny / |strategy_max_loss_cny|：基准情景收益/最大风险',
        'profit_factor': '利润因子 = 盈利情景总和 / |亏损情景总和|：>1 表示系统期望为正',
        'expected_value_cny': '期望盈亏 = win_rate×avg_win_cny - loss_rate×avg_loss_cny（元/张）',
        'edge_pct': '边际收益率 = expected_value_cny / (close×乘数)×100%：期望收益占权利金投入比例',
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
        # 注册 reportlab 中文字体（PDF 报告用）
        self.reportlab_font = self._register_reportlab_font()
        logger.info(f"OptionSingleTradingStrategyAnalyzerReport initialized. "
                    f"Report dir: {self.REPORT_DIR}, "
                    f"{len(self.FIELD_DESCRIPTIONS)} field descriptions loaded")

    def _register_reportlab_font(self):
        """注册 reportlab 中文字体（参照 OptionDailyIndicatorReport）"""
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
    # Step 1.5: 现算胜率与赔率量化指标（报表层，幂等）
    # ================================================================
    @staticmethod
    def _norm_cdf(x):
        """标准正态累积分布函数（用 math.erf 实现，避免 scipy 依赖）"""
        if x is None:
            return None
        try:
            return 0.5 * (1.0 + math.erf(float(x) / math.sqrt(2.0)))
        except (TypeError, ValueError, OverflowError):
            return None

    def _enrich_win_loss_metrics(self, df):
        """在 DataFrame 上现算胜率与赔率量化指标（幂等，列已存在则跳过）

        胜率:
            - win_rate_pct : BE 口径 = N(d2_BE)×100%, d2_BE 以盈亏平衡价 BE 代入 BS d2 公式
            - prob_itm_pct : K 口径 = N(d2)×100%, 到期行权(实值)概率 P(S_T>K)
            - loss_rate_pct = 100% - win_rate_pct
        赔率:
            - payoff_ratio(情景法) = avg_win_cny / avg_loss_cny (7 档到期情景均值)
            - risk_reward_ratio(基准法) = total_pnl_at_K_cny / |strategy_max_loss_cny|
        期望:
            - expected_value_cny = win_rate×avg_win_cny - loss_rate×avg_loss_cny
            - edge_pct = expected_value_cny / (close×乘数)×100%

        Returns:
            pd.DataFrame: 追加新列后的副本（无数据或已含新列时原样返回）
        """
        if len(df) == 0 or 'win_rate_pct' in df.columns:
            return df
        df = df.copy()

        def _safe(row, field, default=None):
            if field not in row.index:
                return default
            val = row[field]
            if val is None:
                return default
            try:
                fv = float(val)
            except (TypeError, ValueError):
                return default
            return fv if not (pd.isna(fv) or np.isinf(fv)) else default

        # 7 档到期情景 S_T = K×系数, 字段形如 scenario_pnl_1_03K_cny
        labels = [f'{f:.2f}'.replace('.', '_') for f in self.SCENARIO_FACTORS]

        # IV 缺失兜底: 同一序列(已按行权价升序)线性插值, 仅用于概率计算, 不落库
        iv_map = {}
        if 'implied_vol' in df.columns:
            iv_series = pd.to_numeric(df['implied_vol'], errors='coerce')
            if iv_series.notna().sum() >= 2 and iv_series.isna().any():
                iv_series = iv_series.interpolate(method='linear', limit_direction='both')
            iv_map = dict(zip(df.index, iv_series))

        for idx, row in df.iterrows():
            S0 = _safe(row, 'spot_price')
            K = _safe(row, 'exercise_price')
            C = _safe(row, 'close')
            sigma = iv_map.get(idx, _safe(row, 'implied_vol'))
            T = _safe(row, 'years_to_maturity_calendar')
            r = _safe(row, 'risk_free_rate', 0.0) or 0.0
            q = _safe(row, 'dividend_yield', 0.0) or 0.0
            multiplier = _safe(row, 'opt_multiplier')
            BE = _safe(row, 'breakeven_S_T')
            cp = str(row.get('call_put', '')).upper()
            ce = _safe(row, 'cost_efficiency')

            # ---- 胜率（BE 口径） ----
            # "现货+期权"组合盈亏随 S_T 单调不减，盈亏平衡点 BE 处 P(S_T>BE) 即盈利概率
            # 特例: 现货+Put 且 K-S0>C (cost_efficiency>1) 时任意到期价格均盈利
            def _d2(X):
                if not (S0 and sigma and T and X and sigma > 0 and T > 0 and X > 0):
                    return None
                return (math.log(S0 / X) + (r - q - 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))

            if cp == 'P' and ce is not None and ce > 1.0:
                win_rate = 100.0
            elif BE:
                d2BE = _d2(BE)
                win_rate = (self._norm_cdf(d2BE) * 100.0) if d2BE is not None else None
            else:
                win_rate = None

            # ---- 行权概率（K 口径） ----
            # Call 到期行权 = P(S_T>K)=N(d2)；Put 到期行权 = P(S_T<K)=1-N(d2)
            d2K = _d2(K) if K else None
            if cp == 'P' and d2K is not None:
                nd2cdf = self._norm_cdf(d2K)
                prob_itm = (1.0 - nd2cdf) * 100.0 if nd2cdf is not None else None
            else:
                prob_itm = (self._norm_cdf(d2K) * 100.0) if d2K is not None else None
            if prob_itm is None:
                nd2 = _safe(row, 'nd2')
                if nd2 is not None:
                    prob_itm = (1.0 - nd2) * 100.0 if cp == 'P' else nd2 * 100.0
            # 兜底: BE 口径因数据缺失无法计算时，退化为 K 口径（同为到期概率），保证报表不空缺
            if win_rate is None and prob_itm is not None:
                win_rate = prob_itm

            # ---- 情景法：平均盈利/亏损 与 盈亏比 ----
            scen_vals = [_safe(row, f'scenario_pnl_{lab}K_cny') for lab in labels]
            scen_vals = [v for v in scen_vals if v is not None]
            wins = [v for v in scen_vals if v > 0]
            losses = [v for v in scen_vals if v < 0]
            avg_win = sum(wins) / len(wins) if wins else None
            avg_loss = abs(sum(losses) / len(losses)) if losses else None
            payoff_ratio = (avg_win / avg_loss) if (avg_win is not None and avg_loss and avg_loss > 0) else None
            profit_factor = ((sum(wins) / abs(sum(losses))) if (wins and losses and abs(sum(losses)) > 0) else None)

            # ---- 基准法：基准情景收益 / 最大风险 ----
            pnl_at_K = _safe(row, 'total_pnl_at_K_cny')
            max_loss = _safe(row, 'strategy_max_loss_cny')
            risk_reward = (pnl_at_K / abs(max_loss)) if (pnl_at_K is not None and max_loss is not None and max_loss < 0) else None

            # ---- 期望盈亏 & 边际收益率 ----
            ev = None
            if win_rate is not None and avg_win is not None and avg_loss is not None:
                w = win_rate / 100.0
                ev = w * avg_win - (1.0 - w) * avg_loss
            edge_pct = None
            if ev is not None and C and multiplier and C * multiplier > 0:
                edge_pct = ev / (C * multiplier) * 100.0

            df.at[idx, 'win_rate_pct'] = win_rate
            df.at[idx, 'loss_rate_pct'] = (100.0 - win_rate) if win_rate is not None else None
            df.at[idx, 'prob_itm_pct'] = prob_itm
            df.at[idx, 'avg_win_cny'] = avg_win
            df.at[idx, 'avg_loss_cny'] = avg_loss
            df.at[idx, 'payoff_ratio'] = payoff_ratio
            df.at[idx, 'risk_reward_ratio'] = risk_reward
            df.at[idx, 'profit_factor'] = profit_factor
            df.at[idx, 'expected_value_cny'] = ev
            df.at[idx, 'edge_pct'] = edge_pct

        logger.info("Win/Loss metrics enriched: "
                    f"win_rate_pct/prob_itm_pct/payoff_ratio/risk_reward_ratio/expected_value_cny added")
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
        target_columns = OptionSingleTradingStrategyAnalyzer.TARGET_COLUMNS
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

    def export_to_excel(self, df, trade_date, ts_code_filter=None, call_put=None,
                        gen_ts=None):
        """导出「指标 × 合约」透视矩阵 Excel，并附加图表 Sheet

        行 = 字段，列 = 合约（按行权价升序），最右增加说明列。
        对指定字段行按数值从小到大应用绿→黄→红色阶。
        新增 Sheet「到期盈亏曲线」嵌入两张图表。

        Args:
            df: fetch_data 返回的当日数据
            trade_date: 交易日期 YYYYMMDD（用于文件名与标题）
            ts_code_filter: LIKE 过滤，用于文件名前缀
            call_put: 'C'/'P'，用于文件名
            gen_ts: 生成时间戳 yyyymmdd_hhmmss（由 run 统一生成，
                    保证 Excel 与 PDF 文件名一致；None 时内部生成）

        Returns:
            str or None: Excel 文件路径
        """
        if len(df) == 0:
            logger.warning("Empty DataFrame, nothing to export")
            return None

        # 按行权价升序排列合约
        df_sorted = df.sort_values('exercise_price', ascending=True).reset_index(drop=True)
        # 现算胜率与赔率量化指标（幂等，底层表未含时补充）
        df_sorted = self._enrich_win_loss_metrics(df_sorted)
        n_contracts = len(df_sorted)
        data_end_col = 1 + n_contracts        # A列指标 + 合约列
        desc_col = data_end_col + 1           # 说明列（K列在9合约时）
        total_cols = desc_col                 # 总列数

        # 字段行列表
        fields = self.build_field_order(df_sorted)

        # 文件名: OptionSingleTradingStrategyAnalyzerReport_{date}_{生成时间yyyymmdd_hhmmss}_{prefix}_{call_put}.xlsx
        # 加入生成时间戳，避免同一交易日重复生成时文件被 Excel 占用导致覆盖失败
        prefix = self._extract_prefix(ts_code_filter)
        call_put_str = call_put or 'ALL'
        if gen_ts is None:
            gen_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = (f'OptionSingleTradingStrategyAnalyzerReport_{trade_date}_{gen_ts}'
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
                     'strategy_max_loss_pct_of_spot',
                     'win_rate_pct', 'loss_rate_pct', 'prob_itm_pct', 'edge_pct'):
            return '0.00"%"'
        if field in ('payoff_ratio', 'risk_reward_ratio', 'profit_factor'):
            return '0.00'
        if field in ('avg_win_cny', 'avg_loss_cny', 'expected_value_cny'):
            return '#,##0'
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
            '本报表读取 indexsysdb.tb_option_trading_strategy_indicator（由 OptionTradingSingleStrategyAnalyzer 写入），',
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
            '【胜率与赔率】(量化盈亏概率, 基于 BS 模型与多情景盈亏)',
            'win_rate_pct = N(d2_BE)×100% : d2_BE=[ln(S0/BE)+(r-q-σ²/2)T]/(σ√T), 即 P(S_T>BE) 到期盈利概率',
            'loss_rate_pct = 100% - win_rate_pct : 到期亏损概率',
            'prob_itm_pct = 到期行权概率 : Call 为 P(S_T>K)=N(d2), Put 为 P(S_T<K)=1-N(d2)',
            'avg_win_cny / avg_loss_cny = 盈利/亏损情景 scenario_pnl_1_xxK_cny 的均值(元/张)',
            'payoff_ratio(情景法) = avg_win_cny / avg_loss_cny : 平均盈利/平均亏损(盈亏比)',
            'risk_reward_ratio(基准法) = total_pnl_at_K_cny / |strategy_max_loss_cny| : 基准情景收益/最大风险',
            'profit_factor = 盈利情景总和 / |亏损情景总和| : >1 表示期望为正',
            'expected_value_cny = win_rate×avg_win_cny - loss_rate×avg_loss_cny : 概率加权期望盈亏',
            'edge_pct = expected_value_cny / (close×乘数) ×100% : 期望收益占权利金投入比例',
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
            'price_bias/implied_vol/bs_theoretical_price/delta/gamma/theta/vega/rho/ '
            'win_rate_pct/loss_rate_pct/prob_itm_pct/avg_win_cny/avg_loss_cny/payoff_ratio/ '
            'risk_reward_ratio/profit_factor/expected_value_cny/edge_pct 等行',
            '2) 静态着色: cost_efficiency: 绿(≥1) / 黄(0.85~1) / 红(<0.85);  '
            'trade_signal: 绿=STRONG_BUY / 黄=BUY / 红=AVOID;  盈亏列: 绿=盈利 / 红=亏损',
        ]
        return '\n'.join(lines)

    # ================================================================
    # PDF 报告生成（专业交易员视角）
    # ================================================================
    def _build_pdf_styles(self):
        """构建 PDF 样式（中文字体）"""
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'ReportTitle', parent=styles['Heading1'],
            fontSize=22, leading=30, alignment=1,
            fontName=self.reportlab_font, spaceAfter=24,
        )
        heading1 = ParagraphStyle(
            'Heading1Style', parent=styles['Heading1'],
            fontSize=16, leading=22, fontName=self.reportlab_font,
            spaceAfter=12, spaceBefore=12,
        )
        heading2 = ParagraphStyle(
            'Heading2Style', parent=styles['Heading2'],
            fontSize=13, leading=18, fontName=self.reportlab_font,
            spaceAfter=8, spaceBefore=8,
        )
        normal = ParagraphStyle(
            'NormalStyle', parent=styles['Normal'],
            fontSize=10, leading=15, fontName=self.reportlab_font,
        )
        small = ParagraphStyle(
            'SmallStyle', parent=styles['Normal'],
            fontSize=8.5, leading=12, fontName=self.reportlab_font,
            textColor=colors.HexColor('#555555'),
        )
        cover_info = ParagraphStyle(
            'CoverInfo', parent=styles['Normal'],
            fontSize=13, leading=20, alignment=1,
            fontName=self.reportlab_font, textColor=colors.HexColor('#333333'),
        )
        return {
            'title': title_style,
            'h1': heading1,
            'h2': heading2,
            'normal': normal,
            'small': small,
            'cover_info': cover_info,
        }

    @staticmethod
    def _safe_num(row, field, default=None):
        """安全取数值，NaN/inf/None 返回 default（兼容 Series 与 namedtuple）"""
        if hasattr(row, 'get'):
            val = row.get(field)
        else:
            val = getattr(row, field, None)
        if val is None:
            return default
        try:
            fv = float(val)
        except (TypeError, ValueError):
            return default
        if pd.isna(fv) or np.isinf(fv):
            return default
        return fv

    @staticmethod
    def _fmt(val, nd=2, suffix=''):
        if val is None:
            return 'N/A'
        try:
            return f"{val:.{nd}f}{suffix}"
        except (TypeError, ValueError):
            return 'N/A'

    @staticmethod
    def _fmt_pct(val, nd=2):
        if val is None:
            return 'N/A'
        try:
            return f"{val*100:.{nd}f}%"
        except (TypeError, ValueError):
            return 'N/A'

    def _build_pdf_key_table(self, df_sorted):
        """构建关键指标矩阵表（行=合约，列=核心指标）"""
        headers = ['行权价', '权利金Close', '价态', '成本效率', '盈亏平衡涨幅',
                   '年化收益率', '胜率', '行权概率', '盈亏比', '期望盈亏',
                   'IV', 'Delta', 'Theta占比', '杠杆', '定价', '信号']
        rows = [headers]
        for _, row in df_sorted.iterrows():
            K = self._safe_num(row, 'exercise_price')
            close = self._safe_num(row, 'close')
            rows.append([
                self._fmt(K, 0),
                self._fmt(close, 2),
                str(getattr(row, 'moneyness_status', None) or 'N/A'),
                self._fmt(self._safe_num(row, 'cost_efficiency'), 2),
                self._fmt_pct(self._safe_num(row, 'breakeven_S_T_pct')),
                self._fmt_pct(self._safe_num(row, 'annualized_return_pct')),
                # 胜率与赔率（win_rate_pct 等已为 ×100 的百分比数值）
                self._fmt(self._safe_num(row, 'win_rate_pct'), 2, '%'),
                self._fmt(self._safe_num(row, 'prob_itm_pct'), 2, '%'),
                self._fmt(self._safe_num(row, 'payoff_ratio'), 2),
                self._fmt(self._safe_num(row, 'expected_value_cny'), 0),
                self._fmt_pct(self._safe_num(row, 'implied_vol')),
                self._fmt(self._safe_num(row, 'delta'), 2),
                self._fmt_pct(self._safe_num(row, 'theta_cost_pct_of_premium')),
                self._fmt(self._safe_num(row, 'leverage_notional'), 1),
                str(getattr(row, 'price_bias', None) or 'N/A'),
                str(getattr(row, 'trade_signal', None) or 'N/A'),
            ])
        return rows

    def _build_pdf_analysis(self, df_sorted, trade_date, call_put_str):
        """从专业交易员视角生成分析段落

        Returns:
            list[tuple(heading, [Paragraph文本])]
        """
        S0 = self._safe_num(df_sorted.iloc[0], 'spot_price')
        n = len(df_sorted)
        ks = [self._safe_num(r, 'exercise_price') for r in df_sorted.itertuples()]
        valid_ks = [k for k in ks if k is not None]
        k_min, k_max = (min(valid_ks), max(valid_ks)) if valid_ks else (None, None)
        dte = self._safe_num(df_sorted.iloc[0], 'days_to_maturity')

        def stat(field, fn, default=None):
            vals = [self._safe_num(r, field) for r in df_sorted.itertuples()]
            vals = [v for v in vals if v is not None]
            if not vals:
                return default
            try:
                return fn(vals)
            except (TypeError, ValueError):
                return default

        avg_close = stat('close', lambda vs: sum(vs)/len(vs))
        med_close = stat('close', lambda vs: sorted(vs)[len(vs)//2])
        min_close = stat('close', min)
        max_close = stat('close', max)
        avg_lev = stat('leverage_notional', lambda vs: sum(vs)/len(vs))
        max_lev = stat('leverage_notional', max)
        avg_iv = stat('implied_vol', lambda vs: sum(vs)/len(vs))
        min_iv = stat('implied_vol', min)
        max_iv = stat('implied_vol', max)

        # 价态分布
        moneyness_counts = {}
        for r in df_sorted.itertuples():
            m = str(r.moneyness_status) if getattr(r, 'moneyness_status', None) else '未知'
            moneyness_counts[m] = moneyness_counts.get(m, 0) + 1
        mn_desc = '、'.join(f'{k} {v}个' for k, v in moneyness_counts.items()) or 'N/A'

        # 成本效率 Top3
        ce_rows = [(self._safe_num(r, 'cost_efficiency'), int(self._safe_num(r, 'exercise_price') or 0))
                   for r in df_sorted.itertuples() if self._safe_num(r, 'cost_efficiency') is not None]
        ce_top = sorted(ce_rows, key=lambda x: x[0], reverse=True)[:3]
        ce_top_txt = '；'.join(f'K={k} (效率 {self._fmt(v, 2)})' for v, k in ce_top) or 'N/A'
        ce_ge1 = sum(1 for v, _ in ce_rows if v >= 1.0)

        # 盈亏平衡最低（纯Call口径）
        be_rows = [(self._safe_num(r, 'pure_call_breakeven_pct'), int(self._safe_num(r, 'exercise_price') or 0))
                   for r in df_sorted.itertuples() if self._safe_num(r, 'pure_call_breakeven_pct') is not None]
        be_top = sorted(be_rows, key=lambda x: x[0])[:3]
        be_top_txt = '；'.join(f'K={k} (需涨 {self._fmt_pct(v)})' for v, k in be_top) or 'N/A'

        # 年化收益率 Top3
        ar_rows = [(self._safe_num(r, 'annualized_return_pct'), int(self._safe_num(r, 'exercise_price') or 0))
                   for r in df_sorted.itertuples() if self._safe_num(r, 'annualized_return_pct') is not None]
        ar_top = sorted(ar_rows, key=lambda x: x[0], reverse=True)[:3]
        ar_top_txt = '；'.join(f'K={k} (年化 {self._fmt_pct(v)})' for v, k in ar_top) or 'N/A'

        # 概率加权期望 Top3
        dw_rows = [(self._safe_num(r, 'delta_weighted_pnl'), int(self._safe_num(r, 'exercise_price') or 0))
                   for r in df_sorted.itertuples() if self._safe_num(r, 'delta_weighted_pnl') is not None]
        dw_top = sorted(dw_rows, key=lambda x: x[0], reverse=True)[:3]
        dw_top_txt = '；'.join(f'K={k} (期望 {self._fmt(v, 2)})' for v, k in dw_top) or 'N/A'

        # 定价偏差分布
        bias_counts = {}
        for r in df_sorted.itertuples():
            b = str(r.price_bias) if getattr(r, 'price_bias', None) else 'N/A'
            bias_counts[b] = bias_counts.get(b, 0) + 1
        bias_desc = '、'.join(f'{k} {v}个' for k, v in bias_counts.items()) or 'N/A'

        # 最被低估 / 最高估
        bias_rows = [(self._safe_num(r, 'close_vs_theoretical_pct'), int(self._safe_num(r, 'exercise_price') or 0))
                     for r in df_sorted.itertuples() if self._safe_num(r, 'close_vs_theoretical_pct') is not None]
        if bias_rows:
            most_und = min(bias_rows, key=lambda x: x[0])
            most_ov = max(bias_rows, key=lambda x: x[0])
            most_und_txt = f'K={most_und[1]} (偏离 {self._fmt_pct(most_und[0])})'
            most_ov_txt = f'K={most_ov[1]} (偏离 {self._fmt_pct(most_ov[0])})'
        else:
            most_und_txt = most_ov_txt = 'N/A'

        # 时间衰减最高 / 杠杆最高
        theta_rows = [(self._safe_num(r, 'theta_cost_pct_of_premium'), int(self._safe_num(r, 'exercise_price') or 0))
                      for r in df_sorted.itertuples() if self._safe_num(r, 'theta_cost_pct_of_premium') is not None]
        theta_top = max(theta_rows, key=lambda x: x[0]) if theta_rows else (None, None)
        theta_top_txt = f'K={theta_top[1]} (衰减占权利金 {self._fmt_pct(theta_top[0])})' if theta_top[0] is not None else 'N/A'

        # 信号统计
        sig_counts = {}
        for r in df_sorted.itertuples():
            s = str(r.trade_signal) if getattr(r, 'trade_signal', None) else 'N/A'
            sig_counts[s] = sig_counts.get(s, 0) + 1
        buy_list = [int(self._safe_num(r, 'exercise_price') or 0) for r in df_sorted.itertuples()
                    if str(getattr(r, 'trade_signal', '')) in ('STRONG_BUY', 'BUY')]
        avoid_list = [int(self._safe_num(r, 'exercise_price') or 0) for r in df_sorted.itertuples()
                      if str(getattr(r, 'trade_signal', '')) == 'AVOID']

        cp_cn = {'C': '看涨(Call)', 'P': '看跌(Put)'}.get(call_put_str, call_put_str)
        secs = []

        # ===== 一、市场概览 =====
        secs.append(('一、市场概览与交易环境', [
            f"标的现货 {self._fmt(S0, 2)}，共 {n} 个{cp_cn}合约，行权价区间 {self._fmt(k_min, 0)} ~ {self._fmt(k_max, 0)}，"
            f"距到期约 {self._fmt(dte, 0)} 天。",
            f"权利金成本：均值 {self._fmt(avg_close, 2)}、中位数 {self._fmt(med_close, 2)}、"
            f"区间 {self._fmt(min_close, 2)} ~ {self._fmt(max_close, 2)}。价态分布：{mn_desc}。",
            f"杠杆水平：平均 {self._fmt(avg_lev, 1)} 倍，最高 {self._fmt(max_lev, 1)} 倍。"
            f"杠杆越高，权利金对标的涨跌的敏感度越大，盈亏波动也越大。",
        ]))

        # ===== 二、成本效率 =====
        secs.append(('二、成本效率（性价比）分析', [
            f"成本效率 = (K-S0)/C，衡量到期 S_T=K 时现货涨幅能否覆盖权利金。"
            f"当前 {ce_ge1}/{n} 个合约效率 ≥ 1，即标的只需涨到行权价即可回本。",
            f"最优效率合约：{ce_top_txt}。",
            "交易提示：成本效率是中性情景（标的不涨不跌到行权价）下的回本能力，"
            "效率越高代表权利金越'便宜'、容错空间越大；但需结合到期时间与波动率综合判断。",
        ]))

        # ===== 三、盈亏平衡与收益 =====
        secs.append(('三、盈亏平衡与收益潜力', [
            f"纯Call口径盈亏平衡（需涨幅度）最低：{be_top_txt}。"
            f"这些合约只需要标的较小幅上涨即可覆盖权利金成本，适合温和看多的交易者。",
            f"到期 S_T=K 情景下年化收益率最高：{ar_top_txt}。年化收益率已按剩余期限折算，"
            f"可用于不同期限合约间的横向比较，但高年化往往伴随高波动与高衰减。",
            f"按 Delta 概率加权的期望盈亏（delta_weighted_pnl）最高：{dw_top_txt}。"
            "该指标融合了'涨到行权价的概率'，比单纯看盈亏更有决策参考意义。",
        ]))

        # ===== 四、波动率与定价 =====
        secs.append(('四、波动率环境与定价偏差', [
            f"隐含波动率 IV：均值 {self._fmt_pct(avg_iv)}，区间 {self._fmt_pct(min_iv)} ~ {self._fmt_pct(max_iv)}。"
            f"{'IV 处于偏低水平，权利金整体偏“便宜”，买方有利。' if (avg_iv is not None and avg_iv < 0.2) else 'IV 处于中性偏高水平，需注意买方支付的时间与波动溢价。'}",
            f"定价偏差分布：{bias_desc}。最被低估合约：{most_und_txt}；最高估合约：{most_ov_txt}。",
            "交易提示：市价低于 BS 理论价的合约（负偏离）存在相对价值机会，可优先关注；"
            "明显高估的合约应避免追买，或考虑作为卖方获取溢价。",
        ]))

        # ===== 五、风险与时间衰减 =====
        secs.append(('五、风险控制与时间衰减', [
            f"持有到期时间衰减最重的合约：{theta_top_txt}。时间价值随到期临近加速损耗，"
            "权利金越贵、剩余期限越短，Theta 侵蚀越明显。",
            f"最大风险敞口：全部权利金（最多亏损 close × 乘数）。"
            f"组合最大亏损占现货比例平均约 {self._fmt_pct(stat('strategy_max_loss_pct_of_spot', lambda vs: sum(vs)/len(vs)))}。",
            "风控建议：控制单一合约权利金占总资金比例；虚值合约虽杠杆高但行权概率低（N(d2) 小），"
            "深度虚值仓位应严设止损；临近到期避免重仓高 Theta 合约。",
        ]))

        # ===== 六、交易信号 =====
        sig_desc = '、'.join(f'{k} {v}个' for k, v in sig_counts.items()) or 'N/A'
        buy_txt = '、'.join(f'K={k}' for k in buy_list) or '无'
        avoid_txt = '、'.join(f'K={k}' for k in avoid_list) or '无'
        secs.append(('六、交易信号汇总与操作建议', [
            f"信号分布：{sig_desc}。",
            f"买入/强烈买入（STRONG_BUY/BUY）：{buy_txt}。"
            f"回避（AVOID）：{avoid_txt}。",
            "综合建议：优先在成本效率高、定价低估、Delta 概率加权期望为正的合约中选择；"
            "若看好标的上涨，可结合纯Call盈亏平衡涨幅小的合约控制回本门槛；"
            "若认为波动率将上升，可增配 Vega 敞口（平值附近合约）。",
        ]))

        # ===== 七、胜率与赔率（量化盈亏概率） =====
        def _wl_stat(field, fn):
            vals = [self._safe_num(r, field) for r in df_sorted.itertuples()]
            vals = [v for v in vals if v is not None]
            return fn(vals) if vals else None

        def _pairs(field):
            return [(self._safe_num(r, field), self._safe_num(r, 'exercise_price'))
                    for r in df_sorted.itertuples()
                    if self._safe_num(r, field) is not None]

        def _top3(pairs, nd=2):
            if not pairs:
                return 'N/A'
            tops = sorted(pairs, key=lambda x: x[0], reverse=True)[:3]
            return '、'.join(f'K={int(p[1])} ({self._fmt(p[0], nd)})' for p in tops)

        wr_pairs = _pairs('win_rate_pct')
        itm_pairs = _pairs('prob_itm_pct')
        pr_pairs = _pairs('payoff_ratio')
        ev_pairs = _pairs('expected_value_cny')
        avg_wr = _wl_stat('win_rate_pct', lambda vs: sum(vs) / len(vs))
        avg_itm = _wl_stat('prob_itm_pct', lambda vs: sum(vs) / len(vs))
        n_pos_ev = sum(1 for v, _ in ev_pairs if v > 0)
        n_neg_ev = sum(1 for v, _ in ev_pairs if v < 0)
        n_pr_gt1 = sum(1 for v, _ in pr_pairs if v > 1.0)
        if call_put_str == 'C':
            itm_trend = '离行权价越远的合约行权概率越低（虚值程度上升）'
        elif call_put_str == 'P':
            itm_trend = '离行权价越远的合约行权概率越高（实值程度上升）'
        else:
            itm_trend = '行权概率随行权价偏移而分布变化'
        secs.append(('七、胜率与赔率（量化盈亏概率）', [
            f"到期盈利概率（BE口径，P(S_T&gt;盈亏平衡价)）：平均 {self._fmt(avg_wr, 2)}%，"
            f"最高 {_top3(wr_pairs)}。到期行权概率（K口径，Call 为 P(S_T&gt;K)、Put 为 P(S_T&lt;K)）："
            f"平均 {self._fmt(avg_itm, 2)}%，{itm_trend}。",
            f"盈亏比（情景法=平均盈利/平均亏损）：{n_pr_gt1}/{len(pr_pairs)} 个合约盈亏比&gt;1，"
            f"最高 {_top3(pr_pairs)}。盈亏比高意味着亏损情景均值小、盈利情景均值大。",
            f"概率加权期望盈亏（元/张）：正期望 {n_pos_ev} 个、负期望 {n_neg_ev} 个；"
            f"期望最高 {_top3(ev_pairs)}。",
            "交易提示：胜率与赔率通常此消彼长——低行权价合约胜率高但盈亏比低，虚值合约胜率低但盈亏比高；"
            "应综合胜率×盈亏比判断期望值（EV），正 EV 且风险可控才是优质标的，"
            "避免陷入高胜率低赔率或高赔率低胜率的单边陷阱。",
        ]))
        return secs

    def export_to_pdf(self, df, trade_date, ts_code_filter=None, call_put=None,
                      gen_ts=None):
        """生成专业交易员视角 PDF 报告（含图表与文字分析）

        PDF 文件名与 Excel 完全一致，仅后缀不同。

        Returns:
            str or None: PDF 文件路径
        """
        if len(df) == 0:
            logger.warning("Empty DataFrame, nothing to export to PDF")
            return None

        df_sorted = df.sort_values('exercise_price', ascending=True).reset_index(drop=True)
        # 现算胜率与赔率量化指标（幂等，底层表未含时补充）
        df_sorted = self._enrich_win_loss_metrics(df_sorted)
        prefix = self._extract_prefix(ts_code_filter)
        call_put_str = call_put or 'ALL'
        if gen_ts is None:
            gen_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = (f'OptionSingleTradingStrategyAnalyzerReport_{trade_date}_{gen_ts}'
                    f'_{prefix}_{call_put_str}.pdf')
        pdf_path = os.path.join(self.REPORT_DIR, filename)

        styles = self._build_pdf_styles()
        report_date = datetime.now().strftime('%Y-%m-%d %H:%M')
        spot_price = self._safe_num(df_sorted.iloc[0], 'spot_price')

        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=landscape(A4),
            rightMargin=50, leftMargin=50,
            topMargin=40, bottomMargin=30,
        )
        page_width = landscape(A4)[0] - 100
        story = []

        # ===== 封面 =====
        cp_cn = {'C': '看涨 (Call)', 'P': '看跌 (Put)', 'ALL': '全部'}
        story.append(Spacer(1, 1.5 * inch))
        story.append(Paragraph(f'期权策略指标分析报告', styles['title']))
        story.append(Spacer(1, 0.25 * inch))
        story.append(Paragraph(
            'Option Trading Strategy Analysis Report',
            ParagraphStyle('Sub', parent=styles['normal'], alignment=1,
                           fontSize=11, textColor=colors.HexColor('#888888'),
                           fontName=self.reportlab_font),
        ))
        story.append(Spacer(1, 0.35 * inch))
        story.append(Paragraph(
            f"交易日：{trade_date} | {cp_cn.get(call_put_str, call_put_str)}<br/>"
            f"标的现货：{self._fmt(spot_price, 2)} | 合约数量：{len(df_sorted)} 个<br/>"
            f"生成时间：{report_date}<br/>"
            f"<br/>策略：买入现货 + 买入 Call（Spot + Long Call）<br/>"
            f"INFINITY 量化系统 · 期权研究专用",
            styles['cover_info'],
        ))
        story.append(PageBreak())

        # ===== 一、市场概览（文字） =====
        story.append(Paragraph('第一部分 · 交易员分析', styles['h1']))
        for heading, paras in self._build_pdf_analysis(df_sorted, trade_date, call_put_str):
            story.append(Paragraph(heading, styles['h2']))
            story.append(Spacer(1, 0.05 * inch))
            for p in paras:
                story.append(Paragraph(p, styles['normal']))
                story.append(Spacer(1, 0.06 * inch))
        story.append(PageBreak())

        # ===== 二、关键指标矩阵表 =====
        story.append(Paragraph('第二部分 · 关键指标矩阵', styles['h1']))
        story.append(Spacer(1, 0.1 * inch))
        rows = self._build_pdf_key_table(df_sorted)
        col_widths = [page_width / len(rows[0])] * len(rows[0])
        table = Table(rows, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.reportlab_font),
            ('FONTSIZE', (0, 0), (-1, -1), 5.5),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#AAAAAA')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#EEF3FA')]),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph(
            '注：成本效率=(K-S0)/C；盈亏平衡涨幅为纯Call口径 (K+C)/S0-1；'
            '年化收益率按剩余期限折算；Theta占比=持有到期总衰减/权利金；杠杆=现货/权利金；'
            '胜率=到期盈利概率 N(d2_BE)；行权概率=到期行权概率 N(d2)；'
            '盈亏比=平均盈利/平均亏损(情景法)；期望盈亏=胜率×平均盈利-亏损率×平均亏损。',
            styles['small'],
        ))
        story.append(PageBreak())

        # ===== 三、图表 =====
        story.append(Paragraph('第三部分 · 到期盈亏与收益率曲线', styles['h1']))
        story.append(Spacer(1, 0.1 * inch))
        chart_buf = self._plot_payoff_curves(df_sorted, trade_date, call_put_str)
        if chart_buf:
            img = RLImage(chart_buf, width=page_width, height=page_width * 0.45)
            story.append(img)
        story.append(Spacer(1, 0.15 * inch))
        story.append(Paragraph(
            '左图为各合约（纯 Call 买方）到期盈亏曲线：横轴为到期标的价格 S_T，纵轴为盈亏金额（元/张，×乘数），'
            '红色虚线为当前现货价。右图为到期收益率曲线（盈亏/权利金），直观展示各合约在不同到期价位的收益率与杠杆效应：'
            '平值附近合约收益曲线平滑、容错高；虚值合约盈亏比高但需标的大幅波动才获利。',
            styles['normal'],
        ))
        story.append(PageBreak())

        # ===== 四、风险提示 =====
        story.append(Paragraph('第四部分 · 风险提示', styles['h1']))
        story.append(Spacer(1, 0.15 * inch))
        story.append(Paragraph(
            "本报告基于历史期权数据进行量化分析，仅供参考，不构成投资建议。<br/>"
            "期权为高杠杆衍生品，最大亏损为全部权利金，但部分策略（含现货）可能放大亏损敞口。<br/>"
            "隐含波动率为 BS 模型反向求解，深度实值期权市价低于理论下界时 IV 可能缺失。<br/>"
            "Greeks 为 BS 框架下的理论值，实际交易受流动性、波动率微笑、跳空等因素影响可能存在偏差。<br/>"
            "建议投资者结合自身风险承受能力，进行独立判断和决策。",
            styles['normal'],
        ))

        doc.build(story)
        logger.info(f"PDF report saved: {pdf_path}")
        return pdf_path

    # ================================================================
    # 主流程
    # ================================================================
    def run(self, trade_date, ts_code_filter=None, call_put=None, gen_pdf=True):
        """主流程：拉取 → 构建字段 → 导出 Excel + PDF

        Args:
            trade_date: 交易日期 YYYYMMDD
            ts_code_filter: LIKE 过滤，如 'HO2612%'
            call_put: 'C'/'P'/None
            gen_pdf: 是否同时生成 PDF 报告（默认 True）

        Returns:
            dict: {'excel': 路径 or None, 'pdf': 路径 or None}
        """
        logger.info("\n" + "=" * 80)
        logger.info(f"OptionSingleTradingStrategyAnalyzerReport.run: "
                    f"trade_date={trade_date}, filter={ts_code_filter}, call_put={call_put}")
        logger.info("=" * 80)

        # 报表任务日志（与 BondYieldComparator 相同的 ReportJobLogger 机制）
        job_logger = ReportJobLogger()
        job_logger.start_job(self.__class__.__name__, 'OptionStrategyReport',
                             params={'trade_date': trade_date,
                                     'ts_code_filter': ts_code_filter,
                                     'call_put': call_put,
                                     'gen_pdf': gen_pdf})

        try:
            # Step 1: 拉取数据
            df = self.fetch_data(trade_date=trade_date,
                                 ts_code_filter=ts_code_filter,
                                 call_put=call_put)
            if len(df) == 0:
                logger.warning("No data found, skipping report generation")
                job_logger.end_job_success(records_processed=0)
                return {'excel': None, 'pdf': None}

            # Step 2: 构建字段顺序（去重，交易员视角）
            fields = self.build_field_order(df)
            logger.info(f"Field order: {fields}")

            # Step 3: 统一生成时间戳，保证 Excel/PDF 文件名一致
            gen_ts = datetime.now().strftime('%Y%m%d_%H%M%S')

            # Step 4: 导出 Excel
            excel_path = self.export_to_excel(df, trade_date=trade_date,
                                              ts_code_filter=ts_code_filter,
                                              call_put=call_put, gen_ts=gen_ts)

            # Step 5: 导出 PDF（与 Excel 同名，仅后缀不同）
            pdf_path = None
            if gen_pdf:
                try:
                    pdf_path = self.export_to_pdf(df, trade_date=trade_date,
                                                  ts_code_filter=ts_code_filter,
                                                  call_put=call_put, gen_ts=gen_ts)
                except Exception as e:
                    logger.error(f"PDF generation failed: {e}", exc_info=True)

            logger.info(f"\n{'=' * 80}")
            logger.info(f"Excel report: {excel_path}")
            logger.info(f"PDF report:   {pdf_path}")
            logger.info(f"{'=' * 80}")

            job_logger.end_job_success(records_processed=len(df))
            return {'excel': excel_path, 'pdf': pdf_path}

        except Exception as e:
            import traceback
            logger.error(f"OptionSingleTradingStrategyAnalyzerReport failed: {e}")
            logger.error(traceback.format_exc())
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise


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

    reporter = OptionSingleTradingStrategyAnalyzerReport()

    for config in report_configs:
        name = config.get("name")
        logger.info(f"\n{'#' * 80}")
        logger.info(f"# Running config: {name}")
        logger.info(f"{'#' * 80}")
        try:
            result = reporter.run(
                trade_date=config.get("trade_date"),
                ts_code_filter=config.get("ts_code_filter"),
                call_put=config.get("call_put"),
            )
            if result.get('excel'):
                logger.info(f"✅ [{name}] Excel: {result['excel']}")
            if result.get('pdf'):
                logger.info(f"✅ [{name}] PDF: {result['pdf']}")
            if not result.get('excel') and not result.get('pdf'):
                logger.warning(f"⚠️ [{name}] No data, report skipped")
        except Exception as e:
            logger.error(f"❌ [{name}] Failed: {e}", exc_info=True)

import sys

import numpy as np
import pandas as pd

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

logger = CommonLib.logger


class PDAnalysis:
    """
    违约概率 (Probability of Default) 分析类

    基于 Altman Z-Score 模型，从 ClickHouse 中的财务指标数据反推原始财务科目，
    计算 Z-Score → 通过 Sigmoid 函数映射为 PD（违约概率） → 进一步计算 EL（预期损失）。

    数据源: df_akshare_stock_financial_analysis_indicator (由 AkShareFinancialDataIndicatorService 写入)
    结果表: df_akshare_stock_financial_analysis_indicator_matrics
    """

    # ClickHouse 源表名
    INDICATOR_TABLE = "indexsysdb.df_akshare_stock_financial_analysis_indicator"
    # ClickHouse 结果表名
    MATRICS_TABLE = "indexsysdb.df_akshare_stock_financial_analysis_indicator_matrics"
    # ClickHouse 股票基础信息表名
    STOCK_BASIC_TABLE = "indexsysdb.df_tushare_stock_basic"

    # Sigmoid 映射参数（标定: Z=3.0 → PD≈0.5%, Z=1.8 → PD≈10%）
    ALPHA = -2.45
    BETA = 2.58

    # 违约损失率 (Loss Given Default)，假设 50%
    LGD = 0.5
    # 风险敞口 (Exposure at Default)，固定 100 万
    EAD = 1_000_000

    def __init__(self):
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName=sys._getframe().f_code.co_name,
                          event="PDAnalysis started")

    def writeLogInfo(self, className="unknown", functionName="unknown", event="unknown"):
        """记录日志信息"""
        print("%s.%s: %s" % (className, functionName, event))
        logger.info("%s.%s: %s" % (className, functionName, event))

    # ========================= 数据获取 =========================

    def fetch_financial_indicator_data(self, symbol: str) -> pd.DataFrame:
        """
        从 ClickHouse 读取指定股票的财务分析指标数据

        Args:
            symbol (str): 股票代码，如 '002093'

        Returns:
            pd.DataFrame: 含英文列名的财务指标数据
        """
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName=sys._getframe().f_code.co_name,
                          event=f"Fetching financial data for symbol={symbol}")

        # 核心列
        columns = [
            'date', 'symbol',
            'total_assets', 'main_profit_amount', 'main_business_margin',
            'total_asset_margin', 'equity_ratio', 'asset_liability_ratio',
            'current_asset_turnover', 'current_ratio',
            'retained_earnings_per_share', 'net_asset_per_share_before_adj',
            'total_asset_turnover',
        ]

        sql = (
            f"SELECT {', '.join(columns)} "
            f"FROM {self.INDICATOR_TABLE} "
            f"WHERE symbol = %(symbol)s "
            f"ORDER BY date ASC"
        )
        result = ClickhouseService.clickhouseClient.execute(sql, {'symbol': symbol})

        if not result:
            logger.warning(f"未找到 symbol={symbol} 的财务指标数据")
            return pd.DataFrame()

        df = pd.DataFrame(result, columns=columns)

        # 数值列: String → float
        numeric_columns = [
            'total_assets', 'main_profit_amount', 'main_business_margin',
            'total_asset_margin', 'equity_ratio', 'asset_liability_ratio',
            'current_asset_turnover', 'current_ratio',
            'retained_earnings_per_share', 'net_asset_per_share_before_adj',
            'total_asset_turnover',
        ]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        logger.info(f"fetch_financial_indicator_data: {len(df)} rows for symbol={symbol}")
        return df

    def _fetch_stock_info(self, symbol: str) -> dict:
        """
        从 df_tushare_stock_basic 获取股票的 name 和 industry

        Args:
            symbol (str): 股票代码，如 '002093'

        Returns:
            dict: {'name': ..., 'industry': ...}，查询不到则返回空字符串
        """
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName=sys._getframe().f_code.co_name,
                          event=f"Fetching stock info for symbol={symbol}")

        sql = (
            f"SELECT name, industry "
            f"FROM {self.STOCK_BASIC_TABLE} "
            f"WHERE symbol = %(symbol)s "
            f"LIMIT 1"
        )
        result = ClickhouseService.clickhouseClient.execute(sql, {'symbol': symbol})

        if result and len(result) > 0:
            name = result[0][0] or ''
            industry = result[0][1] or ''
            logger.info(f"Stock info retrieved: name={name}, industry={industry}")
        else:
            logger.warning(f"未在 df_tushare_stock_basic 中找到 symbol={symbol} 的信息")
            name = ''
            industry = ''

        return {'name': name, 'industry': industry}

    # ========================= 从比率反推原始财务数据 =========================

    def _derive_raw_financials(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        从财务指标比率反推 Altman Z-Score 所需的原始科目

        公式说明:
        - 总资产: 直取 total_assets
        - 主营业务收入: main_profit_amount * 100 / main_business_margin (fallback: total_assets * total_asset_turnover)
        - 利润总额: total_assets * total_asset_margin / 100
        - 股东权益: total_assets * equity_ratio / 100
        - 总负债: total_assets * asset_liability_ratio / 100 (fallback: total_assets - 股东权益)
        - 流动资产: revenue / current_asset_turnover
        - 流动负债: current_assets / current_ratio
        - 留存收益: retained_earnings_per_share / net_asset_per_share_before_adj * 股东权益

        Args:
            df: 含财务指标比率的 DataFrame

        Returns:
            补充了原始科目的 DataFrame
        """
        if df.empty:
            return df

        # ---------- 总资产（直取） ----------
        df["总资产"] = df["total_assets"]

        # ---------- 主营业务收入 ----------
        gross_profit = df["main_profit_amount"]
        gross_margin = df["main_business_margin"]
        revenue_by_margin = np.where(
            pd.notna(gross_profit) & pd.notna(gross_margin) & (gross_margin != 0),
            gross_profit * 100 / gross_margin,
            np.nan
        )
        total_asset_vals = df["总资产"].values
        asset_turnover = df["total_asset_turnover"]
        revenue_by_turnover = np.where(
            pd.notna(total_asset_vals) & pd.notna(asset_turnover) & (asset_turnover != 0),
            total_asset_vals * asset_turnover,
            np.nan
        )
        df["主营业务收入"] = np.where(
            pd.notna(revenue_by_margin), revenue_by_margin, revenue_by_turnover
        )

        # ---------- 利润总额 ----------
        roa_margin = df["total_asset_margin"]
        df["利润总额"] = np.where(
            pd.notna(total_asset_vals) & pd.notna(roa_margin),
            total_asset_vals * roa_margin / 100,
            np.nan
        )

        # ---------- 股东权益 ----------
        equity_ratio_vals = df["equity_ratio"]
        df["股东权益"] = np.where(
            pd.notna(total_asset_vals) & pd.notna(equity_ratio_vals),
            total_asset_vals * equity_ratio_vals / 100,
            np.nan
        )

        # ---------- 总负债 ----------
        debt_ratio_vals = df["asset_liability_ratio"]
        df["总负债"] = np.where(
            pd.notna(total_asset_vals) & pd.notna(debt_ratio_vals),
            total_asset_vals * debt_ratio_vals / 100,
            np.nan
        )
        mask_fallback = pd.isna(df["总负债"]) & pd.notna(df["总资产"]) & pd.notna(df["股东权益"])
        df.loc[mask_fallback, "总负债"] = (
            df.loc[mask_fallback, "总资产"] - df.loc[mask_fallback, "股东权益"]
        )

        # ---------- 流动资产 ----------
        current_turnover = df["current_asset_turnover"]
        revenue = df["主营业务收入"].values
        df["流动资产"] = np.where(
            pd.notna(revenue) & pd.notna(current_turnover) & (current_turnover != 0),
            revenue / current_turnover,
            np.nan
        )

        # ---------- 流动负债 ----------
        current_ratio_vals = df["current_ratio"]
        current_assets = df["流动资产"].values
        df["流动负债"] = np.where(
            pd.notna(current_assets) & pd.notna(current_ratio_vals) & (current_ratio_vals != 0),
            current_assets / current_ratio_vals,
            np.nan
        )

        # ---------- 留存收益（近似） ----------
        undiv_per_share = df["retained_earnings_per_share"]
        equity_per_share = df["net_asset_per_share_before_adj"]
        equity_vals = df["股东权益"].values
        df["留存收益"] = np.where(
            pd.notna(undiv_per_share) & pd.notna(equity_per_share) &
            pd.notna(equity_vals) & (equity_per_share != 0),
            undiv_per_share / equity_per_share * equity_vals,
            np.nan
        )

        return df

    # ========================= Z-Score / PD / EL 计算 =========================

    def calculate_risk_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算 Altman Z-Score, 风险等级, PD (违约概率), EL (预期损失)

        Altman Z-Score 公式 (制造业):
            Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5
        where:
            X1 = (流动资产 - 流动负债) / 总资产   (营运资本 / 总资产)
            X2 = 留存收益 / 总资产
            X3 = 利润总额 / 总资产                (≈ EBIT / 总资产)
            X4 = 股东权益 / 总负债
            X5 = 主营业务收入 / 总资产             (资产周转率)

        Sigmoid PD 映射:
            PD = 1 / (1 + e^(α + β·Z))
            标定: Z=3.0 → PD≈0.5%, Z=1.8 → PD≈10%
            → α = -2.45, β = 2.58

        Args:
            df: 含原始科目的 DataFrame

        Returns:
            含 Z_Score, 风险等级, PD, EL 的 DataFrame
        """
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName=sys._getframe().f_code.co_name,
                          event="Calculating risk metrics")

        if df.empty:
            return df

        result = df.copy()

        # 过滤无效行
        required_cols = ["总资产", "流动资产", "流动负债", "留存收益",
                         "利润总额", "股东权益", "总负债", "主营业务收入"]
        result = result.dropna(subset=required_cols)
        if result.empty:
            logger.warning("推导后无有效数据行，无法计算风险指标")
            return result

        # 核心比率
        X1 = (result["流动资产"] - result["流动负债"]) / result["总资产"]
        X2 = result["留存收益"] / result["总资产"]
        X3 = result["利润总额"] / result["总资产"]
        X4 = result["股东权益"] / result["总负债"]
        X5 = result["主营业务收入"] / result["总资产"]

        # Altman Z-Score
        result["z_score"] = 1.2 * X1 + 1.4 * X2 + 3.3 * X3 + 0.6 * X4 + 1.0 * X5

        # 风险等级（传统三段论）
        conditions = [result["z_score"] >= 3.0, result["z_score"] >= 1.8]
        choices = ["green_safe", "yellow_grey"]
        result["risk_level"] = np.select(conditions, choices, default="red_distress")

        # Sigmoid PD 映射: PD = 1 / (1 + e^(α + β·Z))
        result["pd"] = 1 / (1 + np.exp(self.ALPHA + self.BETA * result["z_score"]))

        # EL = PD × LGD × EAD
        result["el"] = result["pd"] * self.LGD * self.EAD
        result["ead"] = self.EAD

        # 保留分量 X1~X5
        result["x1"] = X1
        result["x2"] = X2
        result["x3"] = X3
        result["x4"] = X4
        result["x5"] = X5

        logger.info(f"calculate_risk_metrics: {len(result)} valid rows")

        return result

    # ========================= 数据持久化 =========================

    def _prepare_output_dataframe(self, df: pd.DataFrame, symbol: str, name: str = '', industry: str = '') -> pd.DataFrame:
        """
        整理最终输出 DataFrame，匹配 matrics 表结构

        Args:
            df: 计算后的 DataFrame
            symbol: 股票代码
            name: 股票名称（来自 df_tushare_stock_basic）
            industry: 行业（来自 df_tushare_stock_basic）

        Returns:
            整理后的 DataFrame，仅含 matrics 表所需列
        """
        output_columns = [
            'date', 'symbol', 'name', 'industry',
            'z_score', 'risk_level', 'pd', 'el', 'ead',
            'total_assets', 'total_equity', 'total_liabilities',
            'profit_before_tax', 'revenue',
            'current_assets', 'current_liabilities', 'retained_earnings',
            'x1', 'x2', 'x3', 'x4', 'x5',
        ]

        output = pd.DataFrame()
        output['date'] = df['date']
        output['symbol'] = symbol
        output['name'] = name
        output['industry'] = industry
        output['z_score'] = df['z_score']
        output['risk_level'] = df['risk_level']
        output['pd'] = df['pd']
        output['el'] = df['el']
        output['ead'] = df['ead']

        output['total_assets'] = df['总资产']
        output['total_equity'] = df['股东权益']
        output['total_liabilities'] = df['总负债']
        output['profit_before_tax'] = df['利润总额']
        output['revenue'] = df['主营业务收入']
        output['current_assets'] = df['流动资产']
        output['current_liabilities'] = df['流动负债']
        output['retained_earnings'] = df['留存收益']

        output['x1'] = df['x1']
        output['x2'] = df['x2']
        output['x3'] = df['x3']
        output['x4'] = df['x4']
        output['x5'] = df['x5']

        return output

    def delete_existing_matrics(self, symbol: str):
        """
        删除 matrics 表中指定股票的旧数据

        Args:
            symbol (str): 股票代码
        """
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName=sys._getframe().f_code.co_name,
                          event=f"Deleting existing matrics for symbol={symbol}")

        del_sql = (
            f"ALTER TABLE {self.MATRICS_TABLE} "
            f"DELETE WHERE symbol = '{symbol}'"
        )
        ClickhouseService.execute_sql(del_sql)
        logger.info(f"Deleted old matrics data for symbol={symbol}")

    def save_matrics_to_clickhouse(self, df: pd.DataFrame):
        """
        将计算结果保存到 ClickHouse matrics 表

        Args:
            df: 最终输出的 DataFrame
        """
        if df.empty:
            logger.info("DataFrame is empty, skipping save")
            return

        ClickhouseService.save_dataframe_to_clickhouse(
            dataframe=df,
            table_name='df_akshare_stock_financial_analysis_indicator_matrics',
            database='indexsysdb'
        )
        logger.info(f"Saved {len(df)} rows to matrics table")

    # ========================= 主流程 =========================

    def run(self, symbol: str) -> pd.DataFrame:
        """
        执行单个股票的 PD 分析完整流程

        步骤:
        1. 从 ClickHouse 读取财务指标数据
        2. 获取股票基础信息 (name, industry)
        3. 反推原始财务科目
        4. 计算 Z-Score / PD / EL
        5. 删除旧数据 & 保存新结果

        Args:
            symbol (str): 股票代码，如 '002093'

        Returns:
            pd.DataFrame: 计算结果（含风险指标）
        """
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName=sys._getframe().f_code.co_name,
                          event=f"Running PD analysis for symbol={symbol}")

        logger.info("=" * 60)
        logger.info(f"  Step 1/5: 获取财务指标数据 (symbol={symbol})")
        logger.info("=" * 60)
        df_indicators = self.fetch_financial_indicator_data(symbol)
        if df_indicators.empty:
            logger.warning(f"symbol={symbol} 无财务指标数据，跳过")
            return pd.DataFrame()

        logger.info("=" * 60)
        logger.info(f"  Step 2/5: 获取股票基础信息 (name, industry)")
        logger.info("=" * 60)
        stock_info = self._fetch_stock_info(symbol)

        logger.info("=" * 60)
        logger.info(f"  Step 3/5: 反推原始财务科目")
        logger.info("=" * 60)
        df_derived = self._derive_raw_financials(df_indicators)
        if df_derived.empty:
            logger.warning(f"symbol={symbol} 反推后无有效数据行")
            return pd.DataFrame()

        logger.info("=" * 60)
        logger.info(f"  Step 4/5: 计算 Z-Score / PD / EL")
        logger.info("=" * 60)
        df_result = self.calculate_risk_metrics(df_derived)
        if df_result.empty:
            logger.warning(f"symbol={symbol} 计算后无有效数据行")
            return pd.DataFrame()

        # 整理输出（含 name, industry）
        output_df = self._prepare_output_dataframe(
            df_result, symbol,
            name=stock_info['name'],
            industry=stock_info['industry']
        )

        logger.info("=" * 60)
        logger.info(f"  Step 5/5: 保存结果到 ClickHouse")
        logger.info("=" * 60)
        self.delete_existing_matrics(symbol)
        self.save_matrics_to_clickhouse(output_df)

        logger.info(f"PD analysis completed for symbol={symbol}: {len(output_df)} rows")

        return output_df

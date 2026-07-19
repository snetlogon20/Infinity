import sys
import numpy as np
import pandas as pd

from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator import CommonLib, CommonParameters

logger = CommonLib.logger
commonLib = CommonLib()


class MacroEconomicIndicatorAnalysis:
    """宏观经济指标数据生成类

    流程：
    1. 从 ClickHouse 拉取日频宏观数据（多表 LEFT JOIN）
    2. 重采样为月度（取月末最后交易日值）
    3. 前向填充缺失值
    4. 计算每条数据的环比增幅 _pct
    5. 写入 tb_macro_economic_indicator
    """

    # 需要计算 _pct 环比增幅的字段
    PCT_FIELDS = [
        'shibor_3m_eom', 'lpr_5y_eom', 'ust_y10_eom',
        'shibor_on', 'shibor_1w', 'shibor_1m', 'shibor_1y',
        'lpr_1y',
        'ust_y2', 'ust_y30',
        'm1_yoy', 'm2_yoy', 'cpi_yoy', 'ppi_yoy', 'pmi030000',
        'forex_reserves', 'gold_reserves',
        'exports_yoy', 'imports_yoy',
        'total_shrzgm', 'rmb_loan', 'entrusted_loan', 'trust_loan',
        'corporate_bonds', 'equity_financing',
        'usdcnh_bid_close', 'usdcnh_ask_close',
        'cn_yield_2y', 'cn_yield_5y', 'cn_yield_10y',
        'gdp_yoy', 'gdp_pi_yoy', 'gdp_si_yoy', 'gdp_ti_yoy',
        'usdx_index', 'gold_close', 'dji_close', 'sh_close', 'sz_close',
        'hsi_close', 'twii_close', 'ks11_close', 'n225_close',
        'vix_close',
    ]

    TARGET_TABLE = 'tb_macro_economic_indicator'

    def __init__(self):
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName=sys._getframe().f_code.co_name,
                          event="MacroEconomicIndicator started")

    def writeLogInfo(self, className="unknown", functionName="unknown", event="unknown"):
        """记录日志信息"""
        print("%s.%s: %s" % (className, functionName, event))
        logger.info("%s.%s: %s" % (className, functionName, event))

    def fetch_macro_data(self):
        """从 ClickHouse 拉取宏观日频数据（多表 LEFT JOIN）

        返回:
        - df: 日频宏观指标 DataFrame，按 trade_date 升序
        """
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName=sys._getframe().f_code.co_name,
                          event="Fetching daily macro economic data from ClickHouse")

        today = CommonParameters.today

        sql = f"""
        SELECT
            cal.trade_date AS trade_date,
            cal.trade_month AS trade_month,
            cal.trade_year AS trade_year,
            cal.quarter AS quarter,
            shibor.tenor_on    AS shibor_on,
            shibor.tenor_1w    AS shibor_1w,
            shibor.tenor_1m    AS shibor_1m,
            shibor.tenor_3m    AS shibor_3m,
            shibor.tenor_1y    AS shibor_1y,
            lpr.tenor_1y       AS lpr_1y,
            lpr.tenor_5y       AS lpr_5y,
            ust.y2             AS ust_y2,
            ust.y10            AS ust_y10,
            ust.y30            AS ust_y30,
            ms.m1_yoy          AS m1_yoy,
            ms.m2_yoy          AS m2_yoy,
            cpi.nt_yoy         AS cpi_yoy,
            ppi.ppi_yoy        AS ppi_yoy,
            pmi.pmi030000      AS pmi030000,
            fg.forex_reserves_value  AS forex_reserves,
            fg.gold_reserves_value   AS gold_reserves,
            hj.monthly_exports_yoy   AS exports_yoy,
            hj.monthly_imports_yoy   AS imports_yoy,
            shr.total_shrzgm         AS total_shrzgm,
            shr.rmb_loan             AS rmb_loan,
            shr.entrusted_loan       AS entrusted_loan,
            shr.trust_loan           AS trust_loan,
            shr.corporate_bonds      AS corporate_bonds,
            shr.non_financial_enterprise_domestic_equity_financing AS equity_financing,
            fx.bid_close       AS usdcnh_bid_close,
            fx.ask_close       AS usdcnh_ask_close,
            cb.cn_yield_2y  AS cn_yield_2y,
            cb.cn_yield_5y  AS cn_yield_5y,
            cb.cn_yield_10y AS cn_yield_10y,
            gdp.gdp_yoy          AS gdp_yoy,
            gdp.pi_yoy         AS gdp_pi_yoy,
            gdp.si_yoy         AS gdp_si_yoy,
            gdp.ti_yoy         AS gdp_ti_yoy,
            udx.USDX_index      AS usdx_index,
            gold.close          AS gold_close,
            dji.close           AS dji_close,
            sh.close            AS sh_close,
            sz.close            AS sz_close,
            hsi.close           AS hsi_close,
            twii.close          AS twii_close,
            ks11.close          AS ks11_close,
            n225.close          AS n225_close,
            vix.close           AS vix_close
        FROM indexsysdb.df_sys_calendar cal
        LEFT JOIN indexsysdb.df_tushare_shibor_daily shibor
            ON cal.trade_date = shibor.trade_date
        LEFT JOIN indexsysdb.df_tushare_shibor_lpr_daily lpr
            ON cal.trade_date = lpr.trade_date
        LEFT JOIN indexsysdb.df_tushare_us_treasury_yield_cruve ust
            ON cal.trade_date = ust.trade_date
        LEFT JOIN indexsysdb.cn_money_supply ms
            ON substring(cal.trade_date, 1, 6) = ms.trade_date
        LEFT JOIN indexsysdb.df_tushare_cn_cpi cpi
            ON substring(cal.trade_date, 1, 6) = cpi.trade_date
        LEFT JOIN indexsysdb.df_tushare_cn_ppi ppi
            ON substring(cal.trade_date, 1, 6) = ppi.trade_date
        LEFT JOIN indexsysdb.df_tushare_cn_pmi pmi
            ON substring(cal.trade_date, 1, 6) = pmi.trade_date
        LEFT JOIN indexsysdb.df_macro_china_fx_gold fg
            ON substring(cal.trade_date, 1, 6) = fg.month
        LEFT JOIN indexsysdb.df_macro_china_hgjck hj
            ON substring(cal.trade_date, 1, 6) = hj.month
        LEFT JOIN indexsysdb.df_macro_china_shrzgm shr
            ON substring(cal.trade_date, 1, 6) = shr.month
        LEFT JOIN indexsysdb.df_tushare_fx_daily fx
            ON cal.trade_date = fx.trade_date AND fx.ts_code = 'USDCNH.FXCM'
        LEFT JOIN indexsysdb.df_akshare_bond_zh_us_rate cb
            ON cal.trade_date = cb.trade_date
        LEFT JOIN indexsysdb.df_tushare_cn_gdp gdp
            ON concat(cal.trade_year, 'Q', cal.quarter) = gdp.quarter
        LEFT JOIN indexsysdb.df_tushare_usd_index_daily udx
            ON cal.trade_date = udx.trade_date
        LEFT JOIN indexsysdb.df_akshare_futures_foreign_hist gold
            ON cal.trade_date = replaceAll(gold.date, '-', '') AND gold.symbol = 'GC'
        LEFT JOIN indexsysdb.df_tushare_index_global dji
            ON cal.trade_date = dji.trade_date AND dji.ts_code = 'DJI'
        LEFT JOIN indexsysdb.df_tushare_cn_index_daily sh
            ON cal.trade_date = sh.trade_date AND sh.ts_code = '000001.SH'
        LEFT JOIN indexsysdb.df_tushare_cn_index_daily sz
            ON cal.trade_date = sz.trade_date AND sz.ts_code = '399001.SZ'
        LEFT JOIN indexsysdb.df_tushare_index_global hsi
            ON cal.trade_date = hsi.trade_date AND hsi.ts_code = 'HSI'
        LEFT JOIN indexsysdb.df_tushare_index_global twii
            ON cal.trade_date = twii.trade_date AND twii.ts_code = 'TWII'
        LEFT JOIN indexsysdb.df_tushare_index_global ks11
            ON cal.trade_date = ks11.trade_date AND ks11.ts_code = 'KS11'
        LEFT JOIN indexsysdb.df_tushare_index_global n225
            ON cal.trade_date = n225.trade_date AND n225.ts_code = 'N225'
        LEFT JOIN indexsysdb.df_cboe_vix vix
            ON cal.trade_date = replaceAll(vix.date, '-', '')
        WHERE cal.trade_date >= '20100101' and cal.trade_date <= '{today}'
        ORDER BY cal.trade_date
        """

        df = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        logger.info(f"Fetched {len(df)} rows of daily macro economic data")
        return df

    def _resample_to_monthly(self, df):
        """将日频数据重采样为月度数据（取月末最后交易日值）

        按 YYYYMM 分组，对每个指标取该月最后一个非空值。
        部分字段重命名以兼容下游：shibor_3m→shibor_3m_eom, lpr_5y→lpr_5y_eom, ust_y10→ust_y10_eom

        参数:
        - df: 日频 DataFrame，含 trade_date 列

        返回:
        - df_monthly: 月度 DataFrame，含 trade_year, trade_month, last_trade_date
        """
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName=sys._getframe().f_code.co_name,
                          event="Resampling daily data to monthly (end-of-month)")

        # 确保按日期排序
        df = df.sort_values('trade_date').reset_index(drop=True)

        # 构造 YYYYMM 列用于分组
        df['yyyymm'] = df['trade_date'].astype(str).str[:6]

        # 数值列（排除 key 列）
        key_cols = ['trade_date', 'trade_year', 'trade_month', 'quarter', 'yyyymm']
        value_cols = [c for c in df.columns if c not in key_cols]

        # 取月末最后非空值
        def _last_non_null(series):
            non_null = series.dropna()
            return non_null.iloc[-1] if len(non_null) > 0 else np.nan

        agg_dict = {col: _last_non_null for col in value_cols}
        agg_dict['trade_date'] = 'max'  # 当月最后交易日

        df_monthly = df.groupby('yyyymm').agg(agg_dict).reset_index()

        # 重命名 trade_date → last_trade_date
        df_monthly = df_monthly.rename(columns={'trade_date': 'last_trade_date'})

        # 构造 trade_year, trade_month
        df_monthly['trade_year'] = df_monthly['yyyymm'].str[:4].astype(int)
        df_monthly['trade_month'] = df_monthly['yyyymm'].astype(int)

        # 对日频取值字段添加 _eom 后缀以兼容下游
        eom_rename = {
            'shibor_3m': 'shibor_3m_eom',
            'lpr_5y': 'lpr_5y_eom',
            'ust_y10': 'ust_y10_eom',
        }
        df_monthly = df_monthly.rename(columns=eom_rename)

        # 整理输出列顺序
        result_cols = ['trade_year', 'trade_month', 'last_trade_date']
        result_cols += [c for c in df_monthly.columns
                        if c not in result_cols and c != 'yyyymm']
        df_monthly = df_monthly[result_cols].sort_values('trade_month').reset_index(drop=True)

        logger.info(f"Resampled: {len(df)} daily rows -> {len(df_monthly)} monthly rows")
        return df_monthly

    def forward_fill_missing(self, df):
        """前向填充缺失数据（将0也视为缺失，按 trade_month 排序取前一阶段非0值）

        ClickHouse 返回的0代表该月份无数据，需按时间排序后取前一期非0值填充。

        参数:
        - df: 原始 DataFrame

        返回:
        - df: 填充后的 DataFrame
        """
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName=sys._getframe().f_code.co_name,
                          event="Forward filling missing data (treat 0 as missing)")

        # 按 trade_month 升序排序，确保取前一阶段的数据
        df = df.sort_values('trade_month').reset_index(drop=True)

        key_cols = ['trade_year', 'trade_month', 'last_trade_date']
        data_cols = [c for c in df.columns if c not in key_cols]

        zero_count = 0
        for col in data_cols:
            # 将0视为缺失，替换为NaN后再前向填充
            col_zero = (df[col] == 0).sum()
            if col_zero > 0:
                zero_count += col_zero
                df[col] = df[col].replace(0, np.nan)
            df[col] = df[col].ffill()

        logger.info(f"Forward fill: sorted by trade_month, {zero_count} zero values filled")

        return df

    def calculate_pct_changes(self, df):
        """计算环比增幅百分比（小数表示，1% = 0.01）

        对 PCT_FIELDS 中每个字段，计算 (当期 - 前期) / 前期，
        新增 _{字段名}_pct 列。

        参数:
        - df: DataFrame

        返回:
        - df: 追加了 _pct 列的 DataFrame
        """
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName=sys._getframe().f_code.co_name,
                          event="Calculating month-over-month percentage changes")

        for col in self.PCT_FIELDS:
            if col not in df.columns:
                continue
            pct_col = f'{col}_pct'
            prev = df[col].shift(1)
            df[pct_col] = np.where(
                (prev.notna()) & (prev != 0),
                (df[col] - prev) / prev,
                np.nan
            )

        pct_cols = [f'{c}_pct' for c in self.PCT_FIELDS if c in df.columns]
        logger.info(f"Calculated {len(pct_cols)} _pct columns")
        return df

    def save_to_clickhouse(self, df):
        """全量覆写写入 ClickHouse 目标表

        先执行标准建表 SQL，再插入数据，避免 save_dataframe_to_clickhouse
        自动推断列类型（如把 None 推断为 String）。

        参数:
        - df: 待写入的 DataFrame
        """
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName=sys._getframe().f_code.co_name,
                          event=f"Saving to {self.TARGET_TABLE}")

        # 删除旧表
        del_sql = f"DROP TABLE IF EXISTS indexsysdb.{self.TARGET_TABLE}"
        ClickhouseService.execute_sql(del_sql)
        logger.info(f"Dropped table {self.TARGET_TABLE} if existed")

        # 执行标准建表 SQL（保留 UInt32 / Float64 等精确类型）
        create_sql = f"""
        CREATE TABLE indexsysdb.{self.TARGET_TABLE} (
            trade_year UInt32,
            trade_month UInt32,
            last_trade_date String,
            shibor_3m_eom Float64,
            lpr_5y_eom Float64,
            ust_y10_eom Float64,
            m1_yoy Float64,
            m2_yoy Float64,
            cpi_yoy Float64,
            ppi_yoy Float64,
            pmi030000 Float64,
            forex_reserves Float64,
            gold_reserves Float64,
            exports_yoy Float64,
            imports_yoy Float64,
            total_shrzgm Float64,
            rmb_loan Float64,
            entrusted_loan Float64,
            trust_loan Float64,
            corporate_bonds Float64,
            equity_financing Float64,
            usdcnh_bid_close Float64,
            usdcnh_ask_close Float64,
            cn_yield_2y Float64,
            cn_yield_5y Float64,
            cn_yield_10y Float64,
            gdp_yoy Float64,
            shibor_on Float64,
            shibor_1w Float64,
            shibor_1m Float64,
            shibor_1y Float64,
            lpr_1y Float64,
            ust_y2 Float64,
            ust_y30 Float64,
            gdp_pi_yoy Float64,
            gdp_si_yoy Float64,
            gdp_ti_yoy Float64,
            shibor_3m_eom_pct Float64,
            lpr_5y_eom_pct Float64,
            ust_y10_eom_pct Float64,
            m1_yoy_pct Float64,
            m2_yoy_pct Float64,
            cpi_yoy_pct Float64,
            ppi_yoy_pct Float64,
            pmi030000_pct Float64,
            forex_reserves_pct Float64,
            gold_reserves_pct Float64,
            exports_yoy_pct Float64,
            imports_yoy_pct Float64,
            total_shrzgm_pct Float64,
            rmb_loan_pct Float64,
            entrusted_loan_pct Float64,
            trust_loan_pct Float64,
            corporate_bonds_pct Float64,
            equity_financing_pct Float64,
            usdcnh_bid_close_pct Float64,
            usdcnh_ask_close_pct Float64,
            cn_yield_2y_pct Float64,
            cn_yield_5y_pct Float64,
            cn_yield_10y_pct Float64,
            gdp_yoy_pct Float64,
            shibor_on_pct Float64,
            shibor_1w_pct Float64,
            shibor_1m_pct Float64,
            shibor_1y_pct Float64,
            lpr_1y_pct Float64,
            ust_y2_pct Float64,
            ust_y30_pct Float64,
            gdp_pi_yoy_pct Float64,
            gdp_si_yoy_pct Float64,
            gdp_ti_yoy_pct Float64,
            usdx_index Float64,
            gold_close Float64,
            dji_close Float64,
            sh_close Float64,
            sz_close Float64,
            hsi_close Float64,
            twii_close Float64,
            ks11_close Float64,
            n225_close Float64,
            vix_close Float64,
            usdx_index_pct Float64,
            gold_close_pct Float64,
            dji_close_pct Float64,
            sh_close_pct Float64,
            sz_close_pct Float64,
            hsi_close_pct Float64,
            twii_close_pct Float64,
            ks11_close_pct Float64,
            n225_close_pct Float64,
            vix_close_pct Float64
        )
        ENGINE = MergeTree()
        ORDER BY (trade_month)
        SETTINGS index_granularity = 8192
        """
        ClickhouseService.execute_sql(create_sql)
        logger.info(f"Created table {self.TARGET_TABLE}")

        # 写入数据（表已存在，save_dataframe_to_clickhouse 会直接 INSERT）
        ClickhouseService.save_dataframe_to_clickhouse(
            dataframe=df,
            table_name=self.TARGET_TABLE,
            database='indexsysdb'
        )
        logger.info(f"Saved {len(df)} rows to {self.TARGET_TABLE}")

    def generate_macro_indicator_data(self):
        """生成宏观经济指标数据的主流程

        返回:
        - df: 最终 DataFrame
        """
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName=sys._getframe().f_code.co_name,
                          event="Starting macro economic indicator data generation")

        # Step 1: 拉取日频数据
        logger.info("\n📊 Step 1/4: Fetching daily macro data from ClickHouse...")
        df = self.fetch_macro_data()

        # Step 1.5: 日频→月度 重采样（取月末最后交易日值）
        logger.info("\n📅 Step 1.5/4: Resampling daily data to monthly...")
        df = self._resample_to_monthly(df)

        # Step 2: 前向填充缺失值
        logger.info("\n🔧 Step 2/4: Forward filling missing data...")
        df = self.forward_fill_missing(df)

        # Step 3: 计算环比增幅 _pct
        logger.info("\n📈 Step 3/4: Calculating MoM percentage changes...")
        df = self.calculate_pct_changes(df)

        # Step 4: 写入 ClickHouse
        logger.info("\n💾 Step 4/4: Saving to ClickHouse...")
        self.save_to_clickhouse(df)

        logger.info("\n" + "=" * 80)
        logger.info("✅ Macro economic indicator data generation completed!")
        logger.info(f"   Total rows: {len(df)}, Total columns: {len(df.columns)}")
        logger.info("=" * 80)

        return df

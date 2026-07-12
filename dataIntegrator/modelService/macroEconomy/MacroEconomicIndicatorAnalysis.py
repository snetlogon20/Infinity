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
    1. 从 ClickHouse 拉取月度宏观数据（多表 JOIN）
    2. 前向填充缺失值
    3. 计算每条数据的环比增幅 _pct
    4. 写入 tb_macro_economic_indicator
    """

    # 需要计算 _pct 环比增幅的字段
    PCT_FIELDS = [
        'shibor_3m_eom', 'lpr_5y_eom', 'ust_y10_eom',
        'm1_yoy', 'm2_yoy', 'cpi_yoy',
        'forex_reserves', 'gold_reserves',
        'exports_yoy', 'imports_yoy',
        'total_shrzgm', 'rmb_loan', 'entrusted_loan', 'trust_loan',
        'corporate_bonds', 'equity_financing',
        'usdcnh_bid_close', 'usdcnh_ask_close',
        'cn_yield_2y', 'cn_yield_5y', 'cn_yield_10y',
        'gdp_yoy',
        'usdx_index', 'gold_close', 'dji_close', 'sh_close', 'sz_close',
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
        """从 ClickHouse 拉取宏观月度数据

        返回:
        - df: 宏观指标 DataFrame，按 trade_month 升序
        """
        self.writeLogInfo(className=self.__class__.__name__,
                          functionName=sys._getframe().f_code.co_name,
                          event="Fetching macro economic data from ClickHouse")

        today = CommonParameters.today

        sql = f"""
        WITH
        money_monthly AS (
            SELECT
                trade_date AS yyyymm,
                max(m1_yoy) AS m1_yoy,
                max(m2_yoy) AS m2_yoy
            FROM indexsysdb.cn_money_supply
            GROUP BY trade_date
        ),
        cpi_monthly AS (
            SELECT
                trade_date AS yyyymm,
                max(nt_yoy) AS cpi_yoy
            FROM indexsysdb.df_tushare_cn_cpi
            GROUP BY trade_date
        ),
        fx_gold_monthly AS (
            SELECT
                month AS yyyymm,
                max(forex_reserves_value) AS forex_reserves,
                max(gold_reserves_value)  AS gold_reserves
            FROM indexsysdb.df_macro_china_fx_gold
            GROUP BY month
        ),
        trade_monthly AS (
            SELECT
                month AS yyyymm,
                max(monthly_exports_yoy) AS exports_yoy,
                max(monthly_imports_yoy) AS imports_yoy
            FROM indexsysdb.df_macro_china_hgjck
            GROUP BY month
        ),
        shrzgm_monthly AS (
            SELECT
                month AS yyyymm,
                max(total_shrzgm)                                       AS total_shrzgm,
                max(rmb_loan)                                           AS rmb_loan,
                max(entrusted_loan)                                     AS entrusted_loan,
                max(trust_loan)                                         AS trust_loan,
                max(corporate_bonds)                                    AS corporate_bonds,
                max(non_financial_enterprise_domestic_equity_financing) AS equity_financing
            FROM indexsysdb.df_macro_china_shrzgm
            GROUP BY month
        ),
        fx_daily_monthly AS (
            SELECT
                substring(trade_date, 1, 6) AS yyyymm,
                argMax(bid_close, trade_date) AS usdcnh_bid_close,
                argMax(ask_close, trade_date) AS usdcnh_ask_close
            FROM indexsysdb.df_tushare_fx_daily
            WHERE ts_code = 'USDCNH.FXCM'
            GROUP BY substring(trade_date, 1, 6)
        ),
        cb_monthly AS (
            SELECT
                substring(trade_date, 1, 6) AS yyyymm,
                argMax(cn_yield_2y, trade_date)  AS cn_yield_2y,
                argMax(cn_yield_5y, trade_date)  AS cn_yield_5y,
                argMax(cn_yield_10y, trade_date) AS cn_yield_10y
            FROM indexsysdb.df_akshare_bond_zh_us_rate
            GROUP BY substring(trade_date, 1, 6)
        ),
        gdp_quarterly AS (
            SELECT
                quarter,
                max(gdp_yoy) AS gdp_yoy
            FROM indexsysdb.df_tushare_cn_gdp
            GROUP BY quarter
        ),
        usdx_monthly AS (
            SELECT
                substring(trade_date, 1, 6) AS yyyymm,
                argMax(USDX_index, trade_date) AS usdx_index
            FROM indexsysdb.df_tushare_usd_index_daily
            GROUP BY substring(trade_date, 1, 6)
        ),
        gold_monthly AS (
            SELECT
                substring(replaceAll(date, '-', ''), 1, 6) AS yyyymm,
                argMax(close, replaceAll(date, '-', '')) AS gold_close
            FROM indexsysdb.df_akshare_futures_foreign_hist
            WHERE symbol = 'GC'
            GROUP BY substring(replaceAll(date, '-', ''), 1, 6)
        ),
        dji_monthly AS (
            SELECT
                substring(trade_date, 1, 6) AS yyyymm,
                argMax(close, trade_date) AS dji_close
            FROM indexsysdb.df_tushare_index_global
            WHERE ts_code = 'DJI'
            GROUP BY substring(trade_date, 1, 6)
        ),
        sh_monthly AS (
            SELECT
                substring(trade_date, 1, 6) AS yyyymm,
                argMax(close, trade_date) AS sh_close
            FROM indexsysdb.df_tushare_cn_index_daily
            WHERE ts_code = '000001.SH'
            GROUP BY substring(trade_date, 1, 6)
        ),
        sz_monthly AS (
            SELECT
                substring(trade_date, 1, 6) AS yyyymm,
                argMax(close, trade_date) AS sz_close
            FROM indexsysdb.df_tushare_cn_index_daily
            WHERE ts_code = '399001.SZ'
            GROUP BY substring(trade_date, 1, 6)
        )
        SELECT
            toUInt32(cal.trade_year) AS trade_year,
            toUInt32(concat(cal.trade_year, lpad(cal.trade_month, 2, '0'))) AS trade_month,
            max(cal.trade_date) AS last_trade_date,
            argMax(shibor.tenor_3m, cal.trade_date) AS shibor_3m_eom,
            argMax(lpr.tenor_5y, cal.trade_date) AS lpr_5y_eom,
            argMax(ust.y10, cal.trade_date) AS ust_y10_eom,
            max(mm.m1_yoy) AS m1_yoy,
            max(mm.m2_yoy) AS m2_yoy,
            max(cpi.cpi_yoy) AS cpi_yoy,
            max(fx.forex_reserves) AS forex_reserves,
            max(fx.gold_reserves)  AS gold_reserves,
            max(tr.exports_yoy) AS exports_yoy,
            max(tr.imports_yoy) AS imports_yoy,
            max(shr.total_shrzgm)   AS total_shrzgm,
            max(shr.rmb_loan)       AS rmb_loan,
            max(shr.entrusted_loan) AS entrusted_loan,
            max(shr.trust_loan)     AS trust_loan,
            max(shr.corporate_bonds) AS corporate_bonds,
            max(shr.equity_financing) AS equity_financing,
            max(fxd.usdcnh_bid_close) AS usdcnh_bid_close,
            max(fxd.usdcnh_ask_close) AS usdcnh_ask_close,
            max(cb.cn_yield_2y)  AS cn_yield_2y,
            max(cb.cn_yield_5y)  AS cn_yield_5y,
            max(cb.cn_yield_10y) AS cn_yield_10y,
            max(gdp.gdp_yoy) AS gdp_yoy,
            max(udx.usdx_index) AS usdx_index,
            max(gld.gold_close) AS gold_close,
            max(dji.dji_close) AS dji_close,
            max(sh.sh_close) AS sh_close,
            max(sz.sz_close) AS sz_close
        FROM indexsysdb.df_sys_calendar cal
        ANY LEFT JOIN indexsysdb.df_tushare_shibor_daily shibor
            ON cal.trade_date = shibor.trade_date
        ANY LEFT JOIN indexsysdb.df_tushare_shibor_lpr_daily lpr
            ON cal.trade_date = lpr.trade_date
        ANY LEFT JOIN indexsysdb.df_tushare_us_treasury_yield_cruve ust
            ON cal.trade_date = ust.trade_date
        ANY LEFT JOIN money_monthly mm
            ON substring(cal.trade_date, 1, 6) = mm.yyyymm
        ANY LEFT JOIN cpi_monthly cpi
            ON substring(cal.trade_date, 1, 6) = cpi.yyyymm
        ANY LEFT JOIN fx_gold_monthly fx
            ON substring(cal.trade_date, 1, 6) = fx.yyyymm
        ANY LEFT JOIN trade_monthly tr
            ON substring(cal.trade_date, 1, 6) = tr.yyyymm
        ANY LEFT JOIN shrzgm_monthly shr
            ON substring(cal.trade_date, 1, 6) = shr.yyyymm
        ANY LEFT JOIN fx_daily_monthly fxd
            ON substring(cal.trade_date, 1, 6) = fxd.yyyymm
        ANY LEFT JOIN cb_monthly cb
            ON substring(cal.trade_date, 1, 6) = cb.yyyymm
        ANY LEFT JOIN gdp_quarterly gdp
            ON concat(cal.trade_year, 'Q', cal.quarter) = gdp.quarter
        ANY LEFT JOIN usdx_monthly udx
            ON substring(cal.trade_date, 1, 6) = udx.yyyymm
        ANY LEFT JOIN gold_monthly gld
            ON substring(cal.trade_date, 1, 6) = gld.yyyymm
        ANY LEFT JOIN dji_monthly dji
            ON substring(cal.trade_date, 1, 6) = dji.yyyymm
        ANY LEFT JOIN sh_monthly sh
            ON substring(cal.trade_date, 1, 6) = sh.yyyymm
        ANY LEFT JOIN sz_monthly sz
            ON substring(cal.trade_date, 1, 6) = sz.yyyymm
        WHERE cal.trade_date BETWEEN '20100101' AND '{today}'
        GROUP BY
            toUInt32(cal.trade_year),
            toUInt32(concat(cal.trade_year, lpad(cal.trade_month, 2, '0')))
        ORDER BY
            toUInt32(cal.trade_year),
            toUInt32(concat(cal.trade_year, lpad(cal.trade_month, 2, '0')))
        """

        df = ClickhouseService.getDataFrameWithoutColumnsName(sql)
        logger.info(f"Fetched {len(df)} rows of macro economic data")
        return df

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
            shibor_3m_eom_pct Float64,
            lpr_5y_eom_pct Float64,
            ust_y10_eom_pct Float64,
            m1_yoy_pct Float64,
            m2_yoy_pct Float64,
            cpi_yoy_pct Float64,
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
            usdx_index Float64,
            gold_close Float64,
            dji_close Float64,
            sh_close Float64,
            sz_close Float64,
            usdx_index_pct Float64,
            gold_close_pct Float64,
            dji_close_pct Float64,
            sh_close_pct Float64,
            sz_close_pct Float64
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

        # Step 1: 拉取数据
        logger.info("\n📊 Step 1/4: Fetching macro data from ClickHouse...")
        df = self.fetch_macro_data()

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

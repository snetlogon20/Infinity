from sklearn.isotonic import IsotonicRegression
import pandas as pd
import numpy as np
from dataIntegrator.analysisService.InquiryManager import InquiryManager
from dataIntegrator import CommonLib, CommonParameters
from matplotlib import pyplot as plt
import streamlit as st

from dataIntegrator.modelService.isotonicAnalysis.IsotonicRegressionAnalyst import IsotonicRegressionAnalyst

logger = CommonLib.logger

def call_isotonic_regression_analyst(symbol, start_date, end_date, sql_template="",
                                      x_column='trade_date', y_column='close',
                                      title=None ):
    # 示例 1: 基本使用
    analyst = IsotonicRegressionAnalyst()
    # 执行分析
    result = analyst.analyze_workflow(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        x_column=x_column,
        y_column=y_column,
        title=title,
        sql_template=sql_template
    )
    # 打印结果
    print("\n保序回归结果:")
    if not result.empty:
        print(result[['trade_date', 'close', 'close_isotonic', 'close_residual']].head(10))
    else:
        print("数据为空，无法显示保序回归结果")

    return result

def analyze_gc():
    # 设置参数
    symbol = 'GC'  # 例如：黄金期货
    start_date = '2024-01-01'
    end_date = '2026-12-31'
    x_column = 'trade_date'
    y_column = 'close'
    title = f'Isotonic Regression - {symbol} Close Price Analysis'

    # 定义 SQL 模板
    sql_template = (
        f"select date as trade_date, open, close, low, high, pct_change "
        f"from indexsysdb.df_akshare_futures_foreign_hist "
        f"where symbol='{symbol}' and date>='{start_date.replace('-', '')}' "
        f"and date<='{end_date.replace('-', '')}' order by date"
    )
    call_isotonic_regression_analyst(symbol, start_date, end_date, sql_template, x_column, y_column, title)

def analyze_wti():
    # 设置参数
    symbol = 'CL'  # 例如：WTI OIL
    start_date = '2024-01-01'
    end_date = '2026-12-31'
    x_column = 'trade_date'
    y_column = 'close'
    title = f'Isotonic Regression - {symbol} Close Price Analysis'

    # 定义 SQL 模板
    sql_template = (
        f"select date as trade_date, open, close, low, high, pct_change "
        f"from indexsysdb.df_akshare_futures_foreign_hist "
        f"where symbol='{symbol}' and date>='{start_date.replace('-', '')}' "
        f"and date<='{end_date.replace('-', '')}' order by date"
    )
    print(sql_template)
    call_isotonic_regression_analyst(symbol, start_date, end_date, sql_template, x_column, y_column, title)

def analyze_usd_index():
    """
    分析美元指数数据

    参数:
        y_column: 要分析的列名，默认是 USDX_index
        start_date: 开始日期
        end_date: 结束日期
    """
    symbol = 'USD INDEX'  # 例如：黄金期货
    start_date = '2023-01-01'
    end_date = '2026-12-31'
    x_column = 'trade_date'
    y_column_original = 'USDX_index'
    y_column_alias = 'close'  # SQL 中的别名
    title = f'Isotonic Regression - {symbol}  Analysis'

    # 定义 SQL 模板
    sql_template = (
        f"select trade_date, {y_column_original} as {y_column_alias}, pct_change "
        f"from indexsysdb.df_tushare_usd_index_daily "
        f"where trade_date>='{start_date.replace('-', '')}' "
        f"and trade_date<='{end_date.replace('-', '')}' "
        f"and {y_column_original} > 0 "
        f"and {y_column_original} < 1000 "
        f"and not isNaN({y_column_original}) "
        f"and not isInfinite({y_column_original}) "
        f"order by trade_date"
    )
    print(sql_template)

    call_isotonic_regression_analyst(symbol, start_date, end_date, sql_template, x_column, y_column_alias, title)

def analyze_usd_cny():
    """
    分析美元指数数据

    参数:
        y_column: 要分析的列名，默认是 USDX_index
        start_date: 开始日期
        end_date: 结束日期
    """
    symbol = 'USD CNY'  # 例如：黄金期货
    start_date = '2025-08-01'
    end_date = '2026-12-31'
    x_column = 'trade_date'
    y_column_original = 'bid_close'
    y_column_alias = 'close'  # SQL 中的别名
    title = f'Isotonic Regression - {symbol}  Analysis'

    # 定义 SQL 模板
    sql_template = (
        f"""
            select trade_date, {y_column_original} as {y_column_alias}
            from indexsysdb.df_tushare_fx_daily
            where ts_code = 'USDCNH.FXCM' AND
                trade_date >= '{start_date.replace('-', '')}' and 
                trade_date <= '{end_date.replace('-', '')}' 
            order by trade_date
        """

    )
    print(sql_template)

    call_isotonic_regression_analyst(symbol, start_date, end_date, sql_template, x_column, y_column_alias, title)

def analyze_stock_daily():
    """
    分析中国股票日线数据

    参数:
        ts_code: 股票代码（如 '000001.SZ' 表示平安银行）
        start_date: 开始日期
        end_date: 结束日期
        y_column: 要分析的列名，默认是 close（收盘价）
    """
    # 设置参数（保持与 analyze_usd_cny 相同的参数结构）
    # symbol = '600000.SH'  # 上证综指
    symbol = '600490.SH'  # 鹏欣资源
    # symbol = '002093.SZ'  # 股票代码示例：国脉科技
    # symbol = '000902.SZ'  # 股票代码示例：新洋丰
    # symbol = '601398.SH'  # 股票代码示例：工商银行
    # symbol = '000001.SZ'  # 股票代码示例：平安银行

    start_date = '2024-01-01'
    end_date = '2026-12-31'
    x_column = 'trade_date'
    y_column_original = 'close'  # 使用表中的 close 列
    y_column_alias = 'close'  # SQL 中的别名（保持一致）
    title = f'Isotonic Regression - {symbol} Close Price Analysis'

    # 定义 SQL 模板
    sql_template = (
        f"""
            select trade_date, {y_column_original} as {y_column_alias}, open, high, low, pct_chg, vol, amount
            from indexsysdb.df_tushare_stock_daily
            where ts_code = '{symbol}' AND
                trade_date >= '{start_date.replace('-', '')}' AND 
                trade_date <= '{end_date.replace('-', '')}' AND
                {y_column_original} > 0 AND
                {y_column_original} < 100000 AND
                not isNaN({y_column_original}) AND
                not isInfinite({y_column_original})
            order by trade_date
        """
    )
    print(sql_template)

    call_isotonic_regression_analyst(symbol, start_date, end_date, sql_template, x_column, y_column_alias, title)

# 使用示例
if __name__ == "__main__":

    # analyze_gc()
    # analyze_usd_index()
    # analyze_usd_cny()
    # analyze_stock_daily()
    analyze_wti()
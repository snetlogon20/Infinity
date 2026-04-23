from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.modelService.financialAnalysis.PortfolioAnalysis import PortfolioAnalysis


logger = CommonLib.logger
commonLib = CommonLib()

class PortfolioAnalysisTest():

    def prepare_sql(self, start_date=None, end_date=None, sql_type="us_stocks"):
        """
        根据类型生成 SQL 查询语句

        参数:
        - stock_codes: 股票代码列表
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')
        - sql_type: SQL 类型 ['us_stocks', 'us_stocks_gold', 'china_self_selected', 'ai_selected', 'commodities']

        返回:
        - sql: SQL 查询语句
        """
        if sql_type == "us_stocks":
            # stock_codes_str = ','.join([f"'{code}'" for code in stock_codes])
            sql = f"""
                select ts_code, trade_date, close_point
                from df_tushare_us_stock_daily
                where ts_code in ('C', 'JPM', 'NVDA', 'MSFT', 'AAPL')
                AND trade_date >= '{start_date}' and trade_date <='{end_date}'
                order by trade_date asc
            """

        elif sql_type == "us_stocks_gold":
            #stock_codes_str = ','.join([f"'{code}'" for code in stock_codes])
            start_date_formatted = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
            end_date_formatted = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"
            sql = f"""
                SELECT
                    ts_code,
                    trade_date,
                    close_point
                FROM
                (
                    SELECT
                        ts_code,
                        trade_date,
                        close_point
                    FROM df_tushare_us_stock_daily
                    WHERE ts_code IN ('C', 'JPM', 'NVDA', 'MSFT', 'AAPL')
                        AND trade_date >= '{start_date}'
                        AND trade_date <= '{end_date}'
                    UNION DISTINCT
                    SELECT
                        'GC' AS ts_code,
                        replaceAll(toString(date), '-', '') AS trade_date,
                        close AS close_point
                    FROM indexsysdb.df_akshare_futures_foreign_hist
                    WHERE symbol = 'GC'
                        AND date >= '{start_date_formatted}'
                        AND date <= '{end_date_formatted}'
                        AND close > 0
                )
                ORDER BY trade_date, ts_code
            """

        elif sql_type == "china_self_selected":
            sql = f"""
                select
                    ts_code as ts_code,
                    trade_date as trade_date,
                    close as close_point
                from indexsysdb.df_tushare_stock_daily
                where ts_code in
                (
                            '002093.SZ',
                            '600490.SH',
                            '000902.SZ',
                            '601368.SH',
                            '603839.SH',
                            --'000546.SZ',
                            --'600470.SH',
                            '600519.SH',
                            '688498.SH',
                )
                AND
                        trade_date >= '20241001' AND
                        trade_date <= '20261231'
                order by trade_date desc
             """

        elif sql_type == "ai_selected":
            sql = f"""
                select
                    ts_code as ts_code,
                    trade_date as trade_date,
                    close as close_point
                from indexsysdb.df_tushare_stock_daily
                where ts_code in
                (
                            '688585.SH',
                            '605255.SH',
                            '300476.SZ',
                            '301232.SZ',
                            '603226.SH'
                )
                AND
                        trade_date >= '20241001' AND
                        trade_date <= '20261231'
                order by trade_date desc
             """

        elif sql_type == "commodities-gold":
            sql = """
                SELECT
                    symbol as ts_code,
                    replaceAll(toString(date), '-', '') as trade_date,
                    close AS close_point
                FROM indexsysdb.df_akshare_futures_foreign_hist
                WHERE symbol in ('GC','CL','OIL','NG','XAG','XAU','S','W','C','CAD','AHD','SZD','NID')
                    AND close > 0
                    AND date >= '2022-01-01'
                    AND date <= '2026-03-31'
                order by date desc
            """

        elif sql_type == "commodities-nongold":
            sql = """
                SELECT
                    symbol as ts_code,
                    replaceAll(toString(date), '-', '') as trade_date,
                    close AS close_point
                FROM indexsysdb.df_akshare_futures_foreign_hist
                WHERE symbol in ('OIL','NG','S','W','C','CAD','AHD','SZD','NID')
                    AND close > 0
                    AND date >= '2022-01-01'
                    AND date <= '2026-03-31'
                order by date desc
            """

        elif sql_type == "fx":
            sql = """
                select ts_code,trade_date, bid_close as close_point 
                from 
                (
                select ts_code,trade_date, bid_close 
                from indexsysdb.df_tushare_fx_daily
                where ts_code in ('GBPUSD.FXCM','EURUSD.FXCM')
                and trade_date>= '20220101' and trade_date<='20260411' 
                union all
                select ts_code,trade_date, 1/ bid_close as bid_close
                from indexsysdb.df_tushare_fx_daily
                where ts_code in ('USDJPY.FXCM', 'USDCNH.FXCM')
                and trade_date>= '20220101' and trade_date<='20260411' 
                )
                order by trade_date desc, ts_code
             """

        else:
            raise ValueError(
                f"不支持的 SQL 类型: {sql_type}。支持的类型: ['us_stocks', 'us_stocks_gold', 'china_self_selected', 'ai_selected', 'commodities']")

        return sql



if __name__ == "__main__":

    portfolioAnalysisTest = PortfolioAnalysisTest()

    """
        测试案例：选定的美国股票
    """
    # end_date_start = '20260301'  # end_date 起始日期
    # end_date_end = CommonParameters.today   # end_date 结束日期（可根据需要调整）
    # interest_country = "US"  # US, CN
    # sql_type = "us_stocks"  # us_stocks, us_stocks_gold, china_self_selected, ai_selected, commodities

    """
        测试案例：选定的美国股票 + 黄金
    """
    # end_date_start = '20260301'  # end_date 起始日期
    # end_date_end = CommonParameters.today   # end_date 结束日期（可根据需要调整）
    # interest_country = "US"  # US, CN
    # sql_type = "us_stocks_gold"  # us_stocks, us_stocks_gold, china_self_selected, ai_selected, commodities

    """
        测试案例：AI选定的中国股票
    """
    # end_date_start = '20251001'  # end_date 起始日期
    # end_date_end = CommonParameters.today   # end_date 结束日期（可根据需要调整）
    # interest_country = "CN"  # US, CN
    # sql_type = "ai_selected"  # us_stocks, us_stocks_gold, china_self_selected, ai_selected, commodities

    """
        测试案例：人选定的中国股票
    """
    end_date_start = '20260301'  # end_date 起始日期
    end_date_end = CommonParameters.today  # end_date 结束日期（可根据需要调整）
    interest_country = "CN"  # US, CN
    sql_type = "china_self_selected"  # us_stocks, us_stocks_gold, china_self_selected, ai_selected, commodities

    """
        测试案例：美国大宗商品（包括黄金）
    """
    # end_date_start = '20260101'  # end_date 起始日期
    # end_date_end = CommonParameters.today   # end_date 结束日期（可根据需要调整）
    # interest_country = "US"  # US, CN
    # sql_type = "commodities-gold"  # us_stocks, us_stocks_gold, china_self_selected, ai_selected, commodities

    """
        测试案例：美国大宗商品（非黄金）
    """
    # end_date_start = '20260101'  # end_date 起始日期
    # end_date_end = CommonParameters.today   # end_date 结束日期（可根据需要调整）
    # interest_country = "US"  # US, CN
    # sql_type = "commodities-nongold"  # us_stocks, us_stocks_gold, china_self_selected, ai_selected, commodities

    """
        测试案例：外币
    """
    # end_date_start = '20260101'  # end_date 起始日期
    # end_date_end = CommonParameters.today   # end_date 结束日期（可根据需要调整）
    # interest_country = "US"  # US, CN
    # sql_type = "fx"  # us_stocks, us_stocks_gold, china_self_selected, ai_selected, commodities, fx


    """
        总体操控代码如下
    """
    portfolioAnalysis = PortfolioAnalysis()

    # 一键执行完整分析工作流
    all_products_results, all_metrics_results, pdf_path = portfolioAnalysis.execute_full_analysis_workflow(
        end_date_start,
        end_date_end,
        interest_country,
        sql_type,
        portfolioAnalysisTest.prepare_sql
    )

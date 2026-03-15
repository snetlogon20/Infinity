from dataIntegrator.TuShareService.TuShareService import TuShareService
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
import sys
from dataIntegrator.modelService.financialAnalysis.SharpRatio import SharpRatio
from dataIntegrator import CommonLib

logger = CommonLib.logger
commonLib = CommonLib()

class SharpRatioTest(TuShareService):
    def __init__(self):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="SharpRatio started")


def get_sharpe_ratio_of_m1_m2():
    logger.info("""中国 M1/M2 之间的 Sharp Ratio""")

    riskfree_sql = """select m1 as risk_free_rate from indexsysdb.cn_money_supply
                        where trade_date = 
                        (SELECT max(trade_date) FROM indexsysdb.cn_money_supply)"""
    portfolio_sql = "SELECT m2 as close_point FROM indexsysdb.cn_money_supply where trade_date >= '20000101'"

    riskfree_column = 'risk_free_rate'
    portfolio_price_column = 'close_point'

    clickhouClickhouseService = ClickhouseService()
    riskfree_data = clickhouClickhouseService.getDataFrameWithoutColumnsName(riskfree_sql)
    portfolio_data = clickhouClickhouseService.getDataFrameWithoutColumnsName(portfolio_sql)

    sharp_ratio_calculator = SharpRatio()
    sharpe_ratio = sharp_ratio_calculator.calculate_sharpe_ratio_from_data(riskfree_data, portfolio_data, riskfree_column, portfolio_price_column)

def get_sharpe_ratio_of_US_stock(ts_code='C'):
    riskfree_sql = """SELECT 4.5 AS risk_free_rate;"""
    portfolio_sql = """
            select * from indexsysdb.df_tushare_us_stock_daily
            where ts_code = '%s' AND trade_date >= '20240308' and trade_date <='20260308'
        """ % ts_code

    riskfree_column = 'risk_free_rate'
    portfolio_price_column = 'close_point'

    clickhouClickhouseService = ClickhouseService()
    riskfree_data = clickhouClickhouseService.getDataFrameWithoutColumnsName(riskfree_sql)
    portfolio_data = clickhouClickhouseService.getDataFrameWithoutColumnsName(portfolio_sql)

    sharp_ratio_calculator = SharpRatio()
    sharpe_ratio = sharp_ratio_calculator.calculate_sharpe_ratio_from_data(riskfree_data, portfolio_data, riskfree_column, portfolio_price_column)

    return sharpe_ratio

def get_sharpe_ratio_of_CN_stock(ts_code='000902.SZ'):
    riskfree_sql = """SELECT 1.5 AS risk_free_rate;"""
    portfolio_sql = """
            select 
                ts_code,
                trade_date,
                open,
                high,
                low,
                close as close_point,
                pre_close,
                change,
                pct_chg,
                vol,
                amount
            from indexsysdb.df_tushare_stock_daily
            where ts_code = '%s'
       			and trade_date >= '20220101'
       			and trade_date <= '20260307'
            order by trade_date
        """ % ts_code

    riskfree_column = 'risk_free_rate'
    portfolio_price_column = 'close_point'

    clickhouClickhouseService = ClickhouseService()
    riskfree_data = clickhouClickhouseService.getDataFrameWithoutColumnsName(riskfree_sql)
    portfolio_data = clickhouClickhouseService.getDataFrameWithoutColumnsName(portfolio_sql)

    sharp_ratio_calculator = SharpRatio()
    sharpe_ratio = sharp_ratio_calculator.calculate_sharpe_ratio_from_data(riskfree_data, portfolio_data, riskfree_column, portfolio_price_column)

    return sharpe_ratio

def get_sharpe_ratio_of_GC():
    riskfree_sql = """SELECT 4.5 AS risk_free_rate;"""
    portfolio_sql = """
             select 
                 date as trade_date,
                 open,
                 close as close_point,
                 low,
                 high,
                 pct_change 
             from indexsysdb.df_akshare_futures_foreign_hist
             where symbol = 'GC' and date>= '2023-03-08' and date<='2026-03-07'
             order by date 
        """
    riskfree_column = 'risk_free_rate'
    portfolio_price_column = 'close_point'

    clickhouClickhouseService = ClickhouseService()
    riskfree_data = clickhouClickhouseService.getDataFrameWithoutColumnsName(riskfree_sql)
    portfolio_data = clickhouClickhouseService.getDataFrameWithoutColumnsName(portfolio_sql)

    sharp_ratio_calculator = SharpRatio()
    sharpe_ratio = sharp_ratio_calculator.calculate_sharpe_ratio_from_data(riskfree_data, portfolio_data, riskfree_column, portfolio_price_column)

    return sharpe_ratio


if __name__ == "__main__":
    #Example 1.6
    sharp_ratio_caculator = SharpRatio()

    # logger.info("="*10 + "Case 1 " + "="*10)
    # sharpe_ratio_rate = sharp_ratio_caculator.calculate_sharpe_ratio_from_stats(portfolio_mean=10/100, riskfree_mean=3/100, portfolio_sigma=20/100)

    # '''Test the sharpe ration for M1/M2'''
    # logger.info("="*10 + '''Test the sharpe ration for M1/M2''' + "=" * 10)
    # get_sharpe_ratio_of_m1_m2()

    # '''Test the sharpe ration for Citi/Treasury rate'''
    # logger.info("="*10 + '''Test the sharpe ration for Citi/Treasury rate''' + "=" * 10)
    # get_sharpe_ratio_of_US_stock(ts_code='C')

    # '''Test the sharpe ration for JPM/Treasury rate'''
    # logger.info("="*10 + '''Test the sharpe ration for Citi/Treasury rate''' + "=" * 10)
    # get_sharpe_ratio_of_US_stock(ts_code='JPM')

    # '''Test the sharpe ration for Gold-AU/Treasury rate'''
    # logger.info("="*10 + '''Test the sharpe ration for GC/Treasury rate''' + "=" * 10)
    # get_sharpe_ratio_of_GC()

    # '''Test the sharpe ration for 000902.SZ 新洋丰/Treasury rate'''
    # logger.info("="*10 + '''Test the sharpe ration for 000902.SZ 新洋丰/Treasury rate''' + "=" * 10)
    # get_sharpe_ratio_of_CN_stock(ts_code='000902.SZ')

    # '''Test the sharpe ration for 603839.SH 安正时尚/Treasury rate'''
    # logger.info("="*10 + '''Test the sharpe ration for 603839.SH 安正时尚/Treasury rate''' + "=" * 10)
    # get_sharpe_ratio_of_CN_stock(ts_code='603839.SH')

    # '''Test the sharpe ration for 601919.SH 中远海控/Treasury rate'''
    # logger.info("="*10 + '''Test the sharpe ration for 601919.SH 中远海控/Treasury rate''' + "=" * 10)
    # get_sharpe_ratio_of_CN_stock(ts_code='601919.SH')


    '''Test the sharpe ration for 000333.SZ 美的集团/Treasury rate'''
    logger.info("="*10 + '''Test the sharpe ration for 000333.SZ 美的集团/Treasury rate''' + "=" * 10)
    get_sharpe_ratio_of_CN_stock(ts_code='000333.SZ')

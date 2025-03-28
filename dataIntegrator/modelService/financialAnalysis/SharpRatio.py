from dataIntegrator.TuShareService.TuShareService import TuShareService
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
import sys

class SharpRatio(TuShareService):
    def __init__(self):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="SharpRatio started")

    def calculate_sharpe_ratio(self, riskfree_data, portfolio_data, riskfree_column, portfolio_column):

        # Calculate mean and segma for risk-free asset
        riskfree_mean = riskfree_data[riskfree_column].mean()
        riskfree_sigma  = riskfree_data[riskfree_column].std()
        print(f'riskfree_mean={riskfree_mean:.6f}，riskfree_sigma={riskfree_sigma:.6f}')

        # Calculate mean and segma for portfilio asset
        portfolio_mean = portfolio_data[portfolio_column].mean()
        portfolio_sigma  = portfolio_data[portfolio_column].std()
        print(f'portfolio_mean={portfolio_mean:.6f}，portfolio_sigma={portfolio_sigma:.6f}')

        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event=f'riskfree_mean={riskfree_mean:.6f}\nriskfree_sigma={riskfree_sigma:.6f}\nportfolio_mean={portfolio_mean:.6f}\nportfolio_sigma={portfolio_sigma:.6f}' )

        sharpe_ratio = self.caculate_sharp_ratio(portfolio_mean, portfolio_sigma, riskfree_mean)
        return sharpe_ratio

    def caculate_sharp_ratio(self, portfolio_mean, portfolio_sigma, riskfree_mean):
        # Calculate Sharpe Ratio
        sharpe_ratio = (portfolio_mean - riskfree_mean) / portfolio_sigma
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event=f'sharpe_ratio={sharpe_ratio:.6f}')
        return  sharpe_ratio


def get_sharptratio_of_m1_m2():
    riskfree_sql = """select m1 from indexsysdb.cn_money_supply
                        where trade_date = 
                        (SELECT max(trade_date) FROM indexsysdb.cn_money_supply)"""
    portfolio_sql = "SELECT m2 FROM indexsysdb.cn_money_supply where trade_date >= '20000101'"
    riskfree_columns = ["m1"]
    portfolio_columns = ["m2"]
    riskfree_column = "m1"
    portfolio_column = "m2"
    clickhouClickhouseService = ClickhouseService()
    riskfree_data = clickhouClickhouseService.getDataFrame(riskfree_sql, riskfree_columns)
    portfolio_data = clickhouClickhouseService.getDataFrame(portfolio_sql, portfolio_columns)
    sharp_ratio_calculator = SharpRatio()
    sharpe_ratio = sharp_ratio_calculator.calculate_sharpe_ratio(riskfree_data, portfolio_data, riskfree_column, portfolio_column)
    return sharpe_ratio

def get_sharptratio_of_citi():
    riskfree_sql = """SELECT 4.5 AS risk_free_rate;"""
    portfolio_sql = """select pct_change from indexsysdb.df_tushare_us_stock_daily
where ts_code = 'C' AND trade_date >= '20220101' and trade_date <='20241013'"""
    riskfree_columns = ["risk_free_rate"]
    portfolio_columns = ["pct_change"]
    riskfree_column = "risk_free_rate"
    portfolio_column = "pct_change"
    clickhouClickhouseService = ClickhouseService()
    riskfree_data = clickhouClickhouseService.getDataFrame(riskfree_sql, riskfree_columns)
    portfolio_data = clickhouClickhouseService.getDataFrame(portfolio_sql, portfolio_columns)
    sharp_ratio_calculator = SharpRatio()
    sharpe_ratio = sharp_ratio_calculator.calculate_sharpe_ratio(riskfree_data, portfolio_data, riskfree_column, portfolio_column)
    return sharpe_ratio

if __name__ == "__main__":
    #Example 1.6
    sharp_ratio_caculator = SharpRatio()
    sharpe_ratio_rate = (sharp_ratio_caculator.caculate_sharp_ratio
     (portfolio_mean=10/100, riskfree_mean=3/100, portfolio_sigma=20/100))

    '''Test the sharpe ration for M1/M2'''
    get_sharptratio_of_m1_m2()
    '''Test the sharpe ration for Citi/Treasury rate'''
    get_sharptratio_of_citi()

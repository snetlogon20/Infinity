import pandas
import matplotlib.pyplot as plt  # 添加 matplotlib.pyplot 导入
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.modelService.MonteCarlo.MonteCarloRandom import MonteCarloRandom


class MonteCarloRandomManager:

    def init(cls):
        pandas.set_option('display.max_rows', None)  # 设置打印所有行
        pandas.set_option('display.max_columns', None)  # 设置打印所有列
        pandas.set_option('display.width', None)  # 自动检测控制台的宽度
        pandas.set_option('display.max_colwidth', None)  # 设置列的最大宽度

    '''
    封装单线 正态分布算法
    '''
    @classmethod
    def caculate_monte_carlo_single_line_normal_distribute(cls, S, u, segma, t, times):
        monteCarloRandom = MonteCarloRandom()
        return monteCarloRandom.caculate_monte_carlo_single_line_normal_distribute(S, u, segma, t, times)

    '''
    封装单线 log分布算法
    '''
    @classmethod
    def caculate_monte_carlo_single_line_lognormal_distribute(cls, S, u, segma, t, times):
        monteCarloRandom = MonteCarloRandom()
        return monteCarloRandom.caculate_monte_carlo_single_line_lognormal_distribute(S, u, segma, t, times)

    '''
    封装多线 算法
    '''
    @classmethod
    def simulation_multi_series(cls, dataFrame, simulat_params):
        monteCarloRandom = MonteCarloRandom()
        return monteCarloRandom.simulation_multi_series(dataFrame, simulat_params)


    @classmethod
    def get_tushare_stock_dataset(cls, market, stock, start_date, end_date):
        if market == "US":
            sql = rf"""
                    select ts_code,
                            trade_date,
                            close_point,
                            open_point,
                            high_point,
                            low_point,
                            pre_close,
                            change_point,
                            pct_change,
                            vol,
                            amount,
                            vwap,
                            turnover_ratio,
                            total_mv,
                            pe,
                            pb
                    from indexsysdb.df_tushare_us_stock_daily
                    where ts_code = '{stock}' AND 
                    trade_date>= '{start_date}' and 
                    trade_date <='{end_date}'
                        """

        if market == "CN":
            sql = rf"""
                    select 
                        ts_code,
                        trade_date,
                        open,
                        high,
                        low,
                        close,
                        pre_close,
                        change,
                        pct_chg,
                        vol,
                        amount
                    from indexsysdb.df_tushare_stock_daily
                    where ts_code = '{stock}' AND
                            trade_date >= '{start_date}' AND 
                            trade_date <= '{end_date}'
                    order by trade_date
                        """

        clickhouseService = ClickhouseService()
        dataFrame = clickhouseService.getDataFrameWithoutColumnsName(sql)

        if market == "US":
            ax_line = dataFrame.plot.line(x='trade_date', y='close_point')
            ax_scatter = dataFrame.plot.scatter(x='trade_date', y='pct_change')

        elif market == "CN":
            ax_line = dataFrame.plot.line(x='trade_date', y='close')
            ax_scatter = dataFrame.plot.scatter(x='trade_date', y='pct_chg')

        ax_line.set_title(rf'Stock Close Point: {market}-{stock} Between:{start_date} ~ {end_date}')
        ax_scatter.set_title(rf'Stock Change Volatility: {market}-{stock} Between:{start_date} ~ {end_date}')

        return dataFrame

    @classmethod
    def get_akshare_gold_dataset(cls, market, stock, start_date, end_date):

        sql = rf"""
                select 
                    date,
                    open,
                    close,
                    low,
                    high,
                    pct_change 
                from indexsysdb.df_akshare_spot_hist_sge
                order by date 
                """

        clickhouseService = ClickhouseService()
        dataFrame = clickhouseService.getDataFrameWithoutColumnsName(sql)

        ax_line = dataFrame.plot.line(x='date', y='close')
        ax_scatter = dataFrame.plot.scatter(x='date', y='close')

        ax_line.set_title(rf'Stock Close Point: {market}-{stock} Between:{start_date} ~ {end_date}')
        ax_scatter.set_title(rf'Stock Change Volatility: {market}-{stock} Between:{start_date} ~ {end_date}')

        return dataFrame
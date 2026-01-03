import pandas
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

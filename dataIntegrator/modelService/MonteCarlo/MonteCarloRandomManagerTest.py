from dataIntegrator.analysisService.InquiryManager import InquiryManager
from dataIntegrator.modelService.MonteCarlo.MonteCarloRandomManager import MonteCarloRandomManager
from dataIntegrator.utility.FileUtility import FileUtility

class MonteCarloRandomTest:
    @classmethod
    def test_single_line_normal_distribute(self):
        """测试单线模拟 - normal_distribute"""
        monteCarloRandomManager = MonteCarloRandomManager()
        S, u, segma, t, times = 100, 0.1, 0.2, 0.01, 10
        x, y = monteCarloRandomManager.caculate_monte_carlo_single_line_normal_distribute(S, u, segma, t, times)
        return x, y

    def test_single_line_lognormal_distribute(self):
        """测试单线模拟 - lognormal_distribute"""
        monteCarloRandomManager = MonteCarloRandomManager()
        S, u, segma, t, times = 100, 0.1, 0.2, 0.01, 10
        x, y = monteCarloRandomManager.caculate_monte_carlo_single_line_lognormal_distribute(S, u, segma, t, times)
        return x, y

    def test_multi_series_normal_distribution_citi(self):
        """多线模拟 - Normal Distribution - 花旗股票"""
        monteCarloRandomManager = MonteCarloRandomManager()
        inquiryManager = InquiryManager()
        dataFrame = inquiryManager.get_tushare_stock_dataset("US", "C", "20240101", "20241207")

        simulat_params = {
            'init_value': 'close_point',
            'analysis_column': 'pct_change',
            't': 0.01,
            'times': 10,
            'series': 1000,
            'alpha': 0.05,
            'distribution_type': 'normal'  # normal/lognormal/historical
        }
        all_line_df, all_lines, stats, var_lower_bound, var_upper_bound = monteCarloRandomManager.simulation_multi_series(dataFrame, simulat_params)
        monteCarloRandomManager.draw_plot(all_lines, simulat_params, stats, var_lower_bound, var_upper_bound)

        # 写入excel
        file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_normal", "xlsx")
        all_line_df.to_excel(file_full_name)
        return all_line_df

    def test_multi_series_lognormal_distribution_citi(self):
        """多线模拟 - LogNormal Distribution - 花旗股票"""
        monteCarloRandomManager = MonteCarloRandomManager()
        inquiryManager = InquiryManager()
        dataFrame = inquiryManager.get_tushare_stock_dataset("US", "C", "20240101", "20241207")

        simulat_params = {
            'init_value': 'close_point',
            'analysis_column': 'pct_change',
            't': 0.01,
            'times': 10,
            'series': 1000,
            'alpha': 0.05,
            'distribution_type': 'lognormal'  # normal/lognormal/historical
        }
        all_line_df, all_lines, stats, var_lower_bound, var_upper_bound = monteCarloRandomManager.simulation_multi_series(dataFrame, simulat_params)
        monteCarloRandomManager.draw_plot(all_lines, simulat_params, stats, var_lower_bound, var_upper_bound)

        # 写入excel
        file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_lognormal", "xlsx")
        all_line_df.to_excel(file_full_name)
        return all_line_df

    def test_multi_series_lognormal_distribution_jpm(self):
        """多线模拟 - LogNormal Distribution - 摩根股票"""
        monteCarloRandomManager = MonteCarloRandomManager()
        inquiryManager = InquiryManager()
        dataFrame = inquiryManager.get_tushare_stock_dataset("US", "JPM", "20240101", "20241207")

        simulat_params = {
            'init_value': 'close_point',
            'analysis_column': 'pct_change',
            't': 0.01,
            'times': 10,
            'series': 1000,
            'alpha': 0.05,
            'distribution_type': 'lognormal'  # normal/lognormal/historical
        }
        all_line_df, all_lines, stats, var_lower_bound, var_upper_bound = monteCarloRandomManager.simulation_multi_series(dataFrame, simulat_params)
        monteCarloRandomManager.draw_plot(all_lines, simulat_params, stats, var_lower_bound, var_upper_bound)

        # 写入excel
        file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_lognormal", "xlsx")
        all_line_df.to_excel(file_full_name)
        return all_line_df

    def test_multi_series_lognormal_distribution_pudong_2022(self):
        """多线模拟 - LogNormal Distribution - 浦发 - 20220101 ~ 20221207"""
        monteCarloRandomManager = MonteCarloRandomManager()
        inquiryManager = InquiryManager()
        dataFrame = inquiryManager.get_tushare_stock_dataset("CN", "600000.SH", "20220101", "20221207")

        simulat_params = {
            'init_value': 'close',
            'analysis_column': 'pct_chg',
            't': 0.01,
            'times': 10,
            'series': 1000,
            'alpha': 0.05,
            'distribution_type': 'lognormal'  # normal/lognormal/historical
        }
        all_line_df, all_lines, stats, var_lower_bound, var_upper_bound = monteCarloRandomManager.simulation_multi_series(dataFrame, simulat_params)
        monteCarloRandomManager.draw_plot(all_lines, simulat_params, stats, var_lower_bound, var_upper_bound)

        # 写入excel
        file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_lognormal", "xlsx")
        all_line_df.to_excel(file_full_name)
        return all_line_df

    def test_multi_series_lognormal_distribution_pudong_2024(self):
        """多线模拟 - LogNormal Distribution - 浦发 - 20240101 ~ 20241207"""
        monteCarloRandomManager = MonteCarloRandomManager()
        inquiryManager = InquiryManager()
        dataFrame = inquiryManager.get_tushare_stock_dataset("CN", "600000.SH", "20241001", "20241207")

        simulat_params = {
            'init_value': 'close',
            'analysis_column': 'pct_chg',
            't': 0.01,
            'times': 10,
            'series': 1000,
            'alpha': 0.05,
            'distribution_type': 'lognormal'  # normal/lognormal/historical
        }
        all_line_df, all_lines, stats, var_lower_bound, var_upper_bound = monteCarloRandomManager.simulation_multi_series(dataFrame, simulat_params)
        monteCarloRandomManager.draw_plot(all_lines, simulat_params, stats, var_lower_bound, var_upper_bound)

        # 写入excel
        file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_lognormal", "xlsx")
        all_line_df.to_excel(file_full_name)
        return all_line_df

    def test_multi_series_lognormal_distribution_lvcw(self):
        """多线模拟 - LogNormal Distribution - 绿城水务 - 20240101 ~ 20241207"""
        monteCarloRandomManager = MonteCarloRandomManager()
        inquiryManager = InquiryManager()

        simulat_params = {
            'market': 'CN', 'stock': '601368.SH',
            'start_date': '20241001', 'end_date': '20241207',
            'init_value': 'close',
            'analysis_column': 'pct_chg',
            't': 0.01,
            'times': 10,
            'series': 1000,
            'alpha': 0.05,
            'distribution_type': 'lognormal'  # normal/lognormal/historical
        }
        dataFrame = inquiryManager.get_tushare_stock_dataset(simulat_params['market'], simulat_params['stock'], simulat_params['start_date'],
                                     simulat_params['end_date'])

        all_line_df, all_lines, stats, var_lower_bound, var_upper_bound = monteCarloRandomManager.simulation_multi_series(dataFrame, simulat_params)
        monteCarloRandomManager.draw_plot(all_lines, simulat_params, stats, var_lower_bound, var_upper_bound)
        # 写入excel
        file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_lognormal", "xlsx")
        all_line_df.to_excel(file_full_name)
        return all_line_df

    @classmethod
    def test_multi_stock_multi_series_lognormal_distribution(self):

        simulat_params_list = [
            {
                'market': 'CN', 'stock': '603839.SH',
                'start_date': '20241001', 'end_date': '20241213',
                'init_value': 'close',
                'analysis_column': 'pct_chg',
                't': 0.01,
                'times': 10,
                'series': 1000,
                'alpha': 0.05,
                'distribution_type': 'historical'  # normal/lognormal/historical
            },
            {
                'market': 'CN', 'stock': '000902.SZ',
                'start_date': '20241001', 'end_date': '20241207',
                'init_value': 'close',
                'analysis_column': 'pct_chg',
                't': 0.01,
                'times': 10,
                'series': 1000,
                'alpha': 0.05,
                'distribution_type': 'lognormal'  # normal/lognormal/historical
            },
            {
                'market': 'CN', 'stock': '002093.SZ',
                'start_date': '20241001', 'end_date': '20241207',
                'init_value': 'close',
                'analysis_column': 'pct_chg',
                't': 0.01,
                'times': 10,
                'series': 1000,
                'alpha': 0.05,
                'distribution_type': 'lognormal'  # normal/lognormal/historical
            },
            {
                'market': 'CN', 'stock': '600490.SH',
                'start_date': '20241001', 'end_date': '20241207',
                'init_value': 'close',
                'analysis_column': 'pct_chg',
                't': 0.01,
                'times': 10,
                'series': 1000,
                'alpha': 0.05,
                'distribution_type': 'lognormal'  # normal/lognormal/historical
            },
            {
                'market': 'CN', 'stock': '601368.SH',
                'start_date': '20241001', 'end_date': '20241207',
                'init_value': 'close',
                'analysis_column': 'pct_chg',
                't': 0.01,
                'times': 10,
                'series': 1000,
                'alpha': 0.05,
                'distribution_type': 'lognormal'  # normal/lognormal/historical
            },
            {
                'market': 'US', 'stock': 'C',
                'start_date': '20221001', 'end_date': '20241119',
                'init_value': 'close_point',
                'analysis_column': 'pct_change',
                't': 0.01,
                'times': 2,
                'series': 10000,
                'alpha': 0.05,
                'distribution_type': 'historical'  # normal/lognormal/historical
            },
            {
                'market': 'US', 'stock': 'JPM',
                'start_date': '20241001', 'end_date': '20241207',
                'init_value': 'close_point',
                'analysis_column': 'pct_change',
                't': 0.01,
                'times': 10,
                'series': 1000,
                'alpha': 0.05,
                'distribution_type': 'lognormal'  # normal/lognormal/historical
            },
            {
                'market': 'CN', 'stock': '600000.SH',
                'start_date': '20241001', 'end_date': '20241207',
                'init_value': 'close',
                'analysis_column': 'pct_chg',
                't': 0.01,
                'times': 10,
                'series': 1000,
                'alpha': 0.05,
                'distribution_type': 'lognormal'  # normal/lognormal/historical
            },
        ]

        results = []

        for simulat_params in simulat_params_list:
            monteCarloRandomManager = MonteCarloRandomManager()
            inquiryManager = InquiryManager()

            dataFrame = inquiryManager.get_tushare_stock_dataset(simulat_params['market'], simulat_params['stock'],
                                                            simulat_params['start_date'],
                                                            simulat_params['end_date'])
            all_line_df, all_lines, stats, var_lower_bound, var_upper_bound = monteCarloRandomManager.simulation_multi_series(
                dataFrame, simulat_params)
            monteCarloRandomManager.draw_plot(all_lines, simulat_params, stats, var_lower_bound, var_upper_bound)
            # 写入excel
            file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_lognormal", "xlsx")
            all_line_df.to_excel(file_full_name)
            results.append(all_line_df)

    def test_multi_series_lognormal_distribution_sge(self):
        """多线模拟 - LogNormal Distribution - Gold"""
        monteCarloRandomManager = MonteCarloRandomManager()
        inquiryManager = InquiryManager()
        dataFrame = inquiryManager.get_akshare_gold_dataset("US", "JPM", "20240101", "20241207")

        simulat_params = {
            'init_value': 'close',
            'analysis_column': 'pct_change',
            't': 0.01,
            'times': 30,
            'series': 1000,
            'alpha': 0.05,
            'distribution_type': 'lognormal'  # normal/lognormal/historical
        }
        all_line_df, all_lines, stats, var_lower_bound, var_upper_bound = monteCarloRandomManager.simulation_multi_series(dataFrame, simulat_params)
        monteCarloRandomManager.draw_plot(all_lines, simulat_params, stats, var_lower_bound, var_upper_bound)

        # 写入excel
        file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_lognormal", "xlsx")
        all_line_df.to_excel(file_full_name)
        return all_line_df

    def test_multi_series_lognormal_distribution_treasury_yield(self):
        """多线模拟 - LogNormal Distribution - Gold"""
        monteCarloRandomManager = MonteCarloRandomManager()
        inquiryManager = InquiryManager()
        dataFrame = inquiryManager.get_akshare_treasury_yield_dataset("US", "JPM", "20240101", "20241207")

        simulat_params = {
            'init_value': 'm1',
            'analysis_column': 'pct_change',
            't': 0.01,
            'times': 30,
            'series': 1000,
            'alpha': 0.05,
            'distribution_type': 'lognormal'  # normal/lognormal/historical
        }
        all_line_df, all_lines, stats, var_lower_bound, var_upper_bound = monteCarloRandomManager.simulation_multi_series(dataFrame, simulat_params)
        monteCarloRandomManager.draw_plot(all_lines, simulat_params, stats, var_lower_bound, var_upper_bound)

        # 写入excel
        file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_lognormal", "xlsx")
        all_line_df.to_excel(file_full_name)
        return all_line_df

if __name__ == "__main__":
    monteCarloTest = MonteCarloRandomTest()

    # 执行各个测试案例
    # monteCarloTest.test_single_line_normal_distribute()
    monteCarloTest.test_single_line_lognormal_distribute()
    # monteCarloTest.test_multi_series_normal_distribution_citi()
    # monteCarloTest.test_multi_series_lognormal_distribution_citi()
    # monteCarloTest.test_multi_series_lognormal_distribution_jpm()
    # monteCarloTest.test_multi_series_lognormal_distribution_pudong_2022()
    # monteCarloTest.test_multi_series_lognormal_distribution_pudong_2024()
    # monteCarloTest.test_multi_series_lognormal_distribution_lvcw()
    # monteCarloTest.test_multi_stock_multi_series_lognormal_distribution()

    monteCarloTest.test_multi_series_lognormal_distribution_sge()
    # monteCarloTest.test_multi_series_lognormal_distribution_treasury_yield()

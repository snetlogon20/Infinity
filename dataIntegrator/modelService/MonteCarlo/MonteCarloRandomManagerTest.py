from dataIntegrator import CommonParameters, CommonLib
from dataIntegrator.analysisService.InquiryManager import InquiryManager
from dataIntegrator.modelService.MonteCarlo.MonteCarloRandomAssistant import MonteCarloRandomAssistant
from dataIntegrator.modelService.MonteCarlo.MonteCarloRandomManager import MonteCarloRandomManager
from dataIntegrator.modelService.commonService.CalendarService import CalendarService
from dataIntegrator.utility.FileUtility import FileUtility
from datetime import datetime, timedelta
import pandas as pd

logger = CommonLib.logger
commonLib = CommonLib()

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

        sql = """
                select 
                    date,
                    open,
                    close,
                    low,
                    high,
                    pct_change 
                from indexsysdb.df_akshare_spot_hist_sge
                where date >= '2025-01-01' and date <= '2026-02-14'
                order by date"""
        inquiryManager = InquiryManager()
        dataFrame = inquiryManager.get_sql_dataset(sql)

        simulat_params = {
            'init_value': 'close',
            'analysis_column': 'pct_change',
            't': 0.01,
            'times': 10,
            'series': 5000,
            'alpha': 0.05,
            'distribution_type': 'lognormal'  # normal/lognormal/historical
        }
        all_line_df, all_lines, stats, var_lower_bound, var_upper_bound, average, median_value = monteCarloRandomManager.simulation_multi_series(dataFrame, simulat_params)
        monteCarloRandomManager.draw_plot(all_lines, simulat_params, stats, var_lower_bound, var_upper_bound, average, median_value)

        # 写入excel
        file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_lognormal", "xlsx")
        all_line_df.to_excel(file_full_name)
        return all_line_df

    def test_multi_series_historical_distribution_sge(self):
        """多线模拟 - LogNormal Distribution - Gold"""
        monteCarloRandomManager = MonteCarloRandomManager()
        inquiryManager = InquiryManager()
        sql = """
                select 
                    date,
                    open,
                    close,
                    low,
                    high,
                    pct_change 
                from indexsysdb.df_akshare_spot_hist_sge
                where date >= '2025-01-01' and date <= '2026-02-14'
                order by date"""
        inquiryManager = InquiryManager()
        dataFrame = inquiryManager.get_sql_dataset(sql)
        print(dataFrame)

        simulat_params = {
            'init_value': 'close',
            'analysis_column': 'pct_change',
            't': 0.01,
            'times': 10,
            'series': 5000,
            'alpha': 0.05,
            'distribution_type': 'historical'  # normal/lognormal/historical
        }
        all_line_df, all_lines, stats, var_lower_bound, var_upper_bound, average, median_value = monteCarloRandomManager.simulation_multi_series(dataFrame, simulat_params)
        monteCarloRandomManager.draw_plot(all_lines, simulat_params, stats, var_lower_bound, var_upper_bound, average, median_value)

        # 写入excel
        file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_lognormal", "xlsx")
        all_line_df.to_excel(file_full_name)
        return all_line_df

    def test_multi_series_historical_distribution_sge_rolling(self):
        """多线模拟 - LogNormal Distribution - Gold"""
        monteCarloRandomManager = MonteCarloRandomManager()
        inquiryManager = InquiryManager()

        # start_date = datetime.strptime('2025-01-01', '%Y-%m-%d')
        start_date = datetime.strptime('2025-11-01', '%Y-%m-%d')
        formatted_start_date = start_date.strftime('%Y-%m-%d')
        #end_date = '2025-02-13'
        # end_date = '2025-12-31'
        # end_date = '2026-02-27'
        end_date = CommonParameters.today

        analysis_column = 'close'
        analysis_column_label = '收盘价'
        limit_date = 600
        next_n_working_days = 10

        results_df = pd.DataFrame(columns=['trade_date', 'var_lower_bound', 'var_upper_bound', 'average', 'median_value'])
        sql = f"select date as trade_date,open,close,low,high,pct_change from indexsysdb.df_akshare_spot_hist_sge where date>='{formatted_start_date}' and date<='{end_date}' order by date "
        original_dataFrame = inquiryManager.get_sql_dataset(sql)
        original_dataFrame.to_excel(rf"D:\workspace_python\infinity_data\data\outbound\original_dataFrame.xlsx")

        sql = f"select date as trade_date from indexsysdb.df_akshare_spot_hist_sge where date>='{formatted_start_date}' and date<='{end_date}' order by date "
        loop_date_dataFrame = inquiryManager.get_sql_dataset(sql)

        sql = f"select date as trade_date,open,close,low,high,pct_change from indexsysdb.df_akshare_spot_hist_sge where date>='{formatted_start_date}' order by date "
        past_calendar_dataFrame = inquiryManager.get_sql_dataset(sql)

        for index, row in loop_date_dataFrame.iterrows():
            current_date = row['trade_date']
            sample_end_date = current_date

            print(f"formatted_start_date: {formatted_start_date}")
            print(f"current_date: {current_date}")
            print(f"end_date: {end_date}")
            print(f"sample_end_date: {sample_end_date}")

            # 格式化当前日期为字符串
            #formatted_date = current_date.strftime('%Y-%m-%d')
            formatted_date = current_date

            # 在这里执行你需要的操作，例如查询数据库或处理数据
            print(f"Processing date: {formatted_date}")
            sql = f"""
                    select *
                    from 
                    (
                        select 
                            date as trade_date,
                            open,
                            close,
                            low,
                            high,
                            pct_change 
                        from indexsysdb.df_akshare_spot_hist_sge
                        where date <= '{sample_end_date}'
                    order by trade_date desc
                    limit {limit_date}
                    )
                    order by trade_date
                """
            print(sql)

            dataFrame = inquiryManager.get_sql_dataset(sql)

            if dataFrame.empty:
                print(f"No data found for date: {formatted_date}")
                current_date += timedelta(days=1)
                continue  # 跳过当前循环

            simulat_params = {
                'init_value': 'close',
                'analysis_column': 'pct_change',
                't': 0.01,
                'times': next_n_working_days,
                'series': 5000,
                #'alpha': 0.05,
                'alpha': 0.30,
                'distribution_type': 'historical'  # normal/lognormal/historical
            }
            all_line_df, all_lines, stats, var_lower_bound, var_upper_bound, average, median_value = monteCarloRandomManager.simulation_multi_series(dataFrame, simulat_params)

            calendarService = CalendarService()
            last_date = (calendarService.find_data_by_given_dataframe_and_date_offset
                         (past_calendar_dataFrame, current_date, next_n_working_days))
            print(f"current_date:{current_date}, last date: {last_date} ============================================================> ")
            if last_date is None:
                print(f"No next working day found for date: {current_date}")

            # 将结果添加到 DataFrame 中
            new_row = pd.DataFrame([{
                'trade_date': formatted_date,
                'predict_date': last_date,
                'var_lower_bound': var_lower_bound,
                'var_upper_bound': var_upper_bound,
                'average': average,
                'median_value': median_value
            }])
            print(new_row)
            results_df = pd.concat([results_df, new_row], ignore_index=True)

            if current_date > end_date:
                print(f"current_date: {current_date}")
                print(f"end_date: {end_date}")
                break

        print(results_df)

        """
            整理需要输出的 dataframe
            输入参数: original_dataFrame - 带日期的业务历史数据, results_df - 带日期的预测数据
            步骤： 
                1. 筛选出原始数据中包含的日期 
                2. Calendar date join history data 
                3. Calendar date join the forecast data
            输出：拼接后的字段
        """
        monteCarloRandomAssistant = MonteCarloRandomAssistant()
        final_result = monteCarloRandomAssistant.generate_forecast_dataframes(original_dataFrame, results_df)

        final_result_copy = monteCarloRandomAssistant.select_required_columns(final_result, analysis_column)

        monteCarloRandomAssistant.save_file_to_excel(final_result_copy)

        monteCarloRandomAssistant.draw_plot(final_result_copy, analysis_column, analysis_column_label)

        return


    def test_multi_series_lognormal_distribution_sge_pctchange(self):
        """多线模拟 - LogNormal Distribution - Gold"""
        monteCarloRandomManager = MonteCarloRandomManager()
        inquiryManager = InquiryManager()
        sql = """
                select 
                    date,
                    open,
                    close,
                    low,
                    high,
                    pct_change 
                from indexsysdb.df_akshare_spot_hist_sge
                where date >= '2025-01-01' and date <= '2026-02-14'
                order by date"""
        inquiryManager = InquiryManager()
        dataFrame = inquiryManager.get_sql_dataset(sql)
        simulat_params = {
            'init_value': 'pct_change',
            'analysis_column': 'pct_change',
            't': 0.01,
            'times': 10,
            'series': 5000,
            'alpha': 0.05,
            'distribution_type': 'lognormal'  # normal/lognormal/historical
        }
        all_line_df, all_lines, stats, var_lower_bound, var_upper_bound, average, median_value = monteCarloRandomManager.simulation_multi_series(dataFrame, simulat_params)
        monteCarloRandomManager.draw_plot(all_lines, simulat_params, stats, var_lower_bound, var_upper_bound, average, median_value)

        # 写入excel
        file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_lognormal", "xlsx")
        all_line_df.to_excel(file_full_name)
        return all_line_df

    def test_multi_series_historical_distribution_sge_pctchange(self):
        """多线模拟 - LogNormal Distribution - Gold"""
        monteCarloRandomManager = MonteCarloRandomManager()
        inquiryManager = InquiryManager()
        sql = """
                select 
                    date,
                    open,
                    close,
                    low,
                    high,
                    pct_change 
                from indexsysdb.df_akshare_spot_hist_sge
                where date >= '2025-01-01' and date <= '2026-02-14'
                order by date"""
        inquiryManager = InquiryManager()
        dataFrame = inquiryManager.get_sql_dataset(sql)

        simulat_params = {
            'init_value': 'pct_change',
            'analysis_column': 'pct_change',
            't': 0.01,
            'times': 10,
            'series': 5000,
            'alpha': 0.05,
            'distribution_type': 'historical'  # normal/lognormal/historical
        }
        all_line_df, all_lines, stats, var_lower_bound, var_upper_bound, average, median_value = monteCarloRandomManager.simulation_multi_series(dataFrame, simulat_params)
        monteCarloRandomManager.draw_plot(all_lines, simulat_params, stats, var_lower_bound, var_upper_bound, average, median_value)

        # 写入excel
        file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_lognormal", "xlsx")
        all_line_df.to_excel(file_full_name)
        return all_line_df

    def test_multi_series_historical_distribution_sge_pct_change_rolling(self):
        """多线模拟 - Historical Distribution - Gold - pct_change - Rolling"""
        monteCarloRandomManager = MonteCarloRandomManager()
        inquiryManager = InquiryManager()

        start_date = datetime.strptime('2025-11-01', '%Y-%m-%d')
        formatted_start_date = start_date.strftime('%Y-%m-%d')
        end_date = CommonParameters.today

        analysis_column = 'pct_change'
        analysis_column_label = '涨跌幅'
        limit_date = 600
        next_n_working_days = 10

        results_df = pd.DataFrame(columns=['trade_date', 'var_lower_bound', 'var_upper_bound', 'average', 'median_value'])
        sql = f"select date as trade_date,open,close,low,high,pct_change from indexsysdb.df_akshare_spot_hist_sge where date>='{formatted_start_date}' and date<='{end_date}' order by date "
        original_dataFrame = inquiryManager.get_sql_dataset(sql)
        original_dataFrame.to_excel(rf"D:\workspace_python\infinity_data\data\outbound\original_dataFrame.xlsx")

        sql = f"select date as trade_date from indexsysdb.df_akshare_spot_hist_sge where date>='{formatted_start_date}' and date<='{end_date}' order by date "
        loop_date_dataFrame = inquiryManager.get_sql_dataset(sql)

        sql = f"select date as trade_date,open,close,low,high,pct_change from indexsysdb.df_akshare_spot_hist_sge where date>='{formatted_start_date}' order by date "
        past_calendar_dataFrame = inquiryManager.get_sql_dataset(sql)

        for index, row in loop_date_dataFrame.iterrows():
            current_date = row['trade_date']
            sample_end_date = current_date

            print(f"formatted_start_date: {formatted_start_date}")
            print(f"current_date: {current_date}")
            print(f"end_date: {end_date}")
            print(f"sample_end_date: {sample_end_date}")

            formatted_date = current_date

            print(f"Processing date: {formatted_date}")
            sql = f"""
                    select *
                    from 
                    (
                        select 
                            date as trade_date,
                            open,
                            close,
                            low,
                            high,
                            pct_change 
                        from indexsysdb.df_akshare_spot_hist_sge
                        where date <= '{sample_end_date}'
                    order by trade_date desc
                    limit {limit_date}
                    )
                    order by trade_date
                """
            print(sql)

            dataFrame = inquiryManager.get_sql_dataset(sql)

            if dataFrame.empty:
                print(f"No data found for date: {formatted_date}")
                current_date += timedelta(days=1)
                continue

            simulat_params = {
                'init_value': 'pct_change',
                'analysis_column': 'pct_change',
                't': 0.01,
                'times': next_n_working_days,
                'series': 5000,
                'alpha': 0.30,
                'distribution_type': 'historical'
            }
            all_line_df, all_lines, stats, var_lower_bound, var_upper_bound, average, median_value = monteCarloRandomManager.simulation_multi_series(dataFrame, simulat_params)

            calendarService = CalendarService()
            last_date = (calendarService.find_data_by_given_dataframe_and_date_offset
                         (past_calendar_dataFrame, current_date, next_n_working_days))
            print(f"current_date:{current_date}, last date: {last_date} ============================================================> ")
            if last_date is None:
                print(f"No next working day found for date: {current_date}")

            new_row = pd.DataFrame([{
                'trade_date': formatted_date,
                'predict_date': last_date,
                'var_lower_bound': var_lower_bound,
                'var_upper_bound': var_upper_bound,
                'average': average,
                'median_value': median_value
            }])
            print(new_row)
            results_df = pd.concat([results_df, new_row], ignore_index=True)

            if current_date > end_date:
                print(f"current_date: {current_date}")
                print(f"end_date: {end_date}")
                break

        print(results_df)

        monteCarloRandomAssistant = MonteCarloRandomAssistant()
        final_result = monteCarloRandomAssistant.generate_forecast_dataframes(original_dataFrame, results_df)

        final_result_copy = monteCarloRandomAssistant.select_required_columns(final_result, analysis_column)

        monteCarloRandomAssistant.save_file_to_excel(final_result_copy)

        monteCarloRandomAssistant.draw_plot(final_result_copy, analysis_column, analysis_column_label)

        return

    def test_multi_series_historical_distribution_GC_rolling_bak(
            self,
            symbol='GC',
            start_date='2025-04-01',
            end_date=None,
            analysis_column='close',
            analysis_column_label='收盘价',
            limit_date=600,
            next_n_working_days=5,
            monte_carlo_params=None,
            output_path=None,
            get_original_data_sql=None,
            get_trade_date_sql=None,
            get_past_calendar_sql=None,
            monteCarlo_simulation_sql_template=None

    ):
        """
        多线模拟 - Historical Distribution - Rolling Window 通用方法

        Args:
            symbol (str): 交易标的代码，默认 'GC'
            start_date (str): 开始日期，格式 'YYYY-MM-DD'，默认 '2025-04-01'
            end_date (str): 结束日期，格式 'YYYY-MM-DD'，默认使用 CommonParameters.today
            analysis_column (str): 分析列名，默认 'close'
            analysis_column_label (str): 分析列标签，默认 '收盘价'
            limit_date (int): 滚动窗口历史数据天数，默认 600
            next_n_working_days (int): 预测未来工作日天数，默认 5
            monte_carlo_params (dict): 蒙特卡洛模拟参数，默认 None 时使用内置配置
            output_path (str): Excel 输出路径，默认 None 时自动生成

        Returns:
            tuple: (final_result, results_df, original_dataFrame) 最终结果 DataFrame、滚动结果 DataFrame、原始数据 DataFrame
        """
        # Step 0 初始化
        monteCarloRandomManager = MonteCarloRandomManager()
        inquiryManager = InquiryManager()

        # 处理默认参数
        if end_date is None:
            from dataIntegrator.common.CommonParameters import CommonParameters
            end_date = CommonParameters.today

        start_date_dt = datetime.strptime(start_date, '%Y-%m-%d')
        formatted_start_date = start_date_dt.strftime('%Y-%m-%d')

        # 设置默认的蒙特卡洛参数
        if monte_carlo_params is None:
            simulat_params = {
                'init_value': 'close',
                'analysis_column': 'pct_change',
                't': 0.01,
                'times': next_n_working_days,
                'series': 5000,
                'alpha': 0.05,
                'distribution_type': 'historical'
            }
        else:
            simulat_params = monte_carlo_params

        # Step 1 收集基础数据
        # 获取原始数据
        results_df = None
        # get_original_data_sql = f"select date as trade_date,open,close,low,high,pct_change from indexsysdb.df_akshare_futures_foreign_hist where symbol='{symbol}' and date>='{formatted_start_date}' and date<='{end_date}' order by date "
        original_dataFrame = inquiryManager.get_sql_dataset(get_original_data_sql)

        if output_path is None:
            output_path = FileUtility.generate_filename_by_timestamp(
                rf"{CommonParameters.outBoundPath}\MonteCarloRandomManager_original_dataFrame", "xlsx")
        original_dataFrame.to_excel(output_path)

        # 获取原始数据中的日期，作为循环条件
        # get_trade_date_sql = f"select date as trade_date from indexsysdb.df_akshare_futures_foreign_hist where symbol='{symbol}' and date>='{formatted_start_date}' and date<='{end_date}' order by date "
        loop_date_dataFrame = inquiryManager.get_sql_dataset(get_trade_date_sql)

        # 获取原始数据中的过去日期，推算 T+N 的工作日
        # get_past_calendar_sql = f"select date as trade_date,open,close,low,high,pct_change from indexsysdb.df_akshare_futures_foreign_hist where symbol='{symbol}' and date>='{formatted_start_date}' order by date "
        past_calendar_dataFrame = inquiryManager.get_sql_dataset(get_past_calendar_sql)

        # Step 2 逐天计算们特卡逻辑预测值
        for index, row in loop_date_dataFrame.iterrows():
            # Step 2.1 先拿到当前的日期
            current_date = row['trade_date']
            sample_end_date = current_date
            formatted_date = current_date
            logger.info(
                f"formatted_start_date: {formatted_start_date} | current_date: {current_date} | end_date: {end_date} | sample_end_date: {sample_end_date}")

            # Step 2.2 获取当前日期的样本数据
            logger.info(f"Processing date: {formatted_date}")
            monteCarlo_simulation_sql = monteCarlo_simulation_sql_template.format(
                symbol=symbol,
                sample_end_date=sample_end_date,
                limit_date=limit_date
            )
            # monteCarlo_simulation_sql = f"""
            #         select *
            #         from
            #         (
            #             select
            #                 date as trade_date,
            #                 open,
            #                 close,
            #                 low,
            #                 high,
            #                 pct_change
            #             from indexsysdb.df_akshare_futures_foreign_hist
            #             where symbol = '{symbol}' and date <= '{sample_end_date}'
            #         order by trade_date desc
            #         limit {limit_date}
            #         )
            #         order by trade_date
            #     """
            logger.info(f"sql: {monteCarlo_simulation_sql}")

            dataFrame = inquiryManager.get_sql_dataset(monteCarlo_simulation_sql)
            if dataFrame.empty:
                logger.warning(f"No data found...")
                current_date += timedelta(days=1)
                continue

            # Step 2.3 设置蒙特卡洛模拟参数
            all_line_df, all_lines, stats, var_lower_bound, var_upper_bound, average, median_value = monteCarloRandomManager.simulation_multi_series(
                dataFrame, simulat_params)

            # Step 2.4 计算 predict_date = 当前日期 + n 工作日，
            calendarService = CalendarService()
            next_n_working_date = calendarService.find_data_by_given_dataframe_and_date_offset(past_calendar_dataFrame,
                                                                                               current_date,
                                                                                               next_n_working_days)
            logger.info(
                f"current_date:{current_date}, next_n_working_days:{next_n_working_days} , next_n_working_date: {next_n_working_date}")
            if next_n_working_date is None:
                logger.warning(f"No next working date found for date: {current_date}")
            predict_date = next_n_working_date

            # Step 2.5 插入新值，
            new_row = pd.DataFrame([{
                'trade_date': formatted_date,
                'predict_date': predict_date,
                'var_lower_bound': var_lower_bound,
                'var_upper_bound': var_upper_bound,
                'average': average,
                'median_value': median_value
            }])
            logger.info(f"next row: {new_row}")
            if results_df is None:
                results_df = new_row  # 第一次赋值
            else:
                results_df = pd.concat([results_df, new_row])  # 后续拼接

            # Step 2.6 到末尾，结束
            if current_date > end_date:
                logger.info(f"current_date: {current_date}")
                logger.info(f"end_date: {end_date}")
                break

        logger.info(results_df)

        # Step 2.6 合并结果集
        monteCarloRandomAssistant = MonteCarloRandomAssistant()
        final_result = monteCarloRandomAssistant.generate_forecast_dataframes(original_dataFrame, results_df)
        final_result_copy = monteCarloRandomAssistant.select_required_columns(final_result, analysis_column)

        # Step 2.7 输出excel
        monteCarloRandomAssistant.save_file_to_excel(final_result_copy)

        # Step 2.8 画图
        monteCarloRandomAssistant.draw_plot(final_result_copy, analysis_column, analysis_column_label)

        return final_result_copy, results_df, original_dataFrame

    def test_multi_series_historical_distribution_GC_rolling(
            self,
            symbol='GC',
            start_date='2025-04-01',
            end_date=None,
            analysis_column='close',
            analysis_column_label='收盘价',
            limit_date=600,
            next_n_working_days=5,
            monte_carlo_params=None,
            output_path=None,
            get_original_data_sql=None,
            get_trade_date_sql=None,
            get_past_calendar_sql=None,
            monteCarlo_simulation_sql_template=None

    ):
        symbol = 'GC'  # 交易标的代码：纽约金
        start_date = '2025-04-01'  # 开始日期
        end_date = CommonParameters.today  # 结束日期：None 表示使用今天
        analysis_column = 'close'  # 分析列名：收盘价
        analysis_column_label = '收盘价'  # 分析列标签
        limit_date = 600  # 滚动窗口历史数据天数
        next_n_working_days = 5  # 预测未来工作日天数

        simulate_params = {
            'init_value': 'close',
            'analysis_column': 'pct_change',
            't': 0.01,
            'times': 5,
            'series': 5000,
            'alpha': 0.05,
            'distribution_type': 'historical'
        }

        start_date_dt = datetime.strptime(start_date, '%Y-%m-%d')
        formatted_start_date = start_date_dt.strftime('%Y-%m-%d')
        get_original_data_sql = f"select date as trade_date,open,close,low,high,pct_change from indexsysdb.df_akshare_futures_foreign_hist where symbol='{symbol}' and date>='{formatted_start_date}' and date<='{end_date}' order by date "
        get_trade_date_sql = f"select date as trade_date from indexsysdb.df_akshare_futures_foreign_hist where symbol='{symbol}' and date>='{formatted_start_date}' and date<='{end_date}' order by date "
        get_past_calendar_sql = f"select date as trade_date,open,close,low,high,pct_change from indexsysdb.df_akshare_futures_foreign_hist where symbol='{symbol}' and date>='{formatted_start_date}' order by date "

        monteCarlo_simulation_sql_template = """
                select *
                from
                (
                    select
                        date as trade_date,
                        open,
                        close,
                        low,
                        high,
                        pct_change
                    from indexsysdb.df_akshare_futures_foreign_hist
                    where symbol = '{symbol}' and date <= '{sample_end_date}'
                order by trade_date desc
                limit {limit_date}
                )
                order by trade_date
            """

        final_result, results_df, original_df = monteCarloTest.test_multi_series_historical_rolling(
            symbol=symbol,  # 交易标的代码：纽约金
            start_date=start_date,  # 开始日期
            end_date=None,  # 结束日期：None 表示使用今天
            analysis_column=analysis_column,  # 分析列名：收盘价
            analysis_column_label=analysis_column_label,  # 分析列标签
            limit_date=limit_date,  # 滚动窗口历史数据天数
            next_n_working_days=next_n_working_days,  # 预测未来工作日天数
            monte_carlo_params=simulate_params,  # 蒙特卡洛模拟参数
            output_path=None,  # Excel 输出路径：None 表示自动生成
            get_original_data_sql=get_original_data_sql,  # 获取原始数据的 SQL 模板：None 使用默认
            get_trade_date_sql=get_trade_date_sql,  # 获取交易日期的 SQL 模板：None 使用默认
            get_past_calendar_sql=get_past_calendar_sql,  # 获取历史日历的 SQL 模板：None 使用默认
            monteCarlo_simulation_sql_template=monteCarlo_simulation_sql_template
        )


    def test_multi_series_historical_distribution_XAU_rolling(self):
        """多线模拟 - Historical Distribution - XAU (伦敦金) - Rolling"""

        symbol = 'XAU'  # 交易标的代码：伦敦金
        start_date = '2025-11-01'  # 开始日期
        end_date = CommonParameters.today  # 结束日期：None 表示使用今天
        analysis_column = 'close'  # 分析列名：收盘价
        analysis_column_label = '收盘价'  # 分析列标签
        limit_date = 600  # 滚动窗口历史数据天数
        next_n_working_days = 5  # 预测未来工作日天数

        simulate_params = {
            'init_value': 'close',
            'analysis_column': 'pct_change',
            't': 0.01,
            'times': 5,
            'series': 5000,
            'alpha': 0.05,
            'distribution_type': 'historical'
        }

        start_date_dt = datetime.strptime(start_date, '%Y-%m-%d')
        formatted_start_date = start_date_dt.strftime('%Y-%m-%d')
        get_original_data_sql = f"select date as trade_date,open,close,low,high,pct_change from indexsysdb.df_akshare_futures_foreign_hist where symbol='{symbol}' and date>='{formatted_start_date}' and date<='{end_date}' order by date "
        get_trade_date_sql = f"select date as trade_date from indexsysdb.df_akshare_futures_foreign_hist where symbol='{symbol}' and date>='{formatted_start_date}' and date<='{end_date}' order by date "
        get_past_calendar_sql = f"select date as trade_date,open,close,low,high,pct_change from indexsysdb.df_akshare_futures_foreign_hist where symbol='{symbol}' and date>='{formatted_start_date}' order by date "

        monteCarlo_simulation_sql_template = """
                select *
                from
                (
                    select
                        date as trade_date,
                        open,
                        close,
                        low,
                        high,
                        pct_change
                    from indexsysdb.df_akshare_futures_foreign_hist
                    where symbol = '{symbol}' and date <= '{sample_end_date}'
                order by trade_date desc
                limit {limit_date}
                )
                order by trade_date
            """

        final_result, results_df, original_df = monteCarloTest.test_multi_series_historical_rolling(
            symbol=symbol,  # 交易标的代码：伦敦金
            start_date=start_date,  # 开始日期
            end_date=None,  # 结束日期：None 表示使用今天
            analysis_column=analysis_column,  # 分析列名：收盘价
            analysis_column_label=analysis_column_label,  # 分析列标签
            limit_date=limit_date,  # 滚动窗口历史数据天数
            next_n_working_days=next_n_working_days,  # 预测未来工作日天数
            monte_carlo_params=simulate_params,  # 蒙特卡洛模拟参数
            output_path=rf"D:\workspace_python\infinity_data\data\outbound\original_dataFrame_XAU.xlsx",  # Excel 输出路径
            get_original_data_sql=get_original_data_sql,  # 获取原始数据的 SQL 模板：None 使用默认
            get_trade_date_sql=get_trade_date_sql,  # 获取交易日期的 SQL 模板：None 使用默认
            get_past_calendar_sql=get_past_calendar_sql,  # 获取历史日历的 SQL 模板：None 使用默认
            monteCarlo_simulation_sql_template=monteCarlo_simulation_sql_template  # 蒙特卡洛模拟 SQL 模板
        )

        return

    def test_multi_series_historical_distribution_XAG_rolling(self):
        """多线模拟 - Historical Distribution - XAG (白银) - Rolling"""

        symbol = 'XAG'  # 交易标的代码：白银
        start_date = '2025-03-01'  # 开始日期
        end_date = None  # 结束日期：None 表示使用今天
        analysis_column = 'close'  # 分析列名：收盘价
        analysis_column_label = '收盘价'  # 分析列标签
        limit_date = 600  # 滚动窗口历史数据天数
        next_n_working_days = 5  # 预测未来工作日天数

        simulate_params = {
            'init_value': 'close',
            'analysis_column': 'pct_change',
            't': 0.01,
            'times': 5,
            'series': 5000,
            'alpha': 0.05,
            'distribution_type': 'historical'
        }

        start_date_dt = datetime.strptime(start_date, '%Y-%m-%d')
        formatted_start_date = start_date_dt.strftime('%Y-%m-%d')
        get_original_data_sql = f"select date as trade_date,open,close,low,high,pct_change from indexsysdb.df_akshare_futures_foreign_hist where symbol='{symbol}' and date>='{formatted_start_date}' and date<='{end_date}' order by date "
        get_trade_date_sql = f"select date as trade_date from indexsysdb.df_akshare_futures_foreign_hist where symbol='{symbol}' and date>='{formatted_start_date}' and date<='{end_date}' order by date "
        get_past_calendar_sql = f"select date as trade_date,open,close,low,high,pct_change from indexsysdb.df_akshare_futures_foreign_hist where symbol='{symbol}' and date>='{formatted_start_date}' order by date "

        monteCarlo_simulation_sql_template = """
                select *
                from
                (
                    select
                        date as trade_date,
                        open,
                        close,
                        low,
                        high,
                        pct_change
                    from indexsysdb.df_akshare_futures_foreign_hist
                    where symbol = '{symbol}' and date <= '{sample_end_date}'
                order by trade_date desc
                limit {limit_date}
                )
                order by trade_date
            """

        final_result, results_df, original_df = monteCarloTest.test_multi_series_historical_rolling(
            symbol=symbol,  # 交易标的代码：白银
            start_date=start_date,  # 开始日期
            end_date=None,  # 结束日期：None 表示使用今天
            analysis_column=analysis_column,  # 分析列名：收盘价
            analysis_column_label=analysis_column_label,  # 分析列标签
            limit_date=limit_date,  # 滚动窗口历史数据天数
            next_n_working_days=next_n_working_days,  # 预测未来工作日天数
            monte_carlo_params=simulate_params,  # 蒙特卡洛模拟参数
            output_path=rf"D:\workspace_python\infinity_data\data\outbound\original_dataFrame_XAG.xlsx",  # Excel 输出路径
            get_original_data_sql=get_original_data_sql,  # 获取原始数据的 SQL 模板：None 使用默认
            get_trade_date_sql=get_trade_date_sql,  # 获取交易日期的 SQL 模板：None 使用默认
            get_past_calendar_sql=get_past_calendar_sql,  # 获取历史日历的 SQL 模板：None 使用默认
            monteCarlo_simulation_sql_template=monteCarlo_simulation_sql_template  # 蒙特卡洛模拟 SQL 模板
        )

        return

    def test_multi_series_historical_distribution_GC_pctchange_rolling(self):
        """多线模拟 - Historical Distribution - GC (纽约金) - pct_change - Rolling"""
        monteCarloRandomManager = MonteCarloRandomManager()
        inquiryManager = InquiryManager()

        start_date = datetime.strptime('2025-01-01', '%Y-%m-%d')
        formatted_start_date = start_date.strftime('%Y-%m-%d')
        end_date = CommonParameters.today

        analysis_column = 'pct_change'
        analysis_column_label = '涨跌幅'
        limit_date = 600
        next_n_working_days = 5

        results_df = pd.DataFrame(columns=['trade_date', 'var_lower_bound', 'var_upper_bound', 'average', 'median_value'])
        sql = f"select date as trade_date,open,close,low,high,pct_change from indexsysdb.df_akshare_futures_foreign_hist where symbol='GC' and date>='{formatted_start_date}' and date<='{end_date}' order by date "
        original_dataFrame = inquiryManager.get_sql_dataset(sql)
        original_dataFrame.to_excel(rf"D:\workspace_python\infinity_data\data\outbound\original_dataFrame_GC_pctchange.xlsx")

        sql = f"select date as trade_date from indexsysdb.df_akshare_futures_foreign_hist where symbol='GC' and date>='{formatted_start_date}' and date<='{end_date}' order by date "
        loop_date_dataFrame = inquiryManager.get_sql_dataset(sql)

        sql = f"select date as trade_date,open,close,low,high,pct_change from indexsysdb.df_akshare_futures_foreign_hist where symbol='GC' and date>='{formatted_start_date}' order by date "
        past_calendar_dataFrame = inquiryManager.get_sql_dataset(sql)

        for index, row in loop_date_dataFrame.iterrows():
            current_date = row['trade_date']
            sample_end_date = current_date

            print(f"formatted_start_date: {formatted_start_date}")
            print(f"current_date: {current_date}")
            print(f"end_date: {end_date}")
            print(f"sample_end_date: {sample_end_date}")

            formatted_date = current_date

            print(f"Processing date: {formatted_date}")
            sql = f"""
                    select *
                    from 
                    (
                        select 
                            date as trade_date,
                            open,
                            close,
                            low,
                            high,
                            pct_change 
                        from indexsysdb.df_akshare_futures_foreign_hist
                        where symbol = 'GC' and date <= '{sample_end_date}'
                    order by trade_date desc
                    limit {limit_date}
                    )
                    order by trade_date
                """
            print(sql)

            dataFrame = inquiryManager.get_sql_dataset(sql)

            if dataFrame.empty:
                print(f"No data found for date: {formatted_date}")
                current_date += timedelta(days=1)
                continue

            simulat_params = {
                'init_value': 'pct_change',
                'analysis_column': 'pct_change',
                't': 0.01,
                'times': next_n_working_days,
                'series': 5000,
                'alpha': 0.05,
                'distribution_type': 'historical'
            }
            all_line_df, all_lines, stats, var_lower_bound, var_upper_bound, average, median_value = monteCarloRandomManager.simulation_multi_series(dataFrame, simulat_params)

            calendarService = CalendarService()
            last_date = (calendarService.find_data_by_given_dataframe_and_date_offset
                         (past_calendar_dataFrame, current_date, next_n_working_days))
            print(f"current_date:{current_date}, last date: {last_date} ============================================================> ")
            if last_date is None:
                print(f"No next working day found for date: {current_date}")

            new_row = pd.DataFrame([{
                'trade_date': formatted_date,
                'predict_date': last_date,
                'var_lower_bound': var_lower_bound,
                'var_upper_bound': var_upper_bound,
                'average': average,
                'median_value': median_value
            }])
            print(new_row)
            results_df = pd.concat([results_df, new_row], ignore_index=True)

            if current_date > end_date:
                print(f"current_date: {current_date}")
                print(f"end_date: {end_date}")
                break

        print(results_df)

        monteCarloRandomAssistant = MonteCarloRandomAssistant()
        final_result = monteCarloRandomAssistant.generate_forecast_dataframes(original_dataFrame, results_df)

        final_result_copy = monteCarloRandomAssistant.select_required_columns(final_result, analysis_column)

        monteCarloRandomAssistant.save_file_to_excel(final_result_copy)

        monteCarloRandomAssistant.draw_plot(final_result_copy, analysis_column, analysis_column_label)

        return

    def test_multi_series_historical_distribution_XAU_pctchange_rolling(self):
        """多线模拟 - Historical Distribution - XAU (伦敦金) - pct_change - Rolling"""
        monteCarloRandomManager = MonteCarloRandomManager()
        inquiryManager = InquiryManager()

        start_date = datetime.strptime('2025-01-01', '%Y-%m-%d')
        formatted_start_date = start_date.strftime('%Y-%m-%d')
        end_date = CommonParameters.today

        analysis_column = 'pct_change'
        analysis_column_label = '涨跌幅'
        limit_date = 600
        next_n_working_days = 5

        results_df = pd.DataFrame(
            columns=['trade_date', 'var_lower_bound', 'var_upper_bound', 'average', 'median_value'])
        sql = f"select date as trade_date,open,close,low,high,pct_change from indexsysdb.df_akshare_futures_foreign_hist where symbol='XAU' and date>='{formatted_start_date}' and date<='{end_date}' order by date "
        original_dataFrame = inquiryManager.get_sql_dataset(sql)

        if original_dataFrame.empty:
            print("警告：没有找到 XAU 的历史数据，请确认数据库中是否存在 symbol='XAU' 的记录")
            return

        original_dataFrame.to_excel(
            rf"D:\workspace_python\infinity_data\data\outbound\original_dataFrame_XAU_pctchange.xlsx")

        sql = f"select date as trade_date from indexsysdb.df_akshare_futures_foreign_hist where symbol='XAU' and date>='{formatted_start_date}' and date<='{end_date}' order by date "
        loop_date_dataFrame = inquiryManager.get_sql_dataset(sql)

        if loop_date_dataFrame.empty:
            print("警告：loop_date_dataFrame 为空，没有可迭代的交易日期")
            return

        sql = f"select date as trade_date,open,close,low,high,pct_change from indexsysdb.df_akshare_futures_foreign_hist where symbol='XAU' and date>='{formatted_start_date}' order by date "
        past_calendar_dataFrame = inquiryManager.get_sql_dataset(sql)

        for index, row in loop_date_dataFrame.iterrows():
            current_date = row['trade_date']
            sample_end_date = current_date

            print(f"formatted_start_date: {formatted_start_date}")
            print(f"current_date: {current_date}")
            print(f"end_date: {end_date}")
            print(f"sample_end_date: {sample_end_date}")

            formatted_date = current_date

            print(f"Processing date: {formatted_date}")
            sql = f"""
                    select *
                    from 
                    (
                        select 
                            date as trade_date,
                            open,
                            close,
                            low,
                            high,
                            pct_change 
                        from indexsysdb.df_akshare_futures_foreign_hist
                        where symbol = 'XAU' and date <= '{sample_end_date}'
                    order by trade_date desc
                    limit {limit_date}
                    )
                    order by trade_date
                """
            print(sql)

            dataFrame = inquiryManager.get_sql_dataset(sql)

            if dataFrame.empty:
                print(f"No data found for date: {formatted_date}")
                current_date += timedelta(days=1)
                continue

            simulat_params = {
                'init_value': 'pct_change',
                'analysis_column': 'pct_change',
                't': 0.01,
                'times': next_n_working_days,
                'series': 5000,
                'alpha': 0.05,
                'distribution_type': 'historical'
            }
            all_line_df, all_lines, stats, var_lower_bound, var_upper_bound, average, median_value = monteCarloRandomManager.simulation_multi_series(
                dataFrame, simulat_params)

            calendarService = CalendarService()
            last_date = (calendarService.find_data_by_given_dataframe_and_date_offset
                         (past_calendar_dataFrame, current_date, next_n_working_days))
            print(
                f"current_date:{current_date}, last date: {last_date} ============================================================> ")

            if last_date is None:
                print(f"No next working day found for date: {current_date}，跳过此条记录")
                continue

            new_row = pd.DataFrame([{
                'trade_date': formatted_date,
                'predict_date': last_date,
                'var_lower_bound': var_lower_bound,
                'var_upper_bound': var_upper_bound,
                'average': average,
                'median_value': median_value
            }])
            print(new_row)
            results_df = pd.concat([results_df, new_row], ignore_index=True)

            if current_date > end_date:
                print(f"current_date: {current_date}")
                print(f"end_date: {end_date}")
                break

        print(results_df)

        if results_df.empty:
            print("警告：results_df 为空，无法生成预测数据")
            return

        monteCarloRandomAssistant = MonteCarloRandomAssistant()
        final_result = monteCarloRandomAssistant.generate_forecast_dataframes(original_dataFrame, results_df)

        final_result_copy = monteCarloRandomAssistant.select_required_columns(final_result, analysis_column)

        monteCarloRandomAssistant.save_file_to_excel(final_result_copy)

        monteCarloRandomAssistant.draw_plot(final_result_copy, analysis_column, analysis_column_label)

        return

    def test_multi_series_historical_distribution_XAG_pctchange_rolling(self):
        """多线模拟 - Historical Distribution - XAG (白银) - pct_change - Rolling"""
        monteCarloRandomManager = MonteCarloRandomManager()
        inquiryManager = InquiryManager()

        start_date = datetime.strptime('2025-01-01', '%Y-%m-%d')
        formatted_start_date = start_date.strftime('%Y-%m-%d')
        end_date = CommonParameters.today

        analysis_column = 'pct_change'
        analysis_column_label = '涨跌幅'
        limit_date = 600
        next_n_working_days = 5

        results_df = pd.DataFrame(columns=['trade_date', 'var_lower_bound', 'var_upper_bound', 'average', 'median_value'])
        sql = f"select date as trade_date,open,close,low,high,pct_change from indexsysdb.df_akshare_futures_foreign_hist where symbol='XAG' and date>='{formatted_start_date}' and date<='{end_date}' order by date "
        original_dataFrame = inquiryManager.get_sql_dataset(sql)
        original_dataFrame.to_excel(rf"D:\workspace_python\infinity_data\data\outbound\original_dataFrame_XAG_pctchange.xlsx")

        sql = f"select date as trade_date from indexsysdb.df_akshare_futures_foreign_hist where symbol='XAG' and date>='{formatted_start_date}' and date<='{end_date}' order by date "
        loop_date_dataFrame = inquiryManager.get_sql_dataset(sql)

        sql = f"select date as trade_date,open,close,low,high,pct_change from indexsysdb.df_akshare_futures_foreign_hist where symbol='XAG' and date>='{formatted_start_date}' order by date "
        past_calendar_dataFrame = inquiryManager.get_sql_dataset(sql)

        for index, row in loop_date_dataFrame.iterrows():
            current_date = row['trade_date']
            sample_end_date = current_date

            print(f"formatted_start_date: {formatted_start_date}")
            print(f"current_date: {current_date}")
            print(f"end_date: {end_date}")
            print(f"sample_end_date: {sample_end_date}")

            formatted_date = current_date

            print(f"Processing date: {formatted_date}")
            sql = f"""
                    select *
                    from 
                    (
                        select 
                            date as trade_date,
                            open,
                            close,
                            low,
                            high,
                            pct_change 
                        from indexsysdb.df_akshare_futures_foreign_hist
                        where symbol = 'XAG' and date <= '{sample_end_date}'
                    order by trade_date desc
                    limit {limit_date}
                    )
                    order by trade_date
                """
            print(sql)

            dataFrame = inquiryManager.get_sql_dataset(sql)

            if dataFrame.empty:
                print(f"No data found for date: {formatted_date}")
                current_date += timedelta(days=1)
                continue

            simulat_params = {
                'init_value': 'pct_change',
                'analysis_column': 'pct_change',
                't': 0.01,
                'times': next_n_working_days,
                'series': 5000,
                'alpha': 0.05,
                'distribution_type': 'historical'
            }
            all_line_df, all_lines, stats, var_lower_bound, var_upper_bound, average, median_value = monteCarloRandomManager.simulation_multi_series(dataFrame, simulat_params)

            calendarService = CalendarService()
            last_date = (calendarService.find_data_by_given_dataframe_and_date_offset
                         (past_calendar_dataFrame, current_date, next_n_working_days))
            print(f"current_date:{current_date}, last date: {last_date} ============================================================> ")
            if last_date is None:
                print(f"No next working day found for date: {current_date}")

            new_row = pd.DataFrame([{
                'trade_date': formatted_date,
                'predict_date': last_date,
                'var_lower_bound': var_lower_bound,
                'var_upper_bound': var_upper_bound,
                'average': average,
                'median_value': median_value
            }])
            print(new_row)
            results_df = pd.concat([results_df, new_row], ignore_index=True)

            if current_date > end_date:
                print(f"current_date: {current_date}")
                print(f"end_date: {end_date}")
                break

        print(results_df)

        monteCarloRandomAssistant = MonteCarloRandomAssistant()
        final_result = monteCarloRandomAssistant.generate_forecast_dataframes(original_dataFrame, results_df)

        final_result_copy = monteCarloRandomAssistant.select_required_columns(final_result, analysis_column)

        monteCarloRandomAssistant.save_file_to_excel(final_result_copy)

        monteCarloRandomAssistant.draw_plot(final_result_copy, analysis_column, analysis_column_label)

        return

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

    def test_multi_series_historical_distribution_USD_index_rolling(self):
        """多线模拟 - Historical Distribution - USD Index (美元指数) - Rolling"""

        symbol = 'USDX'  # 交易标的代码：美元指数
        start_date = '2024-03-01'  # 开始日期
        end_date = None  # 结束日期：None 表示使用今天
        analysis_column = 'close'  # 分析列名：美元指数
        analysis_column_label = '美元指数'  # 分析列标签
        limit_date = 600  # 滚动窗口历史数据天数
        next_n_working_days = 5  # 预测未来工作日天数

        simulate_params = {
            'init_value': 'close',
            'analysis_column': 'pct_change',
            't': 0.01,
            'times': 5,
            'series': 5000,
            'alpha': 0.05,
            'distribution_type': 'historical'
        }

        start_date_dt = datetime.strptime(start_date, '%Y-%m-%d')
        formatted_start_date = start_date_dt.strftime('%Y-%m-%d')

        # 从 ClickHouse 查询美元指数数据
        get_original_data_sql = f"select trade_date, USDX_index as open, USDX_index as close, USDX_index as low, USDX_index as high, pct_change from indexsysdb.df_tushare_usd_index_daily where trade_date>='{formatted_start_date}' and trade_date<='{end_date}'  AND USDX_index IS NOT NULL AND USDX_index > 0 AND NOT isNaN(USDX_index)  AND pct_change > 0 AND isFinite(pct_change) order by trade_date "
        get_trade_date_sql = f"select trade_date from indexsysdb.df_tushare_usd_index_daily where trade_date>='{formatted_start_date}' and trade_date<='{end_date}'  AND USDX_index IS NOT NULL AND USDX_index > 0 AND NOT isNaN(USDX_index)  AND pct_change > 0 AND isFinite(pct_change) order by trade_date "
        get_past_calendar_sql = f"select trade_date, USDX_index as close, pct_change from indexsysdb.df_tushare_usd_index_daily where trade_date>='{formatted_start_date}'  AND USDX_index IS NOT NULL AND USDX_index > 0 AND NOT isNaN(USDX_index)  AND pct_change > 0 AND isFinite(pct_change) order by trade_date "

        monteCarlo_simulation_sql_template = """
                select *
                from
                (
                    select
                        trade_date,
                        USDX_index as close,
                        pct_change
                    from indexsysdb.df_tushare_usd_index_daily
                    where trade_date <= '{sample_end_date}'
                order by trade_date desc
                limit {limit_date}
                )
                order by trade_date
            """

        final_result, results_df, original_df = monteCarloTest.test_multi_series_historical_rolling(
            symbol=symbol,  # 交易标的代码：美元指数
            start_date=start_date,  # 开始日期
            end_date=None,  # 结束日期：None 表示使用今天
            analysis_column=analysis_column,  # 分析列名：美元指数
            analysis_column_label=analysis_column_label,  # 分析列标签
            limit_date=limit_date,  # 滚动窗口历史数据天数
            next_n_working_days=next_n_working_days,  # 预测未来工作日天数
            monte_carlo_params=simulate_params,  # 蒙特卡洛模拟参数
            output_path=rf"D:\workspace_python\infinity_data\data\outbound\original_dataFrame_USDX.xlsx",  # Excel 输出路径
            get_original_data_sql=get_original_data_sql,  # 获取原始数据的 SQL 模板
            get_trade_date_sql=get_trade_date_sql,  # 获取交易日期的 SQL 模板
            get_past_calendar_sql=get_past_calendar_sql,  # 获取历史日历的 SQL 模板
            monteCarlo_simulation_sql_template=monteCarlo_simulation_sql_template  # 蒙特卡洛模拟 SQL 模板
        )

        return

    # 通用代码
    def test_multi_series_historical_rolling(
            self,
            symbol='GC',
            start_date='2025-04-01',
            end_date=CommonParameters.today,
            analysis_column='close',
            analysis_column_label='收盘价',
            limit_date=600,
            next_n_working_days=5,
            monte_carlo_params=None,
            output_path=None,
            get_original_data_sql=None,
            get_trade_date_sql=None,
            get_past_calendar_sql=None,
            monteCarlo_simulation_sql_template=None

    ):
        """
        多线模拟 - Historical Distribution - Rolling Window 通用方法

        Args:
            symbol (str): 交易标的代码，默认 'GC'
            start_date (str): 开始日期，格式 'YYYY-MM-DD'，默认 '2025-04-01'
            end_date (str): 结束日期，格式 'YYYY-MM-DD'，默认使用 CommonParameters.today
            analysis_column (str): 分析列名，默认 'close'
            analysis_column_label (str): 分析列标签，默认 '收盘价'
            limit_date (int): 滚动窗口历史数据天数，默认 600
            next_n_working_days (int): 预测未来工作日天数，默认 5
            monte_carlo_params (dict): 蒙特卡洛模拟参数，默认 None 时使用内置配置
            output_path (str): Excel 输出路径，默认 None 时自动生成

        Returns:
            tuple: (final_result, results_df, original_dataFrame) 最终结果 DataFrame、滚动结果 DataFrame、原始数据 DataFrame
        """
        # Step 0 初始化
        monteCarloRandomManager = MonteCarloRandomManager()
        inquiryManager = InquiryManager()

        # 处理默认参数
        if end_date is None:
            from dataIntegrator.common.CommonParameters import CommonParameters
            end_date = CommonParameters.today

        start_date_dt = datetime.strptime(start_date, '%Y-%m-%d')
        formatted_start_date = start_date_dt.strftime('%Y-%m-%d')
        #end_date = datetime.strptime(end_date, '%Y-%m-%d')

        # 设置默认的蒙特卡洛参数
        if monte_carlo_params is None:
            simulat_params = {
                'init_value': 'close',
                'analysis_column': 'pct_change',
                't': 0.01,
                'times': next_n_working_days,
                'series': 5000,
                'alpha': 0.05,
                'distribution_type': 'historical'
            }
        else:
            simulat_params = monte_carlo_params

        # Step 1 收集基础数据
        # 获取原始数据
        results_df = None
        # get_original_data_sql = f"select date as trade_date,open,close,low,high,pct_change from indexsysdb.df_akshare_futures_foreign_hist where symbol='{symbol}' and date>='{formatted_start_date}' and date<='{end_date}' order by date "
        original_dataFrame = inquiryManager.get_sql_dataset(get_original_data_sql)

        if output_path is None:
            output_path = FileUtility.generate_filename_by_timestamp(
                rf"D:\workspace_python\infinity_data\data\outbound\MonteCarloRandomManager_original_dataFrame", "xlsx")
        original_dataFrame.to_excel(output_path)

        # 获取原始数据中的日期，作为循环条件
        # get_trade_date_sql = f"select date as trade_date from indexsysdb.df_akshare_futures_foreign_hist where symbol='{symbol}' and date>='{formatted_start_date}' and date<='{end_date}' order by date "
        loop_date_dataFrame = inquiryManager.get_sql_dataset(get_trade_date_sql)

        # 获取原始数据中的过去日期，推算 T+N 的工作日
        # get_past_calendar_sql = f"select date as trade_date,open,close,low,high,pct_change from indexsysdb.df_akshare_futures_foreign_hist where symbol='{symbol}' and date>='{formatted_start_date}' order by date "
        past_calendar_dataFrame = inquiryManager.get_sql_dataset(get_past_calendar_sql)

        # Step 2 逐天计算们特卡逻辑预测值
        for index, row in loop_date_dataFrame.iterrows():
            # Step 2.1 先拿到当前的日期
            current_date = row['trade_date']
            sample_end_date = current_date
            formatted_date = current_date
            logger.info(
                f"formatted_start_date: {formatted_start_date} | current_date: {current_date} | end_date: {end_date} | sample_end_date: {sample_end_date}")

            # Step 2.2 获取当前日期的样本数据
            logger.info(f"Processing date: {formatted_date}")
            monteCarlo_simulation_sql = monteCarlo_simulation_sql_template.format(
                symbol=symbol,
                sample_end_date=sample_end_date,
                limit_date=limit_date
            )
            logger.info(f"sql: {monteCarlo_simulation_sql}")

            dataFrame = inquiryManager.get_sql_dataset(monteCarlo_simulation_sql)
            if dataFrame.empty:
                logger.warning(f"No data found...")
                current_date += timedelta(days=1)
                continue

            # Step 2.3 设置蒙特卡洛模拟参数
            all_line_df, all_lines, stats, var_lower_bound, var_upper_bound, average, median_value = monteCarloRandomManager.simulation_multi_series(
                dataFrame, simulat_params)

            # Step 2.4 计算 predict_date = 当前日期 + n 工作日，
            calendarService = CalendarService()
            next_n_working_date = calendarService.find_data_by_given_dataframe_and_date_offset(past_calendar_dataFrame,
                                                                                               current_date,
                                                                                               next_n_working_days)
            logger.info(
                f"current_date:{current_date}, next_n_working_days:{next_n_working_days} , next_n_working_date: {next_n_working_date}")
            if next_n_working_date is None:
                logger.warning(f"No next working date found for date: {current_date}")
            predict_date = next_n_working_date

            # Step 2.5 插入新值，
            new_row = pd.DataFrame([{
                'trade_date': formatted_date,
                'predict_date': predict_date,
                'var_lower_bound': var_lower_bound,
                'var_upper_bound': var_upper_bound,
                'average': average,
                'median_value': median_value
            }])
            logger.info(f"next row: {new_row}")
            if results_df is None:
                results_df = new_row  # 第一次赋值
            else:
                results_df = pd.concat([results_df, new_row])  # 后续拼接

            # Step 2.6 到末尾，结束
            if current_date > end_date:
                logger.info(f"current_date: {current_date}")
                logger.info(f"end_date: {end_date}")
                break

        logger.info(results_df)

        # Step 2.6 合并结果集
        monteCarloRandomAssistant = MonteCarloRandomAssistant()
        final_result = monteCarloRandomAssistant.generate_forecast_dataframes(original_dataFrame, results_df)        # 添加预测差距计算列
        final_result['lower_close_gap'] = (final_result['var_lower_bound'] - final_result['close']) / final_result['close']
        final_result['upper_lower_gap'] = final_result['var_upper_bound'] - final_result['var_lower_bound']

        final_result_copy = monteCarloRandomAssistant.select_required_columns(final_result, analysis_column)

        # Step 2.7 输出excel
        monteCarloRandomAssistant.save_file_to_excel(final_result_copy)

        # Step 2.8 画图
        monteCarloRandomAssistant.draw_plot(final_result_copy, analysis_column, analysis_column_label)
        # Step 2.9 绘制预测差距折线图
        self.plot_predict_gap_chart(final_result_copy)


        return final_result_copy, results_df, original_dataFrame

    def plot_predict_gap_chart(self, final_result_copy):
        """
        绘制预测差距折线图：trade_date 为 x 轴，lower_close_gap 和 upper_lower_gap 为 y 轴
        """
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        logger.info("\n=== 绘制预测差距折线图 ===")

        # 准备数据
        plot_data = final_result_copy.copy()

        # 处理日期列
        if 'trade_date' in plot_data.columns:
            # 移除 None 值和空值
            plot_data = plot_data.dropna(subset=['trade_date'])
            plot_data = plot_data[plot_data['trade_date'] != '']
            plot_data = plot_data[plot_data['trade_date'] != 'None']

            # 转换为日期类型
            try:
                plot_data['trade_date'] = pd.to_datetime(plot_data['trade_date'], format='mixed', errors='coerce')
            except:
                plot_data['trade_date'] = pd.to_datetime(plot_data['trade_date'], errors='coerce')

            # 移除转换失败的行
            plot_data = plot_data.dropna(subset=['trade_date'])
            plot_data = plot_data.sort_values('trade_date')

        # 检查是否有足够的数据绘图
        if len(plot_data) == 0:
            logger.warning("警告：没有足够的有效数据进行绘图")
            return

        # 计算需要的列（如果不存在）
        if 'lower_close_gap' not in plot_data.columns:
            plot_data['lower_close_gap'] = plot_data['var_lower_bound'] - plot_data['close']

        if 'upper_lower_gap' not in plot_data.columns:
            plot_data['upper_lower_gap'] = plot_data['var_upper_bound'] - plot_data['var_lower_bound']

        # 设置图形大小
        plt.figure(figsize=(14, 8))

        # 准备 X 轴数据
        x_data = plot_data['trade_date']

        # 绘制 lower_close_gap (VaR 下界与收盘价的差距)
        if 'lower_close_gap' in plot_data.columns and not plot_data['lower_close_gap'].isna().all():
            plt.plot(x_data, plot_data['lower_close_gap'],
                     linewidth=2.5, label='lower_close_gap (VaR 下界 - 收盘价)',
                     color='blue', linestyle='-', zorder=1)

        # 绘制 upper_lower_gap (VaR 上下界的差距)
        if 'upper_lower_gap' in plot_data.columns and not plot_data['upper_lower_gap'].isna().all():
            plt.plot(x_data, plot_data['upper_lower_gap'],
                     linewidth=2.5, label='upper_lower_gap (VaR 上界 - VaR 下界)',
                     color='red', linestyle='--', zorder=2)

        # 设置图表属性
        plt.xlabel('交易日期', fontsize=12)
        plt.ylabel('数值', fontsize=12)
        plt.title('预测差距趋势图', fontsize=14, fontweight='bold')
        plt.legend(loc='best', fontsize=10)
        plt.grid(True, alpha=0.3, linestyle=':')

        # 添加参考线 y=0
        plt.axhline(y=0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)

        # 格式化 x 轴日期显示
        if len(plot_data) > 0:
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=1))
            plt.xticks(rotation=90, fontsize=8)

        # 调整布局
        plt.tight_layout()

        # 显示图表
        plt.show()

        # 打印数据统计信息
        print("\n=== 预测差距图表数据统计 ===")
        for col in ['lower_close_gap', 'upper_lower_gap']:
            if col in plot_data.columns:
                valid_data = plot_data[col].dropna()
                if len(valid_data) > 0:
                    print(
                        f"{col}: 最小值={valid_data.min():.4f}, 最大值={valid_data.max():.4f}, 平均值={valid_data.mean():.4f}")

        print("=" * 60)


if __name__ == "__main__":
    monteCarloTest = MonteCarloRandomTest()

    """
    # 基础测试案例
    """
    # monteCarloTest.test_single_line_normal_distribute()
    # monteCarloTest.test_single_line_lognormal_distribute()
    # monteCarloTest.test_multi_series_normal_distribution_citi()
    # monteCarloTest.test_multi_series_lognormal_distribution_citi()
    # monteCarloTest.test_multi_series_lognormal_distribution_jpm()
    # monteCarloTest.test_multi_series_lognormal_distribution_pudong_2022()
    # monteCarloTest.test_multi_series_lognormal_distribution_pudong_2024()
    # monteCarloTest.test_multi_series_lognormal_distribution_lvcw()
    # monteCarloTest.test_multi_stock_multi_series_lognormal_distribution()

    """
    用不同方式对上海金价进行分析， lognormal/historical/historical_rolling
    """
    # monteCarloTest.test_multi_series_lognormal_distribution_sge()
    # monteCarloTest.test_multi_series_historical_distribution_sge()
    # monteCarloTest.test_multi_series_historical_distribution_sge_rolling()

    """
    用不同方式对上海金价%进行分析， lognormal/historical/historical_rolling
    """
    # monteCarloTest.test_multi_series_lognormal_distribution_sge_pctchange()
    # monteCarloTest.test_multi_series_historical_distribution_sge_pctchange()
    # monteCarloTest.test_multi_series_historical_distribution_sge_pct_change_rolling()

    """
    用不同方式对伦敦金进行分析， lognormal/historical/historical_rolling
    -- GC  - 纽约金
    -- XAU - 伦敦金
    -- XAG - 白银
    """
    monteCarloTest.test_multi_series_historical_distribution_GC_rolling()
    # monteCarloTest.test_multi_series_historical_distribution_XAU_rolling()
    # monteCarloTest.test_multi_series_historical_distribution_XAG_rolling()

    # monteCarloTest.test_multi_series_historical_distribution_GC_pctchange_rolling()
    # monteCarloTest.test_multi_series_historical_distribution_XAU_pctchange_rolling()
    # monteCarloTest.test_multi_series_historical_distribution_XAG_pctchange_rolling()


    """
        美国债
    """
    # monteCarloTest.test_multi_series_lognormal_distribution_treasury_yield()

    # monteCarloTest.test_multi_series_historical_distribution_USD_index_rolling()

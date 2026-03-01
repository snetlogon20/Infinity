from dataIntegrator import CommonParameters
from dataIntegrator.analysisService.InquiryManager import InquiryManager
from dataIntegrator.modelService.MonteCarlo.MonteCarloRandomAssistant import MonteCarloRandomAssistant
from dataIntegrator.modelService.MonteCarlo.MonteCarloRandomManager import MonteCarloRandomManager
from dataIntegrator.modelService.commonService.CalendarService import CalendarService
from dataIntegrator.utility.FileUtility import FileUtility
from datetime import datetime, timedelta
import pandas as pd

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
        end_date = '2026-02-27'

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

        final_result_copy = monteCarloRandomAssistant.select_required_columns(final_result)

        monteCarloRandomAssistant.save_file_to_excel(final_result_copy)

        monteCarloRandomAssistant.draw_plot(final_result_copy)

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
        """多线模拟 - LogNormal Distribution - Gold"""
        monteCarloRandomManager = MonteCarloRandomManager()
        inquiryManager = InquiryManager()

        start_date = datetime.strptime('2025-02-14', '%Y-%m-%d')
        # end_date = datetime.strptime('2026-02-14', '%Y-%m-%d')
        end_date = datetime.strptime('2026-02-20', '%Y-%m-%d')

        results_df = pd.DataFrame(columns=['date', 'var_lower_bound', 'var_upper_bound', 'average', 'median_value'])

        # 循环遍历日期
        current_date = start_date
        while current_date <= end_date:
            # 格式化当前日期为字符串
            formatted_date = current_date.strftime('%Y-%m-%d')

            # 在这里执行你需要的操作，例如查询数据库或处理数据
            print(f"Processing date: {formatted_date}")
            sql = """
                     select 
                         date,
                         open,
                         close,
                         low,
                         high,
                         pct_change 
                     from indexsysdb.df_akshare_spot_hist_sge
                     where date >= '2025-01-01' and date <= '""" + formatted_date + """'
                     order by date"""
            print(sql)

            dataFrame = inquiryManager.get_sql_dataset(sql)

            simulat_params = {
                'init_value': 'pct_change',
                'analysis_column': 'pct_change',
                't': 0.01,
                'times': 10,
                'series': 1000,
                'alpha': 0.05,
                'distribution_type': 'lognormal'  # normal/lognormal/historical
            }
            all_line_df, all_lines, stats, var_lower_bound, var_upper_bound, average, median_value = monteCarloRandomManager.simulation_multi_series(
                dataFrame, simulat_params)
            # 将结果添加到 DataFrame 中
            new_row = pd.DataFrame([{
                'date': formatted_date,
                'var_lower_bound': var_lower_bound,
                'var_upper_bound': var_upper_bound,
                'average': average,
                'median_value': median_value
            }])
            results_df = pd.concat([results_df, new_row], ignore_index=True)

            # 增加一天
            current_date += timedelta(days=1)

        print(results_df)
        # 可选：将结果保存到 Excel 文件
        file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_results", "xlsx")
        results_df.to_excel(file_full_name, index=False)

        return

    def test_multi_series_historical_distribution_GC_rolling(self):
        """多线模拟 - LogNormal Distribution - Gold"""
        monteCarloRandomManager = MonteCarloRandomManager()
        inquiryManager = InquiryManager()

        start_date = datetime.strptime('2025-01-01', '%Y-%m-%d')
        formatted_start_date = start_date.strftime('%Y-%m-%d')
        #end_date = '2025-12-31'
        #end_date = '2026-02-13'
        end_date = CommonParameters.today
        limit_date = 600

        results_df = pd.DataFrame(columns=['date', 'var_lower_bound', 'var_upper_bound', 'average', 'median_value'])
        sql = "select date from indexsysdb.df_akshare_futures_foreign_hist where symbol = 'XAU' order by date "
        working_date_dataFrame = inquiryManager.get_sql_dataset(sql)

        sql = f"select date from indexsysdb.df_akshare_futures_foreign_hist where date>='{formatted_start_date}' and date<='{end_date}' order by date "
        look_date_dataFrame = inquiryManager.get_sql_dataset(sql)

        for index, row in look_date_dataFrame.iterrows():
            current_date = row['date']
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
                            date,
                            open,
                            close,
                            low,
                            high,
                            pct_change 
                        from indexsysdb.df_akshare_futures_foreign_hist
                        where symbol = 'GC' and 
                        date <= '{sample_end_date}'
                    order by date desc
                    limit {limit_date}
                    )
                    order by date
                """
            print(sql)

            dataFrame = inquiryManager.get_sql_dataset(sql)
            print(dataFrame)
            if dataFrame.empty:
                print(f"No data found for date: {formatted_date}")
                current_date += timedelta(days=1)
                continue  # 跳过当前循环

            simulat_params = {
                'init_value': 'close',
                'analysis_column': 'pct_change',
                't': 0.01,
                'times': 5,
                'series': 5000,
                'alpha': 0.05,
                'distribution_type': 'historical'  # normal/lognormal/historical
            }
            all_line_df, all_lines, stats, var_lower_bound, var_upper_bound, average, median_value = monteCarloRandomManager.simulation_multi_series(dataFrame, simulat_params)
            # 将结果添加到 DataFrame 中
            new_row = pd.DataFrame([{
                'date': formatted_date,
                'var_lower_bound': var_lower_bound,
                'var_upper_bound': var_upper_bound,
                'average': average,
                'median_value': median_value
            }])
            print(new_row)
            results_df = pd.concat([results_df, new_row], ignore_index=True)

            # # 增加一天
            # #current_date += timedelta(days=1)
            # current_date = self.get_next_working_day(working_date_dataFrame, formatted_date) # 获取下一个工作日，但这个只是临时算法
            # print(current_date)
            if current_date > end_date:
                print(f"current_date: {current_date}")
                print(f"end_date: {end_date}")
                break

        print(results_df)

        # 可选：将结果保存到 Excel 文件
        file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_results", "xlsx")
        results_df.to_excel(file_full_name, index=False)
        print(file_full_name)

        return

    def test_multi_series_historical_distribution_XAU_rolling(self):
        """多线模拟 - LogNormal Distribution - Gold"""
        monteCarloRandomManager = MonteCarloRandomManager()
        inquiryManager = InquiryManager()

        start_date = datetime.strptime('2025-01-01', '%Y-%m-%d')
        formatted_start_date = start_date.strftime('%Y-%m-%d')
        #end_date = '2025-12-31'
        #end_date = '2026-02-13'
        end_date = CommonParameters.today
        limit_date = 600

        results_df = pd.DataFrame(columns=['date', 'var_lower_bound', 'var_upper_bound', 'average', 'median_value'])
        sql = "select date from indexsysdb.df_akshare_futures_foreign_hist where symbol = 'XAU' order by date "
        working_date_dataFrame = inquiryManager.get_sql_dataset(sql)

        sql = f"select date from indexsysdb.df_akshare_futures_foreign_hist where date>='{formatted_start_date}' and date<='{end_date}' order by date "
        look_date_dataFrame = inquiryManager.get_sql_dataset(sql)

        for index, row in look_date_dataFrame.iterrows():
            current_date = row['date']
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
                            date,
                            open,
                            close,
                            low,
                            high,
                            pct_change 
                        from indexsysdb.df_akshare_futures_foreign_hist
                        where symbol = 'XAU' and 
                        date <= '{sample_end_date}'
                    order by date desc
                    limit {limit_date}
                    )
                    order by date
                """
            print(sql)

            dataFrame = inquiryManager.get_sql_dataset(sql)
            print(dataFrame)
            if dataFrame.empty:
                print(f"No data found for date: {formatted_date}")
                current_date += timedelta(days=1)
                continue  # 跳过当前循环

            simulat_params = {
                'init_value': 'close',
                'analysis_column': 'pct_change',
                't': 0.01,
                'times': 5,
                'series': 5000,
                'alpha': 0.05,
                'distribution_type': 'historical'  # normal/lognormal/historical
            }
            all_line_df, all_lines, stats, var_lower_bound, var_upper_bound, average, median_value = monteCarloRandomManager.simulation_multi_series(dataFrame, simulat_params)
            # 将结果添加到 DataFrame 中
            new_row = pd.DataFrame([{
                'date': formatted_date,
                'var_lower_bound': var_lower_bound,
                'var_upper_bound': var_upper_bound,
                'average': average,
                'median_value': median_value
            }])
            print(new_row)
            results_df = pd.concat([results_df, new_row], ignore_index=True)

            # # 增加一天
            # #current_date += timedelta(days=1)
            # current_date = self.get_next_working_day(working_date_dataFrame, formatted_date) # 获取下一个工作日，但这个只是临时算法
            # print(current_date)
            if current_date > end_date:
                print(f"current_date: {current_date}")
                print(f"end_date: {end_date}")
                break

        print(results_df)

        # 可选：将结果保存到 Excel 文件
        file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_results", "xlsx")
        results_df.to_excel(file_full_name, index=False)

        return

    def test_multi_series_historical_distribution_XAG_rolling(self):
        """多线模拟 - LogNormal Distribution - Gold"""
        monteCarloRandomManager = MonteCarloRandomManager()
        inquiryManager = InquiryManager()

        start_date = datetime.strptime('2025-01-01', '%Y-%m-%d')
        formatted_start_date = start_date.strftime('%Y-%m-%d')
        #end_date = '2025-12-31'
        #end_date = '2026-02-13'
        end_date = CommonParameters.today
        limit_date = 600

        results_df = pd.DataFrame(columns=['date', 'var_lower_bound', 'var_upper_bound', 'average', 'median_value'])
        sql = "select date from indexsysdb.df_akshare_futures_foreign_hist where symbol = 'XAU' order by date "
        working_date_dataFrame = inquiryManager.get_sql_dataset(sql)

        sql = f"select date from indexsysdb.df_akshare_futures_foreign_hist where date>='{formatted_start_date}' and date<='{end_date}' order by date "
        look_date_dataFrame = inquiryManager.get_sql_dataset(sql)

        for index, row in look_date_dataFrame.iterrows():
            current_date = row['date']
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
                            date,
                            open,
                            close,
                            low,
                            high,
                            pct_change 
                        from indexsysdb.df_akshare_futures_foreign_hist
                        where symbol = 'XAG' and 
                        date <= '{sample_end_date}'
                    order by date desc
                    limit {limit_date}
                    )
                    order by date
                """
            print(sql)

            dataFrame = inquiryManager.get_sql_dataset(sql)
            print(dataFrame)
            if dataFrame.empty:
                print(f"No data found for date: {formatted_date}")
                current_date += timedelta(days=1)
                continue  # 跳过当前循环

            simulat_params = {
                'init_value': 'close',
                'analysis_column': 'pct_change',
                't': 0.01,
                'times': 5,
                'series': 5000,
                'alpha': 0.05,
                'distribution_type': 'historical'  # normal/lognormal/historical
            }
            all_line_df, all_lines, stats, var_lower_bound, var_upper_bound, average, median_value = monteCarloRandomManager.simulation_multi_series(dataFrame, simulat_params)
            # 将结果添加到 DataFrame 中
            new_row = pd.DataFrame([{
                'date': formatted_date,
                'var_lower_bound': var_lower_bound,
                'var_upper_bound': var_upper_bound,
                'average': average,
                'median_value': median_value
            }])
            print(new_row)
            results_df = pd.concat([results_df, new_row], ignore_index=True)

            # # 增加一天
            # #current_date += timedelta(days=1)
            # current_date = self.get_next_working_day(working_date_dataFrame, formatted_date) # 获取下一个工作日，但这个只是临时算法
            # print(current_date)
            if current_date > end_date:
                print(f"current_date: {current_date}")
                print(f"end_date: {end_date}")
                break

        print(results_df)

        # 可选：将结果保存到 Excel 文件
        file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_results", "xlsx")
        results_df.to_excel(file_full_name, index=False)

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
    # monteCarloTest.test_multi_series_historical_distribution_GC_rolling()
    #monteCarloTest.test_multi_series_historical_distribution_XAU_rolling()
    monteCarloTest.test_multi_series_historical_distribution_XAG_rolling()

    # monteCarloTest.test_multi_series_lognormal_distribution_treasury_yield()


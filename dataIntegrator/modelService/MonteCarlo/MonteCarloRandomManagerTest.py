from dataIntegrator.analysisService.InquiryManager import InquiryManager
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
        end_date = '2025-02-13'
        # end_date = '2025-12-31'
        end_date = '2026-02-13'

        limit_date = 600
        next_n_working_days = 10

        results_df = pd.DataFrame(columns=['date', 'var_lower_bound', 'var_upper_bound', 'average', 'median_value'])
        sql = f"select * from indexsysdb.df_akshare_spot_hist_sge where date>='{formatted_start_date}' and date<='{end_date}' order by date "
        original_dataFrame = inquiryManager.get_sql_dataset(sql)
        original_dataFrame.to_excel(rf"D:\workspace_python\infinity_data\data\outbound\original_dataFrame.xlsx")

        sql = f"select date from indexsysdb.df_akshare_spot_hist_sge where date>='{formatted_start_date}' and date<='{end_date}' order by date "
        loop_date_dataFrame = inquiryManager.get_sql_dataset(sql)

        sql = f"select * from indexsysdb.df_akshare_spot_hist_sge where date>='{formatted_start_date}' order by date "
        calendar_dataFrame = inquiryManager.get_sql_dataset(sql)

        for index, row in loop_date_dataFrame.iterrows():
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
                        from indexsysdb.df_akshare_spot_hist_sge
                        where date <= '{sample_end_date}'
                    order by date desc
                    limit {limit_date}
                    )
                    order by date
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
                'alpha': 0.05,
                'distribution_type': 'historical'  # normal/lognormal/historical
            }
            all_line_df, all_lines, stats, var_lower_bound, var_upper_bound, average, median_value = monteCarloRandomManager.simulation_multi_series(dataFrame, simulat_params)

            calendarService = CalendarService()
            last_date = (calendarService.find_data_by_given_dataframe_and_date_offset
                         (calendar_dataFrame, current_date, next_n_working_days))
            print(f"current_date:{current_date}, last date: {last_date} ============================================================> ")
            if last_date is None:
                print(f"No next working day found for date: {current_date}")

            # 将结果添加到 DataFrame 中
            # new_row = pd.DataFrame([{
            #     'date': formatted_date,
            #     'var_lower_bound': var_lower_bound,
            #     'var_upper_bound': var_upper_bound,
            #     'average': average,
            #     'median_value': median_value
            # }])
            new_row = pd.DataFrame([{
                'date': formatted_date,
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

        # 可选：将结果保存到 Excel 文件
        file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_results", "xlsx")
        results_df.to_excel(file_full_name, index=False)
        print("Results saved to Excel %s.",file_full_name)

        self.run_complete_validation_test(original_dataFrame, results_df)


        return

    def find_next_n_dates(self, dataFrame, formatted_date, n_days=2):
        """
        在dataFrame的date字段中找到formatted_date，然后向更大的日期方向查找n_days个日期

        Args:
            dataFrame: 包含date字段的DataFrame
            formatted_date: 要查找的日期字符串
            n_days: 要查找的后续天数，默认为2天

        Returns:
            list: 包含接下来n_days个日期的列表
        """
        # 确保date字段是字符串类型以便比较
        #dataFrame['date'] = dataFrame['date'].astype(str)

        print("=========================================================================>")
        print("formatted_date:", formatted_date)
        print("dataFrame:", dataFrame)


        # 按日期排序
        sorted_df = dataFrame.copy().sort_values('date').reset_index(drop=True)

        # 找到formatted_date的位置
        target_index = sorted_df[sorted_df['date'] == formatted_date].index

        if len(target_index) == 0:
            print(f"未找到日期: {formatted_date}")

        target_index = target_index[0]

        # 获取接下来的n_days个日期
        next_dates = []
        remaining_rows = len(sorted_df) - target_index - 1

        if remaining_rows >= n_days:
            # 有足够的后续日期
            next_dates = sorted_df.iloc[target_index + 1:target_index + 1 + n_days]['date'].tolist()
        else:
            # 没有足够的后续日期，返回所有可用的后续日期
            next_dates = sorted_df.iloc[target_index + 1:]['date'].tolist()
            print(f"只有 {len(next_dates)} 个后续日期可用，少于请求的 {n_days} 个")

            calendar = CalendarService()
            working_days_df = calendar.load_next_n_working_days_calendar(formatted_date, formatted_date, n_days)
            last_trade_date = pd.to_datetime(working_days_df['trade_date'].iloc[-1]).strftime('%Y-%m-%d')
            return last_trade_date

        last_date = next_dates[-1] if next_dates else None
        return last_date


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

    def test_multi_series_historical_distribution_XAU_rolling(self):
        """多线模拟 - LogNormal Distribution - Gold"""
        monteCarloRandomManager = MonteCarloRandomManager()
        inquiryManager = InquiryManager()

        start_date = datetime.strptime('2025-01-01', '%Y-%m-%d')
        formatted_start_date = start_date.strftime('%Y-%m-%d')
        #end_date = '2025-12-31'
        end_date = '2026-02-13'
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

    def create_union_dataframe(cls, original_dataframe, results_df):
        """
        步骤3: 用original_dataframe的trade_date union results_df的predict_date
        """
        print("\n=== 步骤3: 创建union DataFrame ===")

        # 获取original_dataframe的trade_date索引
        #original_dates = set(original_dataframe.index)
        original_dates = set(original_dataframe['date'])

        # 获取results_df的predict_date列
        predict_dates = set(results_df['predict_date'])

        # 执行union操作
        union_dates = list(original_dates.union(predict_dates))

        # 确保所有日期都是字符串格式，然后排序
        union_dates_str = [str(date) for date in union_dates]
        union_dates_sorted = sorted(union_dates_str)

        # 创建新的DataFrame，确保trade_date唯一且正序
        all_dataframe = pd.DataFrame(index=union_dates_sorted)
        all_dataframe.index.name = 'trade_date'

        # 验证结果
        print(f"Union后的唯一日期数量: {len(all_dataframe)}")
        print(f"是否按正序排列: {all_dataframe.index.is_monotonic_increasing}")
        print("Union后的日期列表:")
        print(list(all_dataframe.index))

        return all_dataframe

    def left_join_with_original(cls, all_dataframe, original_dataframe):
        """
        步骤4: 用all_dataframe作为左表连接original_dataframe，将original_dataframe的值带入all_dataframe
        """
        print("\n=== 步骤4: 左连接original_dataframe并带入值 ===")

        # 重置索引以便进行连接
        all_reset = all_dataframe.reset_index()
        original_reset = original_dataframe.reset_index()

        # 执行左连接，连接key为trade_date，将original_dataframe的值带入
        # joined_dataframe = pd.merge(
        #     all_reset,
        #     original_reset,
        #     #on='trade_date',
        #     on='date',
        #     how='left'
        # )
        joined_dataframe = pd.merge(
            all_reset,
            original_reset,
            left_on='trade_date',
            right_on='date',
            how='left'
        )

        # 验证结果 - 显示哪些original值被成功带入
        original_columns = ['open', 'close', 'low', 'high', 'pct_change']
        print(f"成功带入的original列: {[col for col in original_columns if col in joined_dataframe.columns]}")
        print(f"左连接后形状: {joined_dataframe.shape}")
        print("左连接后的列:", list(joined_dataframe.columns))
        print("左连接结果 (显示带入的original值):")
        print(joined_dataframe[['trade_date'] + [col for col in original_columns if col in joined_dataframe.columns]].head())

        return joined_dataframe

    def final_left_join_operation(cls, all_dataframe, results_df):
        """
        步骤5: 用all_dataframe作为左表连接results_df
        """
        print("\n=== 步骤5: 最终左连接操作 ===")

        # 重置索引以便操作
        all_reset = all_dataframe.reset_index()
        results_reset = results_df.reset_index()

        # 用all_dataframe的trade_date作为左表join results_df的predict_date
        final_dataframe = pd.merge(
            all_reset,
            results_reset,
            left_on='trade_date',
            right_on='predict_date',
            how='left'
        )

        # 步骤6: 把NaN值用0填充
        #final_dataframe = final_dataframe.fillna(0)

        # 验证结果
        print(f"最终左连接后形状: {final_dataframe.shape}")
        print("最终左连接后的列:", list(final_dataframe.columns))
        print("最终左连接结果 (NaN已填充为0):")
        print(final_dataframe)

        # 验证NaN值处理
        print(f"NaN值数量: {final_dataframe.isnull().sum().sum()}")

        return final_dataframe

    def run_complete_validation_test(cls, original_dataframe, results_df):
        """
        运行完整的带验证的测试流程
        """
        print("开始完整的带验证DataFrame测试...")
        print("=" * 60)

        try:

            # 步骤3: 创建union DataFrame
            print("\n" + "=" * 60)
            all_dataframe = cls.create_union_dataframe(original_dataframe, results_df)

            # 步骤4: 左连接original_dataframe并带入值
            print("\n" + "=" * 60)
            intermediate_result = cls.left_join_with_original(all_dataframe, original_dataframe)

            # 步骤5-6: 最终左连接操作并填充NaN值
            print("\n" + "=" * 60)
            final_result = cls.final_left_join_operation(intermediate_result, results_df)

            # 选出需要的字段
            final_result_copy = final_result.copy()
            columns_to_keep = ['trade_date', 'open', 'close', 'low', 'high', 'pct_change',
                               'var_lower_bound', 'var_upper_bound', 'average', 'median_value']
            available_columns = [col for col in columns_to_keep if col in final_result_copy.columns]
            final_result_copy = final_result_copy[available_columns]

            file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_normal", "xlsx")
            final_result_copy.to_excel(file_full_name)
            # 创建折线图
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates

            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei']
            plt.rcParams['axes.unicode_minus'] = False

            # 准备绘图数据
            plot_data = final_result_copy.copy()

            # 处理日期列 - 先清理None值和无效数据
            if 'trade_date' in plot_data.columns:
                # 移除None值和空值
                plot_data = plot_data.dropna(subset=['trade_date'])
                # 移除空字符串
                plot_data = plot_data[plot_data['trade_date'] != '']
                # 移除'None'字符串
                plot_data = plot_data[plot_data['trade_date'] != 'None']

                # 转换为日期类型，使用更宽松的格式解析
                try:
                    plot_data['trade_date'] = pd.to_datetime(plot_data['trade_date'], format='mixed', errors='coerce')
                except:
                    plot_data['trade_date'] = pd.to_datetime(plot_data['trade_date'], errors='coerce')

                # 移除转换失败的行
                plot_data = plot_data.dropna(subset=['trade_date'])
                plot_data = plot_data.sort_values('trade_date')

            # 检查是否有足够的数据绘图
            if len(plot_data) == 0:
                print("警告: 没有足够的有效数据进行绘图")
                return

            # 设置图形大小
            plt.figure(figsize=(12, 8))

            # 绘制多条线
            x_data = plot_data['trade_date']

            # 绘制各条线（添加数据存在性检查）
            line_count = 0
            if 'close' in plot_data.columns and not plot_data['close'].isna().all():
                plt.plot(x_data, plot_data['close'],  linewidth=2, label='收盘价')
                line_count += 1

            if 'var_lower_bound' in plot_data.columns and not plot_data['var_lower_bound'].isna().all():
                plt.plot(x_data, plot_data['var_lower_bound'], linestyle='--', linewidth=1, label='VaR下界')
                line_count += 1

            if 'var_upper_bound' in plot_data.columns and not plot_data['var_upper_bound'].isna().all():
                plt.plot(x_data, plot_data['var_upper_bound'], linestyle='--', linewidth=1, label='VaR上界')
                line_count += 1

            if 'average' in plot_data.columns and not plot_data['average'].isna().all():
                plt.plot(x_data, plot_data['average'], linewidth=2, label='平均值')
                line_count += 1

            if 'median_value' in plot_data.columns and not plot_data['median_value'].isna().all():
                plt.plot(x_data, plot_data['median_value'],  linewidth=2, label='中位数')
                line_count += 1

            # 如果没有有效的线条，不显示图表
            if line_count == 0:
                print("警告: 没有有效的数据列可以绘图")
                return

            # 设置图表属性
            plt.xlabel('交易日期')
            plt.ylabel('数值')
            plt.title('蒙特卡洛模拟结果趋势图')
            plt.legend()
            plt.grid(True, alpha=0.3)

            # 格式化x轴日期显示
            if len(plot_data) > 0:
                plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(plot_data) // 10)))
                plt.xticks(rotation=45)

            # 调整布局
            plt.tight_layout()

            # 显示图表
            plt.show()

            # 打印数据统计信息
            print("=== 图表数据统计 ===")
            print(f"有效数据点数量: {len(plot_data)}")
            for col in ['close', 'var_lower_bound', 'var_upper_bound', 'average', 'median_value']:
                if col in plot_data.columns:
                    valid_data = plot_data[col].dropna()
                    if len(valid_data) > 0:
                        print(
                            f"{col}: 最小值={valid_data.min():.2f}, 最大值={valid_data.max():.2f}, 平均值={valid_data.mean():.2f}")

            print("\n" + "=" * 60)
            print("✅ 所有测试通过! 数据生成、合并和NaN处理操作已完成。")

        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            raise


if __name__ == "__main__":
    monteCarloTest = MonteCarloRandomTest()

    # 执行各个测试案例
    # monteCarloTest.test_single_line_normal_distribute()
    # monteCarloTest.test_single_line_lognormal_distribute()
    # monteCarloTest.test_multi_series_normal_distribution_citi()
    # monteCarloTest.test_multi_series_lognormal_distribution_citi()
    # monteCarloTest.test_multi_series_lognormal_distribution_jpm()
    # monteCarloTest.test_multi_series_lognormal_distribution_pudong_2022()
    # monteCarloTest.test_multi_series_lognormal_distribution_pudong_2024()
    # monteCarloTest.test_multi_series_lognormal_distribution_lvcw()
    # monteCarloTest.test_multi_stock_multi_series_lognormal_distribution()

    # 用不同方式对上海金价进行分析， lognormal/historical/historical_rolling
    # monteCarloTest.test_multi_series_lognormal_distribution_sge()
    # monteCarloTest.test_multi_series_historical_distribution_sge()
    monteCarloTest.test_multi_series_historical_distribution_sge_rolling()

    # 用不同方式对上海金价%进行分析， lognormal/historical/historical_rolling
    # monteCarloTest.test_multi_series_lognormal_distribution_sge_pctchange()
    # monteCarloTest.test_multi_series_historical_distribution_sge_pctchange()
    # monteCarloTest.test_multi_series_historical_distribution_sge_pct_change_rolling()

    # 用不同方式对伦敦金进行分析， lognormal/historical/historical_rolling
    # monteCarloTest.test_multi_series_historical_distribution_XAU_rolling()

    # monteCarloTest.test_multi_series_lognormal_distribution_treasury_yield()


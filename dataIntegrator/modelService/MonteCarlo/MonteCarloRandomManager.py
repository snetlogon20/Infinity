import pandas
from dataIntegrator.modelService.MonteCarlo.MonteCarloRandom import MonteCarloRandom
from dataIntegrator.plotService.LinePlotManager import LinePlotManager


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
    def simulation_multi_series(cls, dataFrame, simulat_params, return_step_stats=False):
        monteCarloRandom = MonteCarloRandom()
        return monteCarloRandom.simulation_multi_series(dataFrame, simulat_params, return_step_stats)

    @classmethod
    def draw_plot(cls, all_lines, simulat_params, stats, var_lower_bound, var_upper_bound, average, median_value,
                  step_stats_list=None):

        S = stats["Init_Value"][0]
        times = simulat_params["times"]
        series = simulat_params["series"]
        alpha = simulat_params["alpha"]
        dist_type = simulat_params["distribution_type"]

        # 股票信息
        market = simulat_params.get("market", "Unknown")
        stock = simulat_params.get("stock", "Unknown")
        start_date = simulat_params.get("start_date", "Unknown")
        end_date = simulat_params.get("end_date", "Unknown")

        from matplotlib import pyplot as plt

        paths = {}
        for line_id, x, y in all_lines:
            if line_id not in paths:
                paths[line_id] = {'x': [], 'y': []}
            paths[line_id]['x'].append(x)
            paths[line_id]['y'].append(y)

        # 绘制所有路径
        plt.figure(figsize=(12, 6))
        for line_id, data in paths.items():
            plt.plot(data['x'], data['y'], alpha=0.5, label=f'Path {line_id}' if line_id < 5 else "")

        # 添加VaR红线
        plt.axhline(y=var_lower_bound, color='red', linestyle='--', linewidth=2,
                    label=f'VaR ({alpha * 100:.0f}%): {var_lower_bound:.2f}')
        # 添加VaR红线
        plt.axhline(y=var_upper_bound, color='red', linestyle='--', linewidth=2,
                    label=f'VaR ({alpha * 100:.0f}%): {var_upper_bound:.2f}')

        # 添加average
        plt.axhline(y=average, color='blue', linestyle='--', linewidth=2,
                    label=f'VaR AVG ({alpha * 100:.0f}%): {average:.2f}')

        # 添加median_value
        plt.axhline(y=median_value, color='green', linestyle='--', linewidth=2,
                    label=f'VaR MEDIAN ({alpha * 100:.0f}%): {median_value:.2f}')

        # 绘制逐步分位数曲线（step_stats_list）
        if step_stats_list and len(step_stats_list) > 0:
            steps = [s['step'] for s in step_stats_list]
            step_lowers = [s['var_lower_bound'] for s in step_stats_list]
            step_uppers = [s['var_upper_bound'] for s in step_stats_list]
            step_avgs = [s['average'] for s in step_stats_list]
            step_meds = [s['median_value'] for s in step_stats_list]

            plt.plot(steps, step_lowers, color='darkred', linestyle=':', linewidth=2,
                     marker='o', label='Step VaR Lower')
            plt.plot(steps, step_uppers, color='darkgreen', linestyle=':', linewidth=2,
                     marker='o', label='Step VaR Upper')
            plt.plot(steps, step_avgs, color='darkblue', linestyle='-.', linewidth=2,
                     marker='s', label='Step Average')
            plt.plot(steps, step_meds, color='purple', linestyle='-.', linewidth=2,
                     marker='d', label='Step Median')

        plt.xlabel('Time Step')
        plt.ylabel('Value')
        plt.title('Monte Carlo Simulation Paths')
        plt.legend()
        plt.grid(True)
        plt.show()

        return

        # dataframe = pandas.DataFrame(all_lines, columns=['Path', 'Step', 'Value'])
        # df_pivot_MC = dataframe.pivot(index='Step', columns='Path', values='Value').reset_index(drop=True)
        # df_pivot_MC.columns = [f"path{col}" for col in df_pivot_MC.columns]
        # print(df_pivot_MC)
        #
        # df_pivot_MC.reset_index(inplace=True)
        # df_pivot_MC['step'] = df_pivot_MC.index
        # df_pivot_MC = df_pivot_MC.reindex(columns=['step'] + [col for col in df_pivot_MC.columns if col != 'step'])
        #
        # column_names = df_pivot_MC.columns.tolist()
        # path_columns = [col for col in column_names if col.startswith("path")]
        # yColumn = ",".join(path_columns)
        #
        # param_dict = {}
        # param_dict["isPlotRequired"] = "yes"
        # param_dict["results"] = df_pivot_MC
        # param_dict["plotRequirement"] = {}
        # param_dict["plotRequirement"]["PlotX"] = "index"
        # param_dict["plotRequirement"]["PlotY"] = yColumn
        # param_dict["plotRequirement"]["plotTitle"] = f"Monte Carlo Simulation ({dist_type})\n"
        # f'Stock: {market}-{stock} Between:{start_date} ~ {end_date}\n'
        # f"Paths: {series}, Steps: {times}, Initial Value: {S:.2f}, Mean: {stats['Mean'][0]:.6f}, SDV: {stats['Std_Dev'][0]:.6f}"
        # param_dict["plotRequirement"]["xlabel"] = "days"
        # param_dict["plotRequirement"]["ylabel"] = "points"
        #
        # linePlotManager = LinePlotManager()
        # linePlotManager.draw_plot(param_dict)

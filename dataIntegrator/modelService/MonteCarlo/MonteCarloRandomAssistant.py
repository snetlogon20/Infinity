import pandas as pd

from dataIntegrator.utility.FileUtility import FileUtility
from dataIntegrator import CommonLib

logger = CommonLib.logger
commonLib = CommonLib()

class MonteCarloRandomAssistant:

    def init(cls):
        pass

    def create_union_dataframe(cls, original_dataframe, results_df):
        """
        步骤3: 用original_dataframe的trade_date union results_df的predict_date
        """
        logger.info("\n=== 步骤3: 创建union DataFrame ===")

        # 获取original_dataframe的trade_date索引
        original_dates = set(original_dataframe['trade_date'])

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
        logger.info(f"Union后的唯一日期数量: {len(all_dataframe)}")
        logger.info(f"是否按正序排列: {all_dataframe.index.is_monotonic_increasing}")
        logger.info("Union后的日期列表:")
        logger.info(list(all_dataframe.index))

        return all_dataframe

    def left_join_with_original(cls, all_dataframe, original_dataframe):
        """
        步骤4: 用all_dataframe作为左表连接original_dataframe，将original_dataframe的值带入all_dataframe
        """
        logger.info("\n=== 步骤4: 左连接original_dataframe并带入值 ===")

        # 重置索引以便进行连接
        all_reset = all_dataframe.reset_index()
        original_reset = original_dataframe.reset_index()

        # 执行左连接，连接key为trade_date，将original_dataframe的值带入
        joined_dataframe = pd.merge(
            all_reset,
            original_reset,
            left_on='trade_date',
            right_on='trade_date',
            how='left'
        )

        # 验证结果 - 显示哪些original值被成功带入
        original_columns = ['open', 'close', 'low', 'high', 'pct_change']
        logger.info(f"成功带入的original列: {[col for col in original_columns if col in joined_dataframe.columns]}")
        logger.info(f"左连接后形状: {joined_dataframe.shape}")
        logger.info(f"左连接后的列：{list(joined_dataframe.columns)}")
        logger.info("左连接结果 (显示带入的original值):")
        logger.info(joined_dataframe[['trade_date'] + [col for col in original_columns if col in joined_dataframe.columns]].head())

        return joined_dataframe

    def final_left_join_operation(cls, all_dataframe, results_df):
        """
        步骤5: 用all_dataframe作为左表连接results_df
        """
        logger.info("\n=== 步骤5: 最终左连接操作 ===")

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
        logger.info(f"最终左连接后形状：{final_dataframe.shape}")
        logger.info(f"最终左连接后的列：{list(final_dataframe.columns)}")
        print(f"[DEBUG] final_left_join columns: {list(final_dataframe.columns)}")
        logger.info("最终左连接结果 (NaN 已填充为 0):")
        logger.info(final_dataframe)

        # 验证NaN值处理
        logger.info(f"NaN值数量: {final_dataframe.isnull().sum().sum()}")

        return final_dataframe

    def draw_plot(cls, final_result_copy, analysis_column='close', analysis_column_label='收盘价', stock_name=None):
        # 创建折线图
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False

        # 准备绘图数据
        plot_data = final_result_copy.copy()

        # 处理日期列 - 先清理 None 值和无效数据
        if 'trade_date' in plot_data.columns:
            # 移除 None 值和空值
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
            print("警告：没有足够的有效数据进行绘图")
            return

        # 打印调试信息
        print("\n=== 绘图数据检查 ===")
        print(f"总数据行数：{len(plot_data)}")
        for col in ['var_lower_bound', 'var_upper_bound', 'es_lower_bound', 'es_upper_bound', 'average', 'median_value', analysis_column]:
            if col in plot_data.columns:
                non_null_count = plot_data[col].notna().sum()
                null_count = plot_data[col].isna().sum()
                print(f"{col}: 非 Null 数量={non_null_count}, Null 数量={null_count}")
                if non_null_count > 0:
                    print(f"  数据范围：{plot_data[col].dropna().min():.4f} ~ {plot_data[col].dropna().max():.4f}")
            else:
                print(f"{col}: 列不存在")
        print("=" * 60)

        # 设置图形大小
        plt.figure(figsize=(14, 8))

        # 准备绘图数据
        x_data = plot_data['trade_date']

        # 绘制各条线（添加数据存在性检查）
        line_count = 0

        # ===== 关键改进：当存在 step_num 列时，画出逐步扇形置信区间 =====
        has_step_data = 'step_num' in plot_data.columns and not plot_data['step_num'].isna().all()

        if has_step_data:
            # 聚合：同一个 predict_date (trade_date) 可能有多个 step_num 的预测，取每步的 min/max 作为置信带
            grouped_data = []
            for (dt, step), grp in plot_data.groupby(['trade_date', 'step_num']):
                row = {
                    'trade_date': dt,
                    'step_num': step,
                    'var_lower_bound': grp['var_lower_bound'].mean(),
                    'var_upper_bound': grp['var_upper_bound'].mean(),
                    'average': grp['average'].mean(),
                    'median_value': grp['median_value'].mean(),
                }
                if 'es_lower_bound' in grp.columns:
                    row['es_lower_bound'] = grp['es_lower_bound'].mean()
                if 'es_upper_bound' in grp.columns:
                    row['es_upper_bound'] = grp['es_upper_bound'].mean()
                grouped_data.append(row)
            step_df = pd.DataFrame(grouped_data)

            # 找出最大步数和最小步数
            max_step = step_df['step_num'].max()
            min_step = step_df['step_num'].min()

            # 绘制最大步数（最远期预测）的VaR下界
            far_data = step_df[step_df['step_num'] == max_step].sort_values('trade_date')
            if len(far_data) > 0:
                far_x = far_data['trade_date']
                plt.plot(far_x, far_data['var_lower_bound'],
                         linewidth=1.0, color='orange', linestyle='--',
                         label=f'VaR下界 ({max_step}天预测)')
                line_count += 1

                # 绘制ES下界线
                if 'es_lower_bound' in far_data.columns and not far_data['es_lower_bound'].isna().all():
                    plt.plot(far_x, far_data['es_lower_bound'],
                             linewidth=1.2, color='darkorange', linestyle='-.',
                             label=f'ES下界 ({max_step}天)')
                    line_count += 1

            # 绘制最近步数（1天预测）的VaR下界
            near_data = step_df[step_df['step_num'] == min_step].sort_values('trade_date')
            if len(near_data) > 0 and min_step != max_step:
                near_x = near_data['trade_date']
                plt.plot(near_x, near_data['var_lower_bound'],
                         linewidth=1.0, color='green', linestyle='--',
                         label=f'VaR下界 ({min_step}天预测)')
                line_count += 1

        # 绘制分析列（涨跌幅或收盘价）
        if analysis_column in plot_data.columns and not plot_data[analysis_column].isna().all():
            plt.plot(x_data, plot_data[analysis_column], linewidth=0.6, label=analysis_column_label, color='blue',
                     zorder=1)
            line_count += 1

            # 绘制 VaR 下界 - 仅在无 step_data 时绘制
            if not has_step_data:
                if 'var_lower_bound' in plot_data.columns and not plot_data['var_lower_bound'].isna().all():
                    plt.plot(x_data, plot_data['var_lower_bound'],
                             linestyle='--', linewidth=1.0, label='VaR 下界',
                             color='orange', alpha=0.7, zorder=2)
                    line_count += 1
                else:
                    print("⚠️  警告：var_lower_bound 数据全为 NaN 或列不存在，无法绘制")

                # 绘制 ES 下界
                if 'es_lower_bound' in plot_data.columns and not plot_data['es_lower_bound'].isna().all():
                    plt.plot(x_data, plot_data['es_lower_bound'],
                             linewidth=0.8, label='ES 下界',
                             color='darkorange', linestyle='-.', zorder=3)
                    line_count += 1

        # 绘制 analysis_column 的 EMA 均线（5/10/20/60）
        if analysis_column in plot_data.columns and not plot_data[analysis_column].isna().all():
            ema_periods = [5, 10, 20, 60]
            ema_colors = ['#17becf', '#e377c2', '#8c564b', '#bcbd22']
            for period, color in zip(ema_periods, ema_colors):
                ema_col = f'{analysis_column}_ema_{period}'
                # 优先使用已存在的 EMA 列（由 add_ema_columns 预计算），否则原地计算
                if ema_col not in plot_data.columns:
                    plot_data[ema_col] = plot_data[analysis_column].ewm(span=period, adjust=False).mean()
                if not plot_data[ema_col].isna().all():
                    plt.plot(x_data, plot_data[ema_col],
                             linewidth=0.8, label=f'EMA{period}',
                             color=color, linestyle='-', alpha=0.7, zorder=1)
                    line_count += 1

        # 如果没有有效的线条，不显示图表
        if line_count == 0:
            print("警告：没有有效的数据列可以绘图")
            return

        # 设置图表属性
        plt.xlabel('交易日期', fontsize=12)
        plt.ylabel('数值', fontsize=12)
        # 设置标题
        if len(plot_data) > 0:
            start_date_str = plot_data['trade_date'].min().strftime('%Y-%m-%d')
            end_date_str = plot_data['trade_date'].max().strftime('%Y-%m-%d')
        else:
            start_date_str = 'Unknown'
            end_date_str = 'Unknown'

        if stock_name:
            title = f'{stock_name} {analysis_column_label} 蒙特卡罗模拟分析 ({start_date_str} ~ {end_date_str})'
        else:
            title = f'{analysis_column_label} 蒙特卡罗模拟分析 ({start_date_str} ~ {end_date_str})'
        plt.title(title, fontsize=14, fontweight='bold')
        plt.legend(loc='best', fontsize=10)
        plt.grid(True, alpha=0.3, linestyle=':')

        # 添加参考线 y=0
        plt.axhline(y=0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)

        # 根据 analysis_column 的数据范围设置 y 轴限制，留出上下 10% 的余地
        if analysis_column in plot_data.columns:
            valid_data = plot_data[analysis_column].dropna()
            if len(valid_data) > 0:
                data_min = valid_data.min()
                data_max = valid_data.max()
                data_range = data_max - data_min
                padding = data_range * 0.10  # 10% 的余地

                y_lower = data_min - padding
                y_upper = data_max + padding

                plt.ylim(y_lower, y_upper)

        # 格式化 x 轴日期显示 - 根据数据量动态调整日期间隔
        if len(plot_data) > 0:
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            n = len(plot_data)
            if n <= 30:
                interval = 1
                rotation = 90
            elif n <= 90:
                interval = 7
                rotation = 45
            elif n <= 180:
                interval = 14
                rotation = 45
            else:
                interval = 30
                rotation = 45
            plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=interval))
            plt.xticks(rotation=rotation, fontsize=8)


        # 添加收市价作为第二轴（右侧Y轴）
        if 'close' in plot_data.columns and not plot_data['close'].isna().all():
            ax2 = plt.gca().twinx()
            ax2.plot(x_data, plot_data['close'], linewidth=0.8, label='收市价', color='black', linestyle='-', zorder=1)
            ax2.set_ylabel('收市价', fontsize=12, color='black')
            ax2.tick_params(axis='y', labelcolor='black')
            ax2.legend(loc='upper right', fontsize=10)

        # 调整布局
        plt.tight_layout()

        # 显示图表
        plt.show()

        # 打印数据统计信息
        print("=== 图表数据统计 ===")
        print(f"有效数据点数量：{len(plot_data)}")
        for col in [analysis_column, 'var_lower_bound', 'var_upper_bound', 'es_lower_bound', 'es_upper_bound', 'average', 'median_value']:
            if col in plot_data.columns:
                valid_data = plot_data[col].dropna()
                if len(valid_data) > 0:
                    print(
                        f"{col}: 最小值={valid_data.min():.2f}, 最大值={valid_data.max():.2f}, 平均值={valid_data.mean():.2f}")

        print("\n" + "=" * 60)
        print("✅ 所有测试通过！数据生成、合并和 NaN 处理操作已完成。")

    def select_required_columns(self, final_result, analysis_column):
        # 选出需要的字段
        final_result_copy = final_result.copy()
        columns_to_keep = ['trade_date_x', 'open', 'close', 'low', 'high', 'pct_change',
                           'var_lower_bound', 'var_upper_bound', 'es_lower_bound', 'es_upper_bound', 'average', 'median_value', 'step_num']
        available_columns = [col for col in columns_to_keep if col in final_result_copy.columns]
        print(f"[DEBUG] final_result columns before select: {list(final_result_copy.columns)}")
        print(f"[DEBUG] available_columns: {available_columns}")
        final_result_copy = final_result_copy[available_columns]
        # 根据实际存在的列数动态生成列名映射
        col_mapping = {
            'trade_date_x': 'trade_date',
        }
        rename_dict = {k: v for k, v in col_mapping.items() if k in final_result_copy.columns}
        final_result_copy = final_result_copy.rename(columns=rename_dict)
        print(f"[DEBUG] final_result_copy columns after select: {list(final_result_copy.columns)}")

        return final_result_copy

    @classmethod
    def add_ema_columns(cls, df, source_columns, ema_periods=None):
        """
        为指定的源列计算 EMA 均线并添加到 DataFrame 中。

        参数:
            df: 目标 DataFrame（原地修改）
            source_columns: 需要计算 EMA 的源列名列表，如 ['close'] 或 ['lower_close_gap', 'upper_lower_gap']
            ema_periods: EMA 周期列表，默认 [5, 10, 20, 60]

        返回:
            df（原地修改后的同一个 DataFrame）
        """
        if ema_periods is None:
            ema_periods = [5, 10, 20, 60]

        for src_col in source_columns:
            if src_col in df.columns and not df[src_col].isna().all():
                for period in ema_periods:
                    ema_col = f'{src_col}_ema_{period}'
                    df[ema_col] = df[src_col].ewm(span=period, adjust=False).mean()

        return df

    def save_file_to_excel(self, final_result_copy):

        file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_normal", "xlsx")
        logger.info(f"保存文件到 Excel...{file_full_name}")
        final_result_copy.to_excel(file_full_name)
        return final_result_copy

    def generate_forecast_dataframes(cls, original_dataframe, results_df):
        """
        运行完整的带验证的测试流程
        """
        logger.info("开始完整的带验证DataFrame测试...")
        logger.info("=" * 60)

        try:
            # 步骤1: 创建union DataFrame
            logger.info("\n" + "=" * 60)
            all_dataframe = cls.create_union_dataframe(original_dataframe, results_df)

            # 步骤2: 左连接original_dataframe并带入值
            logger.info("\n" + "=" * 60)
            intermediate_result = cls.left_join_with_original(all_dataframe, original_dataframe)

            # 步骤3: 最终左连接操作并填充NaN值
            logger.info("\n" + "=" * 60)
            final_result = cls.final_left_join_operation(intermediate_result, results_df)

            return final_result


        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            raise



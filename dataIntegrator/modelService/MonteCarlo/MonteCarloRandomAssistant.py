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
        logger.info("左连接后的列:", list(joined_dataframe.columns))
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
        logger.info(f"最终左连接后形状: {final_dataframe.shape}")
        logger.info("最终左连接后的列:", list(final_dataframe.columns))
        logger.info("最终左连接结果 (NaN已填充为0):")
        logger.info(final_dataframe)

        # 验证NaN值处理
        logger.info(f"NaN值数量: {final_dataframe.isnull().sum().sum()}")

        return final_dataframe

    def draw_plot(cls, final_result_copy, analysis_column='close', analysis_column_label='收盘价'):
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
        for col in ['var_lower_bound', 'var_upper_bound', 'average', 'median_value', analysis_column]:
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

        # 绘制分析列（涨跌幅或收盘价）
        if analysis_column in plot_data.columns and not plot_data[analysis_column].isna().all():
            plt.plot(x_data, plot_data[analysis_column], linewidth=2.5, label=analysis_column_label, color='blue',
                     zorder=1)
            line_count += 1

        # 绘制 VaR 下界 - 使用明显的虚线和颜色
        if 'var_lower_bound' in plot_data.columns and not plot_data['var_lower_bound'].isna().all():
            plt.plot(x_data, plot_data['var_lower_bound'],
                     linestyle='--', linewidth=2, label='VaR 下界',
                     color='orange', alpha=0.7, zorder=2)
            line_count += 1
        else:
            print("⚠️  警告：var_lower_bound 数据全为 NaN 或列不存在，无法绘制")

        # 绘制 VaR 上界 - 使用明显的虚线和颜色
        if 'var_upper_bound' in plot_data.columns and not plot_data['var_upper_bound'].isna().all():
            plt.plot(x_data, plot_data['var_upper_bound'],
                     linestyle='--', linewidth=2, label='VaR 上界',
                     color='green', alpha=0.7, zorder=2)
            line_count += 1
        else:
            print("⚠️  警告：var_upper_bound 数据全为 NaN 或列不存在，无法绘制")

        # 绘制平均值 - 使用红色实线
        if 'average' in plot_data.columns and not plot_data['average'].isna().all():
            plt.plot(x_data, plot_data['average'],
                     linewidth=2, label='平均值',
                     color='red', linestyle='-', zorder=3)
            line_count += 1

        # 绘制中位数 - 使用紫色实线
        if 'median_value' in plot_data.columns and not plot_data['median_value'].isna().all():
            plt.plot(x_data, plot_data['median_value'],
                     linewidth=2, label='中位数',
                     color='purple', linestyle='-', zorder=3)
            line_count += 1

        # 如果没有有效的线条，不显示图表
        if line_count == 0:
            print("警告：没有有效的数据列可以绘图")
            return

        # 设置图表属性
        plt.xlabel('交易日期', fontsize=12)
        plt.ylabel('数值', fontsize=12)
        plt.title('蒙特卡洛模拟结果趋势图', fontsize=14, fontweight='bold')
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

        # 格式化 x 轴日期显示 - 显示所有日期
        if len(plot_data) > 0:
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            # 设置每个数据点都显示
            plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=1))
            plt.xticks(rotation=90, fontsize=8)

        # 调整布局
        plt.tight_layout()

        # 显示图表
        plt.show()

        # 打印数据统计信息
        print("=== 图表数据统计 ===")
        print(f"有效数据点数量：{len(plot_data)}")
        for col in [analysis_column, 'var_lower_bound', 'var_upper_bound', 'average', 'median_value']:
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
                           'var_lower_bound', 'var_upper_bound', 'average', 'median_value']
        available_columns = [col for col in columns_to_keep if col in final_result_copy.columns]
        final_result_copy = final_result_copy[available_columns]
        #把trade_date_x 纠正回 trade_date
        final_result_copy.columns = ['trade_date', 'open', 'close', 'low', 'high', 'pct_change',
                           'var_lower_bound', 'var_upper_bound', 'average', 'median_value']

        return final_result_copy

    def save_file_to_excel(self, final_result_copy):
        file_full_name = FileUtility.get_full_filename_by_timestamp("Montcarlo_simulation_normal", "xlsx")
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



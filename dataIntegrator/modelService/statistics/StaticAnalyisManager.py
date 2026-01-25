import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from dataIntegrator.analysisService.InquiryManager import InquiryManager

class StaticAnalysisManager:
    def __init__(self):
        # 设置支持中文的字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun']
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

        # 设置pandas显示选项，确保所有列都显示
        pd.set_option('display.float_format', '{:.2f}'.format)
        pd.set_option('display.max_columns', None)  # 显示所有列
        pd.set_option('display.width', None)        # 不限制显示宽度
        pd.set_option('display.max_colwidth', None) # 不限制列宽
        pd.set_option('display.expand_frame_repr', False)  # 不要换行显示

    def get_data_from_sql(self, sql):
        """
        从SQL查询获取数据
        """
        dataFrame = InquiryManager().get_sql_dataset(sql)
        return dataFrame.copy()

    def calculate_basic_statistics(self, df):
        """
        计算基本统计量
        """
        statistics = pd.DataFrame({
            '均值': df.mean(),
            '方差': df.var(),
            '标准差': df.std(),
            '均值/标准差': df.mean() / df.std(),
            '最小值': df.min(),
            '25%分位数': df.quantile(0.25),
            '中位数': df.median(),
            '75%分位数': df.quantile(0.75),
            '最大值': df.max(),
            '偏度': df.skew(),
            '峰度': df.kurtosis()
        })

        # 按均值列从小到大排序
        statistics = statistics.sort_values(by='均值', ascending=True)
        return statistics

    def display_statistics(self, statistics):
        """
        显示统计量信息
        """
        print("数据预览:")
        print(statistics.head())
        print("\n数据形状:", statistics.shape)

        print("基本统计量:")
        with pd.option_context('display.float_format', '{:.2f}'.format):
            print(statistics.round(2))

    def minmax_normalize(self, statistics):
        """
        按列进行最小-最大归一化 (0-1缩放)
        """
        statistics_minmax = statistics.copy()
        for col in statistics.columns:
            col_min = statistics[col].min()
            col_max = statistics[col].max()
            if col_max != col_min:  # 避免除零错误
                statistics_minmax[col] = (statistics[col] - col_min) / (col_max - col_min)
            else:
                statistics_minmax[col] = 0  # 如果最大值等于最小值，则设为0

        return statistics_minmax

    def plot_statistics_heatmap(self, statistics, title='统计量热力图 - 按列最小-最大归一化 (X轴: 统计量, Y轴: 产品)'):
        """
        绘制统计量热力图
        """
        statistics_minmax = self.minmax_normalize(statistics)

        plt.figure(figsize=(12, 8))
        sns.heatmap(statistics_minmax, annot=statistics.round(2), fmt='', cmap='RdBu_r', center=0.5,
                    cbar_kws={'label': '归一化值 (0-1)'}, xticklabels=True, yticklabels=True)
        ax = plt.gca()
        ax.xaxis.tick_top()  # 将x轴标签移到顶部
        ax.xaxis.set_label_position('top')  # 将x轴标签位置设置为顶部
        plt.title(title, fontsize=14)
        plt.tight_layout()
        plt.show()

    def plot_single_stat_comparison(self, statistics, stats_to_show, figsize=(16, 6)):
        """
        单独展示每个统计量的对比
        """
        subset_statistics = statistics[stats_to_show]

        n_stats = len(stats_to_show)
        ncols = 2
        nrows = int(np.ceil(n_stats / ncols))

        fig, axes = plt.subplots(nrows, ncols, figsize=(figsize[0], figsize[1] * nrows))
        fig.set_size_inches(19.2, 10.8)  # 设置为接近全屏大小

        if nrows == 1:
            axes = axes.flatten() if ncols > 1 else [axes]
        else:
            axes = axes.flatten()

        for i, stat in enumerate(stats_to_show):
            if i < len(axes):
                ax = axes[i]
                values = subset_statistics[stat]

                bars = ax.bar(range(len(values)), values.values, alpha=0.7)
                ax.set_title(f'{stat} - 各产品对比', fontsize=7)  # 减小标题字体
                ax.set_xlabel('产品', fontsize=7)  # 减小x轴标签字体
                ax.set_ylabel('数值', fontsize=7)  # 减小y轴标签字体
                ax.set_xticks(range(len(values)))
                ax.set_xticklabels(values.index, rotation=45, ha='right', fontsize=7)  # 减小x轴刻度标签字体
                ax.tick_params(axis='x', labelsize=6)  # 减小x轴刻度标签字体
                ax.tick_params(axis='y', labelsize=6)  # 减小y轴刻度标签字体

                # 在条形图上添加数值标签
                for bar, value in zip(bars, values.values):
                    ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height(),
                            f'{value:.2f}', ha='center', va='bottom', fontsize=5)  # 减小数值标签字体

        # 隐藏多余的子图
        for j in range(i + 1, len(axes)):
            axes[j].set_visible(False)

        plt.tight_layout()
        plt.show()

    def analyze(self, sql, stats_to_show=['均值', '标准差', '均值/标准差', '偏度', '峰度']):
        """
        执行完整的分析流程
        """
        # 获取数据
        df = self.get_data_from_sql(sql)

        # 计算统计量
        statistics = self.calculate_basic_statistics(df)

        # 显示统计量
        self.display_statistics(statistics)

        # 绘制热力图
        self.plot_statistics_heatmap(statistics)

        # 绘制单个统计量对比图
        self.plot_single_stat_comparison(statistics, stats_to_show)

        return statistics


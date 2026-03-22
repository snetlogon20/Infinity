from sklearn.isotonic import IsotonicRegression
import pandas as pd
import numpy as np
from dataIntegrator.analysisService.InquiryManager import InquiryManager
from dataIntegrator import CommonLib, CommonParameters
from matplotlib import pyplot as plt
import streamlit as st

logger = CommonLib.logger

class IsotonicRegressionAnalyst:
    """
    保序回归分析师
    用于对时间序列数据进行保序回归计算和可视化
    """

    def __init__(self):
        # 设置支持中文的字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun']
        plt.rcParams['axes.unicode_minus'] = False

    def calculate_isotonic_regression(self, dataFrame, x_column, y_column):
        """
        计算保序回归

        参数:
            dataFrame: 输入的数据框
            x_column: X 轴列名（通常是日期或序号）
            y_column: Y 轴列名（需要拟合的目标变量，如 close）

        返回:
            包含保序回归结果的 DataFrame
        """
        try:
            # 复制数据框，避免修改原始数据
            result_df = dataFrame.copy()

            # 提取 X 和 Y 值
            X = result_df[x_column].values
            y = result_df[y_column].values

            # 处理缺失值
            mask = ~np.isnan(y)
            X_clean = X[mask]
            y_clean = y[mask]

            # 如果 X 是日期字符串，转换为数值（使用序号）
            if X_clean.dtype == 'O':  # 对象类型（字符串）
                X_numeric = np.arange(len(X_clean))
            else:
                X_numeric = X_clean.astype(float)

            # 创建并拟合保序回归模型
            isotonic = IsotonicRegression(out_of_bounds='clip')
            isotonic.fit(X_numeric, y_clean)

            # 预测拟合值
            y_fitted = isotonic.predict(X_numeric)

            # 将结果添加到 DataFrame
            result_df[f'{y_column}_isotonic'] = np.nan
            result_df.loc[mask, f'{y_column}_isotonic'] = y_fitted

            # 计算残差（实际值 - 拟合值）
            result_df[f'{y_column}_residual'] = result_df[y_column] - result_df[f'{y_column}_isotonic']

            logger.info(f"保序回归计算完成，数据点数：{len(result_df)}")

            return result_df

        except Exception as e:
            logger.error(f"保序回归计算失败：{str(e)}")
            raise

    def draw_isotonic_plot(self, result_df, x_column, y_column, title=None,
                          figsize=(14, 7), save_path=None):
        """
        绘制保序回归折线图

        参数:
            result_df: 包含保序回归结果的数据框
            x_column: X 轴列名（trade_date）
            y_column: Y 轴列名（close）
            title: 图表标题
            figsize: 图表大小
            save_path: 保存路径（可选）
        """
        try:
            fig, ax = plt.subplots(figsize=figsize)

            # 准备数据
            X = result_df[x_column].values
            y_actual = result_df[y_column].values
            y_fitted = result_df[f'{y_column}_isotonic'].values

            # 如果 X 是日期字符串，使用序号作为 x 轴位置
            if X.dtype == 'O':
                x_numeric = np.arange(len(X))
                use_numeric = True
            else:
                x_numeric = X.astype(float)
                use_numeric = False

            # 绘制实际值
            ax.plot(x_numeric, y_actual, 'o-', label='Actual Close',
                   color='blue', alpha=0.6, linewidth=2, markersize=6)

            # 绘制保序回归拟合值
            ax.plot(x_numeric, y_fitted, 'r-', label='Isotonic Regression Fit',
                   linewidth=2.5, alpha=0.8)

            # 设置图表标题和标签
            if title is None:
                title = f'Isotonic Regression Analysis - {y_column}'

            ax.set_title(title, fontsize=14, fontweight='bold')
            ax.set_xlabel(x_column, fontsize=12)
            ax.set_ylabel(f'{y_column} Price', fontsize=12)

            # 添加网格
            ax.grid(True, alpha=0.3, linestyle='--')

            # 添加图例
            ax.legend(loc='best', fontsize=10)

            # 如果 X 轴是日期，旋转标签以便阅读
            if use_numeric:
                ax.set_xticks(x_numeric[::max(1, len(x_numeric)//20)])
                ax.set_xticklabels(X[::max(1, len(X)//20)], rotation=45, ha='right')

            # 调整布局
            plt.tight_layout()

            # 显示或保存图表
            if CommonParameters.IS_STREAMLIT_ON:
                st.pyplot(fig)
            else:
                plt.show()

            # 保存图表（如果指定了路径）
            if save_path:
                fig.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"图表已保存到：{save_path}")

            return fig

        except Exception as e:
            logger.error(f"绘制保序回归图表失败：{str(e)}")
            raise

    def load_data(self, symbol, start_date, end_date, sql_template=None):
        """
        从 ClickHouse 加载数据

        参数:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            sql_template: SQL 查询模板（可选）

        返回:
            原始 DataFrame
        """
        try:
            inquiryManager = InquiryManager()

            # 格式化日期
            formatted_start_date = start_date.replace('-', '')
            end_date_formatted = end_date.replace('-', '')

            # SQL 查询
            if sql_template is None:
                sql_template = (
                    f"select date as trade_date, open, close, low, high, pct_change "
                    f"from indexsysdb.df_akshare_futures_foreign_hist "
                    f"where symbol='{symbol}' and date>='{formatted_start_date}' "
                    f"and date<='{end_date_formatted}' order by date"
                )

            get_original_data_sql = sql_template.format(
                symbol=symbol,
                formatted_start_date=formatted_start_date,
                end_date_formatted=end_date_formatted
            )

            logger.info(f"执行 SQL 查询：{get_original_data_sql}")
            original_dataFrame = inquiryManager.get_sql_dataset(get_original_data_sql)

            # 检查数据是否为空
            if original_dataFrame.empty:
                logger.warning(f"未查询到数据，symbol={symbol}, date range={start_date}~{end_date}")
                return original_dataFrame

            return original_dataFrame

        except Exception as e:
            logger.error(f"数据加载失败：{str(e)}")
            raise

    def clean_data(self, original_dataFrame, x_column='trade_date', y_column='close'):
        """
        清洗和预处理数据

        参数:
            original_dataFrame: 原始 DataFrame
            x_column: X 轴列名
            y_column: Y 轴列名

        返回:
            清洗后的 DataFrame
        """
        try:
            # 转换数值列为数值类型
            numeric_columns = ['open', 'close', 'low', 'high', 'pct_change']
            for col in numeric_columns:
                if col in original_dataFrame.columns:
                    original_dataFrame[col] = pd.to_numeric(original_dataFrame[col], errors='coerce')

            # 删除有缺失值的行（仅针对需要的列）
            required_columns = [x_column, y_column]
            clean_df = original_dataFrame.dropna(subset=required_columns).reset_index(drop=True)

            logger.info(f"原始数据点数：{len(original_dataFrame)}, 清洗后：{len(clean_df)}")

            return clean_df

        except Exception as e:
            logger.error(f"数据清洗失败：{str(e)}")
            raise

    def analyze_workflow(self, symbol, start_date, end_date,
                         x_column='trade_date', y_column='close',
                         title=None, show_plot=True, sql_template=None):
        """
        完整的保序回归分析流程

        参数:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            x_column: X 轴列名
            y_column: Y 轴列名
            title: 图表标题
            show_plot: 是否显示图表
            sql_template: SQL 查询模板（可选）

        返回:
            包含保序回归结果的 DataFrame
        """
        try:
            # 步骤 1: 加载数据
            original_dataFrame = self.load_data(symbol, start_date, end_date, sql_template)

            # 检查数据是否为空
            if original_dataFrame.empty:
                return original_dataFrame

            # 步骤 2: 清洗数据
            clean_df = self.clean_data(original_dataFrame, x_column, y_column)

            # 步骤 3: 计算保序回归
            result_df = self.calculate_isotonic_regression(clean_df, x_column, y_column)

            # 步骤 4: 绘制图表
            if show_plot:
                self.draw_isotonic_plot(result_df, x_column, y_column, title=title)

            logger.info("保序回归分析完成")

            return result_df

        except Exception as e:
            logger.error(f"保序回归分析流程失败：{str(e)}")
            raise
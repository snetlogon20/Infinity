import pandas as pd
from matplotlib import pyplot as plt
import streamlit as st
import seaborn as sns
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.dataService.ClickhouseService import commonLib
from dataIntegrator.plotService.PlotManagerSuper import PlotManagerSuper

logger = CommonLib.logger
commonLib = CommonLib()

class HeatMapPlotManager(PlotManagerSuper):

    @classmethod
    def draw_plot(self, param_dict):
        logger.info(rf"start - draw_plot")

        try:
            isPlotRequired = param_dict.get("isPlotRequired", "no")
            data_frame = param_dict.get("results", "None")
            PlotTitle = param_dict.get('plotRequirement', {}).get("PlotTitle", "None")
            xlabel = param_dict.get('plotRequirement', {}).get("xlabel", "None")
            ylabel = param_dict.get('plotRequirement', {}).get("ylabel", "None")
        except Exception as e:
            raise commonLib.raise_custom_error(error_code="000102",custom_error_message=rf"Draw plot failed when parsing parameters", e=e)

        try:
            if isPlotRequired != "yes":
                logger.info(rf"isPlotRequired != yes")
                return

            # 创建画布和坐标轴（移除多余的plt.figure）
            fig, ax = plt.subplots(figsize=(10, 8))

            # 创建热力图并绑定到ax
            heatmap = sns.heatmap(
                data_frame,
                annot=True,
                cmap='coolwarm',
                fmt='.2f',
                linewidths=0.5,
                annot_kws={'size': 8},
                ax=ax  # 确保热力图绘制在指定坐标轴
            )

            # 设置坐标轴样式
            ax.set_title(PlotTitle if PlotTitle != "None" else 'Correlation Heatmap', fontsize=14)
            ax.set_xlabel(xlabel if xlabel != "None" else 'Features', fontsize=10)
            ax.set_ylabel(ylabel if ylabel != "None" else 'Features', fontsize=10)

            # 旋转x轴标签25度（核心修改）
            ax.tick_params(
                axis='x',
                rotation=25,  # 设置旋转角度
                labelsize=8,
                bottom=True,
                top=False,
                labeltop=False
            )

            # 设置y轴标签样式
            ax.tick_params(
                axis='y',
                labelsize=8
            )

            # 调整布局
            plt.tight_layout()

            # 显示图表
            if CommonParameters.IS_STREAMLIT_ON:
                st.pyplot(fig)
            else:
                plt.show()

        except Exception as e:
            raise commonLib.raise_custom_error(
                error_code="000102",
                custom_error_message=rf"画图失败",
                e=e
            )
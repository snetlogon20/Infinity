from matplotlib import pyplot as plt
import streamlit as st
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.dataService.ClickhouseService import commonLib
from dataIntegrator.plotService.PlotManagerSuper import PlotManagerSuper

logger = CommonLib.logger
commonLib = CommonLib()

class LinePlotManager(PlotManagerSuper):

    @classmethod
    def draw_plot(self, param_dict):
        logger.info(rf"start - draw_plot, param_dict: {param_dict} ")

        try:
            isPlotRequired = param_dict.get("isPlotRequired", "no")
            PlotX = param_dict.get("PlotX", "None")
            PlotY = param_dict.get("PlotY", "None")
            data_frame = param_dict.get("results", "None")
            PlotTitle = param_dict.get("PlotTitle", "None")
            xlabel = param_dict.get("xlabel", "None")
            ylabel = param_dict.get("ylabel", "None")

            # 绘制折线图
            if isPlotRequired != "yes":
                logger.info(rf"isPlotRequired != yes")
                return

            if CommonParameters.IS_STREAMLIT_ON:
                st.write(rf"")
                st.write(rf"**Plot Diagram：**")

            fig, ax = plt.subplots(figsize=(10, 6))

            split_PlotY_list = PlotY.split(',')
            for item in split_PlotY_list:
                PlotY_str = item.strip()
                ax.plot(data_frame[PlotX], data_frame[PlotY_str], marker='o', label=PlotY_str)

            # 设置图表标题和坐标轴标签
            logger.info(rf"设置图表标题和坐标轴标签")
            ax.set_title(PlotTitle)
            ax.set_xlabel(xlabel)
            plt.xticks(rotation=45)
            ax.set_ylabel(ylabel)
            ax.set_xticks(data_frame[PlotX])
            ax.grid(True)

            ax.legend(loc='best')

            logger.info(rf"plt.show()")
            if CommonParameters.IS_STREAMLIT_ON:
                st.pyplot(fig)
            else:
                plt.show()
        except Exception as e:
            raise commonLib.raise_custom_error(error_code="000102",custom_error_message=rf"画图失败: {param_dict}", e=e)



from dataIntegrator.LLMSuport.RAGFactory.RAGFactory import RAGFactory
from dataIntegrator.LLMSuport.StreamLit.RAG_SQL_inquiry.RAG_SQL_inquiry import BaseRAGSQLInquiry
from dataIntegrator.modelService.financialAnalysis.PortforlioVolatility import PortfolioVolatilityCalculator
import json
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from datetime import datetime

class RAG_SQL_inquiry_mock_data_service(BaseRAGSQLInquiry):

    @classmethod
    def inquiry(self, agent_type, question):
        print("Formatted current time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        sql = "1111"
        explanation_in_Mandarin = "2222"
        explanation_in_English = "333"

        data_dict = """{"ts_code":{"0":"C","1":"C"},"trade_date":{"0":"20241226","1":"20241227"},"close_point":{"0":71.3499984741,"1":71.0},"open_point":{"0":70.5400009155,"1":70.8600006104},"high_point":{"0":71.4800033569,"1":71.5299987793},"low_point":{"0":70.5100021362,"1":70.5400009155},"pre_close":{"0":71.0,"1":71.3499984741},"change_point":{"0":0.0,"1":0.0},"pct_change":{"0":0.4900000095,"1":-0.4900000095},"vol":{"0":6084438.0,"1":7541609.0},"amount":{"0":432772096.0,"1":535209120.0},"vwap":{"0":71.1299972534,"1":70.9700012207},"turnover_ratio":{"0":0.0,"1":0.0},"total_mv":{"0":0.0,"1":0.0},"pe":{"0":0.0,"1":0.0},"pb":{"0":0.0,"1":0.0}}"""
        parsed_dict = json.loads(data_dict)
        data_frame = pd.DataFrame(parsed_dict)
        data_frame['trade_date'] = pd.to_datetime(data_frame['trade_date'])

        isPlotRequired = "yes"
        PlotX = "trade_date"
        PlotY = "close_point"

        print("----------Process of the message from Mocked Data is done----------")

        edited_data_frame = self.write_form(data_frame, explanation_in_English, explanation_in_Mandarin, sql)
        self.write_excel(edited_data_frame)
        self.draw_plot(PlotX, PlotY, data_frame, isPlotRequired)

        response_dict = {
            "sql": sql,
            "explanation_in_Mandarin": explanation_in_Mandarin,
            "explanation_in_English": explanation_in_English,
            "results": data_frame,
            "isPlotRequired": isPlotRequired,
            "PlotX": PlotX,
            "PlotY": PlotY,
        }

        return response_dict

    @classmethod
    def draw_plot(cls, PlotX, PlotY, data_frame, isPlotRequired):
        # 绘制折线图
        if isPlotRequired == "yes":
            st.write(rf"")
            st.write(rf"**Plot Diagram：**")
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(data_frame[PlotX], data_frame[PlotY], marker='o')

            # 设置图表标题和坐标轴标签
            ax.set_title('Close Point Over Trade Date')
            ax.set_xlabel('Trade Date')
            plt.xticks(rotation=45)
            ax.set_ylabel('Close Point')
            ax.grid(True)
            ax.set_xticks(data_frame['trade_date'])

            # ax.set_xticklabels(data_frame['trade_date'].dt.strftime('%Y-%m-%d'))
            # 在 Streamlit 中显示图表
            st.pyplot(fig)

    @classmethod
    def write_form(cls, data_frame, explanation_in_English, explanation_in_Mandarin, sql):
        # 使用st.dataframe显示DataFrame
        st.write(rf"**Explanation：**")
        st.write(rf"{explanation_in_English}/{explanation_in_Mandarin}")
        st.write(rf"**SQL Statement：**")
        st.write(rf"{sql}")
        st.write(rf"**Results：**")
        edited_data_frame = st.data_editor(data_frame)
        return edited_data_frame

    @classmethod
    def write_excel(cls, edited_data_frame):
        pass
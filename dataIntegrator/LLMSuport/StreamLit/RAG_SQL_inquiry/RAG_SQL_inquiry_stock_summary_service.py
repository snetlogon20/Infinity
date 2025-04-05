from dataIntegrator.LLMSuport.StreamLit.RAG_SQL_inquiry.RAG_SQL_inquiry import BaseRAGSQLInquiry
from dataIntegrator.LLMSuport.RAGFactory.RAGFactory import RAGFactory
import streamlit as st
import pandas as pd
from io import BytesIO
import matplotlib.pyplot as plt

class RAG_SQL_inquiry_stock_summary_service(BaseRAGSQLInquiry):

    @classmethod
    def inquiry(self, agent_type, question):
        knowledge_base_file_path = rf"D:\workspace_python\dataIntegrator\dataIntegrator\LLMSuport\RAGFactory\configurations\RAG_SQL_inquiry_stock_summary_knowledge_base.json"
        prompt_file_path = rf"D:\workspace_python\dataIntegrator\dataIntegrator\LLMSuport\RAGFactory\configurations\RAG_SQL_inquiry_stock_summary_prompts.txt"

        response_dict = (
            RAGFactory.run_rag_inquiry(
                "RAG_SQL_inquiry_stock_summary",
                agent_type, question,
                knowledge_base_file_path, prompt_file_path))

        sql = response_dict["sql"]
        explanation_in_Mandarin = response_dict["explanation_in_Mandarin"]
        explanation_in_English = response_dict["explanation_in_English"]
        data_frame = response_dict["results"]
        isPlotRequired = response_dict["isPlotRequired"]
        PlotX = response_dict["PlotX"]
        PlotY = response_dict["PlotY"]

        edited_data_frame = self.write_form(data_frame, explanation_in_English, explanation_in_Mandarin, sql)
        self.write_excel(edited_data_frame)
        self.draw_plot(PlotX, PlotY, data_frame, isPlotRequired)

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
        # 提供 Excel 下载功能
        if not edited_data_frame.empty:
            try:
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    edited_data_frame.to_excel(writer, sheet_name='Sheet1', index=False)
                output.seek(0)
                b64 = output.getvalue().hex()
                href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="query_results.xlsx" style="font-size: 12px;">Download As Excel</a>'
                st.markdown(href, unsafe_allow_html=True)
            except ImportError:
                st.error(
                    "The 'xlsxwriter' module is required for Excel export. Please install it using 'pip install xlsxwriter'.")


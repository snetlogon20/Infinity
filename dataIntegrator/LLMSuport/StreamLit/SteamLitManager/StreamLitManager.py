import streamlit as st
import pandas as pd
from datetime import datetime
import json
import sys

from dataIntegrator.LLMSuport.ChromaService.ChromaDialogAgent import ChromaDialogAgent
from dataIntegrator.LLMSuport.StreamLit.RAG_SQL_inquiry.RAG_SQL_inquiry_portfolio_volatility_service import \
    RAG_SQL_inquiry_portfolio_volatility_service
from dataIntegrator.LLMSuport.StreamLit.RAG_SQL_inquiry.RAG_SQL_inquiry_stock_summary_service import RAG_SQL_inquiry_stock_summary_service
from dataIntegrator.common.CommonLib import CommonLib
from dataIntegrator.utility.FileUtility import FileUtility

st.set_page_config(layout="wide")

class StreamLitManager(CommonLib):
    def __init__(self, base_url='http://127.0.0.1:5000'):
        self.base_url = base_url

    def request_for_rag_inquiry(self, question):
        if question is None or len(question) == 0:
            print("question is null")
            return

        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="request_for_rag_inquiry started")
        try:
            agent_type = "spark"
            service = RAG_SQL_inquiry_stock_summary_service()
            response_dict = service.inquiry(agent_type, question)
            return response_dict
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="prepareData completed")

    def request_for_financial_inquiry(self, question):
        if question is None or len(question) == 0:
            print("question is null")
            return

        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="request_for_rag_inquiry started")
        try:
            agent_type = "spark"
            service = RAG_SQL_inquiry_portfolio_volatility_service
            response_dict = service.inquiry(agent_type, question)
            return response_dict
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="prepareData completed")


        return sql, explanation_in_Mandarin, explanation_in_English


    def callMockedData(self):
        print("----------Send inqiury to Mocked Data----------")
        # print("Formatted current time:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        # sql = "1111"
        # explanation_in_Mandarin = "2222"
        # explanation_in_English = "333"
        # data_dict = """{"ts_code":{"0":"C","1":"C"},"trade_date":{"0":"20241226","1":"20241227"},"close_point":{"0":71.3499984741,"1":71.0},"open_point":{"0":70.5400009155,"1":70.8600006104},"high_point":{"0":71.4800033569,"1":71.5299987793},"low_point":{"0":70.5100021362,"1":70.5400009155},"pre_close":{"0":71.0,"1":71.3499984741},"change_point":{"0":0.0,"1":0.0},"pct_change":{"0":0.4900000095,"1":-0.4900000095},"vol":{"0":6084438.0,"1":7541609.0},"amount":{"0":432772096.0,"1":535209120.0},"vwap":{"0":71.1299972534,"1":70.9700012207},"turnover_ratio":{"0":0.0,"1":0.0},"total_mv":{"0":0.0,"1":0.0},"pe":{"0":0.0,"1":0.0},"pb":{"0":0.0,"1":0.0}}"""
        # parsed_dict = json.loads(data_dict)
        # data_frame = pd.DataFrame(parsed_dict)
        # data_frame['trade_date'] = pd.to_datetime(data_frame['trade_date'])
        # isPlotRequired = "yes"
        # PlotX = "trade_date"
        # PlotY = "close_point"
        #
        # print("Formatted current time:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        # print("----------Process of the message from Mocked Data is done----------")
        # return data_frame, explanation_in_English, explanation_in_Mandarin, sql, isPlotRequired, PlotX, PlotY

if __name__ == "__main__":
    # 添加自定义 CSS 以修改侧边栏样式
    st.markdown(
        """
        <style>
            /* 保持原有侧边栏颜色样式不变... */

            /* 新增radio布局修正 */
            [data-testid="stSidebar"] .stRadio > div {
                display: flex !important;
                flex-direction: column !important;
                gap: 4px !important;
            }

            [data-testid="stSidebar"] .stRadio > label {
                display: flex !important;
                align-items: center !important;
                min-height: 32px !important;
                padding: 4px 12px !important;
                margin: 2px 0 !important;
            }

            [data-testid="stSidebar"] .stRadio [data-baseweb="radio"] {
                margin-top: 0 !important;
                margin-bottom: 0 !important;
                flex-shrink: 0 !important;
            }

            [data-testid="stSidebar"] .stRadio label > div:first-child {
                order: -1 !important;  /* 将radio按钮移到文字前 */
                margin-right: 12px !important;
            }

            [data-testid="stSidebar"] .stRadio label div[data-testid="stMarkdownContainer"] {
                flex-grow: 1 !important;
                line-height: 1.4 !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    # 在侧边栏最上面添加标题
    st.sidebar.title("Infinity Grid")

    # 侧边栏菜单
    menu = [
        "Any-SQL", "Any-Rule", "Any-API",
        "Any-Chart/Plot", "Any-Financial Analysis","CHAT-BOT",
        "Knowledge Base", "Common Queries",
        "Business Rules", "Meta Configration",
        "Choose Your AI Engine"
    ]
    choice = st.sidebar.radio(
        "Data Alchemy for Business Decisions",
        options=menu,  # 添加 options 参数
        format_func=lambda x: x.upper(),
        key="sidebar_menu"
    )

    if choice == "Any-SQL":
        # 添加文本输入框和按钮
        user_input = st.text_area("**Tell me/你的问题:**", height=100, placeholder="Please input question like: show me the average percent change  of Citi between 2024/12/01 to 2024/12/31")
        # 在 Streamlit 中嵌入 HTML 代码

        if 'button_clicked' not in st.session_state:
            st.session_state.button_clicked = False

        if st.button("Go/查询"):
            st.session_state.button_clicked = True


        if st.session_state.button_clicked:
            if user_input is None or len(user_input) == 0:
                print("question is null")
            else:
                manager = StreamLitManager()
                manager.request_for_rag_inquiry(user_input)
                st.session_state.button_clicked = False

    if choice == "Any-Financial Analysis":
        # 添加文本输入框和按钮
        user_input = st.text_area("**Tell me/你的问题:**", height=100, placeholder="Please input question like: show me the average percent change  of Citi between 2024/12/01 to 2024/12/31")
        # 在 Streamlit 中嵌入 HTML 代码

        if 'button_clicked' not in st.session_state:
            st.session_state.button_clicked = False

        if st.button("Go/查询"):
            st.session_state.button_clicked = True

        #components.html(html_code, height=70)

        if st.session_state.button_clicked:
            if user_input is None or len(user_input) == 0:
                print("question is null")
            else:
                manager = StreamLitManager()
                manager.request_for_financial_inquiry(user_input)
                st.session_state.button_clicked = False
    if choice == "CHAT-BOT":

        # 初始化会话状态
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []

        # 显示历史对话
        for user_query, system_response in st.session_state.chat_history:
            with st.chat_message("user"):
                st.markdown(f"**用户问:** {user_query}")
            with st.chat_message("assistant"):
                st.markdown(f"**系统回答:** {system_response}")

        # 文本输入框和按钮
        user_input = st.text_area("**Tell me:**", height=100, placeholder="Please input question like: show me the average percent change of Citi between 2024/12/01 to 2024/12/31")
        if st.button("Go/查询"):
            if user_input is None or len(user_input) == 0:
                print("question is null")
            else:
                try:

                    model_path = FileUtility.get_full_outbound_path("model", "all-MiniLM-L6-v2")
                    db_persistent_path = FileUtility.get_full_outbound_path("chormadb", "persistent.db")
                    meta_excel_path = FileUtility.get_full_outbound_path("inbound", "chromadb_meta_collections.xlsx")
                    user_id = "snetlogon20"
                    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    session_id = f"snetlogon20_{current_time}"  # 每次启动使用新的collection，避免以前消息的干扰

                    agent = ChromaDialogAgent(model_path)  # 使用继承后的对话代理类
                    agent.set_persistent_folder(db_persistent_path)


                    collection = agent.create_collection(model_path=model_path, collection_name=f"{user_id}_{session_id}_ChromaDB")
                    print("集合中的文档数量：", collection.count())

                    query, chromadb_results, ai_response_dict = agent.process_query(user_id, user_input, collection,
                                                                                    n_results=3)
                    print(f"系统回答：{ai_response_dict['response']}")
                    print("-" * 60)

                    # 模拟系统响应
                    system_response = f"---你好--- {ai_response_dict['response']}"
                    # 更新会话历史
                    st.session_state.chat_history.append((query, system_response))
                    # 刷新页面以显示新对话
                    st.rerun()
                except Exception as e:
                    st.error(f"查询处理失败：{str(e)}")

    elif choice == "其他页面":
        st.write("这是其他页面的内容，你可以根据需要进行修改。")


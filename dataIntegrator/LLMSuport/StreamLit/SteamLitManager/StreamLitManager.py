import streamlit as st
import sys

from dataIntegrator import CommonParameters
from dataIntegrator.LLMSuport.ChromaService.ChromaDialogAgent import ChromaDialogAgent
from dataIntegrator.LLMSuport.StreamLit.RAG_SQL_inquiry.RAG_SQL_inquiry_mock_data_service import \
    RAG_SQL_inquiry_mock_data_service
from dataIntegrator.LLMSuport.StreamLit.RAG_SQL_inquiry.RAG_SQL_inquiry_portfolio_volatility_service import \
    RAG_SQL_inquiry_portfolio_volatility_service
from dataIntegrator.LLMSuport.StreamLit.SteamLitManager.AnyFinancialInquiry import AnyFinancialInquiry
from dataIntegrator.LLMSuport.StreamLit.SteamLitManager.AnySQLInquiry import AnySQLInquiry
from dataIntegrator.LLMSuport.StreamLit.SteamLitManager.RAGChatBot import RAGChatBot
from dataIntegrator.common.CommonLib import CommonLib
from dataIntegrator.common.CustomError import CustomError
from dataIntegrator.utility.FileUtility import FileUtility

st.set_page_config(layout="wide")

logger = CommonLib.logger
commonLib = CommonLib()

class StreamLitManager(CommonLib):
    def __init__(self, base_url='http://127.0.0.1:5000'):
        self.base_url = base_url

    def callMockedData(self):
        agent_type = "spark"
        question = "Mocked question"

        service = RAG_SQL_inquiry_mock_data_service()
        response_dict = service.inquiry(agent_type, question)

        return response_dict


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

    #Chang the status of streamLit to ON
    CommonParameters.IS_STREAMLIT_ON = True

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
                service = AnySQLInquiry()
                service.request_for_rag_inquiry(user_input)
                #manager.callMockedData()
                st.session_state.button_clicked = False


    if choice == "Any-Financial Analysis":
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
                service = AnyFinancialInquiry()
                service.request_for_rag_inquiry(user_input)
                st.session_state.button_clicked = False
    if choice == "CHAT-BOT":

        if 'button_clicked' not in st.session_state:
            st.session_state.button_clicked = False

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
            st.session_state.button_clicked = True

        if st.session_state.button_clicked:
            if user_input is None or len(user_input) == 0:
                print("question is null")
            else:
                try:
                    service = RAGChatBot()
                    service.request_for_rag_inquiry(user_input)
                    # 使用components.html注入JavaScript
                    scroll_js = """
                    <script>
                    setTimeout(function() {
                        window.scrollTo({
                            top: document.documentElement.scrollHeight,
                            behavior: 'smooth'
                        });
                    }, 100);
                    </script>
                    """
                    st.components.v1.html(scroll_js, height=0)
                except Exception as e:
                    st.error(f"查询处理失败：{str(e)}")
                finally:
                    st.session_state.button_clicked = False
    elif choice == "其他页面":
        st.write("这是其他页面的内容，你可以根据需要进行修改。")


import streamlit as st
import pandas as pd
import requests
import json
from io import BytesIO
import matplotlib.pyplot as plt
# from Streamlit.FlaskClient import FlaskClient
import streamlit.components.v1 as components

# 定义包含语音识别功能的 HTML 代码
html_code = """
<!DOCTYPE html>
<html>
<button id="startButton">Voice Assistance/语音助手</button>
<p id="result"></p>
<script>
  const startButton = document.getElementById('startButton');
  const result = document.getElementById('result');

  if ('webkitSpeechRecognition' in window) {
    const recognition = new webkitSpeechRecognition();
    recognition.lang = 'zh-CN';

    startButton.addEventListener('click', () => {
      recognition.start();
    });

    recognition.addEventListener('result', (event) => {
      const transcript = event.results[0][0].transcript;
      result.textContent = transcript;
      // 将识别结果发送到 Streamlit
      const streamlitData = {
        type: 'input',
        value: transcript
      };
      window.parent.postMessage(streamlitData, '*');
    });
  } else {
    result.textContent = '您的浏览器不支持语音识别功能。';
  }
</script>
</html>
"""

# 监听来自 HTML 页面的消息
from streamlit.components.v1 import html
import json

# 创建一个隐藏的 iframe 用于接收消息
# html("""
# <iframe id="messageReceiver" style="display:none;"></iframe>
# <script>
#   window.addEventListener('message', (event) => {
#     if (event.data.type === 'input') {
#       const inputValue = event.data.value;
#       // 将输入值传递给 Streamlit
#       const form = document.createElement('form');
#       form.method = 'post';
#       form.action = window.location.href;
#       const input = document.createElement('input');
#       input.type = 'hidden';
#       input.name = 'voice_input';
#       input.value = inputValue;a
#       form.appendChild(input);
#       document.body.appendChild(form);
#       form.submit();
#     }
#   });
# </script>
# """)

class FlaskClient:
    def __init__(self, base_url='http://127.0.0.1:5000'):
        self.base_url = base_url

    def request_for_rag_inquiry(self, question):
        print("----------I am started----------")

        if question is None or len(question) == 0:
            print("question is null")
            return

        url = f"{self.base_url}/rag_inquiry"
        params = {'question': question}


        data_frame, explanation_in_English, explanation_in_Mandarin, sql, isPlotRequired, PlotX, PlotY = self.callAtlas(params, url)
        #data_frame, explanation_in_English, explanation_in_Mandarin, sql, isPlotRequired, PlotX, PlotY = self.callMockedData()


        # 使用st.dataframe显示DataFrame
        st.write(rf"**解释/Explanation：**")
        st.write(rf"{explanation_in_Mandarin}/{explanation_in_English}")
        st.write(rf"**SQL Statement：**")
        st.write(rf"{sql}")

        st.write(rf"**查询结果返回：**")
        #st.dataframe(data_frame)
        edited_data_frame = st.data_editor(data_frame)

        # 提供 Excel 下载功能
        if not edited_data_frame.empty:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                edited_data_frame.to_excel(writer, sheet_name='Sheet1', index=False)
            output.seek(0)
            st.download_button(
                label="Download Excel",
                data=output,
                file_name="query_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

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
            #ax.set_xticklabels(data_frame['trade_date'].dt.strftime('%Y-%m-%d'))
            # 在 Streamlit 中显示图表
            st.pyplot(fig)


        return sql, explanation_in_Mandarin, explanation_in_English, data_frame

    def callMockedData(self):
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

        return data_frame, explanation_in_English, explanation_in_Mandarin, sql, isPlotRequired, PlotX, PlotY

    def callAtlas(self, params, url):
        print("----------Send inqiury to Atlas----------")

        response = requests.get(url, params=params)
        if response.status_code == 200:
            print("Response from /request_for_rag_inquiry:")
            print(response.json())
        else:
            print(f"Error: {response.status_code} - {response.text}")

        response_json = response.json()

        sql = response_json["sql"]
        explanation_in_Mandarin = response_json["explanation_in_Mandarin"]
        explanation_in_English = response_json["explanation_in_English"]
        data_dict = json.loads(response_json["results"])
        data_frame = pd.DataFrame(data_dict)
        isPlotRequired = response_json["isPlotRequired"]
        PlotX = response_json["PlotX"]
        PlotY = response_json["PlotY"]

        print("----------Process of the message from Atlas is done----------")

        return data_frame, explanation_in_English, explanation_in_Mandarin, sql, isPlotRequired, PlotX, PlotY


if __name__ == "__main__":
    # 添加自定义 CSS 以修改侧边栏样式
    st.markdown(
        """
        <style>
            /* 修改侧边栏背景颜色 */
            [data-testid="stSidebar"] {
                background-color: black;
            }
            /* 修改侧边栏菜单标题颜色 */
            [data-testid="stSidebar"] label {
                color: white;
            }
            /* 修改侧边栏文本颜色 */
            [data-testid="stSidebar"] .st-c0 {
                color: white;
            }
            /* 修改侧边栏标题颜色 */
            [data-testid="stSidebar"] .st-eb {
                color: white;
            }
            /* 修改侧边栏列表项选中时的背景颜色和字体颜色 */
            [data-testid="stSidebar"] .st-cc {
                background-color: white;
                color: black;
            }
            /* 修改侧边栏列表项未选中时的字体颜色 */
            [data-testid="stSidebar"] .st-bd {
                color: white;
            }
            /* 修改侧边栏标题字体颜色 */
            [data-testid="stSidebar"] h1 {
                color: white;
            }
            /* 修改 Powered by 文本的字体大小 */
            .powered-by {
                font-size: 12px;
                color: white;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    # 在侧边栏最上面添加标题
    st.sidebar.title("Star Atlas")

    # 创建侧边栏菜单，使用 st.sidebar.radio 实现列表形式
    menu = ["SQL RAG", "Rule RAG", "API RAG","Chart/Plot RAG", "Financial Analysis RAG",
            "Knowledge Base", "Common Queries", "Business Rules", "Knowledge Base",
            "Meta Configration", "Choose AI Engine"]  # 可以根据需要添加更多菜单选项
    choice = st.sidebar.radio("RAG is nothing, but quantified data with analysis is gold", menu)

    if choice == "SQL RAG":
        # 添加文本输入框和按钮
        user_input = st.text_area("**Tell me/你的问题:**", height=100, placeholder="Please input question like: show me the average percent change  of Citi between 2024/12/01 to 2024/12/31")
        # 在 Streamlit 中嵌入 HTML 代码

        if st.button("Go/查询"):
            print(f"请输入你的问题: {user_input}")

        components.html(html_code, height=100)

        if user_input is None or len(user_input) == 0:
            print("question is null")
            #st.write(f"请输入你的问题/Please fill your question")
        else:
            client = FlaskClient()
            sql, explanation_in_Mandarin, explanation_in_English, data_frame = client.request_for_rag_inquiry(user_input)
    elif choice == "其他页面":
        st.write("这是其他页面的内容，你可以根据需要进行修改。")

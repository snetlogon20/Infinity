import streamlit as st
import pandas as pd

# 示例数据
data = {
    'Name': ['Alice', 'Bob', 'Charlie'],
    'Age': [25, 30, 35]
}
df = pd.DataFrame(data)

# 使用 Streamlit 函数
st.markdown('# 1.streamlit入门')
st.markdown('## 1.1 图形控件的使用-文本框组件')
st.text('这是最基本的文本框组件，可以用于输入基本的文本内容')
st.write('哟哟哟')
st.latex(r"基本LATEX公式：E=mc^2")
st.write(df)
st.dataframe(df)
st.table(df)
import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

# 上传 Excel 文件
uploaded_file = st.file_uploader("上传 Excel 文件", type=["xlsx", "xls"])

if uploaded_file is not None:
    # 读取 Excel 文件
    #df = pd.read_excel(uploaded_file)
    df = pd.read_excel(uploaded_file, engine="openpyxl")  # 添加 engine 参数

    # 显示原始表格
    st.write("原始表格:")
    st.dataframe(df)

    # 提供编辑界面
    st.write("编辑表格:")
    edited_df = st.data_editor(df, num_rows="dynamic")

    # 保存修改后的表格
    if st.button("保存修改"):
        try:
            # 将修改后的数据保存到新的 Excel 文件
            output_file = "edited_table.xlsx"
            edited_df.to_excel(output_file, index=False)
            st.success(f"修改已保存到 {output_file}")
        except Exception as e:
            st.error(f"保存失败: {e}")



if __name__ == "__main__":

    data = pd.read_csv(rf'D:\workspace_python\dataIntegrator\dataIntegrator\test\streamLit\csv_test.csv', encoding='utf-8').select_dtypes(['int', 'float'])
    fig = plt.figure(figsize=(8, 6), dpi=200)
    sns.heatmap(data.corr(),
                cmap='bwr', square=True, annot=True, fmt='.2f', linecolor='cyan', linewidths=1)
    plt.xticks(fontproperties='STsong')
    plt.yticks(fontproperties='STsong')
    st.pyplot(fig)
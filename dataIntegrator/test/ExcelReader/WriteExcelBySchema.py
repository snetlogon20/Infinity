import pandas as pd
import json

# 示例数据：用户列表DataFrame
data = [{'col1': 'a', 'col2': 4.0},
 {'col1': 'a', 'col2': 4.0},
 {'col1': 'a', 'col2': 5.0}]
user_df = pd.DataFrame(data)
print(user_df)

# 示例模式（schema），指定在JSON中的位置
schema = {
    "root": {
        "users": user_df.to_dict(orient='records')
    }
}

if __name__ == "__main__":
    # 将模式转换为JSON字符串
    json_output = json.dumps(schema, indent=4)

    # 打印JSON字符串
    print(json_output)

    # 如果你想将JSON保存到文件中
    with open('WriteExcelBySchema.json', 'w') as f:
        f.write(json_output)
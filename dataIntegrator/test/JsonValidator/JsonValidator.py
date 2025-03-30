from jsonschema import validate
import os
import json


class JsonValidator:
    a = 0


if __name__ == "__main__":
    with open('./data.schema', 'r', encoding='utf-8') as f:
        schema = json.load(f)

    with open('./data_list.schema', 'r', encoding='utf-8') as f:
        schema_array = json.load(f)

# Iterate through all JSON files in the current directory
for filename in os.listdir('.'):

    if filename.endswith('.json'):
        print(rf"=========================================")
        print(rf"processing: {filename} ")
        with open(filename) as f:
            data = json.load(f)

        # Use different schema based on filename
        schema_to_use = schema_array if "_list" in filename else schema

        # 执行校验
        try:
            validate(instance=data, schema=schema_to_use)
            print(f"{filename} 校验通过！")
        except Exception as e:
            print(f"{filename} 校验失败：{e}")


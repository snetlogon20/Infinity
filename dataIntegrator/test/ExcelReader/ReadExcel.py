import pandas as pd
import json
from jsonschema import validate, ValidationError
import jsonschema


def read_field_properties(file_path):
    """
    从 JSON 文件中读取字段属性
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def read_excel_range(file_path, sheet_name, start_cell, end_cell, field_properties):
    """
    根据预设的字段属性读取 Excel 文件的指定区域
    """
    # 计算起始行、列和结束行、列
    start_col = ord(start_cell[0]) - ord('A')
    start_row = int(start_cell[1:]) - 1
    end_col = ord(end_cell[0]) - ord('A')
    end_row = int(end_cell[1:]) - 1

    # 读取 Excel 文件
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)

    # 提取指定区域的数据
    selected_data = df.loc[start_row:end_row, start_col:end_col]

    # 设置列名
    columns = [prop['name'] for prop in field_properties]
    selected_data.columns = columns

    # 根据字段属性转换数据类型
    for prop in field_properties:
        col_name = prop['name']
        data_type = prop['type']
        if data_type == 'int':
            selected_data[col_name] = pd.to_numeric(selected_data[col_name], errors='coerce').fillna(0).astype(int)
        elif data_type == 'float':
            selected_data[col_name] = pd.to_numeric(selected_data[col_name], errors='coerce').fillna(0).astype(float)
        elif data_type == 'str':
            selected_data[col_name] = selected_data[col_name].astype(str)

    return selected_data


def convert_to_schema_compliant(data, field_properties):
    """
    将数据转换为符合 Schema 的格式，并检查是否符合规范
    """
    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                prop['name']: {"type": [prop['type']]} for prop in field_properties
            }
        }
    }
    data_list = data.to_dict(orient='records')

    print("-------将数据转换为符合 Schema 的格式，并检查是否符合规范---------")
    for index, item in enumerate(data_list):

        print (rf"{index}: {item}")
        try:
            validate(instance=item, schema=schema["items"])
        except ValidationError as e:
            raise ValueError(f"第 {index + 1} 行数据不符合 Schema 要求: {e.message}")

    return data_list, schema


def write_to_json(output_json_path, schema_with_data):
    try:
        json_output = json.dumps(schema_with_data, indent=4)
        print("-------------write_to_json-------------")
        print(json_output)

        with open(output_json_path, 'w', encoding='utf-8') as f:
            f.write(json_output)
        print(f"数据已成功写入 {output_json_path}，且符合 Schema 要求。")
    except Exception as e:
        print(f"数据不符合 Schema 要求: {e}")


if __name__ == "__main__":
    # 示例调用

    ##########################################################################
    # Step 0 load parameter which shall be store in a metatable for each task
    ##########################################################################
    bash_path = rf"D:\workspace_python\dataIntegrator\dataIntegrator\test\ExcelReader\\"
    # Excel tangular to read + validation rules
    excel_file_path = bash_path + 'source.xlsx'
    excel_read_field_properties_path = bash_path + 'excel_read_field_properties.json'
    sheet_name = 'Sheet1'
    start_cell = 'B2'
    end_cell = 'C4'

    # Jons file to write and validation rules
    output_json_path = bash_path + 'json_output_interface_file.json'
    schema_with_data_template = "to be loaded by factory mode"
    json_write_field_validation_schema_path = bash_path + 'json_write_field_validation.json'

    ############################################
    # Step 1 Read Data， 此处可以用Easy DA 替代
    ############################################
    # 读取excel字段属性的配置
    print("-------------Read Excel Data------------")
    excel_read_field_properties = read_field_properties(excel_read_field_properties_path)
    # 根据指定的字段属性读取指定区域的数据
    data = read_excel_range(excel_file_path, sheet_name, start_cell, end_cell, excel_read_field_properties)
    print(data)

    #######################################
    # Step 2 Validate the Data from excel
    #######################################
    # 将Excel 根据数据Property 转换为符合 Schema 的格式， 并强制校验
    schema_compliant_data, schema = convert_to_schema_compliant(data, excel_read_field_properties)

    ######################################################
    # Step 3 Join and Merge Excel data frame if required
    ######################################################
    #此处应有多个excel frame 进行不同形状拼接的客制化处理，暂不一一举例
    #Python使用pandas, java该怎么办？

    #此处应有多个json 对象按照schema 插入不同节点。
    #Python使用pandas, java该怎么办？

    ######################################################
    # Step 3 Generate JSON per schema
    # 此处只能通过工厂模式配置
    ######################################################
    schema_with_data = {
        "root": {
            "users": data.to_dict(orient='records')
        }
    }

    ######################################################
    # Step 4 Validate JSON
    ######################################################
    json_write_field_validation_schema = read_field_properties(json_write_field_validation_schema_path)
    print("-----------JSON 数据验证---------------")
    try:
        # 验证 JSON 数据
        jsonschema.validate(instance=schema_with_data, schema=json_write_field_validation_schema)
        print("JSON 数据验证通过")
    except jsonschema.exceptions.ValidationError as e:
        #print(f"JSON 数据验证失败: {e}")
        raise ValueError(f"JSON 数据验证失败: {e.message}")

    ######################################################
    # Step 5 Writ JSON
    ######################################################
    write_to_json(output_json_path, schema_with_data)


##########################################################################################
# 测试案例2个
# 修改excel中C列为字符, 应该在excel数据校验时报错
# 修改json_write_field_validation.json, 将 col1 属性修改为number ，应该在json数据校验时报错
##########################################################################################
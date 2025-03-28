import datetime
import json

class FileUtility:
    @staticmethod
    def generate_filename_by_timestamp(prefix, surfix):
        # Get the current date and time
        current_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        # Concatenate the prefix with the current timestamp
        filename = f"{prefix}_{current_time}.{surfix}"

        return filename

    @staticmethod
    def get_outbound_path():
        outbound_path = 'D:\\workspace_python\\dataIntegrator\dataIntegrator\\data\\outbound\\'
        return outbound_path

    @staticmethod
    def get_full_filename_by_timestamp(prefix, surfix):
        outbound_path = FileUtility.get_outbound_path()
        filename = FileUtility.generate_filename_by_timestamp(prefix,surfix)
        file_full_name = rf"{outbound_path}{filename}"
        return file_full_name

    @staticmethod
    def read_file(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                file_string = file.read()
                return file_string
        except FileNotFoundError:
            print(f"错误: 文件 {file_path} 未找到。")
        except Exception as e:
            print(f"错误: 发生了一个未知错误: {e}")
        return ""
    @staticmethod
    def read_json_file(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:  # 修改：指定编码为 utf-8
                json_object = json.load(file)
            if not isinstance(json_object, dict):  # 检查返回值是否为字典
                raise ValueError("加载的知识库不是有效的字典格式")
            return json_object
        except FileNotFoundError:
            print(f"错误: 文件 {file_path} 未找到。")
        except json.JSONDecodeError:
            print(f"错误: 文件 {file_path} 不是有效的 JSON 格式。")
        except Exception as e:
            print(f"错误: 发生了一个未知错误: {e}")
        return ""


if __name__ == "__main__":
    filename = FileUtility.generate_filename_by_timestamp("LinearRegressionCiti","xlsx")
    print(filename)
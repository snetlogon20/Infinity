import json

from dataIntegrator import CommonLib
from dataIntegrator.common.CustomError import CustomError

logger = CommonLib.logger
commonLib = CommonLib()

class JSONUtility:
    def __init__(self):
        pass

    @staticmethod
    def convert_txt_to_json(txt_file_path, json_file_path):
        try:
            # 1. 读取 TXT 文件内容
            with open(txt_file_path, "r", encoding="utf-8") as f:
                # 方法 1：保留所有行（包括换行符），用 "\n" 连接
                content = f.read()

                # # 方法 2：去除换行符，合并为单行（根据需求选择）
                # lines = f.readlines()
                # content = "".join([line.strip() for line in lines])  # 去除每行首尾空格和换行符
                # # 或 content = "".join(lines)  # 保留原始换行符（\n）

            # 2. 构建 JSON 数据
            data = {"context": content}

            # 3. 写入 JSON 文件
            with open(json_file_path, "w", encoding="utf-8") as f:
                # indent=2 表示格式化缩进（可选，使 JSON 更易读）
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(rf"text file {txt_file_path} is saved as {json_file_path} successfully")

            return

        except CustomError as e:
            raise e
        except Exception as e:
            raise commonLib.raise_custom_error(error_code="000104", custom_error_message=rf"Error when executing RAG service", e=e)


if __name__ == "__main__":
    # 配置文件路径（请根据实际情况修改）
    txt_file_path = rf"D:\workspace_python\infinity\dataIntegrator\test\RegulatoryRAG2UML\requirement2.0.md"  # 输入的 TXT 文件路径
    json_file_path = rf"D:\workspace_python\infinity\dataIntegrator\LLMSuport\RAGFactory\configurations\RAG_UML_txt2uml.json"  # 输出的 JSON 文件路径

    JSONUtility.convert_txt_to_json(txt_file_path, json_file_path)
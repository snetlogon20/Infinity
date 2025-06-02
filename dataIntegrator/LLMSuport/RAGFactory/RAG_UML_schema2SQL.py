import json

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.LLMSuport.AiAgents.AiAgentFactory import AIAgentFactory
from dataIntegrator.LLMSuport.RAGFactory.RAGAgent import RAGAgent
from dataIntegrator.LLMSuport.RAGFactory.RAGMockedMessager import RAGMockedMessager
from dataIntegrator.common.CustomError import CustomError
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.utility.FileUtility import FileUtility
import re

logger = CommonLib.logger
commonLib = CommonLib()


class RAG_UML_schema2SQL(RAGAgent):

    def __init__(self, knowledge_base_file_path, prompt_file_path):
        self.knowledge_base_file_path = knowledge_base_file_path
        self.prompt_file_path = prompt_file_path

    @classmethod
    def load_knowledge_base_from_json(self, file_path):
        json_object = FileUtility.read_json_file(file_path)
        return json_object

    @classmethod
    def retrieve_context(self, knowledge_base, question):
        context = []

        context.append("### 数据表定义说明:")
        for item in knowledge_base["table_definitions"]:
            table_name = item["table_name"]
            table_definition = item["table_definition"]
            primary_key = item["primary_key"]
            table_alias = item["table_alias"]
            context.append(rf"数据表名 {table_name}: 业务范围: {table_definition}, Primary Key: {primary_key}, table_alias: {table_alias}")

        # 表结构信息
        context.append("### 表结构说明:")
        for table, schema in knowledge_base["table_schema"].items():
            context.append(f"{table} 表结构如下：")
            for col, desc in schema["columns"].items():
                context.append(f"- {col}: {desc}")

        # # 匹配常见问题
        # context.append("\n### 相关常见查询:")
        # for query in knowledge_base["common_queries"]:
        #     context.append(f"- {query['question']}: {query['sql']}")

        # # 业务规则匹配
        # context.append("\n### 业务规则:")
        # for rule in knowledge_base["business_rules"]:
        #     context.append(f"- {rule}")

        return "\n".join(context)

    @classmethod
    def load_and_generate_prompts(self, prompt_file_path, context, question):
        # 读取 提示模板
        prompt_template = FileUtility.read_file(prompt_file_path)

        # 生成增强提示词
        prompt = prompt_template.format(context=context, question=question)
        return prompt

    @classmethod
    def call_ai_agent(self, agent_type, prompt, question):
        if CommonParameters.IF_ENABLE_MOCKED_AI :
            return

        response = AIAgentFactory.call_agent(agent_type, prompt, question)
        print(response)
        return response

    @classmethod
    def parse_response(cls, response):
        if CommonParameters.IF_ENABLE_MOCKED_AI:
            cleaned_json = RAGMockedMessager.schema2SQL_MOCKED_AI_ANSWER
            return cleaned_json

        # 解析结果
        json_str = response.generations[0][0].text
        cleaned_json = json_str.replace("```json", "").replace("```", "").strip()
        print("cleaned_json:", cleaned_json)
        return cleaned_json

    @classmethod
    def process_response(self, cleaned_json):
        # 清理 JSON 字符串，去除非法字符
        cleaned_json = re.sub(r'[^\x20-\x7E]', '', cleaned_json)
        cleaned_json = cleaned_json.replace("\\n", "\n")

        # 查询数据
        try:
            result = json.loads(cleaned_json)
            sql = result["sql"]

            clickhouseService = ClickhouseService()
            data = clickhouseService.getDataFrameWithoutColumnsName(sql)
        except CustomError as e:
            raise e
        except Exception as e:
            raise commonLib.raise_custom_error(error_code="000104",custom_error_message=rf"Error when executing RAG service", e=e)

        # 组装返回结果
        response_dict = {
            "sql": sql,
            "explanation_in_Mandarin": result["explanation_in_Mandarin"],
            "explanation_in_English": result["explanation_in_English"],
            "results": data,
            "isPlotRequired": result["isPlotRequired"],
            "plotRequirement": {
                "plotType": result["plotRequirement"]["plotType"],
                "PlotX": result["plotRequirement"]["PlotX"],
                "PlotY": result["plotRequirement"]["PlotY"],
                "PlotTitle": result["plotRequirement"]["PlotTitle"],
                "xlabel": result["plotRequirement"]["xlabel"],
                "ylabel": result["plotRequirement"]["ylabel"]
            },
            "isLinearRegressionRequired": result["isLinearRegressionRequired"],
            "linearRequirement": {
                "plotType": result["linearRequirement"]["plotType"],
                "xColumns": result["linearRequirement"]["xColumns"],
                "yColumn": result["linearRequirement"]["yColumn"],
                "PlotXColumn": result["linearRequirement"]["PlotXColumn"],
                "PlotTitle": result["linearRequirement"]["PlotTitle"],
                "xlabel": result["linearRequirement"]["xlabel"],
                "ylabel": result["linearRequirement"]["ylabel"],
                "if_run_test": result["linearRequirement"]["if_run_test"],
                "X_given_test_source_path": result["linearRequirement"]["X_given_test_source_path"]
            }
        }

        # 组装返回结果，先加入动态生成的键值对。
        response_dict = {
            "sql": sql,
            "results": data
        }
        # 再动态添加其他键值对
        for key, value in result.items():
            if key not in ["sql", "results"]:  # 排除特殊处理
                response_dict[key]= value

        return response_dict

    # def display_result(self, response, result_dict):
    #     if "error" in response:
    #         print(f"错误：{response['error']}")
    #         if "sql_attempt" in response:
    #             print(f"尝试执行的SQL：{response['sql_attempt']}")
    #     else:
    #         print("生成的SQL/SQL generated：", result_dict["sql"])
    #         print("解释说明：", result_dict["explanation_in_Mandarin"])
    #         print("Explain：", result_dict["explanation_in_English"])
    #         print("查询结果/Result：")
    #         print(result_dict["results"])
    #         print("isPlotRequired:", result_dict["isPlotRequired"])
    #         print("PlotX:", result_dict["plotRequirement"]["PlotX"])
    #         print("PlotY:", result_dict["plotRequirement"]["PlotY"])
    #     return response

    def run_single_question(self, agent_type, question):

        try:
            knowledge_base = self.load_knowledge_base_from_json(self.knowledge_base_file_path)
            context = self.retrieve_context(knowledge_base, question)
            prompt = self.load_and_generate_prompts(self.prompt_file_path, context, question)
            response = self.call_ai_agent(agent_type, prompt, question)
            cleaned_json = self.parse_response(response)
            response_dict = self.process_response(cleaned_json)
            #self.display_result(response, response_dict)

            return response_dict
        except CustomError as e:
            raise e
        except Exception as e:
            raise commonLib.raise_custom_error(error_code="000104", custom_error_message=rf"Error when executing RAG service", e=e)

    def run_prompt_questions(self):
        while True:
            question = input("Please enter your question (type :quit to exit): ")
            if question == ":quit":
                break

            print(f"\n问题：{question}")
            self.run_single_question(question)

            print(rf"感谢询问有关/Thanks for your question on {question} 的问题。")


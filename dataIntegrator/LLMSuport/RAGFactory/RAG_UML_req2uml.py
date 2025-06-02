import json
import os

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

class RAG_UML_req2uml(RAGAgent):

    def __init__(self, knowledge_base_file_path, prompt_file_path):
        self.knowledge_base_file_path = knowledge_base_file_path
        self.prompt_file_path = prompt_file_path

    @classmethod
    def load_knowledge_base_from_json(self, file_path):
        json_object = FileUtility.read_file(file_path)
        #json_object = FileUtility.read_json_file(file_path)
        return json_object

    @classmethod
    def retrieve_context(self, knowledge_base, question):
        context = []

        # 用户需求说明
        context.append("### 用户需求说明:")
        #user_requirement = knowledge_base["context"]
        user_requirement = knowledge_base
        context.append(user_requirement)

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
            cleaned_json = RAGMockedMessager.txt2uml_MOCKED_AI_ANSWER
            return cleaned_json

        # 解析结果
        json_str = response.generations[0][0].text
        cleaned_json = json_str.replace("```json", "").replace("```", "").strip()
        print("cleaned_json:", cleaned_json)
        return cleaned_json


    @classmethod
    def process_response(self, cleaned_json):

        cleaned_json = re.sub(
            r'(@startuml)(.*?)(@enduml)',
            lambda m: m.group(1) + m.group(2).replace('\n', '\\n') + m.group(3),
            cleaned_json,
            flags=re.DOTALL
        )
        try:
            response_dict = json.loads(cleaned_json)
        except CustomError as e:
            raise e
        except Exception as e:
            raise commonLib.raise_custom_error(error_code="000104",custom_error_message=rf"Error when executing RAG service", e=e)

        return response_dict


    def run_single_question(self, agent_type, question):

        knowledge_base = self.load_knowledge_base_from_json(self.knowledge_base_file_path)
        context = self.retrieve_context(knowledge_base, question)
        prompt = self.load_and_generate_prompts(self.prompt_file_path, context, question)
        response = self.call_ai_agent(agent_type, prompt, question)
        cleaned_json = self.parse_response(response)
        response_dict = self.process_response(cleaned_json)
        self.display_result(response, response_dict)

        response_dict["requirements"] = context
        json_path = os.path.join(CommonParameters.rag_configuration_path,"RAG_UML_uml2schema.json")
        self.write_json(response_dict, json_path)

        json_path = os.path.join(CommonParameters.rag_configuration_path,"RAG_UML_uml2testdata.json")
        self.write_json(response_dict, json_path)

        self.execute(response_dict)

        return response_dict

    # Overwrite the method here, as there is re-structure the dict
    def write_json(self, response_dict: dict, json_file_path):
        try:
            json_dict = {
                "UML_Diagram": response_dict["create_table_uml_statement"],
                "requirements": response_dict["requirements"]
            }
            FileUtility.write_json_file(json_file_path, json_dict)

            return
        except CustomError as e:
            raise e
        except Exception as e:
            raise commonLib.raise_custom_error(error_code="000104",custom_error_message=rf"Error when executing RAG service", e=e)

    def execute(self, response_dict: dict):

        try:

            clickhouseService = ClickhouseService()

            drop_table_sql_statement_list = response_dict["drop_table_sql_statement"]
            for drop_table_sql_statement_dict in drop_table_sql_statement_list:
                table_name = drop_table_sql_statement_dict["table_name"]
                drop_table_sql = drop_table_sql_statement_dict["drop_table_sql"]

                logger.info(rf"executing drop_table_sql_statement: table name{table_name} drop_table_sql {drop_table_sql}")

                clickhouseService.execute_sql(drop_table_sql)

            create_table_sql_statement_list = response_dict["create_table_sql_statement"]
            for create_table_sql_statement_dict in create_table_sql_statement_list:
                table_name = create_table_sql_statement_dict["table_name"]
                create_table_sql = create_table_sql_statement_dict["create_table_sql"]

                logger.info(rf"executing create_table_sql_statement: table name{table_name} create_table_sql {create_table_sql}")

                clickhouseService.execute_sql(create_table_sql)

            return

        except CustomError as e:
            raise e
        except Exception as e:
            raise commonLib.raise_custom_error(error_code="000104",custom_error_message=rf"Error when executing RAG service", e=e)


    def run_prompt_questions(self):
        while True:
            question = input("Please enter your question (type :quit to exit): ")
            if question == ":quit":
                break

            print(f"\n问题：{question}")
            self.run_single_question(question)

            print(rf"感谢询问有关/Thanks for your question on {question} 的问题。")

    def display_result(self, response, result_dict):
        try:
            drop_table_sql_statement_list = result_dict["drop_table_sql_statement"]
            for drop_table_sql_statement_dict in drop_table_sql_statement_list:
                print(drop_table_sql_statement_dict["table_name"])
                print(drop_table_sql_statement_dict["drop_table_sql"])

            create_table_sql_statement_list = result_dict["create_table_sql_statement"]
            for create_table_sql_statement_dict in create_table_sql_statement_list:
                print(create_table_sql_statement_dict["table_name"])
                print(create_table_sql_statement_dict["create_table_sql"])

            print(result_dict["create_table_uml_statement"])
        except CustomError as e:
            raise e
        except Exception as e:
            raise commonLib.raise_custom_error(error_code="000104",custom_error_message=rf"Error when executing RAG service", e=e)

        return result_dict

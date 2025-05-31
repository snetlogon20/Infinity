import json

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.LLMSuport.AiAgents.AiAgentFactory import AIAgentFactory
from dataIntegrator.LLMSuport.RAGFactory.RAGAgent import RAGAgent
from dataIntegrator.LLMSuport.RAGFactory.RAGMockedMessager import RAGMockedMessager
from dataIntegrator.common.CustomError import CustomError
from dataIntegrator.utility.FileUtility import FileUtility
import re

logger = CommonLib.logger
commonLib = CommonLib()

class RAG_UML_uml2schema(RAGAgent):

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

        # 用户需求说明
        context.append("### 1. UML diagram:")
        uml_diagram = knowledge_base["UML_Diagram"]
        context.append(uml_diagram)

        context.append("### 2. User requirements:")
        requirements = knowledge_base["requirements"]
        context.append(requirements)

        return "\n".join(context)

    @classmethod
    def load_and_generate_prompts(self, prompt_file_path, context, question):
        # 读取 提示模板
        prompt_template = FileUtility.read_file(prompt_file_path)

        # 生成增强提示词
        prompt = prompt_template.format(context=context, question=question)
        #prompt = prompt_template
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
            cleaned_json = RAGMockedMessager.UML2schema_MOCKED_AI_ANSWER
            return cleaned_json

        # 解析结果
        json_str = response.generations[0][0].text
        cleaned_json = json_str.replace("```json", "").replace("```", "").strip()
        print("cleaned_json:", cleaned_json)
        return cleaned_json


    @classmethod
    def process_response(self, cleaned_json):
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
        self.write_json(response_dict, rf"D:\workspace_python\infinity\dataIntegrator\test\RegulatoryRAG2UML\schema.json")

        return response_dict

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
            print(result_dict["table_definitions"])
            table_definitions_list = result_dict["table_definitions"]
            for table_definition in table_definitions_list:
                print(table_definition["table_name"])
                print(table_definition["table_definition"])
                print(table_definition["primary_key"])
                print(table_definition["table_alias"])

            table_schema_dict = result_dict["table_schema"]
            for table_name, table_info  in table_schema_dict.items():
                print("table_name:", table_name)
                print("table_info:", table_info)
                columns = table_info.get('columns', {})
                for col_name, col_desc in columns.items():
                    print(col_name)
                    print(col_desc)

        except CustomError as e:
            raise e
        except Exception as e:
            raise commonLib.raise_custom_error(error_code="000104",custom_error_message=rf"Error when executing RAG service", e=e)

        return result_dict

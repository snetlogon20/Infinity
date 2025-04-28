import json

from dataIntegrator.LLMSuport.AiAgents.AiAgentFactory import AIAgentFactory
from dataIntegrator.LLMSuport.RAGFactory.RAGAgent import RAGAgent
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.utility.FileUtility import FileUtility

class RAG_general_inquiry(RAGAgent):

    def __init__(self, knowledge_base_file_path, prompt_file_path):
        self.knowledge_base_file_path = knowledge_base_file_path
        self.prompt_file_path = prompt_file_path

    @classmethod
    def load_knowledge_base_from_json(self, file_path):
        json_object = FileUtility.read_json_file(file_path)
        return json_object

    @classmethod
    def retrieve_context(self, knowledge_base_file_path, question):
        context = FileUtility.read_file(knowledge_base_file_path)
        # context = context.replace("{","{{")
        # context = context.replace("}", "}}")
        return context
        #return ""

    @classmethod
    def load_and_generate_prompts(self, prompt_file_path, context, question):
        # 读取 提示模板
        prompt_template = FileUtility.read_file(prompt_file_path)

        # 生成增强提示词
        prompt = prompt_template.format(context=context, question=question)
        return prompt

    @classmethod
    def call_ai_agent(self, agent_type, prompt, question):
        response = AIAgentFactory.call_agent(agent_type, prompt, question)
        print(response)
        return response

    @classmethod
    def process_response(self, cleaned_json):
        # 组装返回结果
        response_dict = {
            "response_json": cleaned_json
        }

        return response_dict

    def run_single_question(self, agent_type, question):

        knowledge_base = self.load_knowledge_base_from_json(self.knowledge_base_file_path)
        #context = self.retrieve_context(knowledge_base, question)
        context = self.retrieve_context(self.knowledge_base_file_path, question)
        prompt = self.load_and_generate_prompts(self.prompt_file_path, context, question)
        response = self.call_ai_agent(agent_type, prompt, question)
        cleaned_json = self.parse_response(response)
        response_dict = self.process_response(cleaned_json)
        self.display_result(response, response_dict)

        return response_dict

    def display_result(self, response, result_dict):
        # if "error" in response:
        #     print(f"错误：{response['error']}")
        #     if "sql_attempt" in response:
        #         print(f"尝试执行的SQL：{response['sql_attempt']}")
        # else:
        #     print("response_json", result_dict["response_json"])
        # return response

        print("response_json", result_dict["response_json"])
        return response
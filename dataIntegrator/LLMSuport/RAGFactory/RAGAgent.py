from abc import ABC, abstractmethod

from dataIntegrator import CommonLib
from dataIntegrator.LLMSuport.AiAgents.AiAgentFactory import AIAgentFactory
from dataIntegrator.common.CustomError import CustomError
from dataIntegrator.utility.FileUtility import FileUtility

logger = CommonLib.logger
commonLib = CommonLib()

class RAGAgent(ABC):
    @abstractmethod
    def run_single_question(self, agent_type, prompt: str) -> str:
        pass

    @classmethod
    def load_knowledge_base_from_json(self, file_path):
        json_object = FileUtility.read_json_file(file_path)
        return json_object

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
    def parse_response(cls, response):
        # 解析结果
        json_str = response.generations[0][0].text
        cleaned_json = json_str.replace("```json", "").replace("```", "").strip()
        print("cleaned_json:", cleaned_json)
        return cleaned_json

    def write_json(self, response_dict: dict, joson_file_path):
        try:
            FileUtility.write_json_file(joson_file_path, response_dict)

            return
        except CustomError as e:
            raise e
        except Exception as e:
            raise commonLib.raise_custom_error(error_code="000104",custom_error_message=rf"Error when executing RAG service", e=e)


    def run_single_question(self, agent_type, question):

        knowledge_base = self.load_knowledge_base_from_json(self.knowledge_base_file_path)
        context = self.retrieve_context(knowledge_base, question)
        prompt = self.load_and_generate_prompts(self.prompt_file_path, context, question)
        response = self.call_ai_agent(agent_type, prompt, question)
        response_dict = self.process_response(response)
        self.display_result(response, response_dict)

        return response_dict
import json

from dataIntegrator import CommonLib
from dataIntegrator.LLMSuport.AiAgents.AiAgentFactory import AIAgentFactory
from dataIntegrator.LLMSuport.RAGFactory.RAGAgent import RAGAgent
from dataIntegrator.common.CustomError import CustomError
from dataIntegrator.utility.FileUtility import FileUtility
import re

logger = CommonLib.logger
commonLib = CommonLib()

class RAG_UML_txt2uml(RAGAgent):

    def __init__(self, knowledge_base_file_path, prompt_file_path):
        self.knowledge_base_file_path = knowledge_base_file_path
        self.prompt_file_path = prompt_file_path

    @classmethod
    def load_knowledge_base_from_json(self, file_path):
        json_object = FileUtility.read_file(file_path)
        return json_object

    @classmethod
    def retrieve_context(self, knowledge_base, question):
        context = []

        # 用户需求说明
        context.append("### 用户需求说明:")
        context.append(knowledge_base)

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
        # response = AIAgentFactory.call_agent(agent_type, prompt, question)
        # print(response)
        # return response
        pass

    @classmethod
    def parse_response(cls, response):
        cleaned_json = """{
        "create_table_sql_statement": [
          {
          "table_name": "Core_LC_Master_Data",
          "create_table_sql": "CREATE TABLE Core_LC_Master_Data (LC_ID String, Applicant_ID String, Beneficiary_ID String, Issuing_Bank_ID String, Advising_Bank_ID String, LC_Type String, LC_Currency String, LC_Amount Decimal(15, 2), Issue_Date Date, Expiry_Date Date, Latest_Shipment_Date Date, LC_Description String)"
          },
          {
          "table_name": "Documentary_Compliance",
          "create_table_sql": "CREATE TABLE Documentary_Compliance (Document_ID String, LC_ID_Ref String, Document_Type String, Document_Status String, Submission_Date Date, Review_Date Date, Discrepancy_Details String, Document_Reference_Number String)"
          },
          {
          "table_name": "Transaction_Tracking",
          "create_table_sql": "CREATE TABLE Transaction_Tracking (Transaction_ID String, LC_ID_Ref String, Transaction_Date Date, Transaction_Type String, Party_Involved String, Transaction_Status String, Previous_Transaction_ID String)"
          }
        ],
        "create_table_uml_statement": "@startuml
            entity Core_LC_Master_Data {
                LC_ID : String,
                Applicant_ID : String,
                Beneficiary_ID : String,
                Issuing_Bank_ID : String,
                Advising_Bank_ID : String,
                LC_Type : String,
                LC_Currency : String,
                LC_Amount : Decimal(15, 2),
                Issue_Date : Date,
                Expiry_Date : Date,
                Latest_Shipment_Date : Date,
                LC_Description : String
            }
            entity Documentary_Compliance {
                Document_ID : String,
                LC_ID_Ref : String,
                Document_Type : String,
                Document_Status : String,
                Submission_Date : Date,
                Review_Date : Date,
                Discrepancy_Details : String,
                Document_Reference_Number : String
            }
            entity Transaction_Tracking {
                Transaction_ID : String,
                LC_ID_Ref : String,
                Transaction_Date : Date,
                Transaction_Type : String,
                Party_Involved : String,
                Transaction_Status : String,
                Previous_Transaction_ID : String
            }
            Core_LC_Master_Data ||--o{ Documentary_Compliance : contains
            Core_LC_Master_Data ||--o{ Transaction_Tracking : contains
            @enduml",
        "explanation_in_Mandarin": "该JSON包含创建三个表的SQL语句和对应的Plant UML图。SQL语句使用Clickhouse语法，每个表的字段根据提供的业务需求定义。UML图中展示了三个实体及其关系，其中Core_LC_Master_Data与另外两个表是一对多的关系。",
        "explanation_in_English": "This JSON contains the SQL statements to create three tables and the corresponding Plant UML diagram. The SQL statements use Clickhouse syntax, and the fields of each table are defined according to the provided business requirements. The UML diagram shows the three entities and their relationships, where Core_LC_Master_Data has a one-to-many relationship with the other two tables.",
        "feedback":"无"
            }"""
        return cleaned_json

        # 解析结果
        # json_str = response.generations[0][0].text
        # cleaned_json = json_str.replace("```json", "").replace("```", "").strip()
        # print("cleaned_json:", cleaned_json)
        # return cleaned_json


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
            print(result_dict["create_table_sql_statement"])
            create_table_sql_statement_list = result_dict["create_table_sql_statement"]
            for create_table_sql_statement_dict in create_table_sql_statement_list:
                print(create_table_sql_statement_dict["table_name"])
                print(create_table_sql_statement_dict["create_table_sql"])

            print(result_dict["create_table_uml_statement"])
            print(result_dict["explanation_in_Mandarin"])
            print(result_dict["explanation_in_English"])
        except CustomError as e:
            raise e
        except Exception as e:
            raise commonLib.raise_custom_error(error_code="000104",custom_error_message=rf"Error when executing RAG service", e=e)

        return result_dict

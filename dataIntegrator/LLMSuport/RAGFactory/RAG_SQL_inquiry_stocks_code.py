import json

from dataIntegrator.LLMSuport.AiAgents.AiAgentFactory import AIAgentFactory
from dataIntegrator.LLMSuport.RAGFactory.RAGAgent import RAGAgent
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.utility.FileUtility import FileUtility

class RAG_SQL_inquiry_stocks_code(RAGAgent):

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

        # 表结构信息
        context.append("### 表结构说明:")
        for table, schema in knowledge_base["table_schema"].items():
            context.append(f"{table} 表结构如下：")
            for col, desc in schema["columns"].items():
                context.append(f"- {col}: {desc}")

        # 匹配常见问题
        context.append("\n### 相关常见查询:")
        for query in knowledge_base["common_queries"]:
            context.append(f"- {query['question']}: {query['sql']}")

        # 业务规则匹配
        context.append("\n### 业务规则:")
        for rule in knowledge_base["business_rules"]:
            context.append(f"- {rule}")

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
        response = AIAgentFactory.call_agent(agent_type, prompt, question)
        print(response)
        return response

    @classmethod
    def process_response(self, response):
        # 解析结果
        json_str = response.generations[0][0].text
        cleaned_json = json_str.replace("```json", "").replace("```", "").strip()
        print(cleaned_json)

        # 查询数据
        try:
            result = json.loads(cleaned_json)
            sql = result["sql"]

            clickhouseService = ClickhouseService()
            data = clickhouseService.getDataFrameWithoutColumnsName(sql)
            # print(data)
        except Exception as e:
            return {"error": str(e), "sql_attempt": sql}

        # 组装返回结果
        response_dict = {
            "sql": sql,
            "explanation_in_Mandarin": result["explanation_in_Mandarin"],
            "explanation_in_English": result["explanation_in_English"],
            "results": data,
            "isPlotRequired": result["isPlotRequired"],
            "PlotX": result["PlotX"],
            "PlotY": result["PlotY"],
            "start_date": result["start_date"],
            "end_date": result["end_date"]
        }

        return response_dict


    def run_single_question(self, agent_type, question):

        knowledge_base = self.load_knowledge_base_from_json(self.knowledge_base_file_path)
        context = self.retrieve_context(knowledge_base, question)
        prompt = self.load_and_generate_prompts(self.prompt_file_path, context, question)
        response = self.call_ai_agent(agent_type, prompt, question)
        response_dict = self.process_response(response)
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
        if "error" in response:
            print(f"错误：{response['error']}")
            if "sql_attempt" in response:
                print(f"尝试执行的SQL：{response['sql_attempt']}")
        else:
            print("生成的SQL/SQL generated：", result_dict["sql"])
            print("解释说明：", result_dict["explanation_in_Mandarin"])
            print("Explain：", result_dict["explanation_in_English"])
            print("查询结果/Result：")
            print(result_dict["results"])
            print("isPlotRequired:", result_dict["isPlotRequired"])
            print("PlotX:", result_dict["PlotX"])
            print("PlotY:", result_dict["PlotY"])
        return response
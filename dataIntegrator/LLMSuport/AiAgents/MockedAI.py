from sparkai.llm.llm import ChatSparkLLM, ChunkPrintHandler
from sparkai.core.messages import ChatMessage

from dataIntegrator.LLMSuport.AiAgents.AIAgent import AIAgent
from dataIntegrator.common.CommonParameters import CommonParameters

class Generation:
    def __init__(self, text):
        self.text = text

class Response:
    def __init__(self, text):
        self.text = text
        self.generations = Generation(text)
        self.error = ""

class MockedAI(AIAgent):

    def inquiry(self, prompt: str, question: str):

        print(rf"正在查询 Spark LLM，请稍等/Inquiry Spark LLM for: {question}")

        response = Response("initial_text")
        response.generations = [
            [Generation(question)],  # 第一个外层元素，包含一个内层 Generation 对象
            # 其他元素...
        ]


        print(rf"查询 Spark LLM，已完成, response: {response}")
        return response

if __name__ == "__main__":
    mockedAI = MockedAI()
    mockedAI.inquiry("<prompt>", "<question>")
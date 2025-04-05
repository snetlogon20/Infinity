from sparkai.llm.llm import ChatSparkLLM, ChunkPrintHandler
from sparkai.core.messages import ChatMessage

from dataIntegrator.LLMSuport.AiAgents.AIAgent import AIAgent
from dataIntegrator.common.CommonParameters import CommonParameters

class SparkAI(AIAgent):

    def inquiry(self, prompt: str, question: str):
        spark = ChatSparkLLM(
            spark_api_url=CommonParameters.SPARKAI_URL,
            spark_app_id=CommonParameters.SPARK_APPID,
            spark_api_key=CommonParameters.SPARK_API_KEY,
            spark_api_secret=CommonParameters.SPARK_API_SECRET,
            spark_llm_domain=CommonParameters.SPARKAI_DOMAIN,
            streaming=False,
        )
        print(rf"正在查询 Spark LLM，请稍等/Inquiry Spark LLM for: {question}")
        messages = [ChatMessage(role="user", content=prompt)]
        handler = ChunkPrintHandler()
        response = spark.generate([messages], callbacks=[handler])
        print("查询 Spark LLM，已完成")
        return response
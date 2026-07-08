from sparkai.errors import SparkAIConnectionError
from sparkai.llm.llm import ChatSparkLLM, ChunkPrintHandler
from sparkai.core.messages import ChatMessage

from dataIntegrator import CommonLib
from dataIntegrator.LLMSuport.AiAgents.AIAgent import AIAgent
from dataIntegrator.common.CommonParameters import CommonParameters

logger = CommonLib.logger

class SparkAI(AIAgent):


    @classmethod
    def inquiry(self, prompt: str, question: str):
        spark = ChatSparkLLM(
            request_timeout=CommonParameters.SPARKAI_URL_REQUEST_TIMEOUT,
            spark_api_url=CommonParameters.SPARKAI_URL,
            spark_app_id=CommonParameters.SPARK_APPID,
            spark_api_key=CommonParameters.SPARK_API_KEY,
            spark_api_secret=CommonParameters.SPARK_API_SECRET,
            spark_llm_domain=CommonParameters.SPARKAI_DOMAIN,
            streaming=False,
        )
        logger.info(rf"正在查询 Spark LLM，请稍等/Inquiry Spark LLM for: {prompt}")
        logger.info(rf"正在查询 Spark LLM，请稍等/Inquiry Spark LLM for: {question}")

        try:
            messages = [ChatMessage(role="user", content=prompt)]
            handler = ChunkPrintHandler()
            response = spark.generate([messages], callbacks=[handler])
        except SparkAIConnectionError as e:
            print(f"连接异常（错误码 {e}")
        except Exception as e:
            print(f"其他异常: {e}")

        logger.info(rf"查询 Spark LLM，已完成, response: {response.generations[0][0].text}")
        return response
from sparkai.errors import SparkAIConnectionError
from sparkai.llm.llm import ChatSparkLLM, ChunkPrintHandler
from sparkai.core.messages import ChatMessage

from dataIntegrator import CommonLib
from dataIntegrator.LLMSuport.AiAgents.AIAgent import AIAgent
from dataIntegrator.common.CommonParameters import CommonParameters

logger = CommonLib.logger


class SparkAI(AIAgent):
    """讯飞星火 Agent(sparkai SDK), 统一返回 str"""

    def inquiry(self, prompt: str, question: str = "",
                history_messages: list = None) -> str:
        spark = ChatSparkLLM(
            request_timeout=CommonParameters.SPARKAI_URL_REQUEST_TIMEOUT,
            spark_api_url=CommonParameters.SPARKAI_URL,
            spark_app_id=CommonParameters.SPARK_APPID,
            spark_api_key=CommonParameters.SPARK_API_KEY,
            spark_api_secret=CommonParameters.SPARK_API_SECRET,
            spark_llm_domain=CommonParameters.SPARKAI_DOMAIN,
            streaming=False,
        )
        logger.info(rf"正在查询 Spark LLM，请稍等/Inquiry Spark LLM for: {question}")

        try:
            messages = []
            if history_messages:
                messages.extend(ChatMessage(role=m["role"], content=m["content"])
                                for m in history_messages)
            messages.append(ChatMessage(role="user", content=prompt))
            handler = ChunkPrintHandler()
            response = spark.generate([messages], callbacks=[handler])
            answer = response.generations[0][0].text
        except SparkAIConnectionError as e:
            logger.error(f"Spark LLM 连接异常: {e}")
            raise
        except Exception:
            logger.exception("Spark LLM 调用失败")
            raise

        logger.info(rf"查询 Spark LLM，已完成, response: {answer}")
        return answer

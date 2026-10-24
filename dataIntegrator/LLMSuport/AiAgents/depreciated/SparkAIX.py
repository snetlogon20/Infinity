import requests

from dataIntegrator import CommonLib
from dataIntegrator.LLMSuport.AiAgents.AIAgent import AIAgent
from dataIntegrator.common.MyTokens import MyTokens

logger = CommonLib.logger


class SparkX2(AIAgent):
    """讯飞星火 X2 Agent(OpenAI 兼容接口)

    multi_step_inquiry 由 AIAgent 基类模板方法提供。
    """

    BASE_URL = "https://spark-api-open.xf-yun.com/x2/chat/completions"
    MODEL = "spark-x"      # 官方文档指定，不是 "x2"
    TIMEOUT_SECONDS = 120

    def inquiry(self, prompt: str, question: str = "",
                history_messages: list = None) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MyTokens.SPARK_API_KEY}:{MyTokens.SPARK_API_SECRET}"
        }
        messages = list(history_messages) if history_messages else []
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.MODEL,
            "messages": messages,
            "temperature": 0.7,
            "stream": False
        }

        logger.info(f"正在查询 Spark X2，prompt 长度={len(prompt)} 字符，"
                    f"历史消息数={len(history_messages) if history_messages else 0}")

        try:
            resp = requests.post(self.BASE_URL, headers=headers, json=payload,
                                 timeout=self.TIMEOUT_SECONDS)
            resp.raise_for_status()
            answer = resp.json()["choices"][0]["message"]["content"]
            logger.info(f"Spark X2 返回成功: {answer[:200]}...")
            return answer
        except Exception:
            logger.exception("Spark X2 调用失败")
            raise

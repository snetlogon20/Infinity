import requests

from dataIntegrator import CommonLib
from dataIntegrator.LLMSuport.AiAgents.AIAgent import AIAgent
from dataIntegrator.common.MyTokens import MyTokens

logger = CommonLib.logger


class ZhipuGLM4(AIAgent):
    """智谱 GLM-4-Flash 适配（OpenAI 兼容接口）

    multi_step_inquiry 由 AIAgent 基类模板方法提供。
    """

    BASE_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    MODEL = "glm-4-flash"
    TIMEOUT_SECONDS = 60

    def inquiry(self, prompt: str, question: str = "",
                history_messages: list = None) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MyTokens.ZHIPU_API_KEY}"
        }
        messages = list(history_messages) if history_messages else []
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.MODEL,
            "messages": messages,
            "temperature": 0.7,
            "stream": False
        }

        logger.info(f"正在查询智谱 GLM-4-Flash，问题: {question}")
        logger.info(f"正在查询智谱 GLM-4-Flash，prompt 长度={len(prompt)} 字符，"
                    f"历史消息数={len(history_messages) if history_messages else 0}")

        try:
            resp = requests.post(self.BASE_URL, headers=headers, json=payload,
                                timeout=self.TIMEOUT_SECONDS)
            resp.raise_for_status()
            answer = resp.json()["choices"][0]["message"]["content"]
            logger.info(f"智谱 GLM-4-Flash 返回成功: {answer[:200]}...")
            return answer
        except Exception:
            logger.exception("智谱 GLM-4-Flash 调用失败")
            raise

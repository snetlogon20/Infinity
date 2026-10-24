import requests

from dataIntegrator import CommonLib
from dataIntegrator.LLMSuport.AiAgents.AIAgent import AIAgent
from dataIntegrator.common.MyTokens import MyTokens

logger = CommonLib.logger


class BailianAI(AIAgent):
    """阿里百炼 Agent(DashScope OpenAI 兼容接口)

    multi_step_inquiry 由 AIAgent 基类模板方法提供。
    """

    BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    MODEL = "qwen-plus"
    TIMEOUT_SECONDS = 120

    def inquiry(self, prompt: str, question: str = "",
                history_messages: list = None) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MyTokens.BAILIAN_API_KEY}"
        }
        messages = list(history_messages) if history_messages else []
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.MODEL,
            "messages": messages,
            "temperature": 0.7,
            "stream": False
        }

        logger.info(f"正在查询 百炼，问题: {question}")
        logger.info(f"正在查询 百炼，prompt 长度={len(prompt)} 字符，"
                    f"历史消息数={len(history_messages) if history_messages else 0}")

        try:
            resp = requests.post(self.BASE_URL, headers=headers, json=payload,
                                 timeout=self.TIMEOUT_SECONDS)
            if resp.status_code != 200:
                logger.error(f"百炼 HTTP {resp.status_code}，响应内容: {resp.text[:500]}")
            resp.raise_for_status()
            answer = resp.json()["choices"][0]["message"]["content"]
            logger.info(f"百炼 返回成功: {answer[:200]}...")
            return answer
        except Exception:
            logger.exception("百炼 调用失败")
            raise

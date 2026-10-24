import requests

from dataIntegrator import CommonLib
from dataIntegrator.LLMSuport.AiAgents.AIAgent import AIAgent
from dataIntegrator.common.MyTokens import MyTokens

logger = CommonLib.logger


class HuoshanAI(AIAgent):
    """火山方舟(豆包) Agent(OpenAI 兼容接口)

    模型选择通过构造参数 model 注入, 不传则用 DEFAULT_MODEL:
        ep-xxx   -> 方舟在线推理接入点 ID(控制台创建, 如 ep-20261011112622-r6zfg)
        也可直接填模型名(如 doubao-seed-1-6-lite, 以方舟控制台开通为准)

    直接调用:
        HuoshanAI()                                   # 默认接入点
        HuoshanAI(model="ep-xxxxxxxx")                # 其他接入点/模型

    工厂调用(构造参数经 new_agent 的 **kwargs 透传):
        AIAgentFactory.new_agent("huoshan", model="ep-xxxxxxxx")

    multi_step_inquiry 由 AIAgent 基类模板方法提供。
    """

    BASE_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    DEFAULT_MODEL = "ep-20261011112622-r6zfg"   # doubao-seed-2-1-lite
    TIMEOUT_SECONDS = 60

    def __init__(self, model: str = None):
        self.model = model or self.DEFAULT_MODEL
        self.api_key = MyTokens.HUOSHAN_API_KEY

    def inquiry(self, prompt: str, question: str = "",
                history_messages: list = None) -> str:
        if not self.api_key:
            raise ValueError(
                "火山方舟 API Key 未配置, 请在 MyTokens 中填写 HUOSHAN_API_KEY")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        messages = list(history_messages) if history_messages else []
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "stream": False
        }

        logger.info(f"正在查询火山方舟({self.model})，问题: {question}")
        logger.info(f"正在查询火山方舟({self.model})，prompt 长度={len(prompt)} 字符，"
                    f"历史消息数={len(history_messages) if history_messages else 0}")

        try:
            resp = requests.post(self.BASE_URL, headers=headers, json=payload,
                                timeout=self.TIMEOUT_SECONDS)
            if resp.status_code != 200:
                logger.error(f"火山方舟 HTTP {resp.status_code}，响应内容: {resp.text[:500]}")
            resp.raise_for_status()
            answer = resp.json()["choices"][0]["message"]["content"]
            logger.info(f"火山方舟({self.model}) 返回成功: {answer[:200]}...")
            return answer
        except Exception:
            logger.exception(f"火山方舟({self.model}) 调用失败")
            raise

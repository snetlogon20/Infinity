import requests

from dataIntegrator import CommonLib
from dataIntegrator.LLMSuport.AiAgents.AIAgent import AIAgent
from dataIntegrator.common.MyTokens import MyTokens

logger = CommonLib.logger


class HunyuanAI(AIAgent):
    """腾讯混元 Agent(OpenAI 兼容接口, 双平台自动路由)

    模型选择通过构造参数 model 注入, 不传则用 DEFAULT_MODEL:
        hy3 / hy4-preview 等  -> TokenHub(tokenhub-intl.tencentmaas.com, 用 YUNYUAN_API_KEY)
        hunyuan-* 系列        -> 旧版混元(api.hunyuan.cloud.tencent.com, 用 YUNYUAN_LEGACY_API_KEY,
                                 其中 hunyuan-lite 永久免费)

    直接调用:
        HunyuanAI()                          # 默认 hy3
        HunyuanAI(model="hy4-preview")       # TokenHub 其他模型
        HunyuanAI(model="hunyuan-lite")      # 旧平台免费模型

    工厂调用(构造参数经 new_agent 的 **kwargs 透传):
        AIAgentFactory.new_agent("hunyuan", model="hunyuan-lite")

    multi_step_inquiry 由 AIAgent 基类模板方法提供。
    """

    TOKENHUB_BASE_URL = "https://tokenhub-intl.tencentmaas.com/v1/chat/completions"
    LEGACY_BASE_URL = "https://api.hunyuan.cloud.tencent.com/v1/chat/completions"
    DEFAULT_MODEL = "hy3"
    TIMEOUT_SECONDS = 60

    def __init__(self, model: str = None):
        self.model = model or self.DEFAULT_MODEL
        # hunyuan-* 系列在旧平台(lite 永久免费), hy* 系列在 TokenHub
        if self.model.startswith("hunyuan"):
            self.base_url = self.LEGACY_BASE_URL
            self.api_key = MyTokens.YUNYUAN_LEGACY_API_KEY
        else:
            self.base_url = self.TOKENHUB_BASE_URL
            self.api_key = MyTokens.YUNYUAN_API_KEY

    def inquiry(self, prompt: str, question: str = "",
                history_messages: list = None) -> str:
        if not self.api_key:
            raise ValueError(
                f"模型 {self.model} 对应平台的 API Key 未配置, "
                f"请在 MyTokens 中填写 YUNYUAN_API_KEY(TokenHub) "
                f"或 YUNYUAN_LEGACY_API_KEY(旧版混元)")

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

        logger.info(f"正在查询腾讯混元({self.model})，问题: {question}")
        logger.info(f"正在查询腾讯混元({self.model})，prompt 长度={len(prompt)} 字符，"
                    f"历史消息数={len(history_messages) if history_messages else 0}")

        try:
            resp = requests.post(self.base_url, headers=headers, json=payload,
                                timeout=self.TIMEOUT_SECONDS)
            if resp.status_code != 200:
                logger.error(f"腾讯混元 HTTP {resp.status_code}，响应内容: {resp.text[:500]}")
            resp.raise_for_status()
            answer = resp.json()["choices"][0]["message"]["content"]
            logger.info(f"腾讯混元({self.model}) 返回成功: {answer[:200]}...")
            return answer
        except Exception:
            logger.exception(f"腾讯混元({self.model}) 调用失败")
            raise

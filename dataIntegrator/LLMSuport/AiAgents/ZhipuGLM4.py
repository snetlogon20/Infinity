import requests

from dataIntegrator import CommonLib
from dataIntegrator.LLMSuport.AiAgents import AIAgent
from dataIntegrator.common.MyTokens import MyTokens

logger = CommonLib.logger


class ZhipuGLM4(AIAgent):
    """智谱 GLM-4-Flash 适配（OpenAI 兼容接口）"""

    BASE_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    @classmethod
    def inquiry(cls, prompt: str, question: str = "", history_messages: list = None) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MyTokens.ZHIPU_API_KEY}"
        }

        messages = []
        if history_messages:
            messages.extend(history_messages)
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": "glm-4-flash",
            "messages": messages,
            "temperature": 0.7,
            "stream": False
        }

        logger.info(f"正在查询智谱 GLM-4-Flash，prompt 长度={len(prompt)} 字符，"
                     f"历史消息数={len(history_messages) if history_messages else 0}")

        try:
            resp = requests.post(cls.BASE_URL, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()

            answer = data["choices"][0]["message"]["content"]
            logger.info(f"智谱 GLM-4-Flash 返回成功: {answer[:200]}...")
            return answer

        except Exception as e:
            logger.exception("智谱 GLM-4-Flash 调用失败")
            raise

    @classmethod
    def multi_step_inquiry(cls, step_prompts: list, question: str = "") -> str:
        """多步推理，逐步执行并维护对话历史"""
        history_messages = []
        last_result = ""

        for i, step_prompt in enumerate(step_prompts):
            logger.info(f"========== 智谱 GLM-4-Flash 第 {i + 1}/{len(step_prompts)} 步推理 ==========")

            result = cls.inquiry(step_prompt, question, history_messages)

            history_messages.append({"role": "user", "content": step_prompt})
            history_messages.append({"role": "assistant", "content": result})
            last_result = result

        logger.info(f"========== 智谱 GLM-4-Flash 多步推理完成，共 {len(step_prompts)} 步 ==========")
        return last_result
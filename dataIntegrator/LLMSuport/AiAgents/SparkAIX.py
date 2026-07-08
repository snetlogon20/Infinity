import requests

from dataIntegrator import CommonLib
from dataIntegrator.LLMSuport.AiAgents import AIAgent
from dataIntegrator.common.MyTokens import MyTokens

logger = CommonLib.logger

class SparkX2(AIAgent):

    @classmethod
    def inquiry(self, prompt: str, question: str, history_messages: list = None):
        url = "https://spark-api-open.xf-yun.com/x2/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer %s:%s" % (MyTokens.SPARK_API_KEY, MyTokens.SPARK_API_SECRET)
        }

        messages = []
        if history_messages:
            messages.extend(history_messages)
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": "spark-x",      # ✅ 官方文档指定，不是 "x2"
            "messages": messages,
            "temperature": 0.7,
            "stream": False
        }

        logger.info(f"正在查询 Spark X2，prompt 长度={len(prompt)} 字符，历史消息数={len(history_messages) if history_messages else 0}")

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()

            answer = data["choices"][0]["message"]["content"]
            logger.info(f"Spark X2 返回成功: {answer[:200]}...")
            return answer

        except Exception as e:
            logger.exception("Spark X2 调用失败")
            raise

    @classmethod
    def multi_step_inquiry(self, step_prompts: list, question: str = "") -> str:
        """将大 prompt 拆分为多步小请求，逐步推理并合并结果

        利用 messages 数组维护多轮对话历史（user/assistant 交替），
        每一步的输出作为上一轮 assistant 消息，避免把历史拼接成巨大字符串。

        Args:
            step_prompts: 逐步 prompt 列表，如 [step1_prompt, step2_prompt, step3_prompt]
            question: 保留参数（兼容 AIAgent 接口）

        Returns:
            最后一步的完整输出
        """
        history_messages = []
        last_result = ""

        for i, step_prompt in enumerate(step_prompts):
            logger.info(f"========== Spark X2 第 {i + 1}/{len(step_prompts)} 步推理 ==========")

            result = self.inquiry(step_prompt, question, history_messages)

            # 将本轮 Q&A 加入历史，供下一步引用
            history_messages.append({"role": "user", "content": step_prompt})
            history_messages.append({"role": "assistant", "content": result})
            last_result = result

        logger.info(f"========== Spark X2 多步推理完成，共 {len(step_prompts)} 步 ==========")
        return last_result

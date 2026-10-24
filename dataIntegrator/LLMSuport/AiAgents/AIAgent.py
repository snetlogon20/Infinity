r"""AI Agent 统一契约(抽象基类 + 模板方法)

契约(所有实现必须遵守):
    inquiry(prompt, question="", history_messages=None) -> str
        单轮调用, 统一返回 str(模型回答文本), 异常时 raise, 不吞错。
        prompt:           完整提示词(含上下文/指令)
        question:         原始问题(仅用于日志与展示)
        history_messages: 多轮对话历史, [{"role": "user"/"assistant", "content": str}]

    multi_step_inquiry(step_prompts, question="") -> str
        模板方法(本基类提供): 将大 prompt 拆分为多步小请求, 逐步推理,
        user/assistant 交替进入 history, 返回最后一步输出。子类无需重复实现。

历史教训:
    早期实现各自为政(classmethod/实例混用, 返回 Response 对象/str 混杂,
    签名不一), 导致工厂的多态名存实亡 —— 换 agent_type 调用方就要改代码。
    本契约统一后, 调用方一律拿 str。
"""

from abc import ABC, abstractmethod

from dataIntegrator import CommonLib

logger = CommonLib.logger


class AIAgent(ABC):

    @abstractmethod
    def inquiry(self, prompt: str, question: str = "",
                history_messages: list = None) -> str:
        """单轮调用 LLM

        Args:
            prompt: 完整提示词(含上下文)
            question: 原始问题(仅用于日志/展示)
            history_messages: 多轮对话历史 [{"role", "content"}]

        Returns:
            str: 模型回答文本
        """
        pass

    def multi_step_inquiry(self, step_prompts: list, question: str = "") -> str:
        """将大 prompt 拆分为多步小请求，逐步推理并合并结果

        利用 messages 数组维护多轮对话历史（user/assistant 交替），
        每一步的输出作为上一轮 assistant 消息，避免把历史拼接成巨大字符串。

        Args:
            step_prompts: 逐步 prompt 列表，如 [step1_prompt, step2_prompt, step3_prompt]
            question: 原始问题(仅用于日志/展示)

        Returns:
            最后一步的完整输出
        """
        history_messages = []
        last_result = ""

        for i, step_prompt in enumerate(step_prompts):
            logger.info(f"========== 第 {i + 1}/{len(step_prompts)} 步推理 ==========")
            result = self.inquiry(step_prompt, question, history_messages)

            # 将本轮 Q&A 加入历史，供下一步引用
            history_messages.append({"role": "user", "content": step_prompt})
            history_messages.append({"role": "assistant", "content": result})
            last_result = result

        logger.info(f"========== 多步推理完成，共 {len(step_prompts)} 步 ==========")
        return last_result

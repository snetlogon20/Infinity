from dataIntegrator import CommonLib
from dataIntegrator.LLMSuport.AiAgents.AIAgent import AIAgent

logger = CommonLib.logger


class MockedAI(AIAgent):
    """本地假 Agent(离线测试/CI 用，不访问真实 AI 接口)

    统一契约: 与真实 Agent 完全同构, inquiry 返回 str。
    默认原样返回 question(无 question 时返回 prompt)。
    multi_step_inquiry 由 AIAgent 基类模板方法提供。
    """

    MODEL = "mocked"

    def inquiry(self, prompt: str, question: str = "",
                history_messages: list = None) -> str:
        logger.info(f"正在查询 MockedAI，问题: {question}")
        logger.info(f"正在查询 MockedAI，prompt 长度={len(prompt)} 字符，"
                    f"历史消息数={len(history_messages) if history_messages else 0}")

        try:
            answer = question if question else prompt
            logger.info(f"MockedAI 返回成功: {answer[:200]}...")
            return answer
        except Exception:
            logger.exception("MockedAI 调用失败")
            raise

r"""AI Agent 工厂

统一入口:
    new_agent(agent_type, **kwargs)                          -> AIAgent 实例
    call_agent(agent_type, prompt, question="", **kwargs)    -> str(单轮)
    call_agent_steps(agent_type, step_prompts, question="")  -> str(多步推理)
    call_agent_failover(prompt, question, engines)           -> FailoverResult(单轮降级)
    call_agent_steps_failover(step_prompts, question, engines) -> FailoverResult(多步降级, 整链重试)

约定:
    注册表 key 统一小写, 查找大小写不敏感(兼容旧 key "SparkAIX");
    新 Agent 通过 register() 自注册(装饰器或显式调用), 无需改工厂代码;
    call_agent 的 **kwargs 透传给 inquiry(如 history_messages);
    降级链默认顺序在 CommonParameters.AI_ENGINE_FAILOVER_ORDER 配置。
"""

from typing import Dict, NamedTuple, Type

from dataIntegrator import CommonLib
from dataIntegrator.common.CommonParameters import CommonParameters
from dataIntegrator.LLMSuport.AiAgents.AIAgent import AIAgent
from dataIntegrator.LLMSuport.AiAgents.HuoshanAI import HuoshanAI
from dataIntegrator.LLMSuport.AiAgents.HunyuanAI import HunyuanAI
from dataIntegrator.LLMSuport.AiAgents.MockedAI import MockedAI
from dataIntegrator.LLMSuport.AiAgents.ZhipuGLM4 import ZhipuGLM4

logger = CommonLib.logger


class FailoverResult(NamedTuple):
    """降级调用结果: engine=最终成功的引擎, answer=回答文本"""
    engine: str
    answer: str


class AIAgentFactory:
    _registry: Dict[str, Type[AIAgent]] = {}

    @classmethod
    def register(cls, name: str, agent_class: Type[AIAgent]):
        """注册(或覆盖)一个 Agent, 供外部扩展插件式接入"""
        if not (isinstance(agent_class, type) and issubclass(agent_class, AIAgent)):
            raise TypeError(f"{agent_class} is not a subclass of AIAgent")
        cls._registry[str(name).lower()] = agent_class

    @classmethod
    def _resolve(cls, agent_type: str) -> Type[AIAgent]:
        agent_class = cls._registry.get(str(agent_type).lower())
        if not agent_class:
            available = ", ".join(sorted(cls._registry))
            raise ValueError(
                f"Unregistered agent type: {agent_type} (available: {available})")
        return agent_class

    @classmethod
    def new_agent(cls, agent_type: str, **kwargs) -> AIAgent:
        """创建代理实例"""
        return cls._resolve(agent_type)(**kwargs)

    @classmethod
    def call_agent(cls, agent_type: str, prompt: str, question: str = "",
                   **kwargs) -> str:
        """直接调用代理功能(单轮, 返回 str; **kwargs 透传, 如 history_messages)"""
        agent = cls.new_agent(agent_type)
        return agent.inquiry(prompt, question, **kwargs)

    @classmethod
    def call_agent_steps(cls, agent_type: str, step_prompts: list,
                         question: str = "") -> str:
        """多步推理(拆分长 prompt, 逐步执行并维护对话历史)"""
        agent = cls.new_agent(agent_type)
        return agent.multi_step_inquiry(step_prompts, question)

    @classmethod
    def _default_failover_engines(cls) -> list:
        """降级链默认引擎: 开关打开走离线 mockedai, 否则走配置的降级顺序"""
        if CommonParameters.IF_ENABLE_MOCKED_AI:
            return ["mockedai"]
        return list(CommonParameters.AI_ENGINE_FAILOVER_ORDER)

    @classmethod
    def call_agent_failover(cls, prompt: str, question: str = "",
                            engines: list = None) -> "FailoverResult":
        """按引擎顺序依次尝试(责任链式降级), 单个引擎异常时自动切下一个

        默认顺序: IF_ENABLE_MOCKED_AI=True -> ['mockedai'](离线);
                  否则 -> CommonParameters.AI_ENGINE_FAILOVER_ORDER。
        引擎失败的降级过程逐条记 warning; 全部失败时 raise(附最后一个异常), 不吞错。
        """
        engines = engines or cls._default_failover_engines()
        last_error = None
        for engine in engines:
            try:
                answer = cls.call_agent(engine, prompt, question)
                return FailoverResult(engine, answer)
            except Exception as e:
                last_error = e
                logger.warning(f"引擎 {engine} 调用失败({e}), 降级到下一个引擎...")
        raise RuntimeError(f"所有引擎均调用失败: {engines}") from last_error

    @classmethod
    def call_agent_steps_failover(cls, step_prompts: list, question: str = "",
                                  engines: list = None) -> "FailoverResult":
        """多步推理降级(整链重试): 某引擎中途失败时, 换下一个引擎从第 1 步重新执行"""
        engines = engines or cls._default_failover_engines()
        last_error = None
        for engine in engines:
            try:
                answer = cls.call_agent_steps(engine, step_prompts, question)
                return FailoverResult(engine, answer)
            except Exception as e:
                last_error = e
                logger.warning(f"引擎 {engine} 多步推理失败({e}), 降级到下一个引擎...")
        raise RuntimeError(f"所有引擎均调用失败: {engines}") from last_error


# ---- 内置注册(key 统一小写; spark/bailian 系列已移入 depreciated/, 不再注册) ----
AIAgentFactory.register("huoshan", HuoshanAI)
AIAgentFactory.register("hunyuan", HunyuanAI)
AIAgentFactory.register("zhipu", ZhipuGLM4)
AIAgentFactory.register("mockedai", MockedAI)

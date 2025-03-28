from typing import Dict, Type

from dataIntegrator.LLMSuport.AiAgents import AIAgent, SparkAI, DeepSeek


class AIAgentFactory:
    _registry: Dict[str, Type[AIAgent]] = {
        "spark": SparkAI,
        "deepseek": DeepSeek
    }

    @classmethod
    def new_agent(cls, agent_type: str) -> AIAgent:
        """创建代理实例"""
        agent_class = cls._registry.get(agent_type)
        if not agent_class:
            raise ValueError(f"Unregistered agent type: {agent_type}")
        return agent_class()

    @classmethod
    def call_agent(cls, agent_type: str, prompt: str, question: str):
        """直接调用代理功能"""
        agent = cls.new_agent(agent_type)
        return agent.inquiry(prompt, question)
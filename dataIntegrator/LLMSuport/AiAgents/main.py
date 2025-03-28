from dataIntegrator.LLMSuport.AiAgents.AiAgentFactory import AIAgentFactory

if __name__ == "__main__":
    prompt = "What is the capital of France?"

    result = AIAgentFactory.call_agent("spark", prompt)
    print(result)

    result = AIAgentFactory.call_agent("deepseek", prompt)
    print(result)
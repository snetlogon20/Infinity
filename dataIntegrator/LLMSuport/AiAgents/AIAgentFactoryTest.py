from dataIntegrator.LLMSuport.AiAgents.AiAgentFactory import AIAgentFactory

if __name__ == "__main__":
    prompt = "What is the capital of France?"
    question = "What is the capital of France?"
    result = AIAgentFactory.call_agent("spark", prompt, question)
    print(result)

    # result = AIAgentFactory.call_agent("deepseek", prompt, question)
    # print(result)

    # result = AIAgentFactory.call_agent("mockedai", prompt, question)
    # print(result.generations[0][0].text)

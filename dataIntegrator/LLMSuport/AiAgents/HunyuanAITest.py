from dataIntegrator.LLMSuport.AiAgents.HunyuanAI import HunyuanAI

if __name__ == "__main__":
    prompt = "What is the capital of France?"
    question = "What is the capital of France?"

    # ===== 默认模型(DEFAULT_MODEL = hy3, TokenHub) =====
    result = HunyuanAI().inquiry(prompt, question)
    print(result)

    # ===== 指定模型: TokenHub 其他模型 =====
    result = HunyuanAI(model="hy4-preview").inquiry(prompt, question)
    print(result)

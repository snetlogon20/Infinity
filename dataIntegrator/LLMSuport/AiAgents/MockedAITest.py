from dataIntegrator.LLMSuport.AiAgents.MockedAI import MockedAI

if __name__ == "__main__":
    prompt = "What is the capital of France?"
    question = "What is the capital of France?"

    # ===== 单轮(离线, 契约统一后返回 str) =====
    result = MockedAI().inquiry(prompt, question)
    print(result)

    # ===== 多步推理(验证 AIAgent 基类模板方法) =====
    step_prompts = [
        "Step 1: list three fruits.",
        "Step 2: pick one from above.",
    ]
    result = MockedAI().multi_step_inquiry(step_prompts, question="demo")
    print(result)

from dataIntegrator.LLMSuport.AiAgents.HuoshanAI import HuoshanAI

if __name__ == "__main__":
    prompt = "What is the capital of France?"
    question = "What is the capital of France?"

    # ===== 默认接入点(DEFAULT_MODEL = ep-20261011112622-r6zfg) =====
    result = HuoshanAI().inquiry(prompt, question)
    print(result)

    # ===== 指定其他接入点/模型 =====
    # result = HuoshanAI(model="ep-xxxxxxxx").inquiry(prompt, question)
    # print(result)

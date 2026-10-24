from dataIntegrator.common.CommonParameters import CommonParameters
from dataIntegrator.LLMSuport.AiAgents.AIAgentFactory import AIAgentFactory

if __name__ == "__main__":
    prompt = "What is the capital of France?"
    question = "What is the capital of France?"

    # ===== 分支0: IF_ENABLE_MOCKED_AI 开关选引擎 =====
    # True  -> mocked AI(离线, 不访问真实接口)
    # False -> 真实 AI 接口(CommonParameters.Default_AI_Engine)
    if CommonParameters.IF_ENABLE_MOCKED_AI:
        agent_type = "mockedai"
    else:
        agent_type = CommonParameters.Default_AI_Engine
    print(f"IF_ENABLE_MOCKED_AI = {CommonParameters.IF_ENABLE_MOCKED_AI}, "
          f"using engine: {agent_type}")

    # ===== 分支1: 未注册类型(应抛 ValueError, 附可用列表) =====
    try:
        AIAgentFactory.call_agent("not_exist", prompt, question)
    except ValueError as e:
        print(f"[PASS] unregistered agent -> ValueError: {e}")

    # ===== 分支2: mockedai 单轮(离线, 契约统一后返回 str) =====
    result = AIAgentFactory.call_agent("mockedai", prompt, question)
    print(f"[PASS] mockedai returns str: {result!r}")

    # ===== 分支3: mockedai 多步推理(验证 AIAgent 基类模板方法) =====
    steps = ["Step 1: list three fruits.", "Step 2: pick one from above."]
    result = AIAgentFactory.call_agent_steps("mockedai", steps, question="demo")
    print(f"[PASS] mockedai multi-step returns str: {result!r}")

    # ===== 分支4: 大小写不敏感查找 =====
    agent = AIAgentFactory.new_agent("Hunyuan")
    print(f"[PASS] case-insensitive lookup: {type(agent).__name__}")

    # ===== 分支5: 工厂透传构造参数(模型选择) =====
    agent = AIAgentFactory.new_agent("huoshan", model="ep-20261011112622-r6zfg")
    print(f"[PASS] factory kwargs passthrough: "
          f"{type(agent).__name__}(model={agent.model!r})")
    # 真实调用示例(需对应平台的 API Key):
    # result = AIAgentFactory.new_agent("hunyuan", model="hy4-preview").inquiry(prompt, question)
    # print(result)

    # ===== 分支6: 按开关调用引擎，默认就是质谱 =====
    result = AIAgentFactory.call_agent(agent_type, prompt, question)
    print(f"[PASS] {agent_type} returns: {result}")

    # ===== 分支7: 混元默认模型(hy3, TokenHub) =====
    result = AIAgentFactory.call_agent("hunyuan", prompt, question)
    print(f"[PASS] hunyuan returns: {result}")

    # ===== 分支7.5: 火山方舟默认接入点(doubao-seed-2-1-lite) =====
    result = AIAgentFactory.call_agent("huoshan", prompt, question)
    print(f"[PASS] huoshan returns: {result}")

    # ===== 分支8: 降级链(引擎失败自动切下一个, 返回值带 engine) =====
    failover = AIAgentFactory.call_agent_failover(prompt, question)
    print(f"[PASS] failover engine={failover.engine}, answer: {failover.answer}")

    # ===== 分支9: 多步推理降级(整链重试, 换引擎从第 1 步重跑) =====
    failover = AIAgentFactory.call_agent_steps_failover(steps, question="demo")
    print(f"[PASS] failover-steps engine={failover.engine}, "
          f"answer: {failover.answer}")

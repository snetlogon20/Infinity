from dataIntegrator.LLMSuport.AiAgents.BailianAI import BailianAI

if __name__ == "__main__":
    # ===== 简单测试 =====
    # result = BailianAI.inquiry("What is the capital of France?", "")
    # print(result)

    # ===== 多步推理：拆分长 prompt，避免上下文超时 =====
    # 第 1 步：选券（只选，不算）
    step1_prompt = """
你是一个资深的银行债券交易员。
以下是 6 只可转债的量化数据（ts_code, name, ytm, duration, dv01, price）：

113037.SH, 紫银转债, ytm=-6.59, duration=1.07, dv01=0.012, price=109.73
113042.SH, 上银转债, ytm=-10.50, duration=1.12, dv01=0.013, price=116.21
127033.SZ, 中装转2, ytm=+13.68, duration=0.88, dv01=0.008, price=89.73
127025.SZ, 冀东转债, ytm=-2.98, duration=1.03, dv01=0.011, price=105.13
128129.SZ, 青农转债, ytm=-5.23, duration=1.06, dv01=0.011, price=107.63
128135.SZ, 洽洽转债, ytm=-10.84, duration=1.12, dv01=0.013, price=114.40

请从这 6 只中，选出最适合构建投资组合的 5 只债券，并逐只简要说明选择理由。
只需要输出选出的 5 只债券的 ts_code 和理由，不需要计算组合权重。
"""

    # 第 2 步：收益最大化
    step2_prompt = """
基于上一步选出的 5 只债券，请给出「收益最大化」组合。
要求：
1. 列出每只债券的配置权重（总和 100%）
2. 说明为什么这样分配
3. 用加权方法计算组合的预期 YTM、久期和 DV01
"""

    # 第 3 步：风险最小化 + 最佳平衡
    step3_prompt = """
基于上面已有的分析，请继续给出：
1. 「风险最小化」组合：以最小化组合久期和 DV01 为主要目标，给出 5 只债券的配置权重
2. 「最佳收益平衡」组合：在收益和风险之间取得最佳平衡，给出配置权重
3. 对比三个策略（收益最大化 / 风险最小化 / 最佳收益平衡）的优缺点，给出最终的专业推荐建议
"""

    step_prompts = [step1_prompt, step2_prompt, step3_prompt]
    result = BailianAI.multi_step_inquiry(step_prompts)
    print("=" * 60)
    print("最终结果：")
    print(result)


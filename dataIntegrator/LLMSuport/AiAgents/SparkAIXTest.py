from dataIntegrator.LLMSuport.AiAgents.SparkAIX import SparkX2

if __name__ == "__main__":
    # result = SparkX2.inquiry("What is the capital of France?","")
    # print(result)

    # ===== 多步推理：拆分长 prompt，避免上下文超时 =====
    # 第 1 步：选券（只选，不算）
    # step1_prompt = """
    # 你是一个资深的银行债券交易员。
    # 以下是 6 只可转债的量化数据（ts_code, name, ytm, duration, dv01, price）：
    #
    # 113037.SH, 紫银转债, ytm=-6.59, duration=1.07, dv01=0.012, price=109.73
    # 113042.SH, 上银转债, ytm=-10.50, duration=1.12, dv01=0.013, price=116.21
    # 127033.SZ, 中装转2, ytm=+13.68, duration=0.88, dv01=0.008, price=89.73
    # 127025.SZ, 冀东转债, ytm=-2.98, duration=1.03, dv01=0.011, price=105.13
    # 128129.SZ, 青农转债, ytm=-5.23, duration=1.06, dv01=0.011, price=107.63
    # 128135.SZ, 洽洽转债, ytm=-10.84, duration=1.12, dv01=0.013, price=114.40
    #
    # 请从这 6 只中，选出最适合构建投资组合的 5 只债券，并逐只简要说明选择理由。
    # 只需要输出选出的 5 只债券的 ts_code 和理由，不需要计算组合权重。
    # """
    #
    # # 第 2 步：收益最大化
    # step2_prompt = """
    # 基于上一步选出的 5 只债券，请给出「收益最大化」组合。
    # 要求：
    # 1. 列出每只债券的配置权重（总和 100%）
    # 2. 说明为什么这样分配
    # 3. 用加权方法计算组合的预期 YTM、久期和 DV01
    # """
    #
    # # 第 3 步：风险最小化 + 最佳平衡
    # step3_prompt = """
    # 基于上面已有的分析，请继续给出：
    # 1. 「风险最小化」组合：以最小化组合久期和 DV01 为主要目标，给出 5 只债券的配置权重
    # 2. 「最佳收益平衡」组合：在收益和风险之间取得最佳平衡，给出配置权重
    # 3. 对比三个策略（收益最大化 / 风险最小化 / 最佳收益平衡）的优缺点，给出最终的专业推荐建议
    # """
    #
    # step_prompts = [step1_prompt, step2_prompt, step3_prompt]
    # result = SparkX2.multi_step_inquiry(step_prompts)
    # print("=" * 60)
    # print("最终结果：")
    # print(result)


    step1_prompt = """
    你是一个资深的银行债券交易员。
    以下是 6 只可转债的量化数据（ts_code, name, ytm, duration, dv01, price）：

127033.SZ, 中装转2, ytm=+13.68, duration=0.88, dv01=0.0079, price=89.73, es_price_99=-0.00, current_yield=2.23, effective_convexity=1.55
113037.SH, 紫银转债, ytm=-6.63, duration=1.07, dv01=0.0118, price=109.77, es_price_99=0.21, current_yield=2.28, effective_convexity=2.29
128129.SZ, 青农转债, ytm=-5.28, duration=1.06, dv01=0.0114, price=107.69, es_price_99=0.38, current_yield=1.86, effective_convexity=2.23
127025.SZ, 冀东转债, ytm=-3.15, duration=1.03, dv01=0.0109, price=105.32, es_price_99=0.55, current_yield=1.90, effective_convexity=2.13
127018.SZ, 本钢转债, ytm=-11.51, duration=1.13, dv01=0.0134, price=118.66, es_price_99=1.42, current_yield=4.21, effective_convexity=2.55
128135.SZ, 洽洽转债, ytm=-10.86, duration=1.12, dv01=0.0128, price=114.42, es_price_99=1.38, current_yield=1.75, effective_convexity=2.52
123072.SZ, 乐歌转债, ytm=-15.00, duration=1.18, dv01=0.0144, price=122.35, es_price_99=1.30, current_yield=3.27, effective_convexity=2.77
113042.SH, 上银转债, ytm=-11.56, duration=1.13, dv01=0.0133, price=117.59, es_price_99=2.20, current_yield=3.40, effective_convexity=2.56
128127.SZ, 文科转债, ytm=-9.63, duration=1.11, dv01=0.0127, price=114.54, es_price_99=2.03, current_yield=3.06, effective_convexity=2.45
128138.SZ, 侨银转债, ytm=-20.71, duration=1.26, dv01=0.0164, price=129.91, es_price_99=2.11, current_yield=2.31, effective_convexity=3.18

    请从这 6 只中，选出最适合构建投资组合的 5 只债券，并逐只简要说明选择理由。
    只需要输出选出的 5 只债券的 ts_code 和理由，不需要计算组合权重。
    """

    result = SparkX2.inquiry(step1_prompt,"")
    print(result)
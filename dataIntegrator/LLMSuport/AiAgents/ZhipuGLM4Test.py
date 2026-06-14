import requests

from dataIntegrator import CommonLib
from dataIntegrator.LLMSuport.AiAgents import AIAgent
from dataIntegrator.common.MyTokens import MyTokens

logger = CommonLib.logger


from dataIntegrator.LLMSuport.AiAgents.ZhipuGLM4 import ZhipuGLM4

if __name__ == "__main__":
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

    result = ZhipuGLM4.inquiry(step1_prompt, "")
    print(result)
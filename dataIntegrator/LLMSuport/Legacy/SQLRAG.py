import json
from sparkai.llm.llm import ChatSparkLLM, ChunkPrintHandler
from sparkai.core.messages import ChatMessage

from dataIntegrator.LLMSuport.AiAgents.AiAgentFactory import AIAgentFactory
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

class SQLRAG():
    # 1. 配置星火大模型参数
    SPARKAI_URL = 'wss://spark-api.xf-yun.com/v3.5/chat'
    SPARKAI_DOMAIN = 'generalv3.5'

    ####lite 版本######
    # SPARKAI_URL = 'wss://spark-api.xf-yun.com/v1.1/chat'
    # SPARKAI_DOMAIN = 'lite'

    SPARK_APPID = "5f5c4f75"
    SPARK_API_KEY = "7a3136e4cac2160adb122031351fe0a4"
    SPARK_API_SECRET = "0672724ff7d71dc8fbbdcf98614aedb1"


    # 3. SQLRAG 知识库（可扩展为数据库存储）
    knowledge_base = {
        "table_schema": {
            "indexsysdb.us_stock_daily": {
                "columns": {
                    "ts_code": "股票代码（字符串类型）",
                    "trade_date": "交易日期（YYYY-MM-DD格式的字符串类型）",
                    "close_point": "收盘价（浮点类型）",
                    "open_point": "开盘价（浮点类型）",
                    "high_point": "最高价（浮点类型）",
                    "low_point": "最低价（浮点类型）",
                    "pre_close": "前收盘价（浮点类型）",
                    "change_point": "涨跌点（浮点类型）",
                    "pct_change": "涨跌幅（浮点类型）",
                    "vol": "成交量（浮点类型）",
                    "amount": "成交额（浮点类型）",
                    "vwap": "加权平均价（浮点类型）",
                    "turnover_ratio": "换手率（浮点类型）",
                    "total_mv": "总市值（浮点类型）",
                    "pe": "市盈率（浮点类型）",
                    "pb": "市净率（浮点类型）"
                }
            },
            "indexsysdb.df_tushare_us_stock_basic": {
                "columns": {
                    "ts_code": "股票代码，数据类型为字符串",
                    "name": "股票名称，数据类型为字符串，可为空",
                    "enname": "股票英文名称，或者全称，数据类型为字符串",
                    "classify": "股票分类，数据类型为字符串",
                    "list_date": "上市日期，数据类型为字符串",
                    "delist_date": "退市日期，数据类型为字符串，可为空"
                }
            }
        },
        "common_queries": [
            {
                "question": "花旗银行 2024年12月15日到 2024年12月16日的交易",
                "sql": """select * 
                        from indexsysdb.df_tushare_us_stock_daily
                        where ts_code = 'C' AND 
                    trade_date>= '20241215' and 
                    trade_date <='20241216' 
                    order by trade_date desc"""
            },
            {
                "question": "花旗银行 2024年10月15日到 2024年12月16日之间的平均收益率",
                "sql": """select avg(pct_change)
                        from indexsysdb.df_tushare_us_stock_daily
                        where ts_code = 'C' AND 
                    trade_date>= '20241015' and 
                    trade_date <='20241216' 
                    """
            },
            {
                "question": "花旗银行 这个股票的英文名称，股票分类和上市日期",
                "sql": """select enname, classify, list_date from indexsysdb.df_tushare_us_stock_basic
                        where ts_code = 'C'"""
            },
            {
                "question": "show me the trade date and top 3 pct change of Citi between 2022/12/15 to 2024/12/31, please append its english name,股票分类和上市日期 as well",
                "sql": """SELECT us.trade_date, us.pct_change, ub.enname, ub.classify, ub.list_date 
                        FROM indexsysdb.df_tushare_us_stock_daily AS us 
                        INNER JOIN 
                        (SELECT * FROM indexsysdb.df_tushare_us_stock_basic WHERE ts_code = 'C') AS ub ON us.ts_code = ub.ts_code 
                        WHERE us.ts_code = 'C' AND us.trade_date BETWEEN '20221215' AND '20241231' 
                        ORDER BY us.pct_change DESC LIMIT 3"""
            },
        ],
        "business_rules": [
            "花旗银行的 ts_code 是'C'",
            "花旗银行英文名是Citi",
            "close price is the same as close_point",
            "ts_code of JP morgan is 'JPM'",
            "收盘价就是 close price",
            "平均收益率就是 avg(pct_change)",
            "indexsysdb.df_tushare_us_stock_daily 和 indexsysdb.df_tushare_us_stock_basic 的join key 是ts_code",
            "图标就是plot, scatter chart, line chart",
        ]
    }


    # 4. 上下文检索函数
    def retrieve_context(self, question):
        context = []

        # 表结构信息
        context.append("### 表结构说明:")
        for table, schema in self.knowledge_base["table_schema"].items():
            context.append(f"{table} 表结构如下：")
            for col, desc in schema["columns"].items():
                context.append(f"- {col}: {desc}")

        # 匹配常见问题
        context.append("\n### 相关常见查询:")
        for query in self.knowledge_base["common_queries"]:
            context.append(f"- {query['question']}: {query['sql']}")

        # 业务规则匹配
        context.append("\n### 业务规则:")
        for rule in self.knowledge_base["business_rules"]:
            context.append(f"- {rule}")

        return "\n".join(context)


    # 5. 改进的 RAGSQL 处理函数
    def process_query(self, question):
        # 检索上下文
        context = self.retrieve_context(question)

        # 生成增强提示词
        prompt = f"""你是一个资深clickhouse SQL分析师，请根据以下信息生成clickhouse SQL查询：
    
        {context}
        
        **表结构**:
        indexsysdb.df_tushare_us_stock_daily(ts_code, trade_date, close_point, open_point, high_point, low_point, pre_close, change_point, pct_change, vol, amount, vwap, turnover_ratio, total_mv, pe, pb)
        
        **用户问题**:
        {question}
        
        请按以下要求返回结果：
        1. 使用与问题最相关的字段
        2. 使用clickhouse 语法
        3. 包含必要的聚合函数（如SUM、COUNT, AVG）
        4. 使用英文列别名, 按照clickhouse 语法，英文别名不可带有任何单引号或多引号。
        5. remember to use English column alias, and the English alias should not contain any single quotes or double quotes.
        7. the format of trade_date is 'yyyymmdd' rather than 'yyyy-mm-dd'
        6. 返回格式：
        {{
            "sql": "生成的SQL",
            "explanation_in_Mandarin": "解释查询目的和逻辑"
            "explanation_in_English": "Explain the targe and logic of the inquiry in English"
            "isPlotRequired": "是否要求产生图表，yes/no"
            "PlotX": "X轴字段名"
            "PlotY": "Y轴字段名"
        }}
        7. 如果有提到需要图表，请返回PlotX和PlotY字段，否则isPlotRequired就是no。
        """

        response = self.call_ai_agent(prompt)

        # 解析结果
        json_str = response.generations[0][0].text
        cleaned_json = json_str.replace("```json", "").replace("```", "").strip()
        print(cleaned_json)
        try:
            result = json.loads(cleaned_json)
            sql = result["sql"]
            explanation_in_Mandarin = result["explanation_in_Mandarin"]
            explanation_in_English = result["explanation_in_English"]
            isPlotRequired = result["isPlotRequired"]
            PlotX = result["PlotX"]
            PlotY = result["PlotY"]

            clickhouClickhouseService = ClickhouseService()
            data = clickhouClickhouseService.getDataFrameWithoutColumnsName(sql)
            #print(data)

            return {
                "sql": sql,
                "explanation_in_Mandarin": explanation_in_Mandarin,
                "explanation_in_English": explanation_in_English,
                "results": data,
                "isPlotRequired": isPlotRequired,
                "PlotX": PlotX,
                "PlotY": PlotY,
            }
        except Exception as e:
            return {"error": str(e), "sql_attempt": sql}

    def call_ai_agent(self, prompt):
        response = AIAgentFactory.call_agent("spark", prompt)
        print(response)
        return response

    def run_prompt_questions(self):

        while True:
            question = input("Please enter your question (type :quit to exit): ")
            if question == ":quit":
                break

            print(f"\n问题：{question}")
            self.run_single_question(question)

            print(rf"感谢询问有关/Thanks for your question on {question} 的问题。")

    def run_single_question(self, question):
        response = self.process_query(question)
        if "error" in response:
            print(f"错误：{response['error']}")
            if "sql_attempt" in response:
                print(f"尝试执行的SQL：{response['sql_attempt']}")
        else:
            print("生成的SQL/SQL generated：", response["sql"])
            print("解释说明：", response["explanation_in_Mandarin"])
            print("Explain：", response["explanation_in_English"])
            print("查询结果/Result：")
            print(response["results"])
            print("isPlotRequired:", response["isPlotRequired"])
            print("PlotX:", response["PlotX"])
            print("PlotY:", response["PlotY"])
        return response


# 6. 使用示例
if __name__ == "__main__":
    sqlrag = SQLRAG()
    sqlrag.run_prompt_questions()

import json
import sqlite3
from sparkai.llm.llm import ChatSparkLLM, ChunkPrintHandler
from sparkai.core.messages import ChatMessage
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

# 1. 配置星火大模型参数
SPARKAI_URL = 'wss://spark-api.xf-yun.com/v3.5/chat'
SPARK_APPID = "5f5c4f75"
SPARK_API_KEY = "7a3136e4cac2160adb122031351fe0a4"
SPARK_API_SECRET = "0672724ff7d71dc8fbbdcf98614aedb1"
SPARKAI_DOMAIN = 'generalv3.5'


# 3. SQLRAG 知识库（可扩展为数据库存储）
knowledge_base = {
    "table_schema": {
        "sales": {
            "columns": {
                "region": "销售区域（North: 北, South: 南, East: 东, West: 西）",
                "product": "产品类型（Laptop: 笔记本, Phone: 手机, Tablet: 平板）",
                "amount": "销售金额（美元）",
                "sale_date": "销售日期（YYYY-MM-DD格式）"
            }
        },
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
        }
    ],
    "business_rules": [
        "花旗银行的 ts_code 是'C'",
        "花旗银行英文名是Citi",
        "close price is the same as close_point",
        "平均收益率就是 avg(pct_change)"
    ]
}


# 4. 上下文检索函数
def retrieve_context(question):
    context = []

    # 表结构信息
    context.append("### 表结构说明:")
    for col, desc in knowledge_base["table_schema"]["indexsysdb.us_stock_daily"]["columns"].items():
        context.append(f"- {col}: {desc}")

    # 匹配常见问题
    context.append("\n### 相关常见查询:")
    for query in knowledge_base["common_queries"]:
        context.append(f"- {query['question']}: {query['sql']}")

    # 业务规则匹配
    context.append("\n### 业务规则:")
    for rule in knowledge_base["business_rules"]:
        context.append(f"- {rule}")

    return "\n".join(context)


# 5. 改进的 RAGSQL 处理函数
def process_query(question):
    # 检索上下文
    context = retrieve_context(question)

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
4. 使用英文列别名, 英文别名不可带有任何单引号或多引号
5. 返回格式：
{{
    "sql": "生成的SQL",
    "explanation": "解释查询目的和逻辑"
}}
"""

    # 调用大模型
    spark = ChatSparkLLM(
        spark_api_url=SPARKAI_URL,
        spark_app_id=SPARK_APPID,
        spark_api_key=SPARK_API_KEY,
        spark_api_secret=SPARK_API_SECRET,
        spark_llm_domain=SPARKAI_DOMAIN,
        streaming=False,
    )
    print("正在查询 LLM，请稍等")
    messages = [ChatMessage(role="user", content=prompt)]
    handler = ChunkPrintHandler()
    response = spark.generate([messages], callbacks=[handler])
    print("查询 LLM，已完成")

    # 解析结果
    json_str = response.generations[0][0].text
    cleaned_json = json_str.replace("```json", "").replace("```", "").strip()

    try:
        result = json.loads(cleaned_json)
        sql = result["sql"]
        explanation = result["explanation"]

        clickhouClickhouseService = ClickhouseService()
        data = clickhouClickhouseService.getDataFrameWithoutColumnsName(sql)
        #print(data)

        return {
            "sql": sql,
            "explanation": explanation,
            "results": data
        }
    except Exception as e:
        return {"error": str(e), "sql_attempt": sql}


def run_prepared_questions():
    global response
    questions = [
        "花旗银行 2024年12月15日到 2024年12月16日交易的平均收益率"
    ]
    for q in questions:
        print(f"\n问题：{q}")
        response = process_query(q)

        if "error" in response:
            print(f"错误：{response['error']}")
            if "sql_attempt" in response:
                print(f"尝试执行的SQL：{response['sql_attempt']}")
        else:
            print("生成的SQL：", response["sql"])
            print("解释说明：", response["explanation"])
            print("查询结果：")
            print(response["results"])


def run_prompt_questions():
    global response
    while True:
        question = input("Please enter your question (type :quit to exit): ")
        if question == ":quit":
            break

        print(f"\n问题：{question}")
        response = process_query(question)

        if "error" in response:
            print(f"错误：{response['error']}")
            if "sql_attempt" in response:
                print(f"尝试执行的SQL：{response['sql_attempt']}")
        else:
            print("生成的SQL：", response["sql"])
            print("解释说明：", response["explanation"])
            print("查询结果：")
            print(response["results"])

        print(rf"感谢询问有关 {question} 的问题。")


# 6. 使用示例
if __name__ == "__main__":
    #run_prepared_questions()


    #花旗银行 2024年12月15日到 2024年12月16日交易的平均收益率
    #花旗银行 2024年12月13日的开盘价
    #花旗银行 2024年12月13日的收盘价
    #give me the close price of Citi on 2024/12/13
    run_prompt_questions()

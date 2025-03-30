import json
import sqlite3
from sparkai.llm.llm import ChatSparkLLM, ChunkPrintHandler
from sparkai.core.messages import ChatMessage

# 1. 配置星火大模型参数
SPARKAI_URL = 'wss://spark-api.xf-yun.com/v3.5/chat'
SPARK_APPID = "5f5c4f75"
SPARK_API_KEY = "7a3136e4cac2160adb122031351fe0a4"
SPARK_API_SECRET = "0672724ff7d71dc8fbbdcf98614aedb1"
SPARKAI_DOMAIN = 'generalv3.5'

# 2. 创建内存数据库并插入示例数据
conn = sqlite3.connect(':memory:')
cursor = conn.cursor()

# 创建销售表
cursor.execute('''
    CREATE TABLE sales (
        id INTEGER PRIMARY KEY,
        region TEXT,
        product TEXT,
        amount REAL,
        sale_date DATE
    )
''')

# 插入测试数据
data = [
    ('North', 'Laptop', 1500.0, '2024-01-05'),
    ('South', 'Phone', 800.0, '2024-01-06'),
    ('East', 'Tablet', 600.0, '2024-01-07'),
    ('West', 'Laptop', 2000.0, '2024-01-08'),
    ('North', 'Phone', 900.0, '2024-01-09')
]
cursor.executemany('INSERT INTO sales (region, product, amount, sale_date) VALUES (?,?,?,?)', data)
conn.commit()

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
        }
    },
    "common_queries": [
        {
            "question": "各区域销售总额",
            "sql": "SELECT region, SUM(amount) FROM sales GROUP BY region"
        },
        {
            "question": "笔记本电脑销售记录",
            "sql": "SELECT * FROM sales WHERE product = 'Laptop'"
        }
    ],
    "business_rules": [
        "金额大于1000视为大额订单",
        "北区包含北京和天津的销售数据"
    ]
}


# 4. 上下文检索函数
def retrieve_context(question):
    context = []

    # 表结构信息
    context.append("### 表结构说明:")
    for col, desc in knowledge_base["table_schema"]["sales"]["columns"].items():
        context.append(f"- {col}: {desc}")

    # 匹配常见问题
    context.append("\n### 相关常见查询:")
    for query in knowledge_base["common_queries"]:
        if query["question"].lower() in question.lower():
            context.append(f"- {query['question']}: {query['sql']}")

    # 业务规则匹配
    context.append("\n### 业务规则:")
    for rule in knowledge_base["business_rules"]:
        if any(keyword in question for keyword in ["金额", "大额"] if "金额" in rule):
            context.append(f"- {rule}")

    return "\n".join(context)


# 5. 改进的 RAGSQL 处理函数
def process_query(question):
    # 检索上下文
    context = retrieve_context(question)

    # 生成增强提示词
    prompt = f"""你是一个资深SQL分析师，请根据以下信息生成SQL查询：

{context}

**表结构**:
sales(id, region, product, amount, sale_date)

**用户问题**:
{question}

请按以下要求返回结果：
1. 使用与问题最相关的字段
2. 包含必要的聚合函数（如SUM、COUNT）
3. 使用中文列别名
4. 返回格式：
{{
    "sql": "生成的SQL",
    "explanation": "解释查询目的和逻辑"
}}"""

    # 调用大模型
    spark = ChatSparkLLM(
        spark_api_url=SPARKAI_URL,
        spark_app_id=SPARK_APPID,
        spark_api_key=SPARK_API_KEY,
        spark_api_secret=SPARK_API_SECRET,
        spark_llm_domain=SPARKAI_DOMAIN,
        streaming=False,
    )
    messages = [ChatMessage(role="user", content=prompt)]
    handler = ChunkPrintHandler()
    response = spark.generate([messages], callbacks=[handler])

    # 解析结果
    json_str = response.generations[0][0].text
    cleaned_json = json_str.replace("```json", "").replace("```", "").strip()

    try:
        result = json.loads(cleaned_json)
        sql = result["sql"]
        explanation = result["explanation"]

        # 执行验证
        cursor.execute(f"EXPLAIN QUERY PLAN {sql}")
        query_plan = cursor.fetchall()
        if not any("SCAN sales" in str(plan) for plan in query_plan):
            raise ValueError("查询未正确引用销售表")

        # 执行查询
        cursor.execute(sql)
        return {
            "sql": sql,
            "explanation": explanation,
            "results": cursor.fetchall(),
            "plan": query_plan
        }
    except Exception as e:
        return {"error": str(e), "sql_attempt": sql}


# 6. 使用示例
if __name__ == "__main__":
    questions = [
        "显示北部地区笔记本电脑的销售总额",
        "找出金额超过1000的大额订单",
        "按产品类型统计各区域的销量"
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
            for row in response["results"]:
                print(row)

    conn.close()
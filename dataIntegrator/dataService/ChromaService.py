from typing import List, Dict, Optional, Union
import chromadb
from chromadb import Client
from chromadb.api.types import (
    Embeddable,
    EmbeddingFunction,
    QueryResult,
    Where,
    WhereDocument,
)
import numpy as np
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
import openai

# 自定义嵌入模型（例如 OpenAI）
class OpenAIEmbedder(EmbeddingFunction):
    def __call__(self, texts: list[str]) -> list[float]:
        return openai.embeddings.create(input=texts, model="text-embedding-3-small").data[0].embedding

class ChromaService:
    """封装 Chroma 向量数据库操作的 Service 类"""

    def __init__(
            self,
            host: str = None,
            port: int = 8000,
            persist_directory: str = "D:\\AI_projects\\sql_RAG\\chroma\\financial_knowledge",
            reset: bool = False,
            embedding_function: Optional[EmbeddingFunction] = OpenAIEmbedder(),
    ):

        self.client = chromadb.PersistentClient(
            path=persist_directory # 存储路径
             )

        if reset:
            self.client.reset()

        self.embedding_function = embedding_function

    # ----------------- 集合管理 -----------------
    def create_collection(
            self,
            name: str,
            metadata: Optional[Dict] = None,
            embedding_function: Optional[EmbeddingFunction] = None
    ) -> chromadb.Collection:
        """
        创建新集合

        :param name: 集合名称
        :param metadata: 集合元数据（例如索引配置）
        :param embedding_function: 自定义嵌入函数（覆盖全局）
        """
        return self.client.create_collection(
            name=name,
            metadata=metadata,
            embedding_function=embedding_function or self.embedding_function,
        )

    def get_collection(self, name: str) -> chromadb.Collection:
        """获取已存在的集合"""
        return self.client.get_collection(name)

    def delete_collection(self, name: str) -> None:
        """删除集合"""
        return self.client.delete_collection(name)

    def list_collections(self) -> List[Dict]:
        """列出所有集合"""
        return [{"name": col.name, "metadata": col.metadata} for col in self.client.list_collections()]

    # ----------------- 数据操作 -----------------
    def add_documents(
            self,
            collection_name: str,
            documents: List[str],
            metadatas: Optional[List[Dict]] = None,
            ids: Optional[List[str]] = None,
            embeddings: Optional[List[List[float]]] = None,
    ) -> None:
        """
        添加文档到集合

        :param collection_name: 目标集合名称
        :param documents: 文本列表
        :param metadatas: 元数据列表（与documents一一对应）
        :param ids: 自定义ID列表（默认自动生成）
        :param embeddings: 自定义向量（如果未提供则自动生成）
        """
        collection = self.get_collection(collection_name)
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings,
        )

    def query(
            self,
            collection_name: str,
            query_texts: Optional[List[str]] = None,
            query_embeddings: Optional[List[List[float]]] = None,
            n_results: int = 10,
            where: Optional[Where] = None,
            where_document: Optional[WhereDocument] = None,
    ) -> QueryResult:
        """
        执行相似性查询

        :param collection_name: 目标集合名称
        :param query_texts: 查询文本列表（与query_embeddings二选一）
        :param query_embeddings: 查询向量列表
        :param n_results: 返回结果数量
        :param where: 元数据过滤条件
        :param where_document: 文档内容过滤条件
        """
        collection = self.get_collection(collection_name)
        return collection.query(
            query_texts=query_texts,
            query_embeddings=query_embeddings,
            n_results=n_results,
            where=where,
            where_document=where_document,
        )

    def update_document(
            self,
            collection_name: str,
            document_id: str,
            new_document: Optional[str] = None,
            new_metadata: Optional[Dict] = None,
            new_embedding: Optional[List[float]] = None,
    ) -> None:
        """更新文档内容/元数据/向量"""
        collection = self.get_collection(collection_name)
        collection.update(
            ids=document_id,
            documents=new_document,
            metadatas=new_metadata,
            embeddings=new_embedding,
        )

    def delete_documents(self, collection_name: str, document_ids: List[str]) -> None:
        """删除指定ID的文档"""
        collection = self.get_collection(collection_name)
        collection.delete(ids=document_ids)

    @staticmethod
    def default_embedding_function(texts: List[str]) -> List[List[float]]:
        """默认嵌入函数（需替换为实际模型）"""
        return np.random.rand(len(texts), 768).tolist()

    @staticmethod
    def print_query_result(result: QueryResult) -> None:
        """格式化打印查询结果"""
        for i, (doc_id, distance, document, metadata) in enumerate(
                zip(result["ids"][0], result["distances"][0], result["documents"][0], result["metadatas"][0])
        ):
            print(f"结果 #{i + 1}:")
            print(f"  ID: {doc_id}")
            print(f"  距离: {distance:.4f}")
            print(f"  内容: {document}")
            print(f"  元数据: {metadata}\n")

    def add_financial_data(self, financial_data: dict, type: str, collection_name: str) -> None:
        """
            将原始知识库转换为 (documents, metadatas, ids) 三元组
            """
        documents = []
        metadatas = []
        ids = []

        if type == "table_schema":
            # 处理表结构信息
            for table_name, table_info in financial_data.items():
                doc = f"表 {table_name} 结构:\n" + "\n".join(
                    [f"- {col}: {desc}" for col, desc in table_info["columns"].items()]
                )
                documents.append(doc)
                metadatas.append({"type": type})
                ids.append(f"schema_{table_name}")
        elif type == "common_queries":
            # 处理常见SQL查询
            for idx, query in enumerate(financial_data["common_queries"]):
                doc = f"问题: {query['question']}\nSQL示例:\n{query['sql']}"
                documents.append(doc)
                metadatas.append({"type": type})
                ids.append(f"query_{idx}")
        elif type == "business_rules":
            # 处理业务规则
            for idx, rule in enumerate(financial_data["business_rules"]):
                documents.append(rule)
                metadatas.append({"type": type})
                ids.append(f"rule_{idx}")



        self.add_documents(
            collection_name= collection_name,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )



    def add_knowledge_data(self,collection_name:str):

        table_schema= {
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
                    "enname": "股票英文名称，数据类型为字符串",
                    "classify": "股票分类，数据类型为字符串",
                    "list_date": "上市日期，数据类型为字符串",
                    "delist_date": "退市日期，数据类型为字符串，可为空"
                }
            }
        }

        common_queries= {
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
            }
        ] }

        business_rules = {"business_rules":{
            "花旗银行的 ts_code 是'C'",
            "花旗银行英文名是Citi",
            "close price is the same as close_point",
            "ts_code of JP morgan is 'JPM'",
            "收盘价就是 close price",
            "平均收益率就是 avg(pct_change)",
            "indexsysdb.df_tushare_us_stock_daily 和 indexsysdb.df_tushare_us_stock_basic 的join key 是ts_code",
            "图标就是plot, scatter chart, line chart",
        }}



        # # 转换数据并存入
        self.add_financial_data(table_schema,"table_schema",collection_name)
        self.add_financial_data(common_queries,"common_queries",collection_name)
        self.add_financial_data(business_rules,"business_rules",collection_name)




if __name__ == '__main__':
    chroma_service = ChromaService()
    collection_name = "financial_table_schema"
    # # 示例查询
    result = chroma_service.query(
        collection_name=collection_name,
        query_texts=["花旗银行 2024年6月15日到 2024年12月16日交易的平均收益率"],
        n_results=2,
        where={"type": {"$in": ["table_schema"]}}
    )
    #
    ChromaService.print_query_result(result)
    # chroma_service.add_knowledge_data(collection_name)

    # chroma_service.delete_collection(collection_name)
    # 创建专用集合
    # chroma_service.create_collection(
    #     name=collection_name
    # )

from typing import Dict, Tuple
import uuid
from datetime import datetime
from dataIntegrator.LLMSuport.AiAgents.AiAgentFactory import AIAgentFactory
import json

from dataIntegrator.LLMSuport.ChromaService.ChromaLLMService import ChromaLLMService


class ChromaDialogAgent(ChromaLLMService):
    def __init__(self, model_path):
        super().__init__(model_path)

    def process_query(self, user_id: str, query: str, collection, n_results=3) -> Tuple[str, Dict]:
        """处理完整对话流程"""
        try:
            # 查询向量数据库
            chromadb_results, doc_id, closest_doc = self.inquiry_collection(user_id, query, collection, n_results)
            self.inquiry_similarity(chromadb_results)
            # 生成自然语言响应
            ai_response_dict = self.generate_response(query, chromadb_results)
            # 保存至向量数据库
            self.save_query_to_collection(collection, user_id, query, chromadb_results, ai_response_dict)

            return query, chromadb_results, ai_response_dict

        except Exception as e:
            error_msg = f"查询处理失败：{str(e)}"
            print(error_msg)
            return query, {}, {"response": error_msg}  # 返回占位值

    def generate_response(self, query: str, chromadb_results: Dict) -> str:
        """生成自然语言回答（基础版）"""
        if not chromadb_results or not chromadb_results['documents']:
            return "未找到相关文档信息"

        # 构建LLM提示
        context = "".join(
            f"{idx + 1}. {doc}\n"  # 添加序号
            for idx, doc in enumerate(chromadb_results['documents'][0][:3])  # 取前3个相关文档
        )
        prompt = f"""基于以下历史上下文用中文回答问题：
        {context}

        现在，请回答问题：{query}
        请用自然语言组织答案，并标注信息来源。"""

        print("根据ChromaDB返回，组装上下文:\n", prompt)


        result = AIAgentFactory.call_agent("spark", prompt, query)
        print("SparkAi文字返回：",result.generations[0][0].text)

        ai_response_dict = {
            "query": query,
            "response": result.generations[0][0].text
        }

        return ai_response_dict

    def save_query_to_collection(self,collection,  user_id, query: str, results: Dict, ai_response: str):
        """将查询结果保存到集合中"""
        try:
            doc_id = str(uuid.uuid4())

            # 构建元数据
            metadata = {
                "user_id": user_id,
                "source": "user_query",
                "query_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "query_text": query,
                "results": json.dumps(results),
                "ai_response": ai_response["response"]
            }

            document = f"历史查询：{query}"

            # 添加到集合中
            collection.add(
                documents=[document],
                metadatas=[metadata],
                ids=[doc_id]
            )
            print(f"查询结果已保存到集合中，文档 ID: {doc_id}")
        except Exception as e:
            print(f"保存查询结果时出错：{str(e)}")
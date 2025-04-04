import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import pandas as pd

class croma_service:
    def __init__(self, model_path):
        self.client = None
        self.model_path = model_path

    def set_persistent_folder(self, db_persistent_path):
        """设置持久化文件夹路径"""
        self.client = chromadb.PersistentClient(path=db_persistent_path)

    def download_model(self, model_path=None):
        """下载模型"""
        if model_path is None:
            self.model_path = r"D:\workspace_python\infinity_data\model\all-MiniLM-L6-v2"
        else:
            self.model_path = model_path

    def load_model(self, model_path=None):
        """加载模型"""
        if model_path is None:
            model_path = self.model_path
        return SentenceTransformerEmbeddingFunction(model_name=model_path)

    def load_meta_excel(self, meta_excel_path):
        """从 Excel 文件加载元数据"""
        df = pd.read_excel(meta_excel_path)
        meta_date_dict = {
            "id": df["id"].tolist(),
            #"document_name": df["document_name"].tolist(),
            "document": df["document"].tolist(),
            "metadata": df["metadata"].apply(lambda x: eval(x) if isinstance(x, str) else x).tolist()
        }
        return meta_date_dict

    def create_collection(self, model_path, collection_name):
        """创建或获取集合"""
        embedding_function = self.load_model(model_path)
        return self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_function
        )

    def add_collection(self, collection, meta_date_dict):
        """向集合中添加文档"""
        collection.add(
            documents=meta_date_dict["document"],
            metadatas=meta_date_dict["metadata"],
            ids=meta_date_dict["id"]
        )
        return collection

    def create_and_add_collection(self, model_path, collection_name, meta_date_dict):


        collection = self.create_collection(model_path, collection_name)
        collection = self.add_collection(collection, meta_date_dict)
        return collection

    def inquiry_collection(self, query_text, collection, n_results=3):
        """查询集合中最相似的文档"""
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where={
                "$or": [
                    {"source": "官方文档"},
                    {"source": "技术博客"}
                ]
            }
        )
        closest_doc = results['documents'][0][0]
        doc_id = results['ids'][0][0]
        print(f"查询文本：'{query_text}'")
        print(f"最匹配的文档(ID {doc_id})：{closest_doc}")
        return results, doc_id, closest_doc

    def inquiry_similarity(self, results):
        """分析查询结果的相似度"""
        distances = results['distances'][0]
        documents = results['documents'][0]
        for dist, doc in zip(distances, documents):
            print(f"[相似度 {dist:.3f}] {doc}")


    # 下载模型
    def download_model(self, results):
        model = SentenceTransformer("all-MiniLM-L6-v2")
        save_path = r"D:\workspace_python\infinity_data\model\all-MiniLM-L6-v2"
        model.save(save_path)

if __name__ == '__main__':
    model_path = r"D:\workspace_python\infinity_data\model\all-MiniLM-L6-v2"
    db_persistent_path = r"D:\workspace_python\infinity_data\chormadb\persistent.db"
    meta_excel_path = r"D:\workspace_python\infinity_data\inbound\chromadb_meta_collections.xlsx"

    croma_service = croma_service(model_path)
    croma_service.set_persistent_folder(db_persistent_path)
    #service.download_model()

    meta_date_dict = croma_service.load_meta_excel(meta_excel_path)
    collection = croma_service.create_and_add_collection(
        model_path=model_path,
        collection_name="my_docs",
        meta_date_dict=meta_date_dict
    )

    results, doc_id, closest_doc = croma_service.inquiry_collection("ChromaDB是否支持语义向量搜索？", collection)

    croma_service.inquiry_similarity(results)
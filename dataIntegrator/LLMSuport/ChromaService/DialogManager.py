from dataIntegrator.LLMSuport.ChromaService.ChromaDialogAgent import ChromaDialogAgent
from dataIntegrator.utility.FileUtility import FileUtility
from datetime import datetime

def test_run_query_in_batch():
    global query
    test_queries = [
        "ChromaDB是什么？它支持哪些类型的搜索？ ",
        "它的安装复杂吗？如何进行语义向量检索？",
        "提供我相关的python代码"
    ]
    for query in test_queries:
        print(f"\n用户问：{query}")
        query, chromadb_results, ai_response_dict = agent.process_query(user_id, query, collection, n_results=3)
        print(f"系统回答：{ai_response_dict["response"]}")
        print("-" * 60)


def test_run_query_in_coversation():
    '''
    使用以下提示：
        Oracle和mysql是什么区别？
        怎样使用java连接Oracle
        给我代码
        怎样使用python连接Oracle
        给我golang的相关代码
        Oracle pl-SQL 怎么写？
    '''
    while True:  # 无限循环
        query = input("\n请输入您的问题（输入 ':exit' 退出）：")  # 获取用户输入
        if query.lower() == ":exit":  # 如果用户输入 'exit'，退出循环
            print("对话结束，感谢使用！")
            break

        # 处理用户问题
        query, chromadb_results, ai_response_dict = agent.process_query(user_id, query, collection, n_results=3)
        print(f"系统回答：{ai_response_dict['response']}")
        print("-" * 60)


if __name__ == '__main__':
    model_path = FileUtility.get_full_outbound_path("model","all-MiniLM-L6-v2")
    db_persistent_path = FileUtility.get_full_outbound_path("chormadb","persistent.db")
    meta_excel_path = FileUtility.get_full_outbound_path("inbound","chromadb_meta_collections.xlsx")
    user_id = "snetlogon20"
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session_id = f"snetlogon20_{current_time}"  # 每次启动使用新的collection，避免以前消息的干扰

    agent = ChromaDialogAgent(model_path)  # 使用继承后的对话代理类
    agent.set_persistent_folder(db_persistent_path)
    #service.download_model()

    collection = agent.create_collection(model_path=model_path, collection_name=f"{user_id}_{session_id}_ChromaDB")
    print("集合中的文档数量：", collection.count())

    # 批量发送查询
    #test_run_query_in_batch()

    # 人机交互
    test_run_query_in_coversation()
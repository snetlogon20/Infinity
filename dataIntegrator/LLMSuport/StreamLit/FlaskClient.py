import requests
import pandas as pd
import json
import matplotlib.pyplot as plt

class FlaskClient1:
    def __init__(self, base_url='http://127.0.0.1:5000'):
        self.base_url = base_url

    def callAtlas(self, params, url):
        print("----------Send inqiury to Atlas----------")

        response = requests.get(url, params=params)
        if response.status_code == 200:
            print("Response from /request_for_rag_inquiry:")
            print(response.json())
        else:
            print(f"Error: {response.status_code} - {response.text}")

        response_json = response.json()

        sql = response_json["sql"]
        explanation_in_Mandarin = response_json["explanation_in_Mandarin"]
        explanation_in_English = response_json["explanation_in_English"]
        data_dict = json.loads(response_json["results"])
        data_frame = pd.DataFrame(data_dict)
        isPlotRequired = response_json["isPlotRequired"]
        PlotX = response_json["PlotX"]
        PlotY = response_json["PlotY"]

        print("----------Process of the message from Atlas is done----------")

        return data_frame, explanation_in_English, explanation_in_Mandarin, sql, isPlotRequired, PlotX, PlotY


    def request_for_RAG_SQL_inquiry_stock_summary(self, question):
        print("----------I am started  ****----------")

        if question is None or len(question) == 0:
            print("question is null")
            return

        url = f"{self.base_url}/RAG_SQL_inquiry_stock_summary"
        params = {'question': question, 'agent_type': 'spark'}

        print("----------Send inqiury to Atlas----------")
        response = requests.get(url, params=params)
        if response.status_code == 200:
            print("Response from /RAG_SQL_inquiry_stock_summary:")
            print(response.json())
        else:
            print(f"Error: {response.status_code} - {response.text}")

        response_json = response.json()

        sql = response_json["sql"]
        explanation_in_Mandarin = response_json["explanation_in_Mandarin"]
        explanation_in_English = response_json["explanation_in_English"]
        data_dict = json.loads(response_json["results"])
        data_frame = pd.DataFrame(data_dict)
        print("----------Process of the message from Atlas is done----------")

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(data_frame['trade_date'], data_frame['close_point'], marker='o')
        # 设置图表标题和坐标轴标签
        ax.set_title('Close Point Over Trade Date')
        ax.set_xlabel('Trade Date')
        plt.xticks(rotation=45)
        ax.set_ylabel('Close Point')
        ax.grid(True)
        ax.set_xticks(data_frame['trade_date'])

        print("====")

    def request_for_RAG_SQL_inquiry_portfolio_volatility(self, question):
        print("----------I am started----------")

        if question is None or len(question) == 0:
            print("question is null")
            return

        url = f"{self.base_url}/RAG_SQL_inquiry_portfolio_volatility"
        params = {'question': question, 'agent_type': 'spark'}

        print("----------Send inqiury to Atlas----------")

        response = requests.get(url, params=params)
        if response.status_code == 200:
            print("Response from /request_for_rag_inquiry:")
            print(response.json())
        else:
            print(f"Error: {response.status_code} - {response.text}")

        response_json = response.json()

        sql = response_json["sql"]
        explanation_in_Mandarin = response_json["explanation_in_Mandarin"]
        explanation_in_English = response_json["explanation_in_English"]
        data_dict = json.loads(response_json["results"])

        dataframes = {}
        for key, json_str in data_dict.items():
            dataframes[key] = pd.read_json(json_str)


        print("----------Process of the message from Atlas is done----------")

        return sql, explanation_in_Mandarin, explanation_in_English, dataframes

if __name__ == '__main__':
    print("----------------FlaskClient1")
    client = FlaskClient1()

    # request_for_RAG_SQL_inquiry_stock_summary
    # data_frame = client.request_for_RAG_SQL_inquiry_stock_summary('show me all the stock information of Citi change between 2024/12/20to 2024/12/31')
    # print(data_frame)

    #request_for_RAG_SQL_inquiry_stock_summary
    sql, explanation_in_Mandarin, explanation_in_English, dataframes = client.request_for_RAG_SQL_inquiry_portfolio_volatility(question = """
    帮我找出花旗， 美国银行，JP 摩根， 苹果，英伟达， 因特尔的股票代码。股票数据需要2023-01-01到2023-12-31之间的数据。不需要冗余数据，返回单一股票代码即可。
    """)
    for key, df in dataframes.items():
        plt.scatter(df['portfolio_volatility'], df['portfolio_mean'], label=key, s=5)
        # 设置图表标题和标签
    plt.xlabel('Portfolio Volatility')
    plt.ylabel('Portfolio Mean')
    plt.title('Information Ratio of Combined Portfolio')
    plt.legend()
    plt.show()
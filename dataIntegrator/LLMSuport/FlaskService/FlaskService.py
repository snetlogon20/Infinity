from flask import Flask, request, jsonify

from dataIntegrator.LLMSuport.FlaskService.RAG_SQL_inquiry_portfolio_volatility_service import \
    RAG_SQL_inquiry_portfolio_volatility_service
from dataIntegrator.LLMSuport.FlaskService.RAG_SQL_inquiry_stock_summary_service import \
    RAG_SQL_inquiry_stock_summary_service
from dataIntegrator.LLMSuport.RAGFactory.RAGFactory import RAGFactory

class FlaskService:
    def __init__(self):
        self.app = Flask(__name__)
        self.register_routes()

        self.response_dict = {
            "return_code": "999999",
            "return_message": "Unknow Error",
        }

    def register_routes(self):
        self.app.add_url_rule('/RAG_SQL_inquiry_stock_summary', view_func=self.RAG_SQL_inquiry_stock_summary, methods=['GET'])
        self.app.add_url_rule('/RAG_SQL_inquiry_portfolio_volatility', view_func=self.RAG_SQL_inquiry_portfolio_volatility, methods=['GET'])

    def RAG_SQL_inquiry_stock_summary(self):

        response_dict = self.response_dict

        try:
            question = request.args.get('question', '')
            agent_type = request.args.get('agent_type', '')

            rage_sql_inquiry_stock_summary_service = RAG_SQL_inquiry_stock_summary_service()
            service_response_dict = rage_sql_inquiry_stock_summary_service.RAG_SQL_inquiry_stock_summary_service_fetch(agent_type, question)

            response_dict.update({
                "return_code": "000000",
                "return_message": "Success",
                "sql": service_response_dict["sql"],
                "explanation_in_Mandarin": service_response_dict["explanation_in_Mandarin"],
                "explanation_in_English": service_response_dict["explanation_in_English"],
                "results": service_response_dict["results"].to_json(),
                "isPlotRequired": service_response_dict["isPlotRequired"],
                "PlotX": service_response_dict["PlotX"],
                "PlotY": service_response_dict["PlotY"]
            })

        except Exception as e:
            response_dict.update({
                "return_code": "100001",
                "return_message": rf"Error when fetch data. <{str(e)}>",
            })

        response_json = jsonify(response_dict)
        return response_json

    def RAG_SQL_inquiry_portfolio_volatility(self):
        #question = """帮我找出花旗， 美国银行，JP 摩根， 苹果，英伟达， 因特尔的股票代码。股票数据需要2023-01-01到2023-12-31之间的数据。不需要冗余数据，返回单一股票代码即可。"""
        response_dict = self.response_dict

        try:
            question = request.args.get('question', '')
            agent_type = request.args.get('agent_type', '')

            rage_sql_inquiry_portfolio_volatility_service = RAG_SQL_inquiry_portfolio_volatility_service()
            service_response_dict, service_results_json_dict_json = rage_sql_inquiry_portfolio_volatility_service.RAG_SQL_inquiry_portfolio_volatility_fetch(agent_type,
                                                                                                    question,
                                                                                                    response_dict)
            response_dict.update({
                "return_code": "000000",
                "return_message": "Success",
                "sql": "--",
                "explanation_in_Mandarin": "--",
                "explanation_in_English": "--",
                "results": service_results_json_dict_json,
                "isPlotRequired": "--",
                "PlotX": "--",
                "PlotY": "--"
            })

        except Exception as e:
            response_dict.update({
                "return_code": "100001",
                "return_message": rf"Error when fetch data. <{str(e)}>",
            })

        response_json = jsonify(response_dict)
        return response_json



    def run(self):
        self.app.run(debug=True)


if __name__ == '__main__':
    service = FlaskService()
    service.run()
from flask import Flask, request
import json
from dataIntegrator.LLMSuport.Legacy.PortfolioVolatilityService import PortfolioVolatilityService
from dataIntegrator.LLMSuport.Legacy.SQLRAG import SQLRAG


class FlaskService:
    def __init__(self):
        self.app = Flask(__name__)
        self.register_routes()

    def register_routes(self):
        self.app.add_url_rule('/rag_inquiry', view_func=self.rag_inquiry, methods=['GET'])
        self.app.add_url_rule('/financial_analysis_inquiry', view_func=self.financial_analysis_inquiry, methods=['GET'])

    def rag_inquiry(self):
        question = request.args.get('question', '')

        sqlrag = SQLRAG()
        response = sqlrag.run_single_question(question)
        print(response)
        results_json = response["results"].to_json()

        response_json = {
            "sql": response["sql"],
            "explanation_in_Mandarin": response["explanation_in_Mandarin"],
            "explanation_in_English": response["explanation_in_English"],
            "results": results_json,
            "isPlotRequired": response["isPlotRequired"],
            "PlotX": response["PlotX"],
            "PlotY": response["PlotY"]
        }
        return response_json

    def financial_analysis_inquiry(self):
        question = request.args.get('question', '')

        portfolioVolatilityService = PortfolioVolatilityService()
        result_df_list = portfolioVolatilityService.test_portfolio_volatility(question)

        results_json_dict = {}
        for key, df in result_df_list.items():
            results_json_dict[key] = df.to_json()

        print(results_json_dict)
        results_json_dict_json = json.dumps(results_json_dict)

        response_json = {
            "sql": "--",
            "explanation_in_Mandarin": "--",
            "explanation_in_English": "--",
            "results": results_json_dict_json,
            "isPlotRequired": "--",
            "PlotX": "--",
            "PlotY": "--"
        }
        return response_json


    def run(self):
        self.app.run(debug=True)


if __name__ == '__main__':
    service = FlaskService()
    service.run()
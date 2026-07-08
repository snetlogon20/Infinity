import os

from flask import Flask, request, jsonify
import logging

from dataIntegrator.LLMSuport.RAGFactory.RAGFactory import RAGFactory
from dataIntegrator.common.CommonParameters import CommonParameters
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# Temporary storage for demonstration purposes
data_store = {}

@app.route('/fetch_data_with_ai', methods=['POST'])
def fetch_data_with_ai():
    """
    Import data controller
    Expected params in param_dict:
    - source: Data source type (e.g., 'file', 'database')
    - path: Path/connection string for the data source
    """
    try:
        param_dict = request.get_json().get("params")
        if not param_dict:
            return jsonify({"error": "No parameters provided"}), 400

        app.logger.info(f"Importing data with params: {param_dict}")

        # Parameter validation
        required_params = ['question']
        if not all(key in param_dict for key in required_params):
            return jsonify({"error": "Missing required parameters"}), 400

        try:
            knowledge_base_file_path = os.path.join(CommonParameters.rag_configuration_path, "RAG_SQL_inquiry_stock_summary_knowledge_base.json")
            prompt_file_path = os.path.join(CommonParameters.rag_configuration_path, "RAG_SQL_inquiry_stock_summary_prompts.txt")

            response_dict = (
                RAGFactory.run_rag_inquiry(
                    "RAG_SQL_inquiry_stock_summary",
                    CommonParameters.Default_AI_Engine, param_dict["question"],
                    knowledge_base_file_path, prompt_file_path))

            sql = response_dict["sql"]

            clickhouseService = ClickhouseService()
            resultset_df = clickhouseService.getDataFrameWithoutColumnsName(sql)
        except Exception as e:
            return jsonify({"error": rf"Error while inquiry SQL:\n {sql}"}), 400

        # package response
        response_dict = {
            "return_code": "000000",
            "message": "Data imported successfully",
            "resultset_dict": resultset_df.to_dict(orient='records'),
        }

        return jsonify(response_dict), 200

    except Exception as e:
        app.logger.error(f"Import error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)  # 关闭自动重启
    app.run(host='0.0.0.0', port=5000, debug=True)
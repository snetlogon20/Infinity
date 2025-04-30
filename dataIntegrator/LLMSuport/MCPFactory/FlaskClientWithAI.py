import os
import subprocess
import requests
import json
import logging
import pandas as pd
import matplotlib.pyplot as plt

#matplotlib.use('TkAgg')  # 使用 TkAgg 后端

class FlaskClientWithAI:
    def __init__(self):
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)

    def _make_request(self, param_dict):

        print(f"_make_request started - param_dict: {param_dict}")

        """Generic request handler"""
        url = param_dict["params"]["url"]
        try:
            response = self.session.post(
                url,
                json=param_dict,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            return True, response.json()
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error: {str(e)}")
            return False, response.json() if response else {'error': str(e)}
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            self.logger.error(f"Connection error: {str(e)}")
            return False, {'error': 'Connection failed'}
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {str(e)}")
            return False, {'error': str(e)}
        except json.JSONDecodeError:
            self.logger.error("Invalid JSON response")
            return False, {'error': 'Invalid server response'}


    def fetchData(self, param_dict):
        success, response_json = self._make_request(param_dict)

        print(f"fetchData started - param_dict: {param_dict}")

        # Check HTTP request status
        if not success:
            response_dict = {
                "return_code": "99999",
                "message": response_json["error"]
            }
            return response_dict

        # Check message code
        return_code = response_json.get('return_code')
        message = response_json.get('message')
        if return_code !=  "000000":
            response_dict = {
                "return_code": return_code,
                "message": response_json["message"]
            }
            return response_dict

        # parse Message
        resultset_dict = response_json.get('resultset_dict')
        if resultset_dict:
            print(f"Data imported successfully. Records count: {len(resultset_dict)}")

            resultset_df = pd.DataFrame(resultset_dict)
            print(resultset_df.head())
        else:
            return_code = "999999"
            message = "No data found in the specified range."

        response_dict = {
            "return_code": return_code,
            "message": message,
            "resultset_df": resultset_df
        }

        print(f"fetchData completed - response_dict: {response_dict}")
        return response_dict

    def saveData(self, param_dict: dict):

        print(f"saveData started - param_dict: {param_dict}")

        try:
            dataset_df: pd.DataFrame = param_dict["params"]["resultset_df"]
            excel_file_path = os.path.join(param_dict["params"]["path"], rf"{param_dict["name"]}.xlsx")
            dataset_df.to_excel(excel_file_path)

            response_dict = {
                "return_code": "000000",
                "message": rf"save excel successfully",
                "excel_file_path": excel_file_path,
            }

        except Exception as e:
            response_dict = {
                "return_code": "999999",
                "message": rf"save excel failed: {e.with_traceback()} ",
            }

        print(f"saveData completed - response_dict: {response_dict}")
        return response_dict

    def draw_plot(self, param_dict):

        print(f"draw_plot started - param_dict: {param_dict}")

        try:

            data_frame = param_dict["params"]["resultset_df"]
            PlotX = param_dict["params"]["PlotX"]
            PlotY = param_dict["params"]["PlotY"]

            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(data_frame[PlotX], data_frame[PlotY], marker='o')

            # 设置图表标题和坐标轴标签
            ax.set_title('Close Point Over Trade Date')
            ax.set_xlabel('Trade Date')
            plt.xticks(rotation=45)
            ax.set_ylabel('Close Point')
            ax.grid(True)
            ax.set_xticks(data_frame[PlotX])

            plt.savefig(param_dict["params"]["plot_file_path"], dpi=300, bbox_inches='tight')
            plt.show()

            response_dict = {
                "return_code": "000000",
                "message": rf"draw plot successfully",
                "plot_file_path": param_dict["params"]["plot_file_path"],
            }
        except Exception as e:
            response_dict = {
                "return_code": "999999",
                "message": rf"draw plot failed: {e.with_traceback()} "
            }

        print(f"draw_plot completed - response_dict: {response_dict}")
        return response_dict

    def open_file(self, param_dict: dict):
        print(f"open_file started - param_dict: {param_dict}")

        try:
            action = param_dict["params"]["action"]
            command = param_dict["params"]["command"]
            file_path = param_dict["params"]["file_path"]

            if command == "mspaint":
                #subprocess.run(["start", file_path], shell=True)
                process = subprocess.Popen([command, file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')

                stdout, stderr = process.communicate()
                if process.returncode != 0:
                    return {"return_code": "99999", "message": stderr}
                return {"return_code": "000000", "message": stdout}
            else:
                subprocess.run([action, command, file_path], shell=True)

            response_dict = {
                "return_code": "000000",
                "message": rf"Action executed successfully",
            }

        except Exception as e:
            response_dict = {
                "return_code": "999999",
                "message": rf"Action executed failed: {e.with_traceback()} ",
            }

        print(f"open_file completed - response_dict: {response_dict}")
        return response_dict

# if __name__ == '__main__':
#     # Example usage
#     client = FlaskClient_AI()
#     response_dict = {}
#
#     # Step 1 - fetch df_tushare_us_stock_daily
#     param_dict = {
#         "name": "fetch_df_tushare_us_stock_daily",
#         "action": "fetch",
#         "params": {
#             "url": "http://localhost:5000/fetch_data_with_ai",
#             "question": "show me the trade date, percent and volume of Citi change between 2022/12/25 to 2024/12/31",
#             }
#     }
#
#     response = client.fetchData(param_dict)
#     response_dict["fetch_df_tushare_us_stock_daily"] = response
#     if response.get("return_code") != "000000":
#         exit()
#
#     # Step 2 - save df_tushare_us_stock_daily
#     param_dict = {
#         "name": "save_df_tushare_us_stock_daily",
#         "action": "save",
#         "params": {
#             "path": r"D:\workspace_python\infinity\dataIntegrator\data\outbound",
#             "resultset_df": response_dict["fetch_df_tushare_us_stock_daily"]["resultset_df"]
#         }
#     }
#     response = client.saveData(param_dict)
#     response_dict["save_df_tushare_us_stock_daily"] = response
#     if response.get("return_code") != "000000":
#         exit()
#
#     # Step 3 - fetch df_tushare_us_stock_basic
#     param_dict = {
#         "name": "fetch_df_tushare_us_stock_basic",
#         "action": "fetch",
#         "params": {
#             "url": "http://localhost:5000/fetch_data_with_ai",
#             "question": "显示股票分类是 EQ 的这些股票的英文名称，股票分类和上市日期，按照上市日期排序，每个股票只显示一次即可。",
#             }
#     }
#
#     response = client.fetchData(param_dict)
#     response_dict["fetch_df_tushare_us_stock_basic"] = response
#     if response.get("return_code") != "000000":
#         exit()
#
#     # Step 4 - save df_tushare_us_stock_basic
#     param_dict = {
#         "name": "save_df_tushare_us_stock_basic",
#         "action": "save",
#         "params": {
#             "path": r"D:\workspace_python\infinity\dataIntegrator\data\outbound",
#             "resultset_df": response_dict["fetch_df_tushare_us_stock_basic"]["resultset_df"]
#         }
#     }
#     response = client.saveData(param_dict)
#     response_dict["save_df_tushare_us_stock_basic"] = response
#     if response.get("return_code") != "000000":
#         exit()
#
#     # Step 5 - open df_tushare_us_stock_basic excel
#     param_dict = {
#         "name": "open_file",
#         "action": "start",
#         "params": {
#             "action": "start",
#             "command": "excel",
#             "file_path": response_dict["save_df_tushare_us_stock_basic"]["excel_file_path"]
#         }
#     }
#     response = client.open_file(param_dict)
#     response_dict["open_file"] = response
#     if response.get("return_code") != "000000":
#         exit()
#
#     # Step 6 - draw plot
#     param_dict = {
#         "name": "plot_df_tushare_us_stock_basic",
#         "action": "plot",
#         "params": {
#             "resultset_df": response_dict["fetch_df_tushare_us_stock_daily"]["resultset_df"],
#             "PlotX": "trade_date",
#             "PlotY": "pct_change",
#             "plot_file_path": os.path.join(CommonParameters.outBoundPath,"close_point_plot.png")
#         }
#     }
#     response = client.draw_plot(param_dict)
#     response_dict["plot_df_tushare_us_stock_basic"] = response
#     if response.get("return_code") != "000000":
#         exit()
#
#     # Step 7 - open plot
#     param_dict = {
#         "name": "open_file",
#         "action": "start",
#         "params": {
#             "action": "open",
#             "command": "mspaint",
#             "file_path": response_dict["plot_df_tushare_us_stock_basic"]["plot_file_path"]
#         }
#     }
#     response = client.open_file(param_dict)
#     response_dict["open_file"] = response
#     if response.get("return_code") != "000000":
#         exit()
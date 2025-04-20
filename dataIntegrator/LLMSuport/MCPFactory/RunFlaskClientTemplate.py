import os

from dataIntegrator.LLMSuport.MCPFactory.FlaskClientWithAI import FlaskClientWithAI
from dataIntegrator.common.CommonParameters import CommonParameters

if __name__ == '__main__':

    # Step 0 - Init the program
    client = FlaskClientWithAI()
    response_dict = dict()

    # Step 1 - fetch df_tushare_us_stock_daily
    param_dict = {
        "name": "fetch_df_tushare_us_stock_daily",
        "action": "fetch",
        "params": {
            "url": "http://localhost:5000/fetch_data_with_ai",
            "question": "show me the trade date, percent and volume of Citi change between 2022/12/25 to 2024/12/31",
            }
    }

    response = client.fetchData(param_dict)
    response_dict["fetch_df_tushare_us_stock_daily"] = response
    if response.get("return_code") != "000000":
        exit()

    # Step 2 - save df_tushare_us_stock_daily
    param_dict = {
        "name": "save_df_tushare_us_stock_daily",
        "action": "save",
        "params": {
            "path": r"D:\workspace_python\infinity\dataIntegrator\data\outbound",
            "resultset_df": response_dict["fetch_df_tushare_us_stock_daily"]["resultset_df"]
        }
    }
    response = client.saveData(param_dict)
    response_dict["save_df_tushare_us_stock_daily"] = response
    if response.get("return_code") != "000000":
        exit()

    # Step 3 - fetch df_tushare_us_stock_basic
    param_dict = {
        "name": "fetch_df_tushare_us_stock_basic",
        "action": "fetch",
        "params": {
            "url": "http://localhost:5000/fetch_data_with_ai",
            "question": "显示股票分类是 EQ 的这些股票的英文名称，股票分类和上市日期，按照上市日期排序，每个股票只显示一次即可。",
            }
    }

    response = client.fetchData(param_dict)
    response_dict["fetch_df_tushare_us_stock_basic"] = response
    if response.get("return_code") != "000000":
        exit()

    # Step 4 - save df_tushare_us_stock_basic
    param_dict = {
        "name": "save_df_tushare_us_stock_basic",
        "action": "save",
        "params": {
            "path": r"D:\workspace_python\infinity\dataIntegrator\data\outbound",
            "resultset_df": response_dict["fetch_df_tushare_us_stock_basic"]["resultset_df"]
        }
    }
    response = client.saveData(param_dict)
    response_dict["save_df_tushare_us_stock_basic"] = response
    if response.get("return_code") != "000000":
        exit()

    # Step 5 - open df_tushare_us_stock_basic excel
    param_dict = {
        "name": "open_file",
        "action": "start",
        "params": {
            "action": "start",
            "command": "excel",
            "file_path": response_dict["save_df_tushare_us_stock_basic"]["excel_file_path"]
        }
    }
    response = client.open_file(param_dict)
    response_dict["open_file"] = response
    if response.get("return_code") != "000000":
        exit()

    # Step 6 - draw plot
    param_dict = {
        "name": "plot_df_tushare_us_stock_basic",
        "action": "plot",
        "params": {
            "resultset_df": response_dict["fetch_df_tushare_us_stock_daily"]["resultset_df"],
            "PlotX": "trade_date",
            "PlotY": "pct_change",
            "plot_file_path": os.path.join(CommonParameters.outBoundPath,"close_point_plot.png")
        }
    }
    response = client.draw_plot(param_dict)
    response_dict["plot_df_tushare_us_stock_basic"] = response
    if response.get("return_code") != "000000":
        exit()

    # Step 7 - open plot
    param_dict = {
        "name": "open_file",
        "action": "start",
        "params": {
            "action": "open",
            "command": "mspaint",
            "file_path": response_dict["plot_df_tushare_us_stock_basic"]["plot_file_path"]
        }
    }
    response = client.open_file(param_dict)
    response_dict["open_file"] = response
    if response.get("return_code") != "000000":
        exit()
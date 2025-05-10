from dataIntegrator.common.CommonParameters import CommonParameters
from dataIntegrator.common.CustomError import CustomError
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator.dataService.OracleService import OracleService

if __name__ == "__main__":

    data_migration_config_list = [
        # {
        #     "queryStatement": """
        #     SELECT distinct(*)
        #     FROM indexsysdb.df_tushare_us_stock_daily
        #     WHERE ts_code = 'C' AND
        #     trade_date >= '20220101' AND
        #     trade_date <= '20241231'
        #     """,
        #     "target_table": "citi.df_tushare_us_stock_daily"
        # },
        # {
        #     "queryStatement": """
        #     SELECT distinct(*)
        #     FROM indexsysdb.df_tushare_us_stock_basic
        #     """,
        #     "target_table": "citi.df_tushare_us_stock_basic"
        # }

        # {
        # "queryStatement": """
        # SELECT distinct(*)
        # FROM indexsysdb.df_sys_calendar
        # """,
        #     "target_table": "citi.df_sys_calendar"
        # }
        # {
        #     "queryStatement": """
        #     SELECT distinct(*)
        #     FROM indexsysdb.df_tushare_cn_cpi
        #     """,
        #     "target_table": "citi.df_tushare_cn_cpi"
        # }
        {
            "queryStatement": """
        SELECT distinct(*)
        FROM indexsysdb.df_tushare_fx_offshore_basic
        """,
            "target_table": "citi.df_tushare_fx_offshore_basic"
        }
    ]

    for config in data_migration_config_list:
        queryStatement = config['queryStatement']
        target_table = config['target_table']

        try:
            clickhouseService = ClickhouseService()
            result_df = clickhouseService.getDataFrameWithoutColumnsName(queryStatement)

            for col in result_df.columns:
                if result_df[col].dtype == object:  # 字符串类型
                    result_df[col] = result_df[col].fillna("")
                else:  # 数值类型
                    result_df[col] = result_df[col].fillna(0)

            oracle_config = CommonParameters.oracle_config
            oracle_config['oracle_table'] = target_table
            oracle_config['dataframe'] = result_df

            oracleService = OracleService(oracle_config['oracle_client'])
            oracleService.migrate_dataframe_to_oracle(oracle_config)
        except CustomError as e:
            exit(e.error_code)
        except Exception as e:
            print(f"Data migration failed: {e}")
            exit()
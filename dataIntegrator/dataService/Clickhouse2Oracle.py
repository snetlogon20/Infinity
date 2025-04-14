from dataIntegrator.common.CommonParameters import CommonParameters
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

        {
        "queryStatement": """
        SELECT distinct(*)
        FROM indexsysdb.df_sys_calendar
        """,
            "target_table": "citi.df_sys_calendar"
        }
    ]

    for config in data_migration_config_list:
        queryStatement = config['queryStatement']
        target_table = config['target_table']

        try:
            clickhouseService = ClickhouseService()
            result_df = clickhouseService.getDataFrameWithoutColumnsName(queryStatement)

            oracle_config = CommonParameters.oracle_config
            oracle_config['oracle_table'] = target_table
            oracle_config['dataframe'] = result_df

            oracleService = OracleService(oracle_config['oracle_client'])
            oracleService.migrate_dataframe_to_oracle(oracle_config)
        except Exception as e:
            print(f"Data migration failed: {e}")
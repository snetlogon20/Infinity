import pandas as pd
import oracledb

from dataIntegrator import CommonLib, CommonLogLib
from dataIntegrator.TuShareService.TuShareService import TuShareService

from dataIntegrator.common.CommonParameters import CommonParameters
from dataIntegrator.common.CustomError import CustomError

logger = CommonLib.logger
commonLib = CommonLib()

class OracleService(TuShareService):


    def __init__(self, oracle_client):
        super().__init__()
        self.oracleClient = oracle_client

    def getDataFrameWithoutColumnsName(self, sql):
        """执行 SQL 查询并返回包含列名的 DataFrame"""
        logger.info("prepareData started")

        try:
            # 执行 SQL 查询
            cursor = self.oracleClient.cursor()
            cursor.execute(sql)
            result = cursor.fetchall()

            # 获取列名
            columns = [col[0] for col in cursor.description]

            # 将结果转换为 DataFrame
            dataframe = pd.DataFrame(result, columns=columns)

        except Exception as e:
            raise CustomError("", custom_error_message=rf"sql: {sql}")
        finally:
            cursor.close()

        logger.info("execute_query completed")

        return dataframe

    def _insert_data_into_oracle(self, dataframe, oracle_table, oracle_columns):
        """
        将数据插入到 Oracle 表中
        :param dataframe: 要插入的数据
        :param oracle_table: Oracle 目标表名
        :param oracle_columns: Oracle 表的列名列表
        """
        try:
            # 将 DataFrame 转换为插入语句
            placeholders = ", ".join([":" + col for col in oracle_columns])
            insert_sql = f"INSERT INTO {oracle_table} ({', '.join(oracle_columns)}) VALUES ({placeholders})"
            logger.info(insert_sql)

            # 执行批量插入操作
            cursor = self.oracleClient.cursor()
            cursor.executemany(insert_sql, dataframe.to_dict('records'))
            self.oracleClient.commit()
            cursor.close()

        except Exception as e:
            raise commonLib.raise_custom_error(error_code="000100", custom_error_message=rf"插入数据到 Oracle 失败, sql: {insert_sql}", e=e)

    @classmethod
    def migrate_dataframe_to_oracle(self, oracle_config):

        self.logger.info("migrate_dataframe_to_oracle started")

        # 初始化 Oracle 连接
        host = oracle_config["host"]
        port = oracle_config["port"]
        sid = oracle_config["sid"]
        username = oracle_config["username"]
        password = oracle_config["password"]
        dataframe = oracle_config["dataframe"]

        try:
            # 初始化 Oracle 客户端
            #oracledb.init_oracle_client(lib_dir=oracle_config["oracle_client"])
            oracledb.init_oracle_client(lib_dir=None)

            # 生成 DSN 并建立连接
            dsn = oracledb.makedsn(host, port, sid=sid)
            connection = oracledb.connect(user=username, password=password, dsn=dsn)
            logger.info("成功连接到 Oracle 数据库！")

            # 创建 OracleService 对象
            oracle_service = OracleService(connection)

            # 定义目标表名和列名
            oracle_table =oracle_config["oracle_table"]
            oracle_columns = dataframe.columns.tolist()

            # 将数据插入到 Oracle 表中
            logger.info(f"将数据插入到 Oracle 表 {oracle_table} 中...")
            oracle_service._insert_data_into_oracle(dataframe, oracle_table, oracle_columns)
            logger.info("数据插入完成！")

        except oracledb.Error as e:
            raise commonLib.raise_custom_error(error_code="000100", custom_error_message=rf"插入数据到 Oracle 失败, sql: {oracle_table}", e=e, log_error=False)

        finally:
            # 确保连接关闭
            if 'connection' in locals():
                connection.close()


if __name__ == "__main__":
    # 示例 DataFrame
    data = {
        'ts_code': ['AAPL', 'BAC', 'C'],
        'trade_date': ['20231001', '20231002', '20231003'],
        'close_point': [150.0, 25.0, 50.0],
        'open_point': [148.0, 24.5, 49.5],
        'high_point': [152.0, 26.0, 51.0],
        'low_point': [147.0, 24.0, 49.0],
        'pre_close': [149.0, 24.8, 50.0],
        'change_point': [1.0, 0.2, 0.0],
        'pct_change': [0.67, 0.81, 0.0],
        'vol': [1000000, 2000000, 1500000],
        'amount': [150000000, 50000000, 75000000],
        'vwap': [150.5, 25.5, 50.5],
        'turnover_ratio': [0.5, 0.3, 0.4],
        'total_mv': [2500000000, 500000000, 1000000000],
        'pe': [25.0, 10.0, 15.0],
        'pb': [5.0, 1.0, 2.0]
    }
    dataframe = pd.DataFrame(data)

    oracle_config = CommonParameters.oracle_config
    oracle_config['oracle_table'] = "citi.us_stock_daily"
    oracle_config['dataframe'] = dataframe

    oracleService = OracleService(oracle_config['oracle_client'])
    oracleService.migrate_dataframe_to_oracle(oracle_config)

from dataIntegrator import CommonLib, CommonParameters
from clickhouse_driver import Client as ClickhouseClient
import pandas as pd

logger = CommonLib.logger
commonLib = CommonLib()

class ClickhouseService:

    clickhouseClient = ClickhouseClient(
        host=CommonParameters.clickhouseHostName,
        database=CommonParameters.clickhouseHostDatabase)
    @classmethod
    def getDataFrame(self, sql, columns):
        logger.info("prepareData started")
        try:
            result = self.clickhouseClient.execute(sql)
            dataframe = pd.DataFrame(result)
            dataframe.columns  = columns

        except Exception as e:
            raise commonLib.raise_custom_error(error_code="000101", custom_error_message=rf"getDataFrame execute sql error, sql: {sql}", e=e)

        logger.info("execute_query completed")

        return dataframe

    @classmethod
    def getDataFrameWithoutColumnsName(self, sql):
        logger.info(rf"prepareData started - sql: {sql}")
        try:
            #self.clickhouseClient.execute('USE indexsysdb')
            cursor = self.clickhouseClient.execute_iter(sql, with_column_types=True)
            columns = [col[0] for col in next(cursor)]
            result = list(cursor)
            # 创建 DataFrame 并指定列名
            dataframe = pd.DataFrame(result, columns=columns)

        except Exception as e:
            raise commonLib.raise_custom_error(error_code="000101",custom_error_message=rf"getDataFrameWithoutColumnsName execute sql error, sql: {sql}", e=e)

        logger.info("execute_query completed")

        return dataframe


    @classmethod
    def execute_sql(self, sql):
        logger.info(rf"Executing SQL statement: {sql}")
        try:
            self.clickhouseClient.execute(sql)
        except Exception as e:
            raise commonLib.raise_custom_error(
                error_code="000102",
                custom_error_message=rf"execute_sql failed, SQL: {sql}",
                e=e
            )
        logger.info("SQL execution completed")


    @classmethod
    def save_dataframe_to_clickhouse(cls, dataframe, table_name, database='indexsysdb'):
        """
        将带有列名的 DataFrame 保存到 ClickHouse

        Args:
            dataframe: 要保存的 DataFrame
            table_name: 目标表名
            database: 数据库名，默认为 'indexsysdb'

        Returns:
            bool: 保存成功返回 True，失败抛出异常
        """
        logger.info(f"Saving DataFrame to ClickHouse table: {database}.{table_name}")

        try:
            # 检查表是否存在
            check_table_sql = f"""
            SELECT name 
            FROM system.tables 
            WHERE database = '{database}' AND name = '{table_name}'
            """
            table_exists = cls.clickhouseClient.execute(check_table_sql)

            if not table_exists:
                # 表不存在，创建表
                create_table_sql = cls._generate_create_table_sql(dataframe, table_name, database)
                cls.execute_sql(create_table_sql)
                logger.info(f"Created new table: {database}.{table_name}")
            else:
                logger.info(f"Table already exists: {database}.{table_name}")

            # 准备插入数据
            # 将 DataFrame 转换为元组列表
            values = [tuple(row) for row in dataframe.values]

            # 构建插入 SQL
            columns_str = ', '.join(dataframe.columns)
            placeholders = ', '.join(['%s'] * len(dataframe.columns))
            insert_sql = f"INSERT INTO {database}.{table_name} ({columns_str}) VALUES"

            # 执行批量插入
            cls.clickhouseClient.execute(insert_sql, values)

            logger.info(f"Successfully saved {len(dataframe)} rows to {database}.{table_name}")
            return True

        except Exception as e:
            raise commonLib.raise_custom_error(
                error_code="000103",
                custom_error_message=f"Failed to save DataFrame to ClickHouse table: {database}.{table_name}",
                e=e
            )


    @classmethod
    def _generate_create_table_sql(cls, dataframe, table_name, database):
        """
        根据 DataFrame 结构生成 CREATE TABLE 语句

        Args:
            dataframe: 源 DataFrame
            table_name: 表名
            database: 数据库名

        Returns:
            str: CREATE TABLE 语句
        """
        columns_definitions = []

        for col_name in dataframe.columns:
            col_dtype = dataframe[col_name].dtype

            # 根据 pandas 数据类型映射到 ClickHouse 类型
            if 'int' in str(col_dtype):
                ch_type = 'Int64'
            elif 'float' in str(col_dtype):
                ch_type = 'Float64'
            elif 'datetime' in str(col_dtype) or 'date' in str(col_dtype).lower():
                ch_type = 'Date'  # 或者 'DateTime' 根据需要
            else:
                ch_type = 'String'

            columns_definitions.append(f"{col_name} {ch_type}")

        columns_str = ',\n    '.join(columns_definitions)

        create_sql = f"""
        CREATE TABLE {database}.{table_name} (
            {columns_str}
        )
        ENGINE = MergeTree()
        ORDER BY tuple()
        """

        return create_sql
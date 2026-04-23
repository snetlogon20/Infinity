from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

logger = CommonLib.logger

class TuShareStockBasicService(TuShareService):
    @classmethod
    def prepareDataFrame(self, exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date'):
        logger.info("prepareData started")

        try:
            self.dataFrame = self.pro.stock_basic(exchange=exchange, list_status=list_status, fields=fields)
            logger.info(f"成功获取股票列表数据，共 {len(self.dataFrame)} 行")
            logger.info(f"self.dataFrame.shape: {str(self.dataFrame.shape)}")

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")

        return self.dataFrame

    @classmethod
    def saveDateToClickHouse(self):
        logger.info("saveDateToClickHouse started")

        try:
            self.dataFrame = self.dataFrame.replace({None: "Nan"})

            columns = self.dataFrame.columns.tolist()
            columns_str = ','.join(columns)

            insert_sql_statement = f'insert into indexsysdb.df_tushare_stock_basic ({columns_str}) VALUES'
            data = self.dataFrame.to_dict('records')
            self.clickhouseClient.execute(insert_sql_statement, data)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed")

    @classmethod
    def deleteDateFromClickHouse(self):
        logger.info("deleteDataFromClickHouse started")

        try:
            del_df_tushare_sql = "ALTER TABLE indexsysdb.df_tushare_stock_basic DELETE where ts_code is not Null"
            self.clickhouseClient.execute(del_df_tushare_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name, event="ALTER TABLE indexsysdb.df_tushare_stock_basic Error")
            raise e

        logger.info("deleteDateFromClickHouse completed")

    def get_stock_names(self, all_products_results):
        """
        从 ClickHouse 获取股票名称

        参数:
        - all_products_results: 产品权重结果列表

        返回:
        - dict: 股票代码 -> 股票名称 的映射字典
        """
        stock_name_map = {}

        try:
            # 从所有 products 结果中收集所有唯一的股票代码
            all_codes = set()
            if all_products_results:
                for products_df in all_products_results:
                    all_codes.update(products_df['products'].unique())

            if not all_codes:
                logger.warning("没有找到任何股票代码")
                return stock_name_map

            logger.info(f"需要查询 {len(all_codes)} 只股票的名称...")

            # 构建 SQL 查询
            codes_list = "','".join(all_codes)
            sql = f"""
            SELECT ts_code, name
            FROM indexsysdb.df_tushare_stock_basic
            WHERE ts_code IN ('{codes_list}')
            """

            # 执行查询
            clickhouseService = ClickhouseService()
            df = clickhouseService.getDataFrameWithoutColumnsName(sql)

            # 构建映射字典
            for _, row in df.iterrows():
                ts_code = row['ts_code']
                name = row['name']
                stock_name_map[ts_code] = name

            logger.info(f"成功获取 {len(stock_name_map)} 只股票名称")

        except Exception as e:
            logger.error(f"获取股票名称失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

        return stock_name_map
from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib
import pandas as pd


logger = CommonLib.logger

class TuShareOptBasicService(TuShareService):

    @classmethod
    def prepareDataFrame(self, exchange=""):
        """
        获取期权基础信息
        opt_basic 接口根据交易所代码获取该交易所所有期权合约基础信息
        """
        logger.info("prepareData started")

        try:
            # 调用 TuShare opt_basic 接口
            if exchange:
                self.dataFrame = self.pro.opt_basic(exchange=exchange,
                    fields='ts_code,symbol,exchange,name,per_unit,opt_code,opt_type,call_put,'
                           'exercise_type,exercise_price,opt_multiplier,s_month,maturity_date,'
                           'list_price,list_date,delist_date,last_edate,last_ddate,quote_unit,min_price_chg')
            else:
                self.dataFrame = self.pro.opt_basic(
                    fields='ts_code,symbol,exchange,name,per_unit,opt_code,opt_type,call_put,'
                           'exercise_type,exercise_price,opt_multiplier,s_month,maturity_date,'
                           'list_price,list_date,delist_date,last_edate,last_ddate,quote_unit,min_price_chg')

            row_count = len(self.dataFrame)
            logger.info(f"成功获取期权基础信息数据，共 {row_count} 行")

            # 确保列名与数据库定义一致
            expected_columns = [
                'ts_code', 'symbol', 'exchange', 'name', 'per_unit',
                'opt_code', 'opt_type', 'call_put', 'exercise_type',
                'exercise_price', 'opt_multiplier', 's_month', 'maturity_date',
                'list_price', 'list_date', 'delist_date', 'last_edate',
                'last_ddate', 'quote_unit', 'min_price_chg'
            ]

            # 只保留接口实际返回的列
            available_columns = [col for col in expected_columns if col in self.dataFrame.columns]
            self.dataFrame = self.dataFrame[available_columns]

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")
        return self.dataFrame

    @classmethod
    def saveDateToClickHouse(self):
        logger.info("saveDateToClickHouse started")

        try:
            # 定义 ClickHouse 表中所有字段及其类型
            table_columns = [
                'ts_code', 'symbol', 'exchange', 'name', 'per_unit',
                'opt_code', 'opt_type', 'call_put', 'exercise_type',
                'exercise_price', 'opt_multiplier', 's_month', 'maturity_date',
                'list_price', 'list_date', 'delist_date', 'last_edate',
                'last_ddate', 'quote_unit', 'min_price_chg'
            ]

            # String 类型字段
            string_columns = [
                'ts_code', 'symbol', 'exchange', 'name', 'per_unit',
                'opt_code', 'opt_type', 'call_put', 'exercise_type',
                's_month', 'maturity_date', 'list_date', 'delist_date',
                'last_edate', 'last_ddate', 'quote_unit', 'min_price_chg'
            ]

            # Float 类型字段
            numeric_columns = [
                'exercise_price', 'opt_multiplier', 'list_price'
            ]

            # 获取 DataFrame 中实际存在的列
            actual_columns = self.dataFrame.columns.tolist()

            # 为缺少的列填充默认值
            for col in table_columns:
                if col not in actual_columns:
                    if col in string_columns:
                        self.dataFrame[col] = ''  # String 类型用空字符串
                    elif col in numeric_columns:
                        self.dataFrame[col] = 0.0  # 数值类型用 0

            # 按表结构顺序重新排列列
            self.dataFrame = self.dataFrame[table_columns]

            # 处理 API 返回数据中的 None 值
            for col in string_columns:
                if col in self.dataFrame.columns:
                    # 先转为字符串，再替换 'nan'/'None' 为空字符串
                    self.dataFrame[col] = self.dataFrame[col].astype(str).replace('nan', '').replace('None', '')
            for col in numeric_columns:
                if col in self.dataFrame.columns:
                    self.dataFrame[col] = pd.to_numeric(self.dataFrame[col], errors='coerce').fillna(0.0)

            insert_sql_statement = f'INSERT INTO indexsysdb.df_tushare_opt_basic ({", ".join(table_columns)}) VALUES'
            data = self.dataFrame.to_dict('records')
            self.clickhouseClient.execute(insert_sql_statement, data)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed")

    @classmethod
    def deleteDateFromClickHouse(self):
        """
        由于 opt_basic 是全量数据（按交易所），删除旧数据后重新插入
        """
        logger.info("deleteDateFromClickHouse started")

        try:
            del_sql = "ALTER TABLE indexsysdb.df_tushare_opt_basic DELETE WHERE 1=1"
            self.clickhouseClient.execute(del_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDateFromClickHouse completed")

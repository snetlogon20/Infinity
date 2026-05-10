from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib

logger = CommonLib.logger

class TuShareConvertBondBasicService(TuShareService):

    @classmethod
    def prepareDataFrame(self):
        """
        获取可转债基础信息
        由于 cb_basic 接口没有日期范围参数，直接获取所有数据
        """
        logger.info("prepareData started")

        try:
            # 调用 TuShare cb_basic 接口
            self.dataFrame = self.pro.cb_basic()

            # 确保列名与数据库定义一致
            expected_columns = [
                'ts_code', 'bond_full_name', 'bond_short_name', 'cb_code',
                'cb_type', 'stk_code', 'stk_short_name', 'maturity', 'par',
                'issue_price', 'issue_size', 'remain_size', 'value_date',
                'maturity_date', 'rate_type', 'coupon_rate', 'add_rate',
                'pay_per_year', 'list_date', 'delist_date', 'exchange',
                'conv_start_date', 'conv_end_date', 'conv_stop_date',
                'first_conv_price', 'conv_price', 'rate_clause', 'put_clause',
                'maturity_call_price', 'call_clause', 'reset_clause',
                'conv_clause', 'guarantor', 'guarantee_type', 'issue_rating',
                'newest_rating', 'rating_comp'
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
                'ts_code', 'bond_full_name', 'bond_short_name', 'cb_code',
                'cb_type', 'stk_code', 'stk_short_name', 'maturity', 'par',
                'issue_price', 'issue_size', 'remain_size', 'value_date',
                'maturity_date', 'rate_type', 'coupon_rate', 'add_rate',
                'pay_per_year', 'list_date', 'delist_date', 'exchange',
                'conv_start_date', 'conv_end_date', 'conv_stop_date',
                'first_conv_price', 'conv_price', 'rate_clause', 'put_clause',
                'maturity_call_price', 'call_clause', 'reset_clause',
                'conv_clause', 'guarantor', 'guarantee_type', 'issue_rating',
                'newest_rating', 'rating_comp'
            ]
            
            # String 类型字段（不能用 None，需要用空字符串）
            string_columns = [
                'ts_code', 'bond_full_name', 'bond_short_name', 'cb_code',
                'cb_type', 'stk_code', 'stk_short_name', 'value_date',
                'maturity_date', 'rate_type', 'list_date', 'delist_date', 'exchange',
                'conv_start_date', 'conv_end_date', 'conv_stop_date',
                'rate_clause', 'put_clause', 'maturity_call_price', 'call_clause', 
                'reset_clause', 'conv_clause', 'guarantor', 'guarantee_type', 
                'issue_rating', 'newest_rating', 'rating_comp'
            ]
            
            # Float/Int 类型字段
            numeric_columns = [
                'maturity', 'par', 'issue_price', 'issue_size', 'remain_size',
                'coupon_rate', 'add_rate', 'pay_per_year',
                'first_conv_price', 'conv_price'
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
            
            # 处理 API 返回数据中的 None 值（String 列转为空字符串，数值列转为 0）
            for col in string_columns:
                if col in self.dataFrame.columns:
                    self.dataFrame[col] = self.dataFrame[col].fillna('')
            for col in numeric_columns:
                if col in self.dataFrame.columns:
                    self.dataFrame[col] = self.dataFrame[col].fillna(0.0)
            
            insert_sql_statement = f'INSERT INTO indexsysdb.df_tushare_cb_basic ({", ".join(table_columns)}) VALUES'
            data = self.dataFrame.to_dict('records')
            self.clickhouseClient.execute(insert_sql_statement, data)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed")

    @classmethod
    def deleteDateFromClickHouse(self):
        """
        由于 cb_basic 是全量数据，删除所有历史数据后重新插入
        """
        logger.info("deleteDateFromClickHouse started")

        try:
            del_sql = "ALTER TABLE indexsysdb.df_tushare_cb_basic DELETE WHERE 1=1"
            self.clickhouseClient.execute(del_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDateFromClickHouse completed")

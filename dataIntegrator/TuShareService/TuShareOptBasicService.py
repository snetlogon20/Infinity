from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib, CommonParameters
import pandas as pd


logger = CommonLib.logger

class TuShareOptBasicService(TuShareService):

    # opt_basic 单次调用最多返回约 12000 行，超出部分会被 TuShare 静默截断，必须分页拉取
    OPT_BASIC_PAGE_SIZE = 5000

    @classmethod
    def prepareDataFrame(self, exchange="", symbol_prefix=None):
        """
        获取期权基础信息
        opt_basic 接口根据交易所代码获取该交易所所有期权合约基础信息

        Args:
            exchange: 交易所代码（SSE/SZSE/CFFEX/DCE/CZCE/SHFE/INE/GFEX），空串=全市场
            symbol_prefix: 标的代码前缀过滤（如 '510050' = 华夏上证50ETF期权）。
                           TuShare 不支持按 symbol 服务端过滤，此处拉取后在内存中过滤。
                           注意：SSE ETF 期权的 ts_code 是 8 位数字（如 10000201.SH），
                           标的信息只在 symbol 字段中（如 510050C2900M0250.SSE）。
        """
        logger.info("prepareData started")

        try:
            fields = ('ts_code,symbol,exchange,name,per_unit,opt_code,opt_type,call_put,'
                      'exercise_type,exercise_price,opt_multiplier,s_month,maturity_date,'
                      'list_price,list_date,delist_date,last_edate,last_ddate,quote_unit,min_price_chg')

            # 分页拉取，避免单次调用超过行数上限被静默截断
            all_dfs = []
            offset = 0
            while True:
                df = self.pro.opt_basic(exchange=exchange, fields=fields,
                                        offset=offset, limit=self.OPT_BASIC_PAGE_SIZE)
                if df is None or df.empty:
                    break
                all_dfs.append(df)
                logger.info(f"  opt_basic 分页拉取: offset={offset}, 本页 {len(df)} 行")
                if len(df) < self.OPT_BASIC_PAGE_SIZE:
                    break
                offset += self.OPT_BASIC_PAGE_SIZE

            if not all_dfs:
                logger.warning(f"opt_basic 未获取到数据 (exchange='{exchange}')")
                self.dataFrame = pd.DataFrame()
                return self.dataFrame

            self.dataFrame = pd.concat(all_dfs, ignore_index=True).drop_duplicates(subset=['ts_code'])
            row_count = len(self.dataFrame)
            logger.info(f"成功获取期权基础信息数据，共 {row_count} 行")

            # 按标的代码前缀过滤（如 510050 ETF 期权）
            if symbol_prefix:
                mask = (self.dataFrame['symbol'].astype(str)
                        .str.upper()
                        .str.startswith(str(symbol_prefix).upper()))
                self.dataFrame = self.dataFrame[mask]
                logger.info(f"按 symbol 前缀 '{symbol_prefix}' 过滤后剩余 {len(self.dataFrame)} 行")

            # 添加 trade_date 列，值为当天日期
            self.dataFrame['trade_date'] = CommonParameters.today

            # 确保列名与数据库定义一致
            expected_columns = [
                'trade_date', 'ts_code', 'symbol', 'exchange', 'name', 'per_unit',
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
                'trade_date', 'ts_code', 'symbol', 'exchange', 'name', 'per_unit',
                'opt_code', 'opt_type', 'call_put', 'exercise_type',
                'exercise_price', 'opt_multiplier', 's_month', 'maturity_date',
                'list_price', 'list_date', 'delist_date', 'last_edate',
                'last_ddate', 'quote_unit', 'min_price_chg'
            ]

            # String 类型字段
            string_columns = [
                'trade_date', 'ts_code', 'symbol', 'exchange', 'name', 'per_unit',
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
    def deleteDateFromClickHouse(self, symbol_prefix=None):
        """
        按 trade_date 删除当天数据，避免覆盖历史数据

        Args:
            symbol_prefix: 标的代码前缀（如 '510050'）。非空时只删除该标的的当天快照，
                           不影响其他标的已入库的数据；为 None 时删除当天全量数据（兼容旧行为）
        """
        logger.info("deleteDateFromClickHouse started")

        try:
            del_sql = f"ALTER TABLE indexsysdb.df_tushare_opt_basic DELETE WHERE trade_date = '{CommonParameters.today}'"
            if symbol_prefix:
                del_sql += f" AND symbol LIKE '{symbol_prefix}%'"
            self.clickhouseClient.execute(del_sql)
            logger.info(f"已删除 trade_date = {CommonParameters.today} 的旧数据"
                        + (f" (symbol LIKE '{symbol_prefix}%')" if symbol_prefix else " (全量)"))
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDateFromClickHouse completed")

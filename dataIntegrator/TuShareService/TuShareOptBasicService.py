from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib, CommonParameters
import pandas as pd


logger = CommonLib.logger

class TuShareOptBasicService(TuShareService):

    # opt_basic 接口单次调用最多返回 12000 行（实测，超出部分静默截断），翻页步长
    OPT_BASIC_PAGE_SIZE = 5000

    # 全量模式（exchange=''）下需要遍历的交易所
    ALL_OPT_EXCHANGES = ['SSE', 'SZSE', 'CFFEX', 'SHFE', 'DCE', 'CZCE', 'INE', 'GFEX']

    # SHFE 期权代码前缀映射（opt_basic → opt_daily）
    # tushare 的 opt_basic 对上期所沪铜期权用标的前缀 CU（如 CU2612C84000.SHF），
    # 而 opt_daily 用交易所原生代码 HO（如 HO2612C84000.SHF），两表按 ts_code JOIN 时全部失配。
    # 入库前统一映射为 opt_daily 的写法。
    SHFE_OPT_PREFIX_MAP = {'CU': 'HO'}

    @classmethod
    def _normalizeOptCode(self, df):
        """将 SHFE 沪铜期权 ts_code 前缀 CU→HO，与 opt_daily 对齐"""
        for src_prefix, dst_prefix in self.SHFE_OPT_PREFIX_MAP.items():
            mask = df['ts_code'].astype(str).str.match(rf'^{src_prefix}\d{{4}}[CP]\d+\.SHF$')
            if mask.any():
                df.loc[mask, 'ts_code'] = df.loc[mask, 'ts_code'].astype(str).str.replace(
                    rf'^{src_prefix}', dst_prefix, regex=True)
                logger.info(f"SHFE 期权代码前缀映射 {src_prefix}->{dst_prefix}: {int(mask.sum())} 行")
        return df

    @classmethod
    def prepareDataFrame(self, exchange=""):
        """
        获取期权基础信息
        opt_basic 接口根据交易所代码获取该交易所所有期权合约基础信息

        重要：opt_basic 单次调用最多返回 12000 行（实测），全市场数据远超此数，
        一次性调用会导致 SHFE 等交易所数据被静默截断。
        因此必须「按交易所 + offset 翻页」拉取。
        """
        logger.info("prepareData started")

        try:
            fields = ('ts_code,symbol,exchange,name,per_unit,opt_code,opt_type,call_put,'
                      'exercise_type,exercise_price,opt_multiplier,s_month,maturity_date,'
                      'list_price,list_date,delist_date,last_edate,last_ddate,quote_unit,min_price_chg')

            # 按交易所遍历（单交易所也要翻页，SHFE 一家就超过 16000 行）
            exchanges = [exchange] if exchange else self.ALL_OPT_EXCHANGES

            frames = []
            for ex in exchanges:
                offset = 0
                while True:
                    chunk = self.pro.opt_basic(exchange=ex, fields=fields,
                                               offset=offset, limit=self.OPT_BASIC_PAGE_SIZE)
                    if chunk is None or len(chunk) == 0:
                        break
                    frames.append(chunk)
                    logger.info(f"opt_basic[{ex}] offset={offset}: {len(chunk)} 行")
                    if len(chunk) < self.OPT_BASIC_PAGE_SIZE:
                        break
                    offset += self.OPT_BASIC_PAGE_SIZE

            if not frames:
                self.dataFrame = pd.DataFrame()
                logger.warning("期权基础信息数据为空")
                return self.dataFrame

            self.dataFrame = pd.concat(frames, ignore_index=True) \
                .drop_duplicates(subset='ts_code', ignore_index=True)

            row_count = len(self.dataFrame)
            logger.info(f"成功获取期权基础信息数据，共 {row_count} 行")

            # SHFE 沪铜期权代码前缀归一化（CU→HO），保证与 opt_daily 可按 ts_code JOIN
            self.dataFrame = self._normalizeOptCode(self.dataFrame)

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
    def deleteDateFromClickHouse(self):
        """
        按 trade_date 删除当天数据，避免覆盖历史数据
        """
        logger.info("deleteDateFromClickHouse started")

        try:
            del_sql = f"ALTER TABLE indexsysdb.df_tushare_opt_basic DELETE WHERE trade_date = '{CommonParameters.today}'"
            self.clickhouseClient.execute(del_sql)
            logger.info(f"已删除 trade_date = {CommonParameters.today} 的旧数据")
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDateFromClickHouse completed")

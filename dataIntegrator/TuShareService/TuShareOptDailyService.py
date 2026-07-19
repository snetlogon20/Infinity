from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib
import pandas

logger = CommonLib.logger

class TuShareOptDailyService(TuShareService):

    @classmethod
    def prepareDataFrame(self, ts_code=None, trade_date=None, start_date=None, end_date=None, exchange=None):
        """
        获取期权日线行情数据
        opt_daily 接口获取期权每日交易数据

        输入参数：
            ts_code: TS合约代码（选填）
            trade_date: 交易日期 (YYYYMMDD)（选填）
            start_date: 开始日期 (YYYYMMDD)（选填）
            end_date: 结束日期 (YYYYMMDD)（选填）
            exchange: 交易所(SSE/SZSE/CFFEX/DCE/SHFE/CZCE)（选填）

        至少需要指定 ts_code、trade_date 或 start_date/end_date 之一
        """
        logger.info("prepareData started")

        try:
            if ts_code:
                # 按合约代码 + 日期范围查询
                self.dataFrame = self.pro.opt_daily(
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=end_date,
                    exchange=exchange
                )
                row_count = len(self.dataFrame)
                logger.info(f"成功获取期权 {ts_code} 的日线数据，共 {row_count} 行")
            elif trade_date:
                # 按单个交易日查询
                self.dataFrame = self.pro.opt_daily(
                    trade_date=trade_date,
                    exchange=exchange
                )
                row_count = len(self.dataFrame)
                logger.info(f"成功获取期权 {trade_date} 的日线数据，共 {row_count} 行")
            elif start_date and end_date:
                # 按日期范围查询（逐日遍历避免超过2000条限制）
                self.dataFrame = self._fetch_by_date_range(start_date, end_date, exchange)
                row_count = len(self.dataFrame)
                logger.info(f"成功获取期权日线数据（日期范围 {start_date}~{end_date}），共 {row_count} 行")
            else:
                logger.error("必须至少指定 ts_code、trade_date 或 start_date/end_date 之一")
                return pandas.DataFrame()

            # 确保列名与数据库定义一致
            expected_columns = [
                'ts_code', 'trade_date', 'exchange',
                'pre_settle', 'pre_close', 'open', 'high', 'low',
                'close', 'settle', 'vol', 'amount', 'oi'
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
    def _fetch_by_date_range(self, start_date, end_date, exchange=None):
        """
        按日期范围逐日遍历获取期权日线数据
        由于单个交易日的数据大约500-1000行，按日遍历可避免超过2000条限制
        """
        from datetime import datetime, timedelta
        import time

        start_dt = datetime.strptime(start_date, "%Y%m%d")
        end_dt = datetime.strptime(end_date, "%Y%m%d")

        all_dfs = []
        current = start_dt
        batch_no = 0
        while current <= end_dt:
            batch_no += 1
            date_str = current.strftime("%Y%m%d")
            try:
                df = self.pro.opt_daily(trade_date=date_str, exchange=exchange)
                if not df.empty:
                    all_dfs.append(df)
                    logger.info(f"  第 {batch_no} 批: {date_str}，获取 {len(df)} 条记录")
                # 限流控制
                time.sleep(0.3)
            except Exception as e:
                logger.warning(f"  第 {batch_no} 批: {date_str} 获取失败: {e}")
                time.sleep(0.5)
            current += timedelta(days=1)

        if not all_dfs:
            logger.warning("所有日期均未获取到数据")
            return pandas.DataFrame()

        return pandas.concat(all_dfs, ignore_index=True)

    @classmethod
    def saveDateToClickHouse(self):
        """
        保存期权日线数据到 ClickHouse
        """
        logger.info("saveDateToClickHouse started")

        try:
            # 定义 ClickHouse 表中所有字段
            table_columns = [
                'ts_code', 'trade_date', 'exchange',
                'pre_settle', 'pre_close', 'open', 'high', 'low',
                'close', 'settle', 'vol', 'amount', 'oi'
            ]

            # String 类型字段
            string_columns = ['ts_code', 'trade_date', 'exchange']

            # Float 类型字段
            numeric_columns = [
                'pre_settle', 'pre_close', 'open', 'high', 'low',
                'close', 'settle', 'vol', 'amount', 'oi'
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
                    self.dataFrame[col] = self.dataFrame[col].fillna('')
            for col in numeric_columns:
                if col in self.dataFrame.columns:
                    self.dataFrame[col] = self.dataFrame[col].fillna(0.0)

            insert_sql_statement = f'INSERT INTO indexsysdb.df_tushare_opt_daily ({", ".join(table_columns)}) VALUES'
            data = self.dataFrame.to_dict('records')
            self.clickhouseClient.execute(insert_sql_statement, data)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed")

    @classmethod
    def deleteDateFromClickHouse(self, ts_code="", start_date="", end_date=""):
        """
        从 ClickHouse 删除指定条件下的期权日线数据

        Args:
            ts_code: 合约代码（可选）
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        """
        logger.info("deleteDateFromClickHouse started")

        try:
            if ts_code and start_date and end_date:
                # 删除指定合约在指定日期范围的数据
                del_sql = "ALTER TABLE indexsysdb.df_tushare_opt_daily DELETE WHERE ts_code = '%s' AND trade_date >= '%s' AND trade_date <= '%s'" % (ts_code, start_date, end_date)
            elif ts_code:
                # 删除指定合约的所有数据
                del_sql = "ALTER TABLE indexsysdb.df_tushare_opt_daily DELETE WHERE ts_code = '%s'" % ts_code
            elif start_date and end_date:
                # 删除指定日期范围的所有数据
                del_sql = "ALTER TABLE indexsysdb.df_tushare_opt_daily DELETE WHERE trade_date >= '%s' AND trade_date <= '%s'" % (start_date, end_date)
            else:
                # 删除所有数据
                logger.warning("未指定删除条件，将删除所有数据")
                del_sql = "ALTER TABLE indexsysdb.df_tushare_opt_daily DELETE WHERE 1=1"

            logger.info(f"执行删除 SQL: {del_sql}")
            self.clickhouseClient.execute(del_sql)

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDateFromClickHouse completed")

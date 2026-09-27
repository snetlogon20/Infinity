import os
import time

import pandas as pd

from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib, CommonParameters
import pandas

logger = CommonLib.logger

class TuShareOptDailyService(TuShareService):

    # opt_daily 单次调用有行数上限（超出会被静默截断），按交易日全市场拉取时必须分页
    OPT_DAILY_PAGE_SIZE = 5000

    @classmethod
    def _fetch_opt_daily_by_date(self, trade_date_str, exchange=None):
        """
        按交易日分页拉取期权日线数据（全市场或单交易所），避免超过单次行数上限被截断

        Args:
            trade_date_str: 交易日期 YYYYMMDD
            exchange: 交易所（SSE/SZSE/CFFEX/DCE/SHFE/CZCE），None=全市场

        Returns:
            DataFrame: 该交易日全部行情数据，无数据时返回空 DataFrame
        """
        all_dfs = []
        offset = 0
        while True:
            df = self.pro.opt_daily(trade_date=trade_date_str, exchange=exchange,
                                    offset=offset, limit=self.OPT_DAILY_PAGE_SIZE)
            if df is None or df.empty:
                break
            all_dfs.append(df)
            if len(df) < self.OPT_DAILY_PAGE_SIZE:
                break
            offset += self.OPT_DAILY_PAGE_SIZE

        if not all_dfs:
            return pandas.DataFrame()
        return pandas.concat(all_dfs, ignore_index=True)

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
            if ts_code and trade_date:
                # 按合约代码 + 交易日期查询
                self.dataFrame = self.pro.opt_daily(
                    ts_code=ts_code,
                    trade_date=trade_date,
                    exchange=exchange
                )
                row_count = len(self.dataFrame)
                logger.info(f"成功获取期权 {ts_code} 在 {trade_date} 的日线数据，共 {row_count} 行")
            elif ts_code:
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
                df = self._fetch_opt_daily_by_date(date_str, exchange=exchange)
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
    def deleteDateFromClickHouseByTsCodeList(self, ts_code_list, trade_date):
        """
        按合约代码列表 + 交易日期精确删除 ClickHouse 数据

        Args:
            ts_code_list: 合约代码列表，如 ["HO2612-C-2500.CFX", "HO2612-C-2600.CFX"]
            trade_date: 交易日期 YYYYMMDD
        """
        logger.info("deleteDateFromClickHouseByTsCodeList started")

        try:
            if not ts_code_list or not trade_date:
                logger.warning("ts_code_list 或 trade_date 为空，跳过删除")
                return

            ts_code_conditions = "', '".join(ts_code_list)
            del_sql = "ALTER TABLE indexsysdb.df_tushare_opt_daily DELETE WHERE ts_code IN ('%s') AND trade_date = '%s'" % (ts_code_conditions, trade_date)
            logger.info(f"执行删除 SQL: {del_sql}")
            self.clickhouseClient.execute(del_sql)

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDateFromClickHouseByTsCodeList completed")

    @classmethod
    def deleteDateFromClickHouse(self, ts_code="", trade_date="", start_date="", end_date=""):
        """
        从 ClickHouse 删除指定条件下的期权日线数据

        Args:
            ts_code: 合约代码（可选）
            trade_date: 交易日期 YYYYMMDD（可选）
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）
        """
        logger.info("deleteDateFromClickHouse started")

        try:
            if ts_code and trade_date:
                # 按 ts_code + trade_date 删除
                del_sql = "ALTER TABLE indexsysdb.df_tushare_opt_daily DELETE WHERE ts_code = '%s' AND trade_date = '%s'" % (ts_code, trade_date)
            elif ts_code and start_date and end_date:
                # 删除指定合约在指定日期范围的数据
                del_sql = "ALTER TABLE indexsysdb.df_tushare_opt_daily DELETE WHERE ts_code = '%s' AND trade_date >= '%s' AND trade_date <= '%s'" % (ts_code, start_date, end_date)
            elif ts_code:
                # 删除指定合约的所有数据
                del_sql = "ALTER TABLE indexsysdb.df_tushare_opt_daily DELETE WHERE ts_code = '%s'" % ts_code
            elif trade_date:
                # 按 trade_date 删除全天的数据
                del_sql = "ALTER TABLE indexsysdb.df_tushare_opt_daily DELETE WHERE trade_date = '%s'" % trade_date
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

    @classmethod
    def refresh_opt_daily(self, ts_code=None, trade_date=None, start_date=None, end_date=None, exchange=None):
        """
        刷新期权日线行情数据

        Args:
            ts_code: TS合约代码（可选）
            trade_date: 交易日期 (YYYYMMDD)（可选）
            start_date: 开始日期 (YYYYMMDD)（可选）
            end_date: 结束日期 (YYYYMMDD)（可选）
            exchange: 交易所(SSE/SZSE/CFFEX/DCE/SHFE/CZCE)（可选）
        """
        try:
            csvFilePath = os.path.join(CommonParameters.outBoundPath, "df_tushare_opt_daily.csv")

            tuShareService = TuShareOptDailyService()

            logger.info(f"开始获取期权日线数据...")
            logger.info(f"  - ts_code: {ts_code}")
            logger.info(f"  - trade_date: {trade_date}")
            logger.info(f"  - 日期范围: {start_date} ~ {end_date}")
            logger.info(f"  - exchange: {exchange}")

            # 获取数据
            dataFrame = tuShareService.prepareDataFrame(
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date,
                exchange=exchange
            )

            if dataFrame.empty:
                logger.warning("期权日线数据为空，跳过处理")
                return

            logger.info(f"获取到 {len(dataFrame)} 条期权日线记录")

            # 保存到 CSV
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            logger.info(f"数据已保存到: {csvFilePath}")

            # 先删除旧数据，再插入新数据
            logger.info("开始删除 ClickHouse 中的旧数据...")
            tuShareService.deleteDateFromClickHouse(
                ts_code=ts_code if ts_code else "",
                trade_date=trade_date if trade_date else "",
                start_date=start_date if start_date else "",
                end_date=end_date if end_date else ""
            )

            logger.info("开始保存数据到 ClickHouse...")
            tuShareService.saveDateToClickHouse()

            logger.info(f"✅ 期权日线数据处理完成，共 {len(dataFrame)} 条记录")

        except Exception as e:
            logger.error(f"❌ 期权日线数据处理失败：{str(e)}")
            import traceback
            logger.error(traceback.format_exc())

    @classmethod
    def refresh_opt_daily_by_ts_code_list(self, ts_code_list, trade_date_list, exchange=""):
        """
        批量获取期权日线数据（推荐方式，效率高）

        每个交易日只调用一次 API（按 trade_date + exchange 拉全量），
        在内存中过滤目标合约，最后一次性存入 ClickHouse。

        Args:
            ts_code_list: 目标合约代码列表
            trade_date_list: 交易日期列表
            exchange: 交易所，默认空串表示全交易所
        """
        logger.info(f"批量查询期权日线数据: {len(ts_code_list)} 个合约 x {len(trade_date_list)} 个交易日")

        all_dfs = []
        tuShareService = TuShareOptDailyService()

        for i, trade_date_str in enumerate(trade_date_list):
            try:
                logger.info(f"  [{i + 1}/{len(trade_date_list)}] 获取 {trade_date_str} 的全量期权日线数据...")
                df = tuShareService._fetch_opt_daily_by_date(trade_date_str, exchange=exchange)
                if df.empty:
                    logger.warning(f"  {trade_date_str} 获取数据为空，跳过")
                    continue

                # 过滤目标合约
                df_filtered = df[df['ts_code'].isin(ts_code_list)]
                logger.info(f"  全量 {len(df)} 条 -> 过滤后 {len(df_filtered)} 条")

                if not df_filtered.empty:
                    all_dfs.append(df_filtered)

                time.sleep(0.3)
            except Exception as e:
                logger.warning(f"  {trade_date_str} 获取失败: {e}")
                time.sleep(0.5)

        if not all_dfs:
            logger.warning("所有日期均未获取到目标合约数据，跳过")
            return 0

        # 合并所有数据
        dataFrame = pd.concat(all_dfs, ignore_index=True)
        logger.info(f"合并后共 {len(dataFrame)} 条记录")

        # 设置到类级别（因为 saveDateToClickHouse 是 @classmethod，需类属性）
        cls_ref = type(tuShareService)
        cls_ref.dataFrame = dataFrame

        # 确保列名一致
        expected_columns = [
            'ts_code', 'trade_date', 'exchange',
            'pre_settle', 'pre_close', 'open', 'high', 'low',
            'close', 'settle', 'vol', 'amount', 'oi'
        ]
        available_columns = [col for col in expected_columns if col in cls_ref.dataFrame.columns]
        cls_ref.dataFrame = cls_ref.dataFrame[available_columns]

        # 删除旧数据（按每个交易日 + 合约列表精确删除）
        logger.info("开始删除 ClickHouse 中的旧数据...")
        for trade_date_str in trade_date_list:
            try:
                tuShareService.deleteDateFromClickHouseByTsCodeList(
                    ts_code_list=ts_code_list,
                    trade_date=trade_date_str
                )
            except Exception as e:
                logger.warning(f"删除 {trade_date_str} 旧数据失败: {e}")

        # 一次性保存到 ClickHouse
        logger.info("开始保存数据到 ClickHouse...")
        cls_ref.saveDateToClickHouse()

        logger.info(f"✅ 批量期权日线数据处理完成，共 {len(dataFrame)} 条记录")
        return len(dataFrame)


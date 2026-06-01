from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib
import pandas

logger = CommonLib.logger

class TuShareConvertBondDailyService(TuShareService):

    @classmethod
    def prepareDataFrame(self, ts_code=None, start_date=None, end_date=None):
        """
        获取可转债日线行情数据
        
        Args:
            ts_code: 转债代码（可选）
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            DataFrame with cb_daily data
        """
        logger.info("prepareData started")

        try:
            # 如果指定了 ts_code，直接获取
            if ts_code:
                self.dataFrame = self.pro.cb_daily(
                    ts_code=ts_code, 
                    start_date=start_date, 
                    end_date=end_date
                )
                row_count = len(self.dataFrame)
                logger.info(f"成功获取可转债 {ts_code} 的日线数据，共 {row_count} 行")
            else:
                # 如果不指定 ts_code，需要先获取所有可转债代码，然后分批拉取
                logger.info("未指定转债代码，将获取所有可转债的日线数据...")
                self.dataFrame = self._fetch_all_cb_daily(start_date, end_date)
                row_count = len(self.dataFrame)
                logger.info(f"成功获取所有可转债日线数据，共 {row_count} 行")
            
            # 确保列名与数据库定义一致
            expected_columns = [
                'ts_code', 'trade_date', 'pre_close', 'open', 'high', 'low', 
                'close', 'change', 'pct_chg', 'vol', 'amount',
                'bond_value', 'bond_over_rate', 'cb_value', 'cb_over_rate'
            ]
            
            # 只保留接口实际返回的列
            available_columns = [col for col in expected_columns if col in self.dataFrame.columns]
            self.dataFrame = self.dataFrame[available_columns]
            
            logger.info(f"数据列: {available_columns}")

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")
        return self.dataFrame
    
    @classmethod
    def _fetch_all_cb_daily(self, start_date, end_date):
        """
        分批获取所有可转债的日线数据（按日期分片，解决 2000 条限制）
        
        说明：cb_daily 接口不支持逗号分隔的多代码批查询，因此按日期范围分片，
        每次查询一小段时间内的所有可转债数据，避免超过 2000 条限制。
        
        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
        
        Returns:
            合并后的 DataFrame
        """
        from datetime import datetime, timedelta
        import time
        from dataIntegrator.TuShareService.TuShareConvertBondBasicService import TuShareConvertBondBasicService
        
        logger.info("步骤1: 获取所有可转债基础信息...")
        basic_service = TuShareConvertBondBasicService()
        basic_df = basic_service.prepareDataFrame()
        
        if basic_df.empty:
            logger.warning("未获取到可转债基础信息，仍尝试按日期拉取日线数据...")
        
        all_codes = basic_df['ts_code'].tolist() if not basic_df.empty else []
        logger.info(f"共找到 {len(all_codes)} 个可转债")
        
        # 按日期范围分片拉取，每次 2 天，避免超过 2000 条限制
        # （假设每天 ~500-1000 个可转债有交易数据）
        start_dt = datetime.strptime(start_date, "%Y%m%d")
        end_dt = datetime.strptime(end_date, "%Y%m%d")
        chunk_days = 2
        
        all_dfs = []
        batch_no = 0
        current_start = start_dt
        
        while current_start <= end_dt:
            batch_no += 1
            chunk_end = min(current_start + timedelta(days=chunk_days - 1), end_dt)
            chunk_start_str = current_start.strftime("%Y%m%d")
            chunk_end_str = chunk_end.strftime("%Y%m%d")
            
            try:
                logger.info(f"步骤2: 拉取第 {batch_no} 批 (日期: {chunk_start_str} ~ {chunk_end_str})...")
                
                batch_df = self.pro.cb_daily(
                    start_date=chunk_start_str,
                    end_date=chunk_end_str
                )
                
                if not batch_df.empty:
                    all_dfs.append(batch_df)
                    daily_count = len(batch_df)
                    code_count = batch_df['ts_code'].nunique() if 'ts_code' in batch_df.columns else 0
                    logger.info(f"  ✓ 本批获取 {daily_count} 条记录，覆盖 {code_count} 个转债")
                else:
                    logger.info(f"  ✗ 该日期范围无数据（可能为非交易日）")
                
                # 避免频繁请求导致限流
                time.sleep(0.3)
                
            except Exception as e:
                logger.error(f"  ✗ 第 {batch_no} 批失败: {e}")
                time.sleep(0.5)
                continue
            
            current_start = chunk_end + timedelta(days=1)
        
        if not all_dfs:
            logger.error("所有日期范围均未获取到数据")
            return pandas.DataFrame()
        
        # 合并所有批次的数据
        final_df = pandas.concat(all_dfs, ignore_index=True)
        total_codes = final_df['ts_code'].nunique() if 'ts_code' in final_df.columns else 0
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ 数据拉取完成")
        logger.info(f"   - 总转债数 (基础信息): {len(all_codes)}")
        logger.info(f"   - 总转债数 (日线数据): {total_codes}")
        logger.info(f"   - 总记录数: {len(final_df)}")
        logger.info(f"   - 总批次数: {batch_no}")
        logger.info(f"{'='*80}")
        
        return final_df

    @classmethod
    def saveDateToClickHouse(self):
        """
        保存可转债日线数据到 ClickHouse
        """
        logger.info("saveDateToClickHouse started")

        try:
            # 定义 ClickHouse 表中所有字段
            table_columns = [
                'ts_code', 'trade_date', 'pre_close', 'open', 'high', 'low', 
                'close', 'change', 'pct_chg', 'vol', 'amount',
                'bond_value', 'bond_over_rate', 'cb_value', 'cb_over_rate'
            ]
            
            # 获取 DataFrame 中实际存在的列
            actual_columns = self.dataFrame.columns.tolist()
            
            # 为缺少的列填充默认值（可选字段用 0.0）
            optional_columns = ['bond_value', 'bond_over_rate', 'cb_value', 'cb_over_rate']
            for col in table_columns:
                if col not in actual_columns:
                    if col in optional_columns:
                        self.dataFrame[col] = 0.0  # 可选数值字段用 0
                    else:
                        logger.warning(f"缺少必需字段: {col}")
            
            # 按表结构顺序重新排列列
            columns_to_save = [col for col in table_columns if col in self.dataFrame.columns]
            self.dataFrame = self.dataFrame[columns_to_save]
            
            # 处理 NaN 值
            numeric_columns = [
                'pre_close', 'open', 'high', 'low', 'close', 'change', 
                'pct_chg', 'vol', 'amount', 'bond_value', 'bond_over_rate', 
                'cb_value', 'cb_over_rate'
            ]
            for col in numeric_columns:
                if col in self.dataFrame.columns:
                    self.dataFrame[col] = self.dataFrame[col].fillna(0.0)
            
            # 构建 INSERT 语句
            columns_str = ', '.join(columns_to_save)
            insert_sql = f'INSERT INTO indexsysdb.df_tushare_cb_daily ({columns_str}) VALUES'
            
            logger.info(f"执行 SQL: {insert_sql}")
            logger.info(f"准备保存 {len(self.dataFrame)} 条记录")
            
            data = self.dataFrame.to_dict('records')
            self.clickhouseClient.execute(insert_sql, data)
            
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed")

    @classmethod
    def deleteDateFromClickHouse(self, ts_code="", start_date="00000000", end_date="00000000"):
        """
        从 ClickHouse 删除指定条件下的可转债日线数据
        
        Args:
            ts_code: 转债代码
            start_date: 开始日期
            end_date: 结束日期
        """
        logger.info("deleteDateFromClickHouse started")

        try:
            if ts_code and start_date != "00000000" and end_date != "00000000":
                # 删除指定转债在指定日期范围的数据
                del_sql = "ALTER TABLE indexsysdb.df_tushare_cb_daily DELETE WHERE ts_code = '%s' AND trade_date >= '%s' AND trade_date <= '%s'" % (ts_code, start_date, end_date)
            elif ts_code:
                # 删除指定转债的所有数据
                del_sql = "ALTER TABLE indexsysdb.df_tushare_cb_daily DELETE WHERE ts_code = '%s'" % ts_code
            elif start_date != "00000000" and end_date != "00000000":
                # 删除指定日期范围的所有数据
                del_sql = "ALTER TABLE indexsysdb.df_tushare_cb_daily DELETE WHERE trade_date >= '%s' AND trade_date <= '%s'" % (start_date, end_date)
            else:
                # 删除所有数据（谨慎使用）
                logger.warning("未指定删除条件，将删除所有数据")
                del_sql = "ALTER TABLE indexsysdb.df_tushare_cb_daily DELETE WHERE 1=1"
            
            logger.info(f"执行删除 SQL: {del_sql}")
            self.clickhouseClient.execute(del_sql)
            
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDateFromClickHouse completed")

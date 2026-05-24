from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib

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
            # 调用 TuShare cb_daily 接口
            if ts_code:
                self.dataFrame = self.pro.cb_daily(
                    ts_code=ts_code, 
                    start_date=start_date, 
                    end_date=end_date
                )
            else:
                # 如果不指定 ts_code，则获取所有可转债的日线数据
                self.dataFrame = self.pro.cb_daily(
                    start_date=start_date, 
                    end_date=end_date
                )

            row_count = len(self.dataFrame)
            logger.info(f"成功获取可转债日线数据，共 {row_count} 行")
            
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

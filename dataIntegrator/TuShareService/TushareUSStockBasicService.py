from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
import pandas as pd
from dataIntegrator import CommonLib

logger = CommonLib.logger

class TushareUSStockBasicService(TuShareService):
    @classmethod
    @classmethod
    def prepareDataFrame(self, start_date=None, end_date=None, symbol_filter=None, offset=None, limit=None):
        logger.info("prepareData started")

        try:
            if symbol_filter:
                df = self.pro.us_basic(symbol=symbol_filter)
                logger.info(f"获取美股基本信息 - 过滤条件: {symbol_filter}")
            elif offset is not None and limit is not None:
                df = self.pro.us_basic(offset=offset, limit=limit)
                logger.info(f"获取美股基本信息 - offset: {offset}, limit: {limit}")
            else:
                df = self.pro.us_basic()
                logger.info("获取全部美股基本信息")

            logger.info(f"原始数据 shape: {str(df.shape)}")
            logger.info(f"原始数据列名: {df.columns.tolist()}")
            logger.info(f"原始数据前3行:\n{df.head(3)}")

            # 重命名字段以匹配数据库表结构
            column_mapping = {
                'ts_code': 'ts_code',
                'name': 'name',
                'enname': 'enname',
                'classify': 'classify',
                'list_date': 'list_date',
                'delist_date': 'delist_date'
            }

            # 只保留需要的列并重命名
            existing_columns = [col for col in column_mapping.keys() if col in df.columns]
            df = df[existing_columns].rename(columns=column_mapping)

            # 确保所有必需的列都存在
            required_columns = ['ts_code', 'name', 'enname', 'classify', 'list_date', 'delist_date']
            for col in required_columns:
                if col not in df.columns:
                    df[col] = None
                    logger.warning(f"缺少列 {col}，已添加空列")

            self.dataFrame = df
            logger.info(f"处理后数据 shape: {str(self.dataFrame.shape)}")
            logger.info(f"处理后数据列名: {self.dataFrame.columns.tolist()}")

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")

        return self.dataFrame

    @classmethod
    def prepareAllDataFrames(self):
        """
        使用分页方式获取所有美股基本信息
        通过 offset 和 limit 参数循环拉取，突破单次接口返回数量限制
        """
        logger.info("prepareAllDataFrames started - 开始分页获取美股基本信息")

        all_dataframes = []
        limit = 5000  # 每页拉取 5000 条，留有余量避免触发接口限制
        offset = 0
        page_num = 1

        while True:
            try:
                logger.info(f"正在获取第 {page_num} 页数据 (offset={offset}, limit={limit})...")

                df = self.prepareDataFrame(start_date=None, end_date=None, offset=offset, limit=limit)

                if df.empty:
                    logger.info(f"第 {page_num} 页数据为空，已全部获取完成")
                    break

                all_dataframes.append(df)
                logger.info(f"成功获取第 {page_num} 页数据: {len(df)} 条")

                # 如果返回数据少于 limit，说明已经是最后一页
                if len(df) < limit:
                    logger.info(f"返回数据 ({len(df)}) 少于 limit ({limit})，已是最后一页")
                    break

                offset += limit
                page_num += 1

                # 避免请求过快，适当延迟
                import time
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"获取第 {page_num} 页数据失败: {e}")
                break

        if all_dataframes:
            combined_df = pd.concat(all_dataframes, ignore_index=True)

            # 去重：基于 ts_code
            before_count = len(combined_df)
            combined_df = combined_df.drop_duplicates(subset=['ts_code'], keep='first')
            after_count = len(combined_df)

            logger.info(f"合并完成，去重前: {before_count} 条，去重后: {after_count} 条")
            logger.info(f"最终有效数据（ts_code 非空）: {combined_df['ts_code'].notna().sum()} 条")

            # 关键修复：将合并后的完整数据赋值给 self.dataFrame，确保 saveDateToClickHouse 能保存所有数据
            self.dataFrame = combined_df

            return combined_df
        else:
            logger.error("未能获取任何美股数据")
            return pd.DataFrame()

    @classmethod
    def saveDateToClickHouse(self):
        logger.info("saveDateToClickHouse started")

        try:
            # 数据清洗：将 None 替换为 'Nan'
            self.dataFrame = self.dataFrame.replace({None: "Nan"})
            self.dataFrame = self.dataFrame.fillna("Nan")

            # 确保 delist_date 列存在
            if "delist_date" not in self.dataFrame.columns:
                self.dataFrame["delist_date"] = "Nan"

            # 过滤掉 ts_code 为空的记录
            valid_df = self.dataFrame[self.dataFrame['ts_code'].notna() & (self.dataFrame['ts_code'] != 'Nan')]

            logger.info(f"准备保存的数据量: {len(valid_df)} 条（已过滤 ts_code 为空的记录）")
            logger.info(f"保存前数据样例:\n{valid_df.head(3)}")

            if valid_df.empty:
                logger.error("没有有效数据可保存！")
                return

            insert_sql_statement = 'INSERT INTO indexsysdb.df_tushare_us_stock_basic (ts_code,name,enname,classify,list_date,delist_date) VALUES'
            data = valid_df.to_dict('records')
            self.clickhouseClient.execute(insert_sql_statement, data)

            logger.info(f"成功保存 {len(data)} 条记录到 ClickHouse")

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed")

    @classmethod
    def deleteDateFromClickHouse(self, start_date=None, end_date=None):
        logger.info("deleteDataFromClickHouse started")

        try:
            del_df_tushare_sql = "ALTER TABLE indexsysdb.df_tushare_us_stock_basic DELETE where ts_code is not Null"

            self.clickhouseClient.execute(del_df_tushare_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDateFromClickHouse completed")

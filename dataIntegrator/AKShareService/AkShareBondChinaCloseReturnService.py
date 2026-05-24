import pandas
import os
import requests
from datetime import datetime

from dataIntegrator import CommonLib
from dataIntegrator.AKShareService.AkShareService import AkShareService
import sys
logger = CommonLib.logger

class AkShareBondChinaCloseReturnService(AkShareService):

    def prepareDataFrame(self, start_date: str = None, end_date: str = None, period: str = "1"):
        """
        从 AKShare API 获取中国债券收益率曲线数据
        
        Args:
            start_date: 开始日期 (YYYYMMDD)，默认为当前日期前1个月
            end_date: 结束日期 (YYYYMMDD)，默认为当前日期
            period: 期限间隔 ('0.1', '0.5', '1')，默认为'1'
            
        Returns:
            合并后的DataFrame，包含所有债券类型的数据
        """
        logger.info("prepareData started")

        try:
            # 设置默认日期范围（最近1个月）
            if end_date is None:
                end_date = datetime.now().strftime("%Y%m%d")
            if start_date is None:
                # 计算一个月前的日期
                from dateutil.relativedelta import relativedelta
                start_dt = datetime.now() - relativedelta(months=1)
                start_date = start_dt.strftime("%Y%m%d")
            
            logger.info(f"查询日期范围: {start_date} ~ {end_date}, 期限: {period}")
            
            # 1. 获取所有债券类型映射表
            name_code_df = self.ak.bond_china_close_return_map()
            all_bonds = name_code_df['cnLabel'].values.tolist()
            
            logger.info(f"共找到 {len(all_bonds)} 种债券类型: {all_bonds}")
            
            if not all_bonds:
                logger.warning("未找到任何债券类型")
                return pandas.DataFrame()
            
            # 2. 遍历所有债券类型，获取数据
            df_list = []
            success_count = 0
            failed_count = 0
            failed_bonds = []
            
            for idx, symbol in enumerate(all_bonds, 1):
                try:
                    logger.info(f"正在获取第 {idx}/{len(all_bonds)} 个债券: {symbol}")
                    
                    # 查找债券代码
                    match = name_code_df[name_code_df["cnLabel"] == symbol]
                    if len(match) == 0:
                        logger.warning(f"未找到债券类型: {symbol}")
                        failed_count += 1
                        failed_bonds.append(symbol)
                        continue
                    
                    symbol_code = match["value"].values[0]
                    logger.info(f"✓ 找到债券代码: {symbol_code} ({symbol})")
                    
                    # 构造 API 请求
                    url = "https://www.chinamoney.com.cn/ags/ms/cm-u-bk-currency/ClsYldCurvHis"
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/108.0.0.0 Safari/537.36",
                    }
                    params = {
                        "lang": "CN",
                        "reference": "1,2,3",
                        "bondType": symbol_code,
                        "startDate": "-".join([start_date[:4], start_date[4:6], start_date[6:]]),
                        "endDate": "-".join([end_date[:4], end_date[4:6], end_date[6:]]),
                        "termId": period,
                        "pageNum": "1",
                        "pageSize": "50",
                    }
                    
                    response = requests.get(url, params=params, headers=headers)
                    response.raise_for_status()
                    data_json = response.json()
                    
                    # 解析数据
                    temp_df = pandas.DataFrame(data_json["records"])
                    
                    # 【关键修复】安全地删除 newDateValue 列（如果存在）
                    if "newDateValue" in temp_df.columns:
                        del temp_df["newDateValue"]
                        logger.info("✓ 已删除 newDateValue 列")
                    
                    # 重命名列
                    expected_columns = ["日期", "期限", "到期收益率", "即期收益率", "远期收益率"]
                    if len(temp_df.columns) >= len(expected_columns):
                        temp_df.columns = expected_columns
                    else:
                        logger.warning(f"⚠ 警告: 返回列数 ({len(temp_df.columns)}) 与预期 ({len(expected_columns)}) 不匹配")
                        logger.warning(f"   实际列名: {list(temp_df.columns)}")
                        failed_count += 1
                        failed_bonds.append(symbol)
                        continue
                    
                    # 添加债券名称列
                    temp_df["债券类型"] = symbol
                    temp_df["债券代码"] = symbol_code
                    
                    # 调整列顺序
                    temp_df = temp_df[["债券类型", "债券代码", "日期", "期限", "到期收益率", "即期收益率", "远期收益率"]]
                    
                    # 数据类型转换
                    temp_df["日期"] = pandas.to_datetime(temp_df["日期"], errors="coerce").dt.date
                    temp_df["期限"] = pandas.to_numeric(temp_df["期限"], errors="coerce")
                    temp_df["到期收益率"] = pandas.to_numeric(temp_df["到期收益率"], errors="coerce")
                    temp_df["即期收益率"] = pandas.to_numeric(temp_df["即期收益率"], errors="coerce")
                    temp_df["远期收益率"] = pandas.to_numeric(temp_df["远期收益率"], errors="coerce")
                    
                    logger.info(f"✓ 成功获取 {symbol}: {len(temp_df)} 条记录")
                    df_list.append(temp_df)
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"✗ 获取债券 {symbol} 失败: {type(e).__name__}: {e}")
                    failed_count += 1
                    failed_bonds.append(symbol)
                    continue
            
            if not df_list:
                logger.error("没有成功获取任何债券数据")
                return pandas.DataFrame()
            
            # 合并所有DataFrame
            dataFrame = pandas.concat(df_list, ignore_index=True)
            
            logger.info(f"合并后数据 Shape: {dataFrame.shape}")
            logger.info(f"合并后数据列数: {len(dataFrame.columns)}")
            logger.info(f"合并后数据列名: {list(dataFrame.columns)}")
            logger.info(f"合并后数据类型:\n{dataFrame.dtypes}")
            logger.info(f"合并后数据前3行:\n{dataFrame.head(3)}")
            logger.info(f"合并后数据后3行:\n{dataFrame.tail(3)}")
            
            # 统计不同债券类型的数量
            if '债券类型' in dataFrame.columns:
                bond_type_counts = dataFrame['债券类型'].value_counts()
                logger.info(f"债券类型分布:\n{bond_type_counts}")
            
            # 打印统计信息
            logger.info(f"=" * 80)
            logger.info(f"数据获取完成统计")
            logger.info(f"总计: {len(all_bonds)} 种债券")
            logger.info(f"成功: {success_count} 种")
            logger.info(f"失败: {failed_count} 种")
            if failed_bonds:
                logger.info(f"失败的债券类型: {failed_bonds}")
            logger.info(f"=" * 80)

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")
        return dataFrame

    def transformDataFrame(self, dataFrame: pandas.core.frame.DataFrame):
        """
        数据转换：日期格式转换、排序、缺失值处理
        
        Args:
            dataFrame: 原始DataFrame
            
        Returns:
            转换后的DataFrame
        """
        logger.info("transformData started")

        try:
            # 确保列名为英文（与数据库字段对应）
            column_mapping = {
                '债券类型': 'bond_type',
                '债券代码': 'bond_code',
                '日期': 'date',
                '期限': 'tenor',
                '到期收益率': 'yield_to_maturity',
                '即期收益率': 'spot_rate',
                '远期收益率': 'forward_rate'
            }
            
            # 重命名列
            existing_columns = {k: v for k, v in column_mapping.items() if k in dataFrame.columns}
            if existing_columns:
                dataFrame = dataFrame.rename(columns=existing_columns)
                logger.info(f"已重命名列: {list(existing_columns.values())}")
            
            # 数据预处理：转换日期列为datetime.date对象（ClickHouse Date类型需要）
            if 'date' in dataFrame.columns:
                # 如果已经是datetime类型，转换为date对象
                if pandas.api.types.is_datetime64_any_dtype(dataFrame['date']):
                    dataFrame['date'] = dataFrame['date'].dt.date
                else:
                    # 尝试转换为datetime再转为date对象
                    dataFrame['date'] = pandas.to_datetime(dataFrame['date'], errors='coerce').dt.date
                
                logger.info(f"日期列转换完成，示例: {dataFrame['date'].head(3).tolist()}")
            
            # 按债券代码和日期排序
            sort_columns = [col for col in ['bond_code', 'date', 'tenor'] if col in dataFrame.columns]
            if sort_columns:
                dataFrame = dataFrame.sort_values(sort_columns).reset_index(drop=True)
                logger.info(f"已按 {sort_columns} 排序")
            
            # 数值列处理：将NaN替换为None或保持NaN（ClickHouse可以处理）
            numeric_columns = ['tenor', 'yield_to_maturity', 'spot_rate', 'forward_rate']
            for col in numeric_columns:
                if col in dataFrame.columns:
                    dataFrame[col] = pandas.to_numeric(dataFrame[col], errors='coerce')
                    null_count = dataFrame[col].isna().sum()
                    if null_count > 0:
                        logger.info(f"列 {col} 有 {null_count} 个空值")
            
            # 打印转换后的数据信息
            logger.info(f"转换后数据 Shape: {dataFrame.shape}")
            logger.info(f"转换后数据列名: {list(dataFrame.columns)}")
            logger.info(f"转换后数据类型:\n{dataFrame.dtypes}")
            logger.info(f"转换后数据前3行:\n{dataFrame.head(3)}")

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("transformData completed")
        return dataFrame

    def saveDateToClickHouse(self, dataFrame):
        """
        保存数据到ClickHouse
        
        Args:
            dataFrame: 要保存的DataFrame
        """
        logger.info("saveDateToClickHouse started")

        try:
            # 显示数据信息用于调试
            logger.info(f"准备保存的数据列: {list(dataFrame.columns)}")
            logger.info(f"数据类型: {dataFrame.dtypes}")
            logger.info(f"数据形状: {dataFrame.shape}")
            logger.info(f"前几行数据:\n{dataFrame.head()}")
            logger.info(f"后几行数据:\n{dataFrame.tail()}")

            # 确保只保存数据库表中存在的列
            db_columns = ['bond_type', 'bond_code', 'date', 'tenor', 'yield_to_maturity', 'spot_rate', 'forward_rate']
            columns_to_save = [col for col in db_columns if col in dataFrame.columns]

            # 创建要保存的数据副本
            dataFrame_to_save = dataFrame[columns_to_save].copy()

            # 确保数据类型正确
            # 注意：ClickHouse Date类型需要datetime.date对象，不是字符串
            if 'tenor' in dataFrame_to_save.columns:
                dataFrame_to_save['tenor'] = dataFrame_to_save['tenor'].fillna(0).astype('float64')
            if 'yield_to_maturity' in dataFrame_to_save.columns:
                dataFrame_to_save['yield_to_maturity'] = dataFrame_to_save['yield_to_maturity'].fillna(0).astype('float64')
            if 'spot_rate' in dataFrame_to_save.columns:
                dataFrame_to_save['spot_rate'] = dataFrame_to_save['spot_rate'].fillna(0).astype('float64')
            if 'forward_rate' in dataFrame_to_save.columns:
                dataFrame_to_save['forward_rate'] = dataFrame_to_save['forward_rate'].fillna(0).astype('float64')

            logger.info(f"实际保存的列: {list(dataFrame_to_save.columns)}")
            logger.info(f"保存前数据类型: {dataFrame_to_save.dtypes}")

            # 使用明确的列名插入语句
            columns_str = ', '.join(columns_to_save)
            insert_sql = f"INSERT INTO indexsysdb.df_akshare_bond_china_close_return ({columns_str}) VALUES"

            logger.info(f"执行的SQL: {insert_sql}")

            self.saveAkDateToClickHouse(insert_sql, dataFrame_to_save)
            
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed: %s", insert_sql)

        return

    def deleteDateFromClickHouse(self, bond_type=None):
        """
        从ClickHouse删除指定债券类型的数据
        
        Args:
            bond_type: 债券类型，如果为None则不删除任何数据
        """
        logger.info("deleteDataFromClickHouse started")

        try:
            if bond_type:
                del_sql = "ALTER TABLE indexsysdb.df_akshare_bond_china_close_return DELETE where bond_type='%s'" % (bond_type)
            else:
                # 如果不指定债券类型，可以删除所有数据（谨慎使用）
                logger.warning("未指定债券类型，将删除所有数据")
                del_sql = "ALTER TABLE indexsysdb.df_akshare_bond_china_close_return DELETE where 1=1"
            
            self.deleteAkDateFromClickHouse(del_sql)

            # 等待 mutation 完成（ClickHouse DELETE 是异步的）
            self._wait_for_mutation_complete()
            
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDataFromClickHouse completed: %s", del_sql)

        return

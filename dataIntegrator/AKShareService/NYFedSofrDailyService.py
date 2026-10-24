import sys

import pandas
import requests

from dataIntegrator import CommonLib
from dataIntegrator.AKShareService.AkShareService import AkShareService

logger = CommonLib.logger


class NYFedSofrDailyService(AkShareService):
    """纽约联储 SOFR（担保隔夜融资利率）日线数据服务。

    数据源为纽约联储公开 REST API（非 akshare），核心抓取逻辑：
        GET https://markets.newyorkfed.org/api/rates/secured/sofr/last/{days}.json
        返回 JSON 的 ``refRates`` 数组，逐条含 effectiveDate / percentRate / volume。

    入库管线（prepare -> transform -> save）沿用 :class:`AkShareService` 的
    ClickHouse 辅助方法，风格与 ``AkShareStockUsDailyService`` 保持一致。
    """

    # 纽约联储 SOFR 接口前缀，last/{days}.json 表示取最近 days 天
    _API_URL = "https://markets.newyorkfed.org/api/rates/secured/sofr/last/{days}.json"

    def prepareDataFrame(self, days=30):
        logger.info("prepareData started")

        try:
            url = self._API_URL.format(days=days)
            logger.info("请求 URL: %s", url)

            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # refRates 为参考利率数组；接口无数据时可能缺失该键
            rows = response.json().get("refRates", [])
            logger.info("原始记录条数: %s", len(rows))

            # 核心逻辑：把每条 refRate 抽取为标准列
            dataFrame = pandas.DataFrame([{
                "date": x["effectiveDate"],        # 生效日期，形如 YYYYMMDD
                "sofr": x["percentRate"],          # SOFR 年化百分比利率
                "volume_bn": x.get("volume"),      # 交易量（百万美元）
            } for x in rows])

            if dataFrame.empty:
                logger.warning("接口未返回任何 SOFR 数据，days=%s", days)
                return dataFrame

            # 打印原始数据结构用于调试
            logger.info(f"原始数据 Shape: {dataFrame.shape}")
            logger.info(f"原始数据列名: {list(dataFrame.columns)}")
            logger.info(f"原始数据类型:\n{dataFrame.dtypes}")
            logger.info(f"原始数据前3行:\n{dataFrame.head(3)}")

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")
        return dataFrame

    def transformDataFrame(self, dataFrame: pandas.core.frame.DataFrame):
        logger.info("transformData started")

        try:
            if dataFrame is None or dataFrame.empty:
                logger.warning("transformData 输入为空，直接返回")
                return dataFrame

            # 日期归一化：兼容 YYYY-MM-DD 与 YYYYMMDD，统一为 YYYY-MM-DD 字符串
            date_str = dataFrame["date"].astype(str).str.replace("-", "", regex=False)
            dataFrame["date"] = pandas.to_datetime(
                date_str, format="%Y%m%d"
            ).dt.strftime("%Y-%m-%d")

            # 数值列类型转换
            dataFrame["sofr"] = dataFrame["sofr"].astype("float64")
            dataFrame["volume_bn"] = pandas.to_numeric(
                dataFrame["volume_bn"], errors="coerce"
            ).fillna(0).astype("float64")

            # 按日期升序排序，确保变动计算正确
            dataFrame = dataFrame.sort_values("date").reset_index(drop=True)

            # 计算 SOFR 环比变动（基点）：(当期 - 前一期) * 100
            dataFrame["sofr_change_bp"] = dataFrame["sofr"].diff() * 100
            dataFrame["sofr_change_bp"] = dataFrame["sofr_change_bp"].fillna(0).astype("float64")

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("transformData completed")
        return dataFrame

    def saveDateToClickHouse(self, dataFrame):
        logger.info("saveDateToClickHouse started")

        try:
            # 显示数据信息用于调试
            logger.info(f"准备保存的数据列: {list(dataFrame.columns)}")
            logger.info(f"数据类型: {dataFrame.dtypes}")
            logger.info(f"数据形状: {dataFrame.shape}")
            logger.info(f"前几行数据:\n{dataFrame.head()}")
            logger.info(f"后几行数据:\n{dataFrame.tail()}")

            # 确保只保存数据库表中存在的列，并且数据类型正确
            db_columns = ['date', 'sofr', 'volume_bn', 'sofr_change_bp']
            columns_to_save = [col for col in db_columns if col in dataFrame.columns]

            # 创建要保存的数据副本
            dataFrame_to_save = dataFrame[columns_to_save].copy()

            # 确保数据类型正确
            if 'date' in dataFrame_to_save.columns:
                dataFrame_to_save['date'] = dataFrame_to_save['date'].astype(str)
            if 'sofr' in dataFrame_to_save.columns:
                dataFrame_to_save['sofr'] = dataFrame_to_save['sofr'].fillna(0).astype('float64')
            if 'volume_bn' in dataFrame_to_save.columns:
                dataFrame_to_save['volume_bn'] = dataFrame_to_save['volume_bn'].fillna(0).astype('float64')
            if 'sofr_change_bp' in dataFrame_to_save.columns:
                dataFrame_to_save['sofr_change_bp'] = dataFrame_to_save['sofr_change_bp'].fillna(0).astype('float64')

            logger.info(f"实际保存的列: {list(dataFrame_to_save.columns)}")
            logger.info(f"保存前数据类型: {dataFrame_to_save.dtypes}")

            # 使用明确的列名插入语句
            columns_str = ', '.join(columns_to_save)
            insert_sql = f"INSERT INTO indexsysdb.df_nyfed_sofr_daily ({columns_str}) VALUES"

            logger.info(f"执行的SQL: {insert_sql}")

            self.saveAkDateToClickHouse(insert_sql, dataFrame_to_save)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed: %s", insert_sql)

        return

    def deleteDateFromClickHouse(self, start_date=None, end_date=None):
        logger.info("deleteDataFromClickHouse started")

        try:
            if start_date and end_date:
                del_sql = (
                    "ALTER TABLE indexsysdb.df_nyfed_sofr_daily "
                    "DELETE where date >= '%s' and date <= '%s'" % (start_date, end_date)
                )
            else:
                del_sql = "ALTER TABLE indexsysdb.df_nyfed_sofr_daily DELETE where date is not null"

            self.deleteAkDateFromClickHouse(del_sql)

            # 等待 mutation 完成（ClickHouse DELETE 是异步的）
            self._wait_for_mutation_complete()
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDataFromClickHouse completed: %s", del_sql)

        return
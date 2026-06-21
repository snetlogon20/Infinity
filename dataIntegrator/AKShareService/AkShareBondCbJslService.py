import pandas

from dataIntegrator import CommonLib
from dataIntegrator.AKShareService.AkShareService import AkShareService
from dataIntegrator.common.CommonParameters import CommonParameters
from dataIntegrator.common.MyTokens import MyTokens
import sys

logger = CommonLib.logger


class AkShareBondCbJslService(AkShareService):
    """集思录可转债实时数据服务
    接口: bond_cb_jsl (akshare)
    描述: 集思录可转债实时数据，包含行情数据（涨跌幅，成交量和换手率等）
         及可转债基本信息（转股价，溢价率和到期收益率等）
    限量: 单次返回当前交易时刻的所有数据
    """

    # 中文列名 -> 英文列名映射
    COLUMN_MAPPING = {
        '代码': 'ts_code',
        '转债名称': 'bond_name',
        '现价': 'price',
        '涨跌幅': 'pct_chg',
        '正股代码': 'stk_code',
        '正股名称': 'stk_name',
        '正股价': 'stk_price',
        '正股涨跌': 'stk_pct_chg',
        '正股PB': 'stk_pb',
        '转股价': 'conv_price',
        '转股价值': 'conv_value',
        '转股溢价率': 'conv_premium',
        '债券评级': 'bond_rating',
        '回售触发价': 'put_trigger_price',
        '强赎触发价': 'call_trigger_price',
        '转债占比': 'cb_ratio',
        '到期时间': 'maturity_date',
        '剩余年限': 'remain_years',
        '剩余规模': 'remain_size',
        '成交额': 'amount',
        '换手率': 'turnover_rate',
        '到期税前收益': 'ytm_pre_tax',
        '双低': 'double_low',
    }

    def __init__(self):
        super().__init__()
        self.jsl_cookie = MyTokens.AKSHARE_BOND_CB_JSL_COOKIE

    def prepareDataFrame(self, cookie=None):
        """调用 akshare bond_cb_jsl 接口获取可转债实时数据

        Args:
            cookie (str, optional): 集思录登录 cookie，不传则可能只返回前30条

        Returns:
            pandas.DataFrame: 重命名后的可转债实时数据
        """
        logger.info("prepareData started")

        try:
            # 接口调用：优先使用传入的 cookie，其次使用类成员 jsl_cookie
            effective_cookie = cookie if cookie else self.jsl_cookie
            if effective_cookie:
                dataFrame = self.ak.bond_cb_jsl(cookie=effective_cookie)
                logger.info("使用 cookie 获取全量数据")
            else:
                dataFrame = self.ak.bond_cb_jsl()
                logger.info("未提供 cookie，可能仅返回前30条数据")

            # 打印原始数据结构
            logger.info(f"原始数据 Shape: {dataFrame.shape}")
            logger.info(f"原始数据列名: {list(dataFrame.columns)}")
            logger.info(f"原始数据类型:\n{dataFrame.dtypes}")
            logger.info(f"原始数据前3行:\n{dataFrame.head(3)}")

            # 重命名列：中文 -> 英文
            dataFrame = dataFrame.rename(columns=self.COLUMN_MAPPING)

            # 验证列名映射是否完整
            expected_cols = set(self.COLUMN_MAPPING.values())
            actual_cols = set(dataFrame.columns)
            missing_cols = expected_cols - actual_cols
            if missing_cols:
                logger.warning(f"以下列在接口返回数据中缺失: {missing_cols}")

            # 添加数据抓取日期
            dataFrame['trade_date'] = CommonParameters.today

            row_count = len(dataFrame)
            logger.info(f"成功获取可转债实时数据，共 {row_count} 行")

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")
        return dataFrame

    def transformDataFrame(self, dataFrame: pandas.core.frame.DataFrame):
        """数据转换：类型清洗和标准化

        Args:
            dataFrame: 原始数据

        Returns:
            pandas.DataFrame: 转换后的数据
        """
        logger.info("transformData started")

        try:
            # 确保 trade_date 是字符串
            if 'trade_date' in dataFrame.columns:
                dataFrame['trade_date'] = dataFrame['trade_date'].astype(str)

            # 字符串列：NaN -> 空字符串
            string_columns = ['ts_code', 'bond_name', 'stk_code', 'stk_name',
                              'bond_rating', 'maturity_date', 'trade_date']
            for col in string_columns:
                if col in dataFrame.columns:
                    dataFrame[col] = dataFrame[col].fillna('').astype(str)

            # 浮点列：NaN -> 0.0
            float_columns = ['price', 'pct_chg', 'stk_price', 'stk_pct_chg',
                             'stk_pb', 'conv_price', 'conv_value', 'conv_premium',
                             'put_trigger_price', 'call_trigger_price', 'cb_ratio',
                             'remain_years', 'remain_size', 'amount', 'turnover_rate',
                             'ytm_pre_tax', 'double_low']
            for col in float_columns:
                if col in dataFrame.columns:
                    dataFrame[col] = dataFrame[col].fillna(0.0).astype(float)

            logger.info(f"转换后数据 Shape: {dataFrame.shape}")
            logger.info(f"转换后数据类型:\n{dataFrame.dtypes}")

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("transformData completed")
        return dataFrame

    def saveDateToClickHouse(self, dataFrame):
        """将可转债实时数据保存到 ClickHouse

        Args:
            dataFrame: 转换后的数据
        """
        logger.info("saveDateToClickHouse started")

        try:
            logger.info(f"准备保存的数据列: {list(dataFrame.columns)}")
            logger.info(f"数据类型: {dataFrame.dtypes}")
            logger.info(f"数据形状: {dataFrame.shape}")

            # 确保只保存数据库表中存在的列
            db_columns = [
                'ts_code', 'bond_name', 'price', 'pct_chg',
                'stk_code', 'stk_name', 'stk_price', 'stk_pct_chg',
                'stk_pb', 'conv_price', 'conv_value', 'conv_premium',
                'bond_rating', 'put_trigger_price', 'call_trigger_price',
                'cb_ratio', 'maturity_date', 'remain_years', 'remain_size',
                'amount', 'turnover_rate', 'ytm_pre_tax', 'double_low', 'trade_date'
            ]
            columns_to_save = [col for col in db_columns if col in dataFrame.columns]

            dataFrame_to_save = dataFrame[columns_to_save].copy()

            # 构建 INSERT 语句
            columns_str = ', '.join(columns_to_save)
            insert_sql = f"INSERT INTO indexsysdb.df_akshare_bond_cb_jsl ({columns_str}) VALUES"

            logger.info(f"执行的SQL: {insert_sql}")

            self.saveAkDateToClickHouse(insert_sql, dataFrame_to_save)

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed")

    def deleteDateFromClickHouse(self, trade_date=None):
        """删除 ClickHouse 中的可转债实时数据（全量刷新模式）

        Args:
            trade_date (str, optional): 指定删除某日数据；不传则删除全部
        """
        logger.info("deleteDataFromClickHouse started")

        try:
            if trade_date:
                del_sql = "ALTER TABLE indexsysdb.df_akshare_bond_cb_jsl DELETE WHERE trade_date = '%s'" % trade_date
            else:
                # 全量刷新：删除所有历史数据
                del_sql = "ALTER TABLE indexsysdb.df_akshare_bond_cb_jsl DELETE WHERE 1=1"

            self.deleteAkDateFromClickHouse(del_sql)
            self._wait_for_mutation_complete()

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDataFromClickHouse completed: %s", del_sql)

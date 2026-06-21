import pandas

from dataIntegrator import CommonLib
from dataIntegrator.AKShareService.AkShareService import AkShareService
import sys
logger = CommonLib.logger


class AkShareFinancialDataIndicatorService(AkShareService):
    """
    AkShare 财务分析-财务指标 (Financial Data Indicator) Service

    接口: stock_financial_analysis_indicator
    目标地址: https://money.finance.sina.com.cn/corp/go.php/vFD_FinancialGuideLine/stockid/600004/ctrl/2019/displaytype/4.phtml
    描述: 获取新浪财经-财务分析-财务指标
    限量: 单次获取财务指标所有历史数据

    Args:
        symbol (str): 股票代码，如 '600004'
        start_year (str): 起始年份，如 '2020'
    """

    # 中文列名 → 英文列名 映射表
    COLUMN_MAPPING = {
        '摊薄每股收益(元)': 'diluted_eps',
        '加权每股收益(元)': 'weighted_eps',
        '每股收益_调整后(元)': 'adjusted_eps',
        '扣除非经常性损益后的每股收益(元)': 'deducted_eps',
        '每股净资产_调整前(元)': 'net_asset_per_share_before_adj',
        '每股净资产_调整后(元)': 'net_asset_per_share_after_adj',
        '每股经营性现金流(元)': 'operating_cash_flow_per_share',
        '每股资本公积金(元)': 'capital_reserve_per_share',
        '每股未分配利润(元)': 'retained_earnings_per_share',
        '调整后的每股净资产(元)': 'adjusted_net_asset_per_share',
        '总资产利润率(%)': 'total_asset_margin',
        '主营业务利润率(%)': 'main_business_margin',
        '总资产净利润率(%)': 'roa',
        '成本费用利润率(%)': 'cost_profit_margin',
        '营业利润率(%)': 'operating_profit_margin',
        '主营业务成本率(%)': 'main_cost_ratio',
        '销售净利率(%)': 'net_sales_margin',
        '股本报酬率(%)': 'equity_return_rate',
        '净资产报酬率(%)': 'roe_return',
        '资产报酬率(%)': 'asset_return_rate',
        '销售毛利率(%)': 'gross_margin',
        '三项费用比重': 'three_fee_ratio',
        '非主营比重': 'non_main_ratio',
        '主营利润比重': 'main_profit_ratio',
        '股息发放率(%)': 'dividend_payout_ratio',
        '投资收益率(%)': 'investment_return_ratio',
        '主营业务利润(元)': 'main_profit_amount',
        '净资产收益率(%)': 'roe',
        '加权净资产收益率(%)': 'weighted_roe',
        '扣除非经常性损益后的净利润(元)': 'deducted_net_profit',
        '主营业务收入增长率(%)': 'main_income_growth_rate',
        '净利润增长率(%)': 'net_profit_growth_rate',
        '净资产增长率(%)': 'net_asset_growth_rate',
        '总资产增长率(%)': 'total_asset_growth_rate',
        '应收账款周转率(次)': 'receivables_turnover',
        '应收账款周转天数(天)': 'receivables_turnover_days',
        '存货周转天数(天)': 'inventory_turnover_days',
        '存货周转率(次)': 'inventory_turnover',
        '固定资产周转率(次)': 'fixed_asset_turnover',
        '总资产周转率(次)': 'total_asset_turnover',
        '总资产周转天数(天)': 'total_asset_turnover_days',
        '流动资产周转率(次)': 'current_asset_turnover',
        '流动资产周转天数(天)': 'current_asset_turnover_days',
        '股东权益周转率(次)': 'equity_turnover',
        '流动比率': 'current_ratio',
        '速动比率': 'quick_ratio',
        '现金比率(%)': 'cash_ratio',
        '利息支付倍数': 'interest_coverage',
        '长期债务与营运资金比率(%)': 'long_debt_to_working_capital_ratio',
        '股东权益比率(%)': 'equity_ratio',
        '长期负债比率(%)': 'long_term_liability_ratio',
        '股东权益与固定资产比率(%)': 'equity_to_fixed_assets_ratio',
        '负债与所有者权益比率(%)': 'liabilities_to_equity_ratio',
        '长期资产与长期资金比率(%)': 'long_assets_to_long_funds_ratio',
        '资本化比率(%)': 'capitalization_ratio',
        '固定资产净值率(%)': 'fixed_asset_net_value_ratio',
        '资本固定化比率(%)': 'capital_fixed_ratio',
        '产权比率(%)': 'debt_to_equity_ratio',
        '清算价值比率(%)': 'liquidation_value_ratio',
        '固定资产比重(%)': 'fixed_asset_ratio',
        '资产负债率(%)': 'asset_liability_ratio',
        '总资产(元)': 'total_assets',
        '经营现金净流量对销售收入比率(%)': 'operating_cash_flow_to_sales_ratio',
        '资产的经营现金流量回报率(%)': 'operating_cash_flow_roa',
        '经营现金净流量与净利润的比率(%)': 'operating_cash_flow_to_net_profit_ratio',
        '经营现金净流量对负债比率(%)': 'operating_cash_flow_to_liability_ratio',
        '现金流量比率(%)': 'cash_flow_ratio',
        '短期股票投资(元)': 'short_stock_investment',
        '短期债券投资(元)': 'short_bond_investment',
        '短期其它经营性投资(元)': 'short_other_operating_investment',
        '长期股票投资(元)': 'long_stock_investment',
        '长期债券投资(元)': 'long_bond_investment',
        '长期其它经营性投资(元)': 'long_other_operating_investment',
        '1年以内应收帐款(元)': 'receivables_within_1y',
        '1-2年以内应收帐款(元)': 'receivables_within_1_2y',
        '2-3年以内应收帐款(元)': 'receivables_within_2_3y',
        '3年以内应收帐款(元)': 'receivables_within_3y',
        '1年以内预付货款(元)': 'prepayments_within_1y',
        '1-2年以内预付货款(元)': 'prepayments_within_1_2y',
        '2-3年以内预付货款(元)': 'prepayments_within_2_3y',
        '3年以内预付货款(元)': 'prepayments_within_3y',
        '1年以内其它应收款(元)': 'other_receivables_within_1y',
        '1-2年以内其它应收款(元)': 'other_receivables_within_1_2y',
        '2-3年以内其它应收款(元)': 'other_receivables_within_2_3y',
        '3年以内其它应收款(元)': 'other_receivables_within_3y',
    }

    def prepareDataFrame(self, symbol, start_year=None):
        """
        拉取财务分析指标原始数据

        注意：start_year 是 AKShare 接口的必传参数，对应新浪财经按年份分页的特定页面（URL 中的 /ctrl/{year}/）。
        不传 start_year 会导致 AKShare 返回空 DataFrame。
        当外部未指定 start_year 时，默认使用 "2000" 拉取全部可用历史数据。

        Args:
            symbol (str): 股票代码，如 '600004'
            start_year (str|None): 起始年份，如 '2020'；传 None 则默认使用 "2000" 拉取全部历史数据
        """
        logger.info(f"prepareData started, symbol={symbol}, start_year={start_year}")

        try:
            # start_year 是 AKShare 的必传参数，不传会返回空数据
            # 当外部未指定时，使用 "2000" 作为默认年份，以确保能拉取到全部历史数据
            if not start_year:
                start_year = "2000"
                logger.info(f"start_year 未指定，使用默认值: {start_year}")

            dataFrame = self.ak.stock_financial_analysis_indicator(
                symbol=symbol,
                start_year=start_year
            )

            # 诊断：打印原始数据结构
            logger.info(f"原始数据 Shape: {dataFrame.shape}")
            logger.info(f"原始数据 index: {dataFrame.index}")
            if dataFrame.empty:
                logger.warning(f"AKShare 返回空数据！symbol={symbol}, start_year={start_year}。"
                               f"可能原因：1) 该股票在 {start_year} 年份无财务数据（如新股上市前）; "
                               f"2) start_year 参数对应新浪财经分页页面不存在。")
            else:
                logger.info(f"原始数据 columns: {dataFrame.columns.tolist()[:5]}...")
            if isinstance(dataFrame.index, pandas.MultiIndex):
                logger.info(f"原始数据 index names: {dataFrame.index.names}")
            if isinstance(dataFrame.columns, pandas.MultiIndex):
                logger.info(f"原始数据 columns names: {dataFrame.columns.names}")

            # 处理多级列索引：展平并拼接为单一列名
            if isinstance(dataFrame.columns, pandas.MultiIndex):
                dataFrame.columns = [
                    '_'.join(str(c) for c in col if c).strip()
                    for col in dataFrame.columns
                ]

            # 如果是多级索引（MultiIndex），日期通常在 index 中
            if isinstance(dataFrame.index, pandas.MultiIndex):
                # 提取日期层级（通常是第一个层级）
                dataFrame = dataFrame.reset_index()
                # 查找日期列：可能是 '日期'、'date' 或 index 列
                date_col_candidates = [col for col in dataFrame.columns if '日期' in str(col) or str(col).lower() == 'date']
                if date_col_candidates:
                    dataFrame.rename(columns={date_col_candidates[0]: 'date'}, inplace=True)
                elif 'index' in dataFrame.columns:
                    dataFrame.rename(columns={'index': 'date'}, inplace=True)
                elif 'level_0' in dataFrame.columns:
                    dataFrame.rename(columns={'level_0': 'date'}, inplace=True)
            else:
                # 单级索引情况
                dataFrame = dataFrame.reset_index()
                if 'index' in dataFrame.columns:
                    # 检查 index 列是否是日期格式
                    index_sample = dataFrame['index'].head(5).tolist()
                    logger.info(f"reset_index 后的 index 列样本: {index_sample}")
                    # 如果是纯数字行号（如 0,1,2），则丢弃，尝试从列名找日期
                    if all(isinstance(x, int) for x in index_sample):
                        dataFrame.drop(columns=['index'], inplace=True)
                        # 尝试找第一列作为日期（通常是日期列）
                        if len(dataFrame.columns) > 0:
                            first_col = dataFrame.columns[0]
                            logger.info(f"尝试用第一列 '{first_col}' 作为日期")
                            dataFrame.rename(columns={first_col: 'date'}, inplace=True)
                    else:
                        dataFrame.rename(columns={'index': 'date'}, inplace=True)

            # 确保 date 列存在且不是行号
            if 'date' in dataFrame.columns:
                date_sample = dataFrame['date'].head(5).tolist()
                date_dtype = dataFrame['date'].dtype
                logger.info(f"prepareData [提取后] date dtype={date_dtype}, sample={date_sample}")
                # 如果是整数行号，说明提取错了，需要检查原始数据
                if date_dtype == 'int64' and all(isinstance(x, int) and x < 1000 for x in date_sample):
                    logger.warning(f"date 列看起来是行号而不是日期，样本: {date_sample}")

            # 添加 symbol 列
            dataFrame['symbol'] = symbol

            # 中文列名 → 英文列名
            dataFrame.rename(columns=self.COLUMN_MAPPING, inplace=True)

            # 清洗: "--" → NaN
            dataFrame = dataFrame.replace(["--", None], pandas.NA)

            logger.info(f"处理后数据 Shape: {dataFrame.shape}")
            logger.info(f"处理后数据列数: {len(dataFrame.columns)}")

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")
        return dataFrame

    def transformDataFrame(self, dataFrame: pandas.core.frame.DataFrame):
        logger.info("transformData started")

        try:
            # 诊断：打印接收到的 date 列样本（经过 Excel 读写后）
            if 'date' in dataFrame.columns:
                date_sample = dataFrame['date'].head(5).tolist()
                date_dtype = dataFrame['date'].dtype
                logger.info(f"transformData [入参] date dtype={date_dtype}, sample={date_sample}")

            # 数据预处理：转换日期列为 yyyymmdd 格式
            if 'date' in dataFrame.columns:
                # 方法：先尝试解析为 datetime，成功则 strftime；失败则从字符串清洗
                date_series = pandas.to_datetime(dataFrame['date'], errors='coerce')
                date_formatted = date_series.apply(
                    lambda dt: dt.strftime('%Y%m%d') if pandas.notna(dt) else ''
                )

                # 对于解析失败的行，尝试从原始值提取数字
                mask_failed = (date_formatted == '')
                if mask_failed.any():
                    # 原始值可能是 "2016-03-31" 带横线格式 或 "20160331"
                    raw_as_str = dataFrame['date'].astype(str)
                    date_formatted[mask_failed] = raw_as_str[mask_failed].str.extract(r'(\d{4})\D?(\d{2})\D?(\d{2})').apply(
                        lambda row: ''.join(row.dropna().astype(str)), axis=1
                    )

                dataFrame['date'] = date_formatted

                # 诊断：打印转换后的结果
                date_converted_sample = dataFrame['date'].head(5).tolist()
                logger.info(f"transformData [转换后] date sample={date_converted_sample}")

            # symbol 列：强制保持为6位字符串（补前导零，防止 Excel 读写后丢失）
            if 'symbol' in dataFrame.columns:
                dataFrame['symbol'] = dataFrame['symbol'].astype(str).str.zfill(6)

            # 将所有数据列逐单元格转为 String（ClickHouse 建表全为 String 类型）
            # 防止数值列在 Excel 读写后变成 int/float 导致 clickhouse_driver 报 encode 错误
            for col in dataFrame.columns:
                if col in ('date', 'symbol'):
                    continue
                dataFrame[col] = dataFrame[col].map(
                    lambda x: str(x) if pandas.notna(x) else ''
                )

            # 按日期排序（空 DataFrame 可能没有 date 列）
            if 'date' in dataFrame.columns:
                dataFrame = dataFrame.sort_values('date').reset_index(drop=True)

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("transformData completed")
        return dataFrame

    def saveDateToClickHouse(self, dataFrame):
        logger.info("saveDateToClickHouse started")

        insert_sql = "INSERT INTO indexsysdb.df_akshare_stock_financial_analysis_indicator VALUES"

        try:
            # 空 DataFrame 跳过写入
            if dataFrame.empty:
                logger.info("saveDateToClickHouse skipped: empty DataFrame")
                return

            # 二次类型保障：将整个 DataFrame 转为纯 string 后，清理 NaN 字符串
            dataFrame_to_save = dataFrame.astype(str)
            # pandas astype(str) 将 NaN 转为字符串 'nan'，需要替换回空
            dataFrame_to_save = dataFrame_to_save.replace({'nan': '', '<NA>': '', 'None': '', 'NaT': ''})

            self.saveAkDateToClickHouse(insert_sql, dataFrame_to_save)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed: %s", insert_sql)
        return

    def deleteDateFromClickHouse(self, symbol):
        logger.info(f"deleteDataFromClickHouse started, symbol={symbol}")

        try:
            del_sql = "ALTER TABLE indexsysdb.df_akshare_stock_financial_analysis_indicator DELETE where symbol='%s'" % (symbol)
            self.deleteAkDateFromClickHouse(del_sql)
            # 等待 mutation 完成（ClickHouse DELETE 是异步的）
            self._wait_for_mutation_complete()
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDataFromClickHouse completed: %s", del_sql)
        return

    @classmethod
    def loadDataFromClickHouse(self, symbol):
        """
        从 ClickHouse 读取指定股票的财务分析指标数据

        Args:
            symbol (str): 股票代码，如 '002093'

        Returns:
            pandas.DataFrame: 含中文列名的财务数据
        """
        logger.info(f"loadDataFromClickHouse started, symbol={symbol}")

        try:
            # ClickHouse 表的所有列（按建表顺序）
            columns = [
                'date', 'symbol',
                'diluted_eps', 'weighted_eps', 'adjusted_eps', 'deducted_eps',
                'net_asset_per_share_before_adj', 'net_asset_per_share_after_adj',
                'operating_cash_flow_per_share', 'capital_reserve_per_share',
                'retained_earnings_per_share', 'adjusted_net_asset_per_share',
                'total_asset_margin', 'main_business_margin', 'roa',
                'cost_profit_margin', 'operating_profit_margin', 'main_cost_ratio',
                'net_sales_margin', 'equity_return_rate', 'roe_return',
                'asset_return_rate', 'gross_margin', 'three_fee_ratio',
                'non_main_ratio', 'main_profit_ratio', 'dividend_payout_ratio',
                'investment_return_ratio', 'main_profit_amount', 'roe',
                'weighted_roe', 'deducted_net_profit', 'main_income_growth_rate',
                'net_profit_growth_rate', 'net_asset_growth_rate',
                'total_asset_growth_rate', 'receivables_turnover',
                'receivables_turnover_days', 'inventory_turnover_days',
                'inventory_turnover', 'fixed_asset_turnover', 'total_asset_turnover',
                'total_asset_turnover_days', 'current_asset_turnover',
                'current_asset_turnover_days', 'equity_turnover', 'current_ratio',
                'quick_ratio', 'cash_ratio', 'interest_coverage',
                'long_debt_to_working_capital_ratio', 'equity_ratio',
                'long_term_liability_ratio', 'equity_to_fixed_assets_ratio',
                'liabilities_to_equity_ratio', 'long_assets_to_long_funds_ratio',
                'capitalization_ratio', 'fixed_asset_net_value_ratio',
                'capital_fixed_ratio', 'debt_to_equity_ratio',
                'liquidation_value_ratio', 'fixed_asset_ratio',
                'asset_liability_ratio', 'total_assets',
                'operating_cash_flow_to_sales_ratio', 'operating_cash_flow_roa',
                'operating_cash_flow_to_net_profit_ratio',
                'operating_cash_flow_to_liability_ratio', 'cash_flow_ratio',
                'short_stock_investment', 'short_bond_investment',
                'short_other_operating_investment', 'long_stock_investment',
                'long_bond_investment', 'long_other_operating_investment',
                'receivables_within_1y', 'receivables_within_1_2y',
                'receivables_within_2_3y', 'receivables_within_3y',
                'prepayments_within_1y', 'prepayments_within_1_2y',
                'prepayments_within_2_3y', 'prepayments_within_3y',
                'other_receivables_within_1y', 'other_receivables_within_1_2y',
                'other_receivables_within_2_3y', 'other_receivables_within_3y',
            ]

            query = f"SELECT {', '.join(columns)} FROM indexsysdb.df_akshare_stock_financial_analysis_indicator WHERE symbol = %(symbol)s"
            result = self.clickhouseClient.execute(query, {'symbol': symbol})

            if not result:
                logger.warning(f"loadDataFromClickHouse: 未找到 symbol={symbol} 的数据")
                return pandas.DataFrame()

            dataFrame = pandas.DataFrame(result, columns=columns)

            # 英文列名 → 中文列名（反向映射，供 Altman Z-Score 等下游使用）
            reverse_mapping = {v: k for k, v in self.COLUMN_MAPPING.items()}
            # 额外：date → 日期
            reverse_mapping['date'] = '日期'
            # symbol 保持不变，但下游可能不需要
            reverse_mapping['symbol'] = '股票代码'
            dataFrame.rename(columns=reverse_mapping, inplace=True)

            logger.info(f"loadDataFromClickHouse completed: {len(dataFrame)} rows")
            return dataFrame

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

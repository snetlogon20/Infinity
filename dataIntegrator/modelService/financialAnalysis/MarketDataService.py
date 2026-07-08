"""
市场数据服务 - 统一管理多市场资产数据获取

职责:
1. 从 ClickHouse 获取股票、指数、商品等多市场数据
2. 支持 US/CN/GLOBAL 三种市场类型
3. 自动处理资产名称映射
4. 提供统一的 SQL 构建方法
"""

import os
import sys
import pandas as pd
from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from dataIntegrator import CommonLib, CommonParameters

logger = CommonLib.logger


class MarketDataService:
    """市场数据服务类 - 统一管理多市场资产数据获取"""

    def __init__(self):
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event="MarketDataService initialized")

    def writeLogInfo(self, className="unknown", functionName="unknown", event="unknown"):
        """记录日志信息"""
        print("%s.%s: %s" % (className, functionName, event))
        logger.info("%s.%s: %s" % (className, functionName, event))

    def fetch_asset_data(self, assets, start_date, end_date, market_type="CN", 
                        market_symbol=None, include_commodities=None, asset_type="stock"):
        """
        从 ClickHouse 获取资产数据（支持多数据源：股票 + 指数 + 商品）

        参数:
        - assets: 资产代码列表
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')
        - market_type: 市场类型 ['US', 'CN', 'GLOBAL']
        - market_symbol: 市场指数符号（用于区分指数和股票）
        - include_commodities: 商品配置字典，例如 {'GC': '黄金', 'CL': '原油'}
        - asset_type: 资产类型标识 ('stock' 或 'asset'，仅用于日志)

        返回:
        - dfs: 字典，key为资产代码（A股格式为 ts_code-name，美股格式为 ts_code-enname），value为DataFrame
        """
        self.writeLogInfo(className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name,
                          event=f"Fetching data for {len(assets)} {asset_type}s from {start_date} to {end_date}, market={market_type}")

        if include_commodities:
            logger.info(f"📦 同时获取 {len(include_commodities)} 种商品数据: {list(include_commodities.keys())}")

        dfs = {}
        asset_names = {}

        # Step 1: 获取资产名称
        self._fetch_asset_names(assets, market_type, market_symbol, asset_names)

        # Step 2: 获取资产价格数据
        for asset in assets:
            is_market_index = (asset == market_symbol)
            
            # 构建SQL并获取数据
            sql = self._build_query_sql(asset, start_date, end_date, market_type, is_market_index)
            display_name = asset

            clickhouseService = ClickhouseService()
            df = clickhouseService.getDataFrameWithoutColumnsName(sql)
            if df.empty:
                logger.warning(f"⚠️ 警告: {asset} 在 {start_date} 到 {end_date} 期间没有数据")
                continue

            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df.set_index('trade_date', inplace=True)

            # 拼接显示名称（非指数且找到名称时）
            if not is_market_index and asset in asset_names and asset_names[asset]:
                display_name = f"{asset}-{asset_names[asset]}"

            dfs[display_name] = df

        # Step 3: 获取商品数据（如果有配置）
        if include_commodities:
            commodity_dfs = self._fetch_commodities_data(include_commodities, start_date, end_date, market_type)
            dfs.update(commodity_dfs)

        logger.info(f"✅ 成功获取 {len(dfs)} 个{asset_type}的数据")
        return dfs

    def _fetch_asset_names(self, assets, market_type, market_symbol, asset_names):
        """
        获取资产名称映射
        
        参数:
        - assets: 资产代码列表
        - market_type: 市场类型
        - market_symbol: 市场指数符号
        - asset_names: 输出字典，存储名称映射
        """
        if market_type == "CN":
            cn_assets = [a for a in assets if a != market_symbol]
            if cn_assets:
                clickhouseService = ClickhouseService()
                asset_codes = "','".join(cn_assets)
                name_sql = f"""
                SELECT ts_code, name
                FROM indexsysdb.df_tushare_stock_basic
                WHERE ts_code IN ('{asset_codes}')
                """
                logger.info(f"🔍 查询A股名称: {len(cn_assets)} 只股票")
                name_df = clickhouseService.getDataFrameWithoutColumnsName(name_sql)
                if not name_df.empty:
                    for _, row in name_df.iterrows():
                        asset_names[row['ts_code']] = row['name']
                    logger.info(f"✅ 成功获取 {len(asset_names)} 只A股名称")
                else:
                    logger.warning(f"⚠️ 未获取到A股名称数据")

        elif market_type == "US":
            us_assets = [a for a in assets if a != market_symbol]
            if us_assets:
                clickhouseService = ClickhouseService()
                asset_codes = "','".join(us_assets)
                name_sql = f"""
                SELECT ts_code, enname
                FROM indexsysdb.df_tushare_us_stock_basic
                WHERE ts_code IN ('{asset_codes}')
                """
                logger.info(f"🔍 查询美股名称: {len(us_assets)} 只股票")
                name_df = clickhouseService.getDataFrameWithoutColumnsName(name_sql)
                if not name_df.empty:
                    for _, row in name_df.iterrows():
                        asset_names[row['ts_code']] = row['enname']
                    logger.info(f"✅ 成功获取 {len(asset_names)} 只美股名称")
                else:
                    logger.warning(f"⚠️ 未获取到美股名称数据")

        elif market_type == "GLOBAL":
            # 全球指数表(df_tushare_index_global)没有name字段，直接使用ts_code
            logger.info(f"🌍 全球指数数据源不包含名称信息，将使用指数代码作为显示名称")
            pass

    def _build_query_sql(self, asset, start_date, end_date, market_type, is_market_index):
        """
        根据市场类型和资产类型构建查询SQL
        
        参数:
        - asset: 资产代码
        - start_date: 开始日期
        - end_date: 结束日期
        - market_type: 市场类型
        - is_market_index: 是否为市场指数
        
        返回:
        - SQL 查询字符串
        """
        if market_type == "US":
            return self._build_us_stock_sql(asset, start_date, end_date)

        elif market_type == "CN":
            if is_market_index:
                return self._build_cn_index_sql(asset, start_date, end_date)
            else:
                return self._build_cn_stock_sql(asset, start_date, end_date)

        elif market_type == "GLOBAL":
            return self._build_global_index_sql(asset, start_date, end_date)

        else:
            raise ValueError(f"不支持的市场类型: {market_type}。支持的类型: ['US', 'CN', 'GLOBAL']")

    def _build_us_stock_sql(self, stock, start_date, end_date):
        """构建美股查询SQL"""
        return f"""
        SELECT
            date as trade_date,
            close as close_point
        FROM df_akshare_stock_us_daily
        WHERE symbol = '{stock}'
          AND date >= '{start_date}'
          AND date <= '{end_date}'
        ORDER BY date ASC
        """

    def _build_cn_stock_sql(self, stock, start_date, end_date):
        """构建A股查询SQL"""
        return f"""
        SELECT
            trade_date as trade_date,
            close as close_point
        FROM df_tushare_stock_daily
        WHERE ts_code = '{stock}'
          AND trade_date >= '{start_date}'
          AND trade_date <= '{end_date}'
        ORDER BY trade_date ASC
        """

    def _build_cn_index_sql(self, stock, start_date, end_date):
        """构建中国指数查询SQL"""
        return f"""
        SELECT
            trade_date as trade_date,
            close as close_point
        FROM df_tushare_cn_index_daily
        WHERE ts_code = '{stock}'
          AND trade_date >= '{start_date}'
          AND trade_date <= '{end_date}'
        ORDER BY trade_date ASC
        """

    def _build_global_index_sql(self, stock, start_date, end_date):
        """构建全球指数查询SQL"""
        return f"""
        SELECT
            trade_date as trade_date,
            close as close_point
        FROM df_tushare_index_global
        WHERE ts_code = '{stock}'
          AND trade_date >= '{start_date}'
          AND trade_date <= '{end_date}'
        ORDER BY trade_date ASC
        """

    def _fetch_commodities_data(self, commodities, start_date, end_date, market_type="US"):
        """
        获取商品/外汇数据（支持 UNION 多资产一次性查询）
        
        参数:
        - commodities: 资产配置字典，例如 {'GC': '黄金', 'CL': '原油'} 或 {'EURUSD.FXCM': '欧元/美元'}
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')
        - market_type: 市场类型 ('US' 使用国外期货表, 'CN' 使用国内SGE表)
        
        返回:
        - dfs: 资产数据字典
        """
        if not commodities:
            return {}

        logger.info(f"🔍 开始获取资产数据，市场类型: {market_type}, 资产列表: {list(commodities.keys())}")

        # 格式化日期（YYYYMMDD -> YYYY-MM-DD）
        start_date_formatted = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
        end_date_formatted = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"

        # 检测是否包含外汇货币对
        has_forex = any('.FXCM' in str(symbol) for symbol in commodities.keys())
        
        if has_forex:
            # 外汇货币对：使用 df_tushare_fx_daily 表
            return self._fetch_forex_data(commodities, start_date_formatted, end_date_formatted)

        # 根据市场类型选择数据表
        if market_type == "CN":
            # 中国资产：使用上海黄金交易所数据
            table_name = "indexsysdb.df_akshare_spot_hist_sge"
            has_symbol_field = False
            logger.info(f"🇨🇳 使用国内黄金数据表: {table_name}")
        else:
            # 美国/国际资产：使用外盘期货数据
            table_name = "indexsysdb.df_akshare_futures_foreign_hist"
            has_symbol_field = True
            logger.info(f"🇺🇸 使用国外期货数据表: {table_name}")

        # 构建 UNION ALL 查询
        union_queries = []
        for symbol, name in commodities.items():
            if market_type == "CN":
                union_queries.append(f"""
                    SELECT
                        '{symbol}' AS ts_code,
                        replaceAll(toString(date), '-', '') AS trade_date,
                        close AS close_point
                    FROM {table_name}
                    WHERE date >= '{start_date_formatted}'
                      AND date <= '{end_date_formatted}'
                      AND close > 0
                """)
            else:
                union_queries.append(f"""
                    SELECT
                        '{symbol}' AS ts_code,
                        replaceAll(toString(date), '-', '') AS trade_date,
                        close AS close_point
                    FROM {table_name}
                    WHERE symbol = '{symbol}'
                      AND date >= '{start_date_formatted}'
                      AND date <= '{end_date_formatted}'
                      AND close > 0
                """)

        combined_sql = " UNION ALL ".join(union_queries) + " ORDER BY trade_date, ts_code"
        logger.info(f"📝 执行商品数据查询 SQL:\n{combined_sql}")

        clickhouseService = ClickhouseService()
        df = clickhouseService.getDataFrameWithoutColumnsName(combined_sql)

        if df.empty:
            logger.warning(f"⚠️ 警告: 未获取到任何商品数据 (市场类型: {market_type}, 商品: {list(commodities.keys())})")
            return {}

        logger.info(f"✅ 成功获取商品原始数据: {len(df)} 条记录")
        logger.info(f"   包含商品: {df['ts_code'].unique().tolist()}")

        # 按商品分组
        dfs = {}
        for symbol in df['ts_code'].unique():
            commodity_df = df[df['ts_code'] == symbol][['trade_date', 'close_point']].copy()
            commodity_df['trade_date'] = pd.to_datetime(commodity_df['trade_date'])
            commodity_df.set_index('trade_date', inplace=True)
            
            display_name = f"{symbol}-{commodities.get(symbol, '')}"
            dfs[display_name] = commodity_df
            logger.info(f"   {display_name}: {len(commodity_df)} 条数据")

        return dfs

    def _fetch_forex_data(self, forex_pairs, start_date_formatted, end_date_formatted):
        """
        获取外汇货币对数据
        
        参数:
        - forex_pairs: 外汇配置字典，例如 {'EURUSD.FXCM': '欧元/美元'}
        - start_date_formatted: 开始日期 (格式: 'YYYY-MM-DD')
        - end_date_formatted: 结束日期 (格式: 'YYYY-MM-DD')
        
        返回:
        - dfs: 外汇数据字典
        """
        logger.info(f"💱 开始获取外汇数据: {list(forex_pairs.keys())}")

        # 构建 UNION ALL 查询
        union_queries = []
        for symbol, name in forex_pairs.items():
            union_queries.append(f"""
                SELECT
                    '{symbol}' AS ts_code,
                    replaceAll(toString(trade_date), '-', '') AS trade_date,
                    close AS close_point
                FROM indexsysdb.df_tushare_fx_daily
                WHERE ts_code = '{symbol}'
                  AND trade_date >= '{start_date_formatted}'
                  AND trade_date <= '{end_date_formatted}'
                  AND close > 0
            """)

        combined_sql = " UNION ALL ".join(union_queries) + " ORDER BY trade_date, ts_code"
        logger.info(f"📝 执行外汇数据查询 SQL:\n{combined_sql}")

        clickhouseService = ClickhouseService()
        df = clickhouseService.getDataFrameWithoutColumnsName(combined_sql)

        if df.empty:
            logger.warning(f"⚠️ 警告: 未获取到任何外汇数据")
            return {}

        logger.info(f"✅ 成功获取外汇原始数据: {len(df)} 条记录")

        # 按货币对分组
        dfs = {}
        for symbol in df['ts_code'].unique():
            forex_df = df[df['ts_code'] == symbol][['trade_date', 'close_point']].copy()
            forex_df['trade_date'] = pd.to_datetime(forex_df['trade_date'])
            forex_df.set_index('trade_date', inplace=True)
            
            display_name = f"{symbol}-{forex_pairs.get(symbol, '')}"
            dfs[display_name] = forex_df
            logger.info(f"   {display_name}: {len(forex_df)} 条数据")

        return dfs

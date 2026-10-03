import os
import time
import pandas as pd
from dataIntegrator.TuShareService.TuShareService import TuShareService
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.TuShareService.TuShareOptDailyService import TuShareOptDailyService
from dataIntegrator.modelService.commonService.CalendarService import CalendarService
from dataIntegrator.dataService.ClickhouseService import ClickhouseService

logger = CommonLib.logger

class TuShareOptDailyServiceTest(TuShareService):



    @classmethod
    def test_by_trade_date(self, trade_date="20261218", exchange=""):
        """
        按单个交易日测试期权日线数据
        """
        tuShareService = TuShareOptDailyService()

        logger.info(f"按交易日查询: {trade_date}")
        tuShareService.refresh_opt_daily(
            trade_date=trade_date,
            exchange=exchange
        )


    @classmethod
    def load_ts_code_list_from_basic(self, underlying_groups=None, symbol_prefixes=None):
        """
        从 ClickHouse opt_basic 最新快照动态加载目标标的的合约清单

        SSE ETF 期权的 ts_code 是 8 位数字（如 10000201.SH），无语义规律且每月有新合约上市，
        硬编码不可行，必须从 opt_basic 快照（含 symbol 字段）按标的前缀过滤。

        支持跨交易所混合标的（如上交所 50ETF 小合约 + 中金所 HO 指数大合约）：
        每组 (symbol_prefix, exchange) 独立取该组最新快照 trade_date，互不干扰，
        exchange 条件可消除 'HO' 等前缀的跨所歧义。

        Args:
            underlying_groups: 标的分组配置 list[dict]，每项含:
                - symbol_prefix: 标的/合约前缀（如 '510050', 'HO'）
                - exchange: 交易所代码（如 'SSE', 'CFFEX'），空串表示不过滤
            symbol_prefixes: 兼容旧入参，str 或 list[str]（不区分交易所）。
                             与 underlying_groups 同时传入时以 underlying_groups 为准。

        Returns:
            list[str]: 合约代码列表（已去重）
        """
        # 兼容旧入参: symbol_prefixes → 无交易所条件的分组
        if not underlying_groups and symbol_prefixes:
            if isinstance(symbol_prefixes, str):
                symbol_prefixes = [symbol_prefixes]
            underlying_groups = [{'symbol_prefix': p, 'exchange': ''} for p in symbol_prefixes]
        if isinstance(underlying_groups, dict):
            underlying_groups = [underlying_groups]
        if not underlying_groups:
            raise ValueError("underlying_groups / symbol_prefixes 不能为空")

        ts_code_set = set()
        for group in underlying_groups:
            prefix = str(group.get('symbol_prefix', '')).strip()
            exchange = str(group.get('exchange', '') or '').strip()
            if not prefix:
                continue

            # CFFEX 指数期权（如 HO）symbol 与 ts_code 前缀一致，两者 OR 兜底
            # ETF 期权 ts_code 为8位数字，只会命中 symbol
            like_conds = f"symbol LIKE '{prefix}%' OR ts_code LIKE '{prefix}%'"
            if exchange:
                exchange_cond = f"AND exchange = '{exchange}'"
            else:
                exchange_cond = ""

            sql = f"""
            SELECT DISTINCT ts_code
            FROM indexsysdb.df_tushare_opt_basic
            WHERE ({like_conds})
              {exchange_cond}
              AND trade_date = (
                  SELECT max(trade_date) FROM indexsysdb.df_tushare_opt_basic
                  WHERE ({like_conds})
                    {exchange_cond}
              )
            ORDER BY ts_code
            """
            df = ClickhouseService.getDataFrameWithoutColumnsName(sql)

            if df is None or df.empty or 'ts_code' not in df.columns:
                logger.warning(f"opt_basic 快照中未找到 symbol/ts_code LIKE '{prefix}%'"
                               f"{f' (exchange={exchange})' if exchange else ''} 的合约，跳过该组")
                continue

            group_codes = df['ts_code'].astype(str).tolist()
            ts_code_set.update(group_codes)
            logger.info(f"从 opt_basic 最新快照加载到 {len(group_codes)} 个 "
                        f"'{prefix}'{f' ({exchange})' if exchange else ''} 期权合约")

        if not ts_code_set:
            logger.error("opt_basic 快照中未找到任何目标合约，"
                         "请先运行 TuShareOptBasicServiceTest.refresh_opt_basic 刷新基础信息")
            raise ValueError(f"No contracts found for groups {underlying_groups} in opt_basic snapshot")

        ts_code_list = sorted(ts_code_set)
        logger.info(f"合计加载 {len(ts_code_list)} 个期权合约（跨 {len(underlying_groups)} 组）")
        return ts_code_list

    @classmethod
    def refresh_opt_daily_by_ts_code(self, underlying_groups):

        tuShareService = TuShareOptDailyService()

        ts_code_list = self.load_ts_code_list_from_basic(underlying_groups=underlying_groups)

        calendarService = CalendarService()
        start_date = calendarService.calculate_T_minus_n_days(CommonParameters.today, days=300)
        end_date = CommonParameters.today
        calendar_service = CalendarService()
        trade_date_list = calendar_service.calculate_dates_between_start_end_date(start_date, end_date)
        # 批量模式: 每个交易日按交易所各调1次API（.SH→SSE, .CFX→CFFEX 自动分组，内存过滤）
        tuShareService.refresh_opt_daily_by_ts_code_list(
            ts_code_list=ts_code_list,
            trade_date_list=trade_date_list,
            exchange=""
        )
        logger.info("=" * 80)
        logger.info("期权日线数据处理完成")
        logger.info("=" * 80)


if __name__ == '__main__':
    tuShareOptDailyServiceTest = TuShareOptDailyServiceTest()

    try:
        logger.info("=" * 80)
        logger.info("开始处理期权日线数据...")
        logger.info("=" * 80)

        # 使用示例1: 按交易日查询（推荐，单日数据量适中）
        # tuShareOptDailyServiceTest.test_by_trade_date(
        #     trade_date="20260702",
        #     exchange=""
        # )

        # 使用示例2: 批量获取期权日线数据（一次 API 调用获取全天全量，内存过滤，最后一次性存入 ClickHouse）

        # 目标标的分组配置（跨交易所混合）：
        # - 上交所 华夏上证50ETF 小合约: symbol like '510050%'
        # - 中金所 上证50指数 大合约:   HO 前缀指数期权
        # 每组独立取 opt_basic 最新快照；合约清单自动按 ts_code 后缀分组交易所拉取
        underlying_groups = [
            {'symbol_prefix': '510050', 'exchange': 'SSE'},   # 华夏上证50ETF 小合约
            {'symbol_prefix': 'HO',     'exchange': 'CFFEX'}, # 中金所上证50指数 大合约
        ]
        tuShareOptDailyServiceTest.refresh_opt_daily_by_ts_code(underlying_groups)

    except Exception as e:
        logger.error(f"处理失败: {e}")
        import traceback
        traceback.print_exc()

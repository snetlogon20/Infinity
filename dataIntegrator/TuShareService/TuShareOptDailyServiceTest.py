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
    def load_ts_code_list_from_basic(self, symbol_prefixes='510050', exchange=None):
        """
        从 ClickHouse opt_basic 最新快照动态加载目标标的的合约清单

        SSE ETF 期权的 ts_code 是 8 位数字（如 10000201.SH），无语义规律且每月有新合约上市，
        硬编码不可行，必须从 opt_basic 快照（含 symbol 字段）按标的前缀过滤。
        CFFEX 股指期权的 symbol 以合约前缀开头（如 'HO2612C2500'），可用 'HO2612' 前缀匹配。

        Args:
            symbol_prefixes: 标的/合约代码前缀，str 或 list[str]。
                             如 '510050' 或 ['510050', 'HO2612']
            exchange: 交易所过滤（'SSE'/'CFFEX'/...），None=不过滤

        Returns:
            list[str]: 合约代码列表（已去重）
        """
        # 兼容单个 str 入参
        if isinstance(symbol_prefixes, str):
            symbol_prefixes = [symbol_prefixes]
        if not symbol_prefixes:
            raise ValueError("symbol_prefixes 不能为空")

        # 每个 prefix 一对 (symbol LIKE 'x%', trade_date 对齐) 条件
        symbol_conds = " OR ".join(
            f"symbol LIKE '{p}%'" for p in symbol_prefixes
        )
        exchange_cond = f" AND exchange = '{exchange}'" if exchange else ""
        sql = f"""
        SELECT DISTINCT ts_code
        FROM indexsysdb.df_tushare_opt_basic
        WHERE ({symbol_conds}){exchange_cond}
          AND trade_date = (
              SELECT max(trade_date) FROM indexsysdb.df_tushare_opt_basic
              WHERE ({symbol_conds}){exchange_cond}
          )
        ORDER BY ts_code
        """
        df = ClickhouseService.getDataFrameWithoutColumnsName(sql)

        if df is None or df.empty or 'ts_code' not in df.columns:
            logger.error(f"opt_basic 快照中未找到 symbol LIKE {symbol_prefixes} (exchange={exchange}) 的合约，"
                         f"请先运行 TuShareOptBasicServiceTest.refresh_opt_basic 刷新基础信息")
            raise ValueError(f"No contracts found for symbol prefixes {symbol_prefixes} (exchange={exchange}) in opt_basic snapshot")

        ts_code_list = df['ts_code'].astype(str).tolist()
        logger.info(f"从 opt_basic 最新快照加载到 {len(ts_code_list)} 个 {symbol_prefixes} (exchange={exchange}) 期权合约")
        return ts_code_list

    @classmethod
    def refresh_opt_daily_by_ts_code(self):

        tuShareService = TuShareOptDailyService()

        # 目标标的期权合约清单，从 opt_basic 最新快照动态加载（支持多标的）
        ts_code_list = self.load_ts_code_list_from_basic(symbol_prefixes=['510050', 'HO2612'])

        calendarService = CalendarService()
        #start_date = calendarService.calculate_T_minus_n_days(CommonParameters.today, days=300)
        start_date = calendarService.calculate_T_minus_n_days(CommonParameters.today, days=30)
        end_date = CommonParameters.today
        calendar_service = CalendarService()
        trade_date_list = calendar_service.calculate_dates_between_start_end_date(start_date, end_date)

        # 按交易所后缀分组，分交易所拉取：
        # TuShare opt_daily 的 exchange 参数一次只能传一个交易所，
        # 传 'SSE' 只会返回上交所行情（100xxx.SH），CFFEX 的 HO2612-*.CFX 必须单独按 'CFFEX' 拉
        suffix_exchange_map = {
            '.SH': 'SSE',
            '.CFX': 'CFFEX',
        }
        for suffix, exchange in suffix_exchange_map.items():
            group_list = [c for c in ts_code_list if c.endswith(suffix)]
            if not group_list:
                logger.info(f"跳过交易所 {exchange}：无 {suffix} 后缀的目标合约")
                continue
            logger.info(f"开始拉取 {exchange} 行情：{len(group_list)} 个合约")
            # 批量模式: 每个交易日只调1次API（vs 原来每个合约1次）
            tuShareService.refresh_opt_daily_by_ts_code_list(
                ts_code_list=group_list,
                trade_date_list=trade_date_list,
                exchange=exchange
            )

        # 提示未覆盖的后缀（如上期所 .SHF），避免静默漏数据
        handled = tuple(suffix_exchange_map.keys())
        unmatched = [c for c in ts_code_list if not c.endswith(handled)]
        if unmatched:
            logger.warning(f"以下 {len(unmatched)} 个合约的后缀未配置交易所映射，未拉取: {unmatched[:10]}{'...' if len(unmatched) > 10 else ''}")

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
        tuShareOptDailyServiceTest.refresh_opt_daily_by_ts_code()

    except Exception as e:
        logger.error(f"处理失败: {e}")
        import traceback
        traceback.print_exc()

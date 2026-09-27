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
    def load_ts_code_list_from_basic(self, symbol_prefix='510050'):
        """
        从 ClickHouse opt_basic 最新快照动态加载目标标的的合约清单

        SSE ETF 期权的 ts_code 是 8 位数字（如 10000201.SH），无语义规律且每月有新合约上市，
        硬编码不可行，必须从 opt_basic 快照（含 symbol 字段）按标的前缀过滤。

        Args:
            symbol_prefix: 标的代码前缀，默认 '510050'（华夏上证50ETF期权）

        Returns:
            list[str]: 合约代码列表
        """
        # 取快照中 symbol 前缀匹配的最新一天数据（快照按天全量刷新，取最新即可）
        sql = f"""
        SELECT DISTINCT ts_code
        FROM indexsysdb.df_tushare_opt_basic
        WHERE symbol LIKE '{symbol_prefix}%'
          AND trade_date = (
              SELECT max(trade_date) FROM indexsysdb.df_tushare_opt_basic
              WHERE symbol LIKE '{symbol_prefix}%'
          )
        ORDER BY ts_code
        """
        df = ClickhouseService.getDataFrameWithoutColumnsName(sql)

        if df is None or df.empty or 'ts_code' not in df.columns:
            logger.error(f"opt_basic 快照中未找到 symbol LIKE '{symbol_prefix}%' 的合约，"
                         f"请先运行 TuShareOptBasicServiceTest.refresh_opt_basic 刷新基础信息")
            raise ValueError(f"No contracts found for symbol prefix '{symbol_prefix}' in opt_basic snapshot")

        ts_code_list = df['ts_code'].astype(str).tolist()
        logger.info(f"从 opt_basic 最新快照加载到 {len(ts_code_list)} 个 {symbol_prefix} 期权合约")
        return ts_code_list

    @classmethod
    def refresh_opt_daily_by_ts_code(self):

        tuShareService = TuShareOptDailyService()

        # 510050（华夏上证50ETF）期权合约清单，从 opt_basic 最新快照动态加载
        ts_code_list = self.load_ts_code_list_from_basic(symbol_prefix='510050')

        calendarService = CalendarService()
        start_date = calendarService.calculate_T_minus_n_days(CommonParameters.today, days=300)
        end_date = CommonParameters.today
        calendar_service = CalendarService()
        trade_date_list = calendar_service.calculate_dates_between_start_end_date(start_date, end_date)
        # 批量模式: 每个交易日只调1次API（vs 原来每个合约1次）
        tuShareService.refresh_opt_daily_by_ts_code_list(
            ts_code_list=ts_code_list,
            trade_date_list=trade_date_list,
            exchange="SSE"
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
        tuShareOptDailyServiceTest.refresh_opt_daily_by_ts_code()

    except Exception as e:
        logger.error(f"处理失败: {e}")
        import traceback
        traceback.print_exc()

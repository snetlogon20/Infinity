from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib
import pandas as pd
from datetime import datetime

logger = CommonLib.logger

class TuShareUSDIndexDailyService(TuShareService):
    @classmethod
    def prepareDataFrame(self, start_date, end_date):
        """
        从 ClickHouse 读取外汇数据并计算美元指数
        """
        logger.info("prepareData started")

        try:
            # 查询所有需要的外汇对数据
            query_sql = """
            SELECT 
                c.trade_date as trade_date,
                -- 开盘价
                USDJPY.bid_open as USDJPY_bid_open,
                USDJPY.ask_open as USDJPY_ask_open,
                USDHKD.bid_open as USDHKD_bid_open,
                USDHKD.ask_open as USDHKD_ask_open,
                USDCNH.bid_open as USDCNH_bid_open,
                USDCNH.ask_open as USDCNH_ask_open,
                USDCHF.bid_open as USDCHF_bid_open,
                USDCHF.ask_open as USDCHF_ask_open,
                USDCAD.bid_open as USDCAD_bid_open,
                USDCAD.ask_open as USDCAD_ask_open,
                NZDUSD.bid_open as NZDUSD_bid_open,
                NZDUSD.ask_open as NZDUSD_ask_open,
                GBPUSD.bid_open as GBPUSD_bid_open,
                GBPUSD.ask_open as GBPUSD_ask_open,
                EURUSD.bid_open as EURUSD_bid_open,
                EURUSD.ask_open as EURUSD_ask_open,
                AUDUSD.bid_open as AUDUSD_bid_open,
                AUDUSD.ask_open as AUDUSD_ask_open,
                USDSEK.bid_open as USDSEK_bid_open,
                USDSEK.ask_open as USDSEK_ask_open,
                -- 收盘价
                USDJPY.bid_close as USDJPY_bid_close,
                USDJPY.ask_close as USDJPY_ask_close,
                USDHKD.bid_close as USDHKD_bid_close,
                USDHKD.ask_close as USDHKD_ask_close,
                USDCNH.bid_close as USDCNH_bid_close,
                USDCNH.ask_close as USDCNH_ask_close,
                USDCHF.bid_close as USDCHF_bid_close,
                USDCHF.ask_close as USDCHF_ask_close,
                USDCAD.bid_close as USDCAD_bid_close,
                USDCAD.ask_close as USDCAD_ask_close,
                NZDUSD.bid_close as NZDUSD_bid_close,
                NZDUSD.ask_close as NZDUSD_ask_close,
                GBPUSD.bid_close as GBPUSD_bid_close,
                GBPUSD.ask_close as GBPUSD_ask_close,
                EURUSD.bid_close as EURUSD_bid_close,
                EURUSD.ask_close as EURUSD_ask_close,
                AUDUSD.bid_close as AUDUSD_bid_close,
                AUDUSD.ask_close as AUDUSD_ask_close,
                USDSEK.bid_close as USDSEK_bid_close,
                USDSEK.ask_close as USDSEK_ask_close,
                -- 计算美元指数 (使用 ask_close 中间价) - 修正：需要乘以常数因子 50.14348112
                50.14348112 * pow(1/EURUSD.ask_close, 0.576) *
                pow(USDJPY.ask_close, 0.136) *
                pow(1/GBPUSD.ask_close, 0.119) *
                pow(USDCAD.ask_close, 0.091) *
                pow(USDSEK.ask_close, 0.042) *
                pow(USDCHF.ask_close, 0.036) as USDX_index
            FROM indexsysdb.df_sys_calendar c
            LEFT JOIN indexsysdb.df_tushare_fx_daily USDJPY
                ON c.trade_date = USDJPY.trade_date 
                AND USDJPY.ts_code = 'USDJPY.FXCM'
            LEFT JOIN indexsysdb.df_tushare_fx_daily USDHKD
                ON c.trade_date = USDHKD.trade_date 
                AND USDHKD.ts_code = 'USDHKD.FXCM'
            LEFT JOIN indexsysdb.df_tushare_fx_daily USDCNH
                ON c.trade_date = USDCNH.trade_date 
                AND USDCNH.ts_code = 'USDCNH.FXCM'
            LEFT JOIN indexsysdb.df_tushare_fx_daily USDCHF
                ON c.trade_date = USDCHF.trade_date 
                AND USDCHF.ts_code = 'USDCHF.FXCM'
            LEFT JOIN indexsysdb.df_tushare_fx_daily USDCAD
                ON c.trade_date = USDCAD.trade_date 
                AND USDCAD.ts_code = 'USDCAD.FXCM'
            LEFT JOIN indexsysdb.df_tushare_fx_daily NZDUSD
                ON c.trade_date = NZDUSD.trade_date 
                AND NZDUSD.ts_code = 'NZDUSD.FXCM'
            LEFT JOIN indexsysdb.df_tushare_fx_daily GBPUSD
                ON c.trade_date = GBPUSD.trade_date 
                AND GBPUSD.ts_code = 'GBPUSD.FXCM'
            LEFT JOIN indexsysdb.df_tushare_fx_daily EURUSD
                ON c.trade_date = EURUSD.trade_date 
                AND EURUSD.ts_code = 'EURUSD.FXCM'
            LEFT JOIN indexsysdb.df_tushare_fx_daily AUDUSD
                ON c.trade_date = AUDUSD.trade_date 
                AND AUDUSD.ts_code = 'AUDUSD.FXCM'
            LEFT JOIN indexsysdb.df_tushare_fx_daily USDSEK
                ON c.trade_date = USDSEK.trade_date 
                AND USDSEK.ts_code = 'USDSEK.FXCM'
            WHERE c.trade_date >= '%s' 
              AND c.trade_date <= '%s'
            """ % (start_date, end_date)

            # 执行查询
            self.dataFrame = self.clickhouseClient.query_dataframe(query_sql)

            self.dataFrame = self.dataFrame.sort_values('trade_date', ascending=True)
            # 计算变化率：(下一个交易日的值 - 当前值) / 当前值 * 100
            self.dataFrame['pct_change'] = self.dataFrame['USDX_index'].pct_change() * 100

            logger.info("self.dataFrame.shape:" + str(self.dataFrame.shape))

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")

        return self.dataFrame


    @classmethod
    def saveDateToClickHouse(self):
        """
        将美元指数数据保存到 ClickHouse
        """
        logger.info("saveDateToClickHouse started")

        try:
            insert_sql = """
            INSERT INTO indexsysdb.df_tushare_usd_index_daily (
                trade_date,
                USDX_index,
                pct_change,
                USDJPY_bid_open, USDJPY_ask_open,
                USDHKD_bid_open, USDHKD_ask_open,
                USDCNH_bid_open, USDCNH_ask_open,
                USDCHF_bid_open, USDCHF_ask_open,
                USDCAD_bid_open, USDCAD_ask_open,
                NZDUSD_bid_open, NZDUSD_ask_open,
                GBPUSD_bid_open, GBPUSD_ask_open,
                EURUSD_bid_open, EURUSD_ask_open,
                AUDUSD_bid_open, AUDUSD_ask_open,
                USDSEK_bid_open, USDSEK_ask_open,
                USDJPY_bid_close, USDJPY_ask_close,
                USDHKD_bid_close, USDHKD_ask_close,
                USDCNH_bid_close, USDCNH_ask_close,
                USDCHF_bid_close, USDCHF_ask_close,
                USDCAD_bid_close, USDCAD_ask_close,
                NZDUSD_bid_close, NZDUSD_ask_close,
                GBPUSD_bid_close, GBPUSD_ask_close,
                EURUSD_bid_close, EURUSD_ask_close,
                AUDUSD_bid_close, AUDUSD_ask_close,
                USDSEK_bid_close, USDSEK_ask_close
            ) VALUES
            """

            # 确保 DataFrame 包含所有必需的列
            required_columns = [
                'trade_date',
                'pct_change',
                'USDX_index',
                'USDJPY_bid_open', 'USDJPY_ask_open',
                'USDHKD_bid_open', 'USDHKD_ask_open',
                'USDCNH_bid_open', 'USDCNH_ask_open',
                'USDCHF_bid_open', 'USDCHF_ask_open',
                'USDCAD_bid_open', 'USDCAD_ask_open',
                'NZDUSD_bid_open', 'NZDUSD_ask_open',
                'GBPUSD_bid_open', 'GBPUSD_ask_open',
                'EURUSD_bid_open', 'EURUSD_ask_open',
                'AUDUSD_bid_open', 'AUDUSD_ask_open',
                'USDSEK_bid_open', 'USDSEK_ask_open',
                'USDJPY_bid_close', 'USDJPY_ask_close',
                'USDHKD_bid_close', 'USDHKD_ask_close',
                'USDCNH_bid_close', 'USDCNH_ask_close',
                'USDCHF_bid_close', 'USDCHF_ask_close',
                'USDCAD_bid_close', 'USDCAD_ask_close',
                'NZDUSD_bid_close', 'NZDUSD_ask_close',
                'GBPUSD_bid_close', 'GBPUSD_ask_close',
                'EURUSD_bid_close', 'EURUSD_ask_close',
                'AUDUSD_bid_close', 'AUDUSD_ask_close',
                'USDSEK_bid_close', 'USDSEK_ask_close'
            ]

            # 检查是否所有列都存在
            for col in required_columns:
                if col not in self.dataFrame.columns:
                    logger.error(f"缺少列：{col}")
                    raise ValueError(f"DataFrame 缺少必需的列：{col}")

            dataValues = self.dataFrame[required_columns].to_dict('records')
            self.clickhouseClient.execute(insert_sql, dataValues)

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed")

    @classmethod
    def deleteDateFromClickHouse(self, start_date, end_date):
        """
        从 ClickHouse 删除指定日期范围的数据
        """
        logger.info("deleteDataFromClickHouse started")

        try:
            del_sql = "ALTER TABLE indexsysdb.df_tushare_usd_index_daily DELETE WHERE trade_date>= '%s' AND trade_date<='%s'" % (start_date, end_date)
            self.clickhouseClient.execute(del_sql)

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDataFromClickHouse completed")

import os
import sys

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.TuShareService.TuShareService import TuShareService

logger = CommonLib.logger


class TuShareFundDailyService(TuShareService):
    """ETF/LOF基金日线数据服务（TuShare fund_daily 接口）

    用途: 为 ETF 期权（如华夏上证50ETF 510050.SH）提供标的行情，
          供 OptionDailyIndicatorAnalyst 计算 spot_price / moneyness / IV / Greeks 使用。
    目标表: indexsysdb.df_tushare_fund_daily
    """

    # 场内期权标的 ETF 列表
    OPTION_UNDERLYING_ETF_LIST = [
        '510050.SH',  # 华夏上证50ETF（上证50ETF期权标的）
        '510300.SH',  # 华泰柏瑞沪深300ETF
        '510500.SH',  # 南方中证500ETF
        '588000.SH',  # 华夏科创50ETF
        '159915.SZ',  # 易方达创业板ETF
        '159919.SZ',  # 嘉实沪深300ETF
        '159922.SZ',  # 嘉实中证500ETF
    ]

    @classmethod
    def prepareDataFrame(self, ts_code, start_date, end_date):
        """获取基金日线数据（fund_daily 接口）"""
        logger.info("prepareData started")
        try:
            self.dataFrame = self.pro.fund_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")
        return self.dataFrame

    @classmethod
    def saveDateToClickHouse(self):
        """保存数据到 ClickHouse: indexsysdb.df_tushare_fund_daily"""
        logger.info("saveDateToClickHouse started")

        try:
            # TuShare fund_daily 接口列名对齐表结构：
            # 接口返回 vol，表列为 volume；接口无 change/pre_close 时补 0.0
            table_columns = ['ts_code', 'trade_date', 'open', 'high', 'low',
                             'close', 'pre_close', 'change', 'pct_chg', 'volume', 'amount']
            if 'vol' in self.dataFrame.columns:
                self.dataFrame = self.dataFrame.rename(columns={'vol': 'volume'})
            for col in table_columns:
                if col not in self.dataFrame.columns:
                    self.dataFrame[col] = 0.0
            self.dataFrame = self.dataFrame[table_columns]

            insert_df_tushare_fund_daily = \
                'insert into indexsysdb.df_tushare_fund_daily ' \
                '(ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,volume,amount) VALUES'
            dataValues = self.dataFrame.to_dict('records')
            self.clickhouseClient.execute(insert_df_tushare_fund_daily, dataValues)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed")

    @classmethod
    def deleteDateFromClickHouse(self, ts_code="", start_date="00000000", end_date="00000000"):
        """删除数据: 按 ts_code + 日期范围 增量删除"""
        logger.info("deleteDateFromClickHouse started")

        try:
            del_df_tushare_sql = "ALTER TABLE indexsysdb.df_tushare_fund_daily DELETE where ts_code = '%s' and trade_date>= '%s' and trade_date<='%s'" % (ts_code, start_date, end_date)
            self.clickhouseClient.execute(del_df_tushare_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDateFromClickHouse completed")

    @classmethod
    def refresh_fund_data(self, ts_code, start_date, end_date):
        """
        刷新指定基金的日线数据

        参数:
        - ts_code: 基金代码 (例如: '510050.SH' 华夏上证50ETF)
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')
        """
        try:
            csvFilePath = os.path.join(
                CommonParameters.outBoundPath,
                f"df_tushare_fund_daily_{ts_code.replace('.', '_')}.csv")

            logger.info(f"开始获取基金 {ts_code} 的日线数据...")
            logger.info(f"日期范围: {start_date} 至 {end_date}")

            tuShareService = TuShareFundDailyService()
            dataFrame = tuShareService.prepareDataFrame(ts_code=ts_code, start_date=start_date, end_date=end_date)

            if dataFrame.empty:
                logger.warning(f"没有获取到基金 {ts_code} 的数据")
                return

            logger.info(f"获取到 {len(dataFrame)} 条记录")
            logger.info(f"数据日期范围: {dataFrame['trade_date'].min()} 至 {dataFrame['trade_date'].max()}")

            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(ts_code=ts_code, start_date=start_date, end_date=end_date)
            tuShareService.saveDateToClickHouse()

            logger.info(f"成功刷新基金 {ts_code} 的 {len(dataFrame)} 条日线数据")

        except Exception as e:
            logger.error(f"刷新基金 {ts_code} 数据失败：{str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise e

    @classmethod
    def refresh_multiple_funds(self, fund_list, start_date, end_date):
        """
        批量刷新多个基金的日线数据

        参数:
        - fund_list: 基金代码列表
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')
        """
        logger.info("=" * 80)
        logger.info(f"开始批量刷新 {len(fund_list)} 个基金的日线数据")
        logger.info(f"日期范围: {start_date} 至 {end_date}")
        logger.info("=" * 80)

        success_count = 0
        fail_count = 0

        for idx, ts_code in enumerate(fund_list, 1):
            logger.info(f"\n[{idx}/{len(fund_list)}] 处理基金: {ts_code}")
            try:
                self.refresh_fund_data(ts_code, start_date, end_date)
                success_count += 1
                logger.info(f"{ts_code} 刷新成功")
            except Exception as e:
                fail_count += 1
                logger.error(f"{ts_code} 刷新失败: {str(e)}")
                continue

        logger.info("\n" + "=" * 80)
        logger.info("批量刷新完成！")
        logger.info(f"成功: {success_count} 个")
        logger.info(f"失败: {fail_count} 个")
        logger.info("=" * 80)

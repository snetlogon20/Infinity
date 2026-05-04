import os

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys

logger = CommonLib.logger

class TuShareCNIndexDailyService(TuShareService):
    @classmethod
    def prepareDataFrame(self, ts_code, start_date, end_date):
        logger.info("prepareData started")
        try:
            self.dataFrame = self.pro.index_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")

        return self.dataFrame

    @classmethod
    def saveDateToClickHouse(self):
        logger.info("saveDateToClickHouse started")

        try:
            insert_df_tushare_cn_index_daily = 'insert into indexsysdb.df_tushare_cn_index_daily (ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount) VALUES'
            dataValues = self.dataFrame.to_dict('records')
            self.clickhouseClient.execute(insert_df_tushare_cn_index_daily, dataValues)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("saveDateToClickHouse completed")

    @classmethod
    def deleteDateFromClickHouse(self, ts_code="", start_date="00000000", end_date="00000000"):
        logger.info("deleteDataFromClickHouse started")

        try:
            del_df_tushare_sql = "ALTER TABLE indexsysdb.df_tushare_cn_index_daily DELETE where ts_code = '%s' and trade_date>= '%s' and trade_date<='%s'" % (ts_code, start_date, end_date)
            self.clickhouseClient.execute(del_df_tushare_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name, event="ALTER TABLE indexsysdb.df_tushare_stock_daily Error")
            raise e

        logger.info("deleteDateFromClickHouse completed")

    @classmethod
    def refresh_index_data(self, ts_code, start_date, end_date):
        """
        刷新指定指数的日线数据

        参数:
        - ts_code: 指数代码 (例如: '000001.SH' 上证指数, '399001.SZ' 深证成指)
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')
        """
        try:
            csvFilePath = os.path.join(CommonParameters.outBoundPath, f"df_tushare_cn_index_daily_{ts_code.replace('.', '_')}.csv")

            logger.info(f"开始获取指数 {ts_code} 的日线数据...")
            logger.info(f"日期范围: {start_date} 至 {end_date}")

            tuShareService = TuShareCNIndexDailyService()
            dataFrame = tuShareService.prepareDataFrame(ts_code=ts_code, start_date=start_date, end_date=end_date)

            if dataFrame.empty:
                logger.warning(f"没有获取到指数 {ts_code} 的数据")
                return

            logger.info(f"获取到 {len(dataFrame)} 条记录")
            logger.info(f"数据列: {dataFrame.columns.tolist()}")
            logger.info(f"前5条数据:\n{dataFrame.head()}")
            logger.info(f"数据日期范围: {dataFrame['trade_date'].min()} 至 {dataFrame['trade_date'].max()}")

            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(ts_code=ts_code, start_date=start_date, end_date=end_date)
            tuShareService.saveDateToClickHouse()

            logger.info(f"✅ 成功刷新指数 {ts_code} 的 {len(dataFrame)} 条日线数据")

        except Exception as e:
            logger.error(f" 刷新指数 {ts_code} 数据失败：{str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise e

    @classmethod
    def refresh_multiple_indexes(self, index_list, start_date, end_date):
        """
        批量刷新多个指数的日线数据

        参数:
        - index_list: 指数代码列表
        - start_date: 开始日期 (格式: 'YYYYMMDD')
        - end_date: 结束日期 (格式: 'YYYYMMDD')
        """
        logger.info("=" * 80)
        logger.info(f"开始批量刷新 {len(index_list)} 个指数的日线数据")
        logger.info(f"日期范围: {start_date} 至 {end_date}")
        logger.info("=" * 80)

        success_count = 0
        fail_count = 0

        for idx, ts_code in enumerate(index_list, 1):
            logger.info(f"\n[{idx}/{len(index_list)}] 处理指数: {ts_code}")
            try:
                self.refresh_index_data(ts_code, start_date, end_date)
                success_count += 1
                logger.info(f"✅ {ts_code} 刷新成功")
            except Exception as e:
                fail_count += 1
                logger.error(f"❌ {ts_code} 刷新失败: {str(e)}")
                continue

        logger.info("\n" + "=" * 80)
        logger.info(f"批量刷新完成！")
        logger.info(f"成功: {success_count} 个")
        logger.info(f"失败: {fail_count} 个")
        logger.info("=" * 80)
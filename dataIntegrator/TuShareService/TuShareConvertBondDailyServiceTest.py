import time
import os
from dataIntegrator.TuShareService.TuShareService import TuShareService
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.TuShareService.TuShareConvertBondDailyService import TuShareConvertBondDailyService
from dataIntegrator.common.CommonDataParameters import CommonDataParameters

logger = CommonLib.logger

class TuShareConvertBondDailyServiceTest(TuShareService):

    @classmethod
    def refresh_cb_daily(self, ts_code=None, start_date=None, end_date=None):
        """
        刷新可转债日线行情数据
        
        Args:
            ts_code: 转债代码（可选，不指定则获取所有可转债）
            start_date: 开始日期 (YYYYMMDD)，默认为最近30天
            end_date: 结束日期 (YYYYMMDD)，默认为今天
        """
        try:
            # 设置默认日期范围
            if end_date is None:
                end_date = CommonParameters.today
            if start_date is None:
                start_date = CommonDataParameters.get_start_date(days=10)
            
            csvFilePath = os.path.join(CommonParameters.outBoundPath, "df_tushare_cb_daily.csv")

            tuShareService = TuShareConvertBondDailyService()
            
            logger.info(f"开始获取可转债日线数据...")
            logger.info(f"  - 转债代码: {ts_code if ts_code else '全部'}")
            logger.info(f"  - 日期范围: {start_date} ~ {end_date}")
            
            # 获取数据
            dataFrame = tuShareService.prepareDataFrame(
                ts_code=ts_code, 
                start_date=start_date, 
                end_date=end_date
            )

            logger.info(f"获取到 {len(dataFrame)} 条可转债日线记录")
            
            if len(dataFrame) == 0:
                logger.warning("未获取到任何数据，退出")
                return

            # 保存到 CSV（用于验证）
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            logger.info(f"数据已保存到: {csvFilePath}")

            # 先删除旧数据，再插入新数据
            logger.info("开始删除 ClickHouse 中的旧数据...")
            tuShareService.deleteDateFromClickHouse(
                ts_code=ts_code if ts_code else "",
                start_date=start_date,
                end_date=end_date
            )
            
            logger.info("开始保存数据到 ClickHouse...")
            tuShareService.saveDateToClickHouse()

            logger.info("✅ 可转债日线数据处理完成")
            logger.info(f"   - 成功保存 {len(dataFrame)} 条记录")

        except Exception as e:
            logger.error(f"❌ 可转债日线数据处理失败：{str(e)}")
            import traceback
            traceback.print_exc()
            raise e

    @classmethod
    def test_single_bond(self, ts_code="110030.SH"):
        """
        测试单个可转债的日线数据
        
        Args:
            ts_code: 转债代码，默认为 110030.SH
        """
        logger.info(f"测试单个可转债: {ts_code}")
        
        # 获取最近360天的数据
        end_date = CommonParameters.today
        start_date = CommonDataParameters.get_start_date(days=360)
        
        self.refresh_cb_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)

if __name__ == '__main__':
    tuShareCbDailyServiceTest = TuShareConvertBondDailyServiceTest()
    
    try:
        logger.info("=" * 80)
        logger.info("开始处理可转债日线数据...")
        logger.info("=" * 80)
        
        # 方式1: 获取所有可转债最近30天的数据
        end_date = CommonParameters.today
        start_date = CommonDataParameters.get_start_date(days=10)
        tuShareCbDailyServiceTest.refresh_cb_daily(None, start_date, end_date)
        
        # 方式2: 获取指定可转债的数据（取消注释使用）
        # tuShareCbDailyServiceTest.test_single_bond(ts_code="110030.SH")
        
        logger.info("=" * 80)
        logger.info("可转债日线数据处理完成")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"处理失败: {e}")
        import traceback
        traceback.print_exc()

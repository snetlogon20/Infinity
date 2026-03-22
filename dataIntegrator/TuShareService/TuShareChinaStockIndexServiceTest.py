from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib
import os
from dataIntegrator import CommonParameters
from dataIntegrator.TuShareService.TuShareChinaStockIndexService import TuShareChinaStockIndexService

logger = CommonLib.logger

class TuShareChinaStockIndexServiceTest(TuShareService):
    @classmethod
    def refresh_shanghai_index(self):
        try:
            ts_code = '000001.SH'  # 上证指数
            start_date = '20240101'
            end_date = '20261231'

            csvFilePath = os.path.join(CommonParameters.outBoundPath, "df_tushare_china_stock_index_2025.csv")

            tuShareService = TuShareChinaStockIndexService()
            dataFrame = tuShareService.prepareDataFrame(ts_code, start_date, end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(ts_code, start_date, end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            logger.info('Exception', e)
            raise e

    @classmethod
    def refresh_any_china_stock_index(self):
        """批量处理多个股票"""
        # 定义股票列表
        stock_list = [
            {'ts_code': '002093.SZ', 'name': '国脉科技'},
            {'ts_code': '600490.SH', 'name': '鹏欣资源'},
            {'ts_code': '000902.SZ', 'name': '新洋丰'},
            {'ts_code': '601368.SH', 'name': '绿城水务'},
            {'ts_code': '603839.SH', 'name': '安正时尚'}
        ]

        # 设置日期范围
        start_date = '20250101'
        end_date = CommonParameters.today

        logger.info(f"开始批量处理 {len(stock_list)} 只股票...")

        for stock in stock_list:
            ts_code = stock['ts_code']
            name = stock['name']

            try:
                logger.info(f"\n{'=' * 60}")
                logger.info(f"正在处理：{name} ({ts_code})")
                logger.info(f"{'=' * 60}")


                csvFilePath = os.path.join(CommonParameters.outBoundPath,
                                           f"df_tushare_{ts_code.replace('.', '_')}_{start_date[:4]}.csv")

                tuShareService = TuShareChinaStockIndexService()
                dataFrame = tuShareService.prepareDataFrame(ts_code, start_date, end_date)

                if dataFrame.empty:
                    logger.warning(f"{name} ({ts_code}) 没有获取到数据，跳过...")
                    continue

                logger.info(f"转换数据为 JSON...")
                jsonString = tuShareService.convertDataFrame2JSON()
                logger.info(f"保存到：{csvFilePath}")
                tuShareService.saveDateFrameToDisk(csvFilePath)
                tuShareService.deleteDateFromClickHouse(ts_code, start_date, end_date)
                tuShareService.saveDateToClickHouse()

                logger.info(f"✅ {name} ({ts_code}) 处理完成！")

            except Exception as e:
                logger.error(f"❌ {name} ({ts_code}) 处理失败：{str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                continue

        logger.info(f"\n{'=' * 60}")
        logger.info(f"批量处理完成！共处理 {len(stock_list)} 只股票")
        logger.info(f"{'=' * 60}")

if __name__ == '__main__':
    tuShareChinaStockIndexServiceTest = TuShareChinaStockIndexServiceTest()
    # tuShareChinaStockIndexServiceTest.refresh_shanghai_index()
    tuShareChinaStockIndexServiceTest.refresh_any_china_stock_index()

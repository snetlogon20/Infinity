from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib
import os
from dataIntegrator import CommonParameters
from dataIntegrator.TuShareService.TuShareIndexGlobalService import TuShareIndexGlobalService
from dataIntegrator.common.CommonDataParameters import CommonDataParameters

logger = CommonLib.logger

class TuShareIndexGlobalServiceTest(TuShareService):

    @classmethod
    def refresh_global_indexes(self):
        """批量处理多个全球指数"""
        # 定义全球指数列表
        index_list = [
            {'ts_code': 'XIN9', 'name': '富时中国A50指数'},
            {'ts_code': 'HSI', 'name': '恒生指数'},
            {'ts_code': 'HKTECH', 'name': '恒生科技指数'},
            {'ts_code': 'HKAH', 'name': '恒生AH股H指数'},
            {'ts_code': 'DJI', 'name': '道琼斯工业指数'},
            {'ts_code': 'SPX', 'name': '标普500指数'},
            {'ts_code': 'IXIC', 'name': '纳斯达克指数'},
            {'ts_code': 'FTSE', 'name': '富时100指数'},
            {'ts_code': 'FCHI', 'name': '法国CAC40指数'},
            {'ts_code': 'GDAXI', 'name': '德国DAX指数'},
            {'ts_code': 'N225', 'name': '日经225指数'},
            {'ts_code': 'KS11', 'name': '韩国综合指数'},
            {'ts_code': 'AS51', 'name': '澳大利亚标普200指数'},
            {'ts_code': 'SENSEX', 'name': '印度孟买SENSEX指数'},
            {'ts_code': 'IBOVESPA', 'name': '巴西IBOVESPA指数'},
            {'ts_code': 'RTS', 'name': '俄罗斯RTS指数'},
            {'ts_code': 'TWII', 'name': '台湾加权指数'},
            {'ts_code': 'CKLSE', 'name': '马来西亚指数'},
            {'ts_code': 'SPTSX', 'name': '加拿大S&P/TSX指数'},
            {'ts_code': 'CSX5P', 'name': 'STOXX欧洲50指数'},
            {'ts_code': 'RUT', 'name': '罗素2000指数'}
        ]

        # 设置日期范围
        start_date = '20250101'
        end_date = CommonParameters.today

        logger.info(f"开始批量处理 {len(index_list)} 个全球指数...")

        for index in index_list:
            ts_code = index['ts_code']
            name = index['name']

            try:
                logger.info(f"\n{'=' * 60}")
                logger.info(f"正在处理：{name} ({ts_code})")
                logger.info(f"{'=' * 60}")


                csvFilePath = os.path.join(CommonParameters.outBoundPath,
                                           f"df_tushare_{ts_code}_{start_date[:4]}.csv")

                tuShareService = TuShareIndexGlobalService()
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
        logger.info(f"批量处理完成！共处理 {len(index_list)} 个全球指数")
        logger.info(f"{'=' * 60}")

if __name__ == '__main__':
    tuShareIndexGlobalServiceTest = TuShareIndexGlobalServiceTest()
    tuShareIndexGlobalServiceTest.refresh_global_indexes()


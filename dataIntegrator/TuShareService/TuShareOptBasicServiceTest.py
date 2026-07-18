import os
from dataIntegrator.TuShareService.TuShareService import TuShareService
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.TuShareService.TuShareOptBasicService import TuShareOptBasicService

logger = CommonLib.logger

class TuShareOptBasicServiceTest(TuShareService):

    @classmethod
    def refresh_opt_basic(self):
        """
        刷新期权基础信息数据（全量）
        可指定交易所，如 DCE（大商所）、SSE（上交所）、CFFEX（中金所）等
        """
        try:
            # 设置文件路径
            csvFilePath = os.path.join(CommonParameters.outBoundPath, "df_tushare_opt_basic.csv")

            # 创建服务实例
            tuShareService = TuShareOptBasicService()

            # 拉取数据（传空字符串获取所有交易所，传指定交易所如 'DCE' 获取单交易所）
            dataFrame = tuShareService.prepareDataFrame(exchange='')

            if dataFrame.empty:
                logger.warning("期权基础信息数据为空，跳过处理")
                return

            logger.info(f"获取到 {len(dataFrame)} 条期权基础信息记录")

            # 转换并保存
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)

            # 先删除旧数据，再插入新数据
            tuShareService.deleteDateFromClickHouse()
            tuShareService.saveDateToClickHouse()

            logger.info(f"✅ 期权基础信息处理完成，共 {len(dataFrame)} 条记录")

        except Exception as e:
            logger.error(f"❌ 期权基础信息处理失败：{str(e)}")
            import traceback
            logger.error(traceback.format_exc())

if __name__ == '__main__':
    tuShareOptBasicServiceTest = TuShareOptBasicServiceTest()
    tuShareOptBasicServiceTest.refresh_opt_basic()

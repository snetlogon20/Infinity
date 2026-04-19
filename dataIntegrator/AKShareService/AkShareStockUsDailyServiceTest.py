from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.AKShareService.AkShareStockUsDailyService import AkShareStockUsDailyService
from dataIntegrator.common.FileType import FileType
import os

logger = CommonLib.logger

class AkShareStockUsDailyServiceTest:

    def test1_callAkShareStockUsDailyService(cls, symbol='AAPL', adjust=''):
        logger.info("callAkShareStockUsDailyService started...")

        file_path = os.path.join(CommonParameters.outBoundPath, f'akshare_stock_us_daily_{symbol}.xlsx')

        try:
            akShareService = AkShareStockUsDailyService()

            # 获取原始数据
            dataFrame = akShareService.prepareDataFrame(symbol=symbol, adjust=adjust)

            # 保存到磁盘
            akShareService.saveDateFrameToDisk(dataFrame, file_path, FileType.EXCEL)

            # 从磁盘读取
            dataFrame = akShareService.readDataFrameFromDisk(file_path, FileType.EXCEL)

            # 删除 ClickHouse 中的旧数据
            akShareService.deleteDateFromClickHouse(symbol=symbol)

            # 转换数据格式
            dataFrame = akShareService.transformDataFrame(dataFrame)

            # 保存到 ClickHouse
            akShareService.saveDateToClickHouse(dataFrame)

        except Exception as e:
            logger.info('Exception: %s', e)
            raise e

        logger.info("callAkShareStockUsDailyService ended...")

if __name__ == '__main__':
    akShareStockUsDailyServiceTest = AkShareStockUsDailyServiceTest()

    #US_STOCK_LIST = CommonParameters.US_STOCK_LIST
    US_STOCK_LIST = ["SPY", "C", "JPM", "AAPL","NVDA","GS","MS","GE"]

    # 循环处理所有美股
    for symbol in CommonParameters.US_STOCK_LIST:
        try:
            logger.info(f"开始处理股票: {symbol}")

            # 测试未复权数据
            akShareStockUsDailyServiceTest.test1_callAkShareStockUsDailyService(symbol=symbol, adjust='')

            logger.info(f"股票 {symbol} 处理完成\n")

        except Exception as e:
            logger.error(f"股票 {symbol} 处理失败: {e}")
            continue

    # 测试前复权数据
    # for symbol in CommonParameters.US_STOCK_LIST:
    #     try:
    #         logger.info(f"开始处理股票: {symbol}")
    #
    #         # 测试未复权数据
    #         akShareStockUsDailyServiceTest.test1_callAkShareStockUsDailyService(symbol=symbol, adjust='qfq')
    #
    #         logger.info(f"股票 {symbol} 处理完成\n")
    #
    #     except Exception as e:
    #         logger.error(f"股票 {symbol} 处理失败: {e}")
    #         continue
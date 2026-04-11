from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.AKShareService.AkShareMacroChinaNewHousePriceService import AkShareMacroChinaNewHousePriceService
from dataIntegrator.common.FileType import FileType
import os

logger = CommonLib.logger

class AkShareMacroChinaNewHousePriceServiceTest:

    def test1_callAkShareMacroChinaNewHousePriceService(cls):
        logger.info("callAkShareMacroChinaNewHousePriceService started...")

        # 新建商品住宅价格指数数据不需要日期范围，获取全部历史数据
        file_path = os.path.join(CommonParameters.outBoundPath, 'macro_china_new_house_price.xlsx')

        try:
            akShareService = AkShareMacroChinaNewHousePriceService()

            # 获取数据（使用默认城市：北京和上海）
            dataFrame = akShareService.prepareDataFrame(city_first="北京", city_second="上海")

            # 保存到磁盘
            akShareService.saveDateFrameToDisk(dataFrame, file_path, FileType.EXCEL)

            # 从磁盘读取
            dataFrame = akShareService.readDataFrameFromDisk(file_path, FileType.EXCEL)

            # 删除 ClickHouse 中的旧数据（使用最早和最晚的日期）
            if not dataFrame.empty:
                min_date = dataFrame['date'].min()
                max_date = dataFrame['date'].max()
                akShareService.deleteDateFromClickHouse(min_date, max_date)

            # 转换数据格式
            dataFrame = akShareService.transformDataFrame(dataFrame)

            # 保存到 ClickHouse
            akShareService.saveDateToClickHouse(dataFrame)

        except Exception as e:
            logger.info('Exception: %s', e)
            raise e

        logger.info("callAkShareMacroChinaNewHousePriceService ended...")

if __name__ == '__main__':
    akShareMacroChinaNewHousePriceServiceTest = AkShareMacroChinaNewHousePriceServiceTest()
    akShareMacroChinaNewHousePriceServiceTest.test1_callAkShareMacroChinaNewHousePriceService()

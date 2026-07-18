from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.AKShareService.AkShareMacroUsaNonFarmService import AkShareMacroUsaNonFarmService
from dataIntegrator.common.FileType import FileType
import os

logger = CommonLib.logger

class AkShareMacroUsaNonFarmServiceTest:

    def test1_callAkShareMacroUsaNonFarmService(cls):
        logger.info("callAkShareMacroUsaNonFarmService started...")

        # 美国非农就业人数数据不需要日期范围，获取全部历史数据
        file_path = os.path.join(CommonParameters.outBoundPath, 'macro_usa_non_farm.xlsx')

        try:
            akShareService = AkShareMacroUsaNonFarmService()

            # 获取数据（不需要日期参数）
            dataFrame = akShareService.prepareDataFrame()

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

        logger.info("callAkShareMacroUsaNonFarmService ended...")

if __name__ == '__main__':
    akShareMacroUsaNonFarmServiceTest = AkShareMacroUsaNonFarmServiceTest()
    akShareMacroUsaNonFarmServiceTest.test1_callAkShareMacroUsaNonFarmService()

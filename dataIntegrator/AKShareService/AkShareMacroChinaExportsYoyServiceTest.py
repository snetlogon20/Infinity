# D:\workspace_python\infinity\dataIntegrator\AKShareService\AkShareMacroChinaExportsYoyServiceTest.py
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.AKShareService.AkShareMacroChinaExportsYoyService import AkShareMacroChinaExportsYoyService
from dataIntegrator.common.FileType import FileType
import os

logger = CommonLib.logger

class AkShareMacroChinaExportsYoyServiceTest:

    def test1_callAkShareMacroChinaExportsYoyService(cls):
        logger.info("callAkShareMacroChinaExportsYoyService started...")

        # 出口同比增速数据不需要日期范围，获取全部历史数据
        file_path = os.path.join(CommonParameters.outBoundPath, 'macro_china_exports_yoy.xlsx')

        try:
            akShareService = AkShareMacroChinaExportsYoyService()

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

        logger.info("callAkShareMacroChinaExportsYoyService ended...")

if __name__ == '__main__':
    akShareMacroChinaExportsYoyServiceTest = AkShareMacroChinaExportsYoyServiceTest()
    akShareMacroChinaExportsYoyServiceTest.test1_callAkShareMacroChinaExportsYoyService()

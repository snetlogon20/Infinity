# D:\workspace_python\infinity\dataIntegrator\AKShareService\AkShareMacroChinaFxGoldServiceTest.py
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.AKShareService.AkShareMacroChinaFxGoldService import AkShareMacroChinaFxGoldService
from dataIntegrator.common.FileType import FileType
import os

logger = CommonLib.logger

class AkShareMacroChinaFxGoldServiceTest:

    def test1_callAkShareMacroChinaFxGoldService(cls):
        logger.info("callAkShareMacroChinaFxGoldService started...")

        # 外汇和黄金储备数据不需要日期范围，获取全部历史数据
        file_path = os.path.join(CommonParameters.outBoundPath, 'macro_china_fx_gold.xlsx')

        try:
            akShareService = AkShareMacroChinaFxGoldService()

            # 获取数据（不需要日期参数）
            dataFrame = akShareService.prepareDataFrame()

            # 保存到磁盘
            akShareService.saveDateFrameToDisk(dataFrame, file_path, FileType.EXCEL)

            # 从磁盘读取
            dataFrame = akShareService.readDataFrameFromDisk(file_path, FileType.EXCEL)

            # 删除 ClickHouse 中的旧数据（使用最早和最晚的月份）
            if not dataFrame.empty:
                min_month = dataFrame['month'].min()
                max_month = dataFrame['month'].max()
                akShareService.deleteDateFromClickHouse(min_month, max_month)

            # 转换数据格式
            dataFrame = akShareService.transformDataFrame(dataFrame)

            # 保存到 ClickHouse
            akShareService.saveDateToClickHouse(dataFrame)

        except Exception as e:
            logger.info('Exception: %s', e)
            raise e

        logger.info("callAkShareMacroChinaFxGoldService ended...")

if __name__ == '__main__':
    akShareMacroChinaFxGoldServiceTest = AkShareMacroChinaFxGoldServiceTest()
    akShareMacroChinaFxGoldServiceTest.test1_callAkShareMacroChinaFxGoldService()

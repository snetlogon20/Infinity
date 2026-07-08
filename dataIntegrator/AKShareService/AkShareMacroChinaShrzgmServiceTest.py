# D:\workspace_python\infinity\dataIntegrator\AKShareService\AkShareMacroChinaShrzgmServiceTest.py
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.AKShareService.AkShareMacroChinaShrzgmService import AkShareMacroChinaShrzgmService
from dataIntegrator.common.FileType import FileType
import os

logger = CommonLib.logger

class AkShareMacroChinaShrzgmServiceTest:

    def test1_callAkShareMacroChinaShrzgmService(cls):
        logger.info("callAkShareMacroChinaShrzgmService started...")

        # 社会融资规模数据不需要日期范围，获取全部历史数据
        file_path = os.path.join(CommonParameters.outBoundPath, 'macro_china_shrzgm.xlsx')

        try:
            akShareService = AkShareMacroChinaShrzgmService()

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

        logger.info("callAkShareMacroChinaShrzgmService ended...")

if __name__ == '__main__':
    akShareMacroChinaShrzgmServiceTest = AkShareMacroChinaShrzgmServiceTest()
    akShareMacroChinaShrzgmServiceTest.test1_callAkShareMacroChinaShrzgmService()

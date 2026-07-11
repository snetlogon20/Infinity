# D:\workspace_python\infinity\dataIntegrator\AKShareService\AkShareBondZhUsRateServiceTest.py
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.AKShareService.AkShareBondZhUsRateService import AkShareBondZhUsRateService
from dataIntegrator.common.FileType import FileType
import os

logger = CommonLib.logger

class AkShareBondZhUsRateServiceTest:

    def test1_callAkShareBondZhUsRateService(cls, start_date="19901219"):
        logger.info("callAkShareBondZhUsRateService started...")

        file_path = os.path.join(CommonParameters.outBoundPath, 'bond_zh_us_rate.xlsx')

        try:
            akShareService = AkShareBondZhUsRateService()

            # 获取数据（支持指定起始日期，默认从 19901219 开始）
            dataFrame = akShareService.prepareDataFrame(start_date=start_date)

            # 保存到磁盘
            akShareService.saveDateFrameToDisk(dataFrame, file_path, FileType.EXCEL)

            # 从磁盘读取
            dataFrame = akShareService.readDataFrameFromDisk(file_path, FileType.EXCEL)

            # 删除 ClickHouse 中的旧数据（使用最早和最晚的日期）
            if not dataFrame.empty:
                min_date = dataFrame['trade_date'].min()
                max_date = dataFrame['trade_date'].max()
                akShareService.deleteDateFromClickHouse(min_date, max_date)

            # 转换数据格式
            dataFrame = akShareService.transformDataFrame(dataFrame)

            # 保存到 ClickHouse
            akShareService.saveDateToClickHouse(dataFrame)

        except Exception as e:
            logger.info('Exception: %s', e)
            raise e

        logger.info("callAkShareBondZhUsRateService ended...")

if __name__ == '__main__':
    akShareBondZhUsRateServiceTest = AkShareBondZhUsRateServiceTest()
    akShareBondZhUsRateServiceTest.test1_callAkShareBondZhUsRateService()

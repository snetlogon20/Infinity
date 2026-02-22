from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.AKShareService.AkShareFuturesForeignHistService import AkShareFuturesForeignHistService
from dataIntegrator.common.FileType import FileType
import os
import sys

logger = CommonLib.logger

class AkShareFuturesForeignHistServiceTest:

    def callAkShareFuturesForeignHistService(self, symbol='XAU', file_suffix='xau'):
        """
        统一的期货外盘历史数据测试方法

        Args:
            symbol (str): 期货品种代码，如 'XAU'(黄金), 'XAG'(白银), 'GC'(COMEX黄金)等
            file_suffix (str): 文件名后缀，用于区分不同品种
        """
        logger.info(f"callAkShareFuturesForeignHistService started... Symbol: {symbol}")

        file_path = os.path.join(CommonParameters.outBoundPath, f'akshare_futures_foreign_hist_{file_suffix}.xlsx')

        try:
            akShareService = AkShareFuturesForeignHistService()

            # 获取原始数据
            dataFrame = akShareService.prepareDataFrame(symbol)

            # 保存原始数据到Excel
            akShareService.saveDateFrameToDisk(dataFrame, file_path, FileType.EXCEL)

            # 从Excel读取数据
            dataFrame = akShareService.readDataFrameFromDisk(file_path, FileType.EXCEL)

            # 删除所有现有数据
            akShareService.deleteDateFromClickHouse()

            # 转换数据（计算涨跌幅等）
            transformed_dataFrame = akShareService.transformDataFrame(dataFrame)

            # 保存到ClickHouse（只保存表结构中存在的字段）
            akShareService.saveDateToClickHouse(transformed_dataFrame)

        except Exception as e:
            logger.info('Exception: %s', e)
            raise e

        logger.info(f"callAkShareFuturesForeignHistService ended... Symbol: {symbol}")

if __name__ == '__main__':
    akShareFuturesForeignHistServiceTest = AkShareFuturesForeignHistServiceTest()

    #akShareFuturesForeignHistServiceTest.callAkShareFuturesForeignHistService('XAU', 'XAU')
    #akShareFuturesForeignHistServiceTest.callAkShareFuturesForeignHistService('XAG', 'XAG')
    akShareFuturesForeignHistServiceTest.callAkShareFuturesForeignHistService('GC', 'GC')

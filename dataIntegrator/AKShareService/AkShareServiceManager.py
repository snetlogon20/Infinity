import os

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.AKShareService.AkShareSpotHistSGEService import AkShareSpotHistSGEService
from dataIntegrator.AKShareService.AkShareFuturesForeignHistService import AkShareFuturesForeignHistService
from dataIntegrator.common.FileType import FileType

logger = CommonLib.logger

class AkShareServiceManager():

    def __init__(self):
        logger.info("__init__ started")

    @classmethod
    def callAkShareSpotHistSGEService(self, param_dict):
        logger.info("callAkShareSpotHistSGEService started...")

        start_date = param_dict.get("start_date")
        end_date = param_dict.get("end_date")
        file_path = os.path.join(CommonParameters.outBoundPath, param_dict.get("file_name", "akshare_spot_hist_sge.xlsx"))

        try:
            akShareService = AkShareSpotHistSGEService()

            # 准备数据
            dataFrame = akShareService.prepareDataFrame(start_date, end_date)

            # 保存到磁盘
            akShareService.saveDateFrameToDisk(dataFrame, file_path, param_dict.get("file_type", FileType.EXCEL))

            # 从磁盘读取（可选步骤，用于验证）
            dataFrame = akShareService.readDataFrameFromDisk(file_path, param_dict.get("file_type", FileType.EXCEL))

            # 删除ClickHouse中的旧数据
            akShareService.deleteDateFromClickHouse(start_date, end_date)

            # 转换数据
            dataFrame = akShareService.transformDataFrame(dataFrame)

            # 保存到ClickHouse
            akShareService.saveDateToClickHouse(dataFrame)

        except Exception as e:
            logger.info('Exception: %s', e)
            raise e

        logger.info("callAkShareSpotHistSGEService ended...")

    @classmethod
    def callAkShareFuturesForeignHistService(self, param_dict):
        logger.info("callAkShareFuturesForeignHistService started...")

        symbol = param_dict.get("symbol")
        file_path = os.path.join(CommonParameters.outBoundPath, param_dict.get("file_name", f"akshare_futures_foreign_hist_{symbol.lower()}.xlsx"))

        try:
            akShareService = AkShareFuturesForeignHistService()

            # 准备数据
            dataFrame = akShareService.prepareDataFrame(symbol)

            # 保存到磁盘
            akShareService.saveDateFrameToDisk(dataFrame, file_path, param_dict.get("file_type", FileType.EXCEL))

            # 从磁盘读取（可选步骤，用于验证）
            dataFrame = akShareService.readDataFrameFromDisk(file_path, param_dict.get("file_type", FileType.EXCEL))

            # 删除ClickHouse中的旧数据
            akShareService.deleteDateFromClickHouse()

            # 转换数据
            dataFrame = akShareService.transformDataFrame(dataFrame)

            # 保存到ClickHouse
            akShareService.saveDateToClickHouse(dataFrame)

        except Exception as e:
            logger.info('Exception: %s', e)
            raise e

        logger.info("callAkShareFuturesForeignHistService ended...")

    @classmethod
    def callAkShareService(self, start_date = "20260101", end_date = CommonParameters.today):
        try:
            logger.info("callAkShareService started")

            # start_date = "20240101"
            # end_date = CommonParameters.today

            param_method_dict = {
                "callAkShareSpotHistSGEService": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "file_name": "akshare_spot_hist_sge_2024.xlsx",
                    "file_type": FileType.EXCEL
                },
                "callAkShareFuturesForeignHistService": {
                    "symbol": "XAU",  # 伦敦金
                    "file_name": "akshare_futures_foreign_hist_xau.xlsx",
                    "file_type": FileType.EXCEL
                }
            }

            # 按顺序调用方法
            for method_name, params in param_method_dict.items():
                try:
                    method = getattr(self, method_name)
                    method(params)
                except AttributeError as e:
                    logger.error(f"方法 {method_name} 不存在，请检查拼写！", e)
                except Exception as e:
                    logger.error(f"调用 {method_name} 失败: {e}")

            logger.info("callAkShareService completed successfully")

        except Exception as e:
            logger.error('==============================================')
            logger.error('Exception: %s', e)
            logger.error('==============================================')
            raise e

def main():
    akShareServiceManager = AkShareServiceManager()
    akShareServiceManager.callAkShareService()

if __name__ == '__main__':
    main()

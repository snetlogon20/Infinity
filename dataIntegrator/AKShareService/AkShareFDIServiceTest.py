from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.AKShareService.AkShareFDIService import AkShareFDIService

from dataIntegrator.common.FileType import FileType

logger = CommonLib.logger

class AkShareFDIServiceTest:
    def test1_read_write_data_frame(self):  # 修正方法签名，移除cls参数
        akShareFDIService = AkShareFDIService()
        dataFrame = akShareFDIService.readDataFrameFromDisk(
            rf"D:\workspace_python\infinity_data\inbound\akshare_fdi.csv",
            FileType.CSV)
        print(dataFrame)

        akShareFDIService.readDataFrameFromDisk(
            rf"D:\workspace_python\infinity_data\inbound\akshare_fdi.xlsx",
            FileType.EXCEL)
        print(dataFrame)

        # write data
        try:
            akShareFDIService.saveDateFrameToDisk(
                dataFrame,
                rf"d:\workspace_python\infinity_data\outbound\akshare_fdi.csv",
                FileType.CSV)

            akShareFDIService.saveDateFrameToDisk(
                dataFrame,
                rf"D:\workspace_python\infinity_data\outbound\akshare_fdi.xlsx",
                FileType.EXCEL)
        except ValueError as ve:
            print(f"值错误: {ve}")
        except FileNotFoundError as fe:
            print(f"文件未找到: {fe}")
        except PermissionError as pe:
            print(f"权限错误: {pe}")
        except Exception as e:
            print(f"未知错误: {type(e).__name__}: {e}")

    def test2_callAkShareFDIServiceTest(self):  # 修正方法签名，移除cls参数
        logger.info("callAkShareFDIService started...")

        start_date = '202401'  # 使用年月格式
        end_date = CommonParameters.today[:6]  # 使用年月格式
        file_path = rf"D:\workspace_python\infinity_data\inbound\akshare_fdi.xlsx"

        try:
            akShareService = AkShareFDIService()

            dataFrame = akShareService.prepareDataFrame(start_date, end_date)

            # akShareService.saveDateFrameToDisk(dataFrame,file_path,FileType.EXCEL)
            # dataFrame = akShareService.readDataFrameFromDisk(file_path,FileType.EXCEL)

            akShareService.deleteDateFromClickHouse(start_date, end_date)
            akShareService.saveDateToClickHouse(dataFrame)

        except Exception as e:
            logger.info('Exception: %s', e)
            raise e

        logger.info("callAkShareFDIService ended...")

if __name__ == '__main__':
    akShareFDIServiceTest = AkShareFDIServiceTest()
    # akShareFDIServiceTest.test1_read_write_data_frame()
    akShareFDIServiceTest.test2_callAkShareFDIServiceTest()

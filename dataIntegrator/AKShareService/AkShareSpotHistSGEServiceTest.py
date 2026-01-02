from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.AKShareService.AkShareSpotHistSGEService import AkShareSpotHistSGEService
from dataIntegrator.common.FileType import FileType
import os

logger = CommonLib.logger

class AkShareSpotHistSGEServiceTest:
    def test1_read_write_data_frame(cls):
        #read data
        akShareSpotHistSGEService = AkShareSpotHistSGEService()
        dataFrame = akShareSpotHistSGEService.readDataFrameFromDisk(
            os.path.join(CommonParameters.outBoundPath, 'sakshare_spot_hist_sge_dg.csv'),
            FileType.CSV)
        print(dataFrame)

        akShareSpotHistSGEService.readDataFrameFromDisk(
            os.path.join(CommonParameters.outBoundPath, 'sakshare_spot_hist_sge_dg.xlsx'),
            FileType.EXCEL)
        print(dataFrame)

        # write data
        try:
            akShareSpotHistSGEService.saveDateFrameToDisk(
                dataFrame,
                os.path.join(CommonParameters.outBoundPath, 'sakshare_spot_hist_sge_dg.csv'),
                FileType.CSV)

            akShareSpotHistSGEService.saveDateFrameToDisk(
                dataFrame,
                os.path.join(CommonParameters.outBoundPath, 'sakshare_spot_hist_sge_dg.xlsx'),
                FileType.EXCEL)
        except Exception as e:
            print(f"未知错误: {type(e).__name__}: {e}")

    def test2_callAkShareSpotHistSGEService(cls):
        logger.info("callAkShareSpotHistSGEServicee started...")

        start_date = '20240531'
        end_date = CommonParameters.today
        file_path = os.path.join(CommonParameters.outBoundPath,'sakshare_spot_hist_sge_dg.xlsx')

        try:
            akShareService = AkShareSpotHistSGEService()

            dataFrame = akShareService.prepareDataFrame(start_date, end_date)

            akShareService.saveDateFrameToDisk(dataFrame,file_path,FileType.EXCEL)
            dataFrame = akShareService.readDataFrameFromDisk(file_path,FileType.EXCEL)

            akShareService.deleteDateFromClickHouse(start_date, end_date)
            akShareService.saveDateToClickHouse(dataFrame)

        except Exception as e:
            logger.info('Exception: %s', e)
            raise e

        logger.info("callTushareSGEDailyService ended...")

if __name__ == '__main__':
    akShareSpotHistSGEServiceTest = AkShareSpotHistSGEServiceTest()
    akShareSpotHistSGEServiceTest.test1_read_write_data_frame()
    akShareSpotHistSGEServiceTest.test2_callAkShareSpotHistSGEService()


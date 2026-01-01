from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.AKShareService.AkShareSpotHistSGEService import AkShareSpotHistSGEService
from dataIntegrator.common.FileType import FileType

logger = CommonLib.logger

def test1_read_write_data_frame():
    #read data
    akShareSpotHistSGEService = AkShareSpotHistSGEService()
    dataFrame = akShareSpotHistSGEService.readDataFrameFromDisk(
        rf"D:\workspace_python\infinity_data\inbound\sakshare_spot_hist_sge_dg.csv",
        FileType.CSV)
    print(dataFrame)

    akShareSpotHistSGEService.readDataFrameFromDisk(
        rf"D:\workspace_python\infinity_data\inbound\sakshare_spot_hist_sge_dg.xlsx",
        FileType.EXCEL)
    print(dataFrame)

    # write data
    try:
        akShareSpotHistSGEService.saveDateFrameToDisk(
            dataFrame,
            rf"d:\workspace_python\infinity_data\outbound\sakshare_spot_hist_sge_dg.csv",
            FileType.CSV)

        akShareSpotHistSGEService.saveDateFrameToDisk(
            dataFrame,
            rf"D:\workspace_python\infinity_data\outbound\sakshare_spot_hist_sge_dg.xlsx",
            FileType.EXCEL)
    except ValueError as ve:
        print(f"值错误: {ve}")
    except FileNotFoundError as fe:
        print(f"文件未找到: {fe}")
    except PermissionError as pe:
        print(f"权限错误: {pe}")
    except Exception as e:
        print(f"未知错误: {type(e).__name__}: {e}")

def test2_callAkShareSpotHistSGEService():
    logger.info("callAkShareSpotHistSGEServicee started...")

    start_date = '20240531'
    end_date = CommonParameters.today
    file_path = rf"D:\workspace_python\infinity_data\inbound\sakshare_spot_hist_sge_dg.xlsx"

    try:
        akShareService = AkShareSpotHistSGEService()

        dataFrame = akShareService.prepareDataFrame(start_date, end_date)

        # akShareService.saveDateFrameToDisk(dataFrame,file_path,FileType.EXCEL)
        # dataFrame = akShareService.readDataFrameFromDisk(file_path,FileType.EXCEL)

        akShareService.deleteDateFromClickHouse(start_date, end_date)
        akShareService.saveDateToClickHouse(dataFrame)

    except Exception as e:
        logger.info('Exception: %s', e)
        raise e

    logger.info("callTushareSGEDailyService ended...")

if __name__ == '__main__':
    test1_read_write_data_frame()
    test2_callAkShareSpotHistSGEService()


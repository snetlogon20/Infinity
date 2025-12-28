from dataIntegrator.AKShareService.AkShareSpotHistSGEService import AkShareSpotHistSGEService
from dataIntegrator.common.FileType import FileType


def test_read_write_data_frame():
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

if __name__ == '__main__':
    test_read_write_data_frame()
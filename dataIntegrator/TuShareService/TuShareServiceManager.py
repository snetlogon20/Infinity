from dataIntegrator.TuShareService.TuShareCNIndexDailyService import TuShareCNIndexDailyService
from dataIntegrator.TuShareService.TuShareChinaStockIndexService import TuShareChinaStockIndexService
from dataIntegrator.TuShareService.TushareShiborDailyService import TushareShiborDailyService
from dataIntegrator.TuShareService.TushareShiborLPRDailyService import TushareShiborLPRDailyService
from dataIntegrator.TuShareService.TushareCNGDPService import TushareCNGDPService
from dataIntegrator.TuShareService.TushareCNMondySupplyService import TushareCNMondySupplyService
from dataIntegrator.TuShareService.TushareCNCPIService import TushareCNCPIService
from dataIntegrator.TuShareService.TuShareUSStockDailyService import TuShareUSStockDailyService
from dataIntegrator.TuShareService.TuShareFutureBasicInformationService import TuShareFutureBasicInformationService
from dataIntegrator.TuShareService.TuShareFutureDailyService import TuShareFutureDailyService
from dataIntegrator.TuShareService.TushareUSStockBasicService import TushareUSStockBasicService
from dataIntegrator.TuShareService.TuShareHKStockDailyService import TuShareHKStockDailyService
from dataIntegrator.TuShareService.TuShareFXOffsoreBasicService import TuShareFXOffsoreBasicService
from dataIntegrator.TuShareService.TuShareFXDailyService import TuShareFXDailyService
from dataIntegrator.TuShareService.TuShareSGEDailyService import TuShareSGEDailyService
from dataIntegrator.TuShareService.TushareUSTreasuryYieldCurveService import TushareUSTreasuryYieldCurveService
from dataIntegrator.common import CommonLib

class TuShareServiceManager(CommonLib.CommonLib):

    def __init__(self):
        print("__init__ started")

        print("__init__ completed")

    @classmethod
    def callTuShareCNIndexDailyService(self):
        print("callTuShareService started...")

        ts_code = '000001.SH'
        start_date = '20220521'
        end_date = '20241218'
        csvFilePath= "D:\workspace_python\dataIntegrator\dataIntegrator\data\outbound\df_tushare_df_tushare_cn_index_daily_20220507.csv"

        try:
            tuShareService = TuShareCNIndexDailyService()
            dataFrame = tuShareService.prepareDataFrame(ts_code,start_date,end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(ts_code,start_date,end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            print('Exception', e)
            raise e

        print("callTuShareService ended...")

    @classmethod
    def callTuShareChinaStockIndexService(self, ts_code = '603839.SH', start_date = '20220521', end_date = '20241230', csvFilePath= "D:\workspace_python\dataIntegrator\dataIntegrator\data\outbound\df_tushare_df_tushare_shibor_daily_20220507.csv"):
        print("callTuShareService started...")

        # 002093.SZ 国脉科技
        # 600490.SH 鹏欣资源
        # 000902.SZ 新洋丰
        # 601368.SH 绿城水务
        # 603839.SH 安正时尚
        # 000001.SH 上证综指

        # ts_code = '603839.SH'
        # start_date = '20220521'
        # end_date = '20241230'
        # csvFilePath= "D:\workspace_python\dataIntegrator\dataIntegrator\data\outbound\df_tushare_df_tushare_shibor_daily_20220507.csv"

        try:
            tuShareService = TuShareChinaStockIndexService()
            dataFrame = tuShareService.prepareDataFrame(ts_code,start_date,end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(ts_code,start_date,end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            print('Exception', e)
            raise e

        print("callTuShareService ended...")

    @classmethod
    def callTuShareShiborDailyService(self):
        print("callTuShareShiborDailyService started...")

        start_date = '20220101'
        end_date = '20220521'
        csvFilePath= "D:\workspace_python\dataIntegrator\dataIntegrator\data\outbound\df_tushare_df_tushare_shibor_daily_20220507.csv"

        try:
            tuShareService = TushareShiborDailyService()
            dataFrame = tuShareService.prepareDataFrame(start_date,end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date,end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            print('Exception', e)
            raise e

        print("callTuShareShiborDailyService ended...")

    @classmethod
    def callTushareShiborLPRDailyService(self):
        print("callTuShareShiborDailyService started...")

        start_date = '20220101'
        end_date = '20220521'
        csvFilePath= "D:\workspace_python\dataIntegrator\dataIntegrator\data\outbound\df_tushare_df_tushare_shibor_lpr_daily_20220507.csv"

        try:
            tuShareService = TushareShiborLPRDailyService()
            dataFrame = tuShareService.prepareDataFrame(start_date, end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date, end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            print('Exception', e)
            raise e

        print("callTuShareShiborDailyService ended...")

    @classmethod
    def callTushareCNGDPService(self):
        print("callTushareCNGDPService started...")

        start_date = '2018Q1'
        end_date = '2022Q1'
        csvFilePath= "D:\workspace_python\dataIntegrator\dataIntegrator\data\outbound\df_tushare_df_tushare_CNGDP_20220507.csv"

        try:
            tuShareService = TushareCNGDPService()
            dataFrame = tuShareService.prepareDataFrame(start_date,end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date,end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            print('Exception', e)
            raise e

        print("callTushareCNGDPService ended...")

    @classmethod
    def callTushareCNMondySupplyService(self):
        print("callTushareCNMondySupplyService started...")

        start_date = '200001'
        end_date = '202212'
        csvFilePath= "D:\workspace_python\dataIntegrator\dataIntegrator\data\outbound\df_tushare_df_tushare_CNMondySupply_20220507.csv"

        try:
            tuShareService = TushareCNMondySupplyService()
            dataFrame = tuShareService.prepareDataFrame(start_date,end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date,end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            print('Exception', e)
            raise e

        print("callTushareCNMondySupplyService ended...")

    @classmethod
    def callTushareCNCPIService(self):
        print("callTushareCNCPIService started...")

        start_date = '200001'
        end_date = '202212'
        csvFilePath= "D:\workspace_python\dataIntegrator\dataIntegrator\data\outbound\df_tushare_df_tushare_CNCPI_20220507.csv"

        try:
            tuShareService = TushareCNCPIService()
            dataFrame = tuShareService.prepareDataFrame(start_date,end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date,end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            print('Exception', e)
            raise e

        print("callTushareCNCPIService ended...")

    @classmethod
    def callTuShareUSStockDailyService(self):
        print("callTuShareUSStockDailyService started...")

        ts_code = 'C'
        start_date = '20220101'
        end_date = '20241229'
        csvFilePath= "D:\workspace_python\dataIntegrator\dataIntegrator\data\outbound\df_tushare_df_tushare_USStock_Daily_20220507.csv"

        try:
            tuShareService = TuShareUSStockDailyService()
            dataFrame = tuShareService.prepareDataFrame(ts_code, start_date,end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(ts_code, start_date,end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            print('Exception', e)
            raise e

        print("callTuShareUSStockDailyService ended...")

    @classmethod
    def callTuFutureBasicInformationService(self):
        print("callTuShareFutureBasicInformationService started...")

        exchange = 'DCE'
        fut_type = '1'
        fields = 'ts_code,symbol,name,list_date,delist_date,quote_unit'
        csvFilePath = "D:\workspace_python\dataIntegrator\dataIntegrator\data\outbound\df_tushare_df_tushare_FutureBasicInformation_20220507.csv"

        try:
            tuShareService = TuShareFutureBasicInformationService()
            dataFrame = tuShareService.prepareDataFrame(exchange, fut_type, fields)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse()
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            print('Exception', e)
            raise e

        print("callTuShareFutureBasicInformationService ended...")

    @classmethod
    def callTuShareFutureDailyService(self):
        print("callTuShareFutureDailyService started...")

        ts_code = 'JM2304.DCE'
        start_date = '20180101'
        end_date = '20220501'
        csvFilePath = "D:\workspace_python\dataIntegrator\dataIntegrator\data\outbound\df_tushare_df_tushare_FutureDaily_20220507.csv"

        try:
            tuShareService = TuShareFutureDailyService()
            dataFrame = tuShareService.prepareDataFrame(ts_code, start_date, end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(ts_code, start_date, end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            print('Exception', e)
            raise e

        print("callTuShareFutureDailyService ended...")

    @classmethod
    def callTushareUSStockBasicService(self):
        print("callTushareUSStockBasicService started...")

        start_date = '20180101'
        end_date = '20250501'
        csvFilePath = "D:\workspace_python\dataIntegrator\dataIntegrator\data\outbound\df_tushare_df_tushare_USStockBasic_20220507.csv"

        try:
            tuShareService = TushareUSStockBasicService()
            dataFrame = tuShareService.prepareDataFrame(start_date, end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date, end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            print('Exception', e)
            raise e

        print("callTushareUSStockBasicService ended...")

    @classmethod
    def callTuShareHKStockDailyService(self):
        print("callTuShareHKStockDailyService started...")

        ts_code = '00001.HK'
        start_date = '20220101'
        end_date = '20220521'
        csvFilePath = "D:\workspace_python\dataIntegrator\dataIntegrator\data\outbound\df_tushare_df_tushare_HKStockDaily_20220507.csv"

        try:
            tuShareService = TuShareHKStockDailyService()
            dataFrame = tuShareService.prepareDataFrame(ts_code, start_date, end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(ts_code, start_date, end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            print('Exception', e)
            raise e

        print("callTuShareHKStockDailyService ended...")

    @classmethod
    def callTuShareFXOffsoreBasicService(self):
        print("callTuShareFXOffsoreBasicService started...")

        exchange = 'FXCM'
        classify = 'INDEX'
        csvFilePath = "D:\workspace_python\dataIntegrator\dataIntegrator\data\outbound\df_tushare_df_tushare_FX_Offsore_basic_20220507.csv"

        try:
            tuShareService = TuShareFXOffsoreBasicService()
            dataFrame = tuShareService.prepareDataFrame(exchange, classify)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse()
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            print('Exception', e)
            raise e

        print("callTuShareFXOffsoreBasicService ended...")

    @classmethod
    def callTuShareFXDailyService(self):
        print("callTuShareFXDailyService started...")

        ts_code = 'US30.FXCM'
        start_date = '20220101'
        end_date = '20220521'
        csvFilePath = "D:\workspace_python\dataIntegrator\dataIntegrator\data\outbound\df_tushare_df_tushare_FX_Offsore_basic_20220507.txt"

        try:
            tuShareService = TuShareFXDailyService()
            dataFrame = tuShareService.prepareDataFrame(ts_code, start_date, end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(ts_code, start_date, end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            print('Exception', e)
            raise e

        print("callTuShareFXDailyService ended...")

    @classmethod
    def callTushareSGEDailyService(self):
        print("callTushareSGEDailyService started...")

        start_date = '20220531'
        end_date = '20220531'
        csvFilePath = "D:\workspace_python\dataIntegrator\dataIntegrator\data\outbound\df_tushare_df_tushare_FX_Offsore_basic_20220507.csv"

        try:
            tuShareService = TuShareSGEDailyService()
            dataFrame = tuShareService.prepareDataFrame(start_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date, end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            print('Exception', e)
            raise e

        print("callTushareSGEDailyService ended...")

    @classmethod
    def callTushareUSTreasuryYieldCurveService(self):
        print("callTushareUSTreasuryYieldCurveService started...")

        start_date = '20220101'
        end_date = '20241231'
        csvFilePath = "D:\workspace_python\dataIntegrator\dataIntegrator\data\outbound\ddf_tushare_us_treasury_yield_cruve_20241201.csv"

        try:
            tuShareService = TushareUSTreasuryYieldCurveService()
            dataFrame = tuShareService.prepareDataFrame(start_date, end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date, end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            print('Exception', e)
            raise e

        print("callTushareUSTreasuryYieldCurveService ended...")

    @classmethod
    def callTuShareService(self):
        try:
            print("callTuShareService started")

            # self.callTuShareCNIndexDailyService()
            # self.callTuShareChinaStockIndexService()
            # self.callTuShareShiborDailyService()
            # self.callTushareShiborLPRDailyService()
            # self.callTushareCNGDPService()
            # self.callTushareCNMondySupplyService()
            # self.callTushareCNCPIService()
            # self.callTuShareUSStockDailyService() #5 times daily
            # self.callTuFutureBasicInformationService()
            # self.callTuShareFutureDailyService()
            self.callTushareUSStockBasicService()
            # self.callTuShareHKStockDailyService()
            # self.callTuShareFXOffsoreBasicService()
            # self.callTuShareFXDailyService()
            # self.callTushareSGEDailyService() #2 times daily
            #self.callTushareUSTreasuryYieldCurveService()

            print("callTuShareService completed successfully")

        except Exception as e:
            print('==============================================', e)
            print('Exception', e)
            print('==============================================', e)
            raise e

            print("end successfuly")


##todo to add the global exception handler
import os

from dataIntegrator import CommonLib, CommonParameters
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


logger = CommonLib.logger

class TuShareServiceManager():
    
    def __init__(self):
        logger.info("__init__ started")

    @classmethod
    def callTuShareCNIndexDailyService(self, param_dict):
        logger.info("callTuShareService started...")

        # ts_code = '000001.SH'
        # start_date = '20220521'
        # end_date = '20241218'
        #ccsvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_cn_index_daily_20220507.csv")

        ts_code = param_dict.get("ts_code")
        start_date = param_dict.get("start_date")
        end_date = param_dict.get("end_date")
        csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_cn_index_daily_20220507.csv")

        try:
            tuShareService = TuShareCNIndexDailyService()
            dataFrame = tuShareService.prepareDataFrame(ts_code,start_date,end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(ts_code,start_date,end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            logger.info('Exception', e)
            raise e

        logger.info("callTuShareService ended...")

    @classmethod
    def callTuShareChinaStockIndexService(self, param_dict):
        logger.info("callTuShareService started...")

        # 002093.SZ 国脉科技
        # 600490.SH 鹏欣资源
        # 000902.SZ 新洋丰
        # 601368.SH 绿城水务
        # 603839.SH 安正时尚
        # 000001.SH 上证综指

        # ts_code = '603839.SH'
        # start_date = '20220521'
        # end_date = '20241230'
        # ccsvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_shibor_daily_20220507.csv")

        ts_code = param_dict.get("ts_code")
        start_date = param_dict.get("start_date")
        end_date = param_dict.get("end_date")

        #CommonParameters.outBoundPath, "df_tushare_df_tushare_shibor_daily_20220507.csv")
        csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_shibor_daily_20220507.csv")
        try:
            tuShareService = TuShareChinaStockIndexService()
            dataFrame = tuShareService.prepareDataFrame(ts_code,start_date,end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(ts_code,start_date,end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            logger.info('Exception', e)
            raise e

        logger.info("callTuShareService ended...")

    @classmethod
    def callTuShareShiborDailyService(self, param_dict):
        logger.info("callTuShareShiborDailyService started...")

        # start_date = '20220101'
        # end_date = '20250521'
        start_date = param_dict.get("start_date")
        end_date = param_dict.get("end_date")
        csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_shibor_daily_20220507.csv")

        try:
            tuShareService = TushareShiborDailyService()
            dataFrame = tuShareService.prepareDataFrame(start_date,end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date,end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            logger.info('Exception', e)
            raise e

        logger.info("callTuShareShiborDailyService ended...")

    @classmethod
    def callTushareShiborLPRDailyService(self, param_dict):
        logger.info("callTuShareShiborDailyService started...")

        start_date = param_dict.get("start_date")
        end_date = param_dict.get("end_date")
        csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_shibor_lpr_daily_20220507.csv")

        try:
            tuShareService = TushareShiborLPRDailyService()
            dataFrame = tuShareService.prepareDataFrame(start_date, end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date, end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            logger.info('Exception', e)
            raise e

        logger.info("callTuShareShiborDailyService ended...")

    @classmethod
    def callTushareCNGDPService(self, param_dict):
        logger.info("callTushareCNGDPService started...")

        # start_date = '2018Q1'
        # end_date = '2022Q1'
        start_date = param_dict.get("start_date")
        end_date = param_dict.get("end_date")
        csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_CNGDP_20220507.csv")

        try:
            tuShareService = TushareCNGDPService()
            dataFrame = tuShareService.prepareDataFrame(start_date,end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date,end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            logger.info('Exception', e)
            raise e

        logger.info("callTushareCNGDPService ended...")

    @classmethod
    def callTushareCNMondySupplyService(self, param_dict):
        logger.info("callTushareCNMondySupplyService started...")

        start_date = param_dict.get("start_date")
        end_date = param_dict.get("end_date")
        csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_CNMondySupply_20220507.csv")

        try:
            tuShareService = TushareCNMondySupplyService()
            dataFrame = tuShareService.prepareDataFrame(start_date,end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date,end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            logger.info('Exception', e)
            raise e

        logger.info("callTushareCNMondySupplyService ended...")

    @classmethod
    def callTushareCNCPIService(self, param_dict):
        logger.info("callTushareCNCPIService started...")

        start_date = param_dict.get("start_date")
        end_date = param_dict.get("end_date")
        csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_CNCPI_20220507.csv")

        try:
            tuShareService = TushareCNCPIService()
            dataFrame = tuShareService.prepareDataFrame(start_date,end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date,end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            logger.info('Exception', e)
            raise e

        logger.info("callTushareCNCPIService ended...")

    @classmethod
    def callTuShareUSStockDailyService(self, param_dict):
        logger.info("callTuShareUSStockDailyService started...")

        # ts_code = 'C'
        # start_date = '20220101'
        # end_date = '20241229'
        ts_code = param_dict.get("ts_code")
        start_date = param_dict.get("start_date")
        end_date = param_dict.get("end_date")
        csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_USStock_Daily_20220507.csv")

        try:
            tuShareService = TuShareUSStockDailyService()
            dataFrame = tuShareService.prepareDataFrame(ts_code, start_date,end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(ts_code, start_date,end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            logger.info('Exception', e)
            raise e

        logger.info("callTuShareUSStockDailyService ended...")

    @classmethod
    def callTuFutureBasicInformationService(self, param_dict):
        logger.info("callTuShareFutureBasicInformationService started...")

        # exchange = 'DCE'
        # fut_type = '1'
        # fields = 'ts_code,symbol,name,list_date,delist_date,quote_unit'
        exchange = param_dict.get("exchange")
        fut_type = param_dict.get("fut_type")
        fields = param_dict.get("fields")
        csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_FutureBasicInformation_20220507.csv")

        try:
            tuShareService = TuShareFutureBasicInformationService()
            dataFrame = tuShareService.prepareDataFrame(exchange, fut_type, fields)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse()
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            logger.info('Exception', e)
            raise e

        logger.info("callTuShareFutureBasicInformationService ended...")

    @classmethod
    def callTuShareFutureDailyService(self, param_dict):
        logger.info("callTuShareFutureDailyService started...")

        # ts_code = 'JM2304.DCE'
        # start_date = '20180101'
        # end_date = '20220501'
        ts_code = param_dict.get("ts_code")
        start_date = param_dict.get("start_date")
        end_date = param_dict.get("end_date")
        csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_FutureDaily_20220507.csv")

        try:
            tuShareService = TuShareFutureDailyService()
            dataFrame = tuShareService.prepareDataFrame(ts_code, start_date, end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(ts_code, start_date, end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            logger.info('Exception', e)
            raise e

        logger.info("callTuShareFutureDailyService ended...")

    @classmethod
    def callTushareUSStockBasicService(self, param_dict):
        logger.info("callTushareUSStockBasicService started...")

        # start_date = '20180101'
        # end_date = '20250501'
        start_date = param_dict.get("start_date")
        end_date = param_dict.get("end_date")
        csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_USStockBasic_20220507.csv")

        try:
            tuShareService = TushareUSStockBasicService()
            dataFrame = tuShareService.prepareDataFrame(start_date, end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date, end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            logger.info('Exception', e)
            raise e

        logger.info("callTushareUSStockBasicService ended...")

    @classmethod
    def callTuShareHKStockDailyService(self, param_dict):
        logger.info("callTuShareHKStockDailyService started...")

        # ts_code = '00001.HK'
        # start_date = '20220101'
        # end_date = '20220521'
        ts_code = param_dict.get("ts_code")
        start_date = param_dict.get("start_date")
        end_date = param_dict.get("end_date")
        csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_HKStockDaily_20220507.csv")

        try:
            tuShareService = TuShareHKStockDailyService()
            dataFrame = tuShareService.prepareDataFrame(ts_code, start_date, end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(ts_code, start_date, end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            logger.info('Exception', e)
            raise e

        logger.info("callTuShareHKStockDailyService ended...")

    @classmethod
    def callTuShareFXOffsoreBasicService(self, param_dict):
        logger.info("callTuShareFXOffsoreBasicService started...")

        # exchange = 'FXCM'
        # classify = 'INDEX'
        exchange = param_dict.get("exchange")
        classify = param_dict.get("classify")

        csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_FX_Offsore_basic_20220507.csv")

        try:
            tuShareService = TuShareFXOffsoreBasicService()
            dataFrame = tuShareService.prepareDataFrame(exchange, classify)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse()
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            logger.info('Exception', e)
            raise e

        logger.info("callTuShareFXOffsoreBasicService ended...")

    @classmethod
    def callTuShareFXDailyService(self, param_dict):
        logger.info("callTuShareFXDailyService started...")

        # ts_code = 'US30.FXCM'
        # start_date = '20220101'
        # end_date = '20220521'
        ts_code = param_dict.get("ts_code")
        start_date = param_dict.get("start_date")
        end_date = param_dict.get("end_date")
        csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_FX_Offsore_basic_20220507.txt")

        try:
            tuShareService = TuShareFXDailyService()
            dataFrame = tuShareService.prepareDataFrame(ts_code, start_date, end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(ts_code, start_date, end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            logger.info('Exception', e)
            raise e

        logger.info("callTuShareFXDailyService ended...")

    @classmethod
    def callTushareSGEDailyService(self, param_dict):
        logger.info("callTushareSGEDailyService started...")

        # start_date = '20220531'
        # end_date = '20220531'
        start_date = param_dict.get("start_date")
        end_date = param_dict.get("end_date")
        csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_FX_Offsore_basic_20220507.csv")

        try:
            tuShareService = TuShareSGEDailyService()
            dataFrame = tuShareService.prepareDataFrame(start_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date, end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            logger.info('Exception', e)
            raise e

        logger.info("callTushareSGEDailyService ended...")

    @classmethod
    def callTushareUSTreasuryYieldCurveService(self, param_dict):
        logger.info("callTushareUSTreasuryYieldCurveService started...")

        # start_date = '20220101'
        # end_date = '20241231'
        start_date = param_dict.get("start_date")
        end_date = param_dict.get("end_date")
        csvFilePath = os.path.join(CommonParameters.outBoundPath,"ddf_tushare_us_treasury_yield_cruve_20241201.csv")

        try:
            tuShareService = TushareUSTreasuryYieldCurveService()
            dataFrame = tuShareService.prepareDataFrame(start_date, end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date, end_date)
            tuShareService.saveDateToClickHouse()

        except Exception as e:
            logger.info('Exception', e)
            raise e

        logger.info("callTushareUSTreasuryYieldCurveService ended...")

    @classmethod
    def callTuShareService(self):
        try:
            logger.info("callTuShareService started")

            # start_date = "20250101"
            # end_date = "20251231"
            # start_quarter = "2024Q1"
            # end_quarter = "2025Q1"
            start_date = "20260101"
            end_date = "20261231"
            start_quarter = "2025Q1"
            end_quarter = "2026Q1"

            param_method_dict = {
                "callTuShareCNIndexDailyService": {"ts_code": "000001.SH", "start_date": start_date,"end_date": end_date},
                "callTuShareChinaStockIndexService": {"ts_code": "603839.SH", "start_date": start_date,"end_date": end_date},
                "callTuShareShiborDailyService": {"start_date": start_date, "end_date": end_date},
                "callTushareShiborLPRDailyService": {"start_date": start_date, "end_date": end_date},
                "callTushareCNGDPService": {"start_date": start_quarter, "end_date": end_quarter},
                "callTushareCNMondySupplyService": {"start_date": start_date, "end_date": end_date},  # 保持原方法名
                "callTushareCNCPIService": {"start_date": start_date, "end_date": end_date},
                "callTuFutureBasicInformationService": {"exchange": "DCE", "fut_type": '1', "fields": "ts_code,symbol,name,list_date,delist_date,quote_unit"},
                "callTuShareFutureDailyService": {"ts_code": "JM2304.DCE", "start_date": start_date, "end_date": end_date},
                "callTushareUSStockBasicService": {"start_date": start_date, "end_date": end_date},
                "callTuShareHKStockDailyService": {"ts_code": "00001.HK", "start_date": start_date, "end_date": end_date},
                "callTuShareFXOffsoreBasicService": {"exchange": "FXCM", "classify": "INDEX"},  # 保持原方法名
                "callTuShareFXDailyService": {"exchange": "US30.FXCM", "start_date": start_date, "end_date": end_date},
                "callTushareSGEDailyService": {"start_date": start_date, "end_date": end_date},
                "callTushareUSTreasuryYieldCurveService": {"start_date": start_date, "end_date": end_date},
                "callTuShareUSStockDailyService": {"ts_code": "C", "start_date": start_date, "end_date": end_date} #5 times daily
            }

            # 按顺序调用方法
            for method_name, params in param_method_dict.items():
                try:
                    method = getattr(self, method_name)
                    method(params)  # 统一传递参数
                except AttributeError:
                    logger.error(f"方法 {method_name} 不存在，请检查拼写！", e)
                except Exception as e:
                    logger.error(f"调用 {method_name} 失败: {e}")

            ##### have issue here, just doubt it's the compatibility issue between py312 and tushare
            # param_dict = {"ts_code": "C", "start_date": start_date, "end_date": end_date}
            # self.callTuShareUSStockDailyService(param_dict) #5 times daily

            logger.info("callTuShareService completed successfully")

        except Exception as e:
            logger.error('==============================================', e)
            logger.error('Exception', e)
            logger.error('==============================================', e)
            raise e

            logger.info("end successfuly")

##todo to add the global exception handler
def main():
    tuShareServiceManger = TuShareServiceManager()
    tuShareServiceManger.callTuShareService()

if __name__ == '__main__':
    main()


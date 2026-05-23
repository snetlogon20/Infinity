import os
import time
import traceback
from datetime import datetime
import json

from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.TuShareService.TuShareCNIndexDailyService import TuShareCNIndexDailyService
from dataIntegrator.TuShareService.TuShareChinaStockIndexService import TuShareChinaStockIndexService
from dataIntegrator.TuShareService.TuShareUSDIndexDailyService import TuShareUSDIndexDailyService
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
from dataIntegrator.TuShareService.TuShareYieldCurveConvertableBondService import TuShareYieldCurveConvertableBondService
from dataIntegrator.TuShareService.TuShareConvertBondBasicService import TuShareConvertBondBasicService
from dataIntegrator.TuShareService.TushareUSTreasuryYieldCurveService import TushareUSTreasuryYieldCurveService
from dataIntegrator.TuShareService.TuShareIndexGlobalService import TuShareIndexGlobalService
from dataIntegrator.common.CommonDataParameters import CommonDataParameters
from dataIntegrator.modelService.commonService.CalendarService import CalendarService
from dataIntegrator.TuShareService.TuShareJobLogger import TuShareJobLogger

logger = CommonLib.logger

class TuShareServiceManager():


    def __init__(self):
        self.calendarService = CalendarService()
        self.jobLogger = TuShareJobLogger()
        logger.info("__init__ started")

    def callTuShareCNIndexDailyService(self, param_dict):
        self.jobLogger.start_job("callTuShareCNIndexDailyService", param_dict)
        
        try:
            logger.info("callTuShareCNIndexDailyService started...")

            tuShareCNIndexDailyService = TuShareCNIndexDailyService()
            index_list = CommonDataParameters.CN_INDEX_LIST
            end_date = CommonParameters.today
            start_date = CommonDataParameters.get_start_date(days=360)
            
            records_count = tuShareCNIndexDailyService.refresh_multiple_indexes(index_list, start_date, end_date)

            self.jobLogger.end_job_success(records_processed=records_count if records_count else len(index_list))
            logger.info("callTuShareCNIndexDailyService ended...")
            
        except Exception as e:
            self.jobLogger.end_job_failed(str(e), traceback.format_exc())
            raise e

    def callTuShareChinaStockIndexService(self, param_dict):
        self.jobLogger.start_job("callTuShareChinaStockIndexService", param_dict)
            
        try:
            logger.info("callTuShareChinaStockIndexService started...")
    
            """"批量处理多个股票"""
            stock_list = CommonParameters.STOCK_LIST
    
            end_date = CommonParameters.today
            start_date = CommonDataParameters.get_start_date(days=360)
    
            logger.info(f"开始批量处理 {len(stock_list)} 只股票...")
                
            total_records = 0
            success_count = 0
            failed_count = 0
    
            for stock in stock_list:
                ts_code = stock['ts_code']
                name = stock['name']
    
                try:
                    logger.info(f"\n{'=' * 60}")
                    logger.info(f"正在处理：{name} ({ts_code})")
                    logger.info(f"{'=' * 60}")
    
                    csvFilePath = os.path.join(CommonParameters.outBoundPath,
                                               f"df_tushare_{ts_code.replace('.', '_')}_{start_date[:4]}.csv")
    
                    tuShareService = TuShareChinaStockIndexService()
                    dataFrame = tuShareService.prepareDataFrame(ts_code, start_date, end_date)
    
                    if dataFrame.empty:
                        logger.warning(f"{name} ({ts_code}) 没有获取到数据，跳过...")
                        continue
    
                    logger.info(f"转换数据为 JSON...")
                    jsonString = tuShareService.convertDataFrame2JSON()
                    logger.info(f"保存到：{csvFilePath}")
                    tuShareService.saveDateFrameToDisk(csvFilePath)
                    tuShareService.deleteDateFromClickHouse(ts_code, start_date, end_date)
                    tuShareService.saveDateToClickHouse()
    
                    total_records += len(dataFrame)
                    success_count += 1
                    logger.info(f"✅ {name} ({ts_code}) 处理完成！")
    
                except Exception as e:
                    failed_count += 1
                    logger.error(f" {name} ({ts_code}) 处理失败：{str(e)}")
                    logger.error(traceback.format_exc())
                    continue
    
            logger.info(f"\n{'=' * 60}")
            logger.info(f"批量处理完成！共处理 {len(stock_list)} 只股票")
            logger.info(f"成功: {success_count}, 失败: {failed_count}, 总记录数: {total_records}")
            logger.info(f"{'=' * 60}")
    
            self.jobLogger.end_job_success(records_processed=total_records)
            logger.info("callTuShareChinaStockIndexService ended...")
                
        except Exception as e:
            self.jobLogger.end_job_failed(str(e), traceback.format_exc())
            raise e

    def callTuShareShiborDailyService(self, param_dict):
        self.jobLogger.start_job("callTuShareShiborDailyService", param_dict)
        
        try:
            logger.info("callTuShareShiborDailyService started...")

            start_date = param_dict.get("start_date")
            end_date = param_dict.get("end_date")
            csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_shibor_daily_20220507.csv")

            tuShareService = TushareShiborDailyService()
            dataFrame = tuShareService.prepareDataFrame(start_date,end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date,end_date)
            tuShareService.saveDateToClickHouse()

            self.jobLogger.end_job_success(records_processed=len(dataFrame) if not dataFrame.empty else 0)
            logger.info("callTuShareShiborDailyService ended...")

        except Exception as e:
            self.jobLogger.end_job_failed(str(e), traceback.format_exc())
            raise e

    @classmethod
    def callTushareShiborLPRDailyService(self, param_dict):
        job_logger = TuShareJobLogger()
        job_logger.start_job("callTushareShiborLPRDailyService", param_dict)
        
        try:
            logger.info("callTushareShiborLPRDailyService started...")

            start_date = param_dict.get("start_date")
            end_date = param_dict.get("end_date")
            csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_shibor_lpr_daily_20220507.csv")

            tuShareService = TushareShiborLPRDailyService()
            dataFrame = tuShareService.prepareDataFrame(start_date, end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date, end_date)
            tuShareService.saveDateToClickHouse()

            job_logger.end_job_success(records_processed=len(dataFrame) if not dataFrame.empty else 0)
            logger.info("callTushareShiborLPRDailyService ended...")

        except Exception as e:
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise e

    @classmethod
    def callTushareCNGDPService(self, param_dict):
        job_logger = TuShareJobLogger()
        job_logger.start_job("callTushareCNGDPService", param_dict)
        
        try:
            logger.info("callTushareCNGDPService started...")

            start_date = param_dict.get("start_date")
            end_date = param_dict.get("end_date")
            csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_CNGDP_20220507.csv")

            tuShareService = TushareCNGDPService()
            dataFrame = tuShareService.prepareDataFrame(start_date,end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date,end_date)
            tuShareService.saveDateToClickHouse()

            job_logger.end_job_success(records_processed=len(dataFrame) if not dataFrame.empty else 0)
            logger.info("callTushareCNGDPService ended...")

        except Exception as e:
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise e

    @classmethod
    def callTushareCNMondySupplyService(self, param_dict):
        job_logger = TuShareJobLogger()
        job_logger.start_job("callTushareCNMondySupplyService", param_dict)
        
        try:
            logger.info("callTushareCNMondySupplyService started...")

            start_date = param_dict.get("start_date")
            end_date = param_dict.get("end_date")
            csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_CNMondySupply_20220507.csv")

            tuShareService = TushareCNMondySupplyService()
            dataFrame = tuShareService.prepareDataFrame(start_date,end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date,end_date)
            tuShareService.saveDateToClickHouse()

            job_logger.end_job_success(records_processed=len(dataFrame) if not dataFrame.empty else 0)
            logger.info("callTushareCNMondySupplyService ended...")

        except Exception as e:
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise e

    @classmethod
    def callTushareCNCPIService(self, param_dict):
        job_logger = TuShareJobLogger()
        job_logger.start_job("callTushareCNCPIService", param_dict)
        
        try:
            logger.info("callTushareCNCPIService started...")

            start_date = param_dict.get("start_date")
            end_date = param_dict.get("end_date")
            csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_CNCPI_20220507.csv")

            tuShareService = TushareCNCPIService()
            dataFrame = tuShareService.prepareDataFrame(start_date,end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date,end_date)
            tuShareService.saveDateToClickHouse()

            job_logger.end_job_success(records_processed=len(dataFrame) if not dataFrame.empty else 0)
            logger.info("callTushareCNCPIService ended...")

        except Exception as e:
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise e

    @classmethod
    def callTuShareUSStockDailyService(self, param_dict):
        job_logger = TuShareJobLogger()
        job_logger.start_job("callTuShareUSStockDailyService", param_dict)
        
        try:
            logger.info("callTuShareUSStockDailyService started...")

            calenearService = CalendarService()
            end_date = CommonParameters.today
            start_date = CommonDataParameters.get_start_date(days=31)

            ts_code_list = CommonParameters.US_STOCK_LIST
            ts_code_dict = {f"stock_{i}": code for i, code in enumerate(ts_code_list, 1)}

            total_records = 0
            success_count = 0
            failed_count = 0

            # 循环调用
            for key, ts_code in ts_code_dict.items():
                try:
                    csvFilePath = os.path.join(CommonParameters.outBoundPath,
                                               rf"df_tushare_df_tushare_USStockBasic_{ts_code}{start_date}-{end_date}.csv")

                    tuShareService = TuShareUSStockDailyService()
                    dataFrame = tuShareService.prepareDataFrame(ts_code, start_date, end_date)
                    jsonString = tuShareService.convertDataFrame2JSON()
                    tuShareService.saveDateFrameToDisk(csvFilePath)
                    tuShareService.deleteDateFromClickHouse(ts_code, start_date, end_date)
                    tuShareService.saveDateToClickHouse()

                    total_records += len(dataFrame)
                    success_count += 1
                    logger.info(f"{key}: {ts_code} {start_date}-{end_date} 处理完成")
                    
                    # Tushare 规定 1 分钟只能访问 2 次，这里循环休眠 45 秒
                    for i in range(1, 45):
                        logger.info(f"Tushare 限流控制：第 {i}/45 秒...")
                        time.sleep(1)

                except Exception as e:
                    failed_count += 1
                    logger.error(f"{key}: {ts_code} 处理失败：{str(e)}")

            logger.info(f"美股日线处理完成：成功 {success_count} 个，失败 {failed_count} 个，总记录数 {total_records}")
            job_logger.end_job_success(records_processed=total_records)
            logger.info("callTuShareUSStockDailyService ended...")

        except Exception as e:
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise e

    @classmethod
    def callTuFutureBasicInformationService(self, param_dict):
        job_logger = TuShareJobLogger()
        job_logger.start_job("callTuFutureBasicInformationService", param_dict)
        
        try:
            logger.info("callTuFutureBasicInformationService started...")

            exchange = param_dict.get("exchange")
            fut_type = param_dict.get("fut_type")
            fields = param_dict.get("fields")
            csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_FutureBasicInformation_20220507.csv")

            tuShareService = TuShareFutureBasicInformationService()
            dataFrame = tuShareService.prepareDataFrame(exchange, fut_type, fields)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse()
            tuShareService.saveDateToClickHouse()

            job_logger.end_job_success(records_processed=len(dataFrame) if not dataFrame.empty else 0)
            logger.info("callTuFutureBasicInformationService ended...")

        except Exception as e:
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise e

    @classmethod
    def callTuShareFutureDailyService(self, param_dict):
        job_logger = TuShareJobLogger()
        job_logger.start_job("callTuShareFutureDailyService", param_dict)
        
        try:
            logger.info("callTuShareFutureDailyService started...")

            ts_code = param_dict.get("ts_code")
            start_date = param_dict.get("start_date")
            end_date = param_dict.get("end_date")
            csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_FutureDaily_20220507.csv")

            tuShareService = TuShareFutureDailyService()
            dataFrame = tuShareService.prepareDataFrame(ts_code, start_date, end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(ts_code, start_date, end_date)
            tuShareService.saveDateToClickHouse()

            job_logger.end_job_success(records_processed=len(dataFrame) if not dataFrame.empty else 0)
            logger.info("callTuShareFutureDailyService ended...")

        except Exception as e:
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise e

    @classmethod
    def callTushareUSStockBasicService(self, param_dict):
        job_logger = TuShareJobLogger()
        job_logger.start_job("callTushareUSStockBasicService", param_dict)
        
        try:
            logger.info("callTushareUSStockBasicService started...")

            start_date = param_dict.get("start_date")
            end_date = param_dict.get("end_date")
            csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_USStockBasic_20220507.csv")

            tuShareService = TushareUSStockBasicService()
            dataFrame = tuShareService.prepareDataFrame(start_date, end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date, end_date)
            tuShareService.saveDateToClickHouse()

            job_logger.end_job_success(records_processed=len(dataFrame) if not dataFrame.empty else 0)
            logger.info("callTushareUSStockBasicService ended...")

        except Exception as e:
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise e

    @classmethod
    def callTuShareHKStockDailyService(self, param_dict):
        job_logger = TuShareJobLogger()
        job_logger.start_job("callTuShareHKStockDailyService", param_dict)
        
        try:
            logger.info("callTuShareHKStockDailyService started...")

            ts_code = param_dict.get("ts_code")
            start_date = param_dict.get("start_date")
            end_date = param_dict.get("end_date")
            csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_HKStockDaily_20220507.csv")

            tuShareService = TuShareHKStockDailyService()
            dataFrame = tuShareService.prepareDataFrame(ts_code, start_date, end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(ts_code, start_date, end_date)
            tuShareService.saveDateToClickHouse()

            job_logger.end_job_success(records_processed=len(dataFrame) if not dataFrame.empty else 0)
            logger.info("callTuShareHKStockDailyService ended...")

        except Exception as e:
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise e

    @classmethod
    def callTuShareFXOffsoreBasicService(self, param_dict):
        job_logger = TuShareJobLogger()
        job_logger.start_job("callTuShareFXOffsoreBasicService", param_dict)
        
        try:
            logger.info("callTuShareFXOffsoreBasicService started...")

            exchange = param_dict.get("exchange")
            classify = param_dict.get("classify")

            csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_FX_Offsore_basic_20220507.csv")

            tuShareService = TuShareFXOffsoreBasicService()
            dataFrame = tuShareService.prepareDataFrame(exchange, classify)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse()
            tuShareService.saveDateToClickHouse()

            job_logger.end_job_success(records_processed=len(dataFrame) if not dataFrame.empty else 0)
            logger.info("callTuShareFXOffsoreBasicService ended...")

        except Exception as e:
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise e

    @classmethod
    def callTuShareFXDailyService(self, param_dict):
        job_logger = TuShareJobLogger()
        job_logger.start_job("callTuShareFXDailyService", param_dict)
            
        try:
            logger.info("callTuShareFXDailyService started...")
    
            ts_code = "nothing"
            start_date = param_dict.get("start_date")
            end_date = param_dict.get("end_date")
            calendar = CalendarService()
            date_range = calendar.generate_date_range(start_date, end_date)
    
            total_records = 0
            for i, (current_start, current_end) in enumerate(date_range, 1):
                try:
                    csvFilePath = os.path.join(CommonParameters.outBoundPath,
                                               "df_tushare_fx_%s-%s.csv" % (start_date, start_date))
    
                    tuShareService = TuShareFXDailyService()
                    dataFrame = tuShareService.prepareDataFrame(ts_code, current_start, current_start)
                    jsonString = tuShareService.convertDataFrame2JSON()
                    tuShareService.saveDateFrameToDisk(csvFilePath)
                    tuShareService.deleteDateFromClickHouse(ts_code, current_start, current_start)
                    tuShareService.saveDateToClickHouse()
    
                    total_records += len(dataFrame)
                    logger.info(f"✅ {current_start} - {current_end} 刷新成功，共 {len(dataFrame)} 条数据")
    
                except Exception as e:
                    logger.error(f" {current_start} - {current_end} - 刷新失败：{e}")
                    continue
    
            logger.info("\n" + "=" * 60)
            logger.info("所有外汇对刷新完成")
            logger.info("=" * 60)
    
            job_logger.end_job_success(records_processed=total_records)
            logger.info("callTuShareFXDailyService ended...")
    
        except Exception as e:
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise e

    @classmethod
    # 美元指数
    def callUSDIndexDailyService(self, param_dict):
        job_logger = TuShareJobLogger()
        job_logger.start_job("callUSDIndexDailyService", param_dict)
        
        try:
            logger.info("callUSDIndexDailyService started...")

            start_date = param_dict.get("start_date")
            end_date = param_dict.get("end_date")
            csvFilePath = os.path.join(CommonParameters.outBoundPath, "df_tushare_usd_index_%s-%s.csv" % (start_date, end_date))

            tuShareService = TuShareUSDIndexDailyService()
            dataFrame = tuShareService.prepareDataFrame(start_date, end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date, end_date)
            tuShareService.saveDateToClickHouse()

            job_logger.end_job_success(records_processed=len(dataFrame) if not dataFrame.empty else 0)
            logger.info("callUSDIndexDailyService ended...")

        except Exception as e:
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise e

    @classmethod
    def callTushareSGEDailyService(self, param_dict):
        job_logger = TuShareJobLogger()
        job_logger.start_job("callTushareSGEDailyService", param_dict)
        
        try:
            logger.info("callTushareSGEDailyService started...")

            start_date = param_dict.get("start_date")
            end_date = param_dict.get("end_date")
            csvFilePath = os.path.join(CommonParameters.outBoundPath,"df_tushare_df_tushare_FX_Offsore_basic_20220507.csv")

            tuShareService = TuShareSGEDailyService()
            dataFrame = tuShareService.prepareDataFrame(start_date, end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date, end_date)
            tuShareService.saveDateToClickHouse()

            job_logger.end_job_success(records_processed=len(dataFrame) if not dataFrame.empty else 0)
            logger.info("callTushareSGEDailyService ended...")

        except Exception as e:
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise e

    @classmethod
    def callTushareUSTreasuryYieldCurveService(self, param_dict):
        job_logger = TuShareJobLogger()
        job_logger.start_job("callTushareUSTreasuryYieldCurveService", param_dict)
        
        try:
            logger.info("callTushareUSTreasuryYieldCurveService started...")

            #start_date = param_dict.get("start_date")
            #债券信息在更新时有数据条数显示，故改成10天内刷新
            calendarService = CalendarService()
            start_date = calendarService.calculate_T_minus_n_days(CommonParameters.today, days=10)
            end_date = param_dict.get("end_date")
            csvFilePath = os.path.join(CommonParameters.outBoundPath,"ddf_tushare_us_treasury_yield_cruve_20241201.csv")

            tuShareService = TushareUSTreasuryYieldCurveService()
            dataFrame = tuShareService.prepareDataFrame(start_date, end_date)
            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)
            tuShareService.deleteDateFromClickHouse(start_date, end_date)
            tuShareService.saveDateToClickHouse()

            job_logger.end_job_success(records_processed=len(dataFrame) if not dataFrame.empty else 0)
            logger.info("callTushareUSTreasuryYieldCurveService ended...")

        except Exception as e:
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise e

    @classmethod
    def callTuShareConvertBondBasicService(self, param_dict):
        """
        刷新可转债基础信息数据
        参考 TuShareConvertBondBasicServiceTest.refresh_cb_basic
        由于 cb_basic 是全量数据，不需要日期范围
        """
        job_logger = TuShareJobLogger()
        job_logger.start_job("callTuShareConvertBondBasicService", param_dict)
        
        try:
            logger.info("callTuShareConvertBondBasicService started...")

            csvFilePath = os.path.join(CommonParameters.outBoundPath, "df_tushare_cb_basic.csv")

            tuShareService = TuShareConvertBondBasicService()
            dataFrame = tuShareService.prepareDataFrame()

            logger.info(f"获取到 {len(dataFrame)} 条可转债基础信息记录")

            jsonString = tuShareService.convertDataFrame2JSON()
            tuShareService.saveDateFrameToDisk(csvFilePath)

            # 先删除旧数据，再插入新数据
            tuShareService.deleteDateFromClickHouse()
            tuShareService.saveDateToClickHouse()

            job_logger.end_job_success(records_processed=len(dataFrame) if not dataFrame.empty else 0)
            logger.info("✅ 可转债基础信息处理完成")
            logger.info("callTuShareConvertBondBasicService ended...")

        except Exception as e:
            job_logger.end_job_failed(str(e), traceback.format_exc())
            logger.error(f"❌ 可转债基础信息处理失败：{str(e)}")
            raise e

    @classmethod
    def callTuShareIndexGlobalService(self, param_dict):
        """
        刷新全球指数数据
        参考 TuShareIndexGlobalServiceTest.refresh_global_indexes
        """
        job_logger = TuShareJobLogger()
        job_logger.start_job("callTuShareIndexGlobalService", param_dict)
        
        try:
            logger.info("callTuShareIndexGlobalService started...")

            # 定义全球指数列表
            index_list = [
                {'ts_code': 'XIN9', 'name': '富时中国A50指数'},
                {'ts_code': 'HSI', 'name': '恒生指数'},
                {'ts_code': 'HKTECH', 'name': '恒生科技指数'},
                {'ts_code': 'HKAH', 'name': '恒生AH股H指数'},
                {'ts_code': 'DJI', 'name': '道琼斯工业指数'},
                {'ts_code': 'SPX', 'name': '标普500指数'},
                {'ts_code': 'IXIC', 'name': '纳斯达克指数'},
                {'ts_code': 'FTSE', 'name': '富时100指数'},
                {'ts_code': 'FCHI', 'name': '法国CAC40指数'},
                {'ts_code': 'GDAXI', 'name': '德国DAX指数'},
                {'ts_code': 'N225', 'name': '日经225指数'},
                {'ts_code': 'KS11', 'name': '韩国综合指数'},
                {'ts_code': 'AS51', 'name': '澳大利亚标普200指数'},
                {'ts_code': 'SENSEX', 'name': '印度孟买SENSEX指数'},
                {'ts_code': 'IBOVESPA', 'name': '巴西IBOVESPA指数'},
                {'ts_code': 'RTS', 'name': '俄罗斯RTS指数'},
                {'ts_code': 'TWII', 'name': '台湾加权指数'},
                {'ts_code': 'CKLSE', 'name': '马来西亚指数'},
                {'ts_code': 'SPTSX', 'name': '加拿大S&P/TSX指数'},
                {'ts_code': 'CSX5P', 'name': 'STOXX欧洲50指数'},
                {'ts_code': 'RUT', 'name': '罗素2000指数'}
            ]

            start_date = param_dict.get("start_date")
            end_date = param_dict.get("end_date")

            logger.info(f"开始批量处理 {len(index_list)} 个全球指数...")

            total_records = 0
            success_count = 0
            failed_count = 0

            for index in index_list:
                ts_code = index['ts_code']
                name = index['name']

                try:
                    logger.info(f"\n{'=' * 60}")
                    logger.info(f"正在处理：{name} ({ts_code})")
                    logger.info(f"{'=' * 60}")

                    csvFilePath = os.path.join(CommonParameters.outBoundPath,
                                               f"df_tushare_{ts_code}_{start_date[:4]}.csv")

                    tuShareService = TuShareIndexGlobalService()
                    dataFrame = tuShareService.prepareDataFrame(ts_code, start_date, end_date)

                    if dataFrame.empty:
                        logger.warning(f"{name} ({ts_code}) 没有获取到数据，跳过...")
                        continue

                    logger.info(f"转换数据为 JSON...")
                    jsonString = tuShareService.convertDataFrame2JSON()
                    logger.info(f"保存到：{csvFilePath}")
                    tuShareService.saveDateFrameToDisk(csvFilePath)
                    tuShareService.deleteDateFromClickHouse(ts_code, start_date, end_date)
                    tuShareService.saveDateToClickHouse()

                    total_records += len(dataFrame)
                    success_count += 1
                    logger.info(f"✅ {name} ({ts_code}) 处理完成！")

                except Exception as e:
                    failed_count += 1
                    logger.error(f"❌ {name} ({ts_code}) 处理失败：{str(e)}")
                    logger.error(traceback.format_exc())
                    continue

            logger.info(f"\n{'=' * 60}")
            logger.info(f"批量处理完成！共处理 {len(index_list)} 个全球指数")
            logger.info(f"成功: {success_count}, 失败: {failed_count}, 总记录数: {total_records}")
            logger.info(f"{'=' * 60}")

            job_logger.end_job_success(records_processed=total_records)
            logger.info("callTuShareIndexGlobalService ended...")

        except Exception as e:
            job_logger.end_job_failed(str(e), traceback.format_exc())
            raise e

    #@classmethod
    def callTuShareService(self, start_date = "20260101", end_date = CommonParameters.today):
        try:
            logger.info("callTuShareService started")

            # start_date = "20260101"
            # end_date = CommonParameters.today

            start_quarter = self.calendarService.calculate_quarter(start_date) # "2026Q1"
            end_quarter  = self.calendarService.calculate_quarter(end_date) # "2026Q1"

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
                "callTuShareUSStockDailyService": {"ts_code": "C", "start_date": start_date, "end_date": end_date}, #5 times daily,
                "callUSDIndexDailyService": {"start_date": start_date, "end_date": end_date},
                # 可转债基础信息（全量数据，不需要日期范围）
                "callTuShareConvertBondBasicService": {},
                # 全球指数数据
                "callTuShareIndexGlobalService": {"start_date": start_date, "end_date": end_date}
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


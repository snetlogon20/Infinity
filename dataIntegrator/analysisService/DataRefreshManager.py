from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.AKShareService.AkShareServiceManager import AkShareServiceManager
from dataIntegrator.TuShareService.TuShareServiceManager import TuShareServiceManager
from dataIntegrator.modelService.commonService.CalendarService import CalendarService

logger = CommonLib.logger
commonLib = CommonLib()

class DataRefreshManager:
    from dataIntegrator import CommonLib

    logger = CommonLib.logger
    commonLib = CommonLib()

    def __init__(cls):
        pass

    def fresh_data(self):
        """执行数据刷新流程"""
        try:
            self.logger.info("=" * 50)
            self.logger.info("Data refresh started")
            self.logger.info("=" * 50)

            calenearService = CalendarService()
            # 获取31天前的日期，作为滚动扫描的start date
            start_date = calenearService.calculate_T_minus_n_days( CommonParameters.today, days=31)
            end_date = CommonParameters.today

            # Step 1: 执行 TuShare 数据服务
            self.logger.info("Step 1 - TuShareServiceManager started")
            tuShareServiceManager = TuShareServiceManager()
            tuShareServiceManager.callTuShareService(start_date, end_date)
            self.logger.info("Step 1 - TuShareServiceManager ended")

            # Step 2: 执行 AkShare 数据服务
            self.logger.info("Step 2 - AkShareServiceManager started")
            akShareServiceManager = AkShareServiceManager()
            akShareServiceManager.callAkShareService(start_date, end_date)
            self.logger.info("Step 2 - AkShareServiceManager ended")

            self.logger.info("=" * 50)
            self.logger.info("Data refresh finished")
            self.logger.info("=" * 50)

        except Exception as e:
            self.logger.error(f"Error hit during the refresh: {str(e)}")
            raise e

if __name__ == '__main__':
    try:
        dataRefreshManager = DataRefreshManager()
        dataRefreshManager.fresh_data()
    except Exception as e:
        logger.error(f"refresh failed: {str(e)}")
        exit(1)
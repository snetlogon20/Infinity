from dataIntegrator.TuShareService.TuShareCNPPIService import TuShareCNPPIService
from dataIntegrator.TuShareService.TuShareService import TuShareService
from dataIntegrator import CommonLib
import os
from dataIntegrator import CommonParameters
from dataIntegrator.modelService.commonService.CalendarService import CalendarService

logger = CommonLib.logger

class TuShareCNPPIServiceTest(TuShareService):
    pass

if __name__ == '__main__':
    tuShareCNPPIService = TuShareCNPPIService()

    logger.info("=" * 80)
    logger.info("PPI工业生产者出厂价格指数测试开始")
    logger.info("=" * 80)

    start_date = "20000101"
    end_date = CommonParameters.today

    calendarService = CalendarService()
    start_month = calendarService.calculate_month(start_date)  # "201001"
    end_month = calendarService.calculate_month(end_date)  # "202607"

    logger.info(f"拉取PPI数据: {start_month} - {end_month}")

    dataFrame = tuShareCNPPIService.prepareDataFrame(start_month, end_month)
    logger.info(f"获取到 {len(dataFrame)} 条PPI记录")

    if dataFrame is not None and not dataFrame.empty:
        csvFilePath = os.path.join(CommonParameters.outBoundPath, "df_tushare_cn_ppi.csv")
        tuShareCNPPIService.saveDateFrameToDisk(csvFilePath)
        tuShareCNPPIService.deleteDateFromClickHouse(start_month, end_month)
        tuShareCNPPIService.saveDateToClickHouse()
        logger.info(f"✅ PPI数据处理完成，共 {len(dataFrame)} 条记录")
    else:
        logger.warning("PPI数据为空")

    logger.info("=" * 80)
    logger.info("PPI测试完成")
    logger.info("=" * 80)

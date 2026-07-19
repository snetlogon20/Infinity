from dataIntegrator.TuShareService.TuShareCNPMIService import TuShareCNPMIService
from dataIntegrator.TuShareService.TuShareService import TuShareService
from dataIntegrator import CommonLib
import os
from dataIntegrator import CommonParameters
from dataIntegrator.modelService.commonService.CalendarService import CalendarService

logger = CommonLib.logger

class TuShareCNPMIServiceTest(TuShareService):
    pass

if __name__ == '__main__':
    tuShareCNPMIService = TuShareCNPMIService()

    logger.info("=" * 80)
    logger.info("PMI采购经理人指数测试开始")
    logger.info("=" * 80)

    start_date = "20000101"
    end_date = CommonParameters.today

    calendarService = CalendarService()
    start_month = calendarService.calculate_month(start_date)  # "201001"
    end_month = calendarService.calculate_month(end_date)  # "202607"

    logger.info(f"拉取PMI数据: {start_month} - {end_month}")

    dataFrame = tuShareCNPMIService.prepareDataFrame(start_month, end_month)
    logger.info(f"获取到 {len(dataFrame)} 条PMI记录")

    if dataFrame is not None and not dataFrame.empty:
        csvFilePath = os.path.join(CommonParameters.outBoundPath, "df_tushare_cn_pmi.csv")
        tuShareCNPMIService.saveDateFrameToDisk(csvFilePath)
        tuShareCNPMIService.deleteDateFromClickHouse(start_month, end_month)
        tuShareCNPMIService.saveDateToClickHouse()
        logger.info(f"✅ PMI数据处理完成，共 {len(dataFrame)} 条记录")
    else:
        logger.warning("PMI数据为空")

    logger.info("=" * 80)
    logger.info("PMI测试完成")
    logger.info("=" * 80)

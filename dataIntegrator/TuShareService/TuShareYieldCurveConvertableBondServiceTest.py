import time
import os

import pandas

from dataIntegrator.TuShareService.TuShareService import TuShareService
from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.TuShareService.TuShareYieldCurveConvertableBondService import TuShareYieldCurveConvertableBondService
from dataIntegrator.modelService.commonService.CalendarService import CalendarService

logger = CommonLib.logger

class TuShareYieldCurveConvertableBondServiceTest(TuShareService):

    @classmethod
    def refresh_yc_cb(self):
        calendarService = CalendarService()
        # 获取过去600天的数据作为示例
        start_date = calendarService.calculate_T_minus_n_days(CommonParameters.today, days=600)
        end_date = CommonParameters.today
        start_date = "20190921"
        end_date = "20240922"

        # 示例曲线编码：1001.CB-中债国债收益率曲线
        ts_code_list = ["1001.CB"]

        ts_code_dict = {f"code_{i}": code for i, code in enumerate(ts_code_list, 1)}

        for key, ts_code in ts_code_dict.items():
            try:
                total_records = 0
                
                # 从 start_date 开始，每天拉取一次数据
                current_date = start_date
                
                while current_date <= end_date:
                    logger.info(f"拉取数据: {ts_code} {current_date}")
                    
                    tuShareService = TuShareYieldCurveConvertableBondService()
                    dataFrame = tuShareService.prepareDataFrame(ts_code, current_date, current_date)
                    
                    if dataFrame is not None and not dataFrame.empty:
                        batch_count = len(dataFrame)
                        total_records += batch_count
                        logger.info(f"成功获取 {batch_count} 条数据")
                        
                        # 增量刷新：先删除该日期的旧数据，再插入新数据
                        tuShareService.deleteDateFromClickHouse(ts_code, current_date, current_date)
                        tuShareService.saveDateToClickHouse()
                        
                        # 保存该日期的 CSV 文件
                        csvFilePath = os.path.join(CommonParameters.outBoundPath, rf"df_tushare_yc_cb_{ts_code}_{current_date}.csv")
                        tuShareService.saveDateFrameToDisk(csvFilePath)
                        
                        logger.info(f"日期 {current_date} 增量刷新完成")
                    else:
                        logger.warning(f"未获取到数据: {current_date}")
                    
                    # 移动到下一天
                    current_date = calendarService.calculate_T_minus_n_days(current_date, days=-1)
                    
                    # 安全检查：防止无限循环
                    if current_date <= start_date:
                        # 再往前推一天，确保循环能退出
                        current_date = calendarService.calculate_T_minus_n_days(current_date, days=-1)
                        if current_date < start_date:
                            logger.warning(f"检测到循环终止条件，退出循环")
                            break
                    
                    # 添加延时以避免接口频率限制（20次/分钟 = 每3秒一次）
                    time.sleep(3)
                
                logger.info(f"{key}: {ts_code} {start_date}-{end_date} 增量刷新完成，共 {total_records} 条数据")

            except Exception as e:
                logger.error(f"{key}: {ts_code} 处理失败：{str(e)}")

if __name__ == '__main__':
    tuShareYieldCurveConvertableBondServiceTest = TuShareYieldCurveConvertableBondServiceTest()
    tuShareYieldCurveConvertableBondServiceTest.refresh_yc_cb()

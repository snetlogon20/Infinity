from dataIntegrator.TuShareService.TuShareCNIndexDailyService import TuShareCNIndexDailyService
from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib
import os
from dataIntegrator import CommonParameters
from dataIntegrator.common.CommonDataParameters import CommonDataParameters

logger = CommonLib.logger

class TuShareCNIndexDailyServiceTest(TuShareService):
    pass

if __name__ == '__main__':
    tuShareCNIndexDailyService = TuShareCNIndexDailyService()

    """
        测试案例1：刷新上证指数
    """
    # ts_code = '000001.SH'  # 上证指数
    # end_date = CommonParameters.today
    # start_date = CommonDataParameters.get_start_date(days=360)
    # tuShareCNIndexDailyServiceTest.refresh_index_data(ts_code, start_date, end_date)

    """
        测试案例2：刷新深证成指
    """
    # ts_code = '399001.SZ'  # 深证成指
    # end_date = CommonParameters.today
    # start_date = CommonDataParameters.get_start_date(days=360)
    # tuShareCNIndexDailyServiceTest.refresh_index_data(ts_code, start_date, end_date)

    """
        测试案例3：批量刷新多个指数
    """
    index_list = CommonDataParameters.CN_INDEX_LIST
    end_date = CommonParameters.today
    start_date = CommonDataParameters.get_start_date(days=360)
    tuShareCNIndexDailyService.refresh_multiple_indexes(index_list, start_date, end_date)

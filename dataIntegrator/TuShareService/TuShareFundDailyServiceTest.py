from dataIntegrator.TuShareService.TuShareFundDailyService import TuShareFundDailyService
from dataIntegrator.TuShareService.TuShareService import TuShareService
import sys
from dataIntegrator import CommonLib
import os
from dataIntegrator import CommonParameters
from dataIntegrator.common.CommonDataParameters import CommonDataParameters

logger = CommonLib.logger

class TuShareFundDailyServiceTest(TuShareService):
    pass

if __name__ == '__main__':
    tuShareFundDailyService = TuShareFundDailyService()

    """
        测试案例1：刷新华夏上证50ETF（50ETF期权标的）
    """
    ts_code = '510050.SH'  # 华夏上证50ETF
    end_date = CommonParameters.today
    start_date = CommonDataParameters.get_start_date(days=360)
    tuShareFundDailyService.refresh_fund_data(ts_code, start_date, end_date)

    """
        测试案例2：批量刷新全部场内期权标的ETF
    """
    # tuShareFundDailyService.refresh_multiple_funds(
    #     TuShareFundDailyService.OPTION_UNDERLYING_ETF_LIST,
    #     CommonDataParameters.get_start_date(days=360),
    #     CommonParameters.today
    # )

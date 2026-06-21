from dataIntegrator import CommonLib, CommonParameters
from dataIntegrator.AKShareService.AkShareFinancialDataIndicatorService import AkShareFinancialDataIndicatorService
from dataIntegrator.common.CommonDataParameters import CommonDataParameters
from dataIntegrator.common.FileType import FileType
import os

logger = CommonLib.logger


class AkShareFinancialDataIndicatorServiceTest:

    def callAkShareFinancialDataIndicatorService(self, symbol, file_suffix, start_year=None):
        """
        统一的财务分析指标数据测试方法

        Args:
            symbol (str): 股票代码，如 '600004'
            file_suffix (str): 文件名后缀，用于区分不同股票
            start_year (str|None): 起始年份；传 None 则拉取全部历史数据。注意该参数对应新浪财经分页页面，
                                   不是"起始年份过滤器"，指定不存在的年份会返回空数据。
        """
        logger.info(f"callAkShareFinancialDataIndicatorService started... Symbol: {symbol}")

        file_path = os.path.join(CommonParameters.outBoundPath, f'akshare_financial_analysis_indicator_{file_suffix}.xlsx')

        try:
            akShareService = AkShareFinancialDataIndicatorService()

            # 获取原始数据
            dataFrame = akShareService.prepareDataFrame(symbol=symbol, start_year=start_year)

            # 保存到磁盘
            akShareService.saveDateFrameToDisk(dataFrame, file_path, FileType.EXCEL)

            # 从磁盘读取
            dataFrame = akShareService.readDataFrameFromDisk(file_path, FileType.EXCEL)

            # 删除 ClickHouse 中的旧数据
            akShareService.deleteDateFromClickHouse(symbol=symbol)

            # 转换数据格式
            dataFrame = akShareService.transformDataFrame(dataFrame)

            # 保存到 ClickHouse
            akShareService.saveDateToClickHouse(dataFrame)

        except Exception as e:
            logger.info('Exception: %s', e)
            raise e

        logger.info(f"callAkShareFinancialDataIndicatorService ended... Symbol: {symbol}")


if __name__ == '__main__':
    akShareFinancialDataIndicatorServiceTest = AkShareFinancialDataIndicatorServiceTest()

    for stock_info in CommonDataParameters.STOCK_LIST:
        ts_code = stock_info['ts_code']      # e.g. '002093.SZ'
        name = stock_info['name']             # e.g. '国脉科技'
        symbol = ts_code.split('.')[0]        # e.g. '002093'

        logger.info(f"====== 开始处理 {name} ({symbol}) ======")
        try:
            akShareFinancialDataIndicatorServiceTest.callAkShareFinancialDataIndicatorService(
                symbol=symbol,
                file_suffix=symbol,
                start_year="2020"
                # 指定不存在的年份（如新股上市前）会导致空 DataFrame
            )
        except Exception as e:
            logger.error(f"处理 {name} ({symbol}) 失败: %s", e)
        logger.info(f"====== 完成处理 {name} ({symbol}) ======")

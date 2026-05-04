from dataIntegrator.TuShareService.TushareShiborDailyService import TushareShiborDailyService
from dataIntegrator.TuShareService.TushareUSTreasuryYieldCurveService import TushareUSTreasuryYieldCurveService
from dataIntegrator import CommonLib

logger = CommonLib.logger


class RiskFreeRateManager:
    """
    无风险利率管理器
    用于根据不同国家/地区获取相应的无风险利率数据
    """

    def __init__(self):
        logger.info("RiskFreeRateManager initialized")

    def get_risk_free_rate(self, start_date: str, end_date: str, interest_country: str = "CN") -> float:
        """
        根据国家和日期范围获取无风险利率

        参数:
            start_date (str): 开始日期，格式 'YYYYMMDD'
            end_date (str): 结束日期，格式 'YYYYMMDD'
            interest_country (str): 利率国家 ('US' 或 'CN')

        返回:
            float: 最新日期的无风险利率
        """
        if interest_country == "US":
            latest_yield = self._get_us_treasury_yield(start_date, end_date)
        else:
            latest_yield = self._get_cn_shibor_rate(start_date, end_date)

        logger.info(f"最终选取收益率: {latest_yield:.4f}")
        return latest_yield

    def get_risk_free_rate_details(self, start_date: str, end_date: str, interest_country: str = "CN") -> dict:
        """
        根据国家和日期范围获取无风险利率的详细信息

        参数:
            start_date (str): 开始日期，格式 'YYYYMMDD'
            end_date (str): 结束日期，格式 'YYYYMMDD'
            interest_country (str): 利率国家 ('US' 或 'CN')

        返回:
            dict: 包含平均、最早、最新、最大、最小利率的字典
        """
        if interest_country == "US":
            avg_rate, earliest_rate, latest_rate, max_rate, min_rate = self._get_us_treasury_yield_details(start_date, end_date)
        else:
            avg_rate, earliest_rate, latest_rate, max_rate, min_rate = self._get_cn_shibor_rate_details(start_date, end_date)

        return {
            'avg_rate': avg_rate,
            'earliest_rate': earliest_rate,
            'latest_rate': latest_rate,
            'max_rate': max_rate,
            'min_rate': min_rate
        }

    def _get_us_treasury_yield(self, start_date: str, end_date: str) -> float:
        """
        获取美国国债收益率

        参数:
            start_date (str): 开始日期，格式 'YYYYMMDD'
            end_date (str): 结束日期，格式 'YYYYMMDD'

        返回:
            float: 最新日期的美国国债收益率
        """
        tushareUSTreasuryYieldCurveService = TushareUSTreasuryYieldCurveService()
        avg_yield, earliest_yield, latest_yield, max_yield, min_yield = tushareUSTreasuryYieldCurveService.get_yield_for_term(
            start_date, end_date)

        logger.info(f"平均收益率: {avg_yield:.4f}")
        logger.info(f"最早日期收益率: {earliest_yield:.4f}")
        logger.info(f"最晚日期收益率: {latest_yield:.4f}")
        logger.info(f"最大收益率: {max_yield:.4f}")
        logger.info(f"最小收益率: {min_yield:.4f}")

        return latest_yield

    def _get_cn_shibor_rate(self, start_date: str, end_date: str) -> float:
        """
        获取中国 SHIBOR 利率

        参数:
            start_date (str): 开始日期，格式 'YYYYMMDD'
            end_date (str): 结束日期，格式 'YYYYMMDD'

        返回:
            float: 最新日期的 SHIBOR 利率
        """
        tushareShiborDailyService = TushareShiborDailyService()
        avg_rate, earliest_rate, latest_rate, max_rate, min_rate = tushareShiborDailyService.get_rate_for_term(
            start_date, end_date)

        logger.info(f"平均收益率: {avg_rate:.4f}")
        logger.info(f"最早日期收益率: {earliest_rate:.4f}")
        logger.info(f"最晚日期收益率: {latest_rate:.4f}")
        logger.info(f"最大收益率: {max_rate:.4f}")
        logger.info(f"最小收益率: {min_rate:.4f}")

        return latest_rate

    def _get_us_treasury_yield_details(self, start_date: str, end_date: str) -> tuple:
        """
        获取美国国债收益率的详细信息

        参数:
            start_date (str): 开始日期，格式 'YYYYMMDD'
            end_date (str): 结束日期，格式 'YYYYMMDD'

        返回:
            tuple: (平均收益率, 最早日期收益率, 最新日期收益率, 最大收益率, 最小收益率)
        """
        tushareUSTreasuryYieldCurveService = TushareUSTreasuryYieldCurveService()
        avg_yield, earliest_yield, latest_yield, max_yield, min_yield = tushareUSTreasuryYieldCurveService.get_yield_for_term(
            start_date, end_date)

        logger.info(f"平均收益率: {avg_yield:.4f}")
        logger.info(f"最早日期收益率: {earliest_yield:.4f}")
        logger.info(f"最晚日期收益率: {latest_yield:.4f}")
        logger.info(f"最大收益率: {max_yield:.4f}")
        logger.info(f"最小收益率: {min_yield:.4f}")

        return avg_yield, earliest_yield, latest_yield, max_yield, min_yield

    def _get_cn_shibor_rate_details(self, start_date: str, end_date: str) -> tuple:
        """
        获取中国 SHIBOR 利率的详细信息

        参数:
            start_date (str): 开始日期，格式 'YYYYMMDD'
            end_date (str): 结束日期，格式 'YYYYMMDD'

        返回:
            tuple: (平均利率, 最早日期利率, 最新日期利率, 最大利率, 最小利率)
        """
        tushareShiborDailyService = TushareShiborDailyService()
        avg_rate, earliest_rate, latest_rate, max_rate, min_rate = tushareShiborDailyService.get_rate_for_term(
            start_date, end_date)

        logger.info(f"平均收益率: {avg_rate:.4f}")
        logger.info(f"最早日期收益率: {earliest_rate:.4f}")
        logger.info(f"最晚日期收益率: {latest_rate:.4f}")
        logger.info(f"最大收益率: {max_rate:.4f}")
        logger.info(f"最小收益率: {min_rate:.4f}")

        return avg_rate, earliest_rate, latest_rate, max_rate, min_rate
from dataIntegrator import CommonParameters
from dataIntegrator.modelService.option.OptionTradingStrategyManager import OptionTradingStrategyManager
from datetime import datetime, timedelta

class OptionTradingStrategyManagerTest:
    def run(self):
        # 分析区间：end_date = 今天，start_date = 今天往前推 365 天（一年）
        start_date = (datetime.strptime(CommonParameters.today, "%Y%m%d") - timedelta(days=365)).strftime("%Y%m%d")
        end_date = CommonParameters.today

        optionTradingStrategyManager = OptionTradingStrategyManager()
        optionTradingStrategyManager.run(start_date, end_date)


if __name__ == '__main__':
    OptionTradingStrategyManagerTest().run()

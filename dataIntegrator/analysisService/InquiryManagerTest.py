from dataIntegrator.analysisService.InquiryManager import InquiryManager
from dataIntegrator.plotService.LinePlotManager import LinePlotManager
from dataIntegrator.plotService.ScatterPlotManager import ScatterPlotManager
import matplotlib.pyplot as plt

class QuickInquiryManagerTest:
    def __init__(self):
        pass

    def test_get_any_dataset(self):
        sql = """
            select 
                ts_code,
                trade_date,
                open,
                high,
                low,
                close,
                pre_close,
                change,
                pct_chg,
                vol,
                amount
            from indexsysdb.df_tushare_stock_daily
            where ts_code = '000902.SZ'
            order by trade_date
        """
        dataFrame = InquiryManager().get_any_dataset(sql)

        param_dict = {
            "isPlotRequired": "yes",
            "results": dataFrame,
            "plotRequirement": {
                "PlotX": "trade_date",
                "PlotY": "open",
                "PlotTitle": "Test Line Plot",
                "xlabel": "trade_date",
                "ylabel": "open"
            }
        }
        LinePlotManager().draw_plot(param_dict)
        plt.show()

    def test_get_tushare_stock_dataset_us(self):
        """测试获取美国股票数据集"""

        market="US"
        stock="AAPL"
        start_date="20240101"
        end_date="20241207"

        dataFrame = InquiryManager().get_tushare_stock_dataset(market, stock, start_date, end_date)

        ax_line = dataFrame.plot.line(x='trade_date', y='close_point')
        ax_scatter = dataFrame.plot.scatter(x='trade_date', y='pct_change')
        ax_line.set_title(rf'Stock Close Point: {market}-{stock} Between:{start_date} ~ {end_date}')
        ax_scatter.set_title(rf'Stock Change Volatility: {market}-{stock} Between:{start_date} ~ {end_date}')
        plt.show()

    def test_get_tushare_stock_dataset_cn(self):
        """测试获取中国股票数据集"""
        market="CN"
        stock="000902.SZ"
        start_date="20240101"
        end_date="20241207"

        dataFrame = InquiryManager().get_tushare_stock_dataset(market, stock, start_date, end_date)

        ax_line = dataFrame.plot.line(x='trade_date', y='close_point')
        ax_scatter = dataFrame.plot.scatter(x='trade_date', y='pct_change')
        ax_line.set_title(rf'Stock Close Point: {market}-{stock} Between:{start_date} ~ {end_date}')
        ax_scatter.set_title(rf'Stock Change Volatility: {market}-{stock} Between:{start_date} ~ {end_date}')
        plt.show()

    def test_get_akshare_gold_dataset(self):
        """测试获取黄金数据集"""
        market="GOLD"
        stock="SGE"
        start_date="20240101"
        end_date="20241207"

        dataFrame = InquiryManager().get_akshare_gold_dataset("GOLD", "SGE", "20240101", "20251231")

        ax_line = dataFrame.plot.line(x='date', y='close')
        ax_scatter = dataFrame.plot.scatter(x='date', y='pct_change')
        ax_line.set_title(rf'Stock Close Point: {market}-{stock} Between:{start_date} ~ {end_date}')
        ax_scatter.set_title(rf'Stock Change Volatility: {market}-{stock} Between:{start_date} ~ {end_date}')
        plt.show()

    def test_get_akshare_treasury_yield_dataset(self):
        dataFrame = InquiryManager().get_akshare_treasury_yield_dataset("US", "JPM", "20240101", "20241207")
        # 可以用来画图， 但不如直接调用方便
        param_dict = {
            "isPlotRequired": "yes",
            "results": dataFrame,
            "plotRequirement": {
                "PlotX": "trade_date",
                "PlotY": "tenor_1y",
                "PlotTitle": "Test Line Plot",
                "xlabel": "trade_date",
                "ylabel": "m1"
            }
        }
        LinePlotManager().draw_plot(param_dict)

        param_dict = {
            "isPlotRequired": "yes",
            "results": dataFrame,
            "plotRequirement": {
                "PlotX": "trade_date",
                "PlotY": "pct_change",
                "PlotTitle": "Test Line Plot",
                "xlabel": "trade_date",
                "ylabel": "m1"
            }
        }
        ScatterPlotManager().draw_plot(param_dict)
        plt.show()

if __name__ == "__main__":
    inquiryManagerTest = QuickInquiryManagerTest()

    # inquiryManagerTest.test_get_any_dataset()
    # inquiryManagerTest.test_get_tushare_stock_dataset_us()
    # inquiryManagerTest.test_get_tushare_stock_dataset_cn()
    inquiryManagerTest.test_get_akshare_gold_dataset()
    # inquiryManagerTest.test_get_akshare_treasury_yield_dataset()
from dataIntegrator.analysisService.InquiryManager import InquiryManager
from dataIntegrator.modelService.MonteCarlo.MonteCarloRandomManager import MonteCarloRandomManager
from dataIntegrator.modelService.statistics.GeneralLinearRegression import GeneralLinearRegression
from dataIntegrator.modelService.statistics.StaticAnalyisManager import StaticAnalysisManager
from dataIntegrator.plotService.LinePlotManager import LinePlotManager
from dataIntegrator.plotService.ScatterPlotManager import ScatterPlotManager
import matplotlib.pyplot as plt
import seaborn as sns
import re

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

    def test_getdata_SQL_tushare_stock_usstock_gold_cn(self):
        """测试获取中国股票数据集"""

        '''---Step 0 参数区----'''
        sql="""
            SELECT 
                df_sys_calendar.trade_date AS df_sys_calendar__trade_date,
                df_tushare_us_stock_daily.pct_change AS df_tushare_us_stock_daily__pct_change,
                df_tushare_shibor_daily.tenor_on AS df_tushare_shibor_daily__tenor_on,
                df_tushare_stock_daily.pct_chg AS df_tushare_stock_daily__pct_chg,
                df_akshare_spot_hist_sge.close AS df_akshare_spot_hist_sge__close,
                df_akshare_spot_hist_sge.pct_change AS df_akshare_spot_hist_sge__pct_chg
            FROM
                df_sys_calendar
            LEFT JOIN df_tushare_us_stock_daily 
                ON df_sys_calendar.trade_date = df_tushare_us_stock_daily.trade_date 
                AND df_tushare_us_stock_daily.ts_code = 'C'
            LEFT JOIN df_tushare_shibor_daily 
                ON df_sys_calendar.trade_date = df_tushare_shibor_daily.trade_date
            LEFT JOIN df_tushare_stock_daily   
                ON df_sys_calendar.trade_date = df_tushare_stock_daily.trade_date 
                AND df_tushare_stock_daily.ts_code = '002093.SZ'
            LEFT JOIN df_akshare_spot_hist_sge 
                ON df_sys_calendar.trade_date = formatDateTime(toDate(df_akshare_spot_hist_sge.date), '%Y%m%d')
            WHERE 
                df_sys_calendar.trade_date BETWEEN '20250101' AND '20260301'
            order by df_sys_calendar__trade_date  
        """
        columns_to_drop = ['df_sys_calendar__trade_date']

        dataFrame = InquiryManager().get_sql_dataset(sql)

        '''---Step 1 先看线图----'''
        ax_line = dataFrame.plot.line(x='df_sys_calendar__trade_date', y='df_akshare_spot_hist_sge__pct_chg')
        ax_line.set_title(rf'111')

        ax_scatter = dataFrame.plot.scatter(x='df_sys_calendar__trade_date', y='df_akshare_spot_hist_sge__pct_chg')
        ax_scatter.set_title(rf'222')

        '''---Step 2 再看点图----'''
        if 'df_sys_calendar__trade_date' in dataFrame.columns:
            # 对数据按日期排序并添加行号
            result = dataFrame.sort_values(by='df_sys_calendar__trade_date').reset_index(drop=True)
            # 将日期列替换为行号
            result['df_sys_calendar__trade_date'] = range(len(result))
        corr_result = result.corr()

        '''---Step 3 看关系系数----'''
        fig, ax = plt.subplots(figsize=(10, 8))  # 创建画布和坐标轴
        heatmap = sns.heatmap(
            corr_result,  # 相关性矩阵数据
            annot=True,  # 显示数值标注
            cmap='coolwarm',  # 颜色映射方案
            fmt='.2f',  # 数值格式（保留两位小数）
            linewidths=0.5,  # 网格线宽度
            annot_kws={'size': 8},  # 注释文字大小
            ax=ax  # 绘制到指定坐标轴
        )

        plt.show()

        '''---Step 4 基本统计指标 ----'''
        dataFrame_for_correlation = dataFrame.copy()
        analyzer = StaticAnalysisManager()

        # 删除名为 "trade_date" 的列
        for col in columns_to_drop:
            if col in dataFrame_for_correlation.columns:
                dataFrame_for_correlation = dataFrame_for_correlation.drop(columns=[col])
        statistics = analyzer.analyze_with_dataframe(dataFrame_for_correlation)

        '''---Step 5 看蒙特卡罗模拟 ----'''
        monteCarloRandomManager = MonteCarloRandomManager()

        simulat_params = {
            'init_value': 'df_akshare_spot_hist_sge__close',
            'analysis_column': 'df_akshare_spot_hist_sge__pct_chg',
            't': 0.01,
            'times': 300,
            'series': 1000,
            'alpha': 0.05,
            'distribution_type': 'lognormal'  # normal/lognormal/historical
        }
        #all_line_df = monteCarloRandomManager.simulation_multi_series(dataFrame, simulat_params)
        all_line_df, all_lines, stats, var_lower_bound, var_upper_bound = monteCarloRandomManager.simulation_multi_series(dataFrame, simulat_params)
        monteCarloRandomManager.draw_plot(all_lines, simulat_params, stats, var_lower_bound, var_upper_bound)


        '''---Step 6 regression test ----'''
        '''此处放置你需要回归使用时的X轴'''
        response_dict = {}
        xColumns = "df_tushare_shibor_daily__tenor_on, df_tushare_stock_daily__pct_chg"
        yColumn = "df_tushare_us_stock_daily__pct_change"

        response_dict["sql"] = sql
        response_dict["results"] = result
        response_dict["xColumns"] = xColumns
        response_dict["yColumn"] = yColumn

        response_dict["isLinearRegressionRequired"] = "yes"

        '''此处放置你需要画图的X轴'''
        response_dict["PlotXColumn"] = "df_sys_calendar__trade_date"
        response_dict["PlotTitle"] = "df_tushare_shibor_daily__tenor_on"
        response_dict["xlabel"] = "df_sys_calendar__trade_date"
        response_dict["ylabel"] = "df_tushare_shibor_daily__tenor_on"
        response_dict["if_run_test"] = "no"
        response_dict["X_given_test_source_path"] = ""
        generalLinearRegression = GeneralLinearRegression()
        generalLinearRegression.run_linear_regression_by_AI(response_dict)

if __name__ == "__main__":
    inquiryManagerTest = QuickInquiryManagerTest()

    # inquiryManagerTest.test_get_any_dataset()
    # inquiryManagerTest.test_get_tushare_stock_dataset_us()
    # inquiryManagerTest.test_get_tushare_stock_dataset_cn()
    # inquiryManagerTest.test_get_akshare_gold_dataset()
    # inquiryManagerTest.test_get_akshare_treasury_yield_dataset()

    inquiryManagerTest.test_getdata_SQL_tushare_stock_usstock_gold_cn()
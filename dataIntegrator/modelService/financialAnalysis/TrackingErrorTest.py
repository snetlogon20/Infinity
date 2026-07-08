from dataIntegrator.modelService.financialAnalysis.TrackingError import TrackingError

class TrackingErrorTest:

    def test_tev_of_simple_data(cls):
        trackingError = TrackingError()
        ###############################################
        # Option 1, P12, caculate TEV with pure parameter
        ###############################################
        portfolio_segma = 0.25
        benchmark_segma = 0.20
        rho = 0.961
        tev = trackingError.caculate_TEV_with_number(benchmark_segma, portfolio_segma, rho)

    def test_tev_of_citi_jpm(cls):
        trackingError = TrackingError()

        ########################################
        # Option 1, fetch the data of Citi/JPM
        ########################################
        sql = """select calendar.trade_date, 
                     us_stock_daily_portfolio.pct_change as portfolio_pct_change,
                     us_stock_daily_benchmark.pct_change  as benchmark_pct_change
                     from indexsysdb.df_sys_calendar calendar
                     left join (
                         select trade_date, pct_change from indexsysdb.df_tushare_us_stock_daily
                         where ts_code = 'C' AND trade_date >= '20220101' and trade_date <='20241013'
                         ) us_stock_daily_portfolio
                         on calendar.trade_date  = us_stock_daily_portfolio.trade_date 
                     left join (
                         select trade_date, pct_change from indexsysdb.df_tushare_us_stock_daily
                         where ts_code = 'JPM' AND trade_date >= '20220101' and trade_date <='20241013'
                         ) us_stock_daily_benchmark
                         on calendar.trade_date  = us_stock_daily_benchmark.trade_date 
                     where calendar.trade_date >= '20220101' """
        portfolio_columns = ["trade_date", "portfolio_pct_change", "benchmark_pct_change"]
        portfolio_column = "portfolio_pct_change"
        benchmark_column = "benchmark_pct_change"
        portfolio_data, tev = trackingError.caculate_tev_with_sql(sql, portfolio_columns, portfolio_column, benchmark_column)

        #########################################################################
        # Option 2, caculate the tracking error with the dataframe given
        #########################################################################
        portfolio_column = "portfolio_pct_change"
        benchmark_column = "benchmark_pct_change"
        tev = trackingError.caculate_TEV_with_dataframe(portfolio_data, portfolio_column, benchmark_column)

        return tev


if __name__ == "__main__":
    trackingErrorTest = TrackingErrorTest()
    trackingErrorTest.test_tev_of_simple_data()

    '''Test the TEV for Citi/JPM'''
    trackingErrorTest.test_tev_of_citi_jpm()
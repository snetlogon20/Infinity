from dataIntegrator.dataService.ClickhouseService import ClickhouseService
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from sklearn.metrics import r2_score
from scipy import stats
import numpy as np
import pandas as pd
from dataIntegrator.utility.FileUtility import FileUtility
import matplotlib.pyplot as plt
import seaborn as sns

class MyLinearRegression:
    def __init__(self):
        pass

    def get_dataframe(self, sql, columns):
        clickhouClickhouseService = ClickhouseService()
        dataframe = clickhouClickhouseService.getDataFrame(sql, columns)

        return dataframe

    def perform_linear_regression(self, dataframe, xColumns, yColumn, X_given_test_source_path ):
        X = dataframe[xColumns]
        y = dataframe[yColumn]

        ############################
        # Step 1 Test the model
        ############################
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        model = LinearRegression()
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)

        ############################
        # Step 2 Evaluate the model
        ############################
        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        rss = np.sum((y_test - y_pred) ** 2)
        tss = np.sum((y_test - np.mean(y_test)) ** 2)
        f_statistic = (tss - rss) / model.coef_.shape[0] / (rss / (len(y_test) - X_test.shape[1] - 1))
        p_value = 1 - stats.f.cdf(f_statistic, X_test.shape[1], len(y_test) - X_test.shape[1] - 1)
        print(f"r2:{r2},mse:{mse}")
        print(f"rss:{rss},tss:{tss},f_statistic(越大越好):{f_statistic},p_value(越小越好):{p_value}")

        coefficients = pd.DataFrame(model.coef_, X.columns, columns=["Coefficient"])
        print(coefficients)

        ##################################################
        # Step 3 Predict the values per full X value
        ##################################################
        X_full_test = X
        y_full_pred = model.predict(X_full_test)

        full_test_df = pd.DataFrame(X_full_test)
        full_test_df[yColumn] = y
        full_test_df['y_full_pred'] = y_full_pred
        full_test_df['gap'] = y - y_full_pred
        full_test_df['gap_percent'] = (y - y_full_pred)/y

        ##################################################
        # Step 4 Predict the values per the given input
        ##################################################
        X_given_test = pd.read_excel(
            X_given_test_source_path,
            usecols=xColumns)
        # Make predictions
        y_given_pred = model.predict(X_given_test)

        X_given_test_df = pd.DataFrame(X_given_test)
        X_given_test_df['y_given_pred'] = y_given_pred

        ##################################################
        # Step 5 return
        ##################################################
        return (model, mse, r2, full_test_df, X_given_test_df)

    def save_data_to_excel(self, X_given_test, X_test, y_given_test, y_pred, y_test, X_given_test_output_path, option):
        # 根据样本数据预测
        y_test_series = pd.Series(y_test)
        y_pred_series = pd.Series(y_pred)
        combined_df = pd.concat(
            [X_test.reset_index(drop=True), y_test_series.reset_index(drop=True), y_pred_series.reset_index(drop=True)],
            axis=1)
        combined_df.columns = list(X_test.columns) + ['y_test', 'y_pred']
        fileName = FileUtility.generate_filename_by_timestamp(rf"{X_given_test_output_path}\prediction_{option}_with_sample_data","xlsx")
        combined_df.to_excel(fileName)

        # 根据上传测试数据预测
        y_given_test_series = pd.Series(y_given_test)
        combined_df = pd.concat([X_given_test, y_given_test_series], axis=1)
        combined_df.columns = list(X_given_test.columns) + ['y_given_test']
        fileName = FileUtility.generate_filename_by_timestamp(rf"{X_given_test_output_path}\prediction_{option}_with_query_data","xlsx")
        combined_df.to_excel(fileName)

    def save_correlation_to_excel(self, dataframe, file_full_name):
        dataframe_corr_df = dataframe.corr()
        dataframe_corr_df.to_excel(file_full_name)

    def save_correlation_to_heatmap_chart(self, dataframe, file_full_name):
        dataframe_corr_df = dataframe.corr()

        # Create the heatmap
        plt.figure(figsize=(10, 8))
        sns.heatmap(dataframe_corr_df, annot=True, cmap='coolwarm', fmt='.2f', linewidths=0.5, annot_kws={'size': 8})

        # Display the heatmap
        plt.title('Correlation Heatmap', fontsize=14)
        plt.xlabel('Features', fontsize=8)
        plt.ylabel('Features', fontsize=8)
        plt.tight_layout()
        plt.savefig(file_full_name)
        plt.show()

    def save_correlation_to_line_chart(self, dataframe, file_full_name):
        dataframe_corr_df = dataframe.corr()

        plt.figure(figsize=(10, 6))
        sns.lineplot(data=dataframe_corr_df)
        plt.title('Correlation Matrix as Line Chart')
        plt.xlabel('Columns')
        plt.ylabel('Correlation Coefficient')
        plt.xticks(rotation=10)
        plt.tight_layout()
        plt.legend(loc='lower right', bbox_to_anchor=(0.5, -0.05), ncol=3)
        # Save the plot if needed
        plt.savefig(file_full_name)
        # Show the plot
        plt.show()

    def draw_scatter_chart(self, X_given_test_df, full_test_df, mse, option, r2, yColumn):
        merged_df = pd.merge(full_test_df, X_given_test_df[['index_date', 'y_given_pred']], on='index_date', how='left')
        merged_df.to_excel(
            rf"D:\workspace_python\dataIntegrator\dataIntegrator\data\outbound\LinearRegression_{option}_merged_df.xlsx")
        plt.figure(figsize=(10, 6))
        plt.scatter(merged_df['index_date'], merged_df[yColumn], color='red', alpha=0.6, s=20)
        plt.scatter(merged_df['index_date'], merged_df['y_full_pred'], color='blue', alpha=0.6, s=2)
        plt.scatter(merged_df['index_date'], merged_df['y_given_pred'], color='green', alpha=0.6, s=100)
        # Annotate with MSE and R²
        plt.text(0.05, 0.95, f'MSE: {mse:.2f}', transform=plt.gca().transAxes, fontsize=8, verticalalignment='top')
        plt.text(0.05, 0.90, f'R²: {r2:.2f}', transform=plt.gca().transAxes, fontsize=8, verticalalignment='top')
        plt.title(rf"Predicted Values of {option} ")
        plt.xlabel('Date', fontsize=5)
        current_ticks = plt.gca().get_xticks()
        # Display labels only for every 10th tick
        plt.xticks(current_ticks[::30])
        plt.ylabel('Predicted Values (y_full_pred)')
        plt.xticks(rotation=80)
        plt.legend(['Original', 'Full Test', 'Given Test'], loc='lower right')
        plt.tight_layout()
        plt.show()

def test_linear_regression(option):
    columns, sql, xCoulmns, yColumn = load_sql(option)
    myLinearRegression = MyLinearRegression()

    ###########################
    # Step 1 获取数据 dataframe
    ###########################
    clickhouseService = ClickhouseService()
    dataframe = clickhouseService.getDataFrame(sql, columns)
    filename = FileUtility.generate_filename_by_timestamp(f"OriginalData_before_LinearRegression_{option}","xlsx")
    dataframe.to_excel(rf"D:\workspace_python\dataIntegrator\dataIntegrator\data\outbound\{filename}")

    ###########################
    # Step 2 关系系数 corr
    ###########################
    # 保存相关系数至excel
    outbound_path = FileUtility.get_outbound_path()
    filename = FileUtility.generate_filename_by_timestamp(f"LinearRegression_{option}_corr_line_chart","xlsx")
    file_full_name = rf"{outbound_path}{filename}"
    myLinearRegression.save_correlation_to_excel(dataframe, file_full_name)

    # 保存相关系数至热力图
    filename = FileUtility.generate_filename_by_timestamp(f"LinearRegression_{option}_corr_heatmap_chart","png")
    file_full_name = rf"{outbound_path}{filename}"
    myLinearRegression.save_correlation_to_heatmap_chart(dataframe, file_full_name)

    # 保存相关系数至条线图
    filename = FileUtility.generate_filename_by_timestamp(f"LinearRegression_{option}_corr_line_chart","png")
    file_full_name = rf"{outbound_path}{filename}"
    myLinearRegression.save_correlation_to_line_chart(dataframe, file_full_name)


    #####################################
    # Step 3 回归测试
    #####################################
    X_given_test_source_path= rf"D:\workspace_python\dataIntegrator\dataIntegrator\data\inbound\LinearRegression_{option}_Regression_Inquiry.xlsx"
    model, mse, r2, full_test_df, X_given_test_df = myLinearRegression.perform_linear_regression(dataframe, xCoulmns, yColumn, X_given_test_source_path)
    print(f"mse:{mse}\nr2:{r2}\n")

    ###########################
    # Step 4 写数据
    ###########################
    # 4.1 全部预测数据
    file_name = FileUtility.generate_filename_by_timestamp(
        rf"D:\workspace_python\dataIntegrator\dataIntegrator\data\outbound\LinearRegression_{option}_full_test_df", "xlsx")
    full_test_df['index_date'] = (full_test_df['calendar_trade_year'].astype(str) + "-" +
                             full_test_df['calendar_trade_month'].astype(str)+ "-" +
                             full_test_df['calendar_trade_day'].astype(str))
    full_test_df.to_excel(file_name, index=False)

    # 4.2 指定分析数据
    file_name = FileUtility.generate_filename_by_timestamp(
        rf"D:\workspace_python\dataIntegrator\dataIntegrator\data\outbound\LinearRegression_{option}_X_given_test_df", "xlsx")
    X_given_test_df['index_date'] = (X_given_test_df['calendar_trade_year'].astype(str) + "-" +
                                     X_given_test_df['calendar_trade_month'].astype(str) + "-" +
                                     X_given_test_df['calendar_trade_day'].astype(str))
    X_given_test_df.to_excel(file_name, index=False)

    ###########################
    # Step 5 Plot chart
    ###########################
    myLinearRegression.draw_scatter_chart(X_given_test_df, full_test_df, mse, option, r2, yColumn)

def load_sql(option):
    if option == "C":
        sql = """select 
                        calendar.trade_date,
                        calendar.trade_year ,
                        calendar.trade_month ,
                        calendar.trade_day ,
                        calendar.quarter,
                        cn_money_supply.m0  as m0,
                        cn_money_supply.m1  as ml,
                        cn_money_supply.m2  as m2,
                        cn_cpi.nt_yoy,
                        fx_daily.bid_close ,
                        us_stock_daily_portfolio_C.pct_change,
                        us_stock_daily_portfolio_JPM.pct_change
                    from indexsysdb.df_sys_calendar calendar
                    left join df_tushare_shibor_daily shibor_daily
                        on calendar.trade_date  = shibor_daily.trade_date 
                    left join indexsysdb.cn_money_supply cn_money_supply
                        on SUBSTRING(calendar.trade_date,1,6) = cn_money_supply.trade_date 
                    left join indexsysdb.df_tushare_cn_gdp cn_gdp
                        on calendar.trade_year || 'Q' || calendar.quarter    = cn_gdp.quarter
                    left join indexsysdb.df_tushare_cn_cpi cn_cpi
                        on SUBSTRING(calendar.trade_date,1,6)   = cn_cpi.trade_date 
                    left join indexsysdb.df_tushare_fx_daily fx_daily
                        on calendar.trade_date = fx_daily.trade_date 
                    left join (
                        select trade_date, pct_change from indexsysdb.df_tushare_us_stock_daily
                        where ts_code = 'C'
                        ) us_stock_daily_portfolio_C
                        on calendar.trade_date  = us_stock_daily_portfolio_C.trade_date 
                    left join (
                        select trade_date, pct_change from indexsysdb.df_tushare_us_stock_daily
                        where ts_code = 'JPM'
                        ) us_stock_daily_portfolio_JPM
                        on calendar.trade_date  = us_stock_daily_portfolio_JPM.trade_date 
                    where CAST(calendar.trade_year AS BIGINT)  >= '2022'
                    order by calendar.trade_date"""
        columns = ["calendar_trade_date",
                   "calendar_trade_year",
                   "calendar_trade_month",
                   "calendar_trade_day",
                   "calendar_quarter",
                   "cn_money_supply_m0",
                   "cn_money_supply_m1",
                   "cn_money_supply_m2",
                   "cn_cpi_nt_yoy",
                   "fx_daily_bid_close",
                   "us_stock_daily_portfolio_C_pct_change",
                   "us_stock_daily_portfolio_JPM_pct_change"]
        xCoulmns = [
            "calendar_trade_year",
            "calendar_trade_month",
            "calendar_trade_day",
            "calendar_quarter",
            "cn_money_supply_m0",
            "cn_money_supply_m1",
            "cn_money_supply_m2",
            "cn_cpi_nt_yoy",
            "fx_daily_bid_close",
            #"us_stock_daily_portfolio_C_pct_change",
            "us_stock_daily_portfolio_JPM_pct_change"
        ]
        yColumn = "us_stock_daily_portfolio_C_pct_change"
    elif option == "JPM":
        sql = """select 
                        calendar.trade_date,
                        calendar.trade_year ,
                        calendar.trade_month ,
                        calendar.trade_day ,
                        calendar.quarter,
                        cn_money_supply.m0  as m0,
                        cn_money_supply.m1  as ml,
                        cn_money_supply.m2  as m2,
                        cn_cpi.nt_yoy,
                        fx_daily.bid_close ,
                        us_stock_daily_portfolio_C.pct_change,
                        us_stock_daily_portfolio_JPM.pct_change
                    from indexsysdb.df_sys_calendar calendar
                    left join df_tushare_shibor_daily shibor_daily
                        on calendar.trade_date  = shibor_daily.trade_date 
                    left join indexsysdb.cn_money_supply cn_money_supply
                        on SUBSTRING(calendar.trade_date,1,6) = cn_money_supply.trade_date 
                    left join indexsysdb.df_tushare_cn_gdp cn_gdp
                        on calendar.trade_year || 'Q' || calendar.quarter    = cn_gdp.quarter
                    left join indexsysdb.df_tushare_cn_cpi cn_cpi
                        on SUBSTRING(calendar.trade_date,1,6)   = cn_cpi.trade_date 
                    left join indexsysdb.df_tushare_fx_daily fx_daily
                        on calendar.trade_date = fx_daily.trade_date 
                    left join (
                        select trade_date, pct_change from indexsysdb.df_tushare_us_stock_daily
                        where ts_code = 'C'
                        ) us_stock_daily_portfolio_C
                        on calendar.trade_date  = us_stock_daily_portfolio_C.trade_date 
                    left join (
                        select trade_date, pct_change from indexsysdb.df_tushare_us_stock_daily
                        where ts_code = 'JPM'
                        ) us_stock_daily_portfolio_JPM
                        on calendar.trade_date  = us_stock_daily_portfolio_JPM.trade_date 
                    where CAST(calendar.trade_year AS BIGINT)  >= '2022'
                    order by calendar.trade_date"""
        columns = ["calendar_trade_date",
                   "calendar_trade_year",
                   "calendar_trade_month",
                   "calendar_trade_day",
                   "calendar_quarter",
                   "cn_money_supply_m0",
                   "cn_money_supply_m1",
                   "cn_money_supply_m2",
                   "cn_cpi_nt_yoy",
                   "fx_daily_bid_close",
                   "us_stock_daily_portfolio_C_pct_change",
                   "us_stock_daily_portfolio_JPM_pct_change"]
        xCoulmns = [
            "calendar_trade_year",
            "calendar_trade_month",
            "calendar_trade_day",
            "calendar_quarter",
            "cn_money_supply_m0",
            "cn_money_supply_m1",
            "cn_money_supply_m2",
            "cn_cpi_nt_yoy",
            "fx_daily_bid_close",
            "us_stock_daily_portfolio_C_pct_change",
            #"us_stock_daily_portfolio_JPM_pct_change"
        ]
        yColumn = "us_stock_daily_portfolio_JPM_pct_change"
    if option == "TreasuryRate_C":
        sql = """select 
                calendar.trade_date,
                calendar.trade_year ,
                calendar.trade_month ,
                calendar.trade_day ,
                calendar.quarter,
                cn_money_supply.m0  as m0,
                cn_money_supply.m1  as ml,
                cn_money_supply.m2  as m2,
                cn_cpi.nt_yoy,
                fx_daily.bid_close ,
                df_tushare_us_treasury_yield_cruve.m1,
                df_tushare_us_treasury_yield_cruve.m2,
                df_tushare_us_treasury_yield_cruve.m3,
                df_tushare_us_treasury_yield_cruve.m6,
                df_tushare_us_treasury_yield_cruve.y1,
                df_tushare_us_treasury_yield_cruve.y2,
                df_tushare_us_treasury_yield_cruve.y3,
                df_tushare_us_treasury_yield_cruve.y5,
                df_tushare_us_treasury_yield_cruve.y7,
                df_tushare_us_treasury_yield_cruve.y1,
                df_tushare_us_treasury_yield_cruve.y2,
                df_tushare_us_treasury_yield_cruve.y30,
                us_stock_daily_portfolio_C.pct_change,
                us_stock_daily_portfolio_C.close_point,
                us_stock_daily_portfolio_JPM.pct_change
            from indexsysdb.df_sys_calendar calendar
            left join df_tushare_shibor_daily shibor_daily
                on calendar.trade_date  = shibor_daily.trade_date 
            left join indexsysdb.cn_money_supply cn_money_supply
                on SUBSTRING(calendar.trade_date,1,6) = cn_money_supply.trade_date 
            left join indexsysdb.df_tushare_cn_gdp cn_gdp
                on calendar.trade_year || 'Q' || calendar.quarter    = cn_gdp.quarter
            left join indexsysdb.df_tushare_cn_cpi cn_cpi
                on SUBSTRING(calendar.trade_date,1,6)   = cn_cpi.trade_date 
            left join indexsysdb.df_tushare_fx_daily fx_daily
                on calendar.trade_date = fx_daily.trade_date 
            left join (
                select * from indexsysdb.df_tushare_us_treasury_yield_cruve
                ) df_tushare_us_treasury_yield_cruve
                on calendar.trade_date  = df_tushare_us_treasury_yield_cruve.trade_date 
            left join (
                select trade_date, pct_change,close_point from indexsysdb.df_tushare_us_stock_daily
                where ts_code = 'C'
                ) us_stock_daily_portfolio_C
                on calendar.trade_date  = us_stock_daily_portfolio_C.trade_date 
            left join (
                select trade_date, pct_change from indexsysdb.df_tushare_us_stock_daily
                where ts_code = 'JPM'
                ) us_stock_daily_portfolio_JPM
                on calendar.trade_date  = us_stock_daily_portfolio_JPM.trade_date 
            where CAST(calendar.trade_year AS BIGINT)  >= '2022'
            order by calendar.trade_date"""
        columns = ["calendar_trade_date",
                   "calendar_trade_year",
                   "calendar_trade_month",
                   "calendar_trade_day",
                   "calendar_quarter",
                   "cn_money_supply_m0",
                   "cn_money_supply_m1",
                   "cn_money_supply_m2",
                   "cn_cpi_nt_yoy",
                   "fx_daily_bid_close",
                   "m1",
                   "m2",
                   "m3",
                   "m6",
                   "y1",
                   "y2",
                   "y3",
                   "y5",
                   "y7",
                   "y10",
                   "y20",
                   "y30",
                   "us_stock_daily_portfolio_C_pct_change",
                   "us_stock_daily_portfolio_C_close_point",
                   "us_stock_daily_portfolio_JPM_pct_change"]
        xCoulmns = [
            "calendar_trade_year",
            "calendar_trade_month",
            "calendar_trade_day",
            "calendar_quarter",
            "cn_money_supply_m0",
            "cn_money_supply_m1",
            "cn_money_supply_m2",
            "cn_cpi_nt_yoy",
            "fx_daily_bid_close",
            "m1",
            "m2",
            "m3",
            "m6",
            "y1",
            "y2",
            "y3",
            "y5",
            "y7",
            "y10",
            "y20",
            "y30",
            "us_stock_daily_portfolio_C_pct_change",
            #"us_stock_daily_portfolio_C_pct_change",
            "us_stock_daily_portfolio_JPM_pct_change"
        ]
        yColumn = "us_stock_daily_portfolio_C_close_point"

    return columns, sql, xCoulmns, yColumn


def init():
    pd.set_option('display.max_rows', None)  # 设置打印所有行
    pd.set_option('display.max_columns', None)  # 设置打印所有列
    pd.set_option('display.width', None)  # 自动检测控制台的宽度
    pd.set_option('display.max_colwidth', None)  # 设置列的最大宽度

if __name__ == "__main__":
    # 根据输入的 股票代码逐个计算线性回归
    init()
    test_linear_regression("C")
    test_linear_regression("JPM")
    test_linear_regression("TreasuryRate_C")
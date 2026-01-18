from dataIntegrator.dataService.ClickhouseService import ClickhouseService
import pandas as pd

class InquiryManager:

    @classmethod
    def get_any_dataset(cls, sql):

        clickhouseService = ClickhouseService()
        dataFrame = clickhouseService.getDataFrameWithoutColumnsName(sql)

        return dataFrame

    @classmethod
    def get_tushare_stock_dataset(cls, market, stock, start_date, end_date):
        if market == "US":
            sql = rf"""
                    select ts_code,
                            trade_date,
                            close_point,
                            open_point,
                            high_point,
                            low_point,
                            pre_close,
                            change_point,
                            pct_change,
                            vol,
                            amount,
                            vwap,
                            turnover_ratio,
                            total_mv,
                            pe,
                            pb
                    from indexsysdb.df_tushare_us_stock_daily
                    where ts_code = '{stock}' AND 
                    trade_date>= '{start_date}' and 
                    trade_date <='{end_date}'
                        """

        if market == "CN":
            sql = rf"""
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
                    where ts_code = '{stock}' AND
                            trade_date >= '{start_date}' AND 
                            trade_date <= '{end_date}'
                    order by trade_date
                        """

        clickhouseService = ClickhouseService()
        dataFrame = clickhouseService.getDataFrameWithoutColumnsName(sql)

        # 尝试将数值列转换为数值类型
        if market == "US":
            numeric_columns = ['close_point', 'open_point', 'high_point', 'low_point',
                               'pre_close', 'change_point', 'pct_change', 'vol', 'amount',
                               'vwap', 'turnover_ratio', 'total_mv', 'pe', 'pb']
        elif market == "CN":
            numeric_columns = ['open', 'high', 'low', 'close', 'pre_close',
                               'change', 'pct_chg', 'vol', 'amount']

        for col in numeric_columns:
            if col in dataFrame.columns:
                dataFrame[col] = pd.to_numeric(dataFrame[col], errors='coerce')

        # if market == "US":
        #     ax_line = dataFrame.plot.line(x='trade_date', y='close_point')
        #     ax_scatter = dataFrame.plot.scatter(x='trade_date', y='pct_change')
        #
        # elif market == "CN":
        #     ax_line = dataFrame.plot.line(x='trade_date', y='close')
        #     ax_scatter = dataFrame.plot.scatter(x='trade_date', y='pct_chg')
        #
        # ax_line.set_title(rf'Stock Close Point: {market}-{stock} Between:{start_date} ~ {end_date}')
        # ax_scatter.set_title(rf'Stock Change Volatility: {market}-{stock} Between:{start_date} ~ {end_date}')

        return dataFrame

    @classmethod
    def get_akshare_gold_dataset(cls, market, stock, start_date, end_date):

        sql = rf"""
                select 
                    date,
                    open,
                    close,
                    low,
                    high,
                    pct_change 
                from indexsysdb.df_akshare_spot_hist_sge
                order by date 
                """

        clickhouseService = ClickhouseService()
        dataFrame = clickhouseService.getDataFrameWithoutColumnsName(sql)

        # ax_line = dataFrame.plot.line(x='date', y='close')
        # ax_scatter = dataFrame.plot.scatter(x='date', y='close')
        #
        # ax_line.set_title(rf'Stock Close Point: {market}-{stock} Between:{start_date} ~ {end_date}')
        # ax_scatter.set_title(rf'Stock Change Volatility: {market}-{stock} Between:{start_date} ~ {end_date}')

        return dataFrame

    @classmethod
    def get_akshare_treasury_yield_dataset(cls, market, stock, start_date, end_date):

        sql = rf"""
                SELECT trade_date, m1
                FROM indexsysdb.df_tushare_us_treasury_yield_cruve
                --where trade_date>='20230809'
                """

        clickhouseService = ClickhouseService()
        dataFrame = clickhouseService.getDataFrameWithoutColumnsName(sql)

        # 计算涨跌幅：(当前收盘价 - 前一日收盘价) / 前一日收盘价
        dataFrame['pct_change'] = dataFrame['m1'].pct_change() * 100

        return dataFrame

    @classmethod
    def get_sql_dataset(cls, sql):

        clickhouseService = ClickhouseService()
        dataFrame = clickhouseService.getDataFrameWithoutColumnsName(sql)

        return dataFrame
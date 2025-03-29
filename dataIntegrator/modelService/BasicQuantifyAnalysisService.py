import pandas as pd
from holoviews.ipython import display

from dataIntegrator.TuShareService.TuShareService import TuShareService

class CommonCKQuery(TuShareService):

    @classmethod
    def getQueryResult(self, queryStatment =""):
        try:
            queryStatment = """select cn_money_supply.m1
                            from indexsysdb.df_sys_calendar calendar
                            left join df_tushare_shibor_daily shibor_daily
                            on calendar.trade_date  = shibor_daily.trade_date 
                            left join indexsysdb.cn_money_supply cn_money_supply
                            on SUBSTRING(calendar.trade_date,1,6) = cn_money_supply.trade_date 
                            left join indexsysdb.df_tushare_cn_gdp cn_gdp
                            on calendar.trade_year || 'Q' || calendar.quarter    = cn_gdp.quarter 
                            where CAST(calendar.trade_year AS BIGINT)  >= '2018'
                            order by calendar.trade_date"""

            result = self.clickhouseClient.execute(queryStatment)
            df = pd.DataFrame(result)

            print(df)
            df1 = df.dropna()
            print(df1.columns.tolist())

            df1 = pd.DataFrame(df1, columns=[0])
            stats = pd.DataFrame()
            stats["Mean"] = df1.mean()
            stats["Std_Dev"] = df1.std()
            stats["Variance"] = df1.var()
            stats["kurt"] = df1.kurt()
            stats["skew"] = df1.skew()
            stats["median"] = df1.median()
            stats["sem"] = df1.sem()
            stats["skew"] = df1.skew()
            display(stats)

            return df
        except Exception as e:
            print('Exception', e)
            raise e

if __name__ == '__main__':
    commonCKQuery = CommonCKQuery()
    commonCKQuery.getQueryResult()


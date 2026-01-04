import pandas

from dataIntegrator import CommonLib
from dataIntegrator.AKShareService.AkShareService import AkShareService
import sys
import pandas as pd
logger = CommonLib.logger

class AkShareFDIService(AkShareService):

    def prepareDataFrame(self, start_date, end_date):
        logger.info("prepareData started")

        try:
            dataFrame = self.ak.macro_china_fdi()

        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("prepareData completed")
        return dataFrame

    @classmethod
    def transformDataFrame(self, dataFrame: pandas.core.frame.DataFrame):
        logger.info("transformData started")

        try:

            # 重命名列以匹配英文字段名
            # 原始列名: ['月份', '当月', '当月-同比增长', '当月-环比增长', '累计', '累计-同比增长']
            # 目标列名: ['month', 'current_month', 'YoY', 'MoM', 'YTD_YoY', 'YTD_MoM']
            column_mapping = {
                '月份': 'month',
                '当月': 'current_month',
                '当月-同比增长': 'YoY',
                '当月-环比增长': 'MoM',
                '累计': 'YTD_YoY',
                '累计-同比增长': 'YTD_MoM'
            }

            # 仅重命名存在于DataFrame中的列
            existing_columns = {k: v for k, v in column_mapping.items() if k in dataFrame.columns}
            dataFrame = dataFrame.rename(columns=existing_columns)

            # 转换月份格式从 "2008年01月份" 到 "200801"
            if 'month' in dataFrame.columns:
                # 使用正则表达式提取年份和月份，去除"份"字
                import re
                dataFrame['month'] = dataFrame['month'].apply(
                    lambda x: re.sub(r'(\d{4})年(\d{2})月.?', r'\1\2', str(x)) if pd.notna(x) else x
                )
                dataFrame['month'] = dataFrame['month'].astype(str)

            # 数据类型处理以匹配ClickHouse表结构
            if 'current_month' in dataFrame.columns:
                # 将current_month转换为数值类型，NaN值转换为None（ClickHouse中的NULL）
                dataFrame['current_month'] = pd.to_numeric(dataFrame['current_month'], errors='coerce')
                # 将NaN替换为None，以便ClickHouse能正确处理
                dataFrame['current_month'] = dataFrame['current_month'].where(
                    pd.notna(dataFrame['current_month']), None)

            float_columns = ['YoY', 'MoM', 'YTD_YoY', 'YTD_MoM']
            for col in float_columns:
                if col in dataFrame.columns:
                    # 转换为数值类型，NaN值转换为None
                    dataFrame[col] = pd.to_numeric(dataFrame[col], errors='coerce')
                    # 将NaN替换为None
                    dataFrame[col] = dataFrame[col].where(pd.notna(dataFrame[col]), None)

            # 将整个DataFrame中的NaN值转换为0
            dataFrame = dataFrame.fillna(0)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("transformData completed")
        return dataFrame

    def saveDateToClickHouse(self, dataFrame):
        logger.info("saveDateToClickHouse started")
        
        try:
            # 数据预处理：转换月份列
            if 'month' in dataFrame.columns:
                dataFrame['month'] = dataFrame['month'].astype(str)
            
            insert_sql = "INSERT INTO indexsysdb.df_akshare_fdi VALUES"
            self.saveAkDateToClickHouse(insert_sql, dataFrame)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e
        
        logger.info("saveDateToClickHouse completed")
        return

    def deleteDateFromClickHouse(self, start_date="0000000", end_date="0000000"):
        logger.info("deleteDataFromClickHouse started")

        try:
            # 使用 month 字段进行删除操作
            del_df_akshare_sql = "ALTER TABLE indexsysdb.df_akshare_fdi DELETE where month>= '%s' and month<='%s'" % (start_date, end_date)
            self.deleteAkDateFromClickHouse(del_df_akshare_sql)
        except Exception as e:
            self.writeLogError(e, className=self.__class__.__name__, functionName=sys._getframe().f_code.co_name)
            raise e

        logger.info("deleteDateFromClickHouse completed")
        return

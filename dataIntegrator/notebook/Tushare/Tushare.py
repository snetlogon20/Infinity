#!/usr/bin/env python
# coding: utf-8

# In[3]:


# Shibor
import tushare as ts
ts.set_token('00fcaf64c13f1a8e58011bb7b07d2016f9c632e7711162c0b95c2003')
pro = ts.pro_api()
dataFrame = pro.shibor(start_date='20220101', end_date='20220521')
dataFrame.dtypes

dataFrame.columns = ['trade_date','tenor_on','tenor_1w','tenor_2w','tenor_1m','tenor_3m','tenor_6m','tenor_9m','tenor_1y']
dataFrame

from clickhouse_driver import Client
#Step 2 connect click house
client = Client(host='192.168.98.135',database='indexsysdb')

#Setp 3 insert into click house
insert_sql_statement = 'insert into indexsysdb.df_tushare_shibor_daily (trade_date,tenor_on,tenor_1w,tenor_2w,tenor_1m,tenor_3m,tenor_6m,tenor_9m,tenor_1y) VALUES'
data = dataFrame.to_dict('records')
client.execute(insert_sql_statement,data)


# In[7]:


# LPR 贷款基础利率
import tushare as ts
ts.set_token('00fcaf64c13f1a8e58011bb7b07d2016f9c632e7711162c0b95c2003')
pro = ts.pro_api()
dataFrame = pro.shibor_lpr(start_date='20220101', end_date='20220521')
dataFrame.dtypes

dataFrame.columns = [
    "trade_date",
    "tenor_1y",
     "tenor_5y"]
dataFrame


# In[9]:


# LPR 贷款基础利率
import tushare as ts
ts.set_token('00fcaf64c13f1a8e58011bb7b07d2016f9c632e7711162c0b95c2003')
pro = ts.pro_api()
dataFrame = pro.shibor_lpr(start_date='20220101', end_date='20220521')
dataFrame.dtypes

dataFrame.columns = [
    "trade_date",
    "tenor_1y",
    "tenor_5y"]
dataFrame

from clickhouse_driver import Client
#Step 2 connect click house
client = Client(host='192.168.98.135',database='indexsysdb')

#Step 3 remove the previous records
delete_sql_statement = "ALTER TABLE indexsysdb.df_tushare_shibor_lpr_daily DELETE where trade_date>= '20220501' and trade_date<='20220601'"
client.execute(delete_sql_statement)

#Setp 3 insert into click house
insert_sql_statement = 'insert into indexsysdb.df_tushare_shibor_lpr_daily (trade_date,tenor_1y,tenor_5y) VALUES'
data = dataFrame.to_dict('records')
client.execute(insert_sql_statement,data)


# In[11]:


# GDP数据
import tushare as ts
ts.set_token('00fcaf64c13f1a8e58011bb7b07d2016f9c632e7711162c0b95c2003')
pro = ts.pro_api()
dataFrame = pro.cn_gdp(start_q='2018Q1', end_q='2022Q1')
dataFrame.dtypes

dataFrame.columns = ['quarter',
'gdp',
'gdp_yoy',
'pi',
'pi_yoy',
'si',
'si_yoy',
'ti',
'ti_yoy']
dataFrame.head(5)

from clickhouse_driver import Client
#Step 2 connect click house
client = Client(host='192.168.98.135',database='indexsysdb')

#Step 3 remove the previous records
delete_sql_statement = "ALTER TABLE indexsysdb.df_tushare_cn_gdp DELETE where quarter = '2018Q1'"
client.execute(delete_sql_statement)

#Setp 4 insert into click house
insert_sql_statement = 'insert into indexsysdb.df_tushare_cn_gdp (quarter,gdp ,gdp_yoy ,pi ,pi_yoy ,si ,si_yoy ,ti ,ti_yoy) VALUES'
data = dataFrame.to_dict('records')
client.execute(insert_sql_statement,data)


# In[52]:


# 货币供应量
import tushare as ts
ts.set_token('00fcaf64c13f1a8e58011bb7b07d2016f9c632e7711162c0b95c2003')
pro = ts.pro_api()
dataFrame = pro.cn_m(start_m='200001', end_m='202212')
dataFrame.dtypes

dataFrame.columns = ['trade_date',
'm0',
'm0_yoy',
'm0_mom',
'm1',
'm1_yoy',
'm1_mom',
'm2',
'm2_yoy',
'm2_mom']
dataFrame.head(5)

from clickhouse_driver import Client
#Step 2 connect click house
client = Client(host='192.168.98.135',database='indexsysdb')

#Step 3 remove the previous records
delete_sql_statement = "ALTER TABLE indexsysdb.cn_money_supply DELETE where trade_date >='202001' and trade_date <='202212'"
client.execute(delete_sql_statement)

#Setp 4 insert into click house
insert_sql_statement = 'insert into indexsysdb.cn_money_supply (trade_date,m0,m0_yoy,m0_mom,m1 ,m1_yoy ,m1_mom ,m2 ,m2_yoy,m2_mom) VALUES'
data = dataFrame.to_dict('records')
client.execute(insert_sql_statement,data)


# In[1]:


# 居民消费价格指数（CPI）
import tushare as ts
ts.set_token('00fcaf64c13f1a8e58011bb7b07d2016f9c632e7711162c0b95c2003')
pro = ts.pro_api()
dataFrame = pro.cn_cpi(start_m='200001', end_m='202201')
dataFrame.dtypes

dataFrame.columns = ['trade_date',
'nt_val',
'nt_yoy',
'nt_mom',
'nt_accu',
'town_val',
'town_yoy',
'town_mom',
'town_accu',
'cnt_val',
'cnt_yoy',
'cnt_mom',
'cnt_accu']
dataFrame.head(5)

from clickhouse_driver import Client
#Step 2 connect click house
client = Client(host='192.168.98.135',database='indexsysdb')

#Step 3 remove the previous records
delete_sql_statement = "ALTER TABLE indexsysdb.df_tushare_cn_cpi DELETE where trade_date >='200001' and trade_date <='202201'"
client.execute(delete_sql_statement)

#Setp 4 insert into click house
insert_sql_statement = 'insert into indexsysdb.df_tushare_cn_cpi (trade_date,nt_val,nt_yoy,nt_mom,nt_accu,town_val,town_yoy,town_mom,town_accu ,cnt_val,cnt_yoy,cnt_mom,cnt_accu) VALUES'
data = dataFrame.to_dict('records')
client.execute(insert_sql_statement,data)


# In[80]:


# 美股行情
import tushare as ts
ts.set_token('00fcaf64c13f1a8e58011bb7b07d2016f9c632e7711162c0b95c2003')
pro = ts.pro_api()
dataFrame = pro.us_daily(ts_code='C', start_date='19800101', end_date='20220528')
#dataFrame = pro.us_daily(ts_code='AAPL', start_date='19800101', end_date='20220528')
#dataFrame = pro.us_daily(ts_code='DJI', start_date='19800101', end_date='20220528')
#dataFrame = pro.us_daily(start_date='19800101', end_date='20220528')
dataFrame.dtypes


# In[81]:


dataFrame


# In[82]:


dataFrame.dtypes
dataFrame.columns = ['ts_code',
'trade_date',
'close_point',
'open_point',
'high_point',
'low_point',
'pre_close',
'pct_change',
'vol',
'amount',
'vwap']
dataFrame.head(5)

from clickhouse_driver import Client
#Step 2 connect click house
client = Client(host='192.168.98.135',database='indexsysdb')

#Step 3 remove the previous records
delete_sql_statement = "ALTER TABLE indexsysdb.df_tushare_us_stock_daily DELETE where ts_code='AAPL' and trade_date >='19800101' and trade_date <='20220528'"
client.execute(delete_sql_statement)

#Setp 4 insert into click house
insert_sql_statement = 'insert into indexsysdb.df_tushare_us_stock_daily (ts_code,trade_date,close_point,open_point,high_point,low_point,pre_close,pct_change,vol,amount,vwap) VALUES'
data = dataFrame.to_dict('records')
client.execute(insert_sql_statement,data)


# In[83]:


# 期货合约信息表
import tushare as ts
ts.set_token('00fcaf64c13f1a8e58011bb7b07d2016f9c632e7711162c0b95c2003')
pro = ts.pro_api()
dataFrame = pro.fut_basic(exchange='DCE', fut_type='1', fields='ts_code,symbol,name,list_date,delist_date,quote_unit')
dataFrame.dtypes
dataFrame

from clickhouse_driver import Client
#Step 2 connect click house
client = Client(host='192.168.98.135',database='indexsysdb')

#Step 3 remove the previous records
delete_sql_statement = "truncate table indexsysdb.df_tushare_future_basic_information"
client.execute(delete_sql_statement)

#Setp 4 insert into click house
insert_sql_statement = 'insert into indexsysdb.df_tushare_future_basic_information (ts_code,symbol,name,quote_unit,list_date,delist_date) VALUES'
data = dataFrame.to_dict('records')
client.execute(insert_sql_statement,data)


# In[80]:


dataFrame


# In[13]:


# 期货合约信息表
import tushare as ts
ts.set_token('00fcaf64c13f1a8e58011bb7b07d2016f9c632e7711162c0b95c2003')
pro = ts.pro_api()
dataFrame = pro.fut_daily(ts_code='JM2304.DCE', start_date='20180101', end_date='20220501')
print(dataFrame.dtypes)
dataFrame


# In[106]:


from clickhouse_driver import Client
#Step 2 connect click house
client = Client(host='192.168.98.135',database='indexsysdb')

#Step 3 remove the previous records
delete_sql_statement = "ALTER TABLE indexsysdb.df_tushare_future_daily DELETE where ts_code='JM2304.DCE' and (trade_date >='200001' and trade_date <='202201')"
client.execute(delete_sql_statement)

#Setp 4 insert into click house
insert_sql_statement = 'insert into indexsysdb.df_tushare_future_daily (ts_code,trade_date,pre_close,pre_settle,open,high,low,close,settle,change1,change2,vol,amount,oi,oi_chg) VALUES'
data = dataFrame.to_dict('records')
client.execute(insert_sql_statement,data)


# In[14]:


# 美股列表
import tushare as ts
ts.set_token('00fcaf64c13f1a8e58011bb7b07d2016f9c632e7711162c0b95c2003')
pro = ts.pro_api()
dataFrame = pro.us_basic()
dataFrame
print(dataFrame.dtypes)

# import pandas as pd
# import numpy as np

# dataFrame.loc[pd.isnull(dataFrame.loc[:, 'name']), 'name'] = 'unknown'
# dataFrame.loc[pd.isnull(dataFrame.loc[:, 'delist_date']), 'delist_date'] = 'unknown'

dataFrame


# In[75]:


from pandasql import sqldf
global df_us_stock_basic
query_df_tushare_stock_basic = "select * from dataFrame where ts_code like 'DJ%'"
us_stock_basic_dateFrame_selected = sqldf(query_df_tushare_stock_basic)
us_stock_basic_dateFrame_selected


# In[77]:


from clickhouse_driver import Client
#Step 2 connect click house
client = Client(host='192.168.98.135',database='indexsysdb')

#Step 3 remove the previous records
delete_sql_statement = "ALTER TABLE indexsysdb.df_tushare_us_stock_basic DELETE where list_date is not null"
client.execute(delete_sql_statement)

#Setp 4 insert into click house
insert_sql_statement = 'insert into indexsysdb.df_tushare_us_stock_basic (ts_code,name,classify,list_date,delist_date) VALUES'
data = dataFrame.to_dict('records')
#print(data)
client.execute(insert_sql_statement,data)


# In[91]:


# 港股日线行情
import tushare as ts
ts.set_token('00fcaf64c13f1a8e58011bb7b07d2016f9c632e7711162c0b95c2003')
pro = ts.pro_api()
dataFrame = pro.hk_daily(ts_code='00001.HK', start_date='20000101', end_date='20220528')
dataFrame
print(dataFrame.dtypes)

from clickhouse_driver import Client
#Step 2 connect click house
client = Client(host='192.168.98.135',database='indexsysdb')

#Step 3 remove the previous records
delete_sql_statement = "ALTER TABLE indexsysdb.df_tushare_hk_stock_daily DELETE where ts_code='00001.HK' and trade_date >='19800101' and trade_date <='20220528'"
client.execute(delete_sql_statement)

#Setp 4 insert into click house
insert_sql_statement = 'insert into indexsysdb.df_tushare_hk_stock_daily (ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount) VALUES'
data = dataFrame.to_dict('records')
client.execute(insert_sql_statement,data)


# In[18]:


# 外汇基础信息
import tushare as ts
ts.set_token('00fcaf64c13f1a8e58011bb7b07d2016f9c632e7711162c0b95c2003')
pro = ts.pro_api()
dataFrame = pro.fx_obasic(exchange='FXCM', classify='INDEX')
dataFrame
print(dataFrame.dtypes)

dataFrame

from clickhouse_driver import Client
#Step 2 connect click house
client = Client(host='192.168.98.135',database='indexsysdb')

#Step 3 remove the previous records
delete_sql_statement = "ALTER TABLE indexsysdb.df_tushare_fx_offshore_basic DELETE where ts_code is not Null"
client.execute(delete_sql_statement)

#Setp 4 insert into click house
insert_sql_statement = 'insert into indexsysdb.df_tushare_fx_offshore_basic (ts_code,name,classify ,exchange,min_unit ,max_unit,pip ,pip_cost,traget_spread,min_stop_distance,trading_hours,break_time) VALUES'
data = dataFrame.to_dict('records')
client.execute(insert_sql_statement,data)


# In[95]:





# In[13]:


# 外汇日线行情
import tushare as ts
ts.set_token('00fcaf64c13f1a8e58011bb7b07d2016f9c632e7711162c0b95c2003')
pro = ts.pro_api()
#dataFrame = pro.fx_daily(ts_code='USDCNH.FXCM', start_date='20190101', end_date='20220530')  #美元人民币
dataFrame = pro.fx_daily(ts_code='US30.FXCM', start_date='20190101', end_date='20220530')  #道琼斯
dataFrame
print(dataFrame.dtypes)

from clickhouse_driver import Client
#Step 2 connect click house
client = Client(host='192.168.98.135',database='indexsysdb')

#Step 3 remove the previous records
delete_sql_statement = "ALTER TABLE indexsysdb.df_tushare_fx_daily DELETE where ts_code='US30.FXCM' and trade_date >='19800101' and trade_date <='20220528'"
client.execute(delete_sql_statement)

#Setp 4 insert into click house
insert_sql_statement = 'insert into indexsysdb.df_tushare_fx_daily (ts_code,trade_date,bid_open,bid_close,bid_high,bid_low,ask_open,ask_close,ask_high,ask_low,tick_qty) VALUES'
data = dataFrame.to_dict('records')
client.execute(insert_sql_statement,data)


# In[21]:


import pandas as pd
from pandas import DataFrame

#print(dataFrame)

data=dataFrame.to_dict("records")

DataFrame(data).to_excel('D:\workspace_python\practice\data\d.xlsx',sheet_name='测试')


# In[21]:


# 现货黄金日行情
import tushare as ts
ts.set_token('00fcaf64c13f1a8e58011bb7b07d2016f9c632e7711162c0b95c2003')
pro = ts.pro_api()
#dataFrame = pro.sge_daily(trade_date='20220311')
dataFrame = pro.sge_daily()
print(dataFrame.dtypes)

print(dataFrame)

from clickhouse_driver import Client
#Step 2 connect click house
client = Client(host='192.168.98.135',database='indexsysdb')

#Step 3 remove the previous records
delete_sql_statement = "ALTER TABLE indexsysdb.df_tushare_sge_daily DELETE where trade_date >='19800101' and trade_date <='20220528'"
client.execute(delete_sql_statement)

#Setp 4 insert into click house
insert_sql_statement = 'insert into indexsysdb.df_tushare_sge_daily (ts_code,trade_date,close,open,high,low,price_avg,change,pct_change,vol,amount,oi,settle_vol,settle_dire) VALUES'
data = dataFrame.to_dict('records')
client.execute(insert_sql_statement,data)


# In[102]:


from sqlalchemy import create_engine
import pandas as pd
import os

# 导入支持oracle的数据类型
from sqlalchemy.dialects.oracle import \
    BFILE, BLOB, CHAR, CLOB, DATE, \
    DOUBLE_PRECISION, FLOAT, INTERVAL, LONG, NCLOB, \
    NUMBER, NVARCHAR, NVARCHAR2, RAW, TIMESTAMP, VARCHAR, \
    VARCHAR2


# 定义函数，自动输出DataFrme数据写入oracle的数类型字典表,配合to_sql方法使用(注意，其类型只能是SQLAlchemy type )
def mapping_df_types(df):
    dtypedict = {}
    for i, j in zip(df.columns, df.dtypes):
        if "object" in str(j):
            dtypedict.update({i: VARCHAR(256)})
        if "float" in str(j):
            dtypedict.update({i: NUMBER(19, 8)})
        if "int" in str(j):
            dtypedict.update({i: VARCHAR(19)})

    return dtypedict


# 连接Oracle
os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.UTF8'
conn_string = 'oracle+cx_oracle://zs:zs@192.168.98.129:1521/orcl'
engine = create_engine(conn_string)

# 读取 Tushare
import tushare as ts

ts.set_token('00fcaf64c13f1a8e58011bb7b07d2016f9c632e7711162c0b95c2003')
pro = ts.pro_api()
dataFrame = pro.daily(ts_code='600000.SH', start_date="20220101", end_date='20220521')
dataFrame.dtypes
dataFrame

# 写入Oracle
dataFrame.to_sql('df_tushare_stock_daily', engine, index=False, if_exists='append')
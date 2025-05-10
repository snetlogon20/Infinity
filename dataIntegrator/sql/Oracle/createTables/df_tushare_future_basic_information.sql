--表名、列名、约束名均需 ≤ 30 字符（旧版本）或 ≤ 128 字符（新版本），故对表名进行了修改
--drop table citi.df_tushare_future_basic_info;
CREATE TABLE df_tushare_future_basic_info(
    ts_code          VARCHAR2(255) NOT NULL,
    symbol           VARCHAR2(255) NOT NULL,
    name             VARCHAR2(255) NOT NULL,
    quote_unit       VARCHAR2(255) NOT NULL,
    list_date        VARCHAR2(255) NOT NULL,
    delist_date      VARCHAR2(255) NOT NULL,
    CONSTRAINT pk_fut_basic  PRIMARY KEY (ts_code)
);
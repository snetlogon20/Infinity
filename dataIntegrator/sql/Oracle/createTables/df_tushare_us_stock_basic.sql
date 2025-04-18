CREATE TABLE citi.df_tushare_us_stock_basic(
    ts_code        VARCHAR2(255) NOT NULL,
    name           VARCHAR2(255),
    enname         VARCHAR2(255) NOT NULL,
    classify       VARCHAR2(255) NOT NULL,
    list_date      VARCHAR2(255) NOT NULL,
    delist_date    VARCHAR2(255),
    CONSTRAINT pk_df_tushare_stock_basic PRIMARY KEY (ts_code)
);
--drop table citi.df_tushare_fx_offshore_basic
CREATE TABLE df_tushare_fx_offshore_basic(
    ts_code            VARCHAR2(255) NOT NULL,
    name               VARCHAR2(255) NOT NULL,
    classify           VARCHAR2(255) NOT NULL,
    exchange           VARCHAR2(255) NOT NULL,
    min_unit           NUMBER NOT NULL,
    max_unit           NUMBER NOT NULL,
    pip                NUMBER NOT NULL,
    pip_cost           NUMBER NOT NULL,
    traget_spread      NUMBER NOT NULL,
    min_stop_distance  NUMBER NOT NULL,
    trading_hours      VARCHAR2(255),
    break_time         VARCHAR2(255),
    CONSTRAINT pk_fx_offshore PRIMARY KEY (ts_code, name)
);
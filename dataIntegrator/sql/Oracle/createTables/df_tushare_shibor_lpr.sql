-- DROP TABLE df_tushare_shibor_lpr_daily;
CREATE TABLE df_tushare_shibor_lpr_daily(
    trade_date   VARCHAR2(255) NOT NULL,
    tenor_1y     NUMBER NOT NULL,
    tenor_5y      NUMBER NOT NULL,
    CONSTRAINT pk_shibor_lpr PRIMARY KEY (trade_date)
);
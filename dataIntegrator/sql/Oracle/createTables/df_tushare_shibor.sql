-- DROP TABLE df_tushare_shibor_daily;
CREATE TABLE df_tushare_shibor_daily(
    trade_date   VARCHAR2(255) NOT NULL,
    tenor_on     NUMBER NOT NULL,
    tenor_1w     NUMBER NOT NULL,
    tenor_2w     NUMBER NOT NULL,
    tenor_1m     NUMBER NOT NULL,
    tenor_3m     NUMBER NOT NULL,
    tenor_6m     NUMBER NOT NULL,
    tenor_9m     NUMBER NOT NULL,
    tenor_1y     NUMBER NOT NULL,
    CONSTRAINT pk_shibor_daily PRIMARY KEY (trade_date)
);
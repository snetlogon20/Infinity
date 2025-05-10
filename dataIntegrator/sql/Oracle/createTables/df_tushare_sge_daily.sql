-- DROP TABLE df_tushare_sge_daily;
CREATE TABLE df_tushare_sge_daily(
    ts_code         VARCHAR2(255) NOT NULL,
    trade_date      VARCHAR2(255) NOT NULL,
    close          NUMBER NOT NULL,
    open           NUMBER NOT NULL,
    high           NUMBER NOT NULL,
    low            NUMBER NOT NULL,
    price_avg      NUMBER NOT NULL,
    change         NUMBER NOT NULL,
    pct_change     NUMBER NOT NULL,
    vol            NUMBER NOT NULL,
    amount         NUMBER NOT NULL,
    oi             NUMBER NOT NULL,
    settle_vol     NUMBER NOT NULL,
    settle_dire    VARCHAR2(255) NOT NULL,
    CONSTRAINT pk_sge_daily PRIMARY KEY (trade_date, ts_code)
);